"""Versioned v3.1 simulator identities for the R2-10 arrears remediation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .v3_config import (
    V3_ACCEPTANCE_PROTOCOL_VERSION as V3_HISTORICAL_ACCEPTANCE_PROTOCOL_VERSION,
    V3_BILLING_FREQUENCIES, V3_CANONICALIZATION_VERSION, V3_CONTRACT_VERSION,
    V3_FINAL_HOLDOUT_STATUS, V3_RANDOM_DOMAINS, V3_ROLE_COUNTS_PER_600,
    V3_ROLES, V3_STREAM_REGISTRY_VERSION, V3CorpusConfig,
    canonical_json_bytes, intervention_manifest, primitive_normal,
    primitive_uniform, scenario_configuration, stream_set_id,
    stable_identifier as historical_stable_identifier,
    structural_configuration,
)


V31_SIMULATOR_CONTRACT_VERSION = "3.1.0"
V31_ACCEPTANCE_PROTOCOL_VERSION = "2.2.0"


@dataclass(frozen=True)
class V31CorpusConfig(V3CorpusConfig):
    """The remediated simulator retains every frozen structural input."""


def complete_configuration(config: V31CorpusConfig) -> dict[str, Any]:
    return {
        "acceptance_protocol_version": V31_ACCEPTANCE_PROTOCOL_VERSION,
        "base_seed": config.base_seed,
        "billing_frequencies": list(V3_BILLING_FREQUENCIES),
        "canonicalization_version": V3_CANONICALIZATION_VERSION,
        "contract_version": V31_SIMULATOR_CONTRACT_VERSION,
        "final_holdout_status": V3_FINAL_HOLDOUT_STATUS,
        "historical_corpus_protocol_version": V3_HISTORICAL_ACCEPTANCE_PROTOCOL_VERSION,
        "namespace": config.namespace,
        "random_stream_registry_version": V3_STREAM_REGISTRY_VERSION,
        "scenario": scenario_configuration(config),
        "structural": structural_configuration(config),
    }


def artifact_id(config: V31CorpusConfig) -> str:
    material = {
        "all_contract_versions": {
            "acceptance": V31_ACCEPTANCE_PROTOCOL_VERSION,
            "canonicalization": V3_CANONICALIZATION_VERSION,
            "statistical_substrate": V31_SIMULATOR_CONTRACT_VERSION,
            "stream_registry": V3_STREAM_REGISTRY_VERSION,
        },
        "complete_scenario_config": complete_configuration(config),
        "stream_set_id": stream_set_id(config),
    }
    return sha256(canonical_json_bytes(material)).hexdigest()


def execution_id(
    config: V31CorpusConfig, *, source_digest: str,
    dependency_lock_digest: str, command_digest: str,
) -> str:
    for name, value in (
        ("source_digest", source_digest),
        ("dependency_lock_digest", dependency_lock_digest),
        ("command_digest", command_digest),
    ):
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


def stable_identifier(prefix: str, config: V31CorpusConfig, *keys: object) -> str:
    # Preserve policy/event/episode identities so the same primitive keys keep
    # the historical draws. The artifact identity carries the version change.
    return historical_stable_identifier(prefix, config, *keys)


__all__ = [
    "V3_BILLING_FREQUENCIES", "V3_CANONICALIZATION_VERSION",
    "V3_CONTRACT_VERSION", "V3_FINAL_HOLDOUT_STATUS", "V3_RANDOM_DOMAINS",
    "V3_ROLE_COUNTS_PER_600", "V3_ROLES", "V3_STREAM_REGISTRY_VERSION",
    "V31_ACCEPTANCE_PROTOCOL_VERSION", "V31_SIMULATOR_CONTRACT_VERSION",
    "V31CorpusConfig", "artifact_id", "canonical_json_bytes",
    "complete_configuration", "execution_id", "intervention_manifest",
    "primitive_normal", "primitive_uniform", "scenario_configuration",
    "stable_identifier", "stream_set_id", "structural_configuration",
]
