import random
import sys
import unittest
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from contract_support import policy_event_validator  # noqa: E402
from inforsight_simulator import (  # noqa: E402
    GeneratorConfig,
    configuration_digest,
    generate_legacy_policy_histories,
    generate_policy_histories,
    generation_provenance,
    histories_to_jsonl,
    legacy_generation_provenance,
    run_identity,
    verify_generation_provenance,
)


class GeneratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seed = 20260817
        cls.config = GeneratorConfig(
            seed=cls.seed,
            run_namespace="generator-tests",
        )
        cls.histories = generate_policy_histories(cls.config)
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
        first = generate_policy_histories(self.config)
        second = generate_policy_histories(self.config)
        self.assertEqual(first, second)
        self.assertEqual(histories_to_jsonl(first), histories_to_jsonl(second))

    def test_generation_is_independent_of_global_random_state(self) -> None:
        random.seed(1)
        config = GeneratorConfig(
            seed=self.seed,
            policy_count=8,
            run_namespace="global-random-test",
        )
        first = generate_policy_histories(config)
        for _ in range(100):
            random.random()
        second = generate_policy_histories(config)
        self.assertEqual(first, second)

    def test_different_seed_changes_valid_content(self) -> None:
        other = generate_policy_histories(
            GeneratorConfig(seed=self.seed + 1, run_namespace="generator-tests")
        )
        self.assertNotEqual(self.histories, other)
        for history in other:
            for event in history:
                self.assertEqual(list(self.validator.iter_errors(event)), [])

    def test_invalid_counts_are_rejected(self) -> None:
        for invalid_count in (0, -1):
            with self.subTest(policy_count=invalid_count):
                with self.assertRaisesRegex(ValueError, "greater than zero"):
                    GeneratorConfig(
                        seed=self.seed,
                        policy_count=invalid_count,
                        run_namespace="invalid-count-test",
                    )

    def test_provenance_contains_reproduction_inputs(self) -> None:
        provenance = generation_provenance(self.config)
        self.assertEqual(provenance["seed"], self.seed)
        self.assertEqual(provenance["policy_count"], 100)
        self.assertEqual(provenance["run_namespace"], "generator-tests")
        self.assertEqual(provenance["run_identity"], run_identity(self.config))
        self.assertEqual(
            provenance["configuration_sha256"], configuration_digest(self.config)
        )
        self.assertEqual(provenance["generator_version"], "0.2.0")

    def test_custom_simulation_start_controls_histories_and_provenance(self) -> None:
        start = datetime(2026, 5, 4, tzinfo=timezone.utc)
        config = GeneratorConfig(
            seed=self.seed,
            policy_count=4,
            run_namespace="custom-start",
            simulation_start=start,
        )
        histories = generate_policy_histories(config)
        issuance_times = [
            datetime.fromisoformat(history[0]["occurred_at"].replace("Z", "+00:00"))
            for history in histories
        ]
        self.assertTrue(all(value >= start for value in issuance_times))
        self.assertTrue(all(value < start.replace(month=6) for value in issuance_times))
        self.assertEqual(
            generation_provenance(config)["simulation_start"],
            "2026-05-04T00:00:00Z",
        )

    def test_namespaces_isolate_all_generator_owned_identifiers(self) -> None:
        first = generate_policy_histories(
            GeneratorConfig(seed=self.seed, run_namespace="corpus-a")
        )
        second = generate_policy_histories(
            GeneratorConfig(seed=self.seed, run_namespace="corpus-b")
        )

        def identifiers(histories: list[list[dict]]) -> set[str]:
            values: set[str] = set()
            for history in histories:
                for event in history:
                    values.add(event["policy_id"])
                    values.add(event["event_id"])
                    for field in (
                        "billing_id",
                        "payment_id",
                        "notice_id",
                        "contact_id",
                    ):
                        value = event["payload"].get(field)
                        if value is not None:
                            values.add(value)
            return values

        self.assertTrue(identifiers(first).isdisjoint(identifiers(second)))

    def test_namespace_validation_is_strict(self) -> None:
        for invalid in ("", "Uppercase", " space", "a" * 65, 3, None):
            with self.subTest(run_namespace=invalid):
                with self.assertRaises((TypeError, ValueError)):
                    GeneratorConfig(seed=self.seed, run_namespace=invalid)  # type: ignore[arg-type]

    def test_every_config_field_participates_in_run_identity(self) -> None:
        baseline = self.config
        variants = (
            GeneratorConfig(seed=self.seed + 1, run_namespace="generator-tests"),
            GeneratorConfig(
                seed=self.seed,
                policy_count=99,
                run_namespace="generator-tests",
            ),
            GeneratorConfig(seed=self.seed, run_namespace="generator-tests-other"),
            GeneratorConfig(
                seed=self.seed,
                run_namespace="generator-tests",
                simulation_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
        )
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertNotEqual(run_identity(baseline), run_identity(variant))

    def test_provenance_verification_rejects_mismatch(self) -> None:
        provenance = generation_provenance(self.config)
        verify_generation_provenance(self.config, provenance)
        changed = {**provenance, "policy_count": 99}
        with self.assertRaisesRegex(ValueError, "does not match"):
            verify_generation_provenance(self.config, changed)

    def test_corrected_api_cannot_silently_select_legacy_generation(self) -> None:
        with self.assertRaisesRegex(TypeError, "GeneratorConfig"):
            generate_policy_histories(self.seed)  # type: ignore[arg-type]

    def test_legacy_path_reproduces_v1_identifiers_and_provenance(self) -> None:
        histories = generate_legacy_policy_histories(self.seed, 1)
        self.assertEqual(histories[0][0]["policy_id"], "pol_000001000000")
        self.assertEqual(histories[0][0]["event_id"], "evt_000001000001")
        self.assertEqual(
            legacy_generation_provenance(self.seed, 1),
            {
                "generator_version": "0.1.0",
                "schema_version": "1.0.0",
                "seed": self.seed,
                "policy_count": 1,
                "simulation_start": "2024-01-01T00:00:00Z",
            },
        )

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
