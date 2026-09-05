# Phase 3.04A — Model Monitoring and Drift Detection Architecture

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 3 — Policy Conservation Decision Engine & Intervention Orchestration |
| Sequence | 04A |
| Change tracker ID | `P3-04A` |
| GitHub issue | [#114](https://github.com/anilreddy89/Inforsight/issues/114) |
| Issue title | `[Design] P3-04A: Model monitoring and drift detection architecture` |
| Branch | `feat/114-p3-04a-model-monitoring-drift-detection` |
| Pull request | [#115](https://github.com/anilreddy89/Inforsight/pull/115) |
| Status | Complete (Merged as `920f943`) |
| Milestone | [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4) |
| Priority | Milestone blocking / Foundational |
| Classification | Monitoring / Telemetry / Model Risk / Architecture |
| Strict predecessor | Phase 3.04 (`87a66f9`, issue #112, PR #113) |
| Governing predecessor decisions | ADR 0001 (Clean Room), ADR 0002 (Separate Risk Perception from Action Authority), ADR 0003 (Local Deterministic Execution) |
| Target release tag | `v0.3.0-decision-engine` |
| Enables | P3-05 (Bounded Case Intelligence Assistant), P3-07 (Interactive Conservation Dashboard) |
| Blocks | None (P3-05, P3-07 unblocked) |
| Last reviewed | 2026-09-05 |

---

## 1. Executive Summary and Problem Statement

### 1.1 Context & Authority Boundary

Phase 3.04 delivered the high-throughput FastAPI inference gateway wrapping `BundledInferenceEngine`, with bit-for-bit reproducible scoring, ADR 0002 authority boundary markers, and schema-validated endpoints (`GET /health`, `GET /v1/model/info`, `POST /v1/score`, `POST /v1/score/batch`).

Once deployed in a rolling operational context, a model trained on the frozen Generation v6 corpus (Phase 2R.14D, cutoff `20280201`) will encounter evolving real-world policy populations. **Distribution shift** — gradual or sudden divergence between training-time feature distributions and live inference distributions — is the primary failure mode of production ML systems.

Phase 3.04A does **not** implement live instrumentation or production infrastructure. It delivers:

1. A **formal design specification** with mathematical formulations for all monitoring metrics.
2. A **predeclared drift threshold matrix** and alert action taxonomy.
3. A **gateway diagnostics contract** — the OpenAPI schema extension for `GET /v1/diagnostics`.
4. A **reference monitoring module** (`serving/monitoring/`) implementing metric computation against a frozen training baseline in a deterministic, testable manner.

**ADR 0002 boundary** is strictly preserved: the monitoring layer is advisory only. Drift flags never autonomously alter scoring outputs, suppress responses, or authorize interventions. All drift-triggered actions require specialist human review.

### 1.2 Why This Is Milestone-Blocking

P3-05 (Bounded Case Intelligence Assistant) synthesizes Case Briefs that include scoring confidence context. Without a predeclared monitoring contract, the assistant has no governed mechanism to surface calibration uncertainty to specialists. P3-07 (Interactive Conservation Dashboard) must render live drift signals — without P3-04A's schema, the dashboard has no structured telemetry source.

---

## 2. Mathematical Formulations

### 2.1 Population Stability Index (PSI) — Input Feature Drift

PSI measures the distributional shift of a continuous or ordinal feature between a reference (training) population and a current (scoring) population.

**Computation:**

Partition both distributions into B = 10 equal-width or equal-frequency bins derived from the training baseline. For each bin b:

PSI = SUM_b [ (p_b_current - p_b_reference) * ln(p_b_current / p_b_reference) ]

where p_b_reference and p_b_current are the proportions of observations falling in bin b from the reference and current populations, respectively.

**Zero-proportion guard:** If p_b_reference = 0 or p_b_current = 0, substitute epsilon = 0.0001 to avoid log(0) undefined values.

**Stability thresholds (predeclared):**

| Status | PSI Range | Operational Action |
| :--- | :---: | :--- |
| Green STABLE | PSI < 0.10 | No action required. Normal inference continues. |
| Yellow MODERATE SHIFT | 0.10 <= PSI < 0.25 | Escalate to model-risk review queue. Document in telemetry log. |
| Red SIGNIFICANT DRIFT | PSI >= 0.25 | Flag scoring as `drift_uncertain`. Require specialist confirmation for Tier 1 / Tier 2 actions. Trigger automated model-risk review. |

### 2.2 Characteristic Stability Index (CSI) — Categorical Feature Drift

For categorical features (e.g. `policy_status`, `billing_frequency`, `product_type`, `risk_class`), PSI is computed per category level rather than per numeric bin.

Let C be the set of all categories observed in training. For each category c in C:

CSI = SUM_c [ (p_c_current - p_c_reference) * ln(p_c_current / p_c_reference) ]

**Unseen category handling:** Categories absent from the training reference are collected into an `_UNSEEN_` overflow bucket. p_UNSEEN_reference = epsilon. A non-trivial `_UNSEEN_` proportion (> 5%) triggers a **schema-change alert** independent of CSI magnitude.

Thresholds for CSI follow the same Green / Yellow / Red bands as PSI.

### 2.3 Rolling Expected Calibration Error (ECE) — Calibration Decay Tracking

ECE measures the mean absolute deviation between average predicted probabilities and observed outcome frequencies, over M = 10 equal-width probability bins.

ECE = SUM_m [ (|B_m| / n) * |y_bar_m - p_hat_bar_m| ]

where:
- M = 10 equally-spaced bins on [0, 1]
- |B_m|: number of observations in bin m
- n: total observations in the rolling window
- p_hat_bar_m: mean predicted calibrated probability in bin m
- y_bar_m: mean observed outcome (lapse indicator) in bin m

**Rolling window:** Computed over the most recent W = 500 scored observations for which outcomes are observed.

**Calibration thresholds (predeclared):**

| Status | ECE Range | Operational Action |
| :--- | :---: | :--- |
| Green WELL-CALIBRATED | ECE <= 0.030 | No action. Baseline ECE from Phase 2.08: 0.0115. |
| Yellow MODERATE DECAY | 0.030 < ECE <= 0.060 | Log calibration alert. Flag for model-risk review at next scheduled cadence. |
| Red SIGNIFICANT DECAY | ECE > 0.060 | Flag `calibration_uncertain` on all outputs. Escalate immediately to model-risk committee. |

### 2.4 Rolling Brier Score — Probabilistic Accuracy Tracking

BS = (1/n) * SUM_i [ (p_hat_i - y_i)^2 ]

Computed over the same rolling W = 500 window as ECE.

**Reference baseline from Phase 2.08:** BS_ref = 0.1211.

**Brier Skill Score (relative degradation):**

BSS = 1 - (BS_current / BS_ref)

A BSS < -0.05 (5% relative degradation) triggers a **Yellow** calibration flag even if ECE alone is within Green band.

### 2.5 Inference Telemetry Metrics

In addition to statistical drift and calibration metrics, the `/v1/diagnostics` endpoint reports the following operational telemetry:

| Metric | Description |
| :--- | :--- |
| `requests_total` | Cumulative count of scoring requests since service start |
| `requests_single` | Count of `/v1/score` (single) requests |
| `requests_batch` | Count of `/v1/score/batch` requests |
| `latency_p50_ms` | Median end-to-end HTTP response latency (ms) |
| `latency_p95_ms` | 95th-percentile response latency (ms) |
| `latency_p99_ms` | 99th-percentile response latency (ms) |
| `window_size` | Number of observations in the current rolling calibration window |
| `scoring_window_start` | ISO 8601 timestamp of oldest observation in the rolling window |
| `scoring_window_end` | ISO 8601 timestamp of newest observation in the rolling window |

---

## 3. Drift Alert Action Matrix

The following matrix governs the automated response for each combination of drift signal and severity. **All responses are advisory only** — ADR 0002 authority boundary is strictly preserved.

| Signal | Severity | Primary Risk Driver Affected | Automated Response |
| :--- | :--- | :--- | :--- |
| PSI / CSI | Yellow Moderate | Any feature | Log to telemetry. Append `drift_warning` tag to diagnostic report. |
| PSI / CSI | Red Significant | Secondary feature | `drift_uncertain` flag on scoring outputs. Log model-risk alert. |
| PSI / CSI | Red Significant | Primary risk driver (`rolling_on_time_rate`, `late_payment_count`, `tenure_months`) | `drift_uncertain` flag. **Require specialist confirmation** for Tier 1 / Tier 2 recommended actions. Escalate to model-risk committee. |
| CSI | Any | Category `_UNSEEN_` bucket > 5% | `schema_change_alert`. Independent of PSI magnitude. |
| ECE | Yellow Moderate | — | `calibration_warning` tag in diagnostic report. |
| ECE | Red Significant | — | `calibration_uncertain` flag on all outputs. Escalate immediately. |
| BSS | Degraded < -0.05 | — | Trigger Yellow calibration flag regardless of ECE band. |

**Primary risk drivers** are defined as features with the three highest mean absolute SHAP attributions from Phase 2.09: `rolling_on_time_rate`, `late_payment_count`, and `tenure_months`.

---

## 4. Gateway Diagnostics Endpoint Contract

### 4.1 `GET /v1/diagnostics`

**Description:** Returns inference telemetry, PSI/CSI values for all 17 monitored features, rolling calibration metrics (ECE, Brier Score), and the current alert status matrix. Requires no request body.

**Response `200 OK` (OpenAPI schema excerpt):**

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-09-05T15:30:00Z",
  "service_uptime_seconds": 3600,
  "telemetry": {
    "requests_total": 1250,
    "requests_single": 1100,
    "requests_batch": 150,
    "latency_p50_ms": 2.1,
    "latency_p95_ms": 4.8,
    "latency_p99_ms": 8.3,
    "window_size": 500,
    "scoring_window_start": "2026-09-01T08:00:00Z",
    "scoring_window_end": "2026-09-05T14:59:00Z"
  },
  "feature_drift": {
    "reference_bundle_id": "inforsight-v6-logistic-platt-20260817",
    "reference_observation_count": 8560,
    "features": {
      "rolling_on_time_rate": {
        "is_primary_risk_driver": true,
        "feature_type": "continuous",
        "psi": 0.042,
        "status": "stable",
        "bin_count": 10
      },
      "late_payment_count": {
        "is_primary_risk_driver": true,
        "feature_type": "continuous",
        "psi": 0.187,
        "status": "moderate_shift",
        "bin_count": 10
      },
      "billing_frequency": {
        "is_primary_risk_driver": false,
        "feature_type": "categorical",
        "csi": 0.021,
        "status": "stable",
        "unseen_proportion": 0.0
      }
    }
  },
  "calibration": {
    "rolling_window_size": 500,
    "ece": 0.0183,
    "brier_score": 0.1248,
    "brier_skill_score": -0.031,
    "ece_status": "well_calibrated",
    "brier_status": "stable",
    "reference_ece": 0.0115,
    "reference_brier_score": 0.1211
  },
  "alert_summary": {
    "overall_status": "yellow",
    "active_alerts": [
      {
        "feature": "late_payment_count",
        "signal": "psi",
        "severity": "moderate_shift",
        "is_primary_driver": true,
        "action": "drift_warning"
      }
    ],
    "authorized_to_act": false,
    "action_authority_boundary": "ADR_0002_REQUIRES_HUMAN_REVIEW"
  }
}
```

### 4.2 Monitored Features

All 17 features from the Phase 2.10 release model bundle are monitored. The three designated primary risk drivers are explicitly flagged:

| Feature | Type | Primary Risk Driver |
| :--- | :--- | :---: |
| `rolling_on_time_rate` | continuous | YES |
| `late_payment_count` | continuous | YES |
| `tenure_months` | continuous | YES |
| `age_at_issue` | continuous | — |
| `annual_premium` | continuous | — |
| `base_annual_rate` | continuous | — |
| `coverage_amount` | continuous | — |
| `grace_period_count` | continuous | — |
| `market_benchmark_ratio` | continuous | — |
| `monthly_premium` | continuous | — |
| `rate_revision_count` | continuous | — |
| `reinstatement_count` | continuous | — |
| `total_premiums_paid` | continuous | — |
| `billing_frequency` | categorical | — |
| `initial_payment_method` | categorical | — |
| `policy_status` | categorical | — |
| `product_type` | categorical | — |

NOTE: `payment_frequency`, `risk_class`, `underwriting_class`, `servicing_advisor_id`, and `electronic_billing_enabled` are present in the raw feature contract but dropped during preprocessing. They are excluded from drift monitoring as they do not enter the model.

---

## 5. Architecture & Module Design

### 5.1 Directory Structure

```text
serving/
├── monitoring/
│   ├── __init__.py               # Public exports: DriftMonitor, CalibrationTracker
│   ├── baseline.py               # Loads and freezes training baseline distributions from bundle
│   ├── psi.py                    # PSI / CSI computation with zero-proportion guard
│   ├── calibration.py            # Rolling ECE, Brier Score, BSS computation
│   ├── telemetry.py              # In-memory latency ring buffer and request counter
│   ├── alert.py                  # Alert matrix: maps (signal, severity, feature) to action
│   └── models.py                 # Dataclasses: DriftReport, FeatureDriftResult, CalibrationReport, AlertSummary
└── tests/
    └── test_monitoring.py        # Monitoring unit tests
```

### 5.2 Key Data Structures

#### `FeatureDriftResult`
```python
@dataclass(frozen=True)
class FeatureDriftResult:
    feature_name: str
    feature_type: str            # "continuous" | "categorical"
    is_primary_risk_driver: bool
    psi_or_csi: float
    status: str                  # "stable" | "moderate_shift" | "significant_drift"
    unseen_proportion: float     # Categorical only; 0.0 for continuous
    bin_count: int
```

#### `CalibrationReport`
```python
@dataclass(frozen=True)
class CalibrationReport:
    window_size: int
    ece: float
    brier_score: float
    brier_skill_score: float
    ece_status: str              # "well_calibrated" | "moderate_decay" | "significant_decay"
    brier_status: str            # "stable" | "degraded"
    reference_ece: float         # 0.0115 (Phase 2.08 baseline)
    reference_brier_score: float # 0.1211 (Phase 2.08 baseline)
```

#### `AlertSummary`
```python
@dataclass(frozen=True)
class AlertSummary:
    overall_status: str          # "green" | "yellow" | "red"
    active_alerts: tuple[dict, ...]
    authorized_to_act: bool = False
    action_authority_boundary: str = "ADR_0002_REQUIRES_HUMAN_REVIEW"
```

### 5.3 Baseline Freezing Strategy

Training-time reference distributions are **extracted from the frozen model bundle** (`inforsight-v6-logistic-platt-20260817`) at service startup. Specifically:

- For continuous features: bin edges and reference proportions are computed from the calibration partition (8,560 rows, seed `20280201`) and stored as a frozen lookup dict keyed by feature name.
- For categorical features: reference category proportions are computed from the same calibration partition.
- Baseline computation is deterministic and verified against the Phase 2.10 bundle SHA-256 at startup.

This approach avoids any runtime access to training data files, keeping the serving container fully self-contained.

---

## 6. Acceptance Criteria

- [x] Design document specifies complete mathematical formulations for PSI, CSI, rolling ECE, Brier Score, and BSS.
- [x] `GET /v1/diagnostics` OpenAPI schema is predeclared and versioned at `schema_version: "1.0.0"`.
- [x] Predeclared drift thresholds (Green / Yellow / Red) for PSI, CSI, ECE, and BSS are formally documented with operational action per band.
- [x] Drift Alert Action Matrix covers all (signal x severity x driver tier) combinations.
- [x] `serving/monitoring/` reference module implements PSI, CSI, and rolling calibration computation deterministically.
- [x] Monitoring unit tests verify correct PSI/CSI computation, zero-proportion guard, threshold classification, and alert aggregation.
- [x] `authorized_to_act: false` and `ADR_0002_REQUIRES_HUMAN_REVIEW` are injected into every `/v1/diagnostics` response without exception.
- [x] Repository boundary and clean-room checks pass.

---

## 7. Execution Command Reference

```bash
# Run monitoring test suite
.venv/bin/python3 -m unittest serving/tests/test_monitoring.py

# Run full repository checks
make check
./scripts/check_repository_boundaries.sh
```

---

## 8. Verification Scorecard (Verified)

| Check | Target Standard | Status |
| :--- | :--- | :--- |
| **PSI/CSI Formulation** | Correct mathematical spec with zero-proportion guard | Verified (100%) |
| **Rolling ECE & BSS** | Rolling window W=500, correct bin computation | Verified (100%) |
| **Drift Threshold Matrix** | Green/Yellow/Red bands predeclared for all signals | Verified (100%) |
| **Alert Action Matrix** | All (signal x severity x driver) combinations covered | Verified (100%) |
| **`/v1/diagnostics` Schema** | OpenAPI schema versioned at `1.0.0` | Verified (100%) |
| **ADR 0002 Non-Authority Marker** | `authorized_to_act: false` on 100% of diagnostic responses | Verified (100%) |
| **Monitoring Unit Tests** | All tests pass in `serving/tests/test_monitoring.py` | Verified (44/44 passed) |
| **Gateway Regression Tests** | All tests pass in `serving/tests/test_gateway.py` | Verified (8/8 passed) |
| **Repository Boundaries** | Zero secret or real data leaks | Verified |
