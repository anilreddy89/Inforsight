"""Frozen v6 configuration, identities, and random-stream registry for R2-14D."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import hmac
from statistics import NormalDist
from typing import Any

from .v3_config import (
    V3_BILLING_FREQUENCIES, V3_CANONICALIZATION_VERSION, V3_FINAL_HOLDOUT_STATUS,
    V3_RANDOM_DOMAINS, V3_ROLES, V3CorpusConfig, canonical_json_bytes,
    intervention_manifest, scenario_configuration, structural_configuration,
)

V6_SIMULATOR_CONTRACT_VERSION = "6.0.0"
V6_ACCEPTANCE_PROTOCOL_VERSION = "3.0.0"
V6_COEFFICIENT_REGISTRY_VERSION = "3.0.0"
V6_STREAM_REGISTRY_VERSION = "3.0.0"
V6_RANDOM_DOMAINS = {
    **V3_RANDOM_DOMAINS,
    "scheduled_payment_opportunity": ("policy", "due_ordinal"),
}


@dataclass(frozen=True)
class V6CorpusConfig(V3CorpusConfig):
    """Complete authoritative inputs for one non-final v6 artifact."""

    namespace: str = "r2-14d-v6-development-qualification"


def complete_configuration(config: V6CorpusConfig) -> dict[str, Any]:
    _require(config)
    return {
        "acceptance_protocol_version": V6_ACCEPTANCE_PROTOCOL_VERSION,
        "base_seed": config.base_seed,
        "billing_frequencies": list(V3_BILLING_FREQUENCIES),
        "canonicalization_version": V3_CANONICALIZATION_VERSION,
        "coefficient_registry_version": V6_COEFFICIENT_REGISTRY_VERSION,
        "contract_version": V6_SIMULATOR_CONTRACT_VERSION,
        "event_support": {
            "annual": 1, "monthly": 12, "quarterly": 4, "semiannual": 2,
            "missing_or_failed_opportunity_retained": True,
        },
        "final_holdout_status": V3_FINAL_HOLDOUT_STATUS,
        "namespace": config.namespace,
        "random_stream_registry_version": V6_STREAM_REGISTRY_VERSION,
        "scenario": scenario_configuration(config),
        "structural": structural_configuration(config),
    }


@lru_cache(maxsize=64)
def stream_set_id(config: V6CorpusConfig) -> str:
    _require(config)
    return sha256(canonical_json_bytes({
        "base_seed": config.base_seed,
        "namespace": config.namespace,
        "stream_registry_version": V6_STREAM_REGISTRY_VERSION,
        "structural_config": structural_configuration(config),
    })).hexdigest()


@lru_cache(maxsize=64)
def artifact_id(config: V6CorpusConfig) -> str:
    return sha256(canonical_json_bytes({
        "all_contract_versions": {
            "acceptance": V6_ACCEPTANCE_PROTOCOL_VERSION,
            "canonicalization": V3_CANONICALIZATION_VERSION,
            "coefficient_registry": V6_COEFFICIENT_REGISTRY_VERSION,
            "statistical_substrate": V6_SIMULATOR_CONTRACT_VERSION,
            "stream_registry": V6_STREAM_REGISTRY_VERSION,
        },
        "complete_scenario_config": complete_configuration(config),
        "stream_set_id": stream_set_id(config),
    })).hexdigest()


def execution_id(config: V6CorpusConfig, *, source_digest: str,
                 dependency_lock_digest: str, command_digest: str) -> str:
    for name, value in (("source_digest", source_digest),
                        ("dependency_lock_digest", dependency_lock_digest),
                        ("command_digest", command_digest)):
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"{name} must be a SHA-256 hex digest")
        int(value, 16)
    return sha256(canonical_json_bytes({
        "artifact_id": artifact_id(config),
        "canonicalization_version": V3_CANONICALIZATION_VERSION,
        "command_digest": command_digest,
        "dependency_lock_digest": dependency_lock_digest,
        "source_digest": source_digest,
    })).hexdigest()


def primitive_uniform(config: V6CorpusConfig, domain: str, *keys: object) -> float:
    _require(config)
    if domain not in V6_RANDOM_DOMAINS:
        raise ValueError("domain is not in random-stream registry 3.0.0")
    if len(keys) != len(V6_RANDOM_DOMAINS[domain]):
        raise ValueError(f"{domain} requires {len(V6_RANDOM_DOMAINS[domain])} keys")
    message = canonical_json_bytes({"domain": domain, "keys": [str(key) for key in keys]})
    digest = hmac.new(stream_set_id(config).encode("ascii"), message, sha256).digest()
    return (int.from_bytes(digest[:8], "big") + 0.5) / 2**64


def primitive_normal(config: V6CorpusConfig, domain: str, *keys: object) -> float:
    return round(NormalDist().inv_cdf(primitive_uniform(config, domain, *keys)), 12)


def stable_identifier(prefix: str, config: V6CorpusConfig, *keys: object) -> str:
    if not prefix.isalpha():
        raise ValueError("identifier prefix must be alphabetic")
    digest = sha256(canonical_json_bytes({
        "contract_version": V6_SIMULATOR_CONTRACT_VERSION,
        "keys": [str(key) for key in keys], "stream_set_id": stream_set_id(config),
    })).hexdigest()[:24]
    return f"v6-{prefix}-{digest}"


def _require(config: object) -> None:
    if not isinstance(config, V6CorpusConfig):
        raise TypeError("config must be V6CorpusConfig")


__all__ = [
    "V6_ACCEPTANCE_PROTOCOL_VERSION", "V6_COEFFICIENT_REGISTRY_VERSION",
    "V6_RANDOM_DOMAINS", "V6_SIMULATOR_CONTRACT_VERSION",
    "V6_STREAM_REGISTRY_VERSION", "V6CorpusConfig", "artifact_id",
    "canonical_json_bytes", "complete_configuration", "execution_id",
    "intervention_manifest", "primitive_normal", "primitive_uniform",
    "scenario_configuration", "stable_identifier", "stream_set_id",
    "structural_configuration",
]

