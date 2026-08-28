import copy
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator import (  # noqa: E402
    PolicyState,
    generate_legacy_policy_histories,
    reconstruct_policy_state,
)


class ReconstructionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.histories = generate_legacy_policy_histories(seed=20260817)

    def test_active_state_at_issuance_contains_stable_policy_attributes(self) -> None:
        history = self._history_for("active")
        issuance = history[0]

        state = reconstruct_policy_state(history, issuance["effective_at"])

        self.assertIsInstance(state, PolicyState)
        assert state is not None
        self.assertEqual(state.policy_id, issuance["policy_id"])
        self.assertEqual(state.status, "active")
        self.assertEqual(state.product_variant, issuance["payload"]["product_variant"])
        self.assertEqual(
            state.billing_frequency, issuance["payload"]["billing_frequency"]
        )
        self.assertEqual(
            state.premium_amount_cents,
            issuance["payload"]["premium_amount_cents"],
        )
        self.assertEqual(state.currency, "USD")
        self.assertEqual(state.applied_event_count, 1)
        self.assertEqual(state.last_event_id, issuance["event_id"])

    def test_cutoff_before_issuance_returns_none(self) -> None:
        history = self._history_for("active")
        issuance_time = self._datetime(history[0]["effective_at"])

        state = reconstruct_policy_state(history, issuance_time - timedelta(seconds=1))

        self.assertIsNone(state)

    def test_event_at_cutoff_is_included_and_future_status_is_excluded(self) -> None:
        history = self._history_for("recovered")
        status_events = self._status_events(history)
        grace_time = status_events[0]["effective_at"]
        recovery_time = status_events[1]["effective_at"]

        grace_state = reconstruct_policy_state(history, grace_time)
        recovered_state = reconstruct_policy_state(history, recovery_time)

        assert grace_state is not None
        assert recovered_state is not None
        self.assertEqual(grace_state.status, "grace_period")
        self.assertEqual(recovered_state.status, "active")
        self.assertLess(grace_state.applied_event_count, recovered_state.applied_event_count)

    def test_state_immediately_before_grace_transition_remains_active(self) -> None:
        history = self._history_for("lapsed")
        grace_time = self._datetime(self._status_events(history)[0]["effective_at"])

        state = reconstruct_policy_state(history, grace_time - timedelta(seconds=1))

        assert state is not None
        self.assertEqual(state.status, "active")

    def test_terminal_states_are_reconstructed_at_their_status_change(self) -> None:
        for scenario, expected_status in (
            ("lapsed", "lapsed"),
            ("surrendered", "surrendered"),
        ):
            with self.subTest(scenario=scenario):
                history = self._history_for(scenario)
                terminal_change = self._status_events(history)[-1]
                state = reconstruct_policy_state(
                    history, terminal_change["effective_at"]
                )
                assert state is not None
                self.assertEqual(state.status, expected_status)
                self.assertEqual(state.last_event_id, terminal_change["event_id"])

    def test_input_order_does_not_change_state_or_mutate_history(self) -> None:
        history = self._history_for("recovered")
        original = copy.deepcopy(history)
        reversed_history = list(reversed(copy.deepcopy(history)))
        cutoff = max(event["effective_at"] for event in history)

        ordered_state = reconstruct_policy_state(history, cutoff)
        reversed_state = reconstruct_policy_state(reversed_history, cutoff)

        self.assertEqual(ordered_state, reversed_state)
        self.assertEqual(history, original)
        self.assertEqual(reversed_history, list(reversed(original)))

    def test_aware_utc_datetime_cutoff_is_supported(self) -> None:
        history = self._history_for("active")
        cutoff = self._datetime(history[0]["effective_at"])

        state = reconstruct_policy_state(history, cutoff)

        assert state is not None
        self.assertEqual(state.as_of, cutoff)
        self.assertEqual(state.as_of.tzinfo, timezone.utc)

    def test_empty_history_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty list"):
            reconstruct_policy_state([], "2024-01-01T00:00:00Z")

    def test_mixed_policy_history_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        history[-1]["policy_id"] = "pol_ffffffffffff"

        with self.assertRaisesRegex(ValueError, "exactly one policy_id"):
            reconstruct_policy_state(history, "2025-01-01T00:00:00Z")

    def test_duplicate_event_id_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        history[-1]["event_id"] = history[0]["event_id"]

        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            reconstruct_policy_state(history, "2025-01-01T00:00:00Z")

    def test_unsupported_event_type_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        history[-1]["event_type"] = "policy.unknown"

        with self.assertRaisesRegex(ValueError, "fails JSON Schema at event_type"):
            reconstruct_policy_state(history, "2025-01-01T00:00:00Z")

    def test_invalid_event_timestamp_is_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        history[-1]["effective_at"] = "not-a-timestamp"

        with self.assertRaisesRegex(ValueError, "fails JSON Schema at effective_at"):
            reconstruct_policy_state(history, "2025-01-01T00:00:00Z")

    def test_non_utc_and_naive_cutoffs_are_rejected(self) -> None:
        history = self._history_for("active")
        invalid_cutoffs = (
            "2025-01-01T00:00:00+01:00",
            datetime(2025, 1, 1),
            datetime(2025, 1, 1, tzinfo=timezone(timedelta(hours=1))),
        )
        for cutoff in invalid_cutoffs:
            with self.subTest(cutoff=cutoff):
                with self.assertRaisesRegex(ValueError, "UTC|ending in Z"):
                    reconstruct_policy_state(history, cutoff)

    def test_multiple_issuance_events_are_rejected(self) -> None:
        history = copy.deepcopy(self._history_for("active"))
        duplicate = copy.deepcopy(history[0])
        duplicate["event_id"] = "evt_ffffffffffff"
        history.append(duplicate)

        with self.assertRaisesRegex(ValueError, "exactly one policy.issued"):
            reconstruct_policy_state(history, "2025-01-01T00:00:00Z")

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


if __name__ == "__main__":
    unittest.main()
