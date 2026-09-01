from __future__ import annotations

from datetime import datetime, timezone
import unittest

from inforsight_simulator.v3_config import (
    V3CorpusConfig, artifact_id as historical_artifact_id,
    stable_identifier as historical_stable_identifier,
)
from inforsight_simulator.v3_corpus import generate_v3_corpus as generate_historical_corpus
from inforsight_simulator.v3_1_config import (
    V31_ACCEPTANCE_PROTOCOL_VERSION, V31_SIMULATOR_CONTRACT_VERSION,
    V31CorpusConfig, artifact_id, stable_identifier, stream_set_id,
)
from inforsight_simulator.v3_1_corpus import generate_v3_corpus


class V31CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        kwargs = {
            "policy_count": 600, "cohort_count": 1, "policies_per_cohort": 600,
            "watermark": datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        }
        cls.historical_config = V3CorpusConfig(**kwargs)
        cls.config = V31CorpusConfig(**kwargs)
        cls.historical = generate_historical_corpus(cls.historical_config)
        cls.remediated = generate_v3_corpus(cls.config)

    def test_versioned_identity_preserves_streams_and_changes_artifact(self) -> None:
        self.assertEqual(V31_SIMULATOR_CONTRACT_VERSION, "3.1.0")
        self.assertEqual(V31_ACCEPTANCE_PROTOCOL_VERSION, "2.2.0")
        self.assertEqual(stream_set_id(self.config), stream_set_id(self.historical_config))
        self.assertNotEqual(artifact_id(self.config), historical_artifact_id(self.historical_config))
        self.assertEqual(
            stable_identifier("pol", self.config, "2023-01", 7),
            historical_stable_identifier("pol", self.historical_config, "2023-01", 7),
        )

    def test_historical_arrears_defect_is_reproduced_and_remediation_varies(self) -> None:
        historical_arrears = [
            event["payload"]["arrears_days"]
            for history in self.historical.histories for event in history
            if event["event_type"] == "payment.recorded" and event["payload"]["failed"]
        ]
        remediated_arrears = [
            event["payload"]["arrears_days"]
            for history in self.remediated.histories for event in history
            if event["event_type"] == "payment.recorded" and event["payload"]["failed"]
        ]
        self.assertTrue(historical_arrears)
        self.assertEqual(set(historical_arrears), {0})
        self.assertTrue(remediated_arrears)
        self.assertTrue(all(1 <= value <= 60 for value in remediated_arrears))
        self.assertGreater(len(set(remediated_arrears)), 1)

    def test_remediated_corpus_keeps_holdout_unmaterialized(self) -> None:
        self.assertEqual(self.remediated.provenance["final_holdout_status"], "not_materialized")
        self.assertEqual(
            self.remediated.provenance["simulator_contract_version"], "3.1.0",
        )

if __name__ == "__main__":
    unittest.main()
