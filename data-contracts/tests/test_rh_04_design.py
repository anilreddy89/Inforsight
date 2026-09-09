"""Validate RH-04D artifacts without changing runtime behavior or evidence."""

from decimal import Decimal, ROUND_HALF_EVEN
from hashlib import sha256
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "data-contracts/rh/economics/v1"


def read(name: str) -> dict:
    return json.loads((DESIGN / name).read_text())


class RH04DesignTest(unittest.TestCase):
    def test_contract_schema_is_closed_and_catalog_is_pinned(self):
        contract = read("economics-resource-contract.json")
        schema = read("economics-resource-contract.schema.json")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        validator.validate(contract)

        catalog_path = ROOT / contract["semantic_catalog"]["path"]
        self.assertEqual(
            sha256(catalog_path.read_bytes()).hexdigest(),
            contract["semantic_catalog"]["sha256"],
        )
        changed = dict(contract)
        changed["personnel_unit"] = "hour"
        self.assertFalse(validator.is_valid(changed))

    def test_action_money_and_resources_exactly_bridge_rh01(self):
        contract = read("economics-resource-contract.json")
        catalog = json.loads((ROOT / contract["semantic_catalog"]["path"]).read_text())
        expected = {
            row["action_id"]: (
                row["direct_cost_cents"] * contract["usd_micros_per_cent"],
                row["personnel_seconds"],
            )
            for row in catalog["actions"]
        }
        actual = {
            row["action_id"]: (
                row["direct_cost_usd_micros"], row["personnel_seconds"]
            )
            for row in contract["actions"]
        }
        self.assertEqual(actual, expected)

    def test_signed_fixture_arithmetic_preserves_harm(self):
        contract = read("economics-resource-contract.json")
        fixtures = read("acceptance-fixtures.json")["cases"]
        action_costs = {
            row["action_id"]: row["direct_cost_usd_micros"]
            for row in contract["actions"]
        }
        signed = [case for case in fixtures if case["id"].endswith("-treatment")]
        self.assertEqual(
            [case["expected"]["classification"] for case in signed],
            ["harmful", "neutral", "beneficial"],
        )
        for case in signed:
            gross = (
                Decimal(case["effect"])
                * case["annual_premium_cents"]
                * contract["usd_micros_per_cent"]
            ).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
            expected = case["expected"]
            with self.subTest(case=case["id"]):
                self.assertEqual(int(gross), expected["gross_expected_value_usd_micros"])
                self.assertEqual(action_costs[case["action_id"]], expected["direct_cost_usd_micros"])
                self.assertEqual(
                    int(gross) - action_costs[case["action_id"]],
                    expected["net_expected_value_usd_micros"],
                )
        self.assertLess(signed[0]["expected"]["gross_expected_value_usd_micros"], 0)

    def test_cause_contributions_reconcile_without_assumed_shares(self):
        contract = read("economics-resource-contract.json")
        case = next(
            case
            for case in read("acceptance-fixtures.json")["cases"]
            if case["id"] == "combined-target-equal-outcome-values"
        )
        causes = case["diagnostic_cause_effects"]
        self.assertEqual(
            Decimal(causes["lapse"]) + Decimal(causes["surrender"]),
            Decimal(case["effect"]),
        )
        self.assertEqual(
            case["expected"]["lapse_gross_expected_value_usd_micros"]
            + case["expected"]["surrender_gross_expected_value_usd_micros"],
            case["expected"]["gross_expected_value_usd_micros"],
        )
        self.assertEqual(
            contract["value_basis"]["lapse_multiplier"],
            contract["value_basis"]["surrender_multiplier"],
        )

    def test_personnel_and_evaluation_protocol_do_not_truncate_or_refit(self):
        contract = read("economics-resource-contract.json")
        case = next(
            case
            for case in read("acceptance-fixtures.json")["cases"]
            if case["id"] == "fractional-personnel-hour"
        )
        self.assertEqual(
            Decimal(case["expected"]["display_hours"]),
            Decimal(case["expected"]["personnel_seconds"])
            / contract["seconds_per_hour"],
        )
        protocol = contract["evaluation_protocol"]
        self.assertEqual(len(protocol["primary_estimands"]), 2)
        self.assertTrue(protocol["report_separately"])
        self.assertEqual(protocol["cluster_identity"], "policy_id")
        self.assertIn("fixed", protocol["allocation_procedure_budget_rule"])
        self.assertTrue(protocol["predictive_model_rule"].startswith("Never refit"))
        self.assertGreaterEqual(len(protocol["sensitivity_axes"]), 4)

    def test_labels_separate_expected_value_from_profit_and_realized_value(self):
        case = next(
            case
            for case in read("acceptance-fixtures.json")["cases"]
            if case["id"] == "expected-not-realized"
        )
        metric = case["expected"]["metric_id"]
        self.assertIn("modeled_expected", metric)
        for forbidden in case["expected"]["forbidden_labels"]:
            self.assertNotIn(forbidden, metric)


if __name__ == "__main__":
    unittest.main()
