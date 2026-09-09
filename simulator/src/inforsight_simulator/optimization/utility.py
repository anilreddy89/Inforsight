"""Expected economic utility formulation and evaluation.

Computes the net value of each candidate intervention:
    E[ΔU(i, a)] = Tau_a(X_i) * V_policy(i) - c(a)
and enforces the non-negativity rule defaulting to abstain if net utility <= 0.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from inforsight_simulator.economics import USD_MICROS_PER_USD, load_economics_resource_contract

from inforsight_simulator.rules import (
    ConservationActionDefinition,
    EligibleActionSet,
    get_standard_action_catalog,
)

from .models import (
    ActionUtility,
    OptimalRecommendation,
    PolicyValuation,
    UpliftQuadrant,
)
from .uplift import classify_uplift_quadrant, estimate_treatment_effect


_ECONOMICS = load_economics_resource_contract()


def evaluate_action_utilities(
    eligible_set: EligibleActionSet,
    valuation: PolicyValuation,
    lapse_risk_p: float,
    days_past_due: int = 0,
    prior_contact_count: int = 0,
    is_sleeping_dog: bool = False,
    action_catalog: Sequence[ConservationActionDefinition] | None = None,
) -> dict[str, ActionUtility]:
    """Calculate expected economic utility for all catalog actions against an eligible set."""
    catalog = action_catalog if action_catalog is not None else get_standard_action_catalog()
    contract = _ECONOMICS
    annual_premium_cents = int(round(valuation.annual_premium_usd * 100))

    utilities: dict[str, ActionUtility] = {}

    for action in catalog:
        economics = contract.action(action.action_id)
        is_eligible = eligible_set.is_eligible(action.action_type)

        if not is_eligible:
            # Ineligible actions produce zero gross benefit and negative default net utility
            utilities[action.action_type] = ActionUtility(
                action_type=action.action_type,
                is_eligible=False,
                treatment_effect=0.0,
                gross_benefit_usd=0.0,
                direct_cost_usd=action.direct_cost_usd,
                net_utility_usd=-action.direct_cost_usd,
                uplift_quadrant=UpliftQuadrant.SURE_THING,
                action_id=economics.action_id,
                gross_expected_value_usd_micros=0,
                direct_cost_usd_micros=economics.direct_cost_usd_micros,
                net_expected_value_usd_micros=-economics.direct_cost_usd_micros,
                personnel_seconds=economics.personnel_seconds,
            )
            continue

        if action.action_type == "abstain":
            utilities["abstain"] = ActionUtility(
                action_type="abstain",
                is_eligible=True,
                treatment_effect=0.0,
                gross_benefit_usd=0.0,
                direct_cost_usd=0.0,
                net_utility_usd=0.0,
                uplift_quadrant=UpliftQuadrant.SURE_THING,
                action_id=economics.action_id,
            )
            continue

        tau = estimate_treatment_effect(
            action_type=action.action_type,
            lapse_risk_p=lapse_risk_p,
            days_past_due=days_past_due,
            prior_contact_count=prior_contact_count,
            is_sleeping_dog_candidate=is_sleeping_dog,
        )

        calculated = contract.value(
            policy_id=valuation.policy_id,
            snapshot_id=valuation.snapshot_id,
            snapshot_version=valuation.snapshot_version,
            catalog_sha256=(
                contract.catalog.sha256
                if valuation.catalog_sha256 == "legacy-unbound-catalog"
                else valuation.catalog_sha256
            ),
            action=action.action_id,
            effect=tau,
            annual_premium_cents=annual_premium_cents,
        )
        gross_micros = calculated.gross_expected_value_usd_micros
        cost_micros = calculated.direct_cost_usd_micros
        net_micros = calculated.net_expected_value_usd_micros
        assert gross_micros is not None and cost_micros is not None and net_micros is not None
        gross_benefit = gross_micros / USD_MICROS_PER_USD
        direct_cost = cost_micros / USD_MICROS_PER_USD
        net_utility = net_micros / USD_MICROS_PER_USD
        quadrant = classify_uplift_quadrant(lapse_risk_p, tau)

        utilities[action.action_type] = ActionUtility(
            action_type=action.action_type,
            is_eligible=True,
            treatment_effect=tau,
            gross_benefit_usd=gross_benefit,
            direct_cost_usd=direct_cost,
            net_utility_usd=net_utility,
            uplift_quadrant=quadrant,
            action_id=economics.action_id,
            gross_expected_value_usd_micros=gross_micros,
            direct_cost_usd_micros=cost_micros,
            net_expected_value_usd_micros=net_micros,
            personnel_seconds=economics.personnel_seconds,
        )

    return utilities


def select_best_unconstrained_action(
    policy_id: str,
    utilities: Mapping[str, ActionUtility],
) -> OptimalRecommendation:
    """Select the highest net utility action, defaulting to abstain if all net utilities <= 0."""
    eligible_utilities = [u for u in utilities.values() if u.is_eligible]

    if not eligible_utilities:
        return OptimalRecommendation(
            policy_id=policy_id,
            recommended_action="abstain",
            expected_net_utility_usd=0.0,
            uplift_quadrant=UpliftQuadrant.SURE_THING,
            rank_score=0.0,
            action_utilities=dict(utilities),
            authorized_to_act=False,
        )

    # Sort descending by net utility, then by cost ascending
    sorted_candidates = sorted(
        eligible_utilities,
        key=lambda u: (u.net_utility_usd, -u.direct_cost_usd),
        reverse=True,
    )

    best = sorted_candidates[0]

    # Determine dominant uplift quadrant: if any action exhibits sleeping dog, mark as SLEEPING_DOG
    dominant_quadrant = best.uplift_quadrant
    if any(u.uplift_quadrant == UpliftQuadrant.SLEEPING_DOG for u in utilities.values()):
        dominant_quadrant = UpliftQuadrant.SLEEPING_DOG

    # Non-negativity invariant: If highest net utility <= 0, strictly abstain
    if best.net_utility_usd <= 0.0 or best.action_type == "abstain":
        return OptimalRecommendation(
            policy_id=policy_id,
            recommended_action="abstain",
            expected_net_utility_usd=0.0,
            uplift_quadrant=dominant_quadrant,
            rank_score=0.0,
            action_utilities=dict(utilities),
            authorized_to_act=False,
        )

    return OptimalRecommendation(
        policy_id=policy_id,
        recommended_action=best.action_type,
        expected_net_utility_usd=best.net_utility_usd,
        uplift_quadrant=best.uplift_quadrant,
        rank_score=best.net_utility_usd,
        action_utilities=dict(utilities),
        authorized_to_act=False,
    )
