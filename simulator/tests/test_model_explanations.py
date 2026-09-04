"""Unit tests for Phase 2.09 model-behavior explanations and action-authority boundaries."""

from __future__ import annotations

from dataclasses import asdict
import math
import unittest

import numpy as np

from inforsight_simulator.calibration import PlattCalibrator
from inforsight_simulator.explanations import (
    CATEGORICAL_FEATURES,
    FEATURE_GROUPS,
    NUMERIC_FEATURES,
    PORTABLE_ARTIFACT_DECIMALS,
    V6_EXPLANATIONS_ARTIFACT_VERSION,
    V6_EXPLANATIONS_CONTRACT_VERSION,
    DirectionalSanityCheck,
    FeatureAttribution,
    GlobalFeatureImportance,
    LocalExplanation,
    ModelExplainer,
    run_explanations_experiment,
)


class DummyPreprocessor:
    """Mock preprocessor supplying known feature column names."""

    def __init__(self, feature_names: tuple[str, ...]) -> None:
        self.feature_names = feature_names


class DummyMatrix:
    """Mock matrix supplying feature values."""

    def __init__(self, values: tuple[tuple[float, ...], ...]) -> None:
        self.values = values


class DummyEstimator:
    """Mock logistic regression estimator."""

    def __init__(self, intercept: float, coefs: list[float]) -> None:
        self.intercept_ = np.array([intercept])
        self.coef_ = np.array([coefs])


class TestModelExplanations(unittest.TestCase):
    """Test suite for exact logit attributions, centered SHAP, and governance boundaries."""

    def setUp(self) -> None:
        self.cols = (
            "rolling_on_time_rate",
            "recent_delay_days",
            "billing_frequency=annual",
            "billing_frequency=monthly",
            "notice_category=none",
            "notice_category=grace_notice",
        )
        self.preprocessor = DummyPreprocessor(self.cols)
        self.raw_intercept = -0.50
        self.raw_coefs = [-0.60, 0.40, 0.30, -0.20, -0.45, 0.25]
        self.base_model = DummyEstimator(self.raw_intercept, self.raw_coefs)
        self.calibrator = PlattCalibrator(slope=0.95, intercept=-0.05, fit_records=100, fit_sha256="test")

        # Mock background with 3 rows
        bg_rows = (
            (0.85, 2.0, 0.0, 1.0, 1.0, 0.0),
            (0.95, 0.0, 0.0, 1.0, 1.0, 0.0),
            (0.70, 5.0, 1.0, 0.0, 0.0, 1.0),
        )
        self.bg_matrix = DummyMatrix(bg_rows)
        self.explainer = ModelExplainer(
            base_model=self.base_model,  # type: ignore
            calibrator=self.calibrator,
            preprocessor=self.preprocessor,  # type: ignore
            background_matrix=self.bg_matrix,  # type: ignore
        )

    def test_version_constants(self) -> None:
        self.assertEqual(V6_EXPLANATIONS_CONTRACT_VERSION, "1.0.0")
        self.assertEqual(V6_EXPLANATIONS_ARTIFACT_VERSION, "1.0.0")
        self.assertEqual(PORTABLE_ARTIFACT_DECIMALS, 4)

    def test_exact_additive_logit_reconstruction_mock(self) -> None:
        """Verify mathematical identity |z_cal - (phi_0 + sum(Phi_k))| < 1e-12 on mock data."""
        x_vec = (0.80, 4.0, 1.0, 0.0, 0.0, 1.0)
        raw_map = {
            "rolling_on_time_rate": 0.80,
            "recent_delay_days": 4.0,
            "billing_frequency": "annual",
            "notice_category": "grace_notice",
        }
        explanation = self.explainer.explain_vector(
            x_vec=x_vec,
            raw_feature_map=raw_map,
            observation_id="obs_001",
            policy_id="pol_001",
            risk_tier="Tier 2: Moderate Risk",
        )

        self.assertLess(explanation.reconstruction_error, 1e-12)
        reconstructed = self.explainer.calibrated_intercept + sum(
            a.attribution_log_odds for a in explanation.root_attributions
        )
        self.assertAlmostEqual(explanation.calibrated_logit, reconstructed, places=12)

        # Centered SHAP efficiency check
        reconstructed_shap = self.explainer.base_value_logit + sum(
            a.centered_shap for a in explanation.root_attributions
        )
        self.assertAlmostEqual(explanation.calibrated_logit, reconstructed_shap, places=12)

    def test_feature_attribution_properties(self) -> None:
        attr = FeatureAttribution(
            feature_name="rolling_on_time_rate",
            feature_group="billing_discipline",
            raw_value=0.98,
            attribution_log_odds=-0.584,
            centered_shap=-0.210,
            direction="risk_decreasing",
        )
        d = asdict(attr)
        self.assertEqual(d["feature_name"], "rolling_on_time_rate")
        self.assertEqual(d["direction"], "risk_decreasing")
        self.assertEqual(d["feature_group"], "billing_discipline")

    def test_full_experiment_reconstruction_and_directionality(self) -> None:
        """Run full experiment and verify all mathematical invariants and sanity checks."""
        res = run_explanations_experiment()

        # Invariant 1: Reconstruction residual < 1e-10 across all 8,782 observations
        recon = res["reconstruction_validation"]
        self.assertTrue(recon["exact_reconstruction_passed"])
        self.assertLess(recon["max_reconstruction_error"], 1e-10)

        # Invariant 2: 17/17 directional sanity checks passed
        checks = res["directional_sanity_checks"]
        self.assertEqual(len(checks), 17)
        for c in checks:
            self.assertEqual(c["status"], "pass", f"Check failed for {c['feature_name']}")
            self.assertIn("actuarial_rationale", c)
            self.assertGreater(len(c["actuarial_rationale"]), 10)

        # Invariant 3: Global importance ranks and sums
        importance = res["global_feature_importance"]
        self.assertEqual(len(importance), 17)
        total_pct = sum(g["relative_importance_pct"] for g in importance)
        self.assertAlmostEqual(total_pct, 100.0, places=1)
        ranks = [g["rank"] for g in importance]
        self.assertEqual(ranks, list(range(1, 18)))
        # Top feature must be rolling_on_time_rate
        self.assertEqual(importance[0]["feature_name"], "rolling_on_time_rate")

        # Invariant 4: Representative case studies for Tiers 1, 2, 3
        cases = res["representative_case_studies"]
        self.assertIn("tier_1_low_risk", cases)
        self.assertIn("tier_2_moderate_risk", cases)
        self.assertIn("tier_3_high_risk", cases)

        p1 = cases["tier_1_low_risk"]["calibrated_probability"]
        p2 = cases["tier_2_moderate_risk"]["calibrated_probability"]
        p3 = cases["tier_3_high_risk"]["calibrated_probability"]
        self.assertLess(p1, 0.10)
        self.assertGreaterEqual(p2, 0.10)
        self.assertLess(p2, 0.25)
        self.assertGreaterEqual(p3, 0.25)
        self.assertLess(p3, 0.50)
        self.assertLess(p1, p2)
        self.assertLess(p2, p3)

        # Drivers present
        for tier_k in ("tier_1_low_risk", "tier_2_moderate_risk", "tier_3_high_risk"):
            c = cases[tier_k]
            self.assertGreater(len(c["top_risk_drivers"]) + len(c["top_protective_drivers"]), 0)
            self.assertLess(c["reconstruction_error"], 1e-10)

        # Invariant 5: ADR 0002 Action-Authority Boundaries
        bounds = res["action_authority_boundaries"]
        self.assertIn("tier_1_perception_role", bounds)
        self.assertIn("non_causal_boundary", bounds)
        self.assertIn("tier_2_deterministic_rules_required", bounds)
        self.assertIn("tier_4_licensed_human_approval", bounds)
        self.assertIn("perception", bounds["tier_1_perception_role"])
        self.assertIn("causal", bounds["non_causal_boundary"])
        self.assertIn("human", bounds["tier_4_licensed_human_approval"])


if __name__ == "__main__":
    unittest.main()

