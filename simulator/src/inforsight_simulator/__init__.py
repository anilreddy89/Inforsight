"""Inforsight's clean-room fictional policy-event simulator."""

__version__ = "0.0.0"


def project_identity() -> dict[str, str]:
    """Return public project metadata used by the scaffold smoke test."""
    return {
        "name": "Inforsight",
        "tagline": "See Risk. Shape Action.",
        "data_policy": "synthetic-only",
    }
