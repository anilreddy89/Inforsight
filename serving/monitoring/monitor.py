"""DriftMonitor: convenience facade wiring baseline, PSI/CSI, calibration, telemetry, and alerts.

Provides the single object that ``app.py`` holds in global state and calls when
serving ``GET /v1/diagnostics``.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Sequence

from serving.monitoring.baseline import TrainingBaseline, build_training_baseline
from serving.monitoring.psi import compute_numeric_psi, compute_categorical_csi
from serving.monitoring.calibration import CalibrationTracker
from serving.monitoring.telemetry import TelemetryCollector
from serving.monitoring.alert import build_alert_summary
from serving.monitoring.models import (
    DIAGNOSTICS_SCHEMA_VERSION,
    FeatureDriftResult,
)


class DriftMonitor:
    """Stateful monitoring facade for the inference gateway.

    Parameters
    ----------
    bundle:
        A loaded ``ModelBundle`` instance.  The baseline is extracted at
        construction time and frozen.
    calibration_window:
        Maximum number of resolved observations retained for ECE/BSS computation.
    """

    def __init__(self, bundle: Any, calibration_window: int = 500) -> None:
        self._baseline: TrainingBaseline = build_training_baseline(bundle)
        self._bundle_id: str = bundle.bundle_id
        self._calibration: CalibrationTracker = CalibrationTracker(calibration_window)
        self._telemetry: TelemetryCollector = TelemetryCollector()
        self._service_start: float = time.monotonic()

    # ------------------------------------------------------------------
    # Telemetry recording hooks (called by app.py route handlers)
    # ------------------------------------------------------------------

    def record_single_request(self, latency_ms: float) -> None:
        self._telemetry.record_single(latency_ms)

    def record_batch_request(self, latency_ms: float, count: int) -> None:
        self._telemetry.record_batch(latency_ms, count)

    def record_resolved_outcome(
        self,
        predicted_prob: float,
        observed_outcome: float,
        timestamp: str | None = None,
    ) -> None:
        """Register a resolved observation (outcome known) into the calibration window."""
        self._calibration.record(predicted_prob, observed_outcome, timestamp)
        self._telemetry.set_calibration_window(
            self._calibration.window_size,
            self._calibration.oldest_timestamp,
            self._calibration.newest_timestamp,
        )

    # ------------------------------------------------------------------
    # Drift computation
    # ------------------------------------------------------------------

    def compute_drift(
        self,
        feature_observations: dict[str, Sequence],
    ) -> list[FeatureDriftResult]:
        """Compute PSI/CSI for each monitored feature.

        Parameters
        ----------
        feature_observations:
            Dict mapping feature_name -> list of observed values (raw, pre-preprocessing).
            Missing features are silently skipped.
        """
        results: list[FeatureDriftResult] = []

        for feat_name, baseline_spec in self._baseline.numeric.items():
            if feat_name in feature_observations:
                vals = [float(v) for v in feature_observations[feat_name]]
                results.append(compute_numeric_psi(feat_name, vals, baseline_spec))

        for feat_name, baseline_spec in self._baseline.categorical.items():
            if feat_name in feature_observations:
                vals = [str(v) for v in feature_observations[feat_name]]
                results.append(compute_categorical_csi(feat_name, vals, baseline_spec))

        return results

    # ------------------------------------------------------------------
    # Full diagnostics report
    # ------------------------------------------------------------------

    def diagnostics_report(
        self,
        feature_observations: dict[str, Sequence] | None = None,
    ) -> dict:
        """Build the full GET /v1/diagnostics response payload.

        Parameters
        ----------
        feature_observations:
            Optional dict of feature_name -> observed values for PSI/CSI computation.
            If None, drift results are empty (no current scoring window data available).
        """
        drift_results = self.compute_drift(feature_observations or {})
        cal_report = self._calibration.compute()
        tel_snapshot = self._telemetry.snapshot()
        alert_summary = build_alert_summary(drift_results, cal_report)

        uptime_s = int(time.monotonic() - self._service_start)
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Feature drift section
        features_section: dict[str, dict] = {}
        for result in drift_results:
            features_section[result.feature_name] = result.to_dict()

        return {
            "schema_version": DIAGNOSTICS_SCHEMA_VERSION,
            "generated_at": generated_at,
            "service_uptime_seconds": uptime_s,
            "telemetry": tel_snapshot.to_dict(),
            "feature_drift": {
                "reference_bundle_id": self._bundle_id,
                "reference_observation_count": self._baseline.reference_observation_count,
                "features": features_section,
            },
            "calibration": cal_report.to_dict(),
            "alert_summary": alert_summary.to_dict(),
        }
