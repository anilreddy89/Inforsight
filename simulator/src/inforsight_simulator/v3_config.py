"""Frozen v3 configuration, canonical identities, and random-stream registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import math
from statistics import NormalDist
from typing import Any, Literal
import unicodedata


V3_CONTRACT_VERSION = "3.0.0"
V3_STREAM_REGISTRY_VERSION = "1.0.0"
V3_ACCEPTANCE_PROTOCOL_VERSION = "2.0.0"
V3_CANONICALIZATION_VERSION = "1.0.0"
V3_FINAL_HOLDOUT_STATUS = "not_materialized"
V3_BILLING_FREQUENCIES = ("monthly", "quarterly", "semiannual", "annual")
V3_ROLES = (
    "fit", "selection", "calibration", "non_final_evaluation", "acceptance"
)
V3_ROLE_COUNTS_PER_600 = (300, 60, 60, 60, 120)
V3_RANDOM_DOMAINS = {
    "entity_identity": ("cohort", "ordinal"),
    "role_assignment": ("policy",),
    "static_covariate": ("policy", "field"),
    "lifecycle_timing": ("policy", "event_kind", "ordinal"),
    "behavior_value": ("policy", "event_kind", "ordinal", "field"),
    "ingestion_delay": ("event",),
    "missingness": ("policy_or_event", "field"),
    "correction": ("event", "field"),
    "frailty": ("policy",),
    "outcome_uniform": ("policy", "episode", "month"),
    "label_shuffle": ("seed", "fold", "policy"),
    "bootstrap": ("seed", "fold", "metric", "replicate", "draw"),
    "learning_order": ("seed", "fold", "policy"),
}
V3_SCENARIOS = (
    "stable", "null_signal", "doubled_missingness",
    "unknown_category_arrival", "moderate_drift", "stress_drift",
)
Scenario = Literal[
    "stable", "null_signal", "doubled_missingness",
    "unknown_category_arrival", "moderate_drift", "stress_drift",
]


@dataclass(frozen=True)
class V3CorpusConfig:
    """Complete authoritative inputs for one non-final v3 artifact."""

    base_seed: int = 20261001
    namespace: str = "r2-09-default"
    scenario: Scenario = "stable"
    policy_count: int = 14_400
    cohort_count: int = 24
    policies_per_cohort: int = 600
    issuance_start: datetime = datetime(2022, 1, 1, tzinfo=timezone.utc)
    watermark: datetime = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    seasoning_days: int = 30
    episode_days: int = 90

    def __post_init__(self) -> None:
        for name in ("base_seed", "policy_count", "cohort_count", "policies_per_cohort",
                     "seasoning_days", "episode_days"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if name != "base_seed" and value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.policy_count != self.cohort_count * self.policies_per_cohort:
            raise ValueError("policy_count must equal cohort_count * policies_per_cohort")
        if self.seasoning_days != 30 or self.episode_days != 90:
            raise ValueError("v3 seasoning and episode lengths are frozen")
        if not isinstance(self.namespace, str) or not self.namespace:
            raise TypeError("namespace must be a non-empty string")
        if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in self.namespace):
            raise ValueError("namespace has an invalid format")
        if self.scenario not in V3_SCENARIOS:
            raise ValueError("unsupported v3 scenario")
        for name in ("issuance_start", "watermark"):
            value = getattr(self, name)
            if not isinstance(value, datetime):
                raise TypeError(f"{name} must be a datetime")
            if value.utcoffset() != timezone.utc.utcoffset(None) or value.microsecond:
                raise ValueError(f"{name} must be whole-second UTC")
        if self.watermark <= self.issuance_start:
            raise ValueError("watermark must follow issuance_start")


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def structural_configuration(config: V3CorpusConfig) -> dict[str, Any]:
    """Return scenario-invariant fields that own the matched stream set."""

    _require_config(config)
    counts = [int(config.policies_per_cohort * value) for value in (0.50, 0.10, 0.10, 0.10, 0.20)]
    counts[0] += config.policies_per_cohort - sum(counts)
    return {
        "cohort_count": config.cohort_count,
        "episode_days": config.episode_days,
        "issuance_start": _timestamp(config.issuance_start),
        "policies_per_cohort": config.policies_per_cohort,
        "policy_count": config.policy_count,
        "role_counts_per_cohort": dict(zip(V3_ROLES, counts, strict=True)),
        "seasoning_days": config.seasoning_days,
        "watermark": _timestamp(config.watermark),
    }


def scenario_configuration(config: V3CorpusConfig) -> dict[str, Any]:
    settings: dict[str, Any] = {
        "baseline_log_odds_shift": "0.00", "category_arrival": False,
        "delay_mixture": ["0.90", "0.09", "0.01"],
        "mcar_threshold": "0.05", "prevalence_shift": "0.00", "signal_scale": "1.00",
    }
    if config.scenario == "null_signal":
        settings["signal_scale"] = "0.00"
    elif config.scenario == "doubled_missingness":
        settings["mcar_threshold"] = "0.10"
    elif config.scenario == "unknown_category_arrival":
        settings["category_arrival"] = True
    elif config.scenario == "moderate_drift":
        settings.update(baseline_log_odds_shift="0.20", prevalence_shift="0.15")
    elif config.scenario == "stress_drift":
        settings.update(baseline_log_odds_shift="0.50", mcar_threshold="0.10",
                        delay_mixture=["0.80", "0.15", "0.05"])
    return {"name": config.scenario, "settings": settings}


def complete_configuration(config: V3CorpusConfig) -> dict[str, Any]:
    return {
        "acceptance_protocol_version": V3_ACCEPTANCE_PROTOCOL_VERSION,
        "base_seed": config.base_seed,
        "billing_frequencies": list(V3_BILLING_FREQUENCIES),
        "canonicalization_version": V3_CANONICALIZATION_VERSION,
        "contract_version": V3_CONTRACT_VERSION,
        "final_holdout_status": V3_FINAL_HOLDOUT_STATUS,
        "namespace": config.namespace,
        "random_stream_registry_version": V3_STREAM_REGISTRY_VERSION,
        "scenario": scenario_configuration(config),
        "structural": structural_configuration(config),
    }


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize finite JSON with normalized strings and a trailing newline."""

    normalized = _normalize(value)
    return (json.dumps(normalized, ensure_ascii=False, allow_nan=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def stream_set_id(config: V3CorpusConfig) -> str:
    material = {
        "base_seed": config.base_seed, "namespace": config.namespace,
        "stream_registry_version": V3_STREAM_REGISTRY_VERSION,
        "structural_config": structural_configuration(config),
    }
    return sha256(canonical_json_bytes(material)).hexdigest()


def artifact_id(config: V3CorpusConfig) -> str:
    material = {
        "all_contract_versions": {
            "acceptance": V3_ACCEPTANCE_PROTOCOL_VERSION,
            "canonicalization": V3_CANONICALIZATION_VERSION,
            "statistical_substrate": V3_CONTRACT_VERSION,
            "stream_registry": V3_STREAM_REGISTRY_VERSION,
        },
        "complete_scenario_config": complete_configuration(config),
        "stream_set_id": stream_set_id(config),
    }
    return sha256(canonical_json_bytes(material)).hexdigest()


def execution_id(config: V3CorpusConfig, *, source_digest: str,
                 dependency_lock_digest: str, command_digest: str) -> str:
    for name, value in (("source_digest", source_digest),
                        ("dependency_lock_digest", dependency_lock_digest),
                        ("command_digest", command_digest)):
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"{name} must be a SHA-256 hex digest")
        int(value, 16)
    material = {
        "artifact_id": artifact_id(config),
        "canonicalization_version": V3_CANONICALIZATION_VERSION,
        "command_digest": command_digest,
        "dependency_lock_digest": dependency_lock_digest,
        "source_digest": source_digest,
    }
    return sha256(canonical_json_bytes(material)).hexdigest()


def primitive_uniform(config: V3CorpusConfig, domain: str, *keys: object) -> float:
    """Return the registry's deterministic open-interval primitive uniform."""

    if domain not in V3_RANDOM_DOMAINS:
        raise ValueError("domain is not in random-stream registry 1.0.0")
    expected = len(V3_RANDOM_DOMAINS[domain])
    if len(keys) != expected:
        raise ValueError(f"{domain} requires {expected} keys")
    message = canonical_json_bytes({"domain": domain, "keys": [str(key) for key in keys]})
    digest = hmac.new(stream_set_id(config).encode("ascii"), message, sha256).digest()
    integer = int.from_bytes(digest[:8], "big")
    return (integer + 0.5) / 2**64


def primitive_normal(config: V3CorpusConfig, domain: str, *keys: object) -> float:
    # Python 3.11 and 3.12 may differ below portable artifact precision in the
    # stdlib inverse-CDF implementation. Contract 3.0.0 therefore freezes the
    # transform at twelve decimal places before it can affect generated state.
    return round(NormalDist().inv_cdf(primitive_uniform(config, domain, *keys)), 12)


def stable_identifier(prefix: str, config: V3CorpusConfig, *keys: object) -> str:
    if not prefix.isalpha():
        raise ValueError("identifier prefix must be alphabetic")
    digest = sha256(canonical_json_bytes({
        "contract_version": V3_CONTRACT_VERSION, "keys": [str(key) for key in keys],
        "stream_set_id": stream_set_id(config),
    })).hexdigest()[:24]
    return f"v3-{prefix}-{digest}"


def intervention_manifest(config: V3CorpusConfig) -> dict[str, Any]:
    owned = {
        "stable": [], "null_signal": ["signal_scale"],
        "doubled_missingness": ["mcar_threshold"],
        "unknown_category_arrival": ["category_arrival"],
        "moderate_drift": ["baseline_log_odds_shift", "prevalence_shift"],
        "stress_drift": ["baseline_log_odds_shift", "mcar_threshold", "delay_mixture"],
    }
    return {"scenario": config.scenario, "owned_transforms": owned[config.scenario]}


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, datetime):
        if value.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("canonical timestamps must use UTC")
        return _timestamp(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON forbids non-finite values")
        return value
    if isinstance(value, dict):
        return {_normalize(str(key)): _normalize(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(nested) for nested in value]
    if value is None or isinstance(value, (bool, int)):
        return value
    if hasattr(value, "__dataclass_fields__"):
        return _normalize(asdict(value))
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def _require_config(config: object) -> None:
    if not isinstance(config, V3CorpusConfig):
        raise TypeError("config must be V3CorpusConfig")
