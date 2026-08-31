import copy
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator import (  # noqa: E402
    V3CorpusConfig, V3Features, artifact_id, generate_v3_corpus,
    reconstruct_v3_features, stream_set_id, v3_competing_hazards,
    v3_corpus_digest, v3_cumulative_incidence, v3_observable_oracle,
    validate_v3_feature_payload, visible_events,
)


class V3CorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = V3CorpusConfig(
            policy_count=40, cohort_count=1, policies_per_cohort=40,
            namespace="r2-09-test", watermark=datetime(2022, 10, 1, tzinfo=timezone.utc),
        )
        cls.corpus = generate_v3_corpus(cls.config)

    def test_small_corpus_is_deterministic_and_identity_bound(self) -> None:
        duplicate = generate_v3_corpus(self.config)
        self.assertEqual(v3_corpus_digest(self.corpus), v3_corpus_digest(duplicate))
        self.assertEqual(self.corpus.provenance["artifact_id"], artifact_id(self.config))
        self.assertEqual(self.corpus.provenance["stream_set_id"], stream_set_id(self.config))

    def test_observations_have_complete_visible_lineage(self) -> None:
        record = self.corpus.observations[0]
        self.assertEqual(set(record.feature_lineage), set(V3Features.__dataclass_fields__))
        self.assertEqual(tuple(sorted(record.visible_event_ids)), record.visible_event_ids)
        self.assertRegex(record.visible_events_sha256, r"^[0-9a-f]{64}$")

    def test_dual_time_visibility_requires_both_predicates(self) -> None:
        history = list(self.corpus.histories[0])
        cutoff = datetime.fromisoformat(self.corpus.observations[0].as_of.replace("Z", "+00:00"))
        target = next(event for event in history if event["event_type"] == "payment.recorded")
        baseline, _ = reconstruct_v3_features(history, cutoff)
        late_ingestion = copy.deepcopy(history)
        next(event for event in late_ingestion if event["event_id"] == target["event_id"])["ingested_at"] = (cutoff + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        after_ingestion, _ = reconstruct_v3_features(late_ingestion, cutoff)
        self.assertNotEqual(baseline.rolling_payment_count, after_ingestion.rolling_payment_count)
        late_effective = copy.deepcopy(history)
        next(event for event in late_effective if event["event_id"] == target["event_id"])["effective_at"] = (cutoff + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        after_effective, _ = reconstruct_v3_features(late_effective, cutoff)
        self.assertNotEqual(baseline.rolling_payment_count, after_effective.rolling_payment_count)

    def test_visible_events_are_canonically_sorted(self) -> None:
        history = list(reversed(self.corpus.histories[0]))
        cutoff = datetime.fromisoformat(self.corpus.observations[0].as_of.replace("Z", "+00:00"))
        admitted = visible_events(history, cutoff)
        self.assertEqual(admitted, tuple(sorted(admitted, key=lambda event: (
            event["effective_at"], event["ingested_at"], event["event_id"]))))

    def test_hazards_and_oracles_are_valid(self) -> None:
        features = self.corpus.observations[0].features
        hazards = v3_competing_hazards(features, 0, 1)
        self.assertAlmostEqual(sum(hazards), 1)
        self.assertLess(hazards[0] + hazards[1], 0.20)
        conditional = v3_cumulative_incidence(features, 0, signal_scale=1, drift=0)
        observable = v3_observable_oracle(features, signal_scale=1, drift=0)
        for values in (conditional, observable):
            self.assertAlmostEqual(values[0] + values[1], values[2])
            self.assertTrue(all(0 <= value <= 1 for value in values))

    def test_protected_payloads_are_rejected_recursively(self) -> None:
        payload = self.corpus.observations[0].to_dict()["features"]
        validate_v3_feature_payload(payload)
        payload["nested_oracle"] = {"value": 0.5}
        with self.assertRaises(ValueError):
            validate_v3_feature_payload(payload)

    def test_null_reuses_stream_identity(self) -> None:
        null_config = replace(self.config, scenario="null_signal")
        self.assertEqual(stream_set_id(self.config), stream_set_id(null_config))
        self.assertNotEqual(artifact_id(self.config), artifact_id(null_config))
        null_corpus = generate_v3_corpus(null_config)
        stable_events = [event for event in self.corpus.histories[0]
                         if not event["event_type"].startswith("outcome.")]
        null_events = [event for event in null_corpus.histories[0]
                       if not event["event_type"].startswith("outcome.")]
        common = min(len(stable_events), len(null_events))
        self.assertEqual(stable_events[:common], null_events[:common])

    def test_correction_requires_dual_time_visibility(self) -> None:
        for history in self.corpus.histories:
            correction = next((event for event in history if event["event_type"] == "event.corrected"), None)
            if correction is None:
                continue
            cutoff = datetime.fromisoformat(correction["ingested_at"].replace("Z", "+00:00"))
            before, _ = reconstruct_v3_features(history, cutoff - timedelta(seconds=1))
            after, lineage = reconstruct_v3_features(history, cutoff)
            self.assertNotEqual(before.recent_delay_days, after.recent_delay_days)
            self.assertIn(correction["event_id"], lineage["recent_delay_days"])
            return
        self.skipTest("small deterministic fixture contains no correction")

    def test_final_holdout_remains_unmaterialized(self) -> None:
        self.assertEqual(self.corpus.provenance["final_holdout_status"], "not_materialized")


if __name__ == "__main__":
    unittest.main()
