"""Inforsight model monitoring and drift detection module.

Public API
----------
TrainingBaseline
    Frozen reference distributions extracted from the model bundle at startup.

build_training_baseline(bundle) -> TrainingBaseline
    Construct the frozen baseline from a loaded ModelBundle.

compute_numeric_psi(feature_name, current_values, baseline) -> FeatureDriftResult
compute_categorical_csi(feature_name, current_values, baseline) -> FeatureDriftResult
    Compute PSI / CSI for a single feature against the baseline.

CalibrationTracker
    Rolling window ECE / Brier Score / BSS tracker.

TelemetryCollector
    In-memory latency ring buffer and request counter.

build_alert_summary(drift_results, calibration_report) -> AlertSummary
    Aggregate drift and calibration signals into the alert action matrix output.

DriftMonitor
    Convenience facade that wires baseline, PSI/CSI, calibration, and alerts together.
"""

from serving.monitoring.baseline import TrainingBaseline, build_training_baseline
from serving.monitoring.psi import compute_numeric_psi, compute_categorical_csi
from serving.monitoring.calibration import CalibrationTracker
from serving.monitoring.telemetry import TelemetryCollector
from serving.monitoring.alert import build_alert_summary
from serving.monitoring.models import (
    DIAGNOSTICS_SCHEMA_VERSION,
    FeatureDriftResult,
    CalibrationReport,
    AlertSummary,
    AlertEntry,
    TelemetrySnapshot,
)
from serving.monitoring.monitor import DriftMonitor

__all__ = [
    "DIAGNOSTICS_SCHEMA_VERSION",
    "AlertEntry",
    "AlertSummary",
    "CalibrationReport",
    "CalibrationTracker",
    "DriftMonitor",
    "FeatureDriftResult",
    "TelemetryCollector",
    "TelemetrySnapshot",
    "TrainingBaseline",
    "build_alert_summary",
    "build_training_baseline",
    "compute_categorical_csi",
    "compute_numeric_psi",
]
