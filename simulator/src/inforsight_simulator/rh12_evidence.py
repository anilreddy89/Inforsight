"""RH-12 corrected evidence helpers.

This module builds a single frozen comparison context from the Generation v6
synthetic cohort and exposes the two estimands declared by RH-04:

* fixed-assignment sampling uncertainty; and
* new-portfolio allocation-procedure performance.

The historical Phase 3.08 OPE path remains unchanged.  RH-12 uses this module
so corrected evidence is versioned separately and cannot be mistaken for the
legacy dollar/hour/lapse-only artifact.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

import numpy as np

from inforsight_simulator.counterfactual.models import CounterfactualOutcome
from inforsight_simulator.economics import USD_MICROS_PER_USD, load_economics_resource_contract
from inforsight_simulator.optimization import (
    ActionUtility,
    OptimalRecommendation,
    UpliftQuadrant,
    compare_portfolio_strategies,
)
from inforsight_simulator.optimization.solver import PortfolioOptimizer
from inforsight_simulator.optimization.uplift import classify_uplift_quadrant
from inforsight_simulator.rules import (
    ActionEligibilityResult,
    EligibleActionSet,
    EligibilityRulesEngine,
    PolicyContext,
    get_standard_action_catalog,
)
from inforsight_simulator.v6_corpus import V6Observation


ECONOMICS = load_economics_resource_contract()
STRATEGY_IDS = (
    "non_intervention",
    "operational_rules_only",
    "risk_ranked",
    "allocation_engine",
)
_FREQUENCY_MULTIPLIER = {
    "monthly": 12,
    "quarterly": 4,
    "semiannual": 2,
    "annual": 1,
}


def _is_abstain(utility: ActionUtility) -> bool:
    return utility.action_type == "abstain" or utility.action_type.startswith("act_abstain_")


def annual_premium_cents(observation: V6Observation) -> int:
    """Return the exact annualized premium basis required by RH-04."""

    multiplier = _FREQUENCY_MULTIPLIER.get(observation.features.billing_frequency)
    if multiplier is None:
        raise ValueError("unsupported billing frequency in RH-12 cohort")
    return int(observation.features.premium_amount_cents) * multiplier


def _eligibility_set(
    observation: V6Observation,
    risk_score: float,
    rules_engine: EligibilityRulesEngine,
) -> EligibleActionSet:
    """Reproduce the sealed synthetic evaluation eligibility boundary."""

    features = observation.features
    delay = int(features.recent_delay_days or 0)
    in_grace = delay > 0 and delay <= 30
    as_of = datetime.fromisoformat(observation.as_of.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )
    context = PolicyContext(
        policy_id=observation.policy_id,
        as_of=as_of,
        status="grace_period" if in_grace else "active",
        tenure_days=features.tenure_days,
        in_grace_period=in_grace,
        days_past_due=delay,
        # The sealed fictional cohort explicitly supplies clear-state facts.
        has_active_claim=False,
        has_legal_hold=False,
        has_registered_dispute=False,
        sms_opt_out=False,
        email_opt_out=False,
        phone_opt_out=False,
        dnc_registered=False,
    )
    result = rules_engine.evaluate(context)

    # Match the already-qualified local reference refinements. They are part
    # of the frozen comparison context, not a post-hoc result adjustment.
    if features.recent_failed_payment_count <= 0 and delay == 0:
        updated = dict(result.results)
        if "payment_method_remediation" in updated:
            updated["payment_method_remediation"] = ActionEligibilityResult(
                action_type="payment_method_remediation",
                is_eligible=False,
                disqualification_reasons=("DISQUALIFIED_NO_PAYMENT_FAILURE",),
                disqualification_details=(
                    "Policy has zero payment failures and zero arrears duration.",
                ),
            )
            result = replace(
                result,
                results=updated,
                eligible_actions=tuple(
                    action
                    for action in result.eligible_actions
                    if action != "payment_method_remediation"
                ),
            )

    if risk_score < 0.15 and not in_grace:
        updated = dict(result.results)
        for action in result.eligible_actions:
            if action != "abstain":
                updated[action] = ActionEligibilityResult(
                    action_type=action,
                    is_eligible=False,
                    disqualification_reasons=("SURE_THING_SUPPRESSED",),
                    disqualification_details=(
                        "Low risk customer; allow self-cure.",
                    ),
                )
        result = replace(
            result,
            results=updated,
            eligible_actions=("abstain",),
        )

    return result


def build_recommendations(
    observations: Sequence[V6Observation],
    risk_scores: Mapping[str, float],
    potential_outcomes: Mapping[str, Mapping[str, CounterfactualOutcome]],
) -> list[OptimalRecommendation]:
    """Build RH-05 recommendations from one frozen RH-04 comparison context."""

    if set(risk_scores) != {observation.policy_id for observation in observations}:
        raise ValueError("CONTEXT_MISMATCH: RH-12 risk scores do not match cohort")
    if set(potential_outcomes) != {observation.policy_id for observation in observations}:
        raise ValueError("CONTEXT_MISMATCH: RH-12 outcomes do not match cohort")

    rules_engine = EligibilityRulesEngine()
    catalog = get_standard_action_catalog()
    recommendations: list[OptimalRecommendation] = []

    for observation in observations:
        policy_id = observation.policy_id
        risk_score = float(risk_scores[policy_id])
        outcomes = potential_outcomes[policy_id]
        eligible = _eligibility_set(observation, risk_score, rules_engine)
        premium_cents = annual_premium_cents(observation)
        utilities: dict[str, ActionUtility] = {}

        for action_definition in catalog:
            action_type = action_definition.action_type
            action_economics = ECONOMICS.action(action_type)
            is_eligible = action_type == "abstain" or eligible.is_eligible(action_type)
            if not is_eligible:
                utilities[action_type] = ActionUtility(
                    action_type=action_type,
                    action_id=action_economics.action_id,
                    is_eligible=False,
                    treatment_effect=0.0,
                    gross_benefit_usd=0.0,
                    direct_cost_usd=action_economics.direct_cost_usd,
                    net_utility_usd=-action_economics.direct_cost_usd,
                    uplift_quadrant=UpliftQuadrant.SURE_THING,
                    gross_expected_value_usd_micros=0,
                    direct_cost_usd_micros=action_economics.direct_cost_usd_micros,
                    net_expected_value_usd_micros=-action_economics.direct_cost_usd_micros,
                    personnel_seconds=action_economics.personnel_seconds,
                )
                continue

            if action_type == "abstain":
                utilities[action_type] = ActionUtility(
                    action_type=action_type,
                    action_id=action_economics.action_id,
                    is_eligible=True,
                    treatment_effect=0.0,
                    gross_benefit_usd=0.0,
                    direct_cost_usd=0.0,
                    net_utility_usd=0.0,
                    uplift_quadrant=UpliftQuadrant.SURE_THING,
                )
                continue

            outcome = outcomes[action_type]
            effect = outcome.combined_termination_treatment_effect
            valuation = ECONOMICS.value(
                policy_id=policy_id,
                snapshot_id=f"rh12:{policy_id}",
                snapshot_version=ECONOMICS.catalog.snapshot_version,
                catalog_sha256=ECONOMICS.catalog.sha256,
                action=action_type,
                effect=effect,
                annual_premium_cents=premium_cents,
            )
            assert valuation.gross_expected_value_usd_micros is not None
            assert valuation.net_expected_value_usd_micros is not None
            utilities[action_type] = ActionUtility(
                action_type=action_type,
                action_id=action_economics.action_id,
                is_eligible=True,
                treatment_effect=effect,
                gross_benefit_usd=(
                    valuation.gross_expected_value_usd_micros / USD_MICROS_PER_USD
                ),
                direct_cost_usd=action_economics.direct_cost_usd,
                net_utility_usd=(
                    valuation.net_expected_value_usd_micros / USD_MICROS_PER_USD
                ),
                uplift_quadrant=classify_uplift_quadrant(risk_score, effect),
                gross_expected_value_usd_micros=valuation.gross_expected_value_usd_micros,
                direct_cost_usd_micros=action_economics.direct_cost_usd_micros,
                net_expected_value_usd_micros=valuation.net_expected_value_usd_micros,
                personnel_seconds=action_economics.personnel_seconds,
            )

        abstain = utilities["abstain"]
        recommendations.append(
            OptimalRecommendation(
                policy_id=policy_id,
                recommended_action="abstain",
                expected_net_utility_usd=0.0,
                uplift_quadrant=abstain.uplift_quadrant,
                rank_score=0.0,
                action_utilities=utilities,
                authorized_to_act=False,
            )
        )

    return recommendations


def summarize_strategy(
    *,
    strategy_id: str,
    selections: Sequence[tuple[str, str]],
    recommendations: Mapping[str, OptimalRecommendation],
    potential_outcomes: Mapping[str, Mapping[str, CounterfactualOutcome]],
    comparison_context_sha256: str,
    budget_capacity_usd_micros: int,
    personnel_capacity_seconds: int,
) -> dict[str, Any]:
    """Aggregate corrected metrics without using legacy lapse/ROCS aliases."""

    budget_used = personnel_used = gross_value = direct_cost = net_value = 0
    signed_effect = expected_harm = 0.0
    baseline_combined = selected_combined = 0.0
    non_beneficial_contacts = 0
    selected_count = 0
    ineligible_rows = 0
    source_policy_ids: set[str] = set()

    for occurrence_id, action_type in selections:
        recommendation = recommendations[occurrence_id]
        utility = recommendation.action_utilities[action_type]
        source_policy_id = occurrence_id.split("#", 1)[0]
        source_policy_ids.add(source_policy_id)
        outcome = potential_outcomes[source_policy_id][action_type]
        baseline = potential_outcomes[source_policy_id]["abstain"]
        baseline_combined += baseline.baseline_lapse_prob + baseline.baseline_surrender_prob
        selected_combined += outcome.counterfactual_lapse_prob + outcome.counterfactual_surrender_prob
        budget_used += utility.direct_cost_usd_micros
        personnel_used += utility.personnel_seconds
        gross_value += utility.gross_expected_value_usd_micros
        direct_cost += utility.direct_cost_usd_micros
        net_value += utility.net_expected_value_usd_micros
        signed_effect += utility.treatment_effect
        expected_harm += max(0.0, -utility.treatment_effect)
        if action_type != "abstain":
            selected_count += 1
            if utility.treatment_effect <= 0:
                non_beneficial_contacts += 1

    for recommendation in recommendations.values():
        ineligible_rows += sum(
            1 for utility in recommendation.action_utilities.values() if not utility.is_eligible
        )

    occurrence_count = len(selections)
    abstention_count = occurrence_count - selected_count
    return {
        "strategy_id": strategy_id,
        "comparison_context_sha256": comparison_context_sha256,
        "occurrence_count": occurrence_count,
        "unique_source_policy_count": len(source_policy_ids),
        "selected_count": selected_count,
        "abstention_count": abstention_count,
        "unavailable_action_row_count": ineligible_rows,
        "budget_capacity_usd_micros": budget_capacity_usd_micros,
        "budget_used_usd_micros": budget_used,
        "personnel_capacity_seconds": personnel_capacity_seconds,
        "personnel_used_seconds": personnel_used,
        "capacity_adherent": (
            budget_used <= budget_capacity_usd_micros
            and personnel_used <= personnel_capacity_seconds
        ),
        "modeled_expected_annual_premium_preserved_usd_micros": gross_value,
        "direct_cost_usd_micros": direct_cost,
        "modeled_expected_net_value_usd_micros": net_value,
        "signed_combined_termination_effect_90d": round(signed_effect, 8),
        "expected_harm_90d": round(expected_harm, 8),
        "baseline_combined_termination_probability_90d": round(baseline_combined, 8),
        "selected_combined_termination_probability_90d": round(selected_combined, 8),
        "modeled_recall_at_capacity": round(
            signed_effect / baseline_combined if baseline_combined else 0.0, 8
        ),
        "modeled_unnecessary_contact_count": non_beneficial_contacts,
        "lead_time_days": None,
        "lead_time_status": "not_supported",
        "lead_time_reason": (
            "The current synthetic counterfactual contract provides a 90-day horizon "
            "but no intervention timestamp or event-time attribution contract."
        ),
    }


def _interval(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        "median": round(float(np.median(array)), 8),
        "ci_lower": round(float(np.percentile(array, 2.5)), 8),
        "ci_upper": round(float(np.percentile(array, 97.5)), 8),
    }


def summarize_bootstrap(
    samples: Mapping[str, Mapping[str, Sequence[float]]],
    point_estimates: Mapping[str, Mapping[str, Any]],
    *,
    estimand_id: str,
) -> dict[str, Any]:
    """Render interval summaries for the corrected manifest."""

    output: dict[str, Any] = {"estimand_id": estimand_id, "strategies": {}}
    for strategy_id, metric_samples in samples.items():
        point = dict(point_estimates[strategy_id])
        intervals = {
            metric: _interval(values)
            for metric, values in metric_samples.items()
        }
        output["strategies"][strategy_id] = {
            "point_estimate": point,
            "intervals": intervals,
        }
    return output


def occurrence_recommendations(
    source_recommendations: Mapping[str, OptimalRecommendation],
    source_risk_scores: Mapping[str, float],
    indices: Sequence[int],
    source_ids: Sequence[str],
) -> tuple[list[OptimalRecommendation], dict[str, float], dict[str, str]]:
    """Create duplicate-preserving occurrence identities for one resample."""

    recommendations: list[OptimalRecommendation] = []
    risk_scores: dict[str, float] = {}
    occurrence_to_source: dict[str, str] = {}
    for draw_index, source_index in enumerate(indices):
        source_id = source_ids[int(source_index)]
        occurrence_id = f"{source_id}#{draw_index}"
        recommendations.append(replace(source_recommendations[source_id], policy_id=occurrence_id))
        risk_scores[occurrence_id] = source_risk_scores[source_id]
        occurrence_to_source[occurrence_id] = source_id
    return recommendations, risk_scores, occurrence_to_source


def fast_resampled_strategy_results(
    recommendations: Sequence[OptimalRecommendation],
    *,
    risk_scores: Mapping[str, float],
    budget_capacity_usd_micros: int,
    personnel_capacity_seconds: int,
    as_of: datetime,
    portfolio_id: str,
) -> tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...]:
    """Run the RH-05 four-strategy comparison without repeated large serialization.

    ``compare_portfolio_strategies`` is the public contract-level helper and is
    used for the original comparison context. This equivalent hot path is used
    only for bootstrap replicates, where serializing thousands of full
    recommendations per replicate would dominate the experiment. It preserves
    the comparator's traversal order, positive-net filter, resource checks,
    action tie-breaks, and RH-05 allocator call.
    """

    if as_of.tzinfo is None:
        raise ValueError("CONTEXT_MISMATCH: strategy cutoff must be timezone-aware")
    ordered = tuple(sorted(recommendations, key=lambda item: item.policy_id))
    if set(risk_scores) != {item.policy_id for item in ordered}:
        raise ValueError("CONTEXT_MISMATCH: risk scores must match portfolio membership")
    context = {
        "portfolio_id": portfolio_id,
        "as_of": as_of.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "budget_capacity_usd_micros": budget_capacity_usd_micros,
        "personnel_capacity_seconds": personnel_capacity_seconds,
        "risk_scores": sorted(risk_scores.items()),
        "recommendation_ids": [item.policy_id for item in ordered],
    }
    context_digest = sha256(
        json.dumps(context, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    def abstain(recommendation: OptimalRecommendation) -> ActionUtility:
        choices = [
            utility
            for utility in recommendation.action_utilities.values()
            if utility.is_eligible and _is_abstain(utility)
        ]
        if not choices:
            raise ValueError(
                f"INFEASIBLE_SELECTION: occurrence {recommendation.policy_id!r} lacks abstain"
            )
        return min(choices, key=lambda item: (item.action_id, item.action_type))

    def selected(
        recommendation: OptimalRecommendation, choice: ActionUtility
    ) -> tuple[str, str]:
        return recommendation.policy_id, choice.action_type

    def greedy(strategy_id: str) -> tuple[tuple[str, str], ...]:
        if strategy_id == "non_intervention":
            traversal = ordered
        elif strategy_id == "risk_ranked":
            traversal = tuple(
                sorted(ordered, key=lambda item: (-risk_scores[item.policy_id], item.policy_id))
            )
        else:
            traversal = ordered
        remaining_money = budget_capacity_usd_micros
        remaining_seconds = personnel_capacity_seconds
        chosen: dict[str, tuple[str, str]] = {}
        for recommendation in traversal:
            abstain_choice = abstain(recommendation)
            candidates = [
                utility
                for utility in recommendation.action_utilities.values()
                if utility.is_eligible
                and utility.net_expected_value_usd_micros > 0
                and utility.direct_cost_usd_micros <= remaining_money
                and utility.personnel_seconds <= remaining_seconds
                and utility is not abstain_choice
            ]
            if strategy_id == "non_intervention" or not candidates:
                choice = abstain_choice
            elif strategy_id == "operational_rules_only":
                choice = min(candidates, key=lambda item: (item.action_id, item.action_type))
            else:
                choice = min(
                    candidates,
                    key=lambda item: (
                        -item.net_expected_value_usd_micros,
                        item.action_id,
                        item.action_type,
                    ),
                )
            remaining_money -= choice.direct_cost_usd_micros
            remaining_seconds -= choice.personnel_seconds
            chosen[recommendation.policy_id] = selected(recommendation, choice)
        return tuple(chosen[recommendation.policy_id] for recommendation in ordered)

    selections = {
        strategy_id: greedy(strategy_id)
        for strategy_id in ("non_intervention", "operational_rules_only", "risk_ranked")
    }
    allocation = PortfolioOptimizer(
        budget_capacity_usd_micros=budget_capacity_usd_micros,
        personnel_capacity_seconds=personnel_capacity_seconds,
        portfolio_id=portfolio_id,
    ).allocate_recommendations(ordered, as_of=as_of)
    selections["allocation_engine"] = tuple(
        (recommendation.policy_id, recommendation.recommended_action)
        for recommendation in allocation.recommendations
    )
    return tuple(
        (strategy_id, context_digest, selections[strategy_id])
        for strategy_id in STRATEGY_IDS
    )
