from __future__ import annotations

from pathlib import Path
import unittest

from inforsight_simulator.v2_acceptance import (
    FINAL_HOLDOUT_STATUS,
    NOT_RUN_STATUS,
    R2_ACCEPTANCE_FOLDS,
    R2_ACCEPTANCE_SEEDS,
    AcceptanceRuleResult,
    aggregate_decision,
    build_readiness_manifest,
    evaluate_readiness,
)


ROOT = Path(__file__).resolve().parents[2]


def _rule(status: str, classification: str) -> AcceptanceRuleResult:
    return AcceptanceRuleResult(
        rule_id=f"test-{status}-{classification}",
        expected=True,
        observed=status == "pass",
        status=status,
        failure_classification=classification,
        evidence=("fixture",),
    )


class V2AcceptanceReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = evaluate_readiness(ROOT)
        cls.manifest = build_readiness_manifest(ROOT)

    def test_decision_precedence_is_stop_then_redesign_then_proceed(self) -> None:
        self.assertEqual(aggregate_decision(()), "redesign")
        self.assertEqual(aggregate_decision((_rule("pass", "redesign"),)), "proceed")
        self.assertEqual(aggregate_decision((_rule("fail", "redesign"),)), "redesign")
        self.assertEqual(
            aggregate_decision((_rule("fail", "redesign"), _rule("fail", "stop"))),
            "stop",
        )

    def test_rule_objects_reject_unknown_status_and_classification(self) -> None:
        with self.assertRaises(ValueError):
            AcceptanceRuleResult("rule", True, False, "unknown", "redesign", ("fixture",))
        with self.assertRaises(ValueError):
            AcceptanceRuleResult("rule", True, False, "fail", "waive", ("fixture",))

    def test_readiness_fails_closed_on_unfrozen_inputs(self) -> None:
        by_id = {item.rule_id: item for item in self.rules}
        for rule_id in (
            "READINESS-SELECTED-CANDIDATE",
            "READINESS-DRIVER-GROUPS",
            "READINESS-COEFFICIENT-REGISTRY",
            "READINESS-MATCHED-NULL-STREAMS",
            "READINESS-MATCHED-STRESS-STREAMS",
            "READINESS-SHUFFLE-DOMAIN",
            "READINESS-FOLD-SUPPORT",
        ):
            self.assertEqual(by_id[rule_id].status, "fail")
            self.assertEqual(by_id[rule_id].failure_classification, "redesign")

    def test_dual_time_audit_detects_post_cutoff_ingestion_leakage(self) -> None:
        rule = next(item for item in self.rules if item.rule_id == "READINESS-DUAL-TIME-VISIBILITY")
        self.assertEqual(rule.status, "fail")
        self.assertEqual(rule.failure_classification, "stop")
        self.assertGreater(rule.observed["post_cutoff_ingestion_behavior_events"], 0)
        self.assertGreater(rule.observed["observations_with_post_cutoff_ingestion_features"], 0)

    def test_final_holdout_absence_passes(self) -> None:
        rule = next(item for item in self.rules if item.rule_id == "READINESS-HOLDOUT-ABSENCE")
        self.assertEqual(rule.status, "pass")
        self.assertEqual(set(rule.observed.values()), {FINAL_HOLDOUT_STATUS})
        self.assertEqual(self.manifest["final_holdout_status"], FINAL_HOLDOUT_STATUS)

    def test_manifest_accounts_for_every_seed_and_fold_without_running(self) -> None:
        runs = self.manifest["planned_replications"]
        self.assertEqual(tuple(item["seed"] for item in runs), R2_ACCEPTANCE_SEEDS)
        for item in runs:
            self.assertEqual(item["signal_status"], NOT_RUN_STATUS)
            self.assertEqual(item["null_status"], NOT_RUN_STATUS)
            self.assertEqual(tuple(fold["name"] for fold in item["folds"]), R2_ACCEPTANCE_FOLDS)
            self.assertTrue(all(fold["status"] == NOT_RUN_STATUS for fold in item["folds"]))

    def test_manifest_records_stop_without_result_generation(self) -> None:
        self.assertEqual(self.manifest["decision"], "stop")
        self.assertFalse(self.manifest["acceptance_results_generated"])
        self.assertFalse(self.manifest["model_fit_performed"])
        self.assertFalse(self.manifest["prediction_performed"])
        self.assertFalse(self.manifest["bootstrap_performed"])
        self.assertEqual(self.manifest["downstream_status"], {"P2-08": "paused", "P2-09": "paused"})

    def test_lineage_is_complete_and_digest_shaped(self) -> None:
        lineage = self.manifest["lineage"]
        self.assertGreaterEqual(len(lineage), 10)
        for path, digest in lineage.items():
            self.assertTrue((ROOT / path).is_file())
            self.assertEqual(len(digest), 64)
            int(digest, 16)

    def test_manifest_contains_no_row_level_or_fitted_payloads(self) -> None:
        prohibited = {
            "histories",
            "raw_observations",
            "oracle_sidecar",
            "predictions",
            "matrix_values",
            "targets",
            "safe_fitted_state",
            "final_holdout_seed",
            "final_holdout_membership",
        }

        def visit(value):
            if isinstance(value, dict):
                self.assertFalse(prohibited & set(value))
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(self.manifest)


if __name__ == "__main__":
    unittest.main()
