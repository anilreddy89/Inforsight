"""Inforsight's clean-room fictional policy-event simulator."""

from .config import GeneratorConfig
from .generator import generate_policy_histories, generation_provenance
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
    "LABEL_HORIZON_DAYS",
    "LABEL_POLICY_VERSION",
    "OBSERVATION_CONTRACT_VERSION",
    "ObservationFeatures",
    "ObservationRecord",
    "OutcomeLabel",
    "build_first_billing_observations",
    "build_observation",
    "first_billing_observation_time",
    "generate_policy_histories",
    "generation_provenance",
    "histories_to_jsonl",
    "PolicyState",
    "project_identity",
    "reconstruct_policy_state",
    "summarize_observations",
    "validate_policy_history",
]


def project_identity() -> dict[str, str]:
    """Return public project metadata used by the scaffold smoke test."""
    return {
        "name": "Inforsight",
        "tagline": "See Risk. Shape Action.",
        "data_policy": "synthetic-only",
    }
