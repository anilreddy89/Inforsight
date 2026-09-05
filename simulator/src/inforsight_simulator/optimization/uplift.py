"""Treatment effect estimation and uplift quadrant classification.

This module models customer behavioral responsiveness across conservation channels
and partitions policyholders into four canonical uplift quadrants.
"""

from __future__ import annotations

from .models import UpliftQuadrant

# Channel base efficacy parameters (proportional reduction in lapse probability)
CHANNEL_EFFICACY_FACTORS: dict[str, float] = {
    "abstain": 0.00,
    "courtesy_reminder": 0.15,          # 15% relative risk reduction for digital reminder
    "payment_method_remediation": 0.40, # 40% relative risk reduction for payment fix
    "grace_period_consultation": 0.50,  # 50% relative risk reduction for structured call
    "specialist_phone_outreach": 0.65,  # 65% relative risk reduction for senior specialist
}


def estimate_treatment_effect(
    action_type: str,
    lapse_risk_p: float,
    days_past_due: int = 0,
    prior_contact_count: int = 0,
    is_sleeping_dog_candidate: bool = False,
) -> float:
    """Estimate absolute treatment effect Tau_a(X) = P(lapse|control) - P(lapse|action).

    Args:
        action_type: Name of the action from conservation taxonomy.
        lapse_risk_p: Baseline calibrated lapse probability in [0, 1].
        days_past_due: Number of days premium is overdue.
        prior_contact_count: Previous outreach attempts (fatigue discount).
        is_sleeping_dog_candidate: Flag indicating customer hostility to outreach.

    Returns:
        Estimated absolute risk reduction in [-1.0, 1.0].
    """
    if action_type == "abstain":
        return 0.0

    # If customer is irritated by outreach, intervention accelerates lapse
    if is_sleeping_dog_candidate:
        return -0.10

    base_efficacy = CHANNEL_EFFICACY_FACTORS.get(action_type, 0.10)

    # Fatigue discount: repeated touches diminish in effectiveness
    fatigue_multiplier = max(0.20, 1.0 - (0.25 * prior_contact_count))

    # Payment remediation is most potent when payment failure is recent (<= 30 days)
    recency_multiplier = 1.0
    if action_type == "payment_method_remediation":
        if days_past_due > 60:
            recency_multiplier = 0.30
        elif days_past_due > 30:
            recency_multiplier = 0.70

    # Specialist outreach is most potent during grace period and high risk
    grace_multiplier = 1.0
    if action_type in ("specialist_phone_outreach", "grace_period_consultation"):
        if days_past_due > 0:
            grace_multiplier = 1.15

    # Absolute treatment uplift: Tau = p_baseline * relative_efficacy
    relative_reduction = min(
        0.85,
        base_efficacy * fatigue_multiplier * recency_multiplier * grace_multiplier,
    )
    tau = lapse_risk_p * relative_reduction
    return max(0.0, min(1.0, tau))


def classify_uplift_quadrant(
    lapse_risk_p: float,
    treatment_effect: float,
) -> UpliftQuadrant:
    """Classify a policyholder into one of the 4 canonical uplift quadrants.

    - PERSUADABLE: High risk (>= 0.30) and high uplift (>= 0.05).
    - LOST_CAUSE: High risk (>= 0.35) and low uplift (< 0.04).
    - SURE_THING: Low risk (< 0.20) and low uplift (<= 0.03).
    - SLEEPING_DOG: Negative uplift (< 0.0).
    """
    if treatment_effect < 0.0:
        return UpliftQuadrant.SLEEPING_DOG

    if lapse_risk_p < 0.20 and treatment_effect <= 0.03:
        return UpliftQuadrant.SURE_THING

    if lapse_risk_p >= 0.35 and treatment_effect < 0.04:
        return UpliftQuadrant.LOST_CAUSE

    if lapse_risk_p >= 0.30 and treatment_effect >= 0.05:
        return UpliftQuadrant.PERSUADABLE

    # Default intermediate: if moderate risk and positive uplift, consider Persuadable
    if treatment_effect > 0.03:
        return UpliftQuadrant.PERSUADABLE

    return UpliftQuadrant.SURE_THING
