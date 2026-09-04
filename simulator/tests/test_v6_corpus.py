from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import unittest

from inforsight_simulator.v6_config import V6CorpusConfig
from inforsight_simulator.v6_corpus import (
    V6Features, competing_hazards, generate_v6_corpus, observable_oracle,
    public_mechanism_terms, reconstruct_v6_features,
)


class V6CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = V6CorpusConfig(base_seed=20280204, policy_count=48,
                                    cohort_count=2, policies_per_cohort=24)
        cls.corpus = generate_v6_corpus(cls.config)

    def test_separate_v6_types_and_provenance(self) -> None:
        self.assertTrue(all(isinstance(row.features, V6Features)
                            for row in self.corpus.observations))
        self.assertEqual(self.corpus.provenance["simulator_contract_version"], "6.0.0")
        self.assertEqual(self.corpus.provenance["coefficient_registry_version"], "3.0.0")
        self.assertEqual(self.corpus.provenance["random_stream_registry_version"], "3.0.0")
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
            rebuilt, _ = reconstruct_v6_features(histories[row.policy_id], cutoff)
            self.assertEqual(asdict(rebuilt), asdict(row.features))

    def test_bounded_sigmoid_hazard_and_oracle_are_strictly_bounded(self) -> None:
        features = self.corpus.observations[-1].features
        hazards = competing_hazards(features, 0.0, 1)
        self.assertLessEqual(hazards[0] + hazards[1], 0.1500)
        self.assertLess(hazards[0] + hazards[1], 0.20)
        oracle = observable_oracle(features, signal_scale=1.0, drift=0.0)
        self.assertTrue(all(0 < value < 1 for value in oracle))
        doubled = replace(features, recent_failed_payment_count=2)
        self.assertGreater(public_mechanism_terms(doubled)["failed_payments"],
                           public_mechanism_terms(features)["failed_payments"])
        # In v6, bounded sigmoid ensures total hazard <= 0.1500 even under extreme positive frailty!
        extreme_hazards = competing_hazards(doubled, 50.0, 3)
        self.assertLessEqual(extreme_hazards[0] + extreme_hazards[1], 0.1500)
        self.assertLess(extreme_hazards[0] + extreme_hazards[1], 0.20)


if __name__ == "__main__":
    unittest.main()

