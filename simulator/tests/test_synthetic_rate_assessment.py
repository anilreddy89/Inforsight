import json
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPOSITORY_ROOT / "scripts"
SRC = REPOSITORY_ROOT / "simulator" / "src"
RESULT_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "experiments"
    / "phase-01-07-synthetic-rate-assessment.json"
)
REPORT_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "experiments"
    / "phase-01-07-synthetic-rate-assessment.md"
)
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

from assess_synthetic_rates import (  # noqa: E402
    METRIC_DEFINITION_VERSION,
    POLICY_COUNT,
    SCENARIOS,
    SEED,
    assess_histories,
    assessment_bytes,
    build_assessment,
    classify_scenario,
    rate,
)
from inforsight_simulator import generate_legacy_policy_histories  # noqa: E402


class SyntheticRateAssessmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.histories = generate_legacy_policy_histories(SEED, POLICY_COUNT)
        cls.assessment = build_assessment()
        cls.committed = json.loads(RESULT_PATH.read_text(encoding="utf-8"))

    def test_committed_artifact_is_byte_identical_to_clean_assessment(self) -> None:
        self.assertEqual(RESULT_PATH.read_bytes(), assessment_bytes())
        self.assertEqual(assessment_bytes(), assessment_bytes())

    def test_repository_check_command_accepts_committed_artifact(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/assess_synthetic_rates.py", "--check"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("artifact is reproducible", result.stdout)

    def test_canonical_scenario_and_terminal_metrics_are_explicit(self) -> None:
        metrics = self.assessment["metrics"]
        self.assertEqual(metrics["policy_count"], 100)
        self.assertEqual(
            metrics["scenario_mix"]["counts"],
            {scenario: 25 for scenario in SCENARIOS},
        )
        for scenario in SCENARIOS:
            self.assertEqual(
                metrics["scenario_mix"]["proportions"][scenario],
                {
                    "numerator": 25,
                    "denominator": 100,
                    "exact_fraction": "1/4",
                    "decimal": "0.250000",
                },
            )
        self.assertEqual(
            metrics["terminal_outcomes"]["combined"]["decimal"], "0.500000"
        )
        self.assertEqual(
            metrics["grace_recovery"]["value"]["exact_fraction"], "1/2"
        )

    def test_payment_denominator_counts_attempt_events(self) -> None:
        payment = self.assessment["metrics"]["payment_events"]
        self.assertEqual(payment["attempt_count"], 125)
        self.assertEqual(payment["failed_count"], 50)
        self.assertEqual(payment["received_count"], 75)
        self.assertEqual(payment["failure_proportion"]["exact_fraction"], "2/5")
        self.assertEqual(payment["received_proportion"]["exact_fraction"], "3/5")

    def test_rate_rejects_zero_and_negative_denominators(self) -> None:
        for denominator in (0, -1):
            with self.subTest(denominator=denominator):
                with self.assertRaisesRegex(ValueError, "greater than zero"):
                    rate(1, denominator)

    def test_assessment_rejects_empty_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            assess_histories([])

    def test_scenario_classification_uses_structured_events(self) -> None:
        observed = {classify_scenario(history) for history in self.histories}
        self.assertEqual(observed, set(SCENARIOS))

        renamed = deepcopy(self.histories[0])
        for index, event in enumerate(renamed, start=1):
            event["policy_id"] = "pol_abcdef000000"
            event["event_id"] = f"evt_abcdef{index:06x}"
        self.assertEqual(
            classify_scenario(renamed), classify_scenario(self.histories[0])
        )

    def test_source_metadata_and_comparability_values_are_bounded(self) -> None:
        required_source_fields = {
            "source_id",
            "organization",
            "title",
            "publication_date",
            "access_date",
            "url",
            "locators",
            "population",
            "study_period",
            "exposure_basis",
            "definition_note",
            "limitations",
        }
        for source in self.assessment["sources"]:
            self.assertTrue(required_source_fields.issubset(source))
            self.assertTrue(source["url"].startswith("https://www.soa.org/"))
            self.assertEqual(source["access_date"], "2026-08-18")

        allowed = {"comparable", "directional_only", "not_comparable"}
        classifications = {
            comparison["classification"]
            for comparison in self.assessment["comparisons"]
        }
        self.assertTrue(classifications.issubset(allowed))
        self.assertNotIn("comparable", classifications)

    def test_provenance_and_calibration_dispositions_are_complete(self) -> None:
        self.assertEqual(
            self.assessment["metric_definition_version"], METRIC_DEFINITION_VERSION
        )
        self.assertEqual(
            self.assessment["generation"],
            {
                "generator_version": "0.1.0",
                "schema_version": "1.0.0",
                "seed": 20260817,
                "policy_count": 100,
                "simulation_start": "2024-01-01T00:00:00Z",
            },
        )
        dispositions = {
            decision["disposition"]
            for decision in self.assessment["calibration_decisions"]
        }
        self.assertEqual(
            dispositions,
            {
                "retain_as_fixture",
                "parameterize_later",
                "defer_pending_contract_support",
                "no_change",
            },
        )

    def test_report_records_canonical_results_and_source_links(self) -> None:
        report = REPORT_PATH.read_text(encoding="utf-8")
        report_lower = report.lower()
        required_text = (
            "25 active, 25 recovered, 25 lapsed, and 25 surrendered",
            "125 payment-attempt events",
            "https://www.soa.org/globalassets/assets/files/resources/experience-studies/2024/15-22-twlls.pdf",
            "not comparable",
            "retain as fixture",
            "does not establish actuarial credibility",
        )
        for text in required_text:
            with self.subTest(text=text):
                self.assertIn(text.lower(), report_lower)

    def test_loaded_committed_result_matches_built_object(self) -> None:
        self.assertEqual(self.committed, self.assessment)


if __name__ == "__main__":
    unittest.main()
