"""Tests for Phase 2.04 versioned feature construction and preprocessing."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import timedelta
import importlib.util
from pathlib import Path
import random
import sys
import unittest


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator import (
    FEATURE_DEFINITIONS,
    FEATURE_DICTIONARY_VERSION,
    FEATURE_PIPELINE_VERSION,
    LABEL_HORIZON_DAYS,
    UNKNOWN_CATEGORY,
    assign_temporal_splits,
    build_feature_pipeline,
    build_first_billing_observations,
    extract_feature_row,
    feature_dictionary,
    first_billing_observation_time,
    fit_preprocessor,
    fitted_state_bytes,
    generate_legacy_policy_histories,
    matrix_digest,
    transform_partition,
    validate_feature_dictionary,
)
from inforsight_simulator.leakage import ALLOWED_FEATURE_KEYS


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "build_feature_pipeline.py"


def _load_artifact_module():
    spec = importlib.util.spec_from_file_location("build_feature_pipeline", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FeaturePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        histories = generate_legacy_policy_histories(seed=20260817, policy_count=100)
        cutoffs = [first_billing_observation_time(history) for history in histories]
        watermark = max(cutoff + timedelta(days=LABEL_HORIZON_DAYS) for cutoff in cutoffs)
        records = build_first_billing_observations(histories, follow_up_through=watermark)
        cls.split = assign_temporal_splits(records)
        cls.pipeline = build_feature_pipeline(cls.split)

    def test_dictionary_exactly_matches_guarded_feature_surface(self) -> None:
        validate_feature_dictionary()
        self.assertEqual(
            {definition.source_name for definition in FEATURE_DEFINITIONS},
            set(ALLOWED_FEATURE_KEYS),
        )
        material = feature_dictionary()
        self.assertEqual(material["feature_dictionary_version"], FEATURE_DICTIONARY_VERSION)
        self.assertEqual(material["feature_pipeline_version"], FEATURE_PIPELINE_VERSION)
        self.assertEqual(len(material["features"]), 12)

    def test_constant_fields_have_explicit_exclusion_decisions(self) -> None:
        decisions = {definition.source_name: definition for definition in FEATURE_DEFINITIONS}
        self.assertFalse(decisions["current_status"].included)
        self.assertFalse(decisions["currency"].included)
        self.assertIn("constant", decisions["current_status"].decision_rationale)
        self.assertIn("constant", decisions["currency"].decision_rationale)

    def test_fit_uses_exactly_frozen_training_ids(self) -> None:
        expected = tuple(record.observation_id for record in self.split.train)
        self.assertEqual(self.pipeline.preprocessor.training_observation_ids, expected)
        self.assertEqual(
            dict(self.pipeline.preprocessor.partition_observation_ids)["train"], expected
        )

    def test_output_excludes_prohibited_and_audit_fields(self) -> None:
        names = self.pipeline.preprocessor.output_feature_names
        prohibited = (
            "policy_id", "observation_id", "label", "outcome", "as_of",
            "visible_event_ids", "partition", "scenario", "generator",
        )
        for concept in prohibited:
            self.assertFalse(any(concept in name for name in names), concept)
        self.assertNotIn("current_status", names)
        self.assertNotIn("currency", names)

    def test_output_shapes_names_and_targets_are_consistent(self) -> None:
        for name, expected_rows in (("train", 26), ("validation", 27), ("test", 25)):
            matrix = getattr(self.pipeline, name)
            self.assertEqual(len(matrix.values), expected_rows)
            self.assertEqual(len(matrix.observation_ids), expected_rows)
            self.assertEqual(len(matrix.targets), expected_rows)
            self.assertTrue(all(len(row) == len(matrix.feature_names) for row in matrix.values))
            self.assertEqual(matrix.feature_names, self.pipeline.preprocessor.output_feature_names)
            self.assertTrue(set(matrix.targets).issubset({0, 1}))

    def test_unseen_held_out_billing_values_use_unknown_column(self) -> None:
        names = self.pipeline.preprocessor.output_feature_names
        unknown_index = names.index(f"billing_frequency={UNKNOWN_CATEGORY}")
        monthly_index = names.index("billing_frequency=monthly")
        self.assertTrue(all(row[monthly_index] == 1.0 for row in self.pipeline.train.values))
        self.assertTrue(all(row[unknown_index] == 0.0 for row in self.pipeline.train.values))
        for matrix in (self.pipeline.validation, self.pipeline.test):
            self.assertTrue(all(row[monthly_index] == 0.0 for row in matrix.values))
            self.assertTrue(all(row[unknown_index] == 1.0 for row in matrix.values))

    def test_held_out_transform_does_not_mutate_fitted_state(self) -> None:
        fitted = self.pipeline.preprocessor
        before = fitted_state_bytes(fitted)
        transform_partition(fitted, self.split.validation, "validation")
        transform_partition(fitted, self.split.test, "test")
        self.assertEqual(fitted_state_bytes(fitted), before)

    def test_different_held_out_values_cannot_change_fit(self) -> None:
        original = fit_preprocessor(self.split)
        validation = tuple(
            replace(
                record,
                features=replace(record.features, product_variant="unseen_variant")
                if record.features is not None else None,
            )
            for record in self.split.validation
        )
        changed = replace(self.split, validation=validation)
        second = fit_preprocessor(changed)
        self.assertEqual(fitted_state_bytes(original), fitted_state_bytes(second))

    def test_training_mutation_changes_learned_numeric_state(self) -> None:
        record = self.split.train[0]
        assert record.features is not None
        changed_record = replace(
            record,
            features=replace(
                record.features,
                premium_amount_cents=record.features.premium_amount_cents + 100_000,
            ),
        )
        changed_split = replace(
            self.split,
            train=(changed_record,) + self.split.train[1:],
        )
        original = fit_preprocessor(self.split)
        changed = fit_preprocessor(changed_split)
        self.assertNotEqual(fitted_state_bytes(original), fitted_state_bytes(changed))

    def test_train_output_is_stable_after_held_out_application(self) -> None:
        fitted = self.pipeline.preprocessor
        before = transform_partition(fitted, self.split.train, "train")
        transform_partition(fitted, self.split.validation, "validation")
        transform_partition(fitted, self.split.test, "test")
        after = transform_partition(fitted, self.split.train, "train")
        self.assertEqual(before, after)
        self.assertEqual(matrix_digest(before), matrix_digest(after))

    def test_partition_membership_and_order_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "membership/order"):
            transform_partition(
                self.pipeline.preprocessor,
                reversed(self.split.validation),
                "validation",
            )
        with self.assertRaisesRegex(ValueError, "membership/order"):
            transform_partition(
                self.pipeline.preprocessor,
                self.split.embargoed,
                "validation",
            )
        with self.assertRaisesRegex(ValueError, "unsupported modeling partition"):
            transform_partition(
                self.pipeline.preprocessor,
                self.split.embargoed,
                "embargoed",
            )

    def test_missing_extra_wrong_type_and_negative_values_fail(self) -> None:
        record = self.split.train[0]
        assert record.features is not None
        base = asdict(record.features)
        cases = []
        missing = dict(base)
        missing.pop("product_variant")
        cases.append((missing, "shape mismatch"))
        extra = dict(base)
        extra["policy_id"] = "forbidden"
        cases.append((extra, "prohibited path"))
        wrong_type = dict(base)
        wrong_type["policy_age_days"] = "30"
        cases.append((wrong_type, "must be an integer"))
        negative = dict(base)
        negative["visible_event_count"] = -1
        cases.append((negative, "nonnegative"))
        null_value = dict(base)
        null_value["product_variant"] = None
        cases.append((null_value, "does not allow missing"))
        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    extract_feature_row(replace(record, features=payload))

    def test_censored_or_ineligible_record_cannot_be_extracted(self) -> None:
        record = self.split.train[0]
        with self.assertRaisesRegex(ValueError, "not modeling eligible"):
            extract_feature_row(replace(record, eligible=False, features=None))
        with self.assertRaisesRegex(ValueError, "label is not observed"):
            extract_feature_row(
                replace(record, label=replace(record.label, status="right_censored", value=None))
            )

    def test_incompatible_fitted_versions_fail(self) -> None:
        invalid = replace(self.pipeline.preprocessor, feature_pipeline_version="2.0.0")
        with self.assertRaisesRegex(ValueError, "unsupported feature pipeline"):
            transform_partition(invalid, self.split.train, "train")

    def test_explicit_fitted_state_round_trip_reproduces_matrices(self) -> None:
        fitted = self.pipeline.preprocessor
        restored = type(fitted).from_dict(fitted.to_dict())
        self.assertEqual(restored, fitted)
        for name in ("train", "validation", "test"):
            expected = getattr(self.pipeline, name)
            actual = transform_partition(restored, getattr(self.split, name), name)
            self.assertEqual(matrix_digest(actual), matrix_digest(expected))

    def test_pipeline_is_deterministic_from_reordered_source_records(self) -> None:
        records = [
            record
            for _, partition in self.split.disposition_items()
            for record in partition
        ]
        random.Random(204).shuffle(records)
        second_split = assign_temporal_splits(records)
        second = build_feature_pipeline(second_split)
        self.assertEqual(self.pipeline, second)

    def test_artifacts_are_byte_deterministic_and_current(self) -> None:
        module = _load_artifact_module()
        self.assertEqual(module.dictionary_bytes(), module.dictionary_bytes())
        self.assertEqual(module.manifest_bytes(), module.manifest_bytes())
        self.assertEqual(module.DICTIONARY_PATH.read_bytes(), module.dictionary_bytes())
        self.assertEqual(module.MANIFEST_PATH.read_bytes(), module.manifest_bytes())
        manifest = module.build_manifest()
        self.assertEqual(manifest["decision"], "pipeline_engineering_only")
        self.assertNotIn(b'"values"', module.manifest_bytes())


if __name__ == "__main__":
    unittest.main()
