"""Integration and unit tests for Inforsight Model Serving Gateway."""

from __future__ import annotations

import time
import unittest
from fastapi.testclient import TestClient

from inforsight_simulator.bundle import ModelBundle, BundledInferenceEngine
from inforsight_simulator.v6_corpus import generate_v6_corpus, V6CorpusConfig
from inforsight_simulator.v6_evaluation import _feature_map
from serving.app import create_app, DEFAULT_BUNDLE_PATH
from serving.models import ADR_0002_AUTHORITY_BOUNDARY_NOTICE


class TestServingGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import hashlib
        cls.bundle = ModelBundle.load(DEFAULT_BUNDLE_PATH)
        cls.engine = BundledInferenceEngine(cls.bundle)
        cls.expected_digest = hashlib.sha256(DEFAULT_BUNDLE_PATH.read_bytes()).hexdigest()
        cls.app = create_app(DEFAULT_BUNDLE_PATH)
        cls.client = TestClient(cls.app)

        # Build sample test feature map from non_final_evaluation observations
        corpus = generate_v6_corpus(V6CorpusConfig(base_seed=20280201))
        eval_obs = [r for r in corpus.observations if r.role == "non_final_evaluation"]
        cls.sample_obs = eval_obs[:5]
        cls.sample_feature_maps = [_feature_map(obs) for obs in cls.sample_obs]

    def test_health_endpoint(self) -> None:
        """GET /health verifies engine liveness and SHA-256 digest match."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["engine_status"], "ready")
        self.assertEqual(data["bundle_id"], "inforsight-v6-logistic-platt-20260817")
        self.assertEqual(data["bundle_sha256"], self.expected_digest)
        self.assertTrue(data["bundle_sha256"].startswith("7ac292"))

    def test_model_info_endpoint(self) -> None:
        """GET /v1/model/info returns full model bundle metadata, risk tiers, and authority boundaries."""
        resp = self.client.get("/v1/model/info")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["bundle_id"], "inforsight-v6-logistic-platt-20260817")
        self.assertEqual(data["feature_count"], 28)
        self.assertEqual(len(data["ordered_columns"]), 28)
        self.assertEqual(len(data["risk_tiers"]), 4)
        self.assertEqual(len(data["review_queues"]), 3)
        self.assertIn("tier_1_perception_role", data["authority_boundaries"])

    def test_single_policy_scoring_bit_for_bit(self) -> None:
        """POST /v1/score produces bit-for-bit identical probabilities to BundledInferenceEngine."""
        fmap = self.sample_feature_maps[0]
        obs = self.sample_obs[0]
        expected_result = self.engine.score_record(fmap)

        payload = {
            "policy_id": obs.policy_id,
            "as_of_date": obs.as_of,
            "features": fmap,
        }
        resp = self.client.post("/v1/score", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Invariance check: probability must match exactly to 6 decimal places (and within 1e-12 of float)
        self.assertEqual(data["policy_id"], obs.policy_id)
        self.assertEqual(data["risk_tier"], expected_result.risk_tier)
        self.assertAlmostEqual(data["calibrated_probability"], expected_result.calibrated_probability, places=6)
        self.assertAlmostEqual(data["calibrated_logit"], expected_result.calibrated_logit, places=6)

    def test_adr_0002_boundary_markers_enforced(self) -> None:
        """Every response payload strictly includes authorized_to_act: false and boundary notice."""
        payload = {
            "policy_id": "POL-TEST-001",
            "as_of_date": "2026-09-01T00:00:00Z",
            "features": self.sample_feature_maps[0],
        }
        resp = self.client.post("/v1/score", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIs(data["authorized_to_act"], False)
        self.assertEqual(data["action_authority_boundary"], ADR_0002_AUTHORITY_BOUNDARY_NOTICE)

    def test_batch_scoring_endpoint(self) -> None:
        """POST /v1/score/batch correctly scores a batch of records."""
        requests = [
            {
                "policy_id": obs.policy_id,
                "as_of_date": obs.as_of,
                "features": fmap,
            }
            for obs, fmap in zip(self.sample_obs, self.sample_feature_maps)
        ]
        resp = self.client.post("/v1/score/batch", json={"requests": requests})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], len(requests))
        self.assertEqual(len(data["scores"]), len(requests))

        for item, obs, fmap in zip(data["scores"], self.sample_obs, self.sample_feature_maps):
            self.assertEqual(item["policy_id"], obs.policy_id)
            self.assertIs(item["authorized_to_act"], False)
            expected = self.engine.score_record(fmap)
            self.assertAlmostEqual(item["calibrated_probability"], expected.calibrated_probability, places=6)

    def test_input_validation_missing_feature(self) -> None:
        """Request missing required features returns HTTP 422 Unprocessable Entity."""
        fmap_invalid = dict(self.sample_feature_maps[0])
        del fmap_invalid["rolling_on_time_rate"]  # remove required feature

        payload = {
            "policy_id": "POL-INVALID",
            "as_of_date": "2026-09-01T00:00:00Z",
            "features": fmap_invalid,
        }
        resp = self.client.post("/v1/score", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_input_validation_extra_feature(self) -> None:
        """Request with unknown extra features returns HTTP 422 Unprocessable Entity."""
        fmap_invalid = dict(self.sample_feature_maps[0])
        fmap_invalid["unauthorized_shortcut_leakage"] = 999.0

        payload = {
            "policy_id": "POL-INVALID",
            "as_of_date": "2026-09-01T00:00:00Z",
            "features": fmap_invalid,
        }
        resp = self.client.post("/v1/score", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_scoring_latency(self) -> None:
        """Single policy scoring execution latency is well under 15ms target."""
        payload = {
            "policy_id": "POL-LATENCY",
            "as_of_date": "2026-09-01T00:00:00Z",
            "features": self.sample_feature_maps[0],
        }
        # Warmup
        self.client.post("/v1/score", json=payload)

        times = []
        for _ in range(50):
            t0 = time.perf_counter()
            resp = self.client.post("/v1/score", json=payload)
            t1 = time.perf_counter()
            self.assertEqual(resp.status_code, 200)
            times.append((t1 - t0) * 1000.0)

        p95_ms = sorted(times)[int(len(times) * 0.95)]
        self.assertLess(p95_ms, 15.0, f"P95 latency {p95_ms:.2f}ms exceeds 15ms threshold")


if __name__ == "__main__":
    unittest.main()
