import random
import sys
import unittest
from collections import Counter
from pathlib import Path


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from contract_support import policy_event_validator  # noqa: E402
from inforsight_simulator import (  # noqa: E402
    GeneratorConfig,
    generate_policy_histories,
    generation_provenance,
    histories_to_jsonl,
)


class GeneratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seed = 20260817
        cls.histories = generate_policy_histories(cls.seed)
        cls.events = [event for history in cls.histories for event in history]
        cls.validator = policy_event_validator()

    def test_default_run_has_100_unique_policy_histories(self) -> None:
        self.assertEqual(len(self.histories), 100)
        policy_ids = {history[0]["policy_id"] for history in self.histories}
        self.assertEqual(len(policy_ids), 100)
        for history in self.histories:
            self.assertTrue(history)
            policy_id = history[0]["policy_id"]
            self.assertTrue(all(event["policy_id"] == policy_id for event in history))

    def test_every_history_starts_with_exactly_one_issuance(self) -> None:
        for history in self.histories:
            with self.subTest(policy_id=history[0]["policy_id"]):
                self.assertEqual(history[0]["event_type"], "policy.issued")
                self.assertEqual(
                    sum(event["event_type"] == "policy.issued" for event in history),
                    1,
                )

    def test_every_generated_event_matches_the_contract(self) -> None:
        for event in self.events:
            with self.subTest(event_id=event["event_id"]):
                errors = list(self.validator.iter_errors(event))
                self.assertEqual(errors, [], [error.message for error in errors])

    def test_identifiers_are_unique_in_the_default_run(self) -> None:
        event_ids = [event["event_id"] for event in self.events]
        self.assertEqual(len(event_ids), len(set(event_ids)))

        identifiers_by_field: dict[str, list[str]] = {
            "billing_id": [],
            "payment_id": [],
            "notice_id": [],
            "contact_id": [],
        }
        for event in self.events:
            for field in identifiers_by_field:
                identifier = event["payload"].get(field)
                if identifier is not None:
                    identifiers_by_field[field].append(identifier)

        # A billing ID is intentionally repeated by its due and payment events.
        for field in ("payment_id", "notice_id", "contact_id"):
            values = identifiers_by_field[field]
            self.assertEqual(len(values), len(set(values)), field)

        created_billing_ids = [
            event["payload"]["billing_id"]
            for event in self.events
            if event["event_type"] == "billing.premium_due"
        ]
        self.assertEqual(len(created_billing_ids), len(set(created_billing_ids)))

    def test_payments_reference_billing_in_the_same_history(self) -> None:
        for history in self.histories:
            billing_ids = {
                event["payload"]["billing_id"]
                for event in history
                if event["event_type"] == "billing.premium_due"
            }
            for event in history:
                if event["event_type"] in ("payment.received", "payment.failed"):
                    self.assertIn(event["payload"]["billing_id"], billing_ids)

    def test_default_run_has_balanced_scenario_coverage(self) -> None:
        scenarios = Counter(self._scenario(history) for history in self.histories)
        self.assertEqual(
            scenarios,
            Counter({"active": 25, "recovered": 25, "lapsed": 25, "surrendered": 25}),
        )

    def test_terminal_histories_end_at_the_terminal_time(self) -> None:
        for history in self.histories:
            terminal_events = [
                event
                for event in history
                if event["event_type"] in ("outcome.lapsed", "outcome.surrendered")
            ]
            if not terminal_events:
                continue
            terminal_time = terminal_events[0]["occurred_at"]
            self.assertTrue(
                all(event["occurred_at"] <= terminal_time for event in history)
            )

    def test_histories_have_explicit_stable_chronological_order(self) -> None:
        for history in self.histories:
            ordering_keys = [
                (event["occurred_at"], event["event_id"]) for event in history
            ]
            self.assertEqual(ordering_keys, sorted(ordering_keys))

    def test_same_inputs_are_structurally_and_byte_deterministic(self) -> None:
        first = generate_policy_histories(self.seed)
        second = generate_policy_histories(self.seed)
        self.assertEqual(first, second)
        self.assertEqual(histories_to_jsonl(first), histories_to_jsonl(second))

    def test_generation_is_independent_of_global_random_state(self) -> None:
        random.seed(1)
        first = generate_policy_histories(self.seed, 8)
        for _ in range(100):
            random.random()
        second = generate_policy_histories(self.seed, 8)
        self.assertEqual(first, second)

    def test_different_seed_changes_valid_content(self) -> None:
        other = generate_policy_histories(self.seed + 1)
        self.assertNotEqual(self.histories, other)
        for history in other:
            for event in history:
                self.assertEqual(list(self.validator.iter_errors(event)), [])

    def test_invalid_counts_are_rejected(self) -> None:
        for invalid_count in (0, -1):
            with self.subTest(policy_count=invalid_count):
                with self.assertRaisesRegex(ValueError, "greater than zero"):
                    generate_policy_histories(self.seed, invalid_count)

    def test_provenance_contains_reproduction_inputs(self) -> None:
        provenance = generation_provenance(GeneratorConfig(seed=self.seed))
        self.assertEqual(
            set(provenance),
            {
                "generator_version",
                "schema_version",
                "seed",
                "policy_count",
                "simulation_start",
            },
        )
        self.assertEqual(provenance["seed"], self.seed)
        self.assertEqual(provenance["policy_count"], 100)

    def test_output_contains_only_bounded_structured_fields(self) -> None:
        prohibited = {
            "name",
            "address",
            "email_address",
            "phone_number",
            "account_number",
            "message",
            "notes",
            "free_text",
        }
        for event in self.events:
            self.assertTrue(prohibited.isdisjoint(event))
            self.assertTrue(prohibited.isdisjoint(event["payload"]))

    @staticmethod
    def _scenario(history: list[dict]) -> str:
        event_types = {event["event_type"] for event in history}
        if "outcome.lapsed" in event_types:
            return "lapsed"
        if "outcome.surrendered" in event_types:
            return "surrendered"
        statuses = [
            event["payload"].get("new_status")
            for event in history
            if event["event_type"] == "policy.status_changed"
        ]
        return "recovered" if "grace_period" in statuses else "active"


if __name__ == "__main__":
    unittest.main()
