"""Unit and mutation tests for Phase 2R.16 Generation v6 statistical acceptance."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from inforsight_simulator.v6_acceptance import (
    BOOTSTRAP_REPLICATES, DEVELOPMENT_SEEDS, FINAL_HOLDOUT_STATUS,
    GOVERNED_ACCEPTANCE_FOLDS, RESERVED_ACCEPTANCE_SEEDS, RuleResult,
    SPENT_ACCEPTANCE_SEEDS, SPENT_DIAGNOSTIC_SEEDS, SPENT_QUALIFICATION_SEEDS,
    V6_ACCEPTANCE_PROTOCOL_VERSION,
    aggregate_decision, average_precision, brier_score,
    build_readiness_manifest, calibration_intercept_slope,
    evaluate_readiness, percentile_interval, planned_inventory,
    roc_auc,
)

ROOT = Path(__file__).resolve().parents[2]


class V6AcceptanceTests(unittest.TestCase):
    def test_domains_and_inventory_are_frozen(self) -> None:
        self.assertEqual(len(RESERVED_ACCEPTANCE_SEEDS), 20)
        self.assertEqual(RESERVED_ACCEPTANCE_SEEDS[0], 20271201)
        self.assertEqual(RESERVED_ACCEPTANCE_SEEDS[-1], 20271220)
        all_spent = (
            set(SPENT_ACCEPTANCE_SEEDS) | set(SPENT_QUALIFICATION_SEEDS) |
            set(SPENT_DIAGNOSTIC_SEEDS) | set(DEVELOPMENT_SEEDS)
        )
        self.assertFalse(set(RESERVED_ACCEPTANCE_SEEDS) & all_spent)
        inv = planned_inventory()
        self.assertEqual(len(inv), 120)
        self.assertEqual(len(GOVERNED_ACCEPTANCE_FOLDS), 3)

    def test_readiness_passes_on_governed_main(self) -> None:
        manifest = build_readiness_manifest(ROOT)
        self.assertEqual(manifest["readiness_decision"], "proceed")
        self.assertTrue(manifest["result_producing_execution_authorized"])
        self.assertEqual(manifest["final_holdout_status"], FINAL_HOLDOUT_STATUS)
        for check in manifest["checks"]:
            self.assertEqual(check["status"], "pass", f"check failed: {check['rule_id']}")

    def test_metric_primitives(self) -> None:
        targets = [0, 0, 1, 1]
        probs = [0.1, 0.2, 0.8, 0.9]
        self.assertEqual(roc_auc(targets, probs), 1.0)
        self.assertAlmostEqual(brier_score(targets, probs), 0.025, places=3)
        self.assertEqual(average_precision(targets, probs), 1.0)

        intercept, slope = calibration_intercept_slope(targets, probs)
        self.assertIsInstance(intercept, float)
        self.assertIsInstance(slope, float)

        # Inverted targets
        inv_targets = [1, 1, 0, 0]
        self.assertEqual(roc_auc(inv_targets, probs), 0.0)

    def test_percentile_interval(self) -> None:
        values = list(range(100))
        ci = percentile_interval(values)
        self.assertEqual(len(ci), 2)
        self.assertLess(ci[0], ci[1])
        self.assertAlmostEqual(ci[0], 2.0, delta=1.0)
        self.assertAlmostEqual(ci[1], 97.0, delta=1.0)

    def test_decision_precedence(self) -> None:
        r_pass = RuleResult("R1", "fam", "scope", {}, "eq", True, True, "pass", "redesign", ("ev",))
        r_redesign = RuleResult("R2", "fam", "scope", {}, "eq", True, False, "fail", "redesign", ("ev",))
        r_stop = RuleResult("R3", "fam", "scope", {}, "eq", True, False, "fail", "stop", ("ev",))

        self.assertEqual(aggregate_decision([r_pass]), "proceed")
        self.assertEqual(aggregate_decision([r_pass, r_redesign]), "redesign")
        self.assertEqual(aggregate_decision([r_pass, r_stop]), "stop")
        self.assertEqual(aggregate_decision([r_pass, r_redesign, r_stop]), "stop")
        self.assertEqual(aggregate_decision([]), "redesign")

    def test_holdout_protection(self) -> None:
        manifest = build_readiness_manifest(ROOT)
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")

    def test_protocol_version_3_1_0_governance(self) -> None:
        self.assertEqual(V6_ACCEPTANCE_PROTOCOL_VERSION, "3.1.0")
        manifest = build_readiness_manifest(ROOT)
        self.assertEqual(manifest["acceptance_protocol_version"], "3.1.0")
        self.assertEqual(manifest["phase"], "R2-16A")
        self.assertEqual(manifest["issue"], 94)
        self.assertEqual(manifest["readiness_decision"], "proceed")


if __name__ == "__main__":
    unittest.main()
