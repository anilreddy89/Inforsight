"""Tests for Phase 2R-14B v5 redesign diagnostics and readiness verification."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from inforsight_simulator.v5_diagnostics import (
    DEVELOPMENT_SEEDS, DIAGNOSTIC_IDS, FEASIBILITY_GRID, HYPOTHESIS_IDS,
    RESERVED_V4_ACCEPTANCE_SEEDS, SPENT_V3_ACCEPTANCE_SEEDS,
    SPENT_V4_QUALIFICATION_SEEDS, build_readiness_manifest,
    build_governed_stop_manifest, compute_distribution, evaluate_readiness, planned_inventory,
    project_aggregate, readiness_decision,
)

ROOT = Path(__file__).resolve().parents[2]


class TestV5Diagnostics(unittest.TestCase):
    """Test suite for R2-14B diagnostic contracts and readiness boundaries."""

    def test_readiness_stops_when_disposition_rules_are_not_frozen(self) -> None:
        manifest = build_readiness_manifest(ROOT)
        self.assertEqual(manifest["readiness_decision"], "stop")
        self.assertFalse(manifest["result_producing_execution_authorized"])
        self.assertEqual(manifest["contract_version"], "1.0.0")
        self.assertEqual(manifest["predecessor_merge"], "52c03c8")
        self.assertEqual(manifest["planned_inventory"]["units"], 120)
        self.assertEqual(len(manifest["registered_hypotheses"]), 6)
        self.assertEqual(len(manifest["registered_diagnostics"]), 17)
        self.assertEqual(manifest["feasibility_surface_size"], 320)
        self.assertEqual(manifest["reserved_acceptance_status"], "not_materialized")
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")
        rule_check = next(
            check for check in manifest["checks"]
            if check["check_id"] == "mechanical_hypothesis_disposition_rules"
        )
        self.assertEqual(rule_check["status"], "fail")
        self.assertEqual(rule_check["failure_classification"], "stop")

    def test_governed_stop_manifest_has_no_result_inventory(self) -> None:
        manifest = build_governed_stop_manifest(build_readiness_manifest(ROOT))
        self.assertEqual(manifest["execution_decision"], "stop")
        self.assertFalse(manifest["result_producing_execution_authorized"])
        self.assertEqual(manifest["executed_inventory"]["units"], 0)
        self.assertEqual(manifest["executed_inventory"]["feasibility_cells"], 0)
        self.assertEqual(len(manifest["governed_failures"]), 17)
        self.assertEqual(set(manifest["hypothesis_dispositions"].values()), {"unresolved"})
        self.assertEqual(manifest["selected_response"], "stop_contract_not_executable")

    def test_readiness_fails_closed_on_missing_input(self) -> None:
        checks = evaluate_readiness(ROOT / "nonexistent")
        self.assertEqual(readiness_decision(checks), "stop")

    def test_seed_domain_separation(self) -> None:
        all_seeds = (
            set(SPENT_V3_ACCEPTANCE_SEEDS)
            | set(SPENT_V4_QUALIFICATION_SEEDS)
            | set(RESERVED_V4_ACCEPTANCE_SEEDS)
            | set(DEVELOPMENT_SEEDS)
        )
        self.assertEqual(len(all_seeds), 80)
        self.assertEqual(len(DEVELOPMENT_SEEDS), 20)
        self.assertEqual(DEVELOPMENT_SEEDS[0], 20280101)
        self.assertEqual(DEVELOPMENT_SEEDS[-1], 20280120)

    def test_planned_inventory_completeness(self) -> None:
        inv = planned_inventory()
        self.assertEqual(len(inv), 120)
        seeds = {item["seed"] for item in inv}
        self.assertEqual(seeds, set(DEVELOPMENT_SEEDS))
        scenarios = {item["scenario"] for item in inv}
        self.assertEqual(scenarios, {"signal", "matched_null"})
        folds = {item["fold"] for item in inv}
        self.assertEqual(folds, {"fold_1", "fold_2", "fold_3"})

    def test_feasibility_grid_exactness(self) -> None:
        self.assertEqual(len(FEASIBILITY_GRID), 320)
        self.assertEqual(FEASIBILITY_GRID[0]["cell_index"], 0)
        self.assertEqual(FEASIBILITY_GRID[0]["public_coefficient_scale"], 1.0)
        self.assertEqual(FEASIBILITY_GRID[0]["frailty_standard_deviation"], 0.0)
        self.assertEqual(FEASIBILITY_GRID[0]["lapse_intercept_delta"], -0.50)
        self.assertEqual(FEASIBILITY_GRID[0]["surrender_intercept_delta"], -0.50)
        self.assertEqual(FEASIBILITY_GRID[-1]["cell_index"], 319)
        self.assertEqual(FEASIBILITY_GRID[-1]["public_coefficient_scale"], 3.0)
        self.assertEqual(FEASIBILITY_GRID[-1]["frailty_standard_deviation"], 0.30)
        self.assertEqual(FEASIBILITY_GRID[-1]["lapse_intercept_delta"], 0.25)
        self.assertEqual(FEASIBILITY_GRID[-1]["surrender_intercept_delta"], 0.25)

    def test_suppression_rule(self) -> None:
        suppressed = project_aggregate(unique_policy_count=9, observed={"val": 1.23})
        self.assertEqual(suppressed["status"], "suppressed")
        self.assertIsNone(suppressed["observed"])
        self.assertEqual(suppressed["suppression_rule"], "minimum_10_unique_policies")

        reported = project_aggregate(unique_policy_count=10, observed={"val": 1.23})
        self.assertEqual(reported["status"], "reported")
        self.assertEqual(reported["observed"], {"val": 1.23})
        self.assertIsNone(reported["suppression_rule"])

    def test_distribution_calculation(self) -> None:
        vals = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        dist = compute_distribution(vals)
        self.assertEqual(dist["count"], 10)
        self.assertEqual(dist["finite_count"], 10)
        self.assertAlmostEqual(dist["mean"], 5.5)
        self.assertEqual(dist["min"], 1.0)
        self.assertIn("0.50", dist["quantiles"])

        with self.assertRaises(ValueError):
            compute_distribution([float("nan")])


if __name__ == "__main__":
    unittest.main()
