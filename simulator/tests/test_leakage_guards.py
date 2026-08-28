import copy
import sys
import unittest
from dataclasses import asdict, replace
from datetime import timedelta
from pathlib import Path


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator import (  # noqa: E402
    LABEL_HORIZON_DAYS,
    build_first_billing_observations,
    build_observation,
    find_exact_deterministic_proxies,
    first_billing_observation_time,
    generate_legacy_policy_histories,
    validate_feature_payload,
    validate_observation_records,
)


class LeakageGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.histories = generate_legacy_policy_histories(seed=20260817)
        cls.watermark = max(
            first_billing_observation_time(history)
            + timedelta(days=LABEL_HORIZON_DAYS)
            for history in cls.histories
        )
        cls.records = build_first_billing_observations(
            cls.histories,
            follow_up_through=cls.watermark,
        )

    def test_canonical_feature_boundary_and_dataset_integrity_pass(self) -> None:
        validate_observation_records(self.records)

    def test_guard_accepts_current_features_as_dataclass_and_mapping(self) -> None:
        features = self.records[0].features
        assert features is not None

        validate_feature_payload(features)
        validate_feature_payload(asdict(features))

    def test_post_cutoff_outcome_mutation_cannot_change_features(self) -> None:
        history = copy.deepcopy(self._history_with("outcome.lapsed"))
        cutoff = first_billing_observation_time(history)
        baseline = build_observation(
            history,
            cutoff,
            follow_up_through=self.watermark,
        )
        outcome = self._event(history, "outcome.lapsed")
        outcome["payload"]["outstanding_amount_cents"] += 987_654
        mutated = build_observation(
            history,
            cutoff,
            follow_up_through=self.watermark,
        )

        self.assertEqual(baseline.features, mutated.features)
        self.assertEqual(baseline.visible_event_ids, mutated.visible_event_ids)

    def test_effective_before_but_ingested_after_cutoff_is_invariant(self) -> None:
        history = copy.deepcopy(self._history_without_outcome())
        billing = self._event(history, "billing.premium_due")
        effective = self._datetime(billing["effective_at"])
        cutoff = effective + timedelta(minutes=30)
        baseline = build_observation(
            history,
            cutoff,
            follow_up_through=self.watermark,
        )
        billing["payload"]["amount_cents"] += 999_999
        mutated = build_observation(
            history,
            cutoff,
            follow_up_through=self.watermark,
        )

        self.assertEqual(baseline.features, mutated.features)
        self.assertNotIn(billing["event_id"], mutated.visible_event_ids)

    def test_ingested_before_but_effective_after_cutoff_is_invariant(self) -> None:
        history = copy.deepcopy(self._history_without_outcome())
        billing = self._event(history, "billing.premium_due")
        issuance = self._event(history, "policy.issued")
        cutoff = self._datetime(issuance["ingested_at"]) + timedelta(hours=1)
        billing["occurred_at"] = self._timestamp(cutoff - timedelta(minutes=2))
        billing["ingested_at"] = self._timestamp(cutoff - timedelta(minutes=1))
        baseline = build_observation(
            history,
            cutoff,
            follow_up_through=self.watermark,
        )
        billing["payload"]["amount_cents"] += 999_999
        mutated = build_observation(
            history,
            cutoff,
            follow_up_through=self.watermark,
        )

        self.assertEqual(baseline.features, mutated.features)
        self.assertNotIn(billing["event_id"], mutated.visible_event_ids)

    def test_event_at_cutoff_remains_visible(self) -> None:
        history = self._history_without_outcome()
        billing = self._event(history, "billing.premium_due")
        record = build_observation(
            history,
            billing["ingested_at"],
            follow_up_through=self.watermark,
        )

        assert record.features is not None
        self.assertEqual(record.features.visible_billing_count, 1)
        self.assertIn(billing["event_id"], record.visible_event_ids)

    def test_direct_and_normalized_prohibited_keys_are_rejected(self) -> None:
        for key in (
            "label",
            "LabelStatus",
            "scenario-id",
            "POLICY ID",
            "generatorOrder",
            "source.event.id",
        ):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "prohibited|unapproved"):
                    validate_feature_payload({key: "hidden"})

    def test_nested_prohibited_content_is_rejected_recursively(self) -> None:
        payload = self._valid_feature_mapping()
        payload["current_status"] = {
            "safe": ["active", {"terminal-status": "lapsed"}]
        }

        with self.assertRaisesRegex(ValueError, r"features.current_status.safe\[1\]"):
            validate_feature_payload(payload)

    def test_scenario_and_terminal_marker_values_are_rejected(self) -> None:
        for value in (
            "active_after_payment",
            "active-after-service-contact",
            "outcome.lapsed",
            "surrendered",
        ):
            with self.subTest(value=value):
                payload = self._valid_feature_mapping()
                payload["current_status"] = value
                with self.assertRaisesRegex(ValueError, "prohibited value"):
                    validate_feature_payload(payload)

    def test_unapproved_root_and_non_mapping_payloads_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unapproved path"):
            validate_feature_payload({"helpful_new_feature": 1})
        with self.assertRaisesRegex(ValueError, "must be a mapping"):
            validate_feature_payload([("current_status", "active")])

    def test_duplicate_observation_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate observation_id"):
            validate_observation_records([self.records[0], self.records[0]])

    def test_duplicate_policy_cutoff_is_rejected_independently(self) -> None:
        first = self.records[0]
        duplicate = replace(first, observation_id="obs_distinct_for_test")

        with self.assertRaisesRegex(ValueError, "duplicate policy/as_of"):
            validate_observation_records([first, duplicate])

    def test_duplicate_outcome_episode_is_rejected(self) -> None:
        positive = next(record for record in self.records if record.label.value == 1)
        duplicate = replace(
            positive,
            observation_id="obs_distinct_episode_test",
            policy_id="pol_distinct_episode_test",
            as_of=self._timestamp(self._datetime(positive.as_of) + timedelta(seconds=1)),
        )

        with self.assertRaisesRegex(ValueError, "duplicate outcome episode"):
            validate_observation_records([positive, duplicate])

    def test_integrity_result_is_independent_of_record_order(self) -> None:
        validate_observation_records(self.records)
        validate_observation_records(reversed(self.records))

    def test_exact_proxy_diagnostic_reports_only_deterministic_mappings(self) -> None:
        rows = [
            {"direct_proxy": "a", "not_proxy": 1},
            {"direct_proxy": "a", "not_proxy": 1},
            {"direct_proxy": "b", "not_proxy": 1},
            {"direct_proxy": "b", "not_proxy": 2},
        ]
        targets = [0, 0, 1, 1]

        self.assertEqual(
            find_exact_deterministic_proxies(rows, targets),
            ("direct_proxy",),
        )

    def test_proxy_diagnostic_validates_inputs(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty and equal length"):
            find_exact_deterministic_proxies([], [])
        with self.assertRaisesRegex(ValueError, "two target classes"):
            find_exact_deterministic_proxies([{"x": 1}], [0])

    def _history_with(self, event_type: str) -> list[dict]:
        return next(
            history
            for history in self.histories
            if any(event["event_type"] == event_type for event in history)
        )

    def _history_without_outcome(self) -> list[dict]:
        return next(
            history
            for history in self.histories
            if not any(event["event_type"].startswith("outcome.") for event in history)
        )

    @staticmethod
    def _event(history: list[dict], event_type: str) -> dict:
        return next(event for event in history if event["event_type"] == event_type)

    def _valid_feature_mapping(self) -> dict:
        features = self.records[0].features
        assert features is not None
        return asdict(features)

    @staticmethod
    def _datetime(value: str):
        from datetime import datetime

        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _timestamp(value) -> str:
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    unittest.main()
