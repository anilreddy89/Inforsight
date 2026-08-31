import json
import sys
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator import V3CorpusConfig, generate_v3_corpus  # noqa: E402


class V3ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = generate_v3_corpus(V3CorpusConfig(
            policy_count=4, cohort_count=1, policies_per_cohort=4,
            namespace="v3-contract-test", watermark=datetime(2022, 8, 1, tzinfo=timezone.utc),
        ))

    def _validator(self, name: str) -> Draft202012Validator:
        schema = json.loads((ROOT / "data-contracts" / "v3" / name).read_text())
        return Draft202012Validator(schema, format_checker=FormatChecker())

    def test_generated_events_satisfy_closed_contract(self) -> None:
        validator = self._validator("policy-event.schema.json")
        for history in self.corpus.histories:
            for event in history:
                self.assertEqual(list(validator.iter_errors(event)), [])

    def test_observations_satisfy_closed_contract(self) -> None:
        validator = self._validator("observation-record.schema.json")
        for record in self.corpus.observations:
            self.assertEqual(list(validator.iter_errors(record.to_dict())), [])

    def test_oracles_are_separate_and_public_contract_rejects_them(self) -> None:
        oracle_validator = self._validator("oracle-sidecar.schema.json")
        for record in self.corpus.oracle_sidecar:
            serialized = json.loads(json.dumps(asdict(record)))
            self.assertEqual(list(oracle_validator.iter_errors(serialized)), [])
        public = self.corpus.observations[0].to_dict()
        public["latent_frailty"] = 0.0
        self.assertTrue(list(self._validator("observation-record.schema.json").iter_errors(public)))


if __name__ == "__main__":
    unittest.main()
