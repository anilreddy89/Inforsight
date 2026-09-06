"""Counterfactual hazard modulation and bounded potential outcome calculations.

Extends the Generation v6 bounded sigmoid hazard link substrate to evaluate
counterfactual outcomes under conservation interventions with heterogeneous
treatment effects.
"""

from __future__ import annotations

import math
from typing import Any
import numpy as np

from inforsight_simulator.v6_corpus import (
    _MONTH_OFFSETS,
    _ORDERED_LAPSE_COEFFS,
    _ORDERED_SURRENDER_COEFFS,
    _QUADRATURE_NODES,
    _QUADRATURE_WEIGHTS,
    _sigmoid,
    public_mechanism_terms,
    V6_LAPSE_COEFFICIENTS,
    V6_SURRENDER_COEFFICIENTS,
    V6Features,
)

from .models import CANONICAL_INTERVENTIONS

_MONTH_DECAY: tuple[float, float, float] = (1.00, 0.65, 0.40)


def compute_action_logit_shift(
    action_type: str,
    features: V6Features,
    month: int,
    *,
    is_sleeping_dog: bool = False,
) -> float:
    """Calculate the action-specific logit shift gamma_a(X_i, t).

    Args:
        action_type: Canonical action name.
        features: Pre-cutoff observable policy features.
        month: Follow-up month in {1, 2, 3}.
        is_sleeping_dog: Whether the policyholder exhibits negative reaction to contact.

    Returns:
        Logit shift in R. Negative values reduce lapse hazard; positive increase it.
    """
    if action_type == "abstain":
        return 0.0

    if month not in (1, 2, 3):
        raise ValueError("month must be 1, 2, or 3")

    if is_sleeping_dog:
        # Sleeping dog mechanism: outreach irritates the customer and accelerates lapse
        return 0.40 * _MONTH_DECAY[month - 1]

    params = CANONICAL_INTERVENTIONS.get(action_type)
    if params is None:
        raise ValueError(f"Unknown action_type: {action_type}")

    base_shift = params.base_shift

    # 1. Tenure modifier: longer-tenured policyholders have higher loyalty and responsiveness
    # m_tenure in [0.80, 1.20]
    tenure_years = features.tenure_days / 365.0
    m_tenure = 0.80 + 0.10 * min(max(tenure_years, 0.0), 4.0)

    # 2. Payment failure recency modifier
    m_recency = 1.0
    if action_type == "payment_method_remediation":
        delay = features.recent_delay_days or 0.0
        has_payment_issue = (
            delay > 0.0
            or features.recent_failed_payment_count > 0
            or features.arrears_duration_days > 0
        )
        if not has_payment_issue:
            # Fixing payment method has zero benefit if payment is not failing or delayed
            return 0.0

        if delay <= 15.0:
            m_recency = 1.15
        elif delay <= 30.0:
            m_recency = 1.00
        elif delay <= 60.0:
            m_recency = 0.60
        else:
            m_recency = 0.25

    # 3. Contact fatigue multiplier: repeated contacts diminish receptivity
    # m_fatigue in [0.20, 1.00]
    contacts = features.recent_contact_count
    m_fatigue = max(0.20, 1.0 - 0.25 * contacts)

    # 4. Temporal effect decay across the 90-day horizon
    delta_decay = _MONTH_DECAY[month - 1]

    return base_shift * m_tenure * m_recency * m_fatigue * delta_decay


def counterfactual_competing_hazards(
    features: V6Features,
    frailty: float,
    month: int,
    action_type: str,
    *,
    signal_scale: float = 1.0,
    drift: float = 0.0,
    is_sleeping_dog: bool = False,
    enforce_hazard_bound: bool = True,
) -> tuple[float, float, float]:
    """Evaluate monthly competing hazards under a specific counterfactual intervention.

    Guarantees the Generation v6 bounded sigmoid hazard link invariant:
        lambda_a(t) + lambda_surr(t) <= 0.1500 < 0.2000

    Returns:
        (lapse_hazard, surrender_hazard, continuation_prob)
    """
    if month not in (1, 2, 3):
        raise ValueError("month must be 1, 2, or 3")
    if not all(math.isfinite(v) for v in (frailty, signal_scale, drift)):
        raise ValueError("hazard inputs must be finite")

    z = public_mechanism_terms(features)
    lapse_score = (sum(V6_LAPSE_COEFFICIENTS[name] * z[name] for name in z) - 0.21) * 6.0
    surrender_score = (sum(V6_SURRENDER_COEFFICIENTS[name] * z[name] for name in z) - 0.20) * 6.0

    offset = _MONTH_OFFSETS[month - 1]
    gamma = compute_action_logit_shift(action_type, features, month, is_sleeping_dog=is_sleeping_dog)

    z_lapse = -2.20 + offset + frailty + signal_scale * lapse_score + drift + gamma
    z_surrender = -2.80 + offset + 0.50 * frailty + signal_scale * surrender_score + drift

    lapse_h = 0.10 * _sigmoid(z_lapse)
    surrender_h = 0.05 * _sigmoid(z_surrender)
    total_h = lapse_h + surrender_h
    continuation = 1.0 - total_h

    if enforce_hazard_bound and total_h >= 0.20:
        raise ValueError(f"total terminal hazard {total_h:.4f} must remain below 0.20")

    return lapse_h, surrender_h, continuation


def counterfactual_cumulative_incidence(
    features: V6Features,
    frailty: float,
    action_type: str,
    *,
    signal_scale: float = 1.0,
    drift: float = 0.0,
    is_sleeping_dog: bool = False,
    enforce_hazard_bound: bool = True,
) -> tuple[float, float, float, tuple[float, float, float], tuple[float, float, float]]:
    """Compute 90-day cumulative incidence given policy features and latent frailty.

    Returns:
        (cumulative_lapse, cumulative_surrender, cumulative_union, monthly_lapse, monthly_surrender)
    """
    survival, lapse, surrender = 1.0, 0.0, 0.0
    monthly_lapse: list[float] = []
    monthly_surrender: list[float] = []

    for month in (1, 2, 3):
        l_h, s_h, cont = counterfactual_competing_hazards(
            features,
            frailty,
            month,
            action_type,
            signal_scale=signal_scale,
            drift=drift,
            is_sleeping_dog=is_sleeping_dog,
            enforce_hazard_bound=enforce_hazard_bound,
        )
        monthly_lapse.append(l_h)
        monthly_surrender.append(s_h)
        lapse += survival * l_h
        surrender += survival * s_h
        survival *= cont

    return (
        lapse,
        surrender,
        lapse + surrender,
        (monthly_lapse[0], monthly_lapse[1], monthly_lapse[2]),
        (monthly_surrender[0], monthly_surrender[1], monthly_surrender[2]),
    )


def counterfactual_observable_incidence(
    features: V6Features,
    action_type: str,
    *,
    signal_scale: float = 1.0,
    drift: float = 0.0,
    is_sleeping_dog: bool = False,
) -> tuple[float, float, float]:
    """Integrate counterfactual incidence over latent frailty via 32-node Gauss-Hermite quadrature.

    Used when individual latent frailty is not available or for population expectation:
        E_frailty[P_a(lapse | X_i)]

    Returns:
        (expected_lapse, expected_surrender, expected_union)
    """
    nodes, weights = _QUADRATURE_NODES, _QUADRATURE_WEIGHTS
    z = public_mechanism_terms(features)
    values = np.fromiter(z.values(), dtype=float)
    lapse_score = (float(np.dot(_ORDERED_LAPSE_COEFFS, values)) - 0.21) * 6.0
    surrender_score = (float(np.dot(_ORDERED_SURRENDER_COEFFS, values)) - 0.20) * 6.0

    frailty = math.sqrt(2) * 0.20 * nodes
    survival = np.ones(32, dtype=float)
    lapse_total = np.zeros(32, dtype=float)
    surrender_total = np.zeros(32, dtype=float)

    for idx, offset in enumerate(_MONTH_OFFSETS):
        month = idx + 1
        gamma = compute_action_logit_shift(
            action_type, features, month, is_sleeping_dog=is_sleeping_dog
        )
        z_l = -2.20 + offset + frailty + signal_scale * lapse_score + drift + gamma
        z_s = -2.80 + offset + 0.50 * frailty + signal_scale * surrender_score + drift

        clipped_l = np.clip(z_l, -15.0, 15.0)
        clipped_s = np.clip(z_s, -15.0, 15.0)
        lapse_h = 0.10 / (1.0 + np.exp(-clipped_l))
        surrender_h = 0.05 / (1.0 + np.exp(-clipped_s))
        total_h = lapse_h + surrender_h

        lapse_total += survival * lapse_h
        surrender_total += survival * surrender_h
        survival *= (1.0 - total_h)

    totals = (
        np.asarray((
            np.dot(weights, lapse_total),
            np.dot(weights, surrender_total),
            np.dot(weights, lapse_total + surrender_total),
        ))
        / math.sqrt(math.pi)
    )
    return tuple(round(float(val), 12) for val in totals)  # type: ignore[return-value]
