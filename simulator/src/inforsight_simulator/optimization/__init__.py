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
from .solver import ALLOCATOR_ID, ALLOCATOR_VERSION, SPECIALIST_ACTIONS, PortfolioOptimizer
from .strategies import StrategyResult, compare_portfolio_strategies
from .uplift import (
    CHANNEL_EFFICACY_FACTORS,
    classify_uplift_quadrant,
    estimate_treatment_effect,
)
from .utility import evaluate_action_utilities, select_best_unconstrained_action

__all__ = [
    "ActionUtility",
    "ALLOCATOR_ID",
    "ALLOCATOR_VERSION",
    "CHANNEL_EFFICACY_FACTORS",
    "OptimalRecommendation",
    "PolicyValuation",
    "PortfolioAllocation",
    "PortfolioOptimizer",
    "SPECIALIST_ACTIONS",
    "StrategyResult",
    "UpliftQuadrant",
    "classify_uplift_quadrant",
    "compare_portfolio_strategies",
    "estimate_treatment_effect",
    "evaluate_action_utilities",
    "select_best_unconstrained_action",
]
