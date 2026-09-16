"""DriftMonitor: convenience facade wiring baseline, PSI/CSI, calibration, telemetry, and alerts.

Provides the single object that ``app.py`` holds in global state and calls when
serving ``GET /v1/diagnostics``.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
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
    MIN_DRIFT_OBSERVATIONS,
)


class OutcomeJoinError(ValueError):
    """A resolved outcome cannot be safely joined to a retained score."""


@dataclass(frozen=True)
class _ScoreRecord:
    policy_id: str
    observation_id: str
    model_version: str
    predicted_probability: float
    features: dict[str, Any]
    scored_at: str


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

    def __init__(
        self,
        bundle: Any,
        calibration_window: int = 500,
        score_window_size: int = 500,
        minimum_drift_observations: int = MIN_DRIFT_OBSERVATIONS,
    ) -> None:
        if minimum_drift_observations < 1 or minimum_drift_observations > score_window_size:
            raise ValueError("minimum_drift_observations must be between 1 and score_window_size")
        self._baseline: TrainingBaseline = build_training_baseline(bundle)
        self._bundle_id: str = bundle.bundle_id
        self._model_version: str = bundle.bundle_version
        self._calibration: CalibrationTracker = CalibrationTracker(calibration_window)
        self._telemetry: TelemetryCollector = TelemetryCollector()
        self._score_window_size = score_window_size
        self._minimum_drift_observations = minimum_drift_observations
        self._scores: OrderedDict[tuple[str, str, str], _ScoreRecord] = OrderedDict()
        self._outcomes: dict[tuple[str, str, str], tuple[int, str | None]] = {}
        self._service_start: float = time.monotonic()

    # ------------------------------------------------------------------
    # Telemetry recording hooks (called by app.py route handlers)
    # ------------------------------------------------------------------

    def record_single_request(self, latency_ms: float) -> None:
        self._telemetry.record_single(latency_ms)

    def record_batch_request(self, latency_ms: float, count: int) -> None:
        self._telemetry.record_batch(latency_ms, count)

    def record_score(
        self,
        *,
        policy_id: str,
        observation_id: str,
        features: dict[str, Any],
        predicted_probability: float,
    ) -> None:
        """Retain one successful score for drift and later exact outcome joining."""
        key = (policy_id, observation_id, self._model_version)
        record = _ScoreRecord(
            policy_id=policy_id,
            observation_id=observation_id,
            model_version=self._model_version,
            predicted_probability=predicted_probability,
            features=dict(features),
            scored_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        self._scores[key] = record
        self._scores.move_to_end(key)
        while len(self._scores) > self._score_window_size:
            evicted_key, _ = self._scores.popitem(last=False)
            self._outcomes.pop(evicted_key, None)

    def ingest_resolved_outcome(
        self,
        *,
        policy_id: str,
        observation_id: str,
        model_version: str,
        observed_outcome: int,
        resolved_at: str | None = None,
    ) -> str:
        """Join a binary outcome once to a retained score, returning accepted/replayed."""
        key = (policy_id, observation_id, model_version)
        if model_version != self._model_version:
            raise OutcomeJoinError("MODEL_VERSION_MISMATCH")
        score = self._scores.get(key)
        if score is None:
            raise OutcomeJoinError("SCORE_NOT_RETAINED")
        existing = self._outcomes.get(key)
        payload = (observed_outcome, resolved_at)
        if existing is not None:
            if existing == payload:
                return "replayed"
            raise OutcomeJoinError("OUTCOME_CONFLICT")
        self._outcomes[key] = payload
        self._calibration.record(score.predicted_probability, float(observed_outcome), resolved_at)
        self._telemetry.set_calibration_window(
            self._calibration.window_size,
            self._calibration.oldest_timestamp,
            self._calibration.newest_timestamp,
        )
        return "accepted"

    # ------------------------------------------------------------------
    # Drift computation
    # ------------------------------------------------------------------

    def compute_drift(
        self,
        feature_observations: dict[str, Sequence] | None = None,
    ) -> list[FeatureDriftResult]:
        """Compute PSI/CSI for each monitored feature.

        Parameters
        ----------
        feature_observations:
            Dict mapping feature_name -> list of observed values (raw, pre-preprocessing).
            Missing features are silently skipped.
        """
        if feature_observations is None:
            if len(self._scores) < self._minimum_drift_observations:
                return []
            feature_observations = {}
            for record in self._scores.values():
                for name, value in record.features.items():
                    feature_observations.setdefault(name, []).append(value)

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
        drift_results = self.compute_drift(feature_observations)
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
                "model_version": self._model_version,
                "reference_observation_count": self._baseline.reference_observation_count,
                "retained_score_count": len(self._scores),
                "minimum_observations": self._minimum_drift_observations,
                "status": "ready" if len(self._scores) >= self._minimum_drift_observations else "insufficient_data",
                "window_start": next(iter(self._scores.values())).scored_at if self._scores else None,
                "window_end": next(reversed(self._scores.values())).scored_at if self._scores else None,
                "features": features_section,
            },
            "calibration": cal_report.to_dict(),
            "alert_summary": alert_summary.to_dict(),
        }
