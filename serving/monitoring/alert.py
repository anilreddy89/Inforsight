"""Drift Alert Action Matrix (Phase 3.04A design spec §3).

Maps (signal × severity × primary_driver_flag) to predeclared automated responses.
All responses are advisory only — ADR 0002 boundary is strictly preserved.

Threshold bands (predeclared):
  PSI/CSI  Green  < 0.10   → no action
  PSI/CSI  Yellow 0.10–0.25 → drift_warning
  PSI/CSI  Red    >= 0.25   → drift_uncertain (+ specialist confirm if primary driver)
  CSI      unseen > 5%      → schema_change_alert (independent of CSI magnitude)
  ECE      Green  <= 0.030  → no action
  ECE      Yellow 0.030–0.060 → calibration_warning
  ECE      Red    > 0.060   → calibration_uncertain
  BSS      < -0.05           → yellow calibration flag regardless of ECE
"""

from __future__ import annotations

from typing import Sequence

from serving.monitoring.models import (
    AlertEntry,
    AlertSummary,
    CalibrationReport,
    FeatureDriftResult,
    BSS_DEGRADED_THRESHOLD,
)

_UNSEEN_SCHEMA_THRESHOLD = 0.05


def _alert_for_feature(result: FeatureDriftResult) -> list[AlertEntry]:
    """Produce zero or more AlertEntries for a single feature drift result."""
    alerts: list[AlertEntry] = []
    signal = "psi" if result.feature_type == "continuous" else "csi"

    if result.status == "moderate_shift":
        alerts.append(AlertEntry(
            feature=result.feature_name,
            signal=signal,
            severity="moderate_shift",
            is_primary_driver=result.is_primary_risk_driver,
            action="drift_warning",
        ))

    elif result.status == "significant_drift":
        action = "drift_uncertain"
        alerts.append(AlertEntry(
            feature=result.feature_name,
            signal=signal,
            severity="significant_drift",
            is_primary_driver=result.is_primary_risk_driver,
            action=action,
        ))

    # Unseen category check (categorical only, independent of CSI magnitude)
    if result.feature_type == "categorical" and result.unseen_proportion > _UNSEEN_SCHEMA_THRESHOLD:
        alerts.append(AlertEntry(
            feature=result.feature_name,
            signal="unseen_category",
            severity="significant_drift",
            is_primary_driver=result.is_primary_risk_driver,
            action="schema_change_alert",
        ))

    return alerts


def _alert_for_calibration(report: CalibrationReport) -> list[AlertEntry]:
    """Produce zero or more AlertEntries for calibration decay signals."""
    alerts: list[AlertEntry] = []

    if report.ece_status == "moderate_decay":
        alerts.append(AlertEntry(
            feature=None,
            signal="ece",
            severity="moderate_decay",
            is_primary_driver=False,
            action="calibration_warning",
        ))
    elif report.ece_status == "significant_decay":
        alerts.append(AlertEntry(
            feature=None,
            signal="ece",
            severity="significant_decay",
            is_primary_driver=False,
            action="calibration_uncertain",
        ))

    if report.brier_status == "degraded":
        alerts.append(AlertEntry(
            feature=None,
            signal="bss",
            severity="degraded",
            is_primary_driver=False,
            action="calibration_warning",
        ))

    return alerts


def _overall_status(alerts: list[AlertEntry]) -> str:
    """Derive overall traffic-light status from the list of active alerts."""
    if not alerts:
        return "green"
    actions = {a.action for a in alerts}
    if "drift_uncertain" in actions or "calibration_uncertain" in actions or "schema_change_alert" in actions:
        return "red"
    return "yellow"


def build_alert_summary(
    drift_results: Sequence[FeatureDriftResult],
    calibration_report: CalibrationReport,
) -> AlertSummary:
    """Aggregate all feature drift and calibration alerts into a single AlertSummary.

    ADR 0002: ``authorized_to_act`` is unconditionally ``False``.
    """
    all_alerts: list[AlertEntry] = []

    for result in drift_results:
        all_alerts.extend(_alert_for_feature(result))

    all_alerts.extend(_alert_for_calibration(calibration_report))

    return AlertSummary(
        overall_status=_overall_status(all_alerts),
        active_alerts=all_alerts,
        authorized_to_act=False,
    )
