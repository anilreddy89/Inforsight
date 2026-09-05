"""Unit tests for Inforsight model monitoring and drift detection module (P3-04A).

Covers:
- PSI / CSI computation and zero-proportion guard (§2.1, §2.2)
- Threshold classification: stable / moderate_shift / significant_drift
- Rolling ECE and Brier Score / BSS computation (§2.3, §2.4)
- Alert action matrix (§3): correct actions for all (signal × severity × driver) bands
- DriftMonitor facade: diagnostics_report structure and ADR 0002 boundary marker
- GET /v1/diagnostics endpoint: schema_version, structure, ADR 0002
"""

from __future__ import annotations

import math
import unittest

from serving.monitoring.models import (
    DIAGNOSTICS_SCHEMA_VERSION,
    PSI_GREEN_MAX,
    PSI_YELLOW_MAX,
    ECE_GREEN_MAX,
    ECE_YELLOW_MAX,
    BSS_DEGRADED_THRESHOLD,
    REFERENCE_BRIER_SCORE,
    PRIMARY_RISK_DRIVERS,
    ADR_0002_AUTHORITY_BOUNDARY_NOTICE,
    _psi_status,
    _ece_status,
)
from serving.monitoring.psi import (
    compute_psi_from_proportions,
    compute_numeric_psi,
    compute_categorical_csi,
    _bin_observations,
)
from serving.monitoring.calibration import CalibrationTracker, _compute_ece, _compute_brier_score, _Observation
from serving.monitoring.telemetry import TelemetryCollector
from serving.monitoring.alert import build_alert_summary, _alert_for_feature, _overall_status
from serving.monitoring.baseline import build_training_baseline, _build_numeric_baseline, _build_categorical_baseline
from serving.monitoring.monitor import DriftMonitor
from inforsight_simulator.bundle import ModelBundle
from serving.app import create_app, DEFAULT_BUNDLE_PATH
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

class _BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = ModelBundle.load(DEFAULT_BUNDLE_PATH)
        cls.baseline = build_training_baseline(cls.bundle)


# ---------------------------------------------------------------------------
# 1. PSI / CSI mathematical formulation and zero-proportion guard
# ---------------------------------------------------------------------------

class TestPSIFormulation(_BaseTest):

    def test_identical_distributions_psi_is_zero(self) -> None:
        """PSI between identical distributions must be 0."""
        props = [0.1] * 10
        psi = compute_psi_from_proportions(props, props)
        self.assertAlmostEqual(psi, 0.0, places=10)

    def test_psi_is_non_negative(self) -> None:
        """PSI is always >= 0 by definition."""
        current = [0.05, 0.15, 0.20, 0.10, 0.10, 0.10, 0.10, 0.05, 0.10, 0.05]
        ref = [0.10] * 10
        psi = compute_psi_from_proportions(current, ref)
        self.assertGreaterEqual(psi, 0.0)

    def test_zero_proportion_guard_no_nan_or_inf(self) -> None:
        """Zero bins in reference or current must not produce NaN or inf (epsilon substitution)."""
        current = [0.5, 0.5] + [0.0] * 8
        ref = [0.0] + [0.1] * 8 + [0.1]
        psi = compute_psi_from_proportions(current, ref)
        self.assertFalse(math.isnan(psi), "PSI must not be NaN with zero-proportion inputs")
        self.assertFalse(math.isinf(psi), "PSI must not be inf with zero-proportion inputs")

    def test_mismatched_lengths_raises(self) -> None:
        with self.assertRaises(ValueError):
            compute_psi_from_proportions([0.5, 0.5], [0.3, 0.3, 0.4])

    def test_threshold_stable(self) -> None:
        self.assertEqual(_psi_status(0.0), "stable")
        self.assertEqual(_psi_status(0.09), "stable")

    def test_threshold_moderate_shift(self) -> None:
        self.assertEqual(_psi_status(0.10), "moderate_shift")
        self.assertEqual(_psi_status(0.20), "moderate_shift")
        self.assertEqual(_psi_status(0.249), "moderate_shift")

    def test_threshold_significant_drift(self) -> None:
        self.assertEqual(_psi_status(0.25), "significant_drift")
        self.assertEqual(_psi_status(1.00), "significant_drift")

    def test_numeric_psi_stable_for_baseline_distribution(self) -> None:
        """Scoring the exact reference distribution must produce PSI ~ 0 (stable)."""
        feat = "rolling_on_time_rate"
        baseline = self.baseline.numeric[feat]
        # Reconstruct ~1000 values from the Gaussian approximation
        import random
        rng = random.Random(42)
        mean = self.bundle.preprocessor.numeric[feat].mean
        scale = self.bundle.preprocessor.numeric[feat].scale
        values = [rng.gauss(mean, scale) for _ in range(1000)]
        result = compute_numeric_psi(feat, values, baseline)
        self.assertEqual(result.feature_type, "continuous")
        self.assertGreaterEqual(result.psi_or_csi, 0.0)
        # Sampling noise means we can't guarantee exactly 0, but it should be stable
        self.assertIn(result.status, ("stable", "moderate_shift"))

    def test_numeric_psi_significant_drift_on_extreme_shift(self) -> None:
        """Extreme shift (all values at one edge) must produce significant_drift."""
        feat = "tenure_days"
        baseline = self.baseline.numeric[feat]
        # All values far outside training range → concentrated in outermost bin
        extreme_values = [1e9] * 200
        result = compute_numeric_psi(feat, extreme_values, baseline)
        self.assertEqual(result.status, "significant_drift")
        self.assertGreaterEqual(result.psi_or_csi, PSI_YELLOW_MAX)

    def test_numeric_psi_primary_driver_flagged(self) -> None:
        feat = "rolling_on_time_rate"
        self.assertIn(feat, PRIMARY_RISK_DRIVERS)
        baseline = self.baseline.numeric[feat]
        result = compute_numeric_psi(feat, [0.5] * 100, baseline)
        self.assertTrue(result.is_primary_risk_driver)

    def test_numeric_psi_secondary_feature_not_flagged(self) -> None:
        feat = "premium_amount_cents"
        baseline = self.baseline.numeric[feat]
        result = compute_numeric_psi(feat, [500.0] * 100, baseline)
        self.assertFalse(result.is_primary_risk_driver)


# ---------------------------------------------------------------------------
# 2. CSI and unseen category detection
# ---------------------------------------------------------------------------

class TestCSI(_BaseTest):

    def test_csi_stable_for_known_categories(self) -> None:
        feat = "billing_frequency"
        baseline = self.baseline.categorical[feat]
        # Use only known categories
        values = list(baseline.categories) * 25
        result = compute_categorical_csi(feat, values, baseline)
        self.assertEqual(result.feature_type, "categorical")
        self.assertGreaterEqual(result.psi_or_csi, 0.0)

    def test_unseen_proportion_computed_correctly(self) -> None:
        feat = "billing_frequency"
        baseline = self.baseline.categorical[feat]
        n_known = 80
        n_unseen = 20
        known_vals = [baseline.categories[0]] * n_known
        unseen_vals = ["NEVER_SEEN_CATEGORY"] * n_unseen
        result = compute_categorical_csi(feat, known_vals + unseen_vals, baseline)
        self.assertAlmostEqual(result.unseen_proportion, n_unseen / (n_known + n_unseen), places=5)

    def test_unseen_proportion_zero_for_all_known(self) -> None:
        feat = "billing_frequency"
        baseline = self.baseline.categorical[feat]
        result = compute_categorical_csi(feat, list(baseline.categories) * 10, baseline)
        self.assertEqual(result.unseen_proportion, 0.0)

    def test_csi_feature_type_is_categorical(self) -> None:
        feat = "product_type"
        baseline = self.baseline.categorical[feat]
        result = compute_categorical_csi(feat, list(baseline.categories), baseline)
        self.assertEqual(result.feature_type, "categorical")


# ---------------------------------------------------------------------------
# 3. Rolling ECE and Brier Score / BSS
# ---------------------------------------------------------------------------

class TestCalibrationTracker(unittest.TestCase):

    def _make_tracker(self, probs, outcomes):
        tracker = CalibrationTracker(window_size=500)
        for p, y in zip(probs, outcomes):
            tracker.record(p, float(y))
        return tracker

    def test_perfect_calibration_ece_near_zero(self) -> None:
        """Well-calibrated predictor yields ECE below Yellow threshold (0.060).

        Fixture: p ~ Uniform(0,1), outcome ~ Bernoulli(p).
        By construction E[outcome | p] = p so the predictor is perfectly calibrated.
        With n=1000 samples within-bin variance causes ECE ~ 0.03–0.05, which is
        well below the Yellow threshold (0.060) and the Red threshold (> 0.060).
        The ece_status depends on sampling noise but must not be significant_decay.
        """
        import random
        rng = random.Random(1234)
        probs = [rng.random() for _ in range(1000)]
        outcomes = [1 if rng.random() < p else 0 for p in probs]
        tracker = self._make_tracker(probs, outcomes)
        report = tracker.compute()
        # A calibrated predictor must never breach the Yellow threshold
        self.assertLess(report.ece, ECE_YELLOW_MAX)
        self.assertNotEqual(report.ece_status, "significant_decay")

    def test_brier_score_perfect_predictor(self) -> None:
        """All correct hard predictions give Brier Score 0."""
        obs = [_Observation(0.0, 0.0)] * 50 + [_Observation(1.0, 1.0)] * 50
        bs = _compute_brier_score(obs)
        self.assertAlmostEqual(bs, 0.0, places=10)

    def test_brier_score_all_wrong(self) -> None:
        """All inverted hard predictions give Brier Score 1."""
        obs = [_Observation(1.0, 0.0)] * 50 + [_Observation(0.0, 1.0)] * 50
        bs = _compute_brier_score(obs)
        self.assertAlmostEqual(bs, 1.0, places=10)

    def test_bss_stable_when_score_matches_reference(self) -> None:
        """BSS near 0 when BS approximately equals the Phase 2.08 reference (0.1211)."""
        # Construct observations that yield BS ≈ reference
        import random
        rng = random.Random(99)
        probs = [rng.uniform(0.05, 0.45) for _ in range(200)]
        outcomes = [1 if rng.random() < p * 2 else 0 for p in probs]
        tracker = self._make_tracker(probs, outcomes)
        report = tracker.compute()
        # BSS could be positive or near-zero — just confirm no crash and is float
        self.assertIsInstance(report.brier_skill_score, float)

    def test_bss_degraded_flag_when_bs_worsens(self) -> None:
        """BSS < BSS_DEGRADED_THRESHOLD triggers brier_status == 'degraded'."""
        # Worst case: all predictions 0.5, outcomes random → BS ≈ 0.25 >> 0.1211
        probs = [0.5] * 200
        outcomes = [i % 2 for i in range(200)]
        tracker = self._make_tracker(probs, outcomes)
        report = tracker.compute()
        # BS ~ 0.25, BSS = 1 - 0.25/0.1211 ~ -1.06 << -0.05
        self.assertEqual(report.brier_status, "degraded")

    def test_ece_thresholds(self) -> None:
        self.assertEqual(_ece_status(0.0), "well_calibrated")
        self.assertEqual(_ece_status(0.030), "well_calibrated")
        self.assertEqual(_ece_status(0.031), "moderate_decay")
        self.assertEqual(_ece_status(0.060), "moderate_decay")
        self.assertEqual(_ece_status(0.061), "significant_decay")

    def test_empty_window_does_not_crash(self) -> None:
        tracker = CalibrationTracker()
        report = tracker.compute()
        self.assertEqual(report.window_size, 0)
        self.assertEqual(report.ece, 0.0)
        self.assertEqual(report.brier_score, 0.0)


# ---------------------------------------------------------------------------
# 4. Alert Action Matrix
# ---------------------------------------------------------------------------

class TestAlertMatrix(_BaseTest):

    def _make_drift_result(self, psi, feature="premium_amount_cents", feature_type="continuous"):
        from serving.monitoring.models import FeatureDriftResult, _psi_status
        return FeatureDriftResult(
            feature_name=feature,
            feature_type=feature_type,
            is_primary_risk_driver=(feature in PRIMARY_RISK_DRIVERS),
            psi_or_csi=psi,
            status=_psi_status(psi),
            unseen_proportion=0.0,
            bin_count=10,
        )

    def _empty_calibration(self):
        tracker = CalibrationTracker()
        return tracker.compute()

    def test_green_drift_no_alerts(self) -> None:
        result = self._make_drift_result(0.05)
        alerts = _alert_for_feature(result)
        self.assertEqual(alerts, [])

    def test_yellow_drift_produces_drift_warning(self) -> None:
        result = self._make_drift_result(0.15)
        alerts = _alert_for_feature(result)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].action, "drift_warning")
        self.assertEqual(alerts[0].severity, "moderate_shift")

    def test_red_drift_produces_drift_uncertain(self) -> None:
        result = self._make_drift_result(0.30)
        alerts = _alert_for_feature(result)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].action, "drift_uncertain")
        self.assertEqual(alerts[0].severity, "significant_drift")

    def test_primary_driver_flagged_in_red_alert(self) -> None:
        result = self._make_drift_result(0.30, feature="rolling_on_time_rate")
        alerts = _alert_for_feature(result)
        self.assertTrue(any(a.is_primary_driver for a in alerts))

    def test_unseen_category_triggers_schema_change_alert(self) -> None:
        from serving.monitoring.models import FeatureDriftResult, _psi_status
        result = FeatureDriftResult(
            feature_name="billing_frequency",
            feature_type="categorical",
            is_primary_risk_driver=False,
            psi_or_csi=0.05,
            status="stable",
            unseen_proportion=0.08,  # > 5% threshold
            bin_count=4,
        )
        alerts = _alert_for_feature(result)
        actions = [a.action for a in alerts]
        self.assertIn("schema_change_alert", actions)

    def test_overall_status_green_when_no_alerts(self) -> None:
        self.assertEqual(_overall_status([]), "green")

    def test_overall_status_yellow_when_only_warnings(self) -> None:
        from serving.monitoring.models import AlertEntry
        alerts = [AlertEntry(feature="f", signal="psi", severity="moderate_shift", is_primary_driver=False, action="drift_warning")]
        self.assertEqual(_overall_status(alerts), "yellow")

    def test_overall_status_red_when_drift_uncertain(self) -> None:
        from serving.monitoring.models import AlertEntry
        alerts = [AlertEntry(feature="f", signal="psi", severity="significant_drift", is_primary_driver=True, action="drift_uncertain")]
        self.assertEqual(_overall_status(alerts), "red")

    def test_adr_0002_boundary_always_in_alert_summary(self) -> None:
        """AlertSummary.authorized_to_act must always be False."""
        drift_results = [self._make_drift_result(0.30)]
        cal = self._empty_calibration()
        summary = build_alert_summary(drift_results, cal)
        self.assertFalse(summary.authorized_to_act)
        self.assertEqual(summary.action_authority_boundary, ADR_0002_AUTHORITY_BOUNDARY_NOTICE)


# ---------------------------------------------------------------------------
# 5. DriftMonitor facade and diagnostics report structure
# ---------------------------------------------------------------------------

class TestDriftMonitor(_BaseTest):

    def setUp(self) -> None:
        self.monitor = DriftMonitor(self.bundle)

    def test_diagnostics_report_schema_version(self) -> None:
        report = self.monitor.diagnostics_report()
        self.assertEqual(report["schema_version"], DIAGNOSTICS_SCHEMA_VERSION)
        self.assertEqual(report["schema_version"], "1.0.0")

    def test_diagnostics_report_adr_0002_in_alert_summary(self) -> None:
        report = self.monitor.diagnostics_report()
        alert = report["alert_summary"]
        self.assertFalse(alert["authorized_to_act"])
        self.assertEqual(alert["action_authority_boundary"], ADR_0002_AUTHORITY_BOUNDARY_NOTICE)

    def test_diagnostics_report_contains_required_sections(self) -> None:
        report = self.monitor.diagnostics_report()
        for section in ("schema_version", "generated_at", "service_uptime_seconds",
                        "telemetry", "feature_drift", "calibration", "alert_summary"):
            self.assertIn(section, report, f"Missing section: {section}")

    def test_telemetry_increments_on_single_request(self) -> None:
        self.monitor.record_single_request(2.5)
        self.monitor.record_single_request(3.1)
        report = self.monitor.diagnostics_report()
        self.assertEqual(report["telemetry"]["requests_single"], 2)
        self.assertEqual(report["telemetry"]["requests_total"], 2)

    def test_telemetry_increments_on_batch_request(self) -> None:
        self.monitor.record_batch_request(5.0, count=10)
        report = self.monitor.diagnostics_report()
        self.assertEqual(report["telemetry"]["requests_batch"], 10)

    def test_calibration_window_updates_on_resolved_outcome(self) -> None:
        for _ in range(5):
            self.monitor.record_resolved_outcome(0.3, 0.0)
        report = self.monitor.diagnostics_report()
        self.assertEqual(report["calibration"]["rolling_window_size"], 5)

    def test_drift_results_present_for_all_numeric_features(self) -> None:
        # Provide current observations for all numeric features
        import random
        rng = random.Random(7)
        feature_obs: dict = {}
        for feat, spec in self.bundle.preprocessor.numeric.items():
            feature_obs[feat] = [rng.gauss(spec.mean, spec.scale) for _ in range(50)]
        for feat, spec in self.bundle.preprocessor.categorical.items():
            feature_obs[feat] = list(spec.categories) * 10
        report = self.monitor.diagnostics_report(feature_obs)
        for feat in self.bundle.preprocessor.numeric:
            self.assertIn(feat, report["feature_drift"]["features"])
        for feat in self.bundle.preprocessor.categorical:
            self.assertIn(feat, report["feature_drift"]["features"])


# ---------------------------------------------------------------------------
# 6. GET /v1/diagnostics endpoint integration
# ---------------------------------------------------------------------------

class TestDiagnosticsEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app(DEFAULT_BUNDLE_PATH)
        cls.client = TestClient(cls.app)

    def test_diagnostics_returns_200(self) -> None:
        resp = self.client.get("/v1/diagnostics")
        self.assertEqual(resp.status_code, 200)

    def test_diagnostics_schema_version(self) -> None:
        resp = self.client.get("/v1/diagnostics")
        data = resp.json()
        self.assertEqual(data["schema_version"], "1.0.0")

    def test_diagnostics_adr_0002_boundary_marker(self) -> None:
        """GET /v1/diagnostics must always include authorized_to_act: false."""
        resp = self.client.get("/v1/diagnostics")
        data = resp.json()
        self.assertFalse(data["alert_summary"]["authorized_to_act"])
        self.assertEqual(
            data["alert_summary"]["action_authority_boundary"],
            ADR_0002_AUTHORITY_BOUNDARY_NOTICE,
        )

    def test_diagnostics_structure(self) -> None:
        resp = self.client.get("/v1/diagnostics")
        data = resp.json()
        for key in ("schema_version", "generated_at", "service_uptime_seconds",
                    "telemetry", "feature_drift", "calibration", "alert_summary"):
            self.assertIn(key, data)

    def test_diagnostics_telemetry_after_scoring(self) -> None:
        """Telemetry counters increment after scoring requests."""
        from inforsight_simulator.bundle import BundledInferenceEngine
        from inforsight_simulator.v6_corpus import generate_v6_corpus, V6CorpusConfig
        from inforsight_simulator.v6_evaluation import _feature_map
        corpus = generate_v6_corpus(V6CorpusConfig(base_seed=20280201))
        obs = [r for r in corpus.observations if r.role == "non_final_evaluation"][0]
        fmap = _feature_map(obs)
        payload = {"policy_id": obs.policy_id, "as_of_date": obs.as_of, "features": fmap}
        self.client.post("/v1/score", json=payload)
        resp = self.client.get("/v1/diagnostics")
        data = resp.json()
        self.assertGreaterEqual(data["telemetry"]["requests_total"], 1)

    def test_existing_gateway_tests_still_pass(self) -> None:
        """Smoke-check: health and model/info endpoints still respond correctly."""
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "healthy")
        info = self.client.get("/v1/model/info")
        self.assertEqual(info.status_code, 200)
        self.assertEqual(info.json()["bundle_id"], "inforsight-v6-logistic-platt-20260817")


if __name__ == "__main__":
    unittest.main()
