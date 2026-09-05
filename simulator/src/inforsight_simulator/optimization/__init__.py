"""Cost-utility and uplift optimization matrix package.

Under ADR 0002, this package provides economic uplift modeling and capacity-constrained
portfolio allocation, producing advisory recommendations for human caseworkers.
"""

from __future__ import annotations

from .models import (
    ActionUtility,
    OptimalRecommendation,
    PolicyValuation,
    PortfolioAllocation,
    UpliftQuadrant,
)
from .solver import SPECIALIST_ACTIONS, PortfolioOptimizer
from .uplift import (
    CHANNEL_EFFICACY_FACTORS,
    classify_uplift_quadrant,
    estimate_treatment_effect,
)
from .utility import evaluate_action_utilities, select_best_unconstrained_action

__all__ = [
    "ActionUtility",
    "CHANNEL_EFFICACY_FACTORS",
    "OptimalRecommendation",
    "PolicyValuation",
    "PortfolioAllocation",
    "PortfolioOptimizer",
    "SPECIALIST_ACTIONS",
    "UpliftQuadrant",
    "classify_uplift_quadrant",
    "estimate_treatment_effect",
    "evaluate_action_utilities",
    "select_best_unconstrained_action",
]
