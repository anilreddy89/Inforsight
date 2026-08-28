"""Configuration for deterministic fictional policy-history generation."""

from dataclasses import dataclass
from datetime import datetime, timezone
import re


DEFAULT_SIMULATION_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
RUN_NAMESPACE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class GeneratorConfig:
    """Explicit inputs that define a reproducible simulator run."""

    seed: int
    run_namespace: str
    policy_count: int = 100
    simulation_start: datetime = DEFAULT_SIMULATION_START

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")
        if isinstance(self.policy_count, bool) or not isinstance(self.policy_count, int):
            raise TypeError("policy_count must be an integer")
        if self.policy_count <= 0:
            raise ValueError("policy_count must be greater than zero")
        if not isinstance(self.run_namespace, str):
            raise TypeError("run_namespace must be a string")
        if not RUN_NAMESPACE_PATTERN.fullmatch(self.run_namespace):
            raise ValueError(
                "run_namespace must be 1 to 64 lowercase letters, digits, dots, "
                "underscores, or hyphens and must start with a letter or digit"
            )
        if not isinstance(self.simulation_start, datetime):
            raise TypeError("simulation_start must be a datetime")
        if self.simulation_start.tzinfo is None:
            raise ValueError("simulation_start must be timezone-aware")
        if self.simulation_start.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("simulation_start must use UTC")
        if self.simulation_start.microsecond != 0:
            raise ValueError("simulation_start must use whole-second precision")
