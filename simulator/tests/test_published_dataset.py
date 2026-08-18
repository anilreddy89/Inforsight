import hashlib
import json
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SIMULATOR_DIR = REPOSITORY_ROOT / "simulator"
SRC = SIMULATOR_DIR / "src"
SCRIPTS = REPOSITORY_ROOT / "scripts"
DATASET_PATH = REPOSITORY_ROOT / "datasets" / "sample-policy-events.jsonl"
MANIFEST_PATH = REPOSITORY_ROOT / "datasets" / "sample-manifest.json"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SCRIPTS))

from build_sample_dataset import (  # noqa: E402
    HISTORIES_PER_SCENARIO,
    SCENARIOS,
    build_artifacts,
    classify_scenario,
    select_sample_histories,
)
from contract_support import policy_event_validator  # noqa: E402
from inforsight_simulator import validate_policy_history  # noqa: E402


class PublishedDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset_bytes = DATASET_PATH.read_bytes()
        cls.manifest_bytes = MANIFEST_PATH.read_bytes()
        cls.manifest = json.loads(cls.manifest_bytes)
        cls.events = [
            json.loads(line)
            for line in cls.dataset_bytes.decode("utf-8").splitlines()
        ]
        grouped: dict[str, list[dict]] = {}
        for event in cls.events:
            grouped.setdefault(event["policy_id"], []).append(event)
        cls.histories = list(grouped.values())

    def test_artifacts_are_byte_identical_to_clean_regeneration(self) -> None:
        expected_dataset, expected_manifest = build_artifacts()
        self.assertEqual(self.dataset_bytes, expected_dataset)
        self.assertEqual(self.manifest_bytes, expected_manifest)

        second_dataset, second_manifest = build_artifacts()
        self.assertEqual((expected_dataset, expected_manifest), (second_dataset, second_manifest))

    def test_repository_check_command_accepts_committed_artifacts(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/build_sample_dataset.py", "--check"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("artifacts are reproducible", result.stdout)

    def test_every_event_and_complete_history_is_valid(self) -> None:
        validator = policy_event_validator()
        for event in self.events:
            with self.subTest(event_id=event["event_id"]):
                errors = [error.message for error in validator.iter_errors(event)]
                self.assertEqual(errors, [])

        for history in self.histories:
            with self.subTest(policy_id=history[0]["policy_id"]):
                validate_policy_history(history)

    def test_manifest_integrity_and_composition_match_artifact(self) -> None:
        composition = self.manifest["composition"]
        self.assertEqual(
            self.manifest["artifact"]["sha256"],
            hashlib.sha256(self.dataset_bytes).hexdigest(),
        )
        self.assertEqual(composition["policy_count"], len(self.histories))
        self.assertEqual(composition["event_count"], len(self.events))
        self.assertEqual(
            composition["event_type_counts"],
            dict(sorted(Counter(event["event_type"] for event in self.events).items())),
        )
        self.assertEqual(
            composition["product_variant_counts"],
            dict(
                sorted(
                    Counter(
                        history[0]["payload"]["product_variant"]
                        for history in self.histories
                    ).items()
                )
            ),
        )
        self.assertEqual(
            composition["scenario_counts"],
            {
                scenario: sum(
                    classify_scenario(history) == scenario
                    for history in self.histories
                )
                for scenario in SCENARIOS
            },
        )

    def test_sample_has_required_coverage_and_unique_identifiers(self) -> None:
        self.assertEqual(len(self.histories), len(SCENARIOS) * HISTORIES_PER_SCENARIO)
        self.assertEqual(
            Counter(classify_scenario(history) for history in self.histories),
            Counter({scenario: HISTORIES_PER_SCENARIO for scenario in SCENARIOS}),
        )
        self.assertEqual(
            {event["event_type"] for event in self.events},
            {
                "billing.premium_due",
                "notice.sent",
                "outcome.lapsed",
                "outcome.surrendered",
                "payment.failed",
                "payment.received",
                "policy.issued",
                "policy.status_changed",
                "service.contact_recorded",
            },
        )
        self.assertEqual(
            {history[0]["payload"]["product_variant"] for history in self.histories},
            {"fictional_term_life", "fictional_whole_life"},
        )
        policy_ids = [history[0]["policy_id"] for history in self.histories]
        event_ids = [event["event_id"] for event in self.events]
        self.assertEqual(len(policy_ids), len(set(policy_ids)))
        self.assertEqual(len(event_ids), len(set(event_ids)))

    def test_sample_contains_only_bounded_structured_fields(self) -> None:
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

    def test_incomplete_source_corpus_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot satisfy sample composition"):
            select_sample_histories(self.histories[:1])


if __name__ == "__main__":
    unittest.main()
