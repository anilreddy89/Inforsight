"""Frozen configuration and deterministic identity for the v2 modeling corpus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import re
from typing import Any, Literal


V2_SIMULATOR_CONTRACT_VERSION = "2.0.0"
V2_OBSERVATION_CONTRACT_VERSION = "2.0.0"
V2_LABEL_POLICY_VERSION = "2.0.0"
V2_ACCEPTANCE_PROTOCOL_VERSION = "1.0.0"
V2_CONFIGURATION_CANONICALIZATION_VERSION = "1.0.0"
V2_DIGEST_ALGORITHM = "sha256"
V2_FINAL_HOLDOUT_STATUS = "not_materialized"

DEFAULT_V2_ISSUANCE_START = datetime(2022, 1, 1, tzinfo=timezone.utc)
DEFAULT_V2_FOLLOW_UP_WATERMARK = datetime(
    2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc
)
V2_BILLING_FREQUENCIES = ("monthly", "quarterly", "semiannual", "annual")
V2_ROLE_PROPORTIONS = (
    ("fit", 0.50),
    ("selection", 0.10),
    ("calibration", 0.10),
    ("non_final_evaluation", 0.10),
    ("r2_acceptance", 0.20),
)
V2_RANDOM_DOMAINS = (
    "allocation",
    "static_attributes",
    "recurring_behavior",
    "frailty",
    "terminal_outcome",
    "event_censoring",
    "mcar_missingness",
    "conditional_missingness",
    "ingestion_delay",
    "correction",
    "category_arrival",
    "temporal_drift",
)

_NAMESPACE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
DriftScenario = Literal["stable", "moderate_drift", "stress_drift"]
SignalMode = Literal["signal_present", "null_signal"]


@dataclass(frozen=True)
class V2CorpusConfig:
    """Exact authoritative inputs for one non-final v2 corpus."""

    seed: int
    run_namespace: str
    policy_count: int = 3600
    cohort_count: int = 24
    policies_per_cohort: int = 150
    issuance_start: datetime = DEFAULT_V2_ISSUANCE_START
    follow_up_watermark: datetime = DEFAULT_V2_FOLLOW_UP_WATERMARK
    seasoning_days: int = 30
    observation_cadence_days: int = 90
    label_horizon_days: int = 90
    frailty_standard_deviation: float = 0.35
    event_censoring_rate: float = 0.05
    mcar_missingness_rate: float = 0.05
    drift_scenario: DriftScenario = "stable"
    signal_mode: SignalMode = "signal_present"

    def __post_init__(self) -> None:
        _require_integer("seed", self.seed)
        for name in (
            "policy_count",
            "cohort_count",
            "policies_per_cohort",
            "seasoning_days",
            "observation_cadence_days",
            "label_horizon_days",
        ):
            value = getattr(self, name)
            _require_integer(name, value)
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero")

        if self.policy_count != self.cohort_count * self.policies_per_cohort:
            raise ValueError(
                "policy_count must equal cohort_count multiplied by policies_per_cohort"
            )
        if self.observation_cadence_days != self.label_horizon_days:
            raise ValueError(
                "observation_cadence_days must equal label_horizon_days"
            )
        if not isinstance(self.run_namespace, str):
            raise TypeError("run_namespace must be a string")
        if not _NAMESPACE_PATTERN.fullmatch(self.run_namespace):
            raise ValueError("run_namespace has an invalid format")
        _require_utc_seconds("issuance_start", self.issuance_start)
        _require_utc_seconds("follow_up_watermark", self.follow_up_watermark)
        if self.follow_up_watermark <= self.issuance_start:
            raise ValueError("follow_up_watermark must be after issuance_start")
        _require_finite_positive(
            "frailty_standard_deviation", self.frailty_standard_deviation
        )
        _require_probability("event_censoring_rate", self.event_censoring_rate)
        _require_probability("mcar_missingness_rate", self.mcar_missingness_rate)
        if self.drift_scenario not in (
            "stable",
            "moderate_drift",
            "stress_drift",
        ):
            raise ValueError("drift_scenario is unsupported")
        if self.signal_mode not in ("signal_present", "null_signal"):
            raise ValueError("signal_mode is unsupported")


def canonical_v2_configuration(config: V2CorpusConfig) -> dict[str, Any]:
    """Return the complete canonical configuration used for v2 run identity."""

    if not isinstance(config, V2CorpusConfig):
        raise TypeError("config must be a V2CorpusConfig")
    return {
        "acceptance_protocol_version": V2_ACCEPTANCE_PROTOCOL_VERSION,
        "billing_frequencies": list(V2_BILLING_FREQUENCIES),
        "canonicalization_version": V2_CONFIGURATION_CANONICALIZATION_VERSION,
        "cohort_count": config.cohort_count,
        "drift_scenario": config.drift_scenario,
        "event_censoring_rate": config.event_censoring_rate,
        "final_holdout_status": V2_FINAL_HOLDOUT_STATUS,
        "follow_up_watermark": _timestamp(config.follow_up_watermark),
        "frailty_standard_deviation": config.frailty_standard_deviation,
        "issuance_start": _timestamp(config.issuance_start),
        "label_horizon_days": config.label_horizon_days,
        "label_policy_version": V2_LABEL_POLICY_VERSION,
        "mcar_missingness_rate": config.mcar_missingness_rate,
        "observation_cadence_days": config.observation_cadence_days,
        "observation_contract_version": V2_OBSERVATION_CONTRACT_VERSION,
        "policies_per_cohort": config.policies_per_cohort,
        "policy_count": config.policy_count,
        "random_domains": list(V2_RANDOM_DOMAINS),
        "role_proportions": [
            {"role": role, "proportion": proportion}
            for role, proportion in V2_ROLE_PROPORTIONS
        ],
        "run_namespace": config.run_namespace,
        "seasoning_days": config.seasoning_days,
        "seed": config.seed,
        "signal_mode": config.signal_mode,
        "simulator_contract_version": V2_SIMULATOR_CONTRACT_VERSION,
    }


def v2_configuration_digest(config: V2CorpusConfig) -> str:
    """Return the SHA-256 identity of one exact canonical v2 configuration."""

    encoded = json.dumps(
        canonical_v2_configuration(config),
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return sha256(encoded).hexdigest()


def v2_run_identity(config: V2CorpusConfig) -> str:
    """Return a deterministic bounded run identity for v2-owned identifiers."""

    return v2_configuration_digest(config)[:24]


def v2_domain_seed(config: V2CorpusConfig, domain: str, *parts: object) -> int:
    """Derive a stable independent 128-bit seed for an approved random domain."""

    if domain not in V2_RANDOM_DOMAINS:
        raise ValueError("domain is not in the frozen v2 random-domain registry")
    material = json.dumps(
        {
            "domain": domain,
            "parts": [str(part) for part in parts],
            "run_identity": v2_run_identity(config),
        },
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return int.from_bytes(sha256(material).digest()[:16], "big")


def _require_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")


def _require_probability(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and between zero and one")


def _require_finite_positive(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and greater than zero")


def _require_utc_seconds(name: str, value: object) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError(f"{name} must use UTC")
    if value.microsecond != 0:
        raise ValueError(f"{name} must use whole-second precision")


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
