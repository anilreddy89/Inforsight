"""Controlled RH-05 strategy comparison on one immutable portfolio input."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from typing import Mapping, Sequence

from inforsight_simulator.economics import USD_MICROS_PER_USD

from .models import ActionUtility, OptimalRecommendation
from .solver import PortfolioOptimizer


@dataclass(frozen=True)
class StrategyResult:
    strategy_id: str
    comparison_context_sha256: str
    allocation_id: str
    feasible: bool
    selected_count: int
    abstention_count: int
    unavailable_row_count: int
    budget_used_usd_micros: int
    personnel_used_seconds: int
    modeled_expected_net_value_usd_micros: int
    combined_terminations_expected_avoided: float
    selections: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _abstain(utilities: Mapping[str, ActionUtility]) -> ActionUtility:
    choices = [
        utility
        for utility in utilities.values()
        if utility.is_eligible
        and (utility.action_type == "abstain" or utility.action_type.startswith("act_abstain_"))
    ]
    if not choices:
        raise ValueError("INFEASIBLE_SELECTION: comparison occurrence lacks abstain")
    return min(choices, key=lambda item: (item.action_id, item.action_type))


def _is_abstain(utility: ActionUtility) -> bool:
    return utility.action_type == "abstain" or utility.action_type.startswith(
        "act_abstain_"
    )


def _selected(source: OptimalRecommendation, choice: ActionUtility) -> OptimalRecommendation:
    return replace(
        source,
        recommended_action=choice.action_type,
        expected_net_utility_usd=(choice.net_expected_value_usd_micros / USD_MICROS_PER_USD),
        uplift_quadrant=choice.uplift_quadrant,
        rank_score=choice.net_expected_value_usd_micros / USD_MICROS_PER_USD,
        authorized_to_act=False,
    )


def compare_portfolio_strategies(
    recommendations: Sequence[OptimalRecommendation],
    *,
    risk_scores: Mapping[str, float],
    budget_capacity_usd_micros: int,
    personnel_capacity_seconds: int,
    as_of: datetime,
    portfolio_id: str,
) -> tuple[StrategyResult, ...]:
    """Compare the four accepted strategies against identical frozen inputs."""
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
        "recommendations": [item.to_dict() for item in ordered],
    }
    context_sha = _digest(context)

    def greedy(strategy_id: str) -> tuple[OptimalRecommendation, ...]:
        if strategy_id == "non_intervention":
            traversal = ordered
        elif strategy_id == "risk_ranked":
            traversal = tuple(sorted(ordered, key=lambda item: (-risk_scores[item.policy_id], item.policy_id)))
        else:
            traversal = ordered
        remaining_money = budget_capacity_usd_micros
        remaining_seconds = personnel_capacity_seconds
        chosen: dict[str, OptimalRecommendation] = {}
        for rec in traversal:
            abstain = _abstain(rec.action_utilities)
            candidates = [
                item
                for item in rec.action_utilities.values()
                if item.is_eligible
                and item.net_expected_value_usd_micros > 0
                and item.direct_cost_usd_micros <= remaining_money
                and item.personnel_seconds <= remaining_seconds
                and item is not abstain
            ]
            if strategy_id == "non_intervention" or not candidates:
                choice = abstain
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
            chosen[rec.policy_id] = _selected(rec, choice)
        return tuple(chosen[item.policy_id] for item in ordered)

    selections: dict[str, tuple[OptimalRecommendation, ...]] = {
        strategy_id: greedy(strategy_id)
        for strategy_id in ("non_intervention", "operational_rules_only", "risk_ranked")
    }
    engine = PortfolioOptimizer(
        budget_capacity_usd_micros=budget_capacity_usd_micros,
        personnel_capacity_seconds=personnel_capacity_seconds,
        portfolio_id=portfolio_id,
    ).allocate_recommendations(ordered, as_of=as_of)
    selections["allocation_engine"] = engine.recommendations

    results: list[StrategyResult] = []
    for strategy_id in (
        "non_intervention",
        "operational_rules_only",
        "risk_ranked",
        "allocation_engine",
    ):
        selected = selections[strategy_id]
        utilities = [item.action_utilities[item.recommended_action] for item in selected]
        result_selections = tuple((item.policy_id, item.recommended_action) for item in selected)
        results.append(
            StrategyResult(
                strategy_id=strategy_id,
                comparison_context_sha256=context_sha,
                allocation_id=(
                    engine.allocation_id
                    if strategy_id == "allocation_engine"
                    else f"alloc_{_digest([context_sha, strategy_id, result_selections])[:24]}"
                ),
                feasible=True,
                selected_count=sum(not _is_abstain(item) for item in utilities),
                abstention_count=sum(_is_abstain(item) for item in utilities),
                unavailable_row_count=sum(
                    not utility.is_eligible
                    for recommendation in ordered
                    for utility in recommendation.action_utilities.values()
                ),
                budget_used_usd_micros=sum(item.direct_cost_usd_micros for item in utilities),
                personnel_used_seconds=sum(item.personnel_seconds for item in utilities),
                modeled_expected_net_value_usd_micros=sum(
                    item.net_expected_value_usd_micros for item in utilities
                ),
                combined_terminations_expected_avoided=round(
                    sum(item.treatment_effect for item in utilities), 8
                ),
                selections=result_selections,
            )
        )
    return tuple(results)
