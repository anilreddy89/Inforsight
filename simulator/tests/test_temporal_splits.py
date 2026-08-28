"""Tests for Phase 2.03 policy-aware temporal splits."""

from __future__ import annotations

from dataclasses import replace
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
    CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
    LABEL_HORIZON_DAYS,
    TemporalSplitResult,
    TemporalSplitSpecification,
    assign_temporal_splits,
    build_first_billing_observations,
    first_billing_observation_time,
    generate_legacy_policy_histories,
    source_observation_digest,
    summarize_temporal_split,
    validate_temporal_split,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "build_temporal_splits.py"


def _load_manifest_module():
    spec = importlib.util.spec_from_file_location("build_temporal_splits", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TemporalSplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.histories = generate_legacy_policy_histories(seed=20260817, policy_count=100)
        cutoffs = [first_billing_observation_time(history) for history in cls.histories]
        cls.watermark = max(
            cutoff + timedelta(days=LABEL_HORIZON_DAYS) for cutoff in cutoffs
        )
        cls.records = build_first_billing_observations(
            cls.histories, follow_up_through=cls.watermark
        )
        cls.result = assign_temporal_splits(cls.records)

    def test_canonical_assignments_and_class_counts(self) -> None:
        summary = summarize_temporal_split(self.result)
        self.assertEqual(
            {name: value["observation_count"] for name, value in summary.items()},
            {
                "train": 26,
                "embargoed": 22,
                "validation": 27,
                "calendar_gap": 0,
                "test": 25,
                "excluded": 0,
            },
        )
        self.assertEqual(summary["train"]["label_value_counts"], {"0": 13, "1": 13})
        self.assertEqual(summary["validation"]["label_value_counts"], {"0": 12, "1": 15})
        self.assertEqual(summary["test"]["label_value_counts"], {"0": 11, "1": 14})

    def test_canonical_billing_frequency_confounding_is_visible(self) -> None:
        summary = summarize_temporal_split(self.result)
        self.assertEqual(summary["train"]["billing_frequency_counts"], {"monthly": 26})
        self.assertEqual(summary["embargoed"]["billing_frequency_counts"], {"quarterly": 22})
        self.assertEqual(summary["validation"]["billing_frequency_counts"], {"semiannual": 27})
        self.assertEqual(summary["test"]["billing_frequency_counts"], {"annual": 25})

    def test_assignments_are_independent_of_input_order(self) -> None:
        reordered = list(self.records)
        random.Random(17).shuffle(reordered)
        second = assign_temporal_splits(reordered)
        self.assertEqual(self.result, second)
        self.assertEqual(
            source_observation_digest(self.records),
            source_observation_digest(reordered),
        )

    def test_boundary_equality_uses_later_disposition(self) -> None:
        train_record = self.result.train[0]
        at_train_end = replace(
            train_record,
            observation_id="obs_aaaaaaaaaaaaaaaaaaaaaaaa",
            policy_id="pol_boundary_train_end",
            as_of=CANONICAL_TEMPORAL_SPLIT_SPECIFICATION.train_end,
            horizon_start=CANONICAL_TEMPORAL_SPLIT_SPECIFICATION.train_end,
            horizon_end="2024-06-30T00:00:00Z",
        )
        records = list(self.records) + [at_train_end]
        result = assign_temporal_splits(records)
        self.assertIn(at_train_end, result.embargoed)

    def test_censored_record_is_explicitly_excluded(self) -> None:
        original = self.result.embargoed[0]
        censored = replace(
            original,
            observation_id="obs_bbbbbbbbbbbbbbbbbbbbbbbb",
            policy_id="pol_censored_split_test",
            label=replace(
                original.label,
                status="right_censored",
                value=None,
                outcome_type=None,
                source_event_id=None,
                source_effective_at=None,
                source_ingested_at=None,
                censoring_reason="follow_up_ends_before_horizon",
            ),
        )
        result = assign_temporal_splits(list(self.records) + [censored])
        self.assertIn(censored, result.excluded)

    def test_duplicate_observation_assignment_fails(self) -> None:
        invalid = replace(
            self.result,
            validation=self.result.validation + (self.result.train[0],),
        )
        with self.assertRaisesRegex(ValueError, "multiple dispositions"):
            validate_temporal_split(invalid)

    def test_record_in_wrong_disposition_fails(self) -> None:
        misplaced = self.result.train[-1]
        invalid = replace(
            self.result,
            train=self.result.train[:-1],
            embargoed=tuple(
                sorted(
                    self.result.embargoed + (misplaced,),
                    key=lambda item: (item.as_of, item.policy_id, item.observation_id),
                )
            ),
        )
        with self.assertRaisesRegex(ValueError, "belongs in train"):
            validate_temporal_split(invalid)

    def test_policy_cross_partition_overlap_fails(self) -> None:
        validation = list(self.result.validation)
        validation[0] = replace(validation[0], policy_id=self.result.train[0].policy_id)
        invalid = replace(self.result, validation=tuple(validation))
        with self.assertRaisesRegex(ValueError, "policy_id appears"):
            validate_temporal_split(invalid)

    def test_outcome_episode_cross_partition_overlap_fails(self) -> None:
        train_positive = next(record for record in self.result.train if record.label.value == 1)
        validation_positive = next(
            record for record in self.result.validation if record.label.value == 1
        )
        validation = tuple(
            replace(
                record,
                label=replace(
                    record.label,
                    source_event_id=train_positive.label.source_event_id,
                ),
            )
            if record.observation_id == validation_positive.observation_id
            else record
            for record in self.result.validation
        )
        invalid = replace(self.result, validation=validation)
        with self.assertRaisesRegex(ValueError, "outcome episode appears"):
            validate_temporal_split(invalid)

    def test_horizon_equality_with_next_partition_fails(self) -> None:
        validation_start = min(record.as_of for record in self.result.validation)
        specification = TemporalSplitSpecification(
            train_end="2024-04-05T00:00:00Z",
            validation_start="2024-07-01T00:00:00Z",
            validation_end="2024-10-01T00:00:00Z",
            test_start="2024-12-01T00:00:00Z",
        )
        moved = tuple(
            record
            for record in self.result.embargoed
            if record.as_of < specification.train_end
        )
        self.assertEqual(max(record.horizon_end for record in moved), validation_start)
        invalid = replace(
            self.result,
            specification=specification,
            train=self.result.train + moved,
            embargoed=tuple(
                record for record in self.result.embargoed if record not in moved
            ),
        )
        with self.assertRaisesRegex(ValueError, "label horizons overlap"):
            validate_temporal_split(invalid)

    def test_incomplete_accounting_fails(self) -> None:
        invalid = replace(self.result, embargoed=self.result.embargoed[1:])
        with self.assertRaisesRegex(ValueError, "account"):
            validate_temporal_split(invalid, source_records=self.records)

    def test_incompatible_observation_contract_fails(self) -> None:
        records = list(self.records)
        records[0] = replace(records[0], observation_contract_version="2.0.0")
        with self.assertRaisesRegex(ValueError, "unsupported observation contract"):
            assign_temporal_splits(records)

    def test_incompatible_generator_provenance_fails(self) -> None:
        records = list(self.records)
        records[0] = replace(records[0], generator_version="9.9.9")
        with self.assertRaisesRegex(ValueError, "unsupported generator version"):
            assign_temporal_splits(records)

    def test_invalid_boundary_order_fails(self) -> None:
        specification = TemporalSplitSpecification(
            train_end="2024-07-01T00:00:00Z",
            validation_start="2024-04-01T00:00:00Z",
            validation_end="2024-10-01T00:00:00Z",
            test_start="2024-12-01T00:00:00Z",
        )
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            assign_temporal_splits(self.records, specification)

    def test_empty_modeling_partition_fails(self) -> None:
        invalid = TemporalSplitResult(
            specification=self.result.specification,
            train=(),
            embargoed=self.result.embargoed,
            validation=self.result.validation,
            calendar_gap=self.result.calendar_gap,
            test=self.result.test,
            excluded=self.result.excluded,
        )
        with self.assertRaisesRegex(ValueError, "train partition must not be empty"):
            validate_temporal_split(invalid)

    def test_manifest_is_byte_deterministic_and_contains_no_features(self) -> None:
        module = _load_manifest_module()
        first = module.canonical_bytes()
        second = module.canonical_bytes()
        self.assertEqual(first, second)
        self.assertNotIn(b'"features"', first)
        self.assertIn(b'"pipeline_engineering_only"', first)


if __name__ == "__main__":
    unittest.main()
