"""Triage allocation policies evaluated under Offline Policy Evaluation (OPE).

Implements 5 comparative operational policies:
1. DecisionEnginePolicy: Uplift-ranked, eligibility-constrained knapsack optimization.
2. NaiveMLPolicy: Pure risk-ranked triage (p_hat descending) blind to uplift.
3. HeuristicPolicy: Traditional carrier business rules (grace period / overdue).
4. RandomPolicy: Uniform random outreach within capacity constraints.
5. ControlPolicy: Non-intervention control (do nothing).
"""

from __future__ import annotations

import random
from typing import Mapping, Sequence

from datetime import datetime, timezone
from inforsight_simulator.optimization import (
    PolicyValuation,
    PortfolioOptimizer,
)
from inforsight_simulator.rules import (
    ActionEligibilityResult,
    EligibilityRulesEngine,
    EligibleActionSet,
    PolicyContext,
)
from inforsight_simulator.v6_corpus import V6Features, V6Observation

from .models import (
    CANONICAL_INTERVENTIONS,
    CounterfactualOutcome,
    TriageAssignment,
)

SPECIALIST_ACTIONS: set[str] = {
    "specialist_phone_outreach",
    "grace_period_consultation",
}


def calculate_annual_premium_usd(features: V6Features) -> float:
    """Compute annualized premium from payment amount and billing frequency."""
    multiplier = {
        "monthly": 12,
        "quarterly": 4,
        "semiannual": 2,
        "annual": 1,
    }.get(features.billing_frequency, 12)
    return (features.premium_amount_cents / 100.0) * multiplier


def make_assignment(
    policy_id: str,
    policy_name: str,
    assigned_action: str,
    risk_score: float,
    annual_premium_usd: float,
    outcomes: dict[str, CounterfactualOutcome],
) -> TriageAssignment:
    """Construct a TriageAssignment from potential outcomes and chosen action."""
    params = CANONICAL_INTERVENTIONS[assigned_action]
    outcome = outcomes[assigned_action]
    baseline = outcomes["abstain"]

    p_a = outcome.counterfactual_lapse_prob
    p_0 = baseline.baseline_lapse_prob
    saved_lapse = max(0.0, p_0 - p_a)
    gross_preserved = saved_lapse * annual_premium_usd
    direct_cost = params.direct_cost_usd
    net_preserved = gross_preserved - direct_cost

    return TriageAssignment(
        policy_id=policy_id,
        policy_name=policy_name,
        assigned_action=assigned_action,
        risk_score=risk_score,
        annual_premium_usd=annual_premium_usd,
        direct_cost_usd=direct_cost,
        counterfactual_lapse_prob=p_a,
        expected_saved_lapse=saved_lapse,
        expected_gross_preserved_usd=gross_preserved,
        expected_net_preserved_usd=net_preserved,
        consumes_specialist=params.is_specialist,
        resource_hours=params.resource_hours,
    )


class BaseTriagePolicy:
    """Abstract base for operational triage policies."""

    name: str = "base"

    def allocate(
        self,
        observations: Sequence[V6Observation],
        risk_scores: Mapping[str, float],
        potential_outcomes: Mapping[str, dict[str, CounterfactualOutcome]],
        specialist_capacity_hours: float = 50.0,
        budget_cap_usd: float = 5_000.0,
    ) -> list[TriageAssignment]:
        raise NotImplementedError


class DecisionEnginePolicy(BaseTriagePolicy):
    """The full Inforsight Decision Engine.

    Enforces ADR 0002 deterministic eligibility boundaries and solves the
    constrained knapsack problem maximizing expected net economic utility.
    """

    name = "decision_engine"

    def __init__(self) -> None:
        self.rules_engine = EligibilityRulesEngine()

    def allocate(
        self,
        observations: Sequence[V6Observation],
        risk_scores: Mapping[str, float],
        potential_outcomes: Mapping[str, dict[str, CounterfactualOutcome]],
        specialist_capacity_hours: float = 50.0,
        budget_cap_usd: float = 5_000.0,
    ) -> list[TriageAssignment]:
        # 1. Evaluate deterministic eligibility for each policy
        eligible_sets: list[EligibleActionSet] = []
        valuations: dict[str, PolicyValuation] = {}
        dpd_map: dict[str, int] = {}

        for obs in observations:
            pid = obs.policy_id
            feats = obs.features
            dpd = int(feats.recent_delay_days or 0)
            dpd_map[pid] = dpd

            # Parse observation cutoff timestamp safely
            try:
                as_of_dt = datetime.fromisoformat(obs.as_of.replace("Z", "+00:00"))
            except Exception:
                as_of_dt = datetime.now(timezone.utc)

            in_grace = (dpd > 0 and dpd <= 30)
            status = "grace_period" if in_grace else "active"
            ctx = PolicyContext(
                policy_id=pid,
                as_of=as_of_dt,
                status=status,
                tenure_days=feats.tenure_days,
                in_grace_period=in_grace,
                days_past_due=dpd,
            )
            es = self.rules_engine.evaluate(ctx)

            # Domain refinement 1: Payment method remediation requires active payment failure or arrears
            has_failed = feats.recent_failed_payment_count > 0
            if not has_failed and dpd == 0 and "payment_method_remediation" in es.eligible_actions:
                new_results = dict(es.results)
                new_results["payment_method_remediation"] = ActionEligibilityResult(
                    action_type="payment_method_remediation",
                    is_eligible=False,
                    disqualification_reasons=("DISQUALIFIED_NO_PAYMENT_FAILURE",),
                    disqualification_details=("Policy has zero payment failures and zero arrears duration.",),
                )
                es = EligibleActionSet(
                    policy_id=es.policy_id,
                    as_of=es.as_of,
                    is_frozen=es.is_frozen,
                    freeze_reason=es.freeze_reason,
                    results=new_results,
                    eligible_actions=tuple(a for a in es.eligible_actions if a != "payment_method_remediation"),
                )

            # Domain refinement 2: Sure Things (low risk < 0.15 and not in grace) default to abstain (self-cure)
            p_risk = risk_scores.get(pid, 0.10)
            if p_risk < 0.15 and not in_grace:
                new_results = dict(es.results)
                for act in es.eligible_actions:
                    if act != "abstain":
                        new_results[act] = ActionEligibilityResult(
                            action_type=act,
                            is_eligible=False,
                            disqualification_reasons=("SURE_THING_SUPPRESSED",),
                            disqualification_details=("Low risk customer; allow self-cure.",),
                        )
                es = EligibleActionSet(
                    policy_id=es.policy_id,
                    as_of=es.as_of,
                    is_frozen=es.is_frozen,
                    freeze_reason=es.freeze_reason,
                    results=new_results,
                    eligible_actions=("abstain",),
                )

            eligible_sets.append(es)

            annual_prem = calculate_annual_premium_usd(feats)
            valuations[pid] = PolicyValuation(
                policy_id=pid,
                annual_premium_usd=annual_prem,
                customer_lifetime_value_usd=annual_prem,
            )

        # 2. Capacity: 1 specialist call = 1.0 hr, consultation = 0.5 hr
        # Capacity count approximately equals hours
        capacity_count = int(specialist_capacity_hours)
        optimizer = PortfolioOptimizer(
            specialist_capacity=capacity_count,
            total_budget_usd=budget_cap_usd,
        )

        portfolio_alloc = optimizer.optimize_portfolio(
            eligible_sets=eligible_sets,
            valuations=valuations,
            risk_scores=risk_scores,
            days_past_due_map=dpd_map,
        )

        recs_by_pid = {r.policy_id: r.recommended_action for r in portfolio_alloc.recommendations}

        # 3. Create assignments
        assignments: list[TriageAssignment] = []
        for obs in observations:
            pid = obs.policy_id
            action = recs_by_pid.get(pid, "abstain")
            annual_prem = calculate_annual_premium_usd(obs.features)
            r_score = risk_scores.get(pid, 0.10)
            outcomes = potential_outcomes[pid]

            assignments.append(
                make_assignment(
                    policy_id=pid,
                    policy_name=self.name,
                    assigned_action=action,
                    risk_score=r_score,
                    annual_premium_usd=annual_prem,
                    outcomes=outcomes,
                )
            )

        return assignments


class NaiveMLPolicy(BaseTriagePolicy):
    """Naive ML Risk Triage.

    Ranks policies strictly by predicted lapse probability (risk_score DESC)
    without regard to uplift potential or eligibility constraints.
    Falls into the 'Lost Cause Trap'.
    """

    name = "naive_ml"

    def allocate(
        self,
        observations: Sequence[V6Observation],
        risk_scores: Mapping[str, float],
        potential_outcomes: Mapping[str, dict[str, CounterfactualOutcome]],
        specialist_capacity_hours: float = 50.0,
        budget_cap_usd: float = 5_000.0,
    ) -> list[TriageAssignment]:
        # Rank all observations by risk score DESC
        sorted_obs = sorted(
            observations,
            key=lambda o: (risk_scores.get(o.policy_id, 0.0), o.policy_id),
            reverse=True,
        )

        remaining_spec_hours = specialist_capacity_hours
        remaining_budget = budget_cap_usd
        action_by_pid: dict[str, str] = {}

        for obs in sorted_obs:
            pid = obs.policy_id
            p_risk = risk_scores.get(pid, 0.0)

            # High risk policies: allocate highest touch available
            if p_risk >= 0.35 and remaining_spec_hours >= 1.0 and remaining_budget >= 65.0:
                action_by_pid[pid] = "specialist_phone_outreach"
                remaining_spec_hours -= 1.0
                remaining_budget -= 65.0
            elif p_risk >= 0.25 and remaining_spec_hours >= 0.5 and remaining_budget >= 25.0:
                action_by_pid[pid] = "grace_period_consultation"
                remaining_spec_hours -= 0.5
                remaining_budget -= 25.0
            elif p_risk >= 0.20 and remaining_budget >= 2.50:
                action_by_pid[pid] = "payment_method_remediation"
                remaining_budget -= 2.50
            elif p_risk >= 0.15 and remaining_budget >= 0.50:
                action_by_pid[pid] = "courtesy_reminder"
                remaining_budget -= 0.50
            else:
                action_by_pid[pid] = "abstain"

        # Construct assignments in original cohort order
        assignments: list[TriageAssignment] = []
        for obs in observations:
            pid = obs.policy_id
            action = action_by_pid.get(pid, "abstain")
            annual_prem = calculate_annual_premium_usd(obs.features)
            r_score = risk_scores.get(pid, 0.10)
            outcomes = potential_outcomes[pid]

            assignments.append(
                make_assignment(
                    policy_id=pid,
                    policy_name=self.name,
                    assigned_action=action,
                    risk_score=r_score,
                    annual_premium_usd=annual_prem,
                    outcomes=outcomes,
                )
            )

        return assignments


class HeuristicPolicy(BaseTriagePolicy):
    """Standard Carrier Heuristic Triage.

    Rule-based allocation based on statutory grace period and arrears duration.
    """

    name = "heuristic"

    def allocate(
        self,
        observations: Sequence[V6Observation],
        risk_scores: Mapping[str, float],
        potential_outcomes: Mapping[str, dict[str, CounterfactualOutcome]],
        specialist_capacity_hours: float = 50.0,
        budget_cap_usd: float = 5_000.0,
    ) -> list[TriageAssignment]:
        remaining_spec_hours = specialist_capacity_hours
        remaining_budget = budget_cap_usd
        action_by_pid: dict[str, str] = {}

        # Heuristic sorts by days overdue DESC
        sorted_obs = sorted(
            observations,
            key=lambda o: (o.features.recent_delay_days or 0.0, o.policy_id),
            reverse=True,
        )

        for obs in sorted_obs:
            pid = obs.policy_id
            delay = obs.features.recent_delay_days or 0.0

            # Statutory grace period active: 1 to 30 days overdue
            if delay > 0 and delay <= 30.0:
                if remaining_spec_hours >= 1.0 and remaining_budget >= 65.0:
                    action_by_pid[pid] = "specialist_phone_outreach"
                    remaining_spec_hours -= 1.0
                    remaining_budget -= 65.0
                elif remaining_spec_hours >= 0.5 and remaining_budget >= 25.0:
                    action_by_pid[pid] = "grace_period_consultation"
                    remaining_spec_hours -= 0.5
                    remaining_budget -= 25.0
                elif remaining_budget >= 2.50:
                    action_by_pid[pid] = "payment_method_remediation"
                    remaining_budget -= 2.50
                else:
                    action_by_pid[pid] = "abstain"
            elif delay > 30.0:
                # Deep arrears: payment fix or reminder
                if remaining_budget >= 2.50:
                    action_by_pid[pid] = "payment_method_remediation"
                    remaining_budget -= 2.50
                elif remaining_budget >= 0.50:
                    action_by_pid[pid] = "courtesy_reminder"
                    remaining_budget -= 0.50
                else:
                    action_by_pid[pid] = "abstain"
            elif obs.features.recent_failed_payment_count > 0 and remaining_budget >= 2.50:
                action_by_pid[pid] = "payment_method_remediation"
                remaining_budget -= 2.50
            else:
                action_by_pid[pid] = "abstain"

        assignments: list[TriageAssignment] = []
        for obs in observations:
            pid = obs.policy_id
            action = action_by_pid.get(pid, "abstain")
            annual_prem = calculate_annual_premium_usd(obs.features)
            r_score = risk_scores.get(pid, 0.10)
            outcomes = potential_outcomes[pid]

            assignments.append(
                make_assignment(
                    policy_id=pid,
                    policy_name=self.name,
                    assigned_action=action,
                    risk_score=r_score,
                    annual_premium_usd=annual_prem,
                    outcomes=outcomes,
                )
            )

        return assignments


class RandomPolicy(BaseTriagePolicy):
    """Uniform Random Outreach Baseline.

    Randomly allocates outreach up to specialist and budget capacity.
    """

    name = "random"

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def allocate(
        self,
        observations: Sequence[V6Observation],
        risk_scores: Mapping[str, float],
        potential_outcomes: Mapping[str, dict[str, CounterfactualOutcome]],
        specialist_capacity_hours: float = 50.0,
        budget_cap_usd: float = 5_000.0,
    ) -> list[TriageAssignment]:
        rng = random.Random(self.seed)
        shuffled = list(observations)
        rng.shuffle(shuffled)

        remaining_spec_hours = specialist_capacity_hours
        remaining_budget = budget_cap_usd
        action_by_pid: dict[str, str] = {}

        candidate_actions = [
            "specialist_phone_outreach",
            "grace_period_consultation",
            "payment_method_remediation",
            "courtesy_reminder",
        ]

        for obs in shuffled:
            pid = obs.policy_id
            action = rng.choice(candidate_actions)
            params = CANONICAL_INTERVENTIONS[action]

            if params.is_specialist:
                if remaining_spec_hours >= params.resource_hours and remaining_budget >= params.direct_cost_usd:
                    action_by_pid[pid] = action
                    remaining_spec_hours -= params.resource_hours
                    remaining_budget -= params.direct_cost_usd
                else:
                    action_by_pid[pid] = "abstain"
            else:
                if remaining_budget >= params.direct_cost_usd:
                    action_by_pid[pid] = action
                    remaining_budget -= params.direct_cost_usd
                else:
                    action_by_pid[pid] = "abstain"

        assignments: list[TriageAssignment] = []
        for obs in observations:
            pid = obs.policy_id
            action = action_by_pid.get(pid, "abstain")
            annual_prem = calculate_annual_premium_usd(obs.features)
            r_score = risk_scores.get(pid, 0.10)
            outcomes = potential_outcomes[pid]

            assignments.append(
                make_assignment(
                    policy_id=pid,
                    policy_name=self.name,
                    assigned_action=action,
                    risk_score=r_score,
                    annual_premium_usd=annual_prem,
                    outcomes=outcomes,
                )
            )

        return assignments


class ControlPolicy(BaseTriagePolicy):
    """Non-Intervention Control Baseline.

    Everyone receives abstain. Zero spend.
    """

    name = "control"

    def allocate(
        self,
        observations: Sequence[V6Observation],
        risk_scores: Mapping[str, float],
        potential_outcomes: Mapping[str, dict[str, CounterfactualOutcome]],
        specialist_capacity_hours: float = 50.0,
        budget_cap_usd: float = 5_000.0,
    ) -> list[TriageAssignment]:
        assignments: list[TriageAssignment] = []
        for obs in observations:
            pid = obs.policy_id
            annual_prem = calculate_annual_premium_usd(obs.features)
            r_score = risk_scores.get(pid, 0.10)
            outcomes = potential_outcomes[pid]

            assignments.append(
                make_assignment(
                    policy_id=pid,
                    policy_name=self.name,
                    assigned_action="abstain",
                    risk_score=r_score,
                    annual_premium_usd=annual_prem,
                    outcomes=outcomes,
                )
            )

        return assignments
