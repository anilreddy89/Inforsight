"""Inforsight's clean-room fictional policy-event simulator."""

from .config import GeneratorConfig
from .generator import generate_policy_histories, generation_provenance
from .leakage import (
    FEATURE_GUARD_VERSION,
    find_exact_deterministic_proxies,
    validate_feature_payload,
    validate_observation_records,
)
from .observations import (
    LABEL_HORIZON_DAYS,
    LABEL_POLICY_VERSION,
    OBSERVATION_CONTRACT_VERSION,
    ObservationFeatures,
    ObservationRecord,
    OutcomeLabel,
    build_first_billing_observations,
    build_observation,
    first_billing_observation_time,
    summarize_observations,
)
from .reconstruction import PolicyState, reconstruct_policy_state
from .serialization import histories_to_jsonl
from .validation import validate_policy_history


__version__ = "0.1.0"

__all__ = [
    "GeneratorConfig",
    "FEATURE_GUARD_VERSION",
    "LABEL_HORIZON_DAYS",
    "LABEL_POLICY_VERSION",
    "OBSERVATION_CONTRACT_VERSION",
    "ObservationFeatures",
    "ObservationRecord",
    "OutcomeLabel",
    "build_first_billing_observations",
    "build_observation",
    "first_billing_observation_time",
    "find_exact_deterministic_proxies",
    "generate_policy_histories",
    "generation_provenance",
    "histories_to_jsonl",
    "PolicyState",
    "project_identity",
    "reconstruct_policy_state",
    "summarize_observations",
    "validate_feature_payload",
    "validate_observation_records",
    "validate_policy_history",
]


def project_identity() -> dict[str, str]:
    """Return public project metadata used by the scaffold smoke test."""
    return {
        "name": "Inforsight",
        "tagline": "See Risk. Shape Action.",
        "data_policy": "synthetic-only",
    }
