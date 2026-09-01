from __future__ import annotations

import unittest
from copy import deepcopy
from pathlib import Path

from inforsight_simulator.v3_1_config import V31CorpusConfig
from inforsight_simulator.v3_acceptance import (
    R2_V3_ACCEPTANCE_SEEDS, RuleResult, aggregate_decision, average_precision,
    bootstrap_policy_indices, brier_score, build_readiness_manifest, evaluate_readiness,
    evaluate_readiness_payloads, fit_authorized_candidates, percentile_interval,
    policy_cluster_interval, policy_label_shuffle, roc_auc,
)
from inforsight_simulator.v3_evaluation import (
    V3Matrix, V3Preprocessor,
)

ROOT = Path(__file__).resolve().parents[2]


def rule(status: str, classification: str) -> RuleResult:
    return RuleResult("R", "fixture", "unit", {}, "eq", True, True, status,
                      classification, ("0" * 64,))


class V3AcceptanceTests(unittest.TestCase):
    def test_inventory_and_decision_precedence(self) -> None:
        self.assertEqual(R2_V3_ACCEPTANCE_SEEDS, tuple(range(20261001, 20261021)))
        self.assertEqual(aggregate_decision(()), "redesign")
        self.assertEqual(aggregate_decision((rule("pass", "redesign"),)), "proceed")
        self.assertEqual(aggregate_decision((rule("fail", "redesign"),)), "redesign")
        self.assertEqual(aggregate_decision((rule("fail", "redesign"),
                                             rule("fail", "stop"))), "stop")

    def test_metrics_cover_ties_and_perfect_ordering(self) -> None:
        self.assertEqual(roc_auc((0, 1), (0.1, 0.9)), 1.0)
        self.assertEqual(roc_auc((0, 1), (0.5, 0.5)), 0.5)
        self.assertAlmostEqual(brier_score((0, 1), (0.25, 0.75)), 0.0625)
        self.assertEqual(average_precision((0, 1), (0.1, 0.9)), 1.0)

    def test_percentile_indices_follow_contract(self) -> None:
        values = tuple(float(value) for value in range(1000))
        self.assertEqual(percentile_interval(values), (24.0, 975.0))

    def test_bootstrap_is_deterministic_and_policy_clustered(self) -> None:
        config = V31CorpusConfig()
        first = bootstrap_policy_indices(config, seed=20261001, fold="fold_1",
                                         metric="auc", replicate=0,
                                         policy_ids=("b", "a", "a", "c"))
        second = bootstrap_policy_indices(config, seed=20261001, fold="fold_1",
                                          metric="auc", replicate=0,
                                          policy_ids=("c", "b", "a"))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        self.assertTrue(all(0 <= value < 3 for value in first))
        interval, valid = policy_cluster_interval(
            config, seed=20261001, fold="fold_1", metric="roc_auc",
            policy_ids=("a", "a", "b", "b", "c", "c", "d", "d"),
            targets=(0, 0, 0, 0, 1, 1, 1, 1),
            probabilities=(0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9),
            replicates=25,
        )
        self.assertGreater(valid, 0)
        self.assertLessEqual(interval[0], interval[1])

    def test_policy_shuffle_is_deterministic_and_preserves_row_count(self) -> None:
        config = V31CorpusConfig()
        policy_ids = ("a", "a", "b", "b", "c", "c", "d", "d")
        targets = (0, 1, 1, 1, 0, 0, 1, 0)
        first = policy_label_shuffle(
            config, seed=20261001, fold="fold_1", policy_ids=policy_ids,
            targets=targets,
        )
        second = policy_label_shuffle(
            config, seed=20261001, fold="fold_1", policy_ids=policy_ids,
            targets=targets,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(targets))

    def test_invalid_metric_payloads_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            roc_auc((1, 1), (0.2, 0.8))
        with self.assertRaises(ValueError):
            brier_score((0,), (float("nan"),))

    def test_merged_r2_10_evidence_passes_readiness(self) -> None:
        rules = evaluate_readiness(ROOT)
        self.assertGreaterEqual(len(rules), 8)
        self.assertEqual(aggregate_decision(rules), "proceed")
        self.assertTrue(all(item.status == "pass" for item in rules))
        manifest = build_readiness_manifest(ROOT)
        self.assertEqual(manifest["readiness_status"], "pass")
        self.assertTrue(manifest["result_producing_execution_authorized"])
        self.assertFalse(manifest["acceptance_results_generated"])
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")

    def test_identity_and_holdout_mutations_are_stop_conditions(self) -> None:
        import json, hashlib
        names = {
            "support": "phase-02r-10-v3-structural-support-3.2.0.json",
            "split": "phase-02r-10-v3-split-manifest-3.2.0.json",
            "feature": "phase-02r-10-v3-feature-pipeline-manifest-3.2.0.json",
            "diagnostic": "phase-02r-10-v3-feature-diagnostics-manifest-3.2.0.json",
            "candidate": "phase-02r-10-v3-candidate-selection-manifest-3.2.0.json",
        }
        payloads, digests = {}, {}
        for key, name in names.items():
            raw = (ROOT / "docs/experiments" / name).read_bytes()
            payloads[key], digests[key] = json.loads(raw), hashlib.sha256(raw).hexdigest()
        changed = deepcopy(payloads)
        changed["candidate"]["artifact_id"] = "0" * 64
        rules = {item.rule_id: item for item in evaluate_readiness_payloads(changed, digests)}
        self.assertEqual(rules["READINESS-ARTIFACT-IDENTITY"].status, "fail")
        self.assertEqual(rules["READINESS-ARTIFACT-IDENTITY"].failure_classification, "stop")
        changed = deepcopy(payloads)
        changed["support"]["final_holdout_status"] = "materialized"
        rules = {item.rule_id: item for item in evaluate_readiness_payloads(changed, digests)}
        self.assertEqual(rules["READINESS-FINAL-HOLDOUT"].status, "fail")

    def test_committed_redesign_evidence_is_complete_and_bounded(self) -> None:
        import json
        path = ROOT / "docs/experiments/phase-02r-11-v3-statistical-acceptance-manifest.json"
        manifest = json.loads(path.read_text())
        self.assertEqual(manifest["decision"], "redesign")
        self.assertEqual(manifest["readiness"]["passing_seed_pairs"], 20)
        self.assertEqual(len(manifest["primary_seed_evidence"]), 20)
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")
        self.assertEqual(manifest["failed_stop_rules"], [])
        by_id = {item["rule_id"]: item for item in manifest["rules"]}
        self.assertEqual(by_id["SIGNAL-SEED-AUC-PASSCOUNT"]["observed"], 0)
        self.assertEqual(by_id["SIGNAL-MEDIAN-AUC"]["status"], "fail")
        rendered = path.read_text()
        for prohibited in ("safe_fitted_state", "matrix_values",
                           "final_holdout_seed", "bootstrap_samples\": ["):
            self.assertNotIn(prohibited, rendered)
        self.assertEqual(manifest["materialization"]["oracle_sidecars"], "not_accessed")

    def test_frozen_candidate_scores_only_authorized_acceptance_matrix(self) -> None:
        artifact = "a" * 64
        feature_names = ("x1", "x2")
        fit_ids = tuple(f"fit-{index}" for index in range(20))
        fitted = V3Preprocessor(
            "3.0.0", "fold_1", artifact, fit_ids, (), (), feature_names,
        )
        train = V3Matrix(
            "fit", "fold_1", "fit", artifact, fit_ids,
            tuple(f"fit-policy-{index}" for index in range(20)),
            tuple(f"fit-episode-{index}" for index in range(20)), feature_names,
            tuple((float(index % 2), float(index) / 20) for index in range(20)),
            tuple(index % 2 for index in range(20)),
        )
        acceptance = V3Matrix(
            "acceptance", "fold_1", "acceptance", artifact,
            tuple(f"accept-{index}" for index in range(10)),
            tuple(f"accept-policy-{index}" for index in range(10)),
            tuple(f"accept-episode-{index}" for index in range(10)), feature_names,
            tuple((float(index % 2), float(index) / 10) for index in range(10)),
            tuple(index % 2 for index in range(10)),
        )
        results = fit_authorized_candidates(train, acceptance, fitted)
        self.assertEqual(tuple(item.candidate for item in results), ("logistic", "xgboost"))
        self.assertTrue(all(len(item.probabilities) == len(acceptance.targets)
                            for item in results))
        self.assertTrue(all(len(item.authorization_sha256) == 64 for item in results))
        selection_labeled = type(acceptance)(
            "selection", acceptance.fold, acceptance.role, acceptance.artifact_id,
            acceptance.observation_ids, acceptance.policy_ids, acceptance.episode_ids,
            acceptance.feature_names, acceptance.values, acceptance.targets,
        )
        with self.assertRaisesRegex(ValueError, "requires an acceptance matrix"):
            fit_authorized_candidates(train, selection_labeled, fitted)


if __name__ == "__main__":
    unittest.main()
