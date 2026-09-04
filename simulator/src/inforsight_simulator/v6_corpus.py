"""Event-first v6 corpus implementing the bounded sigmoid hazard link substrate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import math
from typing import Any, Iterable

import numpy as np

from .v3_corpus import (
    V3Features, V3Observation, V3OracleRecord, reconstruct_v3_features,
    validate_feature_lineage, validate_v3_feature_payload, visible_events,
)
from .v6_config import (
    V6_COEFFICIENT_REGISTRY_VERSION, V6_SIMULATOR_CONTRACT_VERSION,
    V6_STREAM_REGISTRY_VERSION, V6CorpusConfig, artifact_id,
    canonical_json_bytes, complete_configuration, intervention_manifest,
    primitive_normal, primitive_uniform, scenario_configuration, stable_identifier,
    stream_set_id,
)

V6_EVENT_SCHEMA_VERSION = "6.0.0"
V6_OBSERVATION_SCHEMA_VERSION = "6.0.0"
V6_ORACLE_SIDECAR_VERSION = "6.0.0"
V6_QUADRATURE_VERSION = "gauss-hermite-32-sd-0.20-v1"
V6_ARTIFACT_VERSION = "1.0.0"
_MONTH_OFFSETS = (-0.08, 0.0, 0.08)
_PRODUCTS = ("fictional_term_life", "fictional_whole_life")
_NOTICE_CATEGORIES = ("billing_reminder", "grace_warning", "policy_update")
_CONTACT_CATEGORIES = ("billing_question", "coverage_question", "service_request")
_FREQUENCY_MONTHS = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}
_QUADRATURE_NODES, _QUADRATURE_WEIGHTS = np.polynomial.hermite.hermgauss(32)

V6_LAPSE_COEFFICIENTS = {
    "tenure": -0.20, "premium": 0.30, "quarterly": 0.15,
    "semiannual": 0.25, "annual": 0.35, "recent_delay": 1.20,
    "failed_payments": 1.80, "retries": 0.50, "recoveries": -0.80,
    "arrears": 1.50, "on_time_rate": -1.20, "rolling_payments": -0.25,
    "notices": 0.65, "contacts": 0.35, "failed_x_arrears": 0.60,
    "payment_missing": 0.0, "contact_missing": 0.0,
}
V6_SURRENDER_COEFFICIENTS = {
    "tenure": 0.10, "premium": 0.45, "quarterly": 0.10,
    "semiannual": 0.15, "annual": 0.20, "recent_delay": 0.35,
    "failed_payments": 0.50, "retries": 0.15, "recoveries": -0.20,
    "arrears": 0.40, "on_time_rate": -0.30, "rolling_payments": -0.10,
    "notices": 0.50, "contacts": 0.60, "failed_x_arrears": 0.20,
    "payment_missing": 0.0, "contact_missing": 0.0,
}
_ORDERED_LAPSE_COEFFS = np.array(list(V6_LAPSE_COEFFICIENTS.values()), dtype=float)
_ORDERED_SURRENDER_COEFFS = np.array(list(V6_SURRENDER_COEFFICIENTS.values()), dtype=float)


def _sigmoid(z: float) -> float:
    clipped = max(-15.0, min(15.0, z))
    return 1.0 / (1.0 + math.exp(-clipped))


@dataclass(frozen=True)
class V6Features(V3Features):
    """The public 17-feature surface is preserved under a separate v6 type."""


@dataclass(frozen=True)
class V6Observation(V3Observation):
    features: V6Features


@dataclass(frozen=True)
class V6OracleRecord(V3OracleRecord):
    """Protected v6 oracle sidecar record."""


@dataclass(frozen=True)
class V6Corpus:
    histories: tuple[tuple[dict[str, Any], ...], ...]
    observations: tuple[V6Observation, ...]
    oracle_sidecar: tuple[V6OracleRecord, ...]
    provenance: dict[str, Any]


def reconstruct_v6_features(events: Iterable[dict[str, Any]], cutoff: datetime
                            ) -> tuple[V6Features, dict[str, tuple[str, ...] | str]]:
    features, lineage = reconstruct_v3_features(events, cutoff)
    result = V6Features(**asdict(features))
    validate_feature_lineage(result, lineage, visible_events(events, cutoff))
    return result, lineage


def public_mechanism_terms(features: V6Features) -> dict[str, float]:
    """Return exact clipped public cutoff terms used by both v6 hazards."""

    return {
        "tenure": min(max(features.tenure_days / 365, 0), 5),
        "premium": min(max(math.log1p(features.premium_amount_cents / 100) / 5, 0), 2),
        "quarterly": float(features.billing_frequency == "quarterly"),
        "semiannual": float(features.billing_frequency == "semiannual"),
        "annual": float(features.billing_frequency == "annual"),
        "recent_delay": min(max((features.recent_delay_days or 0) / 30, 0), 3),
        "failed_payments": min(max(features.recent_failed_payment_count / 3, 0), 2),
        "retries": min(max(features.recent_retry_count / 3, 0), 2),
        "recoveries": min(max(features.recent_recovery_count / 3, 0), 2),
        "arrears": min(max(features.arrears_duration_days / 60, 0), 2),
        "on_time_rate": features.rolling_on_time_rate,
        "rolling_payments": min(max(features.rolling_payment_count / 12, 0), 2),
        "notices": min(max(features.recent_notice_count / 3, 0), 2),
        "contacts": min(max(features.recent_contact_count / 3, 0), 2),
        "failed_x_arrears": min(max(features.recent_failed_payment_count / 3, 0), 2)
        * min(max(features.arrears_duration_days / 60, 0), 2),
        "payment_missing": float(features.payment_attribute_missing),
        "contact_missing": float(features.contact_attribute_missing),
    }


def competing_hazards(features: V6Features, frailty: float, month: int, *,
                      signal_scale: float = 1.0, drift: float = 0.0,
                      enforce_generated_bound: bool = True) -> tuple[float, float, float]:
    if month not in (1, 2, 3):
        raise ValueError("month must be 1, 2, or 3")
    if not all(math.isfinite(value) for value in (frailty, signal_scale, drift)):
        raise ValueError("hazard inputs must be finite")
    z = public_mechanism_terms(features)
    lapse_score = (sum(V6_LAPSE_COEFFICIENTS[name] * z[name] for name in z) - 0.21) * 6.0
    surrender_score = (sum(V6_SURRENDER_COEFFICIENTS[name] * z[name] for name in z) - 0.20) * 6.0
    offset = _MONTH_OFFSETS[month - 1]
    z_lapse = -2.20 + offset + frailty + signal_scale * lapse_score + drift
    z_surrender = -2.80 + offset + 0.50 * frailty + signal_scale * surrender_score + drift
    lapse_h = 0.10 * _sigmoid(z_lapse)
    surrender_h = 0.05 * _sigmoid(z_surrender)
    total_h = lapse_h + surrender_h
    continuation = 1.0 - total_h
    if enforce_generated_bound and total_h >= 0.20:
        raise ValueError("total terminal hazard must remain below 0.20")
    return lapse_h, surrender_h, continuation


def cumulative_incidence(features: V6Features, frailty: float, *, signal_scale: float,
                         drift: float, enforce_generated_bound: bool = True
                         ) -> tuple[float, float, float]:
    survival, lapse, surrender = 1.0, 0.0, 0.0
    for month in (1, 2, 3):
        lapse_h, surrender_h, continuation = competing_hazards(
            features, frailty, month, signal_scale=signal_scale, drift=drift,
            enforce_generated_bound=enforce_generated_bound)
        lapse += survival * lapse_h
        surrender += survival * surrender_h
        survival *= continuation
    return lapse, surrender, lapse + surrender


def observable_oracle(features: V6Features, *, signal_scale: float,
                      drift: float) -> tuple[float, float, float]:
    nodes, weights = _QUADRATURE_NODES, _QUADRATURE_WEIGHTS
    z = public_mechanism_terms(features)
    values = np.fromiter(z.values(), dtype=float)
    lapse_score = (float(np.dot(_ORDERED_LAPSE_COEFFS, values)) - 0.21) * 6.0
    surrender_score = (float(np.dot(_ORDERED_SURRENDER_COEFFS, values)) - 0.20) * 6.0
    frailty = math.sqrt(2) * 0.20 * nodes
    survival = np.ones(32, dtype=float)
    lapse_total = np.zeros(32, dtype=float)
    surrender_total = np.zeros(32, dtype=float)
    for offset in _MONTH_OFFSETS:
        z_l = -2.20 + offset + frailty + signal_scale * lapse_score + drift
        z_s = -2.80 + offset + 0.50 * frailty + signal_scale * surrender_score + drift
        clipped_l = np.clip(z_l, -15.0, 15.0)
        clipped_s = np.clip(z_s, -15.0, 15.0)
        lapse_h = 0.10 / (1.0 + np.exp(-clipped_l))
        surrender_h = 0.05 / (1.0 + np.exp(-clipped_s))
        total_h = lapse_h + surrender_h
        lapse_total += survival * lapse_h
        surrender_total += survival * surrender_h
        survival *= (1.0 - total_h)
    totals = np.asarray((np.dot(weights, lapse_total),
                         np.dot(weights, surrender_total),
                         np.dot(weights, lapse_total + surrender_total))) / math.sqrt(math.pi)
    return tuple(round(float(value), 12) for value in totals)  # type: ignore[return-value]


def generate_v6_corpus(config: V6CorpusConfig, *, enforce_hazard_bound: bool = True) -> V6Corpus:
    histories: list[tuple[dict[str, Any], ...]] = []
    observations: list[V6Observation] = []
    sidecars: list[V6OracleRecord] = []
    aid = artifact_id(config)
    settings = scenario_configuration(config)["settings"]
    for cohort_index in range(config.cohort_count):
        issued_at = _add_months(config.issuance_start, cohort_index)
        cohort = issued_at.strftime("%Y-%m")
        for ordinal in range(config.policies_per_cohort):
            policy_id = stable_identifier("pol", config, cohort, ordinal)
            frequency = ("monthly", "quarterly", "semiannual", "annual")[ordinal % 4]
            role = _role(ordinal, config.policies_per_cohort)
            product = _PRODUCTS[int(primitive_uniform(config, "static_covariate", policy_id, "product") * 2)]
            premium = 6000 + int(primitive_uniform(config, "static_covariate", policy_id, "premium") * 14001)
            events = [_event(config, policy_id, "policy.issued", issued_at, 0, {
                "billing_frequency": frequency, "currency": "USD",
                "premium_amount_cents": premium, "product_type": product,
            })]
            frailty = round(0.20 * primitive_normal(config, "frailty", policy_id), 12)
            cutoff, episode, terminal, next_due = issued_at + timedelta(days=30), 0, False, 1
            while cutoff + timedelta(days=90) <= config.watermark and not terminal:
                payment_events, next_due = _scheduled_payments(
                    config, policy_id, issued_at, cutoff, frequency, next_due)
                events.extend(payment_events)
                events.extend(_service_events(config, policy_id, cutoff, episode))
                features, lineage = reconstruct_v6_features(events, cutoff)
                validate_v3_feature_payload(features)
                drift = float(settings["baseline_log_odds_shift"]) if cutoff >= datetime(2024, 1, 1, tzinfo=timezone.utc) else 0.0
                signal = float(settings["signal_scale"])
                conditional = tuple(round(value, 12) for value in cumulative_incidence(
                    features, frailty, signal_scale=signal, drift=drift,
                    enforce_generated_bound=enforce_hazard_bound))
                observable = observable_oracle(features, signal_scale=signal, drift=drift)
                episode_id = stable_identifier("epi", config, policy_id, cutoff.isoformat())
                observation_id = stable_identifier("obs", config, policy_id, cutoff.isoformat())
                draws = tuple(primitive_uniform(config, "outcome_uniform", policy_id, episode_id, month)
                              for month in (1, 2, 3))
                outcome_type = None
                outcome_event = None
                for month, draw in enumerate(draws, 1):
                    lapse_h, surrender_h, _ = competing_hazards(
                        features, frailty, month, signal_scale=signal, drift=drift,
                        enforce_generated_bound=enforce_hazard_bound)
                    if draw < lapse_h:
                        outcome_type = "outcome.lapsed"
                    elif draw < lapse_h + surrender_h:
                        outcome_type = "outcome.surrendered"
                    if outcome_type:
                        when = cutoff + timedelta(days=30 * month)
                        outcome_event = _event(config, policy_id, outcome_type, when,
                                               9_000_000 + episode, {"cause": outcome_type.split(".")[1]})
                        events.append(outcome_event)
                        terminal = True
                        break
                visible = visible_events(events, cutoff)
                visible_ids = tuple(sorted(event["event_id"] for event in visible))
                horizon = cutoff + timedelta(days=90)
                visible_outcome = outcome_event is not None and outcome_event in visible_events(events, config.watermark)
                observations.append(V6Observation(
                    observation_contract_version=V6_OBSERVATION_SCHEMA_VERSION,
                    label_policy_version=V6_SIMULATOR_CONTRACT_VERSION,
                    artifact_id=aid, observation_id=observation_id,
                    outcome_episode_id=episode_id, policy_id=policy_id, role=role,
                    cohort=cohort, as_of=_timestamp(cutoff), horizon_end=_timestamp(horizon),
                    follow_up_through=_timestamp(horizon), features=features,
                    feature_lineage=lineage, visible_event_ids=visible_ids,
                    visible_events_sha256=sha256(canonical_json_bytes(list(visible))).hexdigest(),
                    label_status="observed_positive" if visible_outcome else "observed_negative",
                    label_value=1 if visible_outcome else 0,
                    outcome_type=outcome_type if visible_outcome else None,
                    censoring_reason=None,
                ))
                sidecars.append(V6OracleRecord(
                    sidecar_version=V6_ORACLE_SIDECAR_VERSION,
                    quadrature_version=V6_QUADRATURE_VERSION, artifact_id=aid,
                    observation_id=observation_id, outcome_episode_id=episode_id,
                    oracle_conditional_lapse=conditional[0],
                    oracle_conditional_surrender=conditional[1],
                    oracle_conditional_union=conditional[2],
                    oracle_observable_lapse=observable[0],
                    oracle_observable_surrender=observable[1],
                    oracle_observable_union=observable[2], latent_frailty=frailty,
                    outcome_uniforms=draws,
                ))
                cutoff, episode = horizon, episode + 1
            histories.append(tuple(sorted(events, key=lambda event: (
                event["effective_at"], event["ingested_at"], event["event_id"]))))
    corpus = V6Corpus(tuple(histories), tuple(observations), tuple(sidecars), {
        "artifact_id": aid, "artifact_version": V6_ARTIFACT_VERSION,
        "coefficient_registry_version": V6_COEFFICIENT_REGISTRY_VERSION,
        "configuration": complete_configuration(config),
        "final_holdout_status": "not_materialized",
        "intervention": intervention_manifest(config),
        "random_stream_registry_version": V6_STREAM_REGISTRY_VERSION,
        "simulator_contract_version": V6_SIMULATOR_CONTRACT_VERSION,
        "stream_set_id": stream_set_id(config),
    })
    validate_v6_corpus(corpus, config)
    return corpus


def validate_v6_corpus(corpus: V6Corpus, config: V6CorpusConfig) -> None:
    if len(corpus.histories) != config.policy_count:
        raise ValueError("v6 corpus has an incorrect policy count")
    if len(corpus.observations) != len(corpus.oracle_sidecar):
        raise ValueError("every v6 observation requires one oracle sidecar")
    if len({row.observation_id for row in corpus.observations}) != len(corpus.observations):
        raise ValueError("v6 observation identities must be unique")
    if corpus.provenance.get("final_holdout_status") != "not_materialized":
        raise ValueError("final holdout must remain not_materialized")


def corpus_digest(corpus: V6Corpus) -> dict[str, str]:
    return {
        "histories_sha256": sha256(canonical_json_bytes(corpus.histories)).hexdigest(),
        "observations_sha256": sha256(canonical_json_bytes(
            [row.to_dict() for row in corpus.observations])).hexdigest(),
        "oracle_sidecar_sha256": sha256(canonical_json_bytes(corpus.oracle_sidecar)).hexdigest(),
    }


def _scheduled_payments(config: V6CorpusConfig, policy_id: str, issued_at: datetime,
                        cutoff: datetime, frequency: str, next_due: int
                        ) -> tuple[list[dict[str, Any]], int]:
    result = []
    step = _FREQUENCY_MONTHS[frequency]
    while _add_months(issued_at, next_due * step) <= cutoff:
        due = _add_months(issued_at, next_due * step)
        primitive_uniform(config, "scheduled_payment_opportunity", policy_id, next_due)
        u = primitive_uniform(config, "behavior_value", policy_id, "payment", next_due, "state")
        missing = primitive_uniform(config, "missingness", policy_id, f"payment-delay-{next_due}") < float(
            scenario_configuration(config)["settings"]["mcar_threshold"])
        failed, retry = int(u < 0.05), int(u < 0.04)
        recovered = int(u < 0.03)
        delay = None if missing else round(15 * u, 6)
        arrears_u = primitive_uniform(config, "behavior_value", policy_id, "payment", next_due, "arrears_days")
        payment = _event(config, policy_id, "payment.recorded", due, next_due * 10 + 1, {
            "arrears_days": 1 + math.floor(60 * arrears_u) if failed else 0,
            "delay_days": delay, "failed": failed,
            "on_time": int(not failed and (delay or 0) <= 1),
            "recovered": int(recovered and retry), "retry": int(retry and failed),
            "scheduled_opportunity_ordinal": next_due,
        })
        result.append(payment)
        if primitive_uniform(config, "correction", payment["event_id"], "delay_days") < 0.03 and delay is not None:
            result.append(_event(config, policy_id, "event.corrected", due + timedelta(days=2),
                                 next_due * 10 + 2, {"target_event_id": payment["event_id"],
                                                     "replacement_delay_days": round(delay / 2, 6)}))
        next_due += 1
    return result, next_due


def _service_events(config: V6CorpusConfig, policy_id: str, cutoff: datetime,
                    episode: int) -> list[dict[str, Any]]:
    result = []
    u = primitive_uniform(config, "behavior_value", policy_id, "notice", episode, "present")
    if u < 0.35:
        result.append(_event(config, policy_id, "notice.sent", cutoff - timedelta(days=13),
                             8_000_000 + episode * 2, {"category": _NOTICE_CATEGORIES[int(u * 3) % 3]}))
    u = primitive_uniform(config, "behavior_value", policy_id, "contact", episode, "present")
    if u < 0.30:
        result.append(_event(config, policy_id, "service.contact", cutoff - timedelta(days=11),
                             8_000_001 + episode * 2, {"category": _CONTACT_CATEGORIES[int((1-u) * 3) % 3]}))
    return result


def _event(config: V6CorpusConfig, policy_id: str, event_type: str,
           effective_at: datetime, ordinal: int, payload: dict[str, Any]) -> dict[str, Any]:
    event_id = stable_identifier("evt", config, policy_id, event_type, ordinal)
    delay_u = primitive_uniform(config, "ingestion_delay", event_id)
    mixture = scenario_configuration(config)["settings"]["delay_mixture"]
    p1, p2 = float(mixture[0]), float(mixture[1])
    if delay_u < p1:
        delay = timedelta(hours=24 * delay_u / p1)
    elif delay_u < p1 + p2:
        delay = timedelta(days=1 + 6 * (delay_u - p1) / p2)
    else:
        delay = timedelta(days=7 + 23 * (delay_u - p1 - p2) / float(mixture[2]))
    return {"schema_version": V6_EVENT_SCHEMA_VERSION, "event_id": event_id,
            "policy_id": policy_id, "event_type": event_type,
            "effective_at": _timestamp(effective_at),
            "ingested_at": _timestamp(effective_at + delay), "payload": payload}


def _role(ordinal: int, size: int) -> str:
    counts = [int(size * value) for value in (0.50, 0.10, 0.10, 0.10, 0.20)]
    counts[0] += size - sum(counts)
    for role, count in zip(("fit", "selection", "calibration", "non_final_evaluation", "acceptance"), counts, strict=True):
        if ordinal < count:
            return role
        ordinal -= count
    raise ValueError("role ordinal exceeds cohort allocation")


def _add_months(value: datetime, months: int) -> datetime:
    total = value.year * 12 + value.month - 1 + months
    day = min(value.day, (28, 29 if total // 12 % 4 == 0 else 28, 31, 30, 31, 30,
                          31, 31, 30, 31, 30, 31)[total % 12])
    return value.replace(year=total // 12, month=total % 12 + 1, day=day)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "V6_ARTIFACT_VERSION", "V6_EVENT_SCHEMA_VERSION", "V6_LAPSE_COEFFICIENTS",
    "V6_OBSERVATION_SCHEMA_VERSION", "V6_ORACLE_SIDECAR_VERSION",
    "V6_QUADRATURE_VERSION", "V6_SURRENDER_COEFFICIENTS", "V6Corpus", "V6Features",
    "V6Observation", "V6OracleRecord", "competing_hazards", "corpus_digest",
    "cumulative_incidence", "generate_v6_corpus", "observable_oracle",
    "public_mechanism_terms", "reconstruct_v6_features", "validate_v6_corpus",
]

