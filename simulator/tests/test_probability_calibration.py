"""Unit tests for Phase 2.08 probability calibration and operational threshold evaluation."""

from __future__ import annotations

import math
import unittest

import numpy as np

from inforsight_simulator.calibration import (
    DEFAULT_CAPACITIES, DEFAULT_COST_RATIOS, DEFAULT_N_BINS,
    IsotonicCalibrator, PlattCalibrator, evaluate_calibration,
    evaluate_decision_curves, evaluate_operational_capacities,
    evaluate_risk_tiers, fit_isotonic_calibrator, fit_platt_calibrator,
)


class TestProbabilityCalibration(unittest.TestCase):
    """Test suite for calibrators, metrics, and operational capacity evaluations."""

    def test_platt_calibrator_properties_and_serialization(self) -> None:
        cal = PlattCalibrator(slope=1.2, intercept=-0.5, fit_records=100, fit_sha256="abc123")
        self.assertEqual(cal.to_dict(), {
            "type": "platt_scaling",
            "slope": 1.2,
            "intercept": -0.5,
            "fit_records": 100,
            "fit_sha256": "abc123",
        })

        restored = PlattCalibrator.from_dict(cal.to_dict())
        self.assertEqual(cal, restored)

        logits = (-5.0, -1.0, 0.0, 1.0, 5.0)
        probs = cal.predict_proba(logits)
        self.assertEqual(len(probs), len(logits))

        # Strictly in (0, 1)
        for p in probs:
            self.assertGreater(p, 0.0)
            self.assertLess(p, 1.0)

        # Strictly monotonic
        for i in range(len(probs) - 1):
            self.assertLess(probs[i], probs[i + 1])

    def test_isotonic_calibrator_properties_and_serialization(self) -> None:
        xs = (0.0, 0.2, 0.5, 0.8, 1.0)
        ys = (0.05, 0.15, 0.45, 0.75, 0.95)
        cal = IsotonicCalibrator(
            x_thresholds=xs, y_thresholds=ys, fit_records=200, fit_sha256="iso456",
        )
        self.assertEqual(cal.to_dict()["knot_count"], 5)

        restored = IsotonicCalibrator.from_dict(cal.to_dict())
        self.assertEqual(cal, restored)

        in_probs = (0.0, 0.1, 0.5, 0.9, 1.0)
        out_probs = cal.predict_proba(in_probs)
        self.assertEqual(len(out_probs), len(in_probs))

        # Weakly monotonic
        for i in range(len(out_probs) - 1):
            self.assertLessEqual(out_probs[i], out_probs[i + 1])

    def test_fit_calibrators_on_synthetic_data(self) -> None:
        rng = np.random.default_rng(42)
        logits = rng.normal(loc=0.0, scale=1.5, size=500)
        true_probs = 1.0 / (1.0 + np.exp(-(0.9 * logits - 0.2)))
        targets = rng.binomial(1, true_probs)

        platt = fit_platt_calibrator(logits, targets, fit_sha256="test_fit")
        self.assertGreater(platt.slope, 0.5)
        self.assertLess(platt.slope, 1.5)
        self.assertEqual(platt.fit_records, 500)

        raw_probs = 1.0 / (1.0 + np.exp(-logits))
        iso = fit_isotonic_calibrator(raw_probs, targets, fit_sha256="test_fit")
        self.assertGreater(len(iso.x_thresholds), 2)
        self.assertEqual(iso.fit_records, 500)

    def test_brier_murphy_decomposition_exact_identity(self) -> None:
        rng = np.random.default_rng(123)
        targets = rng.binomial(1, 0.2, size=1000)
        probs = rng.uniform(0.01, 0.6, size=1000)

        metrics = evaluate_calibration(targets, probs, n_bins=10)

        # Mathematical identity: BS = REL - RES + UNC + bin_discretization_delta
        decomp_sum = metrics.reliability - metrics.resolution + metrics.uncertainty + metrics.bin_discretization_delta
        self.assertAlmostEqual(metrics.brier_score, decomp_sum, places=12)

        # Basic properties
        self.assertGreaterEqual(metrics.ece, 0.0)
        self.assertLessEqual(metrics.ece, 1.0)
        self.assertGreaterEqual(metrics.mce, 0.0)
        self.assertLessEqual(metrics.mce, 1.0)
        self.assertEqual(len(metrics.bins), 10)

    def test_platt_scaling_preserves_auc_exactly(self) -> None:
        rng = np.random.default_rng(999)
        logits = rng.normal(0.0, 1.0, size=300)
        targets = rng.binomial(1, 0.2, size=300)

        platt = PlattCalibrator(slope=0.85, intercept=-0.15, fit_records=300, fit_sha256="sim")
        cal_probs = platt.predict_proba(logits)
        raw_probs = tuple(1.0 / (1.0 + math.exp(-z)) for z in logits)

        metrics_raw = evaluate_calibration(targets, raw_probs)
        metrics_platt = evaluate_calibration(targets, cal_probs)

        # AUC should be mathematically identical (tolerance 1e-12)
        self.assertAlmostEqual(metrics_raw.roc_auc, metrics_platt.roc_auc, places=12)

    def test_operational_capacities_invariants(self) -> None:
        rng = np.random.default_rng(2026)
        N = 1000
        policy_ids = [f"POL-{i // 5:04d}" for i in range(N)]
        probs = rng.beta(2, 10, size=N)
        targets = rng.binomial(1, probs)

        capacities = (0.01, 0.05, 0.10, 0.20)
        points = evaluate_operational_capacities(
            targets, probs, policy_ids, capacities=capacities, n_bootstraps=50, seed=42,
        )
        self.assertEqual(len(points), 4)

        prev_thresh = 1.0
        prev_recall = 0.0
        for pt in points:
            # Threshold must decrease as review capacity increases
            self.assertLessEqual(pt.threshold, prev_thresh)
            prev_thresh = pt.threshold

            # Recall must increase as capacity increases
            self.assertGreaterEqual(pt.recall, prev_recall)
            prev_recall = pt.recall

            # Confusion matrix sum must equal N
            self.assertEqual(pt.tp + pt.fp + pt.tn + pt.fn, N)

            # Check CI validity (lower bound <= upper bound)
            self.assertLessEqual(pt.precision_ci_95[0], pt.precision_ci_95[1])
            self.assertLessEqual(pt.recall_ci_95[0], pt.recall_ci_95[1])
            self.assertLessEqual(pt.lift_ci_95[0], pt.lift_ci_95[1])
            self.assertLessEqual(pt.net_benefit_ci_95[0], pt.net_benefit_ci_95[1])

    def test_decision_curves_utility(self) -> None:
        rng = np.random.default_rng(777)
        targets = rng.binomial(1, 0.15, size=500)
        # Well-discriminating probabilities
        probs = np.where(targets == 1, rng.beta(5, 2, size=500), rng.beta(1, 5, size=500))

        curves = evaluate_decision_curves(targets, probs, cost_ratios=DEFAULT_COST_RATIOS)
        self.assertEqual(len(curves), len(DEFAULT_COST_RATIOS))

        for c in curves:
            # Model net benefit should outperform treat all and treat none
            self.assertGreaterEqual(c["net_benefit_model"], c["net_benefit_treat_none"])
            self.assertGreater(c["benefit_over_treat_all"], 0.0)

    def test_risk_tiers_exhaustiveness(self) -> None:
        probs = (0.02, 0.05, 0.09, 0.12, 0.19, 0.25, 0.40)
        targets = (0, 0, 1, 0, 1, 1, 1)

        tiers = evaluate_risk_tiers(targets, probs, tau_low=0.08, tau_high=0.20)
        self.assertEqual(len(tiers), 3)

        total_count = sum(tier.count for tier in tiers)
        self.assertEqual(total_count, len(probs))

        total_fraction = sum(tier.fraction for tier in tiers)
        self.assertAlmostEqual(total_fraction, 1.0, places=4)

        total_lapses = sum(tier.observed_lapses for tier in tiers)
        self.assertEqual(total_lapses, sum(targets))


if __name__ == "__main__":
    unittest.main()
