"""Inforsight's clean-room fictional policy-event simulator."""

from .config import GeneratorConfig
from .generator import generate_policy_histories, generation_provenance
from .serialization import histories_to_jsonl


__version__ = "0.1.0"

__all__ = [
    "GeneratorConfig",
    "generate_policy_histories",
    "generation_provenance",
    "histories_to_jsonl",
    "project_identity",
]


def project_identity() -> dict[str, str]:
    """Return public project metadata used by the scaffold smoke test."""
    return {
        "name": "Inforsight",
        "tagline": "See Risk. Shape Action.",
        "data_policy": "synthetic-only",
    }
