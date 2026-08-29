"""Deterministic synthetic v2 corpus and recurring observation generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
import random
from typing import Any

import numpy as np

from .v2_config import (
    V2_BILLING_FREQUENCIES,
    V2CorpusConfig,
    canonical_v2_configuration,
    v2_configuration_digest,
    v2_domain_seed,
    v2_run_identity,
)


V2_EVENT_SCHEMA_VERSION = "2.0.0"
V2_ORACLE_SIDECAR_VERSION = "1.0.0"
V2_QUADRATURE_VERSION = "gauss-hermite-32-v1"
V2_ARTIFACT_VERSION = "1.0.0"
_PRODUCTS = ("fictional_term_life", "fictional_whole_life")
_ROLES = ("fit", "selection", "calibration", "non_final_evaluation", "r2_acceptance")
_ROLE_COUNTS_PER_150 = (75, 15, 15, 15, 30)


@dataclass(frozen=True)
class V2Features:
    tenure_days: int
    premium_amount_cents: int
    product_type: str
    billing_frequency: str
    due_to_paid_delay_days: float | None
    rolling_on_time_payment_rate: float
    recent_failed_payment_count: int
    recent_retry_count: int
    recent_recovery_count: int
    arrears_duration_days: int
    recent_notice_count: int
    notice_category: str
    recent_service_contact_count: int
    contact_category: str
    visible_grace_entries: int
    visible_grace_recoveries: int
    payment_attribute_missing: bool
    contact_attribute_missing: bool


@dataclass(frozen=True)
class V2Observation:
    observation_contract_version: str
    label_policy_version: str
    observation_id: str
    outcome_episode_id: str
    policy_id: str
    role: str
    cohort: str
    as_of: str
    horizon_end: str
    follow_up_through: str
    features: V2Features
    label_status: str
    label_value: int | None
    outcome_type: str | None
    censoring_reason: str | None
    visible_event_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["visible_event_ids"] = list(self.visible_event_ids)
        return result


@dataclass(frozen=True)
class V2OracleRecord:
    sidecar_version: str
    quadrature_version: str
    run_identity: str
    observation_id: str
    outcome_episode_id: str
    oracle_conditional_lapse: float
    oracle_conditional_surrender: float
    oracle_conditional: float
    oracle_observable_lapse: float
    oracle_observable_surrender: float
    oracle_observable: float
    latent_frailty: float
    outcome_uniform_draw: float
    signal_mode: str
    drift_scenario: str


@dataclass(frozen=True)
class V2Corpus:
    histories: tuple[tuple[dict[str, Any], ...], ...]
    observations: tuple[V2Observation, ...]
    oracle_sidecar: tuple[V2OracleRecord, ...]
    provenance: dict[str, Any]


def validate_v2_feature_payload(payload: Any) -> None:
    """Reject protected concepts recursively and require the frozen v2 surface."""

    value = asdict(payload) if isinstance(payload, V2Features) else payload
    if not isinstance(value, dict):
        raise ValueError("v2 feature payload must be a mapping")
    allowed = frozenset(V2Features.__dataclass_fields__)
    if frozenset(value) != allowed:
        raise ValueError("v2 feature payload does not match the frozen feature surface")
    protected = ("oracle", "frailty", "draw", "scenario", "role", "outcome", "identifier", "event_id")
    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, nested in node.items():
                normalized = str(key).lower().replace("-", "_")
                if any(token in normalized for token in protected):
                    raise ValueError(f"protected v2 feature concept: {key}")
                visit(nested)
        elif isinstance(node, (list, tuple)):
            for nested in node:
                visit(nested)
    visit(value)


def competing_hazards(
    features: V2Features,
    frailty: float,
    *,
    signal_mode: str,
    drift_scenario: str,
) -> tuple[float, float, float]:
    """Return monthly lapse, surrender, and continuation probabilities."""

    if not math.isfinite(frailty):
        raise ValueError("frailty must be finite")
    signal = 0.0 if signal_mode == "null_signal" else 1.0
    drift = {"stable": 0.0, "moderate_drift": 0.20, "stress_drift": 0.50}[drift_scenario]
    premium = (features.premium_amount_cents - 10000) / 10000
    annual = 1.0 if features.billing_frequency == "annual" else 0.0
    whole = 1.0 if features.product_type == "fictional_whole_life" else 0.0
    eta_lapse = (
        -5.00
        + frailty
        + drift
        + signal
        * (
            0.45 * premium
            + 0.55 * features.recent_failed_payment_count
            + 0.035 * min(features.arrears_duration_days, 30)
            - 0.80 * features.rolling_on_time_payment_rate
            + 0.35 * annual * features.recent_failed_payment_count
        )
    )
    eta_surrender = (
        -5.30
        + 0.5 * frailty
        + 0.5 * drift
        + signal
        * (
            0.30 * premium
            + 0.40 * whole
            + 0.20 * features.recent_service_contact_count
            + 0.00025 * min(features.tenure_days, 1460)
        )
    )
    lapse_exp = math.exp(eta_lapse)
    surrender_exp = math.exp(eta_surrender)
    denominator = 1.0 + lapse_exp + surrender_exp
    lapse = lapse_exp / denominator
    surrender = surrender_exp / denominator
    continuation = 1.0 - lapse - surrender
    return lapse, surrender, continuation


def cumulative_incidence(lapse: float, surrender: float) -> tuple[float, float, float]:
    """Return exact three-month cause-specific and union cumulative incidence."""

    continuation = 1.0 - lapse - surrender
    exposure_sum = 1.0 + continuation + continuation * continuation
    lapse_90 = lapse * exposure_sum
    surrender_90 = surrender * exposure_sum
    return lapse_90, surrender_90, lapse_90 + surrender_90


def observable_oracle(
    features: V2Features, *, signal_mode: str, drift_scenario: str
) -> tuple[float, float, float]:
    """Marginalize policy frailty with frozen 32-node Gauss-Hermite quadrature."""

    nodes, weights = np.polynomial.hermite.hermgauss(32)
    totals = np.zeros(3, dtype=float)
    for node, weight in zip(nodes, weights, strict=True):
        frailty = math.sqrt(2.0) * 0.35 * float(node)
        monthly = competing_hazards(
            features, frailty, signal_mode=signal_mode, drift_scenario=drift_scenario
        )
        totals += float(weight) * np.asarray(cumulative_incidence(*monthly[:2]))
    totals /= math.sqrt(math.pi)
    return tuple(float(value) for value in totals)  # type: ignore[return-value]


def generate_v2_corpus(config: V2CorpusConfig) -> V2Corpus:
    """Build deterministic non-final histories, recurring observations, and sidecars."""

    histories: list[tuple[dict[str, Any], ...]] = []
    observations: list[V2Observation] = []
    oracles: list[V2OracleRecord] = []
    run_id = v2_run_identity(config)
    for cohort_index in range(config.cohort_count):
        cohort_start = _add_months(config.issuance_start, cohort_index)
        cohort_name = cohort_start.strftime("%Y-%m")
        for within_cohort in range(config.policies_per_cohort):
            policy_number = cohort_index * config.policies_per_cohort + within_cohort
            policy_id = _identifier("pol", run_id, str(policy_number))
            frequency = V2_BILLING_FREQUENCIES[within_cohort % 4]
            role = _role_for_index(within_cohort)
            product = _PRODUCTS[v2_domain_seed(config, "static_attributes", policy_id) % 2]
            premium = 6000 + int(v2_domain_seed(config, "static_attributes", policy_id, "premium") % 14001)
            frailty_rng = random.Random(v2_domain_seed(config, "frailty", policy_id))
            frailty = frailty_rng.gauss(0.0, config.frailty_standard_deviation)
            event_list: list[dict[str, Any]] = [
                _event(config, policy_id, 0, "policy.issued", cohort_start, {
                    "product_type": product,
                    "billing_frequency": frequency,
                    "premium_amount_cents": premium,
                    "currency": "USD",
                })
            ]
            cutoff = cohort_start + timedelta(days=config.seasoning_days)
            episode_index = 0
            terminal = False
            while cutoff <= config.follow_up_watermark and not terminal:
                features, behavior_events = _episode_features(
                    config, policy_id, cutoff, episode_index, product, frequency, premium
                )
                event_list.extend(behavior_events)
                conditional_monthly = competing_hazards(
                    features,
                    frailty,
                    signal_mode=config.signal_mode,
                    drift_scenario=config.drift_scenario,
                )
                if conditional_monthly[0] + conditional_monthly[1] >= 0.20:
                    raise ValueError(
                        "generated monthly total terminal probability must remain below 0.20"
                    )
                conditional = cumulative_incidence(*conditional_monthly[:2])
                observable = observable_oracle(
                    features,
                    signal_mode=config.signal_mode,
                    drift_scenario=config.drift_scenario,
                )
                obs_id = _identifier("obs", run_id, policy_id, _timestamp(cutoff))
                episode_id = _identifier("epi", run_id, policy_id, _timestamp(cutoff))
                draw = random.Random(
                    v2_domain_seed(config, "terminal_outcome", policy_id, episode_index)
                ).random()
                horizon_end = cutoff + timedelta(days=config.label_horizon_days)
                censor_draw = random.Random(
                    v2_domain_seed(config, "event_censoring", policy_id, episode_index)
                ).random()
                label_status = "observed_negative"
                label_value: int | None = 0
                outcome_type: str | None = None
                censoring_reason: str | None = None
                follow_up = min(horizon_end, config.follow_up_watermark)
                if follow_up < horizon_end:
                    label_status, label_value = "right_censored", None
                    censoring_reason = "administrative_censoring"
                elif censor_draw < config.event_censoring_rate:
                    label_status, label_value = "right_censored", None
                    censoring_reason = "event_driven_censoring"
                    follow_up = cutoff + timedelta(days=45)
                elif draw < conditional[2]:
                    label_status, label_value = "observed_positive", 1
                    outcome_type = "outcome.lapsed" if draw < conditional[0] else "outcome.surrendered"
                    terminal_time = cutoff + timedelta(days=30 + int(draw * 59))
                    event_list.append(_event(
                        config, policy_id, len(event_list), outcome_type, terminal_time,
                        {"cause": outcome_type.removeprefix("outcome.")},
                    ))
                    terminal = True
                visible_ids = tuple(
                    event["event_id"]
                    for event in event_list
                    if event["effective_at"] <= _timestamp(cutoff)
                    and event["ingested_at"] <= _timestamp(cutoff)
                )
                observations.append(V2Observation(
                    observation_contract_version="2.0.0",
                    label_policy_version="2.0.0",
                    observation_id=obs_id,
                    outcome_episode_id=episode_id,
                    policy_id=policy_id,
                    role=role,
                    cohort=cohort_name,
                    as_of=_timestamp(cutoff),
                    horizon_end=_timestamp(horizon_end),
                    follow_up_through=_timestamp(follow_up),
                    features=features,
                    label_status=label_status,
                    label_value=label_value,
                    outcome_type=outcome_type,
                    censoring_reason=censoring_reason,
                    visible_event_ids=visible_ids,
                ))
                validate_v2_feature_payload(features)
                oracles.append(V2OracleRecord(
                    sidecar_version=V2_ORACLE_SIDECAR_VERSION,
                    quadrature_version=V2_QUADRATURE_VERSION,
                    run_identity=run_id,
                    observation_id=obs_id,
                    outcome_episode_id=episode_id,
                    oracle_conditional_lapse=conditional[0],
                    oracle_conditional_surrender=conditional[1],
                    oracle_conditional=conditional[2],
                    oracle_observable_lapse=observable[0],
                    oracle_observable_surrender=observable[1],
                    oracle_observable=observable[2],
                    latent_frailty=frailty,
                    outcome_uniform_draw=draw,
                    signal_mode=config.signal_mode,
                    drift_scenario=config.drift_scenario,
                ))
                cutoff = horizon_end
                episode_index += 1
            histories.append(tuple(sorted(event_list, key=lambda item: (item["effective_at"], item["event_id"]))))
    provenance = {
        "artifact_version": V2_ARTIFACT_VERSION,
        "configuration": canonical_v2_configuration(config),
        "configuration_sha256": v2_configuration_digest(config),
        "run_identity": run_id,
        "history_count": len(histories),
        "observation_count": len(observations),
        "oracle_record_count": len(oracles),
        "final_holdout_status": "not_materialized",
    }
    corpus = V2Corpus(tuple(histories), tuple(observations), tuple(oracles), provenance)
    validate_v2_corpus(corpus, config)
    return corpus


def validate_v2_corpus(corpus: V2Corpus, config: V2CorpusConfig) -> None:
    if len(corpus.histories) != config.policy_count:
        raise ValueError("v2 corpus has an incorrect policy count")
    if len(corpus.observations) != len(corpus.oracle_sidecar):
        raise ValueError("every v2 observation must have one oracle record")
    policy_ids = {history[0]["policy_id"] for history in corpus.histories}
    if len(policy_ids) != config.policy_count:
        raise ValueError("v2 policy identities must be unique")
    observation_ids = [record.observation_id for record in corpus.observations]
    episode_ids = [record.outcome_episode_id for record in corpus.observations]
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("v2 observation identities must be unique")
    if len(episode_ids) != len(set(episode_ids)):
        raise ValueError("v2 outcome episodes must be unique")
    oracle_ids = [record.observation_id for record in corpus.oracle_sidecar]
    if oracle_ids != observation_ids:
        raise ValueError("oracle sidecar must preserve exact observation membership and order")
    for role in _ROLES:
        role_rows = [row for row in corpus.observations if row.role == role]
        if config.policy_count == 3600:
            frequencies = {row.features.billing_frequency for row in role_rows}
            if frequencies != set(V2_BILLING_FREQUENCIES):
                raise ValueError(f"role {role} lacks required billing-frequency coverage")
            positives = sum(row.label_value == 1 for row in role_rows)
            negatives = sum(row.label_value == 0 for row in role_rows)
            censored = sum(row.label_status == "right_censored" for row in role_rows)
            if len(role_rows) < 500 or positives < 50 or negatives < 50:
                raise ValueError(f"role {role} fails minimum observation/outcome counts")
            if censored / len(role_rows) > 0.25:
                raise ValueError(f"role {role} exceeds the censoring limit")


def corpus_jsonl(records: tuple[Any, ...]) -> bytes:
    return ("\n".join(
        json.dumps(record.to_dict() if hasattr(record, "to_dict") else asdict(record),
                   allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        for record in records
    ) + "\n").encode("ascii")


def _episode_features(
    config: V2CorpusConfig,
    policy_id: str,
    cutoff: datetime,
    episode: int,
    product: str,
    frequency: str,
    premium: int,
) -> tuple[V2Features, list[dict[str, Any]]]:
    rng = random.Random(v2_domain_seed(config, "recurring_behavior", policy_id, episode))
    prevalence_shift = 0.0 if config.drift_scenario == "stable" else (0.10 if config.drift_scenario == "moderate_drift" else 0.15)
    failures = int(rng.random() < 0.24 + prevalence_shift) + int(rng.random() < 0.06)
    retries = failures
    recoveries = sum(rng.random() < 0.72 for _ in range(failures))
    missing_rate = config.mcar_missingness_rate * (2.0 if config.drift_scenario == "stress_drift" else 1.0)
    delay = None if rng.random() < missing_rate else round(rng.random() * 18, 3)
    conditional_rate = 0.08 if frequency == "annual" or product == "fictional_whole_life" else 0.02
    missing_contact = rng.random() < min(1.0, missing_rate + conditional_rate)
    arrears = 0 if failures == 0 else int(3 + rng.random() * 28)
    features = V2Features(
        tenure_days=(cutoff - _policy_start_from_id_placeholder(cutoff, episode, config)).days,
        premium_amount_cents=premium,
        product_type=product,
        billing_frequency=frequency,
        due_to_paid_delay_days=delay,
        rolling_on_time_payment_rate=max(0.0, min(1.0, 0.94 - failures * 0.18 + rng.random() * 0.04)),
        recent_failed_payment_count=failures,
        recent_retry_count=retries,
        recent_recovery_count=recoveries,
        arrears_duration_days=arrears,
        recent_notice_count=failures + int(rng.random() < 0.15),
        notice_category="late_category" if cutoff.year >= 2024 and rng.random() < 0.1 else "billing",
        recent_service_contact_count=int(rng.random() < 0.30),
        contact_category="missing" if missing_contact else "billing_question",
        visible_grace_entries=int(failures > 0),
        visible_grace_recoveries=int(recoveries > 0),
        payment_attribute_missing=delay is None,
        contact_attribute_missing=missing_contact,
    )
    event_time = cutoff - timedelta(days=5)
    delay_hours = _ingestion_delay_hours(config, policy_id, episode)
    event = _event(config, policy_id, episode + 1, "behavior.snapshot", event_time, {
        "failed_payment_count": failures,
        "retry_count": retries,
        "recovery_count": recoveries,
        "notice_category": features.notice_category,
        "contact_category": None if missing_contact else features.contact_category,
    }, ingestion_delay=timedelta(hours=delay_hours))
    events = [event]
    if failures:
        events.append(_event(
            config, policy_id, 1000 + episode * 2, "policy.grace_entered",
            event_time + timedelta(hours=1), {"reason": "payment_overdue"}
        ))
        if recoveries:
            events.append(_event(
                config, policy_id, 1001 + episode * 2, "policy.grace_recovered",
                event_time + timedelta(days=2), {"reason": "payment_recovered"}
            ))
    correction_rng = random.Random(v2_domain_seed(config, "correction", policy_id, episode))
    if correction_rng.random() < 0.05:
        events.append(_event(
            config, policy_id, 2000 + episode, "event.corrected",
            event_time + timedelta(days=3),
            {"corrected_event_id": event["event_id"], "correction_type": "category_correction"},
            ingestion_delay=timedelta(days=1),
        ))
    return features, events


def _policy_start_from_id_placeholder(cutoff: datetime, episode: int, config: V2CorpusConfig) -> datetime:
    return cutoff - timedelta(days=config.seasoning_days + episode * config.observation_cadence_days)


def _ingestion_delay_hours(config: V2CorpusConfig, policy_id: str, episode: int) -> float:
    rng = random.Random(v2_domain_seed(config, "ingestion_delay", policy_id, episode))
    draw = rng.random()
    if config.drift_scenario == "stress_drift":
        draw = max(0.0, draw - 0.10)
    if draw < 0.90:
        return rng.random() * 24
    if draw < 0.99:
        return 24 + rng.random() * (7 * 24 - 24)
    return 7 * 24 + rng.random() * (30 * 24 - 7 * 24)


def _role_for_index(index: int) -> str:
    normalized = index % 150
    boundary = 0
    for role, count in zip(_ROLES, _ROLE_COUNTS_PER_150, strict=True):
        boundary += count
        if normalized < boundary:
            return role
    raise AssertionError("unreachable role assignment")


def _event(
    config: V2CorpusConfig,
    policy_id: str,
    index: int,
    event_type: str,
    effective_at: datetime,
    payload: dict[str, Any],
    *,
    ingestion_delay: timedelta = timedelta(0),
) -> dict[str, Any]:
    event_id = _identifier("evt", v2_run_identity(config), policy_id, str(index), event_type)
    ingested_at = effective_at + ingestion_delay
    return {
        "schema_version": V2_EVENT_SCHEMA_VERSION,
        "event_id": event_id,
        "policy_id": policy_id,
        "event_type": event_type,
        "occurred_at": _timestamp(effective_at),
        "effective_at": _timestamp(effective_at),
        "ingested_at": _timestamp(ingested_at),
        "payload": payload,
    }


def _identifier(prefix: str, *parts: str) -> str:
    digest = sha256("\x1f".join((prefix, *parts)).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.year * 12 + value.month - 1 + months
    return value.replace(year=month_index // 12, month=month_index % 12 + 1)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
