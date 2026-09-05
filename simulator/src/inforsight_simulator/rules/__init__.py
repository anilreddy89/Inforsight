"""Policy conservation action eligibility rules package.

Under ADR 0002, this package provides a pure, deterministic rules engine that
evaluates allowed actions independently from probabilistic predictive risk models.
"""

from __future__ import annotations

from .engine import (
    EligibilityRulesEngine,
    evaluate_action_eligibility,
    get_standard_action_catalog,
)
from .invariants import (
    evaluate_channel_consent,
    evaluate_contact_cooling_off,
    evaluate_grace_period,
    evaluate_legal_freeze,
    evaluate_policy_viability,
    evaluate_tenure_bounds,
)
from .models import (
    ActionEligibilityResult,
    ConservationActionDefinition,
    EligibleActionSet,
    PolicyContext,
)
from .reasons import (
    DISQUALIFICATION_DESCRIPTIONS,
    DisqualificationReasonCode,
)

__all__ = [
    "ActionEligibilityResult",
    "ConservationActionDefinition",
    "DisqualificationReasonCode",
    "DISQUALIFICATION_DESCRIPTIONS",
    "EligibilityRulesEngine",
    "EligibleActionSet",
    "PolicyContext",
    "evaluate_action_eligibility",
    "evaluate_channel_consent",
    "evaluate_contact_cooling_off",
    "evaluate_grace_period",
    "evaluate_legal_freeze",
    "evaluate_policy_viability",
    "evaluate_tenure_bounds",
    "get_standard_action_catalog",
]

