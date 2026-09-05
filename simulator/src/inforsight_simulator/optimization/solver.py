"""Capacity-constrained portfolio triage and resource solver.

Solves the constrained optimization problem allocating scarce caseworkers
(specialist call capacity) and total expenditure budget to maximize net
preserved portfolio value with deterministic lexicographical tie-breaking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence

from inforsight_simulator.rules import EligibleActionSet

from .models import (
    OptimalRecommendation,
    PolicyValuation,
    PortfolioAllocation,
    UpliftQuadrant,
)
from .utility import evaluate_action_utilities, select_best_unconstrained_action

# High-touch actions that consume human specialist caseworker capacity
SPECIALIST_ACTIONS: set[str] = {
    "specialist_phone_outreach",
    "grace_period_consultation",
}


class PortfolioOptimizer:
    """Solves resource-constrained conservation queue triage."""

    def __init__(
        self,
        specialist_capacity: int = 100,
        total_budget_usd: float = 10_000.0,
    ) -> None:
        self.specialist_capacity = specialist_capacity
        self.total_budget_usd = total_budget_usd

    def optimize_portfolio(
        self,
        eligible_sets: Sequence[EligibleActionSet],
        valuations: Mapping[str, PolicyValuation],
        risk_scores: Mapping[str, float],
        days_past_due_map: Mapping[str, int] | None = None,
        as_of: datetime | None = None,
    ) -> PortfolioAllocation:
        """Allocate interventions across policies subject to capacity and budget constraints.

        Uses greedy knapsack ordering on net marginal return per resource unit with
        deterministic tie-breaking:
            (expected_net_utility DESC, policy_id ASC)
        """
        eval_time = as_of or datetime.now(timezone.utc)
        dpd_map = days_past_due_map or {}

        # 1. Compute unconstrained action utilities for each policy
        candidates_by_policy: dict[str, OptimalRecommendation] = {}
        for es in eligible_sets:
            pid = es.policy_id
            val = valuations.get(
                pid,
                PolicyValuation(
                    policy_id=pid,
                    annual_premium_usd=1200.0,
                    customer_lifetime_value_usd=3000.0,
                ),
            )
            p_risk = risk_scores.get(pid, 0.10)
            dpd = dpd_map.get(pid, 0)

            utils = evaluate_action_utilities(
                eligible_set=es,
                valuation=val,
                lapse_risk_p=p_risk,
                days_past_due=dpd,
            )
            candidates_by_policy[pid] = select_best_unconstrained_action(pid, utils)

        # 2. Separate candidates by whether they consume specialist capacity
        specialist_candidates: list[OptimalRecommendation] = []
        non_specialist_candidates: list[OptimalRecommendation] = []

        for rec in candidates_by_policy.values():
            if rec.recommended_action in SPECIALIST_ACTIONS:
                specialist_candidates.append(rec)
            else:
                non_specialist_candidates.append(rec)

        # 3. Rank specialist candidates deterministically by expected net utility DESC, policy_id ASC
        sorted_specialists = sorted(
            specialist_candidates,
            key=lambda r: (r.expected_net_utility_usd, -ord(r.policy_id[0]) if r.policy_id else 0),
            reverse=True,
        )
        # Sort secondary key policy_id deterministically ASC
        sorted_specialists = sorted(
            specialist_candidates,
            key=lambda r: (-r.expected_net_utility_usd, r.policy_id),
        )

        final_recommendations: list[OptimalRecommendation] = []
        allocated_specialists = 0
        total_allocated_cost = 0.0
        total_portfolio_value = 0.0

        # 4. Allocate specialist slots up to capacity limit and budget
        for rec in sorted_specialists:
            cost = rec.action_utilities[rec.recommended_action].direct_cost_usd
            can_allocate = (
                allocated_specialists < self.specialist_capacity
                and (total_allocated_cost + cost) <= self.total_budget_usd
                and rec.expected_net_utility_usd > 0.0
            )

            if can_allocate:
                allocated_specialists += 1
                total_allocated_cost += cost
                total_portfolio_value += rec.expected_net_utility_usd
                final_recommendations.append(rec)
            else:
                # Capacity exceeded: fallback to best non-specialist eligible action or abstain
                utils = rec.action_utilities
                non_spec_utils = {
                    k: v
                    for k, v in utils.items()
                    if k not in SPECIALIST_ACTIONS and v.is_eligible and v.net_utility_usd > 0
                }
                if non_spec_utils:
                    best_non_spec = max(
                        non_spec_utils.values(),
                        key=lambda u: (u.net_utility_usd, -u.direct_cost_usd),
                    )
                    fallback_cost = best_non_spec.direct_cost_usd
                    if (total_allocated_cost + fallback_cost) <= self.total_budget_usd:
                        total_allocated_cost += fallback_cost
                        total_portfolio_value += best_non_spec.net_utility_usd
                        final_recommendations.append(
                            OptimalRecommendation(
                                policy_id=rec.policy_id,
                                recommended_action=best_non_spec.action_type,
                                expected_net_utility_usd=best_non_spec.net_utility_usd,
                                uplift_quadrant=best_non_spec.uplift_quadrant,
                                rank_score=best_non_spec.net_utility_usd,
                                action_utilities=utils,
                                authorized_to_act=False,
                            )
                        )
                        continue

                # Final fallback: abstain
                final_recommendations.append(
                    OptimalRecommendation(
                        policy_id=rec.policy_id,
                        recommended_action="abstain",
                        expected_net_utility_usd=0.0,
                        uplift_quadrant=rec.uplift_quadrant,
                        rank_score=0.0,
                        action_utilities=utils,
                        authorized_to_act=False,
                    )
                )

        # 5. Allocate non-specialist candidates up to remaining budget
        sorted_non_specialists = sorted(
            non_specialist_candidates,
            key=lambda r: (-r.expected_net_utility_usd, r.policy_id),
        )

        for rec in sorted_non_specialists:
            if rec.recommended_action == "abstain":
                final_recommendations.append(rec)
                continue

            cost = rec.action_utilities[rec.recommended_action].direct_cost_usd
            if (total_allocated_cost + cost) <= self.total_budget_usd and rec.expected_net_utility_usd > 0.0:
                total_allocated_cost += cost
                total_portfolio_value += rec.expected_net_utility_usd
                final_recommendations.append(rec)
            else:
                final_recommendations.append(
                    OptimalRecommendation(
                        policy_id=rec.policy_id,
                        recommended_action="abstain",
                        expected_net_utility_usd=0.0,
                        uplift_quadrant=rec.uplift_quadrant,
                        rank_score=0.0,
                        action_utilities=rec.action_utilities,
                        authorized_to_act=False,
                    )
                )

        # Sort final recommendations by policy_id for deterministic output
        sorted_final = tuple(
            sorted(final_recommendations, key=lambda r: r.policy_id)
        )

        return PortfolioAllocation(
            as_of=eval_time,
            specialist_capacity=self.specialist_capacity,
            allocated_specialist_count=allocated_specialists,
            total_budget_usd=self.total_budget_usd,
            allocated_cost_usd=total_allocated_cost,
            net_portfolio_value_usd=total_portfolio_value,
            recommendations=sorted_final,
        )
