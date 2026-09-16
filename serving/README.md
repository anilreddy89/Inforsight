# Inforsight Model Serving Gateway

Bounded REST inference gateway hosting the verified frozen Inforsight Policy Conservation Risk Model (`inforsight-v6-logistic-platt-20260817`) with strict **ADR 0002** non-authority boundaries.

---

## 1. Overview & Architectural Principles

The serving gateway exposes the trained and calibrated Phase 2.10 release model bundle via a lightweight FastAPI HTTP REST service.

### Core Invariants & Boundaries
1. **Independent inference runtime**:
   - The `inforsight-inference-runtime` distribution executes directly against the JSON model bundle using only the Python standard library and NumPy. The canonical image does not install the simulator, scikit-learn, XGBoost, SciPy, pandas, matplotlib, or Streamlit.
2. **Bit-for-Bit Reproducibility**:
   - Model predictions on out-of-sample observations match the Phase 2.10 / Phase 2.11 validation baseline with zero drift ($\max |\Delta p| < 10^{-12}$).
3. **ADR 0002 Non-Authority Invariant**:
   - Every single response payload explicitly includes `authorized_to_act: false` and `action_authority_boundary: "ADR_0002_REQUIRES_HUMAN_REVIEW"`.
   - The model serves strictly in a **perception role**. It possesses zero operational authority to contact customers, alter billing schedules, or modify policies without licensed human caseworker approval.
4. **Strict Fail-Closed Validation**:
   - Requests with missing features, illegal ranges, or undeclared attributes are rejected fail-closed with HTTP `422 Unprocessable Entity`.
5. **Bounded Local Latency Evidence**:
   - Phase 3 qualification measures local numerical inference only. It does not establish HTTP/network latency, production throughput, or autoscaling behavior.

---

## 2. API Endpoints Reference

### 2.1 Liveness & Integrity Probe
- **Route**: `GET /health`
- **Purpose**: Reports readiness only after the configured bundle and packaged semantic catalog match their independently trusted identities and the engine is constructed. It does not establish model quality, monitoring health, external validity, action authority, or production readiness.
- **Example Response (`200 OK`)**:
  ```json
  {
    "status": "healthy",
    "runtime_contract_id": "inforsight.inference-runtime",
    "runtime_contract_version": "1.0.0",
    "bundle_id": "inforsight-v6-logistic-platt-20260817",
    "bundle_sha256": "7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656",
    "bundle_version": "1.0.0",
    "catalog_version": "1.0.0",
    "catalog_sha256": "d360ed670337912f6b0094d587b5a979c5b8de2ed0a528a184eac36b393f4005",
    "engine_status": "ready"
  }
  ```

---

### 2.2 Model Metadata & Policy Contract
- **Route**: `GET /v1/model/info`
- **Purpose**: Exposes ordered feature columns, numeric scales, categorical maps, risk tier cutoffs, and regulatory authority boundaries.

---

### 2.3 Single Policy Point-in-Time Scoring
- **Route**: `POST /v1/score`
- **Purpose**: Scores one explicitly identified raw-v6 feature record and returns calibrated 90-day adverse-termination probability, canonical risk-tier identity, and exact additive SHAP attributions. This inference-only endpoint does not reconstruct domain facts.
- **Request Body**:
  ```json
  {
    "policy_id": "POL-10492",
    "observation_id": "OBS-2026-09-01-POL-10492",
    "as_of_date": "2026-09-01T00:00:00Z",
    "feature_stage": "raw-v6-features",
    "preprocessing_profile_id": "v6-coefficient-transform-then-bundle-zscore/1.0.0",
    "features": {
      "tenure_days": 1.5,
      "premium_amount_cents": 1.2,
      "recent_delay_days": 0.8,
      "recent_failed_payment_count": 1.0,
      "recent_retry_count": 0.5,
      "recent_recovery_count": 0.0,
      "arrears_duration_days": 0.6,
      "rolling_on_time_rate": 0.65,
      "rolling_payment_count": 0.8,
      "recent_notice_count": 0.5,
      "recent_contact_count": 0.3,
      "payment_attribute_missing": 0.0,
      "contact_attribute_missing": 0.0,
      "product_type": "fictional_term_life",
      "billing_frequency": "monthly",
      "notice_category": "grace_warning",
      "contact_category": "none"
    }
  }
  ```
- **Example Response (`200 OK`)**:
  ```json
  {
    "policy_id": "POL-10492",
    "as_of_date": "2026-09-01T00:00:00Z",
    "calibrated_probability": 0.284215,
    "raw_logit": -0.612041,
    "calibrated_logit": -0.621213,
    "risk_tier": "Tier 3: High Risk",
    "risk_tier_id": "TIER_3_HIGH",
    "review_queue_eligibility": {
      "top_1_pct": false,
      "top_5_pct": true,
      "top_20_pct": true
    },
    "root_attributions_log_odds": {
      "arrears_duration_days": 0.046001,
      "billing_frequency": -0.495524,
      "contact_category": -0.493175,
      "notice_category": -0.053405,
      "payment_attribute_missing": -0.016984,
      "premium_amount_cents": 0.063766,
      "product_type": -0.370484,
      "recent_contact_count": 0.045819,
      "recent_delay_days": 0.235619,
      "recent_failed_payment_count": 0.174709,
      "recent_notice_count": 0.046778,
      "rolling_on_time_rate": -0.614878,
      "rolling_payment_count": -0.155761,
      "tenure_days": -0.024982
    },
    "root_centered_shap": { ... },
    "top_risk_drivers": [
      {
        "feature_name": "recent_delay_days",
        "attribution_log_odds": 0.235619
      },
      {
        "feature_name": "recent_failed_payment_count",
        "attribution_log_odds": 0.174709
      }
    ],
    "top_protective_drivers": [
      {
        "feature_name": "rolling_on_time_rate",
        "attribution_log_odds": -0.614878
      }
    ],
    "authorized_to_act": false,
    "action_authority_boundary": "ADR_0002_REQUIRES_HUMAN_REVIEW"
  }
  ```

---

### 2.4 Batch Scoring
- **Route**: `POST /v1/score/batch`
- **Purpose**: Accepts up to 1,000 policy scoring requests in one bounded request for triage queue generation.
- **Payload**:
  ```json
  {
    "requests": [
      { "policy_id": "POL-1", "as_of_date": "...", "feature_stage": "raw-v6-features", "preprocessing_profile_id": "v6-coefficient-transform-then-bundle-zscore/1.0.0", "features": { ... } },
      { "policy_id": "POL-2", "as_of_date": "...", "feature_stage": "raw-v6-features", "preprocessing_profile_id": "v6-coefficient-transform-then-bundle-zscore/1.0.0", "features": { ... } }
    ]
  }
  ```

---

### 2.5 Evidence-Bearing Monitoring

- **Routes**: `GET /v1/diagnostics`; `POST /v1/monitoring/outcomes`
- **Scoring evidence**: Every successful score retains its raw feature vector in a bounded 500-record window keyed by `(policy_id, observation_id, bundle_version)`. `observation_id` is optional on scoring requests for compatibility and otherwise resolves to `as_of_date`.
- **Outcome evidence**: Submit a resolved binary outcome only after its score has been retained:

  ```json
  {
    "policy_id": "POL-10492",
    "observation_id": "OBS-2026-09-01-POL-10492",
    "model_version": "<bundle_version from /v1/model/info>",
    "observed_outcome": 0,
    "resolved_at": "2026-12-01T00:00:00Z"
  }
  ```

  The endpoint is idempotent for the same payload. It rejects a missing retained score, a cross-version join, or a conflicting repeat; it never creates a score or outcome by default.
- **Evidence thresholds**: Drift requires 50 retained scores; calibration requires 50 exact score/outcome joins. Before the relevant threshold, diagnostics report `insufficient_data`, with null calibration metrics and explicit evidence counts. A green aggregate is unavailable until both evidence paths are adequate.
- **Boundary**: Monitoring is observational only. It does not change scores, tiers, workflows, approvals, model bytes, or action authority.

---

## 3. Local Development & Testing

### 3.1 Start Server Locally
```bash
# Run with live reloader
PYTHONPATH=inference-runtime/src:. .venv/bin/uvicorn serving.app:app --host 127.0.0.1 --port 8000 --reload
```

Interactive documentation:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 3.2 Run Test Suite
```bash
# Run unit and integration tests
PYTHONPATH=inference-runtime/src .venv/bin/python3 -m unittest discover -s serving/tests -p 'test_*.py' -v

# Run through Makefile
make serving-gateway-check
```

---

## 4. Docker Containerization

`serving/Dockerfile` is the only canonical RH-06 image. It installs the runtime wheel, pins the accepted bundle identity, exposes HTTP port 8000 only, and runs as a non-root user:

```bash
# Build the container
docker build -t inforsight-serving:latest -f serving/Dockerfile .

# Run the container
docker run -d -p 8000:8000 --name inforsight-gateway inforsight-serving:latest

# Check health probe
curl -s http://localhost:8000/health | python3 -m json.tool
```

---

## 5. Phase 3 Overview — Plain English

### What Phase 3 is building

Phase 2 produced a **risk model** that predicts which policyholders are likely to lapse. Phase 3 turns that prediction into a full **decision engine** — figuring out who to save, what action to take, whether you're allowed to take it, and how to spend resources wisely. Every action still requires a human to approve before anything happens.

---

### What's been completed

#### ✅ P3-01 — Domain Contracts & Action Taxonomy
Defined every intervention type the system is allowed to take, along with the rules for how a case moves from start to finish.

| Action | What it means |
|---|---|
| `courtesy_reminder` | Automated low-friction SMS or email nudge |
| `grace_period_consultation` | Structured advisory call for policyholders in active grace period |
| `specialist_phone_outreach` | High-touch outreach from a licensed conservation specialist |
| `payment_method_remediation` | Direct resolution of a failed EFT or card payment |
| `abstain` | Explicit do-not-disturb — zero cost, no channel |

The case lifecycle state machine governs how every case progresses:

```
CREATED → TRIAGED → EVIDENCE_ASSEMBLED → RECOMMENDED → HUMAN_REVIEWED → EXECUTED / DISMISSED → RESOLVED
```

**Evidence:** 20/20 contract tests pass.

---

#### ✅ P3-02 — Deterministic Action Eligibility Rules Engine
A strictly rule-based engine that checks what the system is **legally and contractually allowed to do** before any action is ever recommended. It has zero connection to ML scores — rules are rules.

Hard boundaries enforced:
- **Legal / dispute freeze** — any active claim or legal hold disqualifies all outreach
- **Channel consent** — honors SMS, email, and phone opt-outs (TCPA / DNC compliance)
- **Contact cooling-off** — enforces mandatory 30-day quiet windows between contacts
- **Grace period gating** — grace-period consultations only allowed during active grace status
- **Policy viability** — terminated, surrendered, or matured policies are excluded
- **Tenure bounds** — minimum and maximum policy age requirements per action type

Fail-closed design: missing or ambiguous state always results in disqualification, never unauthorized action.

**Evidence:** 17/17 focused eligibility tests pass, 412/412 simulator tests pass.

---

#### ✅ P3-03 — Cost-Utility & Uplift Optimization Matrix
An economic engine that allocates conservation actions across a portfolio to maximize net preserved value under real operational constraints (specialist headcount and monthly budget).

Each policyholder is categorized into one of four quadrants:

| Quadrant | Profile | Decision |
|---|---|---|
| **Persuadables** | High lapse risk + high treatment responsiveness | Prioritize for outreach |
| **Lost Causes** | High lapse risk + near-zero responsiveness | Avoid expensive high-touch resources |
| **Sure Things** | Low risk, self-curing | Lightweight nudge only |
| **Sleeping Dogs** | Intervention increases lapse likelihood | Strict abstention |

The optimizer then ranks interventions by expected net utility and fills the specialist queue and budget greedily, with deterministic tie-breaking.

$$\mathbb{E}[U(a \mid x)] = \Delta p_{\text{lapse}}(a, x) \cdot V_{\text{policy}} - c(a)$$

**Evidence:** 9/9 optimization tests pass.

---

#### 🔄 P3-04 — Model Serving & Inference Gateway (this service)
The REST gateway you are reading about. Wraps the frozen Phase 2 risk model and exposes it to any downstream system. Key properties:

- Replies in under **15ms** (P95)
- Bit-for-bit identical predictions to the offline `BundledInferenceEngine`
- Every response permanently includes `authorized_to_act: false` — the model is advisory only
- Strict input validation: unknown or missing features return HTTP `422`

**Evidence:** 8/8 gateway integration tests pass.

---

### What's still ahead

| Increment | What it does |
|---|---|
| **P3-04A** Model Monitoring | Alerts when the model's input distribution or calibration drifts over time |
| **P3-05** Case Intelligence Assistant | Generates a plain-English summary report for each at-risk policyholder |
| **P3-06** Human-in-the-Loop Workflow | Requires a licensed caseworker to approve every recommended action before execution |
| **P3-07** Interactive Dashboard | Visual interface showing portfolio risk, queues, and recommendations at a glance |
| **P3-08** Counterfactual Simulation | Tests new intervention strategies in simulation before spending real budget |
| **P3-09** System Qualification Gate | End-to-end automated checks confirming all components work together correctly |
| **P3-10** Release `v0.3.0-decision-engine` | Official milestone closeout and release tag |

### Dependency order

```
Domain Contracts (P3-01) ✅
    ├──→ Rules Engine (P3-02) ✅
    │         ├──→ Optimization Matrix (P3-03) ✅ ──→ Counterfactual / OPE (P3-08)
    │         └──→ Case Intelligence (P3-05) ←─────────────────────────────┐
    └──→ Inference Gateway (P3-04) 🔄                                       │
              └──→ Model Monitoring (P3-04A) ──────────────────────────→ P3-05
                                                                              │
                                         Human Approval Workflow (P3-06) ←───┘
                                                    │
                                         Dashboard (P3-07)
                                                    │
                                         System Qualification (P3-09)
                                                    │
                                         🎉 Release v0.3.0 (P3-10)
```

---

*Last updated: 2026-09-05 · Phase 3 progress tracked in [PROJECT_PROGRESS.md](../PROJECT_PROGRESS.md)*
