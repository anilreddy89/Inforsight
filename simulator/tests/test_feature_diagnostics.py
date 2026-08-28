"""Focused tests for Phase 2.07 feature-sanity diagnostics."""

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
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "run_feature_diagnostics.py"

from inforsight_simulator import (  # noqa: E402
    CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
    FROZEN_DIAGNOSTIC_SPECIFICATION,
    LABEL_HORIZON_DAYS,
    assign_temporal_splits,
    authorize_feature_pipeline,
    build_feature_pipeline,
    build_first_billing_observations,
    diagnostic_flags,
    first_billing_observation_time,
    fit_boosted_model,
    fit_logistic_baseline,
    fitted_baseline_bytes,
    fitted_boosted_bytes,
    fitted_state_bytes,
    generate_legacy_policy_histories,
    identifier_and_cardinality_checks,
    identifier_token_matches,
    perturbation_flags,
    shallow_feature_models,
    source_feature_groups,
    targeted_permutation_checks,
    training_mutual_information,
    validate_dispositions,
)


def _load_artifact_module():
    spec = importlib.util.spec_from_file_location("run_feature_diagnostics", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FeatureDiagnosticTests(unittest.TestCase):
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

    def test_source_grouping_is_complete_and_groups_one_hot_outputs(self) -> None:
        groups = dict(source_feature_groups(self.pipeline.train))
        self.assertEqual(set(groups), {
            "premium_amount_cents", "policy_age_days", "visible_event_count",
            "visible_billing_count", "visible_failed_payment_count",
            "visible_received_payment_count", "visible_notice_count",
            "visible_service_contact_count", "product_variant", "billing_frequency",
        })
        self.assertGreater(len(groups["product_variant"]), 1)
        names = tuple(self.pipeline.train.feature_names[index] for index in groups["billing_frequency"])
        self.assertTrue(any(name.endswith("=__unknown__") for name in names))

    def test_test_and_unknown_partitions_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "sealed or unsupported"):
            training_mutual_information(self.pipeline.test, self.authorizations.validation)
        with self.assertRaisesRegex(ValueError, "sealed or unsupported"):
            source_feature_groups(replace(self.pipeline.validation, partition="embargoed"))

    def test_mutual_information_is_train_only_and_deterministic(self) -> None:
        first = training_mutual_information(self.pipeline.train, self.authorizations.train)
        second = training_mutual_information(self.pipeline.train, self.authorizations.train)
        self.assertEqual(first, second)
        self.assertEqual({item["source_feature"] for item in first}, set(dict(source_feature_groups(self.pipeline.train))))

    def test_mutated_diagnostic_specification_is_rejected(self) -> None:
        changed = replace(FROZEN_DIAGNOSTIC_SPECIFICATION, random_seed=1)
        with self.assertRaisesRegex(ValueError, "not frozen"):
            training_mutual_information(
                self.pipeline.train, self.authorizations.train, changed
            )

    def test_shallow_models_fit_train_and_score_validation(self) -> None:
        results = shallow_feature_models(
            self.pipeline.train,
            self.pipeline.validation,
            self.authorizations.train,
            self.authorizations.validation,
        )
        self.assertTrue(results)
        self.assertTrue(all(item["fit_partition"] == "train" for item in results))
        self.assertTrue(all(item["score_partition"] == "validation" for item in results))
        self.assertTrue(all(item["metrics"]["record_count"] == len(self.pipeline.validation.targets) for item in results))

    def test_feature_order_drift_is_rejected(self) -> None:
        changed = replace(self.pipeline.validation, feature_names=self.pipeline.validation.feature_names[::-1])
        with self.assertRaisesRegex(ValueError, "frozen feature names"):
            shallow_feature_models(
                self.pipeline.train,
                changed,
                self.authorizations.train,
                self.authorizations.validation,
            )

    def test_cardinality_checks_detect_canonical_constants(self) -> None:
        checks = {
            item["source_feature"]: item
            for item in identifier_and_cardinality_checks(
                self.pipeline.train,
                self.pipeline.validation,
                self.authorizations.train,
                self.authorizations.validation,
            )
        }
        self.assertTrue(checks["policy_age_days"]["constant_in_train"])
        self.assertTrue(checks["billing_frequency"]["constant_in_train"])
        self.assertFalse(checks["premium_amount_cents"]["constant_in_train"])
        self.assertEqual(checks["premium_amount_cents"]["identifier_token_matches"], [])

    def test_identifier_tokens_detect_ids_without_flagging_policy_age(self) -> None:
        self.assertEqual(identifier_token_matches("policy_age_days"), ())
        self.assertEqual(identifier_token_matches("customer_id"), ("customer", "id"))
        self.assertEqual(identifier_token_matches("scenario_key"), ("key", "scenario"))

    def test_flags_are_source_level_and_deterministic(self) -> None:
        mi = training_mutual_information(self.pipeline.train, self.authorizations.train)
        shallow = shallow_feature_models(
            self.pipeline.train,
            self.pipeline.validation,
            self.authorizations.train,
            self.authorizations.validation,
        )
        cardinality = identifier_and_cardinality_checks(
            self.pipeline.train,
            self.pipeline.validation,
            self.authorizations.train,
            self.authorizations.validation,
        )
        first = diagnostic_flags(mi, shallow, cardinality)
        second = diagnostic_flags(mi, shallow, cardinality)
        self.assertEqual(first, second)
        self.assertTrue(all("=" not in flag["source_feature"] for flag in first))
        self.assertIn("billing_frequency:constant", {flag["flag_id"] for flag in first})

    def test_targeted_permutation_is_deterministic_and_does_not_mutate_state(self) -> None:
        before = (
            fitted_state_bytes(self.pipeline.preprocessor),
            fitted_baseline_bytes(self.logistic),
            fitted_boosted_bytes(self.boosted),
            self.pipeline.validation,
        )
        sources = ("billing_frequency", "policy_age_days")
        first = targeted_permutation_checks(
            self.logistic,
            self.boosted,
            self.pipeline.validation,
            self.authorizations.validation,
            sources,
        )
        second = targeted_permutation_checks(
            self.logistic,
            self.boosted,
            self.pipeline.validation,
            self.authorizations.validation,
            sources,
        )
        self.assertEqual(first, second)
        self.assertEqual(before, (
            fitted_state_bytes(self.pipeline.preprocessor),
            fitted_baseline_bytes(self.logistic),
            fitted_boosted_bytes(self.boosted),
            self.pipeline.validation,
        ))

    def test_unknown_and_duplicate_permutation_targets_are_rejected(self) -> None:
        for sources in (("not_a_feature",), ("policy_age_days", "policy_age_days")):
            with self.assertRaisesRegex(ValueError, "duplicated or unknown"):
                targeted_permutation_checks(
                    self.logistic,
                    self.boosted,
                    self.pipeline.validation,
                    self.authorizations.validation,
                    sources,
                )

    def test_dispositions_must_be_complete_and_valid(self) -> None:
        flags = ({"flag_id": "policy_age_days:constant", "source_feature": "policy_age_days", "rule": "constant"},)
        complete = {
            "policy_age_days": {
                "decision": "allow", "rationale": "Cutoff-visible constant.",
                "owner": "maintainer", "decision_date": "2026-08-20", "follow_up": "Retain tests.",
            }
        }
        self.assertEqual(validate_dispositions(flags, complete)[0]["decision"], "allow")
        with self.assertRaisesRegex(ValueError, "complete set"):
            validate_dispositions(flags, {})
        invalid = {"policy_age_days": {**complete["policy_age_days"], "decision": "ignore"}}
        with self.assertRaisesRegex(ValueError, "invalid disposition"):
            validate_dispositions(flags, invalid)

    def test_perturbation_flags_apply_frozen_materiality_rules(self) -> None:
        result = ({
            "source_feature": "policy_age_days",
            "models": {
                "logistic_regression": {"delta_log_loss": 0.11, "delta_roc_auc": 0.0},
                "xgboost": {"delta_log_loss": 0.0, "delta_roc_auc": -0.11},
            },
        },)
        rules = {flag["rule"] for flag in perturbation_flags(result)}
        self.assertEqual(rules, {"material_permutation_log_loss:logistic_regression", "material_permutation_auc:xgboost"})

    def test_artifacts_are_current_deterministic_and_keep_test_sealed(self) -> None:
        module = _load_artifact_module()
        first = module.artifact_bytes()
        second = module.artifact_bytes()
        self.assertEqual(first, second)
        self.assertEqual(module.MANIFEST_PATH.read_bytes(), first[0])
        self.assertEqual(module.REPORT_PATH.read_bytes(), first[1])
        manifest = module.build_diagnostics()
        self.assertEqual(manifest["test_partition_status"], "sealed_not_scored")
        self.assertEqual(set(manifest["source"]["input_matrices"]), {"train", "validation"})
        self.assertTrue(manifest["integrity"]["upstream_artifacts_unchanged"])
        serialized = json.dumps(manifest)
        self.assertNotIn('"values"', serialized)
        self.assertNotIn('"targets"', serialized)


if __name__ == "__main__":
    unittest.main()
