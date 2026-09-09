"""Design validation for RH-05 portfolio allocation contract 1.0.0."""

from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = ROOT / "data-contracts/rh/allocation/v1"


def exact_reference(case: dict) -> dict:
    occurrence_ids = sorted(case["choices"])
    best = None
    for selection in product(*(case["choices"][oid] for oid in occurrence_ids)):
        cost = sum(choice["cost"] for choice in selection)
        seconds = sum(choice["seconds"] for choice in selection)
        if cost > case["budget_capacity_usd_micros"] or seconds > case["personnel_capacity_seconds"]:
            continue
        objective = sum(choice["value"] for choice in selection)
        vector = tuple((oid, choice["action_id"]) for oid, choice in zip(occurrence_ids, selection))
        candidate = (objective, vector, cost, seconds)
        if best is None or objective > best[0] or (objective == best[0] and vector < best[1]):
            best = candidate
    if best is None:
        raise AssertionError("abstain must make every structurally valid fixture feasible")
    return {
        "selected": dict(best[1]),
        "objective": best[0],
        "cost": best[2],
        "seconds": best[3],
    }


class RH05AllocationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((CONTRACT_DIR / "portfolio-allocation-contract.json").read_text())
        cls.schema = json.loads((CONTRACT_DIR / "portfolio-allocation-contract.schema.json").read_text())
        cls.fixtures = json.loads((CONTRACT_DIR / "acceptance-fixtures.json").read_text())

    def test_contract_matches_closed_schema(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        Draft202012Validator(self.schema).validate(self.contract)

    def test_exact_reference_matches_predeclared_fixtures(self) -> None:
        for case in self.fixtures["cases"]:
            with self.subTest(case=case["id"]):
                actual = exact_reference(case)
                expected = {key: case["expected"][key] for key in ("selected", "objective", "cost", "seconds")}
                self.assertEqual(actual, expected)

    def test_contract_uses_exact_rh04_resource_units(self) -> None:
        pairs = {(item["capacity"], item["consumption"]) for item in self.contract["resource_constraints"]}
        self.assertEqual(pairs, {("budget_capacity_usd_micros", "direct_cost_usd_micros"), ("personnel_capacity_seconds", "personnel_seconds")})

    def test_acceptance_predeclares_zero_additive_gap(self) -> None:
        acceptance = self.contract["acceptance"]
        self.assertEqual(acceptance["gap_metric"], "additive_usd_micros")
        self.assertEqual(acceptance["maximum_gap_usd_micros"], 0)
        self.assertFalse(acceptance["relative_gap_authoritative"])
        self.assertTrue(acceptance["feasibility_required"])

    def test_strategy_comparison_is_closed_and_ordered(self) -> None:
        self.assertEqual(self.contract["strategy_comparison"], ["non_intervention", "operational_rules_only", "risk_ranked", "allocation_engine"])

    def test_required_conflict_and_capacity_failures_are_named(self) -> None:
        codes = set(self.contract["required_failure_codes"])
        self.assertTrue({"STALE_ALLOCATION", "CAPACITY_VERSION_CONFLICT", "CAPACITY_EXCEEDED"}.issubset(codes))


if __name__ == "__main__":
    unittest.main()
