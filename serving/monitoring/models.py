"""Dataclasses for monitoring: drift, calibration, telemetry, and alert summaries."""

from __future__ import annotations

from dataclasses import dataclass, field


ADR_0002_AUTHORITY_BOUNDARY_NOTICE = "ADR_0002_REQUIRES_HUMAN_REVIEW"

# PSI / CSI threshold bands (predeclared in Phase 3.04A design spec)
PSI_GREEN_MAX = 0.10
PSI_YELLOW_MAX = 0.25

# ECE threshold bands (predeclared in Phase 3.04A design spec)
ECE_GREEN_MAX = 0.030
ECE_YELLOW_MAX = 0.060

# BSS degradation threshold
BSS_DEGRADED_THRESHOLD = -0.05

# Phase 2.08 reference baselines (frozen)
REFERENCE_ECE = 0.0115
REFERENCE_BRIER_SCORE = 0.1211

# Features with highest mean |SHAP| from Phase 2.09 (frozen primary risk drivers)
PRIMARY_RISK_DRIVERS: frozenset[str] = frozenset({
    "rolling_on_time_rate",
    "recent_failed_payment_count",
    "tenure_days",
})

DIAGNOSTICS_SCHEMA_VERSION = "1.0.0"


def _psi_status(value: float) -> str:
    if value < PSI_GREEN_MAX:
        return "stable"
    if value < PSI_YELLOW_MAX:
        return "moderate_shift"
    return "significant_drift"


def _ece_status(value: float) -> str:
    if value <= ECE_GREEN_MAX:
        return "well_calibrated"
    if value <= ECE_YELLOW_MAX:
        return "moderate_decay"
    return "significant_decay"


@dataclass(frozen=True)
class FeatureDriftResult:
    """PSI or CSI result for a single monitored feature."""

    feature_name: str
    feature_type: str          # "continuous" | "categorical"
    is_primary_risk_driver: bool
    psi_or_csi: float
    status: str                # "stable" | "moderate_shift" | "significant_drift"
    unseen_proportion: float   # categorical only; 0.0 for continuous
    bin_count: int

    def to_dict(self) -> dict:
        return {
            "feature_name": self.feature_name,
            "feature_type": self.feature_type,
            "is_primary_risk_driver": self.is_primary_risk_driver,
            "psi" if self.feature_type == "continuous" else "csi": round(self.psi_or_csi, 6),
            "status": self.status,
            "unseen_proportion": round(self.unseen_proportion, 6),
            "bin_count": self.bin_count,
        }


@dataclass(frozen=True)
class CalibrationReport:
    """Rolling ECE, Brier Score, and BSS over a sliding observation window."""

    window_size: int
    ece: float
    brier_score: float
    brier_skill_score: float
    ece_status: str             # "well_calibrated" | "moderate_decay" | "significant_decay"
    brier_status: str           # "stable" | "degraded"
    reference_ece: float = REFERENCE_ECE
    reference_brier_score: float = REFERENCE_BRIER_SCORE

    def to_dict(self) -> dict:
        return {
            "rolling_window_size": self.window_size,
            "ece": round(self.ece, 6),
            "brier_score": round(self.brier_score, 6),
            "brier_skill_score": round(self.brier_skill_score, 6),
            "ece_status": self.ece_status,
            "brier_status": self.brier_status,
            "reference_ece": self.reference_ece,
            "reference_brier_score": self.reference_brier_score,
        }


@dataclass(frozen=True)
class AlertEntry:
    """Single active alert produced by the drift alert matrix."""

    feature: str | None
    signal: str          # "psi" | "csi" | "ece" | "bss" | "unseen_category"
    severity: str        # "moderate_shift" | "significant_drift" | "degraded"
    is_primary_driver: bool
    action: str          # "drift_warning" | "drift_uncertain" | "calibration_warning" | "calibration_uncertain" | "schema_change_alert"

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "signal": self.signal,
            "severity": self.severity,
            "is_primary_driver": self.is_primary_driver,
            "action": self.action,
        }


@dataclass
class AlertSummary:
    """Aggregated alert status across all drift and calibration signals."""

    overall_status: str                    # "green" | "yellow" | "red"
    active_alerts: list[AlertEntry] = field(default_factory=list)
    authorized_to_act: bool = False
    action_authority_boundary: str = ADR_0002_AUTHORITY_BOUNDARY_NOTICE

    def to_dict(self) -> dict:
        return {
            "overall_status": self.overall_status,
            "active_alerts": [a.to_dict() for a in self.active_alerts],
            "authorized_to_act": self.authorized_to_act,
            "action_authority_boundary": self.action_authority_boundary,
        }


@dataclass(frozen=True)
class TelemetrySnapshot:
    """In-memory inference telemetry snapshot."""

    requests_total: int
    requests_single: int
    requests_batch: int
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    window_size: int
    scoring_window_start: str | None
    scoring_window_end: str | None

    def to_dict(self) -> dict:
        return {
            "requests_total": self.requests_total,
            "requests_single": self.requests_single,
            "requests_batch": self.requests_batch,
            "latency_p50_ms": round(self.latency_p50_ms, 3),
            "latency_p95_ms": round(self.latency_p95_ms, 3),
            "latency_p99_ms": round(self.latency_p99_ms, 3),
            "window_size": self.window_size,
            "scoring_window_start": self.scoring_window_start,
            "scoring_window_end": self.scoring_window_end,
        }
