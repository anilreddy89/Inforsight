"""Focused tests for the R2-03 scoring-authorization boundary."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "simulator" / "src"))

from inforsight_simulator import (  # noqa: E402
    CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
    LABEL_HORIZON_DAYS,
    SCORING_AUTHORIZATION_VERSION,
    assign_temporal_splits,
    authorize_diagnostic_derivative,
    authorize_feature_pipeline,
    build_feature_pipeline,
    build_first_billing_observations,
    first_billing_observation_time,
    fit_boosted_model,
    fit_logistic_baseline,
    generate_legacy_policy_histories,
    inference_matrix_from_model_matrix,
    predict_boosted_inference,
    predict_boosted_probabilities,
    predict_logistic_inference,
    predict_positive_probabilities,
    validate_scoring_authorization,
)


class ScoringAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        histories = generate_legacy_policy_histories(20260817, 100)
        cutoffs = [first_billing_observation_time(history) for history in histories]
        watermark = max(value + timedelta(days=LABEL_HORIZON_DAYS) for value in cutoffs)
        records = build_first_billing_observations(histories, follow_up_through=watermark)
        split = assign_temporal_splits(records, CANONICAL_TEMPORAL_SPLIT_SPECIFICATION)
        cls.pipeline = build_feature_pipeline(split)
        cls.authorizations = authorize_feature_pipeline(cls.pipeline)
        cls.logistic = fit_logistic_baseline(cls.pipeline.train)
        cls.boosted = fit_boosted_model(cls.pipeline.train)

    def test_authorization_is_versioned_and_binds_exact_matrices(self) -> None:
        self.assertEqual(
            self.authorizations.validation.contract_version,
            SCORING_AUTHORIZATION_VERSION,
        )
        validate_scoring_authorization(
            self.authorizations.train, self.pipeline.train
        )
        validate_scoring_authorization(
            self.authorizations.validation, self.pipeline.validation
        )

    def test_relabeling_test_as_validation_is_rejected_before_logistic_prediction(self) -> None:
        relabeled = replace(self.pipeline.test, partition="validation")
        with patch("inforsight_simulator.modeling._sigmoid") as predictor:
            with self.assertRaisesRegex(ValueError, "membership|digest"):
                predict_positive_probabilities(
                    self.logistic, relabeled, self.authorizations.validation
                )
            predictor.assert_not_called()

    def test_relabeling_test_as_validation_is_rejected_before_booster_restore(self) -> None:
        relabeled = replace(self.pipeline.test, partition="validation")
        with patch("inforsight_simulator.boosted_modeling._restore_booster") as restore:
            with self.assertRaisesRegex(ValueError, "membership|digest"):
                predict_boosted_probabilities(
                    self.boosted, relabeled, self.authorizations.validation
                )
            restore.assert_not_called()

    def test_row_id_target_and_feature_mutations_fail_closed(self) -> None:
        matrix = self.pipeline.validation
        mutations = (
            replace(matrix, observation_ids=matrix.observation_ids[::-1]),
            replace(matrix, values=matrix.values[::-1], targets=matrix.targets[::-1]),
            replace(matrix, targets=(1 - matrix.targets[0],) + matrix.targets[1:]),
            replace(matrix, feature_names=matrix.feature_names[::-1]),
            replace(
                matrix,
                values=((matrix.values[0][0] + 1.0,) + matrix.values[0][1:],)
                + matrix.values[1:],
            ),
        )
        for changed in mutations:
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    validate_scoring_authorization(
                        self.authorizations.validation, changed
                    )

    def test_authorization_integrity_and_version_mutations_fail(self) -> None:
        for changed in (
            replace(self.authorizations.validation, authorization_sha256="0" * 64),
            replace(self.authorizations.validation, contract_version="999.0.0"),
            replace(self.authorizations.validation, purpose="final_holdout"),
            replace(self.authorizations.validation, preprocessor_sha256="0" * 64),
            replace(self.authorizations.validation, training_matrix_sha256="0" * 64),
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    validate_scoring_authorization(changed, self.pipeline.validation)

    def test_train_and_validation_authorizations_cannot_be_mixed(self) -> None:
        with self.assertRaisesRegex(ValueError, "partition"):
            validate_scoring_authorization(
                self.authorizations.train, self.pipeline.validation
            )

    def test_authorization_builder_rejects_replaced_pipeline_field(self) -> None:
        relabeled_test = replace(self.pipeline.test, partition="validation")
        changed = replace(self.pipeline, validation=relabeled_test)
        with self.assertRaisesRegex(ValueError, "membership"):
            authorize_feature_pipeline(changed)

    def test_diagnostic_derivative_binds_base_and_transformation(self) -> None:
        matrix = self.pipeline.validation
        changed = replace(
            matrix,
            values=(matrix.values[1], matrix.values[0]) + matrix.values[2:],
        )
        derivative = authorize_diagnostic_derivative(
            self.authorizations.validation,
            matrix,
            changed,
            transformation={"kind": "test_permutation", "seed": 7},
        )
        validate_scoring_authorization(derivative, changed)
        with self.assertRaisesRegex(ValueError, "digest"):
            validate_scoring_authorization(derivative, matrix)

    def test_diagnostic_derivative_cannot_change_membership_features_or_targets(self) -> None:
        matrix = self.pipeline.validation
        for changed in (
            replace(matrix, observation_ids=matrix.observation_ids[::-1]),
            replace(matrix, feature_names=matrix.feature_names[::-1]),
            replace(matrix, targets=(1 - matrix.targets[0],) + matrix.targets[1:]),
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    authorize_diagnostic_derivative(
                        self.authorizations.validation,
                        matrix,
                        changed,
                        transformation={"kind": "invalid"},
                    )

    def test_unlabeled_inference_has_no_partition_targets_or_metrics(self) -> None:
        inference = inference_matrix_from_model_matrix(self.pipeline.validation)
        self.assertFalse(hasattr(inference, "partition"))
        self.assertFalse(hasattr(inference, "targets"))
        logistic = predict_logistic_inference(self.logistic, inference)
        boosted = predict_boosted_inference(self.boosted, inference)
        self.assertEqual(len(logistic), len(inference.values))
        self.assertEqual(len(boosted), len(inference.values))


if __name__ == "__main__":
    unittest.main()
