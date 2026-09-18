"""Focused RH-12 corrected-evidence comparison tests."""

from __future__ import annotations

from datetime import datetime, timezone
import unittest

from inforsight_inference import (
    MODEL_BUNDLE_VERSION,
    MODEL_ID,
    TRUSTED_BUNDLE_SHA256,
    load_verified_runtime,
)
from inforsight_simulator.counterfactual import CounterfactualSimulator
from inforsight_simulator.optimization import compare_portfolio_strategies
from inforsight_simulator.rh12_evidence import (
    build_recommendations,
    fast_resampled_strategy_results,
    occurrence_recommendations,
)
from inforsight_simulator.v6_corpus import V6CorpusConfig, generate_v6_corpus
from inforsight_simulator.v6_evaluation import _feature_map


class RH12EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        corpus = generate_v6_corpus(
            V6CorpusConfig(
                base_seed=20280201,
                policy_count=60,
                cohort_count=6,
                policies_per_cohort=10,
            )
        )
        latest = {}
        frailties = {
            record.observation_id: record.latent_frailty
            for record in corpus.oracle_sidecar
        }
        for observation in corpus.observations:
            if (
                observation.policy_id not in latest
                or observation.as_of > latest[observation.policy_id].as_of
            ):
                latest[observation.policy_id] = observation
        cls.observations = list(latest.values())
        runtime = load_verified_runtime(
            "docs/experiments/phase-02-10-model-bundle.json",
            expected_sha256=TRUSTED_BUNDLE_SHA256,
            expected_bundle_id=MODEL_ID,
            expected_bundle_version=MODEL_BUNDLE_VERSION,
        )
        cls.risk_scores = {
            observation.policy_id: runtime.engine.score_record(
                _feature_map(observation)
            ).calibrated_probability
            for observation in cls.observations
        }
        cls.outcomes = CounterfactualSimulator().simulate_cohort(
            cls.observations,
            frailty_map={
                observation.policy_id: frailties[observation.observation_id]
                for observation in cls.observations
            },
        )
        cls.recommendations = build_recommendations(
            cls.observations, cls.risk_scores, cls.outcomes
        )
        cls.as_of = max(
            datetime.fromisoformat(observation.as_of.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
            for observation in cls.observations
        )

    def test_fast_bootstrap_comparator_matches_contract_comparator(self) -> None:
        public = compare_portfolio_strategies(
            self.recommendations,
            risk_scores=self.risk_scores,
            budget_capacity_usd_micros=5_000_000_000,
            personnel_capacity_seconds=180_000,
            as_of=self.as_of,
            portfolio_id="rh12-test",
        )
        fast = fast_resampled_strategy_results(
            self.recommendations,
            risk_scores=self.risk_scores,
            budget_capacity_usd_micros=5_000_000_000,
            personnel_capacity_seconds=180_000,
            as_of=self.as_of,
            portfolio_id="rh12-test",
        )
        self.assertEqual(
            [result.strategy_id for result in public],
            [result[0] for result in fast],
        )
        for contract_result, fast_result in zip(public, fast):
            self.assertEqual(list(contract_result.selections), list(fast_result[2]))

    def test_duplicate_occurrences_preserve_source_join_identity(self) -> None:
        source_ids = sorted(self.risk_scores)
        source_recommendations = {
            recommendation.policy_id: recommendation
            for recommendation in self.recommendations
        }
        recommendations, risk_scores, occurrence_to_source = occurrence_recommendations(
            source_recommendations,
            self.risk_scores,
            [0, 0, 1],
            source_ids,
        )
        self.assertEqual(
            [recommendation.policy_id for recommendation in recommendations],
            [f"{source_ids[0]}#0", f"{source_ids[0]}#1", f"{source_ids[1]}#2"],
        )
        self.assertEqual(
            occurrence_to_source[f"{source_ids[0]}#1"], source_ids[0]
        )
        self.assertEqual(risk_scores[f"{source_ids[0]}#1"], self.risk_scores[source_ids[0]])


if __name__ == "__main__":
    unittest.main()
