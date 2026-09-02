from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import unittest

from inforsight_simulator.v4_config import V4CorpusConfig
from inforsight_simulator.v4_corpus import (
    V4Features, competing_hazards, generate_v4_corpus, observable_oracle,
    public_mechanism_terms, reconstruct_v4_features,
)


class V4CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = V4CorpusConfig(base_seed=20271101, policy_count=48,
                                    cohort_count=2, policies_per_cohort=24)
        cls.corpus = generate_v4_corpus(cls.config)

    def test_separate_v4_types_and_provenance(self) -> None:
        self.assertTrue(all(isinstance(row.features, V4Features)
                            for row in self.corpus.observations))
        self.assertEqual(self.corpus.provenance["simulator_contract_version"], "4.0.0")
        self.assertEqual(self.corpus.provenance["random_stream_registry_version"], "2.0.0")
        self.assertEqual(self.corpus.provenance["final_holdout_status"], "not_materialized")

    def test_scheduled_opportunities_follow_frequency(self) -> None:
        by_frequency = {}
        for history in self.corpus.histories:
            frequency = history[0]["payload"]["billing_frequency"]
            payments = [event for event in history if event["event_type"] == "payment.recorded"]
            by_frequency[frequency] = max(by_frequency.get(frequency, 0), len(payments))
        self.assertGreater(by_frequency["monthly"], by_frequency["quarterly"])
        self.assertGreater(by_frequency["quarterly"], by_frequency["semiannual"])
        self.assertGreater(by_frequency["semiannual"], by_frequency["annual"])

    def test_feature_reconstruction_has_exact_parity(self) -> None:
        histories = {history[0]["policy_id"]: history for history in self.corpus.histories}
        for row in self.corpus.observations[:50]:
            cutoff = datetime.fromisoformat(row.as_of.replace("Z", "+00:00"))
            rebuilt, _ = reconstruct_v4_features(histories[row.policy_id], cutoff)
            self.assertEqual(asdict(rebuilt), asdict(row.features))

    def test_frozen_hazard_and_oracle_are_finite(self) -> None:
        features = self.corpus.observations[-1].features
        hazards = competing_hazards(features, 0.0, 1)
        self.assertLess(hazards[0] + hazards[1], 0.20)
        oracle = observable_oracle(features, signal_scale=1.0, drift=0.0)
        self.assertTrue(all(0 < value < 1 for value in oracle))
        doubled = replace(features, recent_failed_payment_count=2)
        self.assertGreater(public_mechanism_terms(doubled)["failed_payments"],
                           public_mechanism_terms(features)["failed_payments"])
        with self.assertRaisesRegex(ValueError, "below 0.20"):
            competing_hazards(doubled, 10.0, 3)


if __name__ == "__main__":
    unittest.main()
