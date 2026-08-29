import json
import sys
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "simulator" / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator import V2CorpusConfig, generate_v2_corpus  # noqa: E402


class V2ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config = V2CorpusConfig(
            seed=20260901,
            run_namespace="v2-contract-test",
            policy_count=4,
            cohort_count=1,
            policies_per_cohort=4,
            follow_up_watermark=datetime(2022, 7, 1, tzinfo=timezone.utc),
        )
        cls.corpus = generate_v2_corpus(config)

    def _validator(self, name: str) -> Draft202012Validator:
        schema = json.loads((ROOT / "data-contracts" / "v2" / name).read_text())
        return Draft202012Validator(schema, format_checker=FormatChecker())

    def test_generated_events_satisfy_v2_contract(self) -> None:
        validator = self._validator("policy-event.schema.json")
        for history in self.corpus.histories:
            for event in history:
                self.assertEqual(list(validator.iter_errors(event)), [])

    def test_public_observations_satisfy_v2_contract(self) -> None:
        validator = self._validator("observation-record.schema.json")
        for record in self.corpus.observations:
            self.assertEqual(list(validator.iter_errors(record.to_dict())), [])

    def test_oracle_records_satisfy_separate_closed_contract(self) -> None:
        validator = self._validator("oracle-sidecar.schema.json")
        for record in self.corpus.oracle_sidecar:
            self.assertEqual(list(validator.iter_errors(asdict(record))), [])
        public = self.corpus.observations[0].to_dict()
        public["oracle_conditional"] = 0.5
        self.assertTrue(list(self._validator("observation-record.schema.json").iter_errors(public)))


if __name__ == "__main__":
    unittest.main()
