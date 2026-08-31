"""Event-first v3 corpus, dual-time observations, and protected oracle sidecars."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import math
from typing import Any, Iterable

import numpy as np

from .v3_config import (
    V3_BILLING_FREQUENCIES, V3_CONTRACT_VERSION, V3_FINAL_HOLDOUT_STATUS,
    V3_ROLE_COUNTS_PER_600, V3_ROLES, V3CorpusConfig, artifact_id,
    canonical_json_bytes, complete_configuration, intervention_manifest,
    primitive_normal, primitive_uniform, scenario_configuration, stable_identifier,
    stream_set_id,
)


V3_EVENT_SCHEMA_VERSION = "3.0.0"
V3_OBSERVATION_SCHEMA_VERSION = "3.0.0"
V3_ORACLE_SIDECAR_VERSION = "3.0.0"
V3_QUADRATURE_VERSION = "gauss-hermite-32-v1"
V3_ARTIFACT_VERSION = "1.0.0"
_PRODUCTS = ("fictional_term_life", "fictional_whole_life")
_NOTICE_CATEGORIES = ("billing_reminder", "grace_warning", "policy_update")
_CONTACT_CATEGORIES = ("billing_question", "coverage_question", "service_request")
_MONTH_OFFSETS = (-0.08, 0.0, 0.08)
_PROTECTED_TOKENS = (
    "oracle", "frailty", "draw", "scenario", "role", "outcome", "identifier",
    "event_id", "artifact_id", "stream_set_id", "label",
)


@dataclass(frozen=True)
class V3Features:
    tenure_days: int
    premium_amount_cents: int
    product_type: str
    billing_frequency: str
    recent_delay_days: float | None
    recent_failed_payment_count: int
    recent_retry_count: int
    recent_recovery_count: int
    arrears_duration_days: int
    rolling_on_time_rate: float
    rolling_payment_count: int
    recent_notice_count: int
    notice_category: str
    recent_contact_count: int
    contact_category: str
    payment_attribute_missing: bool
    contact_attribute_missing: bool


@dataclass(frozen=True)
class V3Observation:
    observation_contract_version: str
    label_policy_version: str
    artifact_id: str
    observation_id: str
    outcome_episode_id: str
    policy_id: str
    role: str
    cohort: str
    as_of: str
    horizon_end: str
    follow_up_through: str
    features: V3Features
    feature_lineage: dict[str, tuple[str, ...] | str]
    visible_event_ids: tuple[str, ...]
    visible_events_sha256: str
    label_status: str
    label_value: int | None
    outcome_type: str | None
    censoring_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["visible_event_ids"] = list(self.visible_event_ids)
        value["feature_lineage"] = {
            key: list(source) if isinstance(source, tuple) else source
            for key, source in self.feature_lineage.items()
        }
        return value


@dataclass(frozen=True)
class V3OracleRecord:
    sidecar_version: str
    quadrature_version: str
    artifact_id: str
    observation_id: str
    outcome_episode_id: str
    oracle_conditional_lapse: float
    oracle_conditional_surrender: float
    oracle_conditional_union: float
    oracle_observable_lapse: float
    oracle_observable_surrender: float
    oracle_observable_union: float
    latent_frailty: float
    outcome_uniforms: tuple[float, float, float]


@dataclass(frozen=True)
class V3Corpus:
    histories: tuple[tuple[dict[str, Any], ...], ...]
    observations: tuple[V3Observation, ...]
    oracle_sidecar: tuple[V3OracleRecord, ...]
    provenance: dict[str, Any]


def visible_events(events: Iterable[dict[str, Any]], cutoff: datetime) -> tuple[dict[str, Any], ...]:
    """Return the canonical dual-time-visible history at cutoff."""

    cutoff_text = _timestamp(cutoff)
    admitted = [event for event in events
                if event["effective_at"] <= cutoff_text and event["ingested_at"] <= cutoff_text]
    return tuple(sorted(admitted, key=lambda event: (event["effective_at"], event["ingested_at"], event["event_id"])))


def reconstruct_v3_features(events: Iterable[dict[str, Any]], cutoff: datetime) -> tuple[V3Features, dict[str, tuple[str, ...] | str]]:
    """Reconstruct the frozen public vector only from dual-time-visible events."""

    visible = visible_events(events, cutoff)
    issued = [event for event in visible if event["event_type"] == "policy.issued"]
    if len(issued) != 1:
        raise ValueError("visible history must contain one policy.issued event")
    issue = issued[0]
    corrections = {event["payload"]["target_event_id"]: event for event in visible
                   if event["event_type"] == "event.corrected"}
    payments = []
    for event in visible:
        if event["event_type"] != "payment.recorded":
            continue
        corrected = dict(event)
        corrected["payload"] = dict(event["payload"])
        if event["event_id"] in corrections:
            corrected["payload"]["delay_days"] = corrections[event["event_id"]]["payload"]["replacement_delay_days"]
        payments.append(corrected)
    recent_start = cutoff - timedelta(days=90)
    rolling_start = cutoff - timedelta(days=365)
    recent_payments = [event for event in payments if _parse(event["effective_at"]) > recent_start]
    rolling_payments = [event for event in payments if _parse(event["effective_at"]) > rolling_start]
    notices = [event for event in visible if event["event_type"] == "notice.sent"
               and _parse(event["effective_at"]) > recent_start]
    contacts = [event for event in visible if event["event_type"] == "service.contact"
                and _parse(event["effective_at"]) > recent_start]
    recent_original_ids = {event["event_id"] for event in recent_payments}
    rolling_original_ids = {event["event_id"] for event in rolling_payments}
    payment_ids = tuple(sorted(recent_original_ids | {
        correction["event_id"] for target, correction in corrections.items()
        if target in recent_original_ids
    }))
    rolling_ids = tuple(sorted(rolling_original_ids | {
        correction["event_id"] for target, correction in corrections.items()
        if target in rolling_original_ids
    }))
    notice_ids = tuple(event["event_id"] for event in notices)
    contact_ids = tuple(event["event_id"] for event in contacts)
    last_payment = recent_payments[-1] if recent_payments else None
    nonmissing_delays = [event["payload"]["delay_days"] for event in recent_payments
                         if event["payload"].get("delay_days") is not None]
    features = V3Features(
        tenure_days=(cutoff - _parse(issue["effective_at"])).days,
        premium_amount_cents=issue["payload"]["premium_amount_cents"],
        product_type=issue["payload"]["product_type"],
        billing_frequency=issue["payload"]["billing_frequency"],
        recent_delay_days=float(nonmissing_delays[-1]) if nonmissing_delays else None,
        recent_failed_payment_count=sum(event["payload"]["failed"] for event in recent_payments),
        recent_retry_count=sum(event["payload"]["retry"] for event in recent_payments),
        recent_recovery_count=sum(event["payload"]["recovered"] for event in recent_payments),
        arrears_duration_days=int(last_payment["payload"]["arrears_days"]) if last_payment else 0,
        rolling_on_time_rate=(sum(event["payload"]["on_time"] for event in rolling_payments) /
                              len(rolling_payments) if rolling_payments else 0.5),
        rolling_payment_count=len(rolling_payments),
        recent_notice_count=len(notices),
        notice_category=notices[-1]["payload"]["category"] if notices else "none",
        recent_contact_count=len(contacts),
        contact_category=contacts[-1]["payload"]["category"] if contacts else "none",
        payment_attribute_missing=bool(last_payment and last_payment["payload"].get("delay_days") is None),
        contact_attribute_missing=bool(contacts and contacts[-1]["payload"].get("category") == "missing"),
    )
    issue_id = (issue["event_id"],)
    lineage: dict[str, tuple[str, ...] | str] = {
        "tenure_days": "cutoff_derived", "premium_amount_cents": issue_id,
        "product_type": issue_id, "billing_frequency": issue_id,
        "recent_delay_days": payment_ids, "recent_failed_payment_count": payment_ids,
        "recent_retry_count": payment_ids, "recent_recovery_count": payment_ids,
        "arrears_duration_days": payment_ids, "rolling_on_time_rate": rolling_ids,
        "rolling_payment_count": rolling_ids, "recent_notice_count": notice_ids,
        "notice_category": notice_ids, "recent_contact_count": contact_ids,
        "contact_category": contact_ids, "payment_attribute_missing": payment_ids,
        "contact_attribute_missing": contact_ids,
    }
    validate_feature_lineage(features, lineage, visible)
    return features, lineage


def validate_feature_lineage(features: V3Features, lineage: dict[str, tuple[str, ...] | str],
                             visible: Iterable[dict[str, Any]]) -> None:
    if set(lineage) != set(V3Features.__dataclass_fields__):
        raise ValueError("lineage must cover every v3 feature exactly once")
    visible_ids = {event["event_id"] for event in visible}
    for feature, sources in lineage.items():
        if sources == "cutoff_derived":
            if feature != "tenure_days":
                raise ValueError("only declared cutoff-derived features may omit event lineage")
            continue
        if not isinstance(sources, tuple) or len(sources) != len(set(sources)):
            raise ValueError("event lineage must be a unique tuple")
        if any(source not in visible_ids for source in sources):
            raise ValueError("feature lineage names an invisible event")


def validate_v3_feature_payload(payload: Any) -> None:
    value = asdict(payload) if isinstance(payload, V3Features) else payload
    if not isinstance(value, dict) or set(value) != set(V3Features.__dataclass_fields__):
        raise ValueError("v3 feature payload does not match the frozen public surface")
    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, nested in node.items():
                normalized = str(key).lower().replace("-", "_")
                if any(token in normalized for token in _PROTECTED_TOKENS):
                    raise ValueError(f"protected v3 feature concept: {key}")
                visit(nested)
        elif isinstance(node, (list, tuple)):
            for nested in node:
                visit(nested)
    visit(value)


def competing_hazards(features: V3Features, frailty: float, month: int, *,
                      signal_scale: float = 1.0, drift: float = 0.0,
                      enforce_generated_bound: bool = True) -> tuple[float, float, float]:
    if month not in (1, 2, 3):
        raise ValueError("month must be 1, 2, or 3")
    if not all(math.isfinite(value) for value in (frailty, signal_scale, drift)):
        raise ValueError("hazard inputs must be finite")
    tenure = min(max(features.tenure_days / 365, 0), 5)
    premium = min(max(math.log1p(features.premium_amount_cents / 100) / 5, 0), 2)
    category_lapse = {"monthly": 0.0, "quarterly": 0.06, "semiannual": 0.10, "annual": 0.14}[features.billing_frequency]
    category_surrender = {"monthly": 0.0, "quarterly": 0.04, "semiannual": 0.06, "annual": 0.08}[features.billing_frequency]
    delay = min(max((features.recent_delay_days or 0) / 30, 0), 3)
    failed = min(max(features.recent_failed_payment_count / 3, 0), 2)
    retries = min(max(features.recent_retry_count / 3, 0), 2)
    recoveries = min(max(features.recent_recovery_count / 3, 0), 2)
    arrears = min(max(features.arrears_duration_days / 60, 0), 2)
    payments = min(max(features.rolling_payment_count / 12, 0), 2)
    notices = min(max(features.recent_notice_count / 3, 0), 2)
    contacts = min(max(features.recent_contact_count / 3, 0), 2)
    lapse_score = (-0.08 * tenure + 0.12 * premium + category_lapse + 0.42 * delay +
                   0.70 * failed + 0.18 * retries - 0.30 * recoveries + 0.55 * arrears -
                   0.45 * features.rolling_on_time_rate - 0.10 * payments +
                   0.24 * notices + 0.12 * contacts + 0.22 * failed * arrears)
    surrender_score = (0.04 * tenure + 0.18 * premium + category_surrender + 0.12 * delay +
                       0.20 * failed + 0.05 * retries - 0.08 * recoveries + 0.15 * arrears -
                       0.12 * features.rolling_on_time_rate - 0.04 * payments +
                       0.18 * notices + 0.22 * contacts + 0.08 * failed * arrears)
    eta_lapse = -3.35 + _MONTH_OFFSETS[month - 1] + frailty + signal_scale * lapse_score + drift
    eta_surrender = -4.05 + _MONTH_OFFSETS[month - 1] + 0.50 * frailty + signal_scale * surrender_score + drift
    lapse_exp, surrender_exp = math.exp(eta_lapse), math.exp(eta_surrender)
    denominator = 1 + lapse_exp + surrender_exp
    result = (lapse_exp / denominator, surrender_exp / denominator,
              1 / denominator)
    if enforce_generated_bound and result[0] + result[1] >= 0.20:
        raise ValueError("total terminal hazard must remain below 0.20")
    return result


def cumulative_incidence(features: V3Features, frailty: float, *, signal_scale: float,
                         drift: float, enforce_generated_bound: bool = True) -> tuple[float, float, float]:
    survival, lapse, surrender = 1.0, 0.0, 0.0
    for month in (1, 2, 3):
        lapse_h, surrender_h, continuation = competing_hazards(
            features, frailty, month, signal_scale=signal_scale, drift=drift,
            enforce_generated_bound=enforce_generated_bound)
        lapse += survival * lapse_h
        surrender += survival * surrender_h
        survival *= continuation
    return lapse, surrender, lapse + surrender


def observable_oracle(features: V3Features, *, signal_scale: float,
                      drift: float) -> tuple[float, float, float]:
    nodes, weights = np.polynomial.hermite.hermgauss(32)
    totals = np.zeros(3, dtype=float)
    for node, weight in zip(nodes, weights, strict=True):
        frailty = math.sqrt(2) * 0.35 * float(node)
        totals += float(weight) * np.asarray(cumulative_incidence(
            features, frailty, signal_scale=signal_scale, drift=drift,
            enforce_generated_bound=False))
    totals /= math.sqrt(math.pi)
    return tuple(round(float(value), 12) for value in totals)  # type: ignore[return-value]


def generate_v3_corpus(config: V3CorpusConfig) -> V3Corpus:
    histories: list[tuple[dict[str, Any], ...]] = []
    observations: list[V3Observation] = []
    sidecars: list[V3OracleRecord] = []
    aid = artifact_id(config)
    scenario = scenario_configuration(config)["settings"]
    for cohort_index in range(config.cohort_count):
        issued_at = _add_months(config.issuance_start, cohort_index)
        cohort = issued_at.strftime("%Y-%m")
        for ordinal in range(config.policies_per_cohort):
            policy_id = stable_identifier("pol", config, cohort, ordinal)
            frequency = V3_BILLING_FREQUENCIES[ordinal % 4]
            role = _role(ordinal, config.policies_per_cohort)
            product = _PRODUCTS[int(primitive_uniform(config, "static_covariate", policy_id, "product") * 2)]
            premium = 6000 + int(primitive_uniform(config, "static_covariate", policy_id, "premium") * 14001)
            events = [_event(config, policy_id, "policy.issued", issued_at, 0, {
                "billing_frequency": frequency, "currency": "USD",
                "premium_amount_cents": premium, "product_type": product,
            })]
            frailty = round(0.35 * primitive_normal(config, "frailty", policy_id), 12)
            cutoff = issued_at + timedelta(days=30)
            episode = 0
            terminal = False
            while cutoff + timedelta(days=90) <= config.watermark and not terminal:
                events.extend(_behavior_events(config, policy_id, cutoff, episode))
                features, lineage = reconstruct_v3_features(events, cutoff)
                validate_v3_feature_payload(features)
                drift = float(scenario["baseline_log_odds_shift"]) if cutoff >= datetime(2024, 1, 1, tzinfo=timezone.utc) else 0.0
                signal = float(scenario["signal_scale"])
                conditional = tuple(round(value, 12) for value in cumulative_incidence(
                    features, frailty, signal_scale=signal, drift=drift))
                observable = observable_oracle(features, signal_scale=signal, drift=drift)
                episode_id = stable_identifier("epi", config, policy_id, cutoff.isoformat())
                observation_id = stable_identifier("obs", config, policy_id, cutoff.isoformat())
                draws = tuple(primitive_uniform(config, "outcome_uniform", policy_id, episode_id, month)
                              for month in (1, 2, 3))
                outcome_type: str | None = None
                outcome_event: dict[str, Any] | None = None
                for month, draw in enumerate(draws, 1):
                    lapse, surrender, _ = competing_hazards(
                        features, frailty, month, signal_scale=signal, drift=drift)
                    if draw < lapse:
                        outcome_type = "outcome.lapsed"
                    elif draw < lapse + surrender:
                        outcome_type = "outcome.surrendered"
                    if outcome_type:
                        when = cutoff + timedelta(days=30 * month)
                        outcome_event = _event(config, policy_id, outcome_type, when,
                                               10_000 + episode, {"cause": outcome_type.split(".")[1]})
                        events.append(outcome_event)
                        terminal = True
                        break
                visible = visible_events(events, cutoff)
                visible_ids = tuple(sorted(event["event_id"] for event in visible))
                horizon = cutoff + timedelta(days=90)
                watermark_visible = visible_events(events, config.watermark)
                visible_outcome = (
                    outcome_event is not None
                    and outcome_event in watermark_visible
                    and cutoff < _parse(outcome_event["effective_at"]) <= horizon
                )
                label_status = "observed_positive" if visible_outcome else "observed_negative"
                label_value = 1 if visible_outcome else 0
                observations.append(V3Observation(
                    observation_contract_version=V3_OBSERVATION_SCHEMA_VERSION,
                    label_policy_version=V3_CONTRACT_VERSION, artifact_id=aid,
                    observation_id=observation_id, outcome_episode_id=episode_id,
                    policy_id=policy_id, role=role, cohort=cohort, as_of=_timestamp(cutoff),
                    horizon_end=_timestamp(horizon), follow_up_through=_timestamp(horizon),
                    features=features, feature_lineage=lineage, visible_event_ids=visible_ids,
                    visible_events_sha256=sha256(canonical_json_bytes(list(visible))).hexdigest(),
                    label_status=label_status, label_value=label_value,
                    outcome_type=outcome_type if visible_outcome else None, censoring_reason=None,
                ))
                sidecars.append(V3OracleRecord(
                    sidecar_version=V3_ORACLE_SIDECAR_VERSION,
                    quadrature_version=V3_QUADRATURE_VERSION, artifact_id=aid,
                    observation_id=observation_id, outcome_episode_id=episode_id,
                    oracle_conditional_lapse=conditional[0],
                    oracle_conditional_surrender=conditional[1],
                    oracle_conditional_union=conditional[2],
                    oracle_observable_lapse=observable[0],
                    oracle_observable_surrender=observable[1],
                    oracle_observable_union=observable[2], latent_frailty=frailty,
                    outcome_uniforms=draws,
                ))
                cutoff = horizon
                episode += 1
            histories.append(tuple(sorted(events, key=lambda event: (
                event["effective_at"], event["ingested_at"], event["event_id"]))))
    corpus = V3Corpus(tuple(histories), tuple(observations), tuple(sidecars), {
        "artifact_id": aid, "artifact_version": V3_ARTIFACT_VERSION,
        "configuration": complete_configuration(config),
        "final_holdout_status": V3_FINAL_HOLDOUT_STATUS,
        "intervention": intervention_manifest(config), "stream_set_id": stream_set_id(config),
    })
    validate_v3_corpus(corpus, config)
    return corpus


def validate_v3_corpus(corpus: V3Corpus, config: V3CorpusConfig) -> None:
    if len(corpus.histories) != config.policy_count:
        raise ValueError("v3 corpus has an incorrect policy count")
    if len(corpus.observations) != len(corpus.oracle_sidecar):
        raise ValueError("every v3 observation requires one oracle sidecar")
    policy_ids = [history[0]["policy_id"] for history in corpus.histories]
    if len(policy_ids) != len(set(policy_ids)):
        raise ValueError("v3 policy identities must be unique")
    observation_ids = [record.observation_id for record in corpus.observations]
    episode_ids = [record.outcome_episode_id for record in corpus.observations]
    if len(observation_ids) != len(set(observation_ids)) or len(episode_ids) != len(set(episode_ids)):
        raise ValueError("v3 observation and episode identities must be unique")
    if corpus.provenance.get("final_holdout_status") != "not_materialized":
        raise ValueError("final holdout must remain not_materialized")


def corpus_digest(corpus: V3Corpus) -> dict[str, str]:
    return {
        "histories_sha256": sha256(canonical_json_bytes(
            _portable_artifact(corpus.histories))).hexdigest(),
        "observations_sha256": sha256(canonical_json_bytes(
            _portable_artifact([record.to_dict() for record in corpus.observations]))).hexdigest(),
        "oracle_sidecar_sha256": sha256(canonical_json_bytes(
            _portable_artifact(corpus.oracle_sidecar))).hexdigest(),
    }


def _portable_artifact(value: Any) -> Any:
    """Normalize subprecision native-math noise at the committed evidence boundary."""

    if isinstance(value, float):
        return round(value, 10)
    if isinstance(value, dict):
        return {key: _portable_artifact(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable_artifact(nested) for nested in value]
    if hasattr(value, "__dataclass_fields__"):
        return _portable_artifact(asdict(value))
    return value


def _behavior_events(config: V3CorpusConfig, policy_id: str, cutoff: datetime,
                     episode: int) -> list[dict[str, Any]]:
    settings = scenario_configuration(config)["settings"]
    u = primitive_uniform(config, "behavior_value", policy_id, "payment", episode, "state")
    missing = primitive_uniform(config, "missingness", policy_id, f"payment-delay-{episode}") < float(settings["mcar_threshold"])
    failed = int(u < 0.05)
    retry = int(failed and u < 0.04)
    recovered = int(retry and u < 0.03)
    delay = None if missing else round(15 * u, 6)
    arrears = int(15 * u) if failed else 0
    when = cutoff - timedelta(days=10)
    payment = _event(config, policy_id, "payment.recorded", when, episode * 4 + 1, {
        "arrears_days": arrears, "delay_days": delay, "failed": failed,
        "on_time": int(not failed and (delay or 0) <= 1), "recovered": recovered,
        "retry": retry,
    })
    result = [payment]
    if primitive_uniform(config, "correction", payment["event_id"], "delay_days") < 0.03 and delay is not None:
        result.append(_event(config, policy_id, "event.corrected", when + timedelta(days=2),
                             episode * 4 + 2, {"target_event_id": payment["event_id"],
                                               "replacement_delay_days": round(delay / 2, 6)}))
    notice_threshold = 0.35
    if config.scenario == "moderate_drift" and cutoff >= datetime(2024, 1, 1, tzinfo=timezone.utc):
        notice_threshold += 0.15
    if primitive_uniform(config, "behavior_value", policy_id, "notice", episode, "present") < notice_threshold:
        category = _NOTICE_CATEGORIES[int(u * len(_NOTICE_CATEGORIES)) % len(_NOTICE_CATEGORIES)]
        result.append(_event(config, policy_id, "notice.sent", when - timedelta(days=3),
                             episode * 4 + 3, {"category": category}))
    if primitive_uniform(config, "behavior_value", policy_id, "contact", episode, "present") < 0.30:
        category = _CONTACT_CATEGORIES[int((1 - u) * len(_CONTACT_CATEGORIES)) % len(_CONTACT_CATEGORIES)]
        if config.scenario == "unknown_category_arrival" and cutoff >= datetime(2024, 1, 1, tzinfo=timezone.utc):
            category = "new_service_category"
        result.append(_event(config, policy_id, "service.contact", when - timedelta(days=1),
                             episode * 4 + 4, {"category": category}))
    return result


def _event(config: V3CorpusConfig, policy_id: str, event_type: str, effective_at: datetime,
           ordinal: int, payload: dict[str, Any]) -> dict[str, Any]:
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
    return {
        "schema_version": V3_EVENT_SCHEMA_VERSION, "event_id": event_id,
        "policy_id": policy_id, "event_type": event_type,
        "effective_at": _timestamp(effective_at), "ingested_at": _timestamp(effective_at + delay),
        "payload": payload,
    }


def _role(ordinal: int, cohort_size: int) -> str:
    cursor = ordinal
    proportions = (0.50, 0.10, 0.10, 0.10, 0.20)
    counts = [int(cohort_size * proportion) for proportion in proportions]
    counts[0] += cohort_size - sum(counts)
    for role, count in zip(V3_ROLES, counts, strict=True):
        if cursor < count:
            return role
        cursor -= count
    raise ValueError("role ordinal exceeds cohort allocation")


def _add_months(value: datetime, months: int) -> datetime:
    total = value.year * 12 + value.month - 1 + months
    return value.replace(year=total // 12, month=total % 12 + 1)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
