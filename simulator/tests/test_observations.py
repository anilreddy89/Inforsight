import copy
import json
import sys
import unittest
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SIMULATOR_DIR.parent
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator import (  # noqa: E402
    LABEL_HORIZON_DAYS,
    OBSERVATION_CONTRACT_VERSION,
    ObservationRecord,
    OutcomeLabel,
    build_first_billing_observations,
    build_observation,
    first_billing_observation_time,
    generate_legacy_policy_histories,
    summarize_observations,
)
from inforsight_simulator.leakage import PROHIBITED_FEATURE_CONCEPTS  # noqa: E402


class ObservationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.histories = generate_legacy_policy_histories(seed=20260817)
        cls.watermark = max(
            first_billing_observation_time(history)
            + timedelta(days=LABEL_HORIZON_DAYS)
            for history in cls.histories
        )
        schema_path = REPOSITORY_ROOT / "data-contracts" / "observation-record.schema.json"
        cls.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(
            cls.schema,
            format_checker=FormatChecker(),
        )

    def test_canonical_first_billing_observations_are_deterministic(self) -> None:
        first = build_first_billing_observations(
            self.histories,
            follow_up_through=self.watermark,
        )
        second = build_first_billing_observations(
            list(reversed(copy.deepcopy(self.histories))),
            follow_up_through=self.watermark,
        )

        self.assertEqual(first, second)
        self.assertEqual(len(first), 100)
        self.assertEqual(len({record.observation_id for record in first}), 100)
        self.assertEqual(
            [(record.as_of, record.policy_id) for record in first],
            sorted((record.as_of, record.policy_id) for record in first),
        )

    def test_canonical_sufficiency_counts_match_coverage_fixture(self) -> None:
        records = build_first_billing_observations(
            self.histories,
            follow_up_through=self.watermark,
        )

        self.assertEqual(
            summarize_observations(records),
            {
                "observation_count": 100,
                "eligible_observation_count": 100,
                "ineligible_observation_count": 0,
                "label_status_counts": {
                    "observed_negative": 50,
                    "observed_positive": 50,
                },
                "outcome_type_counts": {
                    "outcome.lapsed": 25,
                    "outcome.surrendered": 25,
                },
                "unique_policy_count": 100,
            },
        )

    def test_records_satisfy_strict_json_schema(self) -> None:
        records = build_first_billing_observations(
            self.histories,
            follow_up_through=self.watermark,
        )

        for record in records:
            with self.subTest(observation_id=record.observation_id):
                self.validator.validate(record.to_dict())

    def test_billing_is_hidden_until_both_effective_and_ingested(self) -> None:
        history = self._history_for("active")
        billing = self._event(history, "billing.premium_due")
        effective = self._datetime(billing["effective_at"])
        ingested = self._datetime(billing["ingested_at"])

        before_ingestion = build_observation(
            history,
            effective + timedelta(minutes=30),
            follow_up_through=self.watermark,
        )
        at_ingestion = build_observation(
            history,
            ingested,
            follow_up_through=self.watermark,
        )

        assert before_ingestion.features is not None
        assert at_ingestion.features is not None
        self.assertEqual(before_ingestion.features.visible_event_count, 1)
        self.assertEqual(before_ingestion.features.visible_billing_count, 0)
        self.assertNotIn(billing["event_id"], before_ingestion.visible_event_ids)
        self.assertEqual(at_ingestion.features.visible_event_count, 2)
        self.assertEqual(at_ingestion.features.visible_billing_count, 1)
        self.assertIn(billing["event_id"], at_ingestion.visible_event_ids)

    def test_future_effective_event_is_hidden_even_if_ingested_early(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        billing = self._event(history, "billing.premium_due")
        issuance = self._event(history, "policy.issued")
        cutoff = self._datetime(issuance["ingested_at"]) + timedelta(hours=1)
        billing["occurred_at"] = self._timestamp(cutoff - timedelta(minutes=2))
        billing["ingested_at"] = self._timestamp(cutoff - timedelta(minutes=1))

        record = build_observation(
            history,
            cutoff,
            follow_up_through=self.watermark,
        )

        assert record.features is not None
        self.assertEqual(record.features.visible_billing_count, 0)
        self.assertNotIn(billing["event_id"], record.visible_event_ids)

    def test_grace_period_policy_is_ineligible(self) -> None:
        history = self._history_for("lapsed")
        grace = next(
            event
            for event in history
            if event["event_type"] == "policy.status_changed"
            and event["payload"]["new_status"] == "grace_period"
        )

        record = build_observation(
            history,
            grace["ingested_at"],
            follow_up_through=self.watermark,
        )

        self.assertFalse(record.eligible)
        self.assertEqual(record.eligibility_reason, "status_grace_period_not_eligible")
        self.assertIsNone(record.features)
        self.assertEqual(record.label.status, "not_applicable")
        self.assertIsNone(record.label.value)

    def test_lapse_and_surrender_are_positive_adverse_terminations(self) -> None:
        for scenario, outcome_type in (
            ("lapsed", "outcome.lapsed"),
            ("surrendered", "outcome.surrendered"),
        ):
            with self.subTest(scenario=scenario):
                history = self._history_for(scenario)
                record = build_observation(
                    history,
                    first_billing_observation_time(history),
                    follow_up_through=self.watermark,
                )

                self.assertEqual(record.label.status, "observed_positive")
                self.assertEqual(record.label.value, 1)
                self.assertEqual(record.label.outcome_type, outcome_type)
                self.assertIsNotNone(record.label.source_event_id)

    def test_full_follow_up_without_outcome_is_negative(self) -> None:
        history = self._history_for("active")
        cutoff = first_billing_observation_time(history)

        record = build_observation(
            history,
            cutoff,
            follow_up_through=cutoff + timedelta(days=LABEL_HORIZON_DAYS),
        )

        self.assertEqual(record.label.status, "observed_negative")
        self.assertEqual(record.label.value, 0)
        self.assertIsNone(record.label.outcome_type)

    def test_incomplete_follow_up_is_censored_not_negative(self) -> None:
        history = self._history_for("active")
        cutoff = first_billing_observation_time(history)

        record = build_observation(
            history,
            cutoff,
            follow_up_through=cutoff + timedelta(days=89, hours=23),
        )

        self.assertEqual(record.label.status, "right_censored")
        self.assertIsNone(record.label.value)
        self.assertEqual(
            record.label.censoring_reason,
            "follow_up_ends_before_horizon",
        )

    def test_positive_observed_before_early_watermark_is_not_censored(self) -> None:
        history = self._history_for("surrendered")
        cutoff = first_billing_observation_time(history)
        outcome = self._event(history, "outcome.surrendered")

        record = build_observation(
            history,
            cutoff,
            follow_up_through=outcome["ingested_at"],
        )

        self.assertEqual(record.label.status, "observed_positive")
        self.assertEqual(record.label.value, 1)

    def test_outcome_not_ingested_by_watermark_is_censored(self) -> None:
        history = copy.deepcopy(self._history_for("surrendered"))
        cutoff = first_billing_observation_time(history)
        horizon_end = cutoff + timedelta(days=LABEL_HORIZON_DAYS)
        outcome = self._event(history, "outcome.surrendered")
        outcome["ingested_at"] = self._timestamp(horizon_end + timedelta(days=1))

        record = build_observation(
            history,
            cutoff,
            follow_up_through=horizon_end,
        )

        self.assertEqual(record.label.status, "right_censored")
        self.assertEqual(
            record.label.censoring_reason,
            "outcome_not_ingested_by_watermark",
        )

    def test_horizon_end_is_inclusive(self) -> None:
        history = copy.deepcopy(self._history_for("lapsed"))
        cutoff = first_billing_observation_time(history)
        horizon_end = cutoff + timedelta(days=LABEL_HORIZON_DAYS)
        self._move_terminal_pair(history, horizon_end)

        record = build_observation(
            history,
            cutoff,
            follow_up_through=horizon_end + timedelta(hours=1),
        )

        self.assertEqual(record.label.status, "observed_positive")
        self.assertEqual(record.label.source_effective_at, self._timestamp(horizon_end))

    def test_horizon_start_is_exclusive(self) -> None:
        history = copy.deepcopy(self._history_for("surrendered"))
        original_outcome = self._event(history, "outcome.surrendered")
        cutoff = self._datetime(original_outcome["effective_at"])

        record = build_observation(
            history,
            cutoff,
            follow_up_through=cutoff + timedelta(days=LABEL_HORIZON_DAYS),
        )

        self.assertTrue(record.eligible)
        self.assertEqual(record.label.status, "observed_negative")

    def test_feature_surface_excludes_identity_label_and_scenario_keys(self) -> None:
        history = self._history_for("lapsed")
        record = build_observation(
            history,
            first_billing_observation_time(history),
            follow_up_through=self.watermark,
        )

        assert record.features is not None
        feature_keys = set(asdict(record.features))
        self.assertFalse(feature_keys.intersection(PROHIBITED_FEATURE_CONCEPTS))
        self.assertNotIn("outcome.lapsed", json.dumps(asdict(record.features)))

    def test_invalid_history_and_non_utc_cutoffs_fail_closed(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        history[-1]["event_id"] = history[0]["event_id"]
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            build_observation(
                history,
                "2024-02-01T00:00:00Z",
                follow_up_through="2024-05-01T00:00:00Z",
            )

        valid = self._history_for("active")
        with self.assertRaisesRegex(ValueError, "UTC|ending in Z"):
            build_observation(
                valid,
                "2024-02-01T00:00:00+01:00",
                follow_up_through="2024-05-01T00:00:00Z",
            )

    def test_observation_identifier_changes_with_cutoff_and_contract_version(self) -> None:
        history = self._history_for("active")
        cutoff = first_billing_observation_time(history)
        first = build_observation(
            history,
            cutoff,
            follow_up_through=self.watermark,
        )
        second = build_observation(
            history,
            cutoff + timedelta(seconds=1),
            follow_up_through=self.watermark,
        )

        self.assertEqual(first.observation_contract_version, OBSERVATION_CONTRACT_VERSION)
        self.assertNotEqual(first.observation_id, second.observation_id)

    def test_watermark_before_cutoff_is_rejected(self) -> None:
        history = self._history_for("active")
        cutoff = first_billing_observation_time(history)

        with self.assertRaisesRegex(ValueError, "at or after as_of"):
            build_observation(
                history,
                cutoff,
                follow_up_through=cutoff - timedelta(seconds=1),
            )

    def test_schema_rejects_contradictory_label_variants(self) -> None:
        valid = build_observation(
            self._history_for("lapsed"),
            first_billing_observation_time(self._history_for("lapsed")),
            follow_up_through=self.watermark,
        ).to_dict()
        mutations = (
            ("positive value", {"value": 0}),
            ("positive censoring", {"censoring_reason": "follow_up_ends_before_horizon"}),
            (
                "negative provenance",
                {
                    "status": "observed_negative",
                    "value": 0,
                    "outcome_type": "outcome.lapsed",
                },
            ),
            (
                "censored value",
                {
                    "status": "right_censored",
                    "value": 1,
                    "outcome_type": None,
                    "source_event_id": None,
                    "source_effective_at": None,
                    "source_ingested_at": None,
                    "censoring_reason": "follow_up_ends_before_horizon",
                },
            ),
            (
                "not applicable value",
                {
                    "status": "not_applicable",
                    "value": 0,
                    "outcome_type": None,
                    "source_event_id": None,
                    "source_effective_at": None,
                    "source_ingested_at": None,
                    "censoring_reason": None,
                },
            ),
        )
        for name, fields in mutations:
            with self.subTest(name=name):
                candidate = copy.deepcopy(valid)
                candidate["label"].update(fields)
                self.assertTrue(list(self.validator.iter_errors(candidate)))

    def test_schema_rejects_eligibility_version_currency_and_unknown_fields(self) -> None:
        record = build_observation(
            self._history_for("active"),
            first_billing_observation_time(self._history_for("active")),
            follow_up_through=self.watermark,
        ).to_dict()
        candidates = []
        missing_features = copy.deepcopy(record)
        missing_features["features"] = None
        candidates.append(missing_features)
        unsupported_version = copy.deepcopy(record)
        unsupported_version["event_schema_version"] = "9.0.0"
        candidates.append(unsupported_version)
        unsupported_currency = copy.deepcopy(record)
        unsupported_currency["features"]["currency"] = "EUR"
        candidates.append(unsupported_currency)
        unexpected = copy.deepcopy(record)
        unexpected["unexpected"] = True
        candidates.append(unexpected)
        for candidate in candidates:
            self.assertTrue(list(self.validator.iter_errors(candidate)))

    def test_runtime_label_variants_fail_closed(self) -> None:
        invalid = (
            ("observed_positive", 0, "outcome.lapsed", "evt_000000000001", "2024-02-01T00:00:00Z", "2024-02-01T01:00:00Z", None),
            ("observed_negative", 0, "outcome.lapsed", None, None, None, None),
            ("right_censored", None, None, None, None, None, None),
            ("not_applicable", 1, None, None, None, None, None),
        )
        for fields in invalid:
            with self.subTest(status=fields[0]), self.assertRaises(ValueError):
                OutcomeLabel(*fields)

    def test_runtime_record_rejects_composite_and_temporal_contradictions(self) -> None:
        record = build_observation(
            self._history_for("active"),
            first_billing_observation_time(self._history_for("active")),
            follow_up_through=self.watermark,
        )
        invalid_changes = (
            {"features": None},
            {"eligible": False},
            {"eligibility_reason": "policy_not_visible"},
            {"event_schema_version": "9.0.0"},
            {"horizon_start": "2024-01-01T00:00:00Z"},
            {"follow_up_through": "2024-01-01T00:00:00Z"},
        )
        for changes in invalid_changes:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(record, **changes)

        assert record.features is not None
        with self.assertRaisesRegex(ValueError, "unsupported observation currency"):
            replace(record.features, currency="EUR")
        with self.assertRaisesRegex(ValueError, "nonnegative integer"):
            replace(record.features, visible_event_count=True)

    def _history_for(self, scenario: str) -> list[dict]:
        for history in self.histories:
            event_types = {event["event_type"] for event in history}
            statuses = [
                event["payload"].get("new_status")
                for event in history
                if event["event_type"] == "policy.status_changed"
            ]
            if scenario == "lapsed" and "outcome.lapsed" in event_types:
                return history
            if scenario == "surrendered" and "outcome.surrendered" in event_types:
                return history
            if scenario == "active" and not statuses:
                return history
        self.fail(f"no generated history for scenario {scenario}")

    @staticmethod
    def _event(history: list[dict], event_type: str) -> dict:
        return next(event for event in history if event["event_type"] == event_type)

    @classmethod
    def _move_terminal_pair(cls, history: list[dict], effective_at: datetime) -> None:
        for event in history:
            is_outcome = event["event_type"] in {"outcome.lapsed", "outcome.surrendered"}
            is_terminal_status = (
                event["event_type"] == "policy.status_changed"
                and event["payload"].get("new_status") in {"lapsed", "surrendered"}
            )
            if is_outcome or is_terminal_status:
                event["occurred_at"] = cls._timestamp(effective_at)
                event["effective_at"] = cls._timestamp(effective_at)
                event["ingested_at"] = cls._timestamp(effective_at + timedelta(hours=1))

    @staticmethod
    def _datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    unittest.main()
