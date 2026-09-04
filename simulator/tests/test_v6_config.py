from __future__ import annotations

from dataclasses import replace
import unittest

from inforsight_simulator.v6_config import (
    V6CorpusConfig, artifact_id, complete_configuration, primitive_uniform,
    stream_set_id,
)


class V6ConfigTests(unittest.TestCase):
    def test_versions_and_event_support_are_frozen(self) -> None:
        value = complete_configuration(V6CorpusConfig())
        self.assertEqual(value["contract_version"], "6.0.0")
        self.assertEqual(value["coefficient_registry_version"], "3.0.0")
        self.assertEqual(value["random_stream_registry_version"], "3.0.0")
        self.assertEqual(value["acceptance_protocol_version"], "3.0.0")
        self.assertEqual(value["event_support"], {
            "annual": 1, "monthly": 12, "quarterly": 4, "semiannual": 2,
            "missing_or_failed_opportunity_retained": True,
        })

    def test_matched_null_shares_streams_but_not_artifact(self) -> None:
        signal = V6CorpusConfig(base_seed=20280201, scenario="stable")
        null = replace(signal, scenario="null_signal")
        self.assertEqual(stream_set_id(signal), stream_set_id(null))
        self.assertNotEqual(artifact_id(signal), artifact_id(null))

    def test_scheduled_opportunity_is_a_registered_stream(self) -> None:
        config = V6CorpusConfig()
        value = primitive_uniform(config, "scheduled_payment_opportunity", "policy", 1)
        self.assertGreater(value, 0)
        self.assertLess(value, 1)
        with self.assertRaisesRegex(ValueError, "requires 2 keys"):
            primitive_uniform(config, "scheduled_payment_opportunity", "policy")


if __name__ == "__main__":
    unittest.main()

