"""Tests for Phase 2R-14BB v5 redesign diagnostics execution and readiness verification."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np

from inforsight_simulator.v5_diagnostics_execution import (
    DEVELOPMENT_SEEDS,
    DIAGNOSTIC_IDS,
    FEASIBILITY_GRID,
    HYPOTHESIS_IDS,
    RESERVED_V4_ACCEPTANCE_SEEDS,
    SPENT_V3_ACCEPTANCE_SEEDS,
    SPENT_V4_QUALIFICATION_SEEDS,
    build_readiness_manifest,
    compute_distribution,
    evaluate_grid_cell,
    evaluate_readiness,
    planned_inventory,
    project_aggregate,
    readiness_decision,
)

ROOT = Path(__file__).resolve().parents[2]


class TestV5DiagnosticsExecution(unittest.TestCase):
    """Test suite for R2-14BB diagnostic contracts, readiness, and execution boundaries."""

    def test_readiness_authorized_under_contract_1_1_0(self) -> None:
        manifest = build_readiness_manifest(ROOT)
        self.assertEqual(manifest["readiness_decision"], "authorized")
        self.assertTrue(manifest["result_producing_execution_authorized"])
        self.assertEqual(manifest["contract_version"], "1.1.0")
        self.assertEqual(manifest["predecessor_merge"], "627e698")
        self.assertEqual(manifest["planned_inventory"]["units"], 120)
        self.assertEqual(len(manifest["registered_hypotheses"]), 6)
        self.assertEqual(len(manifest["registered_diagnostics"]), 17)
        self.assertEqual(manifest["feasibility_surface_size"], 320)
        self.assertEqual(manifest["reserved_acceptance_status"], "not_materialized")
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")
        for check in manifest["checks"]:
            self.assertEqual(check["status"], "pass", f"Check {check['check_id']} failed")

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
        dist = compute_distribution([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(dist["count"], 5)
        self.assertEqual(dist["finite_count"], 5)
        self.assertAlmostEqual(dist["mean"], 3.0)
        self.assertAlmostEqual(dist["min"], 1.0)
        self.assertIn("0.50", dist["quantiles"])

    def test_evaluate_grid_cell_constraint_logic(self) -> None:
        cell = FEASIBILITY_GRID[0]
        eval_matrix = np.zeros((100, 17), dtype=float)
        eval_frailties = np.zeros(100, dtype=float)
        eval_targets = np.array([0] * 90 + [1] * 10, dtype=int)

        result = evaluate_grid_cell(cell, eval_matrix, eval_frailties, eval_targets)
        self.assertIn("cell_index", result)
        self.assertIn("simultaneous_constraints_met", result)
        self.assertIsInstance(result["simultaneous_constraints_met"], bool)


if __name__ == "__main__":
    unittest.main()

