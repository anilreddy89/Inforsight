"""Focused tests for the Phase 2.05 sealed-test logistic baseline."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from math import exp, isfinite
import importlib.util
import sys
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "simulator" / "src"))
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "train_logistic_baseline.py"

from inforsight_simulator import (  # noqa: E402
    CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
    FittedLogisticBaseline,
    GeneratorConfig,
    LABEL_HORIZON_DAYS,
    ModelMatrix,
    assign_temporal_splits,
    build_feature_pipeline,
    build_first_billing_observations,
    coefficient_summary,
    evaluate_logistic_baseline,
    first_billing_observation_time,
    fit_logistic_baseline,
    fitted_baseline_bytes,
    generate_policy_histories,
    predict_positive_probabilities,
)


def _load_artifact_module():
    spec = importlib.util.spec_from_file_location("train_logistic_baseline", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LogisticBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = GeneratorConfig(seed=20260817, policy_count=100)
        histories = generate_policy_histories(config.seed, config.policy_count)
        cutoffs = [first_billing_observation_time(history) for history in histories]
        watermark = max(value + timedelta(days=LABEL_HORIZON_DAYS) for value in cutoffs)
        records = build_first_billing_observations(histories, follow_up_through=watermark)
        split = assign_temporal_splits(records, CANONICAL_TEMPORAL_SPLIT_SPECIFICATION)
        cls.pipeline = build_feature_pipeline(split)

    def test_repeated_fit_is_byte_identical(self) -> None:
        first = fit_logistic_baseline(self.pipeline.train)
        second = fit_logistic_baseline(self.pipeline.train)
        self.assertEqual(fitted_baseline_bytes(first), fitted_baseline_bytes(second))
        self.assertEqual(
            predict_positive_probabilities(first, self.pipeline.validation),
            predict_positive_probabilities(second, self.pipeline.validation),
        )

    def test_fit_uses_exact_training_membership(self) -> None:
        fitted = fit_logistic_baseline(self.pipeline.train)
        self.assertEqual(fitted.training_observation_ids, self.pipeline.train.observation_ids)
        self.assertEqual(len(fitted.coefficients), len(self.pipeline.train.feature_names))

    def test_non_train_fit_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected train"):
            fit_logistic_baseline(self.pipeline.validation)

    def test_canonical_test_scoring_is_sealed(self) -> None:
        fitted = fit_logistic_baseline(self.pipeline.train)
        with self.assertRaisesRegex(ValueError, "sealed or unsupported"):
            predict_positive_probabilities(fitted, self.pipeline.test)

    def test_validation_scoring_does_not_mutate_fitted_state(self) -> None:
        fitted = fit_logistic_baseline(self.pipeline.train)
        before = fitted_baseline_bytes(fitted)
        evaluation = evaluate_logistic_baseline(fitted, self.pipeline.validation)
        self.assertEqual(before, fitted_baseline_bytes(fitted))
        self.assertEqual(evaluation.metrics.partition, "validation")

    def test_probabilities_and_metrics_are_valid(self) -> None:
        fitted = fit_logistic_baseline(self.pipeline.train)
        probabilities = predict_positive_probabilities(fitted, self.pipeline.validation)
        self.assertTrue(all(isfinite(value) and 0.0 <= value <= 1.0 for value in probabilities))
        metrics = evaluate_logistic_baseline(fitted, self.pipeline.validation).metrics
        self.assertTrue(all(isfinite(value) for value in (metrics.log_loss, metrics.roc_auc, metrics.brier_score)))
        self.assertEqual(metrics.record_count, len(self.pipeline.validation.targets))

    def test_explicit_state_round_trip_reproduces_predictions(self) -> None:
        fitted = fit_logistic_baseline(self.pipeline.train)
        restored = FittedLogisticBaseline.from_dict(fitted.to_dict())
        self.assertEqual(fitted_baseline_bytes(fitted), fitted_baseline_bytes(restored))
        self.assertEqual(
            predict_positive_probabilities(fitted, self.pipeline.validation),
            predict_positive_probabilities(restored, self.pipeline.validation),
        )

    def test_coefficient_summary_is_aligned(self) -> None:
        fitted = fit_logistic_baseline(self.pipeline.train)
        summary = coefficient_summary(fitted)
        self.assertEqual(tuple(item["feature_name"] for item in summary), fitted.feature_names)
        for item, coefficient in zip(summary, fitted.coefficients, strict=True):
            self.assertAlmostEqual(item["odds_ratio"], exp(coefficient))

    def test_one_class_training_is_rejected(self) -> None:
        matrix = replace(self.pipeline.train, targets=(0,) * len(self.pipeline.train.targets))
        with self.assertRaisesRegex(ValueError, "both binary classes"):
            fit_logistic_baseline(matrix)

    def test_non_finite_and_feature_drift_are_rejected(self) -> None:
        row = (float("nan"),) + self.pipeline.train.values[0][1:]
        bad_values = (row,) + self.pipeline.train.values[1:]
        with self.assertRaisesRegex(ValueError, "non-finite"):
            fit_logistic_baseline(replace(self.pipeline.train, values=bad_values))
        fitted = fit_logistic_baseline(self.pipeline.train)
        with self.assertRaisesRegex(ValueError, "feature names"):
            predict_positive_probabilities(
                fitted,
                replace(self.pipeline.validation, feature_names=self.pipeline.validation.feature_names[::-1]),
            )

    def test_held_out_changes_cannot_change_fitted_state(self) -> None:
        original = fit_logistic_baseline(self.pipeline.train)
        changed_validation = replace(
            self.pipeline.validation,
            values=tuple(tuple(-value for value in row) for row in self.pipeline.validation.values),
            targets=tuple(1 - value for value in self.pipeline.validation.targets),
        )
        self.assertNotEqual(self.pipeline.validation.values, changed_validation.values)
        refit = fit_logistic_baseline(self.pipeline.train)
        self.assertEqual(fitted_baseline_bytes(original), fitted_baseline_bytes(refit))

    def test_training_change_changes_fitted_state(self) -> None:
        original = fit_logistic_baseline(self.pipeline.train)
        row = list(self.pipeline.train.values[0])
        row[0] += 0.25
        changed = replace(self.pipeline.train, values=(tuple(row),) + self.pipeline.train.values[1:])
        refit = fit_logistic_baseline(changed)
        self.assertNotEqual(fitted_baseline_bytes(original), fitted_baseline_bytes(refit))

    def test_train_identity_and_digest_drift_fail_closed(self) -> None:
        fitted = fit_logistic_baseline(self.pipeline.train)
        changed_ids = replace(
            self.pipeline.train,
            observation_ids=self.pipeline.train.observation_ids[::-1],
        )
        with self.assertRaisesRegex(ValueError, "training membership"):
            predict_positive_probabilities(fitted, changed_ids)
        changed_values = replace(
            self.pipeline.train,
            values=self.pipeline.train.values[::-1],
            targets=self.pipeline.train.targets[::-1],
        )
        with self.assertRaisesRegex(ValueError, "digest"):
            predict_positive_probabilities(fitted, changed_values)

    def test_artifacts_are_deterministic_current_and_keep_test_sealed(self) -> None:
        module = _load_artifact_module()
        first_manifest, first_report = module.artifact_bytes()
        second_manifest, second_report = module.artifact_bytes()
        self.assertEqual(first_manifest, second_manifest)
        self.assertEqual(first_report, second_report)
        self.assertEqual(module.MANIFEST_PATH.read_bytes(), first_manifest)
        self.assertEqual(module.REPORT_PATH.read_bytes(), first_report)
        manifest, _ = module.build_baseline()
        self.assertEqual(manifest["test_partition_status"], "sealed_not_scored")
        self.assertEqual(set(manifest["evaluation"]), {"train", "validation"})
        self.assertEqual(set(manifest["source"]["input_matrices"]), {"train", "validation"})


if __name__ == "__main__":
    unittest.main()
