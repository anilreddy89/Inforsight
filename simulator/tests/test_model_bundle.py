"""Unit tests for Phase 2.10 release model bundle and standalone inference engine."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import unittest

import numpy as np

from inforsight_simulator.bundle import (
    MODEL_BUNDLE_ARTIFACT_VERSION,
    MODEL_BUNDLE_CONTRACT_VERSION,
    BundledInferenceEngine,
    ModelBundle,
    ScoringResult,
)
from inforsight_simulator.explanations import CATEGORICAL_FEATURES, NUMERIC_FEATURES

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUNDLE_PATH = REPO_ROOT / "docs" / "experiments" / "phase-02-10-model-bundle.json"
MANIFEST_PATH = REPO_ROOT / "docs" / "experiments" / "phase-02-10-model-bundle-manifest.json"


def _sample_observation() -> dict[str, object]:
    """Provide a valid raw observation dictionary conforming to V6 schema."""
    return {
        "tenure_days": 0.55,
        "premium_amount_cents": 0.96,
        "recent_delay_days": 0.11,
        "recent_failed_payment_count": 0.01,
        "recent_retry_count": 0.01,
        "recent_recovery_count": 0.008,
        "arrears_duration_days": 0.012,
        "rolling_on_time_rate": 0.27,
        "rolling_payment_count": 0.16,
        "recent_notice_count": 0.11,
        "recent_contact_count": 0.10,
        "payment_attribute_missing": 0.02,
        "contact_attribute_missing": 0.0,
        "product_type": "fictional_term_life",
        "billing_frequency": "monthly",
        "notice_category": "none",
        "contact_category": "none",
    }


class TestModelBundle(unittest.TestCase):
    """Test suite for release model bundle serialization, inference, and invariants."""

    def setUp(self) -> None:
        self.assertTrue(
            BUNDLE_PATH.exists(),
            f"Release model bundle not found at {BUNDLE_PATH}. Run scripts/run_model_bundle.py --write first.",
        )
        self.bundle = ModelBundle.load(BUNDLE_PATH)
        self.engine = BundledInferenceEngine(self.bundle)

    def test_bundle_versions_and_metadata(self) -> None:
        """Verify model bundle contract versions and architecture dimensions."""
        self.assertEqual(self.bundle.bundle_version, MODEL_BUNDLE_CONTRACT_VERSION)
        self.assertEqual(self.bundle.bundle_id, "inforsight-v6-logistic-platt-20260817")
        self.assertEqual(self.bundle.base_model.family, "LogisticRegression")
        self.assertEqual(self.bundle.base_model.penalty, "l2")
        self.assertEqual(self.bundle.base_model.c_param, 1.0)
        self.assertEqual(self.bundle.base_model.solver, "liblinear")
        self.assertEqual(self.bundle.calibrator.method, "platt_scaling")

        # Dimensions: 13 numeric + 15 categorical one-hot indicators = 28 columns
        self.assertEqual(len(self.bundle.preprocessor.numeric), len(NUMERIC_FEATURES))
        self.assertEqual(len(self.bundle.preprocessor.categorical), len(CATEGORICAL_FEATURES))
        self.assertEqual(len(self.bundle.preprocessor.ordered_columns), 28)
        self.assertEqual(len(self.bundle.base_model.raw_coefficients), 28)
        self.assertEqual(len(self.bundle.calibrator.calibrated_coefficients), 28)
        self.assertEqual(len(self.bundle.explainer_reference.background_column_means), 28)

    def test_bundle_serialization_roundtrip(self) -> None:
        """Verify that ModelBundle serializes to/from dict and JSON with exact fidelity."""
        bundle_dict = self.bundle.to_dict()
        reconstructed = ModelBundle.from_dict(bundle_dict)
        self.assertEqual(self.bundle, reconstructed)

        json_str = self.bundle.to_json()
        self.assertNotIn("NaN", json_str)
        self.assertNotIn("Infinity", json_str)
        from_json_bundle = ModelBundle.from_json(json_str)
        self.assertEqual(self.bundle, from_json_bundle)

    def test_transform_features(self) -> None:
        """Verify feature transformation vector shape and standardization."""
        obs = _sample_observation()
        vec = self.engine.transform_features(obs)
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (28,))
        self.assertFalse(np.isnan(vec).any())

        # Verify numeric standardization for tenure_days (first column)
        spec = self.bundle.preprocessor.numeric["tenure_days"]
        expected_scaled = (0.55 - spec.mean) / spec.scale
        self.assertAlmostEqual(vec[0], expected_scaled, places=12)

    def test_score_record_scoring_result(self) -> None:
        """Verify that score_record computes calibrated probabilities and explanations."""
        obs = _sample_observation()
        result = self.engine.score_record(obs)

        self.assertIsInstance(result, ScoringResult)
        self.assertIsInstance(result.raw_logit, float)
        self.assertIsInstance(result.calibrated_logit, float)
        self.assertIsInstance(result.calibrated_probability, float)
        self.assertTrue(0.0 <= result.calibrated_probability <= 1.0)
        self.assertIn(result.risk_tier, [t.name for t in self.bundle.operational_policy.risk_tiers])

        # Mathematical link: cal_logit = A * raw_logit + B
        expected_cal_logit = self.bundle.calibrator.param_a * result.raw_logit + self.bundle.calibrator.param_b
        self.assertAlmostEqual(result.calibrated_logit, expected_cal_logit, places=12)

        # Mathematical link: cal_prob = 1 / (1 + exp(-cal_logit))
        expected_prob = 1.0 / (1.0 + math.exp(-expected_cal_logit))
        self.assertAlmostEqual(result.calibrated_probability, expected_prob, places=12)

    def test_additive_calibrated_logit_reconstruction(self) -> None:
        """Verify that calibrated intercept and coefficients reconstruct calibrated logit exactly."""
        obs = _sample_observation()
        x = self.engine.transform_features(obs)
        result = self.engine.score_record(obs)

        cal_coef_arr = np.array([
            self.bundle.calibrator.calibrated_coefficients[c] for c in self.bundle.preprocessor.ordered_columns
        ], dtype=float)
        reconstructed_cal_logit = self.bundle.calibrator.calibrated_intercept + float(np.dot(cal_coef_arr, x))
        self.assertAlmostEqual(result.calibrated_logit, reconstructed_cal_logit, places=12)

    def test_centered_shap_efficiency_property(self) -> None:
        """Verify the efficiency property: sum(SHAP) = calibrated_logit - base_value_logit."""
        obs = _sample_observation()
        result = self.engine.score_record(obs)

        total_shap = sum(result.root_centered_shap.values())
        expected_diff = result.calibrated_logit - self.bundle.explainer_reference.base_value_logit
        self.assertAlmostEqual(total_shap, expected_diff, places=12)

    def test_operational_tier_and_authority_boundaries(self) -> None:
        """Verify operational policy thresholds and ADR 0002 authority rules."""
        policy = self.bundle.operational_policy
        self.assertEqual(len(policy.risk_tiers), 4)
        self.assertEqual(len(policy.review_queues), 3)

        # Check tier bounds
        tiers = policy.risk_tiers
        self.assertEqual(tiers[0].name, "Tier 1: Low Risk")
        self.assertEqual((tiers[0].min_prob, tiers[0].max_prob), (0.0, 0.10))

        self.assertEqual(tiers[1].name, "Tier 2: Moderate Risk")
        self.assertEqual((tiers[1].min_prob, tiers[1].max_prob), (0.10, 0.25))

        self.assertEqual(tiers[2].name, "Tier 3: High Risk")
        self.assertEqual((tiers[2].min_prob, tiers[2].max_prob), (0.25, 0.50))

        self.assertEqual(tiers[3].name, "Tier 4: Critical Risk")
        self.assertEqual((tiers[3].min_prob, tiers[3].max_prob), (0.50, 1.0))

        # Check authority boundaries compliance
        auth = policy.authority_boundaries
        self.assertIn("tier_1_perception_role", auth)
        self.assertIn("non_causal_boundary", auth)
        self.assertIn("tier_2_deterministic_rules_required", auth)
        self.assertIn("tier_4_licensed_human_approval", auth)

    def test_manifest_cryptographic_lineage(self) -> None:
        """Verify manifest SHA256 integrity and clean-room final holdout isolation."""
        self.assertTrue(MANIFEST_PATH.exists(), f"Manifest not found at {MANIFEST_PATH}")

        with open(BUNDLE_PATH, "rb") as f:
            computed_bundle_sha = hashlib.sha256(f.read()).hexdigest()

        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertEqual(manifest["lineage"]["bundle_sha256"], computed_bundle_sha)
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")
        self.assertTrue(manifest["reproducibility_validation"]["bit_for_bit_verified"])
        self.assertTrue(manifest["reproducibility_validation"]["reconstruction_verified"])
        self.assertEqual(manifest["reproducibility_validation"]["tier_concordance_rate"], 1.0)
        self.assertLessEqual(manifest["reproducibility_validation"]["max_probability_divergence"], 1e-12)
        self.assertLessEqual(manifest["reproducibility_validation"]["max_logit_divergence"], 1e-12)
        self.assertLessEqual(manifest["reproducibility_validation"]["max_reconstruction_divergence"], 1e-12)


if __name__ == "__main__":
    unittest.main()
