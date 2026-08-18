"""Configuration for deterministic fictional policy-history generation."""

from dataclasses import dataclass
from datetime import datetime, timezone


DEFAULT_SIMULATION_START = datetime(2024, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class GeneratorConfig:
    """Explicit inputs that define a reproducible simulator run."""

    seed: int
    policy_count: int = 100
    simulation_start: datetime = DEFAULT_SIMULATION_START

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")
        if isinstance(self.policy_count, bool) or not isinstance(self.policy_count, int):
            raise TypeError("policy_count must be an integer")
        if self.policy_count <= 0:
            raise ValueError("policy_count must be greater than zero")
        if self.simulation_start.tzinfo is None:
            raise ValueError("simulation_start must be timezone-aware")
        if self.simulation_start.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("simulation_start must use UTC")
