"""Runtime regressions for RH-04 economics/resource contract 1.0.0."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from inforsight_simulator.economics import (
    EconomicsContractError,
    SignedTreatmentEffect,
    ValuationStatus,
    load_economics_resource_contract,
)
from inforsight_simulator.optimization import PolicyValuation, evaluate_action_utilities
from inforsight_simulator.rules import PolicyContext, evaluate_action_eligibility


ROOT = Path(__file__).resolve().parents[2]


class RH04EconomicsRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_economics_resource_contract()
        cls.fixtures = json.loads(
            (
                ROOT
                / "data-contracts/rh/economics/v1/acceptance-fixtures.json"
            ).read_text()
        )["cases"]

    def _value(self, case: dict):
        return self.contract.value(
            policy_id="pol_fixture",
            snapshot_id="snap_fixture",
            snapshot_version=self.contract.catalog.snapshot_version,
            catalog_sha256=self.contract.catalog.sha256,
            action=case["action_id"],
            effect=case["effect"],
            annual_premium_cents=case.get("annual_premium_cents"),
        )

    def test_harmful_neutral_and_beneficial_exact_arithmetic(self) -> None:
        for case in self.fixtures[:3]:
            with self.subTest(case=case["id"]):
                value = self._value(case)
                expected = case["expected"]
                self.assertEqual(value.status, ValuationStatus.AVAILABLE)
                self.assertEqual(value.classification, expected["classification"])
                self.assertEqual(
                    value.gross_expected_value_usd_micros,
                    expected["gross_expected_value_usd_micros"],
                )
                self.assertEqual(
                    value.direct_cost_usd_micros,
                    expected["direct_cost_usd_micros"],
                )
                self.assertEqual(
                    value.net_expected_value_usd_micros,
                    expected["net_expected_value_usd_micros"],
                )

    def test_fractional_personnel_hour_remains_exact_seconds(self) -> None:
        case = self.fixtures[3]
        action = self.contract.action(case["action_id"])
        self.assertEqual(action.personnel_seconds, case["expected"]["personnel_seconds"])
        self.assertEqual(f"{action.personnel_hours:.6f}", case["expected"]["display_hours"])

    def test_equal_cause_values_reconcile_to_combined_effect(self) -> None:
        case = self.fixtures[4]
        value = self._value(case)
        self.assertEqual(
            value.gross_expected_value_usd_micros,
            case["expected"]["gross_expected_value_usd_micros"],
        )
        component_total = sum(
            round(float(effect) * case["annual_premium_cents"] * 10_000)
            for effect in case["diagnostic_cause_effects"].values()
        )
        self.assertEqual(component_total, value.gross_expected_value_usd_micros)

    def test_missing_annual_premium_is_explicitly_unavailable(self) -> None:
        value = self._value(self.fixtures[5])
        self.assertEqual(value.status, ValuationStatus.UNAVAILABLE)
        self.assertEqual(value.error_code, "VALUATION_UNAVAILABLE")
        self.assertIsNone(value.gross_expected_value_usd_micros)
        self.assertIsNone(value.direct_cost_usd_micros)
        self.assertIsNone(value.net_expected_value_usd_micros)

    def test_unknown_contract_version_and_action_fail(self) -> None:
        with self.assertRaises(EconomicsContractError) as version_error:
            load_economics_resource_contract("2.0.0")
        self.assertEqual(version_error.exception.code, "INCOMPATIBLE_ECONOMICS_CONTRACT")
        with self.assertRaises(EconomicsContractError) as action_error:
            self.contract.action("unknown")
        self.assertEqual(action_error.exception.code, "UNKNOWN_ACTION_ID")

    def test_metric_is_expected_not_realized(self) -> None:
        value = self._value(self.fixtures[7])
        self.assertEqual(value.metric_id, self.fixtures[7]["expected"]["metric_id"])
        serialized = value.to_dict()
        for forbidden in self.fixtures[7]["expected"]["forbidden_labels"]:
            self.assertNotIn(forbidden, serialized)

    def test_effect_validation_and_canonicalization(self) -> None:
        self.assertEqual(SignedTreatmentEffect("-0.1").canonical_value(), "-0.100000")
        for invalid in (True, "NaN", "Infinity", "1.1", "-1.1"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(EconomicsContractError):
                    SignedTreatmentEffect(invalid)

    def test_canonical_serialization_is_deterministic(self) -> None:
        value = self._value(self.fixtures[0])
        self.assertEqual(value.canonical_bytes(), value.canonical_bytes())
        self.assertNotIn(b" ", value.canonical_bytes())

    def test_optimization_uses_annual_premium_not_legacy_clv(self) -> None:
        eligible = evaluate_action_eligibility(
            PolicyContext(
                policy_id="pol_fixture",
                as_of=datetime(2026, 9, 9, tzinfo=timezone.utc),
                status="active",
                tenure_days=365,
                in_grace_period=False,
                days_past_due=0,
                has_active_claim=False,
                has_legal_hold=False,
                has_registered_dispute=False,
                sms_opt_out=False,
                email_opt_out=False,
                phone_opt_out=False,
                dnc_registered=False,
            )
        )
        low_clv = PolicyValuation("pol_fixture", 1200.0, 1.0)
        high_clv = PolicyValuation("pol_fixture", 1200.0, 999999.0)
        low = evaluate_action_utilities(eligible, low_clv, 0.4)
        high = evaluate_action_utilities(eligible, high_clv, 0.4)
        self.assertEqual(
            low["courtesy_reminder"].net_expected_value_usd_micros,
            high["courtesy_reminder"].net_expected_value_usd_micros,
        )
        self.assertEqual(low["courtesy_reminder"].direct_cost_usd_micros, 1_500_000)


if __name__ == "__main__":
    unittest.main()
