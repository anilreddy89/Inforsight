import sys
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

SIMULATOR_DIR = Path(__file__).resolve().parents[1]
SRC = SIMULATOR_DIR / "src"
sys.path.insert(0, str(SRC))

from inforsight_simulator import (  # noqa: E402
    V2CorpusConfig,
    competing_hazards,
    corpus_jsonl,
    cumulative_incidence,
    generate_v2_corpus,
    observable_oracle,
    validate_v2_corpus,
    validate_v2_feature_payload,
)


class V2CorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = V2CorpusConfig(
            seed=20260901,
            run_namespace="v2-corpus-test",
            policy_count=8,
            cohort_count=1,
            policies_per_cohort=8,
            follow_up_watermark=datetime(2022, 10, 1, tzinfo=timezone.utc),
        )
        cls.corpus = generate_v2_corpus(cls.config)

    def test_generation_is_structurally_and_byte_deterministic(self) -> None:
        repeated = generate_v2_corpus(self.config)
        self.assertEqual(self.corpus, repeated)
        self.assertEqual(
            corpus_jsonl(self.corpus.observations),
            corpus_jsonl(repeated.observations),
        )

    def test_recurring_episodes_are_unique_and_non_overlapping(self) -> None:
        by_policy: dict[str, list] = {}
        for row in self.corpus.observations:
            by_policy.setdefault(row.policy_id, []).append(row)
        self.assertTrue(any(len(rows) > 1 for rows in by_policy.values()))
        for rows in by_policy.values():
            for previous, current in zip(rows, rows[1:]):
                self.assertLessEqual(previous.horizon_end, current.as_of)
        validate_v2_corpus(self.corpus, self.config)

    def test_oracle_is_separate_and_bound_to_observations(self) -> None:
        self.assertEqual(
            [row.observation_id for row in self.corpus.observations],
            [row.observation_id for row in self.corpus.oracle_sidecar],
        )
        public = self.corpus.observations[0].to_dict()
        self.assertNotIn("oracle_conditional", public)
        self.assertNotIn("latent_frailty", public)
        self.assertNotIn("outcome_uniform_draw", public)

    def test_competing_hazard_and_cumulative_incidence_equations(self) -> None:
        features = self.corpus.observations[0].features
        lapse, surrender, continuation = competing_hazards(
            features, 0.0, signal_mode="signal_present", drift_scenario="stable"
        )
        self.assertAlmostEqual(lapse + surrender + continuation, 1.0, places=14)
        self.assertLess(lapse + surrender, 0.20)
        lapse_90, surrender_90, union = cumulative_incidence(lapse, surrender)
        self.assertAlmostEqual(union, 1.0 - continuation**3, places=14)
        self.assertAlmostEqual(union, lapse_90 + surrender_90, places=14)

    def test_observable_oracle_is_bounded_and_repeatable(self) -> None:
        features = self.corpus.observations[0].features
        first = observable_oracle(
            features, signal_mode="signal_present", drift_scenario="stable"
        )
        second = observable_oracle(
            features, signal_mode="signal_present", drift_scenario="stable"
        )
        self.assertEqual(first, second)
        self.assertTrue(all(0.0 < value < 1.0 for value in first))
        self.assertAlmostEqual(first[2], first[0] + first[1], places=14)

    def test_null_signal_removes_observable_driver_effects(self) -> None:
        first = self.corpus.observations[0].features
        changed = replace(
            first,
            premium_amount_cents=first.premium_amount_cents + 10000,
            recent_failed_payment_count=first.recent_failed_payment_count + 2,
        )
        self.assertEqual(
            competing_hazards(
                first, 0.1, signal_mode="null_signal", drift_scenario="stable"
            ),
            competing_hazards(
                changed, 0.1, signal_mode="null_signal", drift_scenario="stable"
            ),
        )

    def test_public_features_contain_no_protected_field_names(self) -> None:
        prohibited = {"oracle", "frailty", "draw", "scenario", "role", "outcome"}
        keys = set(self.corpus.observations[0].to_dict()["features"])
        self.assertTrue(all(not any(token in key for token in prohibited) for key in keys))
        validate_v2_feature_payload(self.corpus.observations[0].features)
        nested = self.corpus.observations[0].to_dict()["features"]
        nested["oracle_wrapper"] = {"latent_frailty": 0.5}
        with self.assertRaises(ValueError):
            validate_v2_feature_payload(nested)

    def test_corrections_are_new_immutable_referencing_events(self) -> None:
        config = replace(
            self.config,
            policy_count=40,
            policies_per_cohort=40,
            run_namespace="v2-correction-test",
        )
        corpus = generate_v2_corpus(config)
        events = [event for history in corpus.histories for event in history]
        by_id = {event["event_id"]: event for event in events}
        corrections = [event for event in events if event["event_type"] == "event.corrected"]
        self.assertTrue(corrections)
        for correction in corrections:
            source = by_id[correction["payload"]["corrected_event_id"]]
            self.assertEqual(source["event_type"], "behavior.snapshot")
            self.assertGreater(correction["ingested_at"], source["ingested_at"])

    def test_dual_time_visibility_excludes_late_ingested_events(self) -> None:
        events_by_policy = {
            history[0]["policy_id"]: history for history in self.corpus.histories
        }
        for row in self.corpus.observations:
            history = events_by_policy[row.policy_id]
            expected = {
                event["event_id"]
                for event in history
                if event["effective_at"] <= row.as_of and event["ingested_at"] <= row.as_of
            }
            self.assertEqual(set(row.visible_event_ids), expected)
            self.assertTrue(all(
                event["event_id"] not in row.visible_event_ids
                for event in history
                if event["effective_at"] > row.as_of or event["ingested_at"] > row.as_of
            ))


if __name__ == "__main__":
    unittest.main()
