import math
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator.v2_config import (  # noqa: E402
    V2_BILLING_FREQUENCIES,
    V2_FINAL_HOLDOUT_STATUS,
    V2_RANDOM_DOMAINS,
    V2_ROLE_PROPORTIONS,
    V2CorpusConfig,
    canonical_v2_configuration,
    v2_configuration_digest,
    v2_domain_seed,
    v2_run_identity,
)


class V2CorpusConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = V2CorpusConfig(seed=20260901, run_namespace="r2-05-test")

    def test_defaults_match_the_approved_r2_04_contract(self) -> None:
        self.assertEqual(self.config.policy_count, 3600)
        self.assertEqual(self.config.cohort_count, 24)
        self.assertEqual(self.config.policies_per_cohort, 150)
        self.assertEqual(self.config.seasoning_days, 30)
        self.assertEqual(self.config.observation_cadence_days, 90)
        self.assertEqual(self.config.label_horizon_days, 90)
        self.assertEqual(
            self.config.issuance_start,
            datetime(2022, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            self.config.follow_up_watermark,
            datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        )
        self.assertEqual(V2_BILLING_FREQUENCIES, (
            "monthly", "quarterly", "semiannual", "annual"
        ))
        self.assertAlmostEqual(sum(value for _, value in V2_ROLE_PROPORTIONS), 1.0)

    def test_canonical_configuration_records_versions_and_holdout_absence(self) -> None:
        canonical = canonical_v2_configuration(self.config)
        self.assertEqual(canonical["simulator_contract_version"], "2.0.0")
        self.assertEqual(canonical["observation_contract_version"], "2.0.0")
        self.assertEqual(canonical["label_policy_version"], "2.0.0")
        self.assertEqual(canonical["acceptance_protocol_version"], "1.0.0")
        self.assertEqual(canonical["final_holdout_status"], V2_FINAL_HOLDOUT_STATUS)
        self.assertNotIn("final_holdout_seed", canonical)

    def test_identity_is_exact_and_namespace_separated(self) -> None:
        same = V2CorpusConfig(seed=20260901, run_namespace="r2-05-test")
        other = replace(self.config, run_namespace="r2-05-other")
        self.assertEqual(v2_configuration_digest(self.config), v2_configuration_digest(same))
        self.assertEqual(v2_run_identity(self.config), v2_run_identity(same))
        self.assertNotEqual(v2_run_identity(self.config), v2_run_identity(other))

    def test_named_random_domains_are_stable_and_separate(self) -> None:
        first = v2_domain_seed(self.config, "frailty", "policy-1")
        self.assertEqual(first, v2_domain_seed(self.config, "frailty", "policy-1"))
        self.assertNotEqual(
            first,
            v2_domain_seed(self.config, "terminal_outcome", "policy-1"),
        )
        self.assertEqual(len(V2_RANDOM_DOMAINS), len(set(V2_RANDOM_DOMAINS)))
        with self.assertRaisesRegex(ValueError, "frozen v2 random-domain"):
            v2_domain_seed(self.config, "caller_selected", "policy-1")

    def test_invalid_integer_and_structural_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "seed must be an integer"):
            V2CorpusConfig(seed=True, run_namespace="invalid")
        with self.assertRaisesRegex(ValueError, "policy_count must equal"):
            replace(self.config, policy_count=3599)
        with self.assertRaisesRegex(ValueError, "cadence_days must equal"):
            replace(self.config, observation_cadence_days=30)

    def test_invalid_namespace_time_and_mode_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid format"):
            replace(self.config, run_namespace="Invalid Namespace")
        with self.assertRaisesRegex(ValueError, "must use UTC"):
            replace(self.config, issuance_start=datetime(2022, 1, 1))
        with self.assertRaisesRegex(ValueError, "drift_scenario is unsupported"):
            replace(self.config, drift_scenario="invented")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "signal_mode is unsupported"):
            replace(self.config, signal_mode="invented")  # type: ignore[arg-type]

    def test_nonfinite_and_out_of_range_rates_are_rejected(self) -> None:
        for value in (-0.01, 1.01, math.nan, math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    replace(self.config, event_censoring_rate=value)
        with self.assertRaises(ValueError):
            replace(self.config, frailty_standard_deviation=math.nan)


if __name__ == "__main__":
    unittest.main()
