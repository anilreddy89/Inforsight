"""Focused tests for the Phase 2.06 frozen boosted-model comparison."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "simulator" / "src"))
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "train_boosted_comparison.py"

from inforsight_simulator import (  # noqa: E402
    CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
    FROZEN_BOOSTED_SPECIFICATION,
    FittedBoostedModel,
    LABEL_HORIZON_DAYS,
    assign_temporal_splits,
    authorize_feature_pipeline,
    build_feature_pipeline,
    build_first_billing_observations,
    compare_models,
    evaluate_boosted_model,
    first_billing_observation_time,
    fit_boosted_model,
    fit_logistic_baseline,
    fitted_boosted_bytes,
    generate_legacy_policy_histories,
    predict_boosted_probabilities,
)


def _load_artifact_module():
    spec = importlib.util.spec_from_file_location("train_boosted_comparison", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BoostedComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        histories = generate_legacy_policy_histories(20260817, 100)
        cutoffs = [first_billing_observation_time(history) for history in histories]
        watermark = max(value + timedelta(days=LABEL_HORIZON_DAYS) for value in cutoffs)
        records = build_first_billing_observations(histories, follow_up_through=watermark)
        split = assign_temporal_splits(records, CANONICAL_TEMPORAL_SPLIT_SPECIFICATION)
        cls.pipeline = build_feature_pipeline(split)
        cls.authorizations = authorize_feature_pipeline(cls.pipeline)

    def test_frozen_fit_is_deterministic(self) -> None:
        first = fit_boosted_model(self.pipeline.train)
        second = fit_boosted_model(self.pipeline.train)
        self.assertEqual(fitted_boosted_bytes(first), fitted_boosted_bytes(second))
        self.assertEqual(
            predict_boosted_probabilities(first, self.pipeline.validation, self.authorizations.validation),
            predict_boosted_probabilities(second, self.pipeline.validation, self.authorizations.validation),
        )

    def test_fit_records_exact_training_provenance(self) -> None:
        fitted = fit_boosted_model(self.pipeline.train)
        self.assertEqual(fitted.training_observation_ids, self.pipeline.train.observation_ids)
        self.assertEqual(fitted.feature_names, self.pipeline.train.feature_names)
        self.assertEqual(fitted.trained_tree_count, FROZEN_BOOSTED_SPECIFICATION.n_estimators)

    def test_non_train_fit_and_specification_mutation_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected train"):
            fit_boosted_model(self.pipeline.validation)
        with self.assertRaisesRegex(ValueError, "not the frozen"):
            fit_boosted_model(
                self.pipeline.train,
                replace(FROZEN_BOOSTED_SPECIFICATION, max_depth=3),
            )

    def test_test_scoring_is_rejected(self) -> None:
        fitted = fit_boosted_model(self.pipeline.train)
        with self.assertRaisesRegex(ValueError, "partition"):
            predict_boosted_probabilities(
                fitted, self.pipeline.test, self.authorizations.validation
            )

    def test_safe_state_round_trip_reproduces_probabilities(self) -> None:
        fitted = fit_boosted_model(self.pipeline.train)
        restored = FittedBoostedModel.from_dict(fitted.to_dict())
        self.assertEqual(fitted_boosted_bytes(fitted), fitted_boosted_bytes(restored))
        self.assertEqual(
            predict_boosted_probabilities(fitted, self.pipeline.validation, self.authorizations.validation),
            predict_boosted_probabilities(restored, self.pipeline.validation, self.authorizations.validation),
        )

    def test_malformed_and_incomplete_state_are_rejected(self) -> None:
        fitted = fit_boosted_model(self.pipeline.train)
        with self.assertRaisesRegex(ValueError, "digest"):
            FittedBoostedModel.from_dict({**fitted.to_dict(), "model_json_sha256": "0" * 64})
        with self.assertRaisesRegex(ValueError, "training evidence"):
            FittedBoostedModel.from_dict({**fitted.to_dict(), "trained_tree_count": 24})

    def test_matrix_compatibility_fails_closed(self) -> None:
        fitted = fit_boosted_model(self.pipeline.train)
        with self.assertRaisesRegex(ValueError, "feature contract"):
            predict_boosted_probabilities(
                fitted,
                replace(self.pipeline.validation, feature_names=self.pipeline.validation.feature_names[::-1]),
                self.authorizations.validation,
            )
        with self.assertRaisesRegex(ValueError, "membership or row order"):
            predict_boosted_probabilities(
                fitted,
                replace(self.pipeline.train, observation_ids=self.pipeline.train.observation_ids[::-1]),
                self.authorizations.train,
            )

    def test_comparison_uses_identical_membership_and_metrics(self) -> None:
        logistic = fit_logistic_baseline(self.pipeline.train)
        boosted = fit_boosted_model(self.pipeline.train)
        comparison = compare_models(
            logistic, boosted, self.pipeline.validation, self.authorizations.validation
        )
        self.assertEqual(comparison["observation_ids"], list(self.pipeline.validation.observation_ids))
        self.assertEqual(
            set(comparison["logistic_regression"]["metrics"]),
            set(comparison["xgboost"]["metrics"]),
        )
        self.assertEqual(
            comparison["logistic_regression"]["metrics"]["record_count"],
            comparison["xgboost"]["metrics"]["record_count"],
        )

    def test_validation_scoring_does_not_mutate_state(self) -> None:
        fitted = fit_boosted_model(self.pipeline.train)
        before = fitted_boosted_bytes(fitted)
        evaluation = evaluate_boosted_model(
            fitted, self.pipeline.validation, self.authorizations.validation
        )
        self.assertEqual(evaluation.metrics.partition, "validation")
        self.assertEqual(before, fitted_boosted_bytes(fitted))

    def test_training_mutation_changes_fitted_state(self) -> None:
        original = fit_boosted_model(self.pipeline.train)
        row = list(self.pipeline.train.values[0])
        row[0] += 2.0
        changed = replace(self.pipeline.train, values=(tuple(row),) + self.pipeline.train.values[1:])
        refit = fit_boosted_model(changed)
        self.assertNotEqual(fitted_boosted_bytes(original), fitted_boosted_bytes(refit))

    def test_artifacts_are_current_safe_and_test_sealed(self) -> None:
        module = _load_artifact_module()
        first = module.artifact_bytes()
        second = module.artifact_bytes()
        self.assertEqual(first, second)
        self.assertEqual(module.MANIFEST_PATH.read_bytes(), first[0])
        self.assertEqual(module.REPORT_PATH.read_bytes(), first[1])
        manifest = json.loads(first[0])
        self.assertEqual(manifest["test_partition_status"], "sealed_not_scored")
        self.assertEqual(set(manifest["comparison"]), {"train", "validation"})
        serialized = first[0].decode("utf-8")
        self.assertNotIn('"values"', serialized)
        self.assertNotIn('"targets"', serialized)

    def test_phase_02_05_artifacts_are_not_rewritten(self) -> None:
        module = _load_artifact_module()
        before = (module.LOGISTIC_MANIFEST_PATH.read_bytes(), module.LOGISTIC_REPORT_PATH.read_bytes())
        module.artifact_bytes()
        after = (module.LOGISTIC_MANIFEST_PATH.read_bytes(), module.LOGISTIC_REPORT_PATH.read_bytes())
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
