"""Unit tests for Phase 2.11 final evaluation harness, metrics, and gate checks."""

from __future__ import annotations

from pathlib import Path
import unittest

from inforsight_simulator.bundle import ModelBundle
from inforsight_simulator.final_evaluation import (
    EVALUATION_SEED,
    FINAL_EVALUATION_ARTIFACT_VERSION,
    FINAL_EVALUATION_CONTRACT_VERSION,
    execute_final_evaluation,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUNDLE_PATH = REPO_ROOT / "docs" / "experiments" / "phase-02-10-model-bundle.json"
MANIFEST_PATH = REPO_ROOT / "docs" / "experiments" / "phase-02-11-final-evaluation-manifest.json"
REPORT_PATH = REPO_ROOT / "docs" / "experiments" / "phase-02-11-final-evaluation-report.md"
DECISION_NOTE_PATH = REPO_ROOT / "docs" / "experiments" / "phase-02-11-phase-2-decision-note.md"
CONTRACT_PATH = REPO_ROOT / "docs" / "modeling" / "phase-02-11-final-evaluation-contract.md"


class TestFinalEvaluation(unittest.TestCase):
    """Test suite for Phase 2.11 final evaluation protocol, metrics, and gates."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.assertTrue(cls, BUNDLE_PATH.is_file(), "Model bundle must exist")
        cls.assertTrue(cls, MANIFEST_PATH.is_file(), "Final evaluation manifest must exist")
        cls.assertTrue(cls, REPORT_PATH.is_file(), "Final evaluation report must exist")
        cls.assertTrue(cls, DECISION_NOTE_PATH.is_file(), "Decision note must exist")
        cls.assertTrue(cls, CONTRACT_PATH.is_file(), "Final evaluation contract must exist")

    def test_artifacts_exist_and_non_empty(self) -> None:
        self.assertGreater(MANIFEST_PATH.stat().st_size, 1000)
        self.assertGreater(REPORT_PATH.stat().st_size, 500)
        self.assertGreater(DECISION_NOTE_PATH.stat().st_size, 500)

    def test_final_evaluation_execution_gates(self) -> None:
        bundle = ModelBundle.load(BUNDLE_PATH)
        self.assertEqual(bundle.bundle_id, "inforsight-v6-logistic-platt-20260817")

        manifest = execute_final_evaluation(BUNDLE_PATH)
        self.assertEqual(manifest["contract_version"], FINAL_EVALUATION_CONTRACT_VERSION)
        self.assertEqual(manifest["artifact_version"], FINAL_EVALUATION_ARTIFACT_VERSION)
        self.assertEqual(manifest["decision"], "RELEASE")

        # Verify all gates passed
        for gate in manifest["gates"]:
            self.assertTrue(gate["passed"], f"Gate {gate['gate_id']} ({gate['metric']}) did not pass")

        # Verify key metric values
        metrics = manifest["metrics"]
        self.assertAlmostEqual(metrics["roc_auc"], 0.6998, places=4)
        self.assertAlmostEqual(metrics["average_precision"], 0.2765, places=4)
        self.assertAlmostEqual(metrics["brier_score"], 0.1211, places=4)
        self.assertAlmostEqual(metrics["ece"], 0.0115, places=4)
        self.assertAlmostEqual(metrics["calibration_slope"], 0.9498, places=4)

        # Verify operational queue lift
        top_1 = next(q for q in manifest["operational_review_capacities"] if abs(q["capacity"] - 0.01) < 1e-4)
        self.assertGreaterEqual(top_1["precision"], 0.3000)
        self.assertGreaterEqual(top_1["lift"], 2.00)

        top_5 = next(q for q in manifest["operational_review_capacities"] if abs(q["capacity"] - 0.05) < 1e-4)
        self.assertGreaterEqual(top_5["lift"], 2.00)

    def test_bootstrap_cis_valid(self) -> None:
        manifest = execute_final_evaluation(BUNDLE_PATH)
        metrics = manifest["metrics"]

        auc_ci = metrics["roc_auc_ci_95"]
        self.assertLess(auc_ci[0], metrics["roc_auc"])
        self.assertGreater(auc_ci[1], metrics["roc_auc"])

        ap_ci = metrics["average_precision_ci_95"]
        self.assertLess(ap_ci[0], metrics["average_precision"])
        self.assertGreater(ap_ci[1], metrics["average_precision"])

        brier_ci = metrics["brier_score_ci_95"]
        self.assertLess(brier_ci[0], metrics["brier_score"])
        self.assertGreater(brier_ci[1], metrics["brier_score"])


if __name__ == "__main__":
    unittest.main()

