"""Deterministic RH-05 multiple-choice, two-resource portfolio allocation."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from typing import Mapping, Sequence

from inforsight_simulator.economics import USD_MICROS_PER_USD
from inforsight_simulator.rules import EligibleActionSet

from .models import ActionUtility, OptimalRecommendation, PolicyValuation, PortfolioAllocation
from .utility import evaluate_action_utilities

ALLOCATOR_ID = "inforsight.portfolio-allocation"
ALLOCATOR_VERSION = "1.0.0"

# Compatibility export only. Personnel seconds, not membership in this set, are
# authoritative under RH-05.
SPECIALIST_ACTIONS: set[str] = {
    "specialist_phone_outreach",
    "grace_period_consultation",
}


def _canonical_digest(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _selected_recommendation(
    source: OptimalRecommendation, action_name: str
) -> OptimalRecommendation:
    utility = source.action_utilities[action_name]
    return replace(
        source,
        recommended_action=action_name,
        expected_net_utility_usd=(
            utility.net_expected_value_usd_micros / USD_MICROS_PER_USD
        ),
        uplift_quadrant=utility.uplift_quadrant,
        rank_score=utility.net_expected_value_usd_micros / USD_MICROS_PER_USD,
        authorized_to_act=False,
    )


class PortfolioOptimizer:
    """Exact deterministic allocator for the bounded local RH-05 runtime.

    ``specialist_capacity`` and ``total_budget_usd`` are an explicitly isolated
    legacy adapter. Governed callers use integer ``personnel_capacity_seconds``
    and ``budget_capacity_usd_micros``.
    """

    def __init__(
        self,
        specialist_capacity: int | None = None,
        total_budget_usd: float | None = None,
        *,
        personnel_capacity_seconds: int | None = None,
        budget_capacity_usd_micros: int | None = None,
        portfolio_id: str = "portfolio-local",
    ) -> None:
        self._legacy_specialist_capacity: int | None = None
        if personnel_capacity_seconds is None:
            legacy_count = 100 if specialist_capacity is None else specialist_capacity
            if not isinstance(legacy_count, int) or legacy_count < 0:
                raise ValueError("INVALID_CAPACITY: specialist_capacity must be nonnegative")
            self._legacy_specialist_capacity = legacy_count
            # Preserve the historical count constraint separately. This large
            # seconds ceiling prevents it from inventing a duration equivalence.
            personnel_capacity_seconds = 2**63 - 1
        if budget_capacity_usd_micros is None:
            legacy_budget = 10_000.0 if total_budget_usd is None else total_budget_usd
            converted = legacy_budget * USD_MICROS_PER_USD
            if legacy_budget < 0 or not converted.is_integer():
                raise ValueError("INVALID_CAPACITY: budget must convert exactly to USD micros")
            budget_capacity_usd_micros = int(converted)
        if not isinstance(personnel_capacity_seconds, int) or personnel_capacity_seconds < 0:
            raise ValueError("INVALID_CAPACITY: personnel capacity must be nonnegative seconds")
        if not isinstance(budget_capacity_usd_micros, int) or budget_capacity_usd_micros < 0:
            raise ValueError("INVALID_CAPACITY: budget capacity must be nonnegative USD micros")
        self.personnel_capacity_seconds = personnel_capacity_seconds
        self.budget_capacity_usd_micros = budget_capacity_usd_micros
        self.portfolio_id = portfolio_id

    @staticmethod
    def _is_abstain(action_name: str) -> bool:
        return action_name == "abstain" or action_name.startswith("act_abstain_")

    def _heuristic_state(
        self,
        ordered: Sequence[tuple[str, OptimalRecommendation]],
    ) -> tuple[tuple[int, int, int], tuple[int, tuple[str, ...], tuple[str, ...]]]:
        """Return a deterministic feasible selection outside the exact domain."""
        selected: dict[str, ActionUtility] = {}
        candidates: list[tuple[int, str, str, ActionUtility]] = []
        for occurrence_id, recommendation in ordered:
            eligible = [u for u in recommendation.action_utilities.values() if u.is_eligible]
            abstain = next((u for u in eligible if self._is_abstain(u.action_type)), None)
            if abstain is None:
                raise ValueError(f"INFEASIBLE_SELECTION: occurrence {occurrence_id!r} lacks abstain")
            selected[occurrence_id] = abstain
            for choice in eligible:
                if (
                    not self._is_abstain(choice.action_type)
                    and choice.net_expected_value_usd_micros > 0
                    and choice.direct_cost_usd_micros >= 0
                    and choice.personnel_seconds >= 0
                ):
                    candidates.append(
                        (
                            -choice.net_expected_value_usd_micros,
                            occurrence_id,
                            choice.action_id or choice.action_type,
                            choice,
                        )
                    )

        used_cost = used_seconds = used_specialists = objective = 0
        committed: set[str] = set()
        for _, occurrence_id, _, choice in sorted(candidates):
            if occurrence_id in committed:
                continue
            specialist_count = used_specialists + int(choice.action_type in SPECIALIST_ACTIONS)
            if used_cost + choice.direct_cost_usd_micros > self.budget_capacity_usd_micros:
                continue
            if used_seconds + choice.personnel_seconds > self.personnel_capacity_seconds:
                continue
            if (
                self._legacy_specialist_capacity is not None
                and specialist_count > self._legacy_specialist_capacity
            ):
                continue
            selected[occurrence_id] = choice
            committed.add(occurrence_id)
            used_cost += choice.direct_cost_usd_micros
            used_seconds += choice.personnel_seconds
            used_specialists = specialist_count
            objective += choice.net_expected_value_usd_micros

        chosen = [selected[occurrence_id] for occurrence_id, _ in ordered]
        return (
            (used_cost, used_seconds, used_specialists),
            (
                objective,
                tuple(choice.action_id or choice.action_type for choice in chosen),
                tuple(choice.action_type for choice in chosen),
            ),
        )

    def allocate_recommendations(
        self,
        recommendations: Sequence[OptimalRecommendation],
        *,
        occurrence_ids: Sequence[str] | None = None,
        as_of: datetime | None = None,
    ) -> PortfolioAllocation:
        """Choose one action per occurrence using exact dynamic programming."""
        eval_time = as_of or datetime.now(timezone.utc)
        if eval_time.tzinfo is None:
            raise ValueError("CONTEXT_MISMATCH: allocation cutoff must be timezone-aware")
        occurrence_ids = tuple(occurrence_ids or (r.policy_id for r in recommendations))
        if len(occurrence_ids) != len(recommendations) or len(set(occurrence_ids)) != len(occurrence_ids):
            raise ValueError("CONTEXT_MISMATCH: occurrence IDs must be unique and complete")

        ordered = sorted(zip(occurrence_ids, recommendations), key=lambda pair: pair[0])
        if len(ordered) > 6:
            used, best = self._heuristic_state(ordered)
            states = None
        else:
            used = best = None

        # (cost, seconds, legacy-specialist-count) ->
        # (objective, stable action-ID tie vector, runtime action-name vector)
        states: dict[
            tuple[int, int, int], tuple[int, tuple[str, ...], tuple[str, ...]]
        ] = {
            (0, 0, 0): (0, (), ())
        }
        for occurrence_id, recommendation in (() if used is not None else ordered):
            choices = [
                utility
                for utility in recommendation.action_utilities.values()
                if utility.is_eligible
                and utility.direct_cost_usd_micros >= 0
                and utility.personnel_seconds >= 0
            ]
            if not any(self._is_abstain(choice.action_type) for choice in choices):
                raise ValueError(f"INFEASIBLE_SELECTION: occurrence {occurrence_id!r} lacks abstain")
            choices.sort(key=lambda choice: (choice.action_id, choice.action_type))
            next_states: dict[
                tuple[int, int, int], tuple[int, tuple[str, ...], tuple[str, ...]]
            ] = {}
            for (used_cost, used_seconds, used_specialists), (
                objective,
                tie_vector,
                action_vector,
            ) in states.items():
                for choice in choices:
                    cost = used_cost + choice.direct_cost_usd_micros
                    seconds = used_seconds + choice.personnel_seconds
                    specialist_count = used_specialists + int(
                        choice.action_type in SPECIALIST_ACTIONS
                    )
                    if cost > self.budget_capacity_usd_micros or seconds > self.personnel_capacity_seconds:
                        continue
                    if (
                        self._legacy_specialist_capacity is not None
                        and specialist_count > self._legacy_specialist_capacity
                    ):
                        continue
                    candidate = (
                        objective + choice.net_expected_value_usd_micros,
                        tie_vector + ((choice.action_id or choice.action_type),),
                        action_vector + (choice.action_type,),
                    )
                    key = (cost, seconds, specialist_count)
                    incumbent = next_states.get(key)
                    if incumbent is None or candidate[0] > incumbent[0] or (
                        candidate[0] == incumbent[0] and candidate[1] < incumbent[1]
                    ):
                        next_states[key] = candidate
            states = next_states

        if used is None:
            if not states:
                raise ValueError("INFEASIBLE_SELECTION: no feasible portfolio allocation")
            used, best = min(states.items(), key=lambda item: (-item[1][0], item[1][1]))
        assert best is not None
        selected = tuple(
            _selected_recommendation(rec, action)
            for (_, rec), action in zip(ordered, best[2])
        )
        canonical = {
            "allocator_id": ALLOCATOR_ID,
            "allocator_version": ALLOCATOR_VERSION,
            "portfolio_id": self.portfolio_id,
            "as_of": eval_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "budget_capacity_usd_micros": self.budget_capacity_usd_micros,
            "personnel_capacity_seconds": self.personnel_capacity_seconds,
            "selections": [
                [occurrence_id, rec.recommended_action]
                for (occurrence_id, _), rec in zip(ordered, selected)
            ],
        }
        return PortfolioAllocation(
            allocation_id=f"alloc_{_canonical_digest(canonical)[:24]}",
            portfolio_id=self.portfolio_id,
            as_of=eval_time,
            budget_capacity_usd_micros=self.budget_capacity_usd_micros,
            budget_used_usd_micros=used[0],
            personnel_capacity_seconds=self.personnel_capacity_seconds,
            personnel_used_seconds=used[1],
            objective_usd_micros=best[0],
            recommendations=selected,
            occurrence_ids=tuple(pair[0] for pair in ordered),
        )

    def optimize_portfolio(
        self,
        eligible_sets: Sequence[EligibleActionSet],
        valuations: Mapping[str, PolicyValuation],
        risk_scores: Mapping[str, float],
        days_past_due_map: Mapping[str, int] | None = None,
        as_of: datetime | None = None,
    ) -> PortfolioAllocation:
        """Evaluate governed choices, then allocate jointly under both capacities."""
        dpd_map = days_past_due_map or {}
        recommendations: list[OptimalRecommendation] = []
        for eligible_set in eligible_sets:
            policy_id = eligible_set.policy_id
            valuation = valuations.get(policy_id)
            if valuation is None:
                raise ValueError(f"VALUATION_UNAVAILABLE: annual premium valuation missing for {policy_id!r}")
            if policy_id not in risk_scores:
                raise ValueError(f"CONTEXT_MISMATCH: risk score missing for {policy_id!r}")
            utilities = evaluate_action_utilities(
                eligible_set=eligible_set,
                valuation=valuation,
                lapse_risk_p=risk_scores[policy_id],
                days_past_due=dpd_map.get(policy_id, 0),
            )
            recommendations.append(
                OptimalRecommendation(
                    policy_id=policy_id,
                    recommended_action="abstain",
                    expected_net_utility_usd=0.0,
                    uplift_quadrant=utilities["abstain"].uplift_quadrant,
                    rank_score=0.0,
                    action_utilities=utilities,
                    authorized_to_act=False,
                )
            )
        return self.allocate_recommendations(recommendations, as_of=as_of)

    def marginal_opportunity_values(
        self,
        recommendations: Sequence[OptimalRecommendation],
        *,
        delta_money_usd_micros: int,
        delta_personnel_seconds: int,
        occurrence_ids: Sequence[str] | None = None,
        as_of: datetime | None = None,
    ) -> dict[str, object]:
        """Return contract-defined finite-difference capacity values."""
        if delta_money_usd_micros <= 0 or delta_personnel_seconds <= 0:
            raise ValueError("INVALID_CAPACITY: marginal increments must be positive")
        eval_time = as_of or datetime.now(timezone.utc)
        base = self.allocate_recommendations(
            recommendations, occurrence_ids=occurrence_ids, as_of=eval_time
        )
        money = PortfolioOptimizer(
            budget_capacity_usd_micros=(
                self.budget_capacity_usd_micros + delta_money_usd_micros
            ),
            personnel_capacity_seconds=self.personnel_capacity_seconds,
            portfolio_id=f"{self.portfolio_id}-money-plus",
        ).allocate_recommendations(
            recommendations, occurrence_ids=occurrence_ids, as_of=eval_time
        )
        personnel = PortfolioOptimizer(
            budget_capacity_usd_micros=self.budget_capacity_usd_micros,
            personnel_capacity_seconds=(
                self.personnel_capacity_seconds + delta_personnel_seconds
            ),
            portfolio_id=f"{self.portfolio_id}-personnel-plus",
        ).allocate_recommendations(
            recommendations, occurrence_ids=occurrence_ids, as_of=eval_time
        )
        return {
            "status": "AVAILABLE",
            "label": "modeled marginal value for the declared increment",
            "base_allocation_id": base.allocation_id,
            "money": {
                "delta_usd_micros": delta_money_usd_micros,
                "expanded_allocation_id": money.allocation_id,
                "modeled_marginal_value_usd_micros": (
                    money.objective_usd_micros - base.objective_usd_micros
                ),
            },
            "personnel": {
                "delta_seconds": delta_personnel_seconds,
                "expanded_allocation_id": personnel.allocation_id,
                "modeled_marginal_value_usd_micros": (
                    personnel.objective_usd_micros - base.objective_usd_micros
                ),
            },
        }
