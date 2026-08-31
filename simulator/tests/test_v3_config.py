import math
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator import (  # noqa: E402
    V3CorpusConfig, artifact_id, canonical_json_bytes, intervention_manifest,
    primitive_normal, primitive_uniform, scenario_configuration, stable_identifier,
    stream_set_id,
)


class V3ConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = V3CorpusConfig()

    def test_default_is_frozen_non_final_design(self) -> None:
        self.assertEqual(self.config.policy_count, 14_400)
        self.assertEqual(self.config.cohort_count, 24)
        self.assertEqual(self.config.policies_per_cohort, 600)

    def test_scenarios_share_stream_set_but_not_artifact(self) -> None:
        null = replace(self.config, scenario="null_signal")
        self.assertEqual(stream_set_id(self.config), stream_set_id(null))
        self.assertNotEqual(artifact_id(self.config), artifact_id(null))

    def test_uniform_is_open_interval_and_repeatable(self) -> None:
        first = primitive_uniform(self.config, "frailty", "policy")
        self.assertEqual(first, primitive_uniform(self.config, "frailty", "policy"))
        self.assertGreater(first, 0)
        self.assertLess(first, 1)
        self.assertTrue(math.isfinite(primitive_normal(self.config, "frailty", "policy")))
        self.assertEqual(primitive_normal(self.config, "frailty", "policy"), -1.2940649404)

    def test_domain_arity_and_unknown_domain_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            primitive_uniform(self.config, "frailty")
        with self.assertRaises(ValueError):
            primitive_uniform(self.config, "caller", "x")

    def test_identifier_is_v3_namespaced(self) -> None:
        self.assertRegex(stable_identifier("pol", self.config, "x"), r"^v3-pol-[0-9a-f]{24}$")

    def test_interventions_declare_only_owned_transforms(self) -> None:
        stress = replace(self.config, scenario="stress_drift")
        self.assertEqual(intervention_manifest(stress)["owned_transforms"],
                         ["baseline_log_odds_shift", "mcar_threshold", "delay_mixture"])
        self.assertEqual(scenario_configuration(stress)["settings"]["signal_scale"], "1.00")

    def test_canonical_json_rejects_non_finite_values(self) -> None:
        with self.assertRaises(ValueError):
            canonical_json_bytes({"value": float("nan")})

    def test_invalid_configuration_fails_closed(self) -> None:
        with self.assertRaises(TypeError):
            V3CorpusConfig(base_seed=True)
        with self.assertRaises(ValueError):
            V3CorpusConfig(scenario="caller")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            V3CorpusConfig(policy_count=5, cohort_count=1, policies_per_cohort=4)


if __name__ == "__main__":
    unittest.main()
