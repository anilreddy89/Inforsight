"""Runtime acceptance tests for RH-05 allocation contract 1.0.0."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import product
import json
from pathlib import Path
import unittest

from inforsight_simulator.optimization import (
    ActionUtility,
    OptimalRecommendation,
    PortfolioOptimizer,
    UpliftQuadrant,
    compare_portfolio_strategies,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data-contracts/rh/allocation/v1/acceptance-fixtures.json"
AS_OF = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)


def _recommendation(occurrence_id: str, choices: list[dict]) -> OptimalRecommendation:
    utilities = {
        choice["action_id"]: ActionUtility(
            action_type=choice["action_id"],
            action_id=choice["action_id"],
            is_eligible=True,
            treatment_effect=0.0,
            gross_benefit_usd=choice["value"] / 1_000_000,
            direct_cost_usd=choice["cost"] / 1_000_000,
            net_utility_usd=choice["value"] / 1_000_000,
            uplift_quadrant=UpliftQuadrant.SURE_THING,
            gross_expected_value_usd_micros=choice["value"] + choice["cost"],
            direct_cost_usd_micros=choice["cost"],
            net_expected_value_usd_micros=choice["value"],
            personnel_seconds=choice["seconds"],
        )
        for choice in choices
    }
    return OptimalRecommendation(
        policy_id=f"pol_{occurrence_id.replace('-', '')}",
        recommended_action="abstain",
        expected_net_utility_usd=0.0,
        uplift_quadrant=UpliftQuadrant.SURE_THING,
        rank_score=0.0,
        action_utilities=utilities,
    )


class RH05PortfolioAllocationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = json.loads(FIXTURES.read_text())["cases"]

    def test_production_allocator_matches_all_predeclared_fixtures(self) -> None:
        for case in self.fixtures:
            occurrence_ids = list(case["choices"])
            recommendations = [
                _recommendation(oid, case["choices"][oid]) for oid in occurrence_ids
            ]
            allocation = PortfolioOptimizer(
                budget_capacity_usd_micros=case["budget_capacity_usd_micros"],
                personnel_capacity_seconds=case["personnel_capacity_seconds"],
                portfolio_id=case["id"],
            ).allocate_recommendations(
                recommendations, occurrence_ids=occurrence_ids, as_of=AS_OF
            )
            selected = dict(
                zip(
                    allocation.occurrence_ids,
                    (rec.recommended_action for rec in allocation.recommendations),
                )
            )
            with self.subTest(case=case["id"]):
                self.assertEqual(selected, case["expected"]["selected"])
                self.assertEqual(allocation.objective_usd_micros, case["expected"]["objective"])
                self.assertEqual(allocation.budget_used_usd_micros, case["expected"]["cost"])
                self.assertEqual(allocation.personnel_used_seconds, case["expected"]["seconds"])

    def test_zero_gap_on_declared_exhaustive_generated_domain(self) -> None:
        """Exhaust 64 cases: n=1..4 and both capacities in {0,1,2,3}."""
        checked = 0
        for occurrence_count, money, seconds in product(range(1, 5), range(4), range(4)):
            occurrence_ids = [f"occ-{index:03d}" for index in range(occurrence_count)]
            choices_by_occurrence = {
                occurrence_id: [
                    {"action_id": "abstain", "value": 0, "cost": 0, "seconds": 0},
                    {
                        "action_id": "action-a",
                        "value": 2 + index,
                        "cost": index % 3,
                        "seconds": (index + 1) % 3,
                    },
                    {
                        "action_id": "action-b",
                        "value": (-1 if index == 0 else 3),
                        "cost": (index + 1) % 3,
                        "seconds": index % 3,
                    },
                ]
                for index, occurrence_id in enumerate(occurrence_ids)
            }
            reference = None
            for choices in product(*(choices_by_occurrence[oid] for oid in occurrence_ids)):
                cost = sum(item["cost"] for item in choices)
                used_seconds = sum(item["seconds"] for item in choices)
                if cost > money or used_seconds > seconds:
                    continue
                objective = sum(item["value"] for item in choices)
                vector = tuple(item["action_id"] for item in choices)
                candidate = (objective, vector, cost, used_seconds)
                if reference is None or objective > reference[0] or (
                    objective == reference[0] and vector < reference[1]
                ):
                    reference = candidate
            assert reference is not None
            recommendations = [
                _recommendation(oid, choices_by_occurrence[oid]) for oid in occurrence_ids
            ]
            actual = PortfolioOptimizer(
                budget_capacity_usd_micros=money,
                personnel_capacity_seconds=seconds,
                portfolio_id=f"exhaustive-{occurrence_count}-{money}-{seconds}",
            ).allocate_recommendations(
                recommendations, occurrence_ids=occurrence_ids, as_of=AS_OF
            )
            self.assertEqual(actual.objective_usd_micros - reference[0], 0)
            self.assertEqual(
                tuple(item.recommended_action for item in actual.recommendations), reference[1]
            )
            checked += 1
        self.assertEqual(checked, 64)

    def test_input_order_does_not_change_canonical_allocation(self) -> None:
        case = self.fixtures[1]
        occurrence_ids = list(case["choices"])
        recommendations = [_recommendation(oid, case["choices"][oid]) for oid in occurrence_ids]
        optimizer = PortfolioOptimizer(
            budget_capacity_usd_micros=case["budget_capacity_usd_micros"],
            personnel_capacity_seconds=case["personnel_capacity_seconds"],
            portfolio_id=case["id"],
        )
        forward = optimizer.allocate_recommendations(
            recommendations, occurrence_ids=occurrence_ids, as_of=AS_OF
        )
        reverse = optimizer.allocate_recommendations(
            list(reversed(recommendations)),
            occurrence_ids=list(reversed(occurrence_ids)),
            as_of=AS_OF,
        )
        self.assertEqual(forward.to_dict(), reverse.to_dict())

    def test_invalid_capacity_and_occurrence_identity_fail_explicitly(self) -> None:
        with self.assertRaisesRegex(ValueError, "INVALID_CAPACITY"):
            PortfolioOptimizer(
                budget_capacity_usd_micros=-1, personnel_capacity_seconds=0
            )
        rec = _recommendation("occ-001", self.fixtures[0]["choices"]["occ-001"])
        with self.assertRaisesRegex(ValueError, "CONTEXT_MISMATCH"):
            PortfolioOptimizer(
                budget_capacity_usd_micros=0, personnel_capacity_seconds=0
            ).allocate_recommendations(
                [rec, rec], occurrence_ids=["occ-001", "occ-001"], as_of=AS_OF
            )

    def test_marginal_opportunity_values_use_finite_differences(self) -> None:
        case = self.fixtures[1]
        occurrence_ids = list(case["choices"])
        recommendations = [_recommendation(oid, case["choices"][oid]) for oid in occurrence_ids]
        values = PortfolioOptimizer(
            budget_capacity_usd_micros=50,
            personnel_capacity_seconds=50,
            portfolio_id="marginal-test",
        ).marginal_opportunity_values(
            recommendations,
            occurrence_ids=occurrence_ids,
            delta_money_usd_micros=50,
            delta_personnel_seconds=50,
            as_of=AS_OF,
        )
        self.assertEqual(values["status"], "AVAILABLE")
        self.assertGreaterEqual(values["money"]["modeled_marginal_value_usd_micros"], 0)
        self.assertGreaterEqual(values["personnel"]["modeled_marginal_value_usd_micros"], 0)

    def test_four_strategy_comparison_uses_one_context_and_exact_capacities(self) -> None:
        case = self.fixtures[1]
        occurrence_ids = list(case["choices"])
        recommendations = [_recommendation(oid, case["choices"][oid]) for oid in occurrence_ids]
        risk_scores = {item.policy_id: 0.5 + index / 100 for index, item in enumerate(recommendations)}
        results = compare_portfolio_strategies(
            recommendations,
            risk_scores=risk_scores,
            budget_capacity_usd_micros=case["budget_capacity_usd_micros"],
            personnel_capacity_seconds=case["personnel_capacity_seconds"],
            as_of=AS_OF,
            portfolio_id="comparison-test",
        )
        self.assertEqual(
            [item.strategy_id for item in results],
            ["non_intervention", "operational_rules_only", "risk_ranked", "allocation_engine"],
        )
        self.assertEqual(len({item.comparison_context_sha256 for item in results}), 1)
        self.assertEqual(results[0].selected_count, 0)
        for item in results:
            self.assertTrue(item.feasible)
            self.assertLessEqual(item.budget_used_usd_micros, case["budget_capacity_usd_micros"])
            self.assertLessEqual(item.personnel_used_seconds, case["personnel_capacity_seconds"])


if __name__ == "__main__":
    unittest.main()
