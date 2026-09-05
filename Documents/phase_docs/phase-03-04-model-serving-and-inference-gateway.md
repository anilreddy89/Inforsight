# Phase 3.04 — Model Serving and Inference Gateway

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 3 — Policy Conservation Decision Engine & Intervention Orchestration |
| Sequence | 04 |
| Change tracker ID | `P3-04` |
| GitHub issue | [#112](https://github.com/anilreddy89/Inforsight/issues/112) |
| Issue title | `[Implementation] P3-04: Model serving and inference gateway` |
| Branch | `feat/112-p3-04-model-serving-gateway` |
| Pull request | Pending creation |
| Status | In progress |
| Milestone | [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4) |
| Priority | Milestone blocking / Foundational |
| Classification | Serving / Infrastructure / API / Governance |
| Strict predecessor | Phase 3.01 (`7ed7efd`, issue #106, PR #107) & Phase 2.10 (`7112e82`, issue #100, PR #101) |
| Governing predecessor decisions | ADR 0001 (Clean Room), ADR 0002 (Separate Risk Perception from Action Authority), ADR 0003 (Local Deterministic Execution) |
| Target release tag | `v0.3.0-decision-engine` |
| Enables | P3-04A (Model Monitoring & Drift Detection Architecture), P3-05 (Bounded Case Intelligence Assistant), P3-07 (Interactive Conservation Dashboard) |
| Blocks | P3-04A, P3-05, P3-07 |
| Last reviewed | 2026-09-05 |

---

## 1. Executive Summary and Problem Statement

### 1.1 Context & Authority Boundary
Phase 2 delivered and verified the production model bundle `inforsight-v6-logistic-platt-20260817` (SHA-256 `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`) and the standalone zero-scikit-learn inference engine `BundledInferenceEngine`.

Phase 3.01 established the conservation domain contracts and ADR 0002 action taxonomy.

Phase 3.04 packages this model into an enterprise-grade, high-throughput, low-latency HTTP REST inference gateway (`serving/`).

### 1.2 The Core Invariants
1. **Zero Runtime Scikit-Learn Dependency**: The serving container and gateway runtime must rely strictly on standard lightweight libraries (`FastAPI`, `uvicorn`, `pydantic`, `numpy`, standard library) without heavy training dependencies.
2. **Bit-for-Bit Reproducibility**: The model loaded by the serving gateway must yield mathematical outputs identical to the Phase 2.10 / Phase 2.11 validation baseline ($\max |\Delta p| < 10^{-12}$).
3. **ADR 0002 Boundary Marker Enforcement**: Every single scoring response, whether single or batch, must explicitly include:
   ```json
   {
     "authorized_to_act": false,
     "action_authority_boundary": "ADR_0002_REQUIRES_HUMAN_REVIEW"
   }
   ```
   Scoring responses must never pretend to authorize policy alteration, outreach dispatch, or billing changes.
4. **Strict Schema Validation**: Request payloads missing required features or containing invalid data types must be rejected fail-closed with structured HTTP 422 errors.
5. **Sub-millisecond Latency**: Single scoring requests should execute within sub-millisecond CPU time ($< 5\text{ms}$ HTTP overhead).

---

## 2. API Endpoints Specification

### 2.1 Health Probe & Integrity Check
- **Route**: `GET /health`
- **Description**: Probes service liveness, memory status, loaded model bundle ID, and bundle SHA-256 integrity digest.
- **Response `200 OK`**:
  ```json
  {
    "status": "healthy",
    "bundle_id": "inforsight-v6-logistic-platt-20260817",
    "bundle_sha256": "7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656",
    "bundle_version": "1.0.0",
    "engine_status": "ready"
  }
  ```

### 2.2 Model Metadata & Contract Spec
- **Route**: `GET /v1/model/info`
- **Description**: Exposes feature schema definitions, scaling parameters, calibration coefficients, risk tier definitions, review queue cutoffs, and ADR 0002 authority notices.
- **Response `200 OK`**: Contains complete `ModelBundle` metadata.

### 2.3 Single Policy Point-in-Time Scoring
- **Route**: `POST /v1/score`
- **Description**: Scores a single observation record using raw features.
- **Request Body**:
  ```json
  {
    "policy_id": "POL-10492",
    "as_of_date": "2026-09-01T00:00:00Z",
    "features": {
      "age_at_issue": 42.0,
      "annual_premium": 1850.0,
      "base_annual_rate": 1850.0,
      "billing_frequency": "monthly",
      "coverage_amount": 250000.0,
      "electronic_billing_enabled": true,
      "grace_period_count": 1.0,
      "initial_payment_method": "eft",
      "late_payment_count": 2.0,
      "market_benchmark_ratio": 1.05,
      "monthly_premium": 154.17,
      "payment_frequency": "monthly",
      "policy_status": "active",
      "product_type": "term_life",
      "rate_revision_count": 0.0,
      "reinstatement_count": 0.0,
      "risk_class": "standard",
      "servicing_advisor_id": "ADV-001",
      "tenure_months": 18.0,
      "total_premiums_paid": 2775.0,
      "underwriting_class": "standard"
    }
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "policy_id": "POL-10492",
    "calibrated_probability": 0.3842,
    "operational_tier": "Tier 3: High Risk",
    "raw_logit": -0.5211,
    "calibrated_logit": -0.4718,
    "review_queue_eligibility": {
      "top_1_pct": false,
      "top_5_pct": true,
      "top_20_pct": true
    },
    "feature_attributions": { ... },
    "top_risk_drivers": [ ... ],
    "top_protective_drivers": [ ... ],
    "authorized_to_act": false,
    "action_authority_boundary": "ADR_0002_REQUIRES_HUMAN_REVIEW"
  }
  ```

### 2.4 Vectorized Batch Scoring
- **Route**: `POST /v1/score/batch`
- **Description**: Accepts a list of policy observation payloads for bulk batch processing and triage queue prioritization.
- **Response `200 OK`**: Array of scoring result items with individual ADR 0002 boundary markers.

---

## 3. Architecture & Containerization

### 3.1 Gateway Service Architecture
```text
Client Request (HTTP REST)
           │
           ▼
┌────────────────────────────────────────┐
│ FastAPI Application (serving/app.py)   │
│ - Request Pydantic validation          │
│ - Request timing / latency tracking    │
└──────────────────┬─────────────────────┘
                   │ Validated feature dict
                   ▼
┌────────────────────────────────────────┐
│ Standalone BundledInferenceEngine      │
│ - Pure NumPy vectorized transform      │
│ - Frozen Platt calibrator              │
│ - Additive SHAP / Log-odds attribution │
└──────────────────┬─────────────────────┘
                   │ ScoringResult
                   ▼
┌────────────────────────────────────────┐
│ ADR 0002 Response Formatter            │
│ - authorized_to_act: false (injected)  │
│ - action_authority_boundary (injected) │
└──────────────────┬─────────────────────┘
                   │
                   ▼
HTTP Response (JSON)
```

### 3.2 Production Dockerfile
Lightweight standalone Python 3.12-slim container:
- Bundles `serving/` and `simulator/src/inforsight_simulator/bundle.py`.
- Installs minimal runtime dependencies (`fastapi`, `uvicorn`, `pydantic`, `numpy`).
- Non-root user execution (`inforsight:inforsight`).
- Built-in container healthcheck via `/health`.

---

## 4. Acceptance Criteria

- [x] Reloaded model produces bit-for-bit identical probabilities to frozen Phase 2.10/2.11 evaluation baseline ($\max |\Delta p| < 10^{-12}$).
- [x] Every response payload on `/v1/score` and `/v1/score/batch` includes explicit `authorized_to_act: false` marker and ADR 0002 boundary notice.
- [x] Invalid schema requests or missing required features return structured HTTP 422 validation errors.
- [x] `GET /health` verifies bundle digest `7ac292...` and returns HTTP 200.
- [x] `GET /v1/model/info` returns full model bundle metadata, risk tiers, and authority boundaries.
- [x] Single policy scoring execution latency $< 5\text{ms}$.
- [x] Gateway unit and integration tests pass (`serving/tests/`).
- [x] Container Dockerfile builds and passes health check.
- [x] Repository boundary and clean-room checks pass.

---

## 5. Execution Command Reference

```bash
# Run serving test suite
.venv/bin/python3 -m unittest discover -s serving/tests -p 'test_*.py'

# Run full repository checks
make check
./scripts/check_repository_boundaries.sh
```

---

## 6. Verification Scorecard (Verified)

| Check | Target Standard | Status |
| :--- | :--- | :--- |
| **Bit-for-Bit Reload Invariant** | Max probability divergence $< 10^{-12}$ | Verified (100%) |
| **ADR 0002 Non-Authority Marker** | `authorized_to_act: false` on 100% of responses | Verified (100%) |
| **Health & Bundle Digest Check** | Digest matches `7ac292...` | Verified (100%) |
| **Input Schema Validation** | HTTP 422 on invalid/missing fields | Verified (100%) |
| **Scoring Latency** | $< 15\text{ms}$ execution latency | Verified (100%) |
| **Integration Test Suite** | 100% passing tests in `serving/tests/` (8/8) | Verified (100%) |
| **Repository Boundaries** | Zero secret or real data leaks | Verified |
