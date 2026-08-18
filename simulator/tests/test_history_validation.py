import copy
import random
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator import (  # noqa: E402
    generate_policy_histories,
    reconstruct_policy_state,
    validate_policy_history,
)


class PolicyHistoryValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.histories = generate_policy_histories(seed=20260817)

    def test_every_default_generated_history_is_valid(self) -> None:
        for history in self.histories:
            with self.subTest(policy_id=history[0]["policy_id"]):
                self.assertIsNone(validate_policy_history(history))

    def test_all_supported_transition_edges_are_generated_and_valid(self) -> None:
        transitions = {
            (
                event["payload"]["previous_status"],
                event["payload"]["new_status"],
            )
            for history in self.histories
            for event in history
            if event["event_type"] == "policy.status_changed"
        }

        self.assertEqual(
            transitions,
            {
                ("active", "grace_period"),
                ("grace_period", "active"),
                ("grace_period", "lapsed"),
                ("active", "surrendered"),
            },
        )

    def test_shuffled_history_validates_and_replays_without_mutation(self) -> None:
        history = copy.deepcopy(self._history_for("recovered"))
        original = copy.deepcopy(history)
        shuffled = copy.deepcopy(history)
        random.Random(10).shuffle(shuffled)
        shuffled_original = copy.deepcopy(shuffled)
        cutoff = max(event["effective_at"] for event in history)

        validate_policy_history(history)
        validate_policy_history(shuffled)

        self.assertEqual(
            reconstruct_policy_state(history, cutoff),
            reconstruct_policy_state(shuffled, cutoff),
        )
        self.assertEqual(history, original)
        self.assertEqual(shuffled, shuffled_original)

    def test_repeated_replay_is_equal_at_each_status_cutoff(self) -> None:
        history = self._history_for("lapsed")
        for event in history:
            if event["event_type"] != "policy.status_changed":
                continue
            with self.subTest(event_id=event["event_id"]):
                first = reconstruct_policy_state(history, event["effective_at"])
                second = reconstruct_policy_state(history, event["effective_at"])
                self.assertEqual(first, second)

    def test_mismatched_previous_status_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("recovered"))
        status_event = self._status_events(history)[0]
        status_event["payload"]["previous_status"] = "grace_period"

        with self.assertRaisesRegex(ValueError, "does not match current status"):
            validate_policy_history(history)

    def test_no_op_transition_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("recovered"))
        status_event = self._status_events(history)[0]
        status_event["payload"]["new_status"] = "active"

        with self.assertRaisesRegex(ValueError, "unsupported policy status transition"):
            validate_policy_history(history)

    def test_unsupported_transition_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("surrendered"))
        status_event = self._status_events(history)[0]
        status_event["payload"]["new_status"] = "lapsed"

        with self.assertRaisesRegex(ValueError, "unsupported policy status transition"):
            validate_policy_history(history)

    def test_activity_after_terminal_status_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("lapsed"))
        terminal = self._status_events(history)[-1]
        later = copy.deepcopy(history[1])
        later["event_id"] = "evt_ffffffffffff"
        later_time = self._datetime(terminal["effective_at"]) + timedelta(days=1)
        later["occurred_at"] = self._timestamp(later_time)
        later["effective_at"] = self._timestamp(later_time)
        later["ingested_at"] = self._timestamp(later_time + timedelta(hours=1))
        later["payload"]["due_date"] = later_time.date().isoformat()
        later["payload"]["billing_id"] = "bil_ffffffffffff"
        history.append(later)

        with self.assertRaisesRegex(ValueError, "effective after terminal status"):
            validate_policy_history(history)

    def test_terminal_status_without_outcome_is_rejected(self) -> None:
        history = [
            event
            for event in copy.deepcopy(self._history_for("lapsed"))
            if event["event_type"] != "outcome.lapsed"
        ]

        with self.assertRaisesRegex(ValueError, "must both be present"):
            validate_policy_history(history)

    def test_terminal_outcome_without_status_is_rejected(self) -> None:
        history = [
            event
            for event in copy.deepcopy(self._history_for("surrendered"))
            if event["event_type"] != "policy.status_changed"
        ]

        with self.assertRaisesRegex(ValueError, "must both be present"):
            validate_policy_history(history)

    def test_terminal_pair_must_share_effective_time(self) -> None:
        history = copy.deepcopy(self._history_for("lapsed"))
        outcome = next(
            event for event in history if event["event_type"] == "outcome.lapsed"
        )
        changed = self._datetime(outcome["effective_at"]) - timedelta(seconds=1)
        outcome["effective_at"] = self._timestamp(changed)

        with self.assertRaisesRegex(ValueError, "must share effective_at"):
            validate_policy_history(history)

    def test_event_before_issuance_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        issuance_time = self._datetime(history[0]["occurred_at"])
        event = history[1]
        earlier = issuance_time - timedelta(seconds=1)
        event["occurred_at"] = self._timestamp(earlier)
        event["effective_at"] = self._timestamp(earlier)
        event["ingested_at"] = self._timestamp(earlier + timedelta(hours=1))
        event["payload"]["due_date"] = earlier.date().isoformat()

        with self.assertRaisesRegex(ValueError, "before issuance"):
            validate_policy_history(history)

    def test_ingestion_before_occurrence_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        event = history[-1]
        event["ingested_at"] = self._timestamp(
            self._datetime(event["occurred_at"]) - timedelta(seconds=1)
        )

        with self.assertRaisesRegex(ValueError, "ingested before it occurred"):
            validate_policy_history(history)

    def test_billing_due_date_must_match_effective_date(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        billing = next(
            event for event in history if event["event_type"] == "billing.premium_due"
        )
        billing["payload"]["due_date"] = "2024-12-31"

        with self.assertRaisesRegex(ValueError, "does not match effective_at date"):
            validate_policy_history(history)

    def test_malformed_billing_due_date_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        billing = next(
            event for event in history if event["event_type"] == "billing.premium_due"
        )
        billing["payload"]["due_date"] = "2024-02-30"

        with self.assertRaisesRegex(ValueError, "valid ISO 8601 date"):
            validate_policy_history(history)

    def test_payment_must_reference_an_existing_prior_billing(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        payment = next(
            event for event in history if event["event_type"] == "payment.received"
        )
        payment["payload"]["billing_id"] = "bil_ffffffffffff"

        with self.assertRaisesRegex(ValueError, "unknown or future billing_id"):
            validate_policy_history(history)

    def test_payment_must_not_occur_before_its_billing(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        billing = next(
            event for event in history if event["event_type"] == "billing.premium_due"
        )
        payment = next(
            event for event in history if event["event_type"] == "payment.received"
        )
        earlier = self._datetime(billing["occurred_at"]) - timedelta(seconds=1)
        payment["occurred_at"] = self._timestamp(earlier)

        with self.assertRaisesRegex(ValueError, "before its billing"):
            validate_policy_history(history)

    def test_payment_reminder_must_not_precede_payment_failure(self) -> None:
        history = copy.deepcopy(self._history_for("recovered"))
        reminder = next(
            event
            for event in history
            if event["event_type"] == "notice.sent"
            and event["payload"]["notice_type"] == "payment_reminder"
        )
        billing = next(
            event for event in history if event["event_type"] == "billing.premium_due"
        )
        earlier = self._datetime(billing["effective_at"]) + timedelta(hours=1)
        reminder["occurred_at"] = self._timestamp(earlier)
        reminder["effective_at"] = self._timestamp(earlier)
        reminder["ingested_at"] = self._timestamp(earlier + timedelta(hours=1))

        with self.assertRaisesRegex(ValueError, "precedes a payment failure"):
            validate_policy_history(history)

    def test_surrender_outcome_requires_a_prior_inquiry(self) -> None:
        history = [
            event
            for event in copy.deepcopy(self._history_for("surrendered"))
            if not (
                event["event_type"] == "service.contact_recorded"
                and event["payload"]["reason"] == "surrender_inquiry"
            )
        ]

        with self.assertRaisesRegex(ValueError, "precedes a surrender inquiry"):
            validate_policy_history(history)

    def test_lapse_outcome_requires_a_prior_warning(self) -> None:
        history = [
            event
            for event in copy.deepcopy(self._history_for("lapsed"))
            if not (
                event["event_type"] == "notice.sent"
                and event["payload"]["notice_type"] == "lapse_warning"
            )
        ]

        with self.assertRaisesRegex(ValueError, "precedes a lapse warning"):
            validate_policy_history(history)

    def test_reconstruction_rejects_an_invalid_future_suffix(self) -> None:
        history = copy.deepcopy(self._history_for("recovered"))
        issuance_cutoff = history[0]["effective_at"]
        self._status_events(history)[-1]["payload"]["previous_status"] = "active"

        with self.assertRaisesRegex(ValueError, "does not match current status"):
            reconstruct_policy_state(history, issuance_cutoff)

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
            if scenario == "recovered" and "grace_period" in statuses and "active" in statuses:
                return history
            if scenario == "active" and not statuses:
                return history
        self.fail(f"no generated history for scenario {scenario}")

    @staticmethod
    def _status_events(history: list[dict]) -> list[dict]:
        return [
            event
            for event in history
            if event["event_type"] == "policy.status_changed"
        ]

    @staticmethod
    def _datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    unittest.main()
