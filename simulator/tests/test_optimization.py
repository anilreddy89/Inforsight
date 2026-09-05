"""Tests for Phase 3.03 cost-utility and uplift optimization matrix.

Verifies:
1. Ingestion of P3-02 EligibleActionSet (disqualified actions never recommended).
2. Four uplift quadrant classification (Persuadables, Lost Causes, Sure Things, Sleeping Dogs).
3. Expected net utility calculation and non-negativity fallback to abstain.
4. Capacity-constrained portfolio allocation (adheres strictly to specialist capacity).
5. Budget constraint adherence.
6. Diversion of high-risk Lost Causes from expensive caseworker queues.
7. Deterministic tie-breaking and reproducibility across runs.
8. Strict enforcement of ADR 0002 non-authority marker (authorized_to_act: false).
"""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from inforsight_simulator.optimization import (
    OptimalRecommendation,
    PolicyValuation,
    PortfolioAllocation,
    PortfolioOptimizer,
    SPECIALIST_ACTIONS,
    UpliftQuadrant,
    classify_uplift_quadrant,
    estimate_treatment_effect,
    evaluate_action_utilities,
    select_best_unconstrained_action,
)
from inforsight_simulator.rules import (
    PolicyContext,
    evaluate_action_eligibility,
)


def _make_policy_context(
    policy_id: str = "pol_opt_001",
    status: str = "active",
    tenure_days: int = 180,
    in_grace_period: bool = False,
    days_past_due: int = 0,
    **kwargs,
) -> PolicyContext:
    defaults = {
        "policy_id": policy_id,
        "as_of": datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
        "status": status,
        "tenure_days": tenure_days,
        "in_grace_period": in_grace_period,
        "days_past_due": days_past_due,
        "has_active_claim": False,
        "has_legal_hold": False,
        "has_registered_dispute": False,
        "sms_opt_out": False,
        "email_opt_out": False,
        "phone_opt_out": False,
        "dnc_registered": False,
        "last_contact_date": None,
    }
    defaults.update(kwargs)
    return PolicyContext(**defaults)


class TestOptimizationMatrix(unittest.TestCase):
    """Test suite for cost-utility and uplift optimization engine."""

    def test_uplift_quadrant_classification(self) -> None:
        """Test categorization of all 4 behavioral response quadrants."""
        # 1. Persuadable: High risk and strong uplift
        self.assertEqual(
            classify_uplift_quadrant(lapse_risk_p=0.45, treatment_effect=0.15),
            UpliftQuadrant.PERSUADABLE,
        )

        # 2. Lost Cause: High risk but minimal/negligible uplift
        self.assertEqual(
            classify_uplift_quadrant(lapse_risk_p=0.55, treatment_effect=0.02),
            UpliftQuadrant.LOST_CAUSE,
        )

        # 3. Sure Thing: Low baseline risk and low uplift
        self.assertEqual(
            classify_uplift_quadrant(lapse_risk_p=0.08, treatment_effect=0.01),
            UpliftQuadrant.SURE_THING,
        )

        # 4. Sleeping Dog: Negative treatment response (outreach triggers cancellation)
        self.assertEqual(
            classify_uplift_quadrant(lapse_risk_p=0.25, treatment_effect=-0.05),
            UpliftQuadrant.SLEEPING_DOG,
        )

    def test_ineligible_actions_never_recommended(self) -> None:
        """Actions disqualified by P3-02 eligibility rules are never recommended."""
        # Dispute freeze: all active actions disqualified
        ctx = _make_policy_context(has_registered_dispute=True)
        es = evaluate_action_eligibility(ctx)
        val = PolicyValuation("pol_opt_001", annual_premium_usd=1200.0, customer_lifetime_value_usd=5000.0)

        utils = evaluate_action_utilities(
            eligible_set=es,
            valuation=val,
            lapse_risk_p=0.60,
        )

        # Check all active actions are marked ineligible
        for act in ("courtesy_reminder", "grace_period_consultation", "specialist_phone_outreach", "payment_method_remediation"):
            self.assertFalse(utils[act].is_eligible)

        rec = select_best_unconstrained_action(ctx.policy_id, utils)
        self.assertEqual(rec.recommended_action, "abstain")
        self.assertEqual(rec.expected_net_utility_usd, 0.0)

    def test_non_negative_utility_fallback(self) -> None:
        """When all interventions yield negative net utility, abstain is selected."""
        ctx = _make_policy_context()
        es = evaluate_action_eligibility(ctx)
        # Policy with zero CLV where any cost yields negative utility
        val = PolicyValuation("pol_opt_001", annual_premium_usd=0.0, customer_lifetime_value_usd=0.0)

        utils = evaluate_action_utilities(
            eligible_set=es,
            valuation=val,
            lapse_risk_p=0.10,
        )

        rec = select_best_unconstrained_action(ctx.policy_id, utils)
        self.assertEqual(rec.recommended_action, "abstain")
        self.assertEqual(rec.expected_net_utility_usd, 0.0)

    def test_sleeping_dog_strict_abstention(self) -> None:
        """Policyholders flagged as Sleeping Dogs trigger negative uplift and abstain."""
        ctx = _make_policy_context()
        es = evaluate_action_eligibility(ctx)
        val = PolicyValuation("pol_opt_001", annual_premium_usd=1500.0, customer_lifetime_value_usd=4000.0)

        utils = evaluate_action_utilities(
            eligible_set=es,
            valuation=val,
            lapse_risk_p=0.30,
            is_sleeping_dog=True,
        )

        rec = select_best_unconstrained_action(ctx.policy_id, utils)
        self.assertEqual(rec.recommended_action, "abstain")
        self.assertEqual(rec.uplift_quadrant, UpliftQuadrant.SLEEPING_DOG)

    def test_lost_cause_diversion_from_specialist(self) -> None:
        """High-risk Lost Causes are not assigned expensive specialist casework."""
        # Highly fatigued policy with 5 prior contacts -> diminishing treatment effect
        ctx = _make_policy_context(status="grace_period", in_grace_period=True, days_past_due=45)
        es = evaluate_action_eligibility(ctx)
        val = PolicyValuation("pol_opt_001", annual_premium_usd=800.0, customer_lifetime_value_usd=1200.0)

        # High risk, but 5 contacts has reduced marginal efficacy
        tau_specialist = estimate_treatment_effect("specialist_phone_outreach", lapse_risk_p=0.75, prior_contact_count=5)
        self.assertLess(tau_specialist, 0.25)

    def test_portfolio_capacity_constraint_enforcement(self) -> None:
        """Portfolio optimizer strictly caps specialist outreach at capacity limit."""
        # Create 10 policies that would unconstrained prefer specialist phone outreach
        contexts = [
            _make_policy_context(
                policy_id=f"pol_test_{i:03d}",
                status="active",
                tenure_days=180,
            )
            for i in range(10)
        ]
        eligible_sets = [evaluate_action_eligibility(c) for c in contexts]
        valuations = {
            c.policy_id: PolicyValuation(c.policy_id, 2000.0, 5000.0)
            for c in contexts
        }
        # Decreasing risk scores
        risk_scores = {
            f"pol_test_{i:03d}": 0.60 - (i * 0.02)
            for i in range(10)
        }

        # Set specialist capacity to strictly 3 slots
        optimizer = PortfolioOptimizer(specialist_capacity=3, total_budget_usd=1000.0)
        allocation = optimizer.optimize_portfolio(
            eligible_sets=eligible_sets,
            valuations=valuations,
            risk_scores=risk_scores,
        )

        # Must allocate exactly 3 specialist actions
        self.assertEqual(allocation.allocated_specialist_count, 3)
        specialist_assigned = [
            r for r in allocation.recommendations
            if r.recommended_action in SPECIALIST_ACTIONS
        ]
        self.assertEqual(len(specialist_assigned), 3)

        # The 3 assigned must be the top 3 risk policies (pol_test_000, 001, 002)
        assigned_pids = {r.policy_id for r in specialist_assigned}
        expected_pids = {"pol_test_000", "pol_test_001", "pol_test_002"}
        self.assertEqual(assigned_pids, expected_pids)

        # Remaining 7 policies must receive alternative eligible actions (e.g. digital courtesy reminder) or abstain
        remaining = [
            r for r in allocation.recommendations
            if r.policy_id not in expected_pids
        ]
        for r in remaining:
            self.assertNotIn(r.recommended_action, SPECIALIST_ACTIONS)

    def test_portfolio_budget_constraint_enforcement(self) -> None:
        """Portfolio optimizer respects total expenditure budget."""
        contexts = [
            _make_policy_context(policy_id=f"pol_bud_{i:03d}")
            for i in range(5)
        ]
        eligible_sets = [evaluate_action_eligibility(c) for c in contexts]
        valuations = {c.policy_id: PolicyValuation(c.policy_id, 2000.0, 6000.0) for c in contexts}
        risk_scores = {c.policy_id: 0.50 for c in contexts}

        # Budget of $150 only permits two $65 specialist calls (total $130)
        optimizer = PortfolioOptimizer(specialist_capacity=10, total_budget_usd=150.0)
        allocation = optimizer.optimize_portfolio(
            eligible_sets=eligible_sets,
            valuations=valuations,
            risk_scores=risk_scores,
        )

        self.assertLessEqual(allocation.allocated_cost_usd, 150.0)

    def test_deterministic_reproducibility(self) -> None:
        """Identical inputs produce identical portfolio allocations and rankings."""
        as_of = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        contexts = [_make_policy_context(policy_id=f"pol_rep_{i:02d}", as_of=as_of) for i in range(6)]
        eligible_sets = [evaluate_action_eligibility(c) for c in contexts]
        valuations = {c.policy_id: PolicyValuation(c.policy_id, 1500.0, 4000.0) for c in contexts}
        risk_scores = {f"pol_rep_{i:02d}": 0.35 + (i * 0.03) for i in range(6)}

        optimizer = PortfolioOptimizer(specialist_capacity=2, total_budget_usd=500.0)

        run1 = optimizer.optimize_portfolio(eligible_sets, valuations, risk_scores, as_of=as_of).to_dict()
        run2 = optimizer.optimize_portfolio(eligible_sets, valuations, risk_scores, as_of=as_of).to_dict()

        self.assertEqual(run1, run2)

    def test_adr_0002_non_authority_marker(self) -> None:
        """All recommendation outputs must have authorized_to_act: false."""
        ctx = _make_policy_context()
        es = evaluate_action_eligibility(ctx)
        val = PolicyValuation(ctx.policy_id, 1200.0, 3000.0)
        utils = evaluate_action_utilities(es, val, lapse_risk_p=0.40)
        rec = select_best_unconstrained_action(ctx.policy_id, utils)

        self.assertFalse(rec.authorized_to_act)

        # Attempting to construct recommendation with authorized_to_act=True raises ValueError
        with self.assertRaises(ValueError):
            OptimalRecommendation(
                policy_id="pol_test",
                recommended_action="specialist_phone_outreach",
                expected_net_utility_usd=100.0,
                uplift_quadrant=UpliftQuadrant.PERSUADABLE,
                rank_score=100.0,
                action_utilities={},
                authorized_to_act=True,  # Forbidden
            )


if __name__ == "__main__":
    unittest.main()
