# Inforsight Model Serving Gateway

Enterprise-grade, high-throughput, low-latency REST inference gateway hosting the frozen Inforsight Policy Conservation Risk Model (`inforsight-v6-logistic-platt-20260817`) with strict **ADR 0002** non-authority boundaries.

---

## 1. Overview & Architectural Principles

The serving gateway exposes the trained and calibrated Phase 2.10 release model bundle via a lightweight FastAPI HTTP REST service.

### Core Invariants & Boundaries
1. **Zero Scikit-Learn Dependency at Runtime**:
   - The inference engine (`BundledInferenceEngine`) executes directly against the pure-JSON model bundle using only standard libraries, NumPy, and Pydantic. Heavy training dependencies (`scikit-learn`, `scipy`) are completely omitted from the runtime container.
2. **Bit-for-Bit Reproducibility**:
   - Model predictions on out-of-sample observations match the Phase 2.10 / Phase 2.11 validation baseline with zero drift ($\max |\Delta p| < 10^{-12}$).
3. **ADR 0002 Non-Authority Invariant**:
   - Every single response payload explicitly includes `authorized_to_act: false` and `action_authority_boundary: "ADR_0002_REQUIRES_HUMAN_REVIEW"`.
   - The model serves strictly in a **perception role**. It possesses zero operational authority to contact customers, alter billing schedules, or modify policies without licensed human caseworker approval.
4. **Strict Fail-Closed Validation**:
   - Requests with missing features, illegal ranges, or undeclared attributes are rejected fail-closed with HTTP `422 Unprocessable Entity`.
5. **Sub-millisecond Latency Target**:
   - Vectorized single-record inference executes in sub-millisecond CPU time ($< 5\text{ms}$ HTTP response time).

---

## 2. API Endpoints Reference

### 2.1 Liveness & Integrity Probe
- **Route**: `GET /health`
- **Purpose**: Verifies gateway liveness and confirms the loaded bundle SHA-256 digest matches the verified manifest.
- **Example Response (`200 OK`)**:
  ```json
  {
    "status": "healthy",
    "bundle_id": "inforsight-v6-logistic-platt-20260817",
    "bundle_sha256": "7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656",
    "bundle_version": "1.0.0",
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
- **Purpose**: Scores an individual policyholder observation record and returns calibrated lapse probabilities, risk tier classification, and exact additive SHAP attributions.
- **Request Body**:
  ```json
  {
    "policy_id": "POL-10492",
    "as_of_date": "2026-09-01T00:00:00Z",
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

### 2.4 Vectorized Batch Scoring
- **Route**: `POST /v1/score/batch`
- **Purpose**: Accepts up to 1,000 policy scoring requests in a single batch for high-throughput operational triage queue generation.
- **Payload**:
  ```json
  {
    "requests": [
      { "policy_id": "POL-1", "as_of_date": "...", "features": { ... } },
      { "policy_id": "POL-2", "as_of_date": "...", "features": { ... } }
    ]
  }
  ```

---

## 3. Local Development & Testing

### 3.1 Start Server Locally
```bash
# Run with live reloader
PYTHONPATH=simulator/src:. .venv/bin/uvicorn serving.app:app --host 127.0.0.1 --port 8000 --reload
```

Interactive documentation:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 3.2 Run Test Suite
```bash
# Run unit and integration tests
.venv/bin/python3 -m unittest discover -s serving/tests -p 'test_*.py' -v

# Run through Makefile
make serving-gateway-check
```

---

## 4. Docker Containerization

The serving container uses a hardened multi-stage build running as a non-root user:

```bash
# Build the container
docker build -t inforsight-serving:latest -f serving/Dockerfile .

# Run the container
docker run -d -p 8000:8000 --name inforsight-gateway inforsight-serving:latest

# Check health probe
curl -s http://localhost:8000/health | python3 -m json.tool
```
