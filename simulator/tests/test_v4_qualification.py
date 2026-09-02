from __future__ import annotations

from pathlib import Path
import json
import unittest

from inforsight_simulator.v4_qualification import (
    DEVELOPMENT_SEEDS, FUTURE_ACCEPTANCE_SEEDS, GATE_IDS, planned_inventory,
    build_readiness_manifest,
)

ROOT = Path(__file__).resolve().parents[2]


class V4QualificationTests(unittest.TestCase):
    def test_domains_and_inventory_are_frozen(self) -> None:
        self.assertEqual(DEVELOPMENT_SEEDS, tuple(range(20271101, 20271121)))
        self.assertEqual(FUTURE_ACCEPTANCE_SEEDS, tuple(range(20271201, 20271221)))
        self.assertFalse(set(DEVELOPMENT_SEEDS) & set(FUTURE_ACCEPTANCE_SEEDS))
        self.assertEqual(len(planned_inventory()), 120)
        self.assertEqual(len(GATE_IDS), 9)

    def test_readiness_authorizes_only_development(self) -> None:
        manifest = build_readiness_manifest(ROOT)
        self.assertEqual(manifest["readiness_decision"], "authorized")
        self.assertTrue(manifest["result_producing_execution_authorized"])
        self.assertEqual(manifest["future_acceptance_status"], "not_materialized")
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")

    def test_committed_evidence_is_complete_and_mechanical(self) -> None:
        path = ROOT / "docs/experiments/phase-02r-14-v4-qualification-manifest.json"
        manifest = json.loads(path.read_text())
        self.assertEqual(manifest["issue"], 72)
        self.assertEqual(manifest["seed_count"], 20)
        self.assertEqual(len(manifest["seed_evidence"]), 20)
        self.assertEqual(manifest["decision"], "redesign")
        self.assertFalse(manifest["r2_15_authorized"])
        self.assertEqual(set(manifest["gates"]), set(GATE_IDS))
        self.assertEqual(manifest["summary"]["observable_oracle_auc_pass_count"], 0)
        self.assertGreater(manifest["summary"]["maximum_monthly_terminal_hazard"], 0.20)
        self.assertFalse(manifest["protected_intermediates_committed"])
        self.assertEqual(manifest["future_acceptance_status"], "not_materialized")
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")
        rendered = path.read_text()
        for prohibited in ("outcome_uniforms", "latent_frailty", "probabilities",
                           "matrix_values", "final_holdout_seed"):
            self.assertNotIn(prohibited, rendered)


if __name__ == "__main__":
    unittest.main()
