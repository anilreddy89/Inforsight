# Model Card for Inforsight Life Insurance Conservation Risk Model

## Model Details

- **Model Name**: Inforsight Conservation Intelligence Risk Model (Baseline v0.2.0)
- **Model Version**: `1.0.0` (`inforsight-v6-logistic-platt-20260817`)
- **Model Type**: $L_2$-regularized Logistic Regression ($C=1.0$, `liblinear` solver) with post-hoc univariate Platt scaling calibration
- **Release Date**: September 2026
- **License**: Apache 2.0
- **Governing Architecture Decisions**:
  - [ADR 0001: Clean-Room Policy and Synthetic Data Foundation](docs/adr/0001-clean-room-and-synthetic-data.md)
  - [ADR 0002: Action Authority Separation — Perception vs. Action Eligibility](docs/adr/0002-separate-risk-from-action-eligibility.md)
  - [ADR 0003: Local Deterministic Execution and Reproducibility](docs/adr/0003-start-local-and-defer-distributed-infrastructure.md)
  - [ADR 0012: Bounded Sigmoid Hazard Link Architecture](docs/adr/0012-bounded-sigmoid-hazard-link-architecture.md)
  - [ADR 0013: Statistical Acceptance Protocol 3.1.0](docs/adr/0013-amend-v6-statistical-acceptance-protocol.md)
- **Model Artifact**: [`docs/experiments/phase-02-10-model-bundle.json`](docs/experiments/phase-02-10-model-bundle.json) (SHA-256: `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`)
- **Evaluation Manifest**: [`docs/experiments/phase-02-11-final-evaluation-manifest.json`](docs/experiments/phase-02-11-final-evaluation-manifest.json)
- **Feedback & Issues**: [GitHub Issue Tracker](https://github.com/anilreddy89/Inforsight/issues)

---

## Intended Use

### Primary Intended Use
The model generates well-calibrated posterior probability estimates ($\hat{p} \in [0, 1]$) representing the likelihood that an active individual life insurance policy will lapse or surrender over the subsequent 90-day observation horizon.

The outputs are designed strictly for **operational perception and conservation queue triage**:
1. **Queue Prioritization**: Sorting active policyholder accounts by risk to prioritize conservation outreach under fixed operational capacity budgets (Top 1%, 5%, and 20% review queues).
2. **Perceptual Situational Awareness**: Providing conservation caseworkers with directional risk drivers (additive log-odds and centered SHAP attributions) to understand behavioral signals contributing to risk.

### Out-of-Scope and Prohibited Uses
- **Autonomous Action Prohibited**: The model possesses zero authority to execute customer communications, issue payment retries, alter billing terms, or adjust policy parameters autonomously.
- **Adverse Underwriting & Pricing Prohibited**: The model must never be used for initial underwriting, risk selection, premium loading, denial of coverage, or policy termination.
- **Causal Interpretation Prohibited**: Model explanations reflect observational statistical associations ($P(y \mid x)$), not causal effects ($P(y \mid \text{do}(x))$). Operators must not treat model coefficients as causal levers.
- **Real-World Deployment Prohibited Without Field Validation**: The model was trained and evaluated strictly on synthetic benchmark data; deployment against real human policyholders without comprehensive real-world validation and compliance approval is prohibited.

---

## Factors & Feature Contract

The model scores observations using **17 point-in-time public features** (13 standard-scaled numeric features and 4 one-hot encoded categorical features, expanding to 27 input columns). All features strictly satisfy point-in-time visibility ($t_{\text{effective}} \le t_{\text{as\_of}}$ and $t_{\text{ingested}} \le t_{\text{as\_of}}$).

| Feature Name | Category | Description | Scaler / Encoding |
| --- | --- | --- | --- |
| `tenure_days` | Numeric | Policy tenure at observation cutoff | Standard scaled ($\mu=1.706, \sigma=1.042$) |
| `premium_amount_cents` | Numeric | Contract premium amount | Log1p standard scaled ($\mu=0.963, \sigma=0.015$) |
| `recent_delay_days` | Numeric | Payment delay days in preceding window | Standard scaled ($\mu=0.106, \sigma=0.315$) |
| `recent_failed_payment_count` | Numeric | Count of failed payment attempts | Standard scaled ($\mu=0.014, \sigma=0.088$) |
| `recent_retry_count` | Numeric | Count of payment retries triggered | Standard scaled ($\mu=0.011, \sigma=0.076$) |
| `recent_recovery_count` | Numeric | Count of successful recoveries post-failure | Standard scaled ($\mu=0.008, \sigma=0.065$) |
| `arrears_duration_days` | Numeric | Accumulated duration in grace/arrears status | Standard scaled ($\mu=0.013, \sigma=0.081$) |
| `rolling_on_time_rate` | Numeric | Historical fraction of payments made on time | Standard scaled ($\mu=0.273, \sigma=0.366$) |
| `rolling_payment_count` | Numeric | Historical count of completed billing cycles | Standard scaled ($\mu=0.159, \sigma=0.219$) |
| `recent_notice_count` | Numeric | Count of service or billing notices issued | Standard scaled ($\mu=0.111, \sigma=0.316$) |
| `recent_contact_count` | Numeric | Count of customer service interactions | Standard scaled ($\mu=0.098, \sigma=0.298$) |
| `payment_attribute_missing` | Indicator | Flag for unobserved payment attributes | Binary indicator ($\mu=0.020, \sigma=0.141$) |
| `contact_attribute_missing` | Indicator | Flag for unobserved contact attributes | Binary indicator ($\mu=0.000, \sigma=0.000$) |
| `product_type` | Categorical | Insurance product (`fictional_term_life`, `fictional_whole_life`) | One-hot encoded (2 levels + `__unknown__`) |
| `billing_frequency` | Categorical | Payment frequency (`monthly`, `quarterly`, `semiannual`, `annual`) | One-hot encoded (4 levels + `__unknown__`) |
| `notice_category` | Categorical | Most recent notice type | One-hot encoded (3 levels + `__unknown__`) |
| `contact_category` | Categorical | Most recent contact inquiry type | One-hot encoded (3 levels + `__unknown__`) |

---

## Training and Evaluation Data

### Dataset Profile
- **Data Source**: Inforsight Synthetic Modeling Corpus Generation v6 (Bounded Sigmoid Hazard Link architecture).
- **Cohort Structure**: 24 monthly policy-issuance cohorts spanning 2 calendar years, avoiding temporal confounding (`LIM-002-001`).
- **Target Label**: Binary indicator $y \in \{0, 1\}$ denoting policy lapse or surrender within the 90-day horizon following $t_{\text{as\_of}}$. Right-censored policies are strictly excluded from labeled evaluation.
- **Partition Allocation**: Pre-assigned before random draws:
  - `fit` (Fit / Training): 43,590 observations across 7,200 policies.
  - `selection` (Model Selection): 9,034 observations across 1,440 policies.
  - `calibration` (Platt Calibrator Fitting): 8,560 observations across 1,440 policies.
  - `non_final_evaluation` (Out-of-Sample Final Evaluation): 8,782 observations across 1,440 policies.
  - `acceptance` (Reserved Multi-Seed Acceptance): 17,300 observations per seed across 2,880 policies.

---

## Quantitative Performance Metrics

Evaluated strictly out-of-sample on the 8,782 observations of the `non_final_evaluation` partition of seed `20280201`:

### Discrimination & Overall Quality
- **ROC AUC**: **`0.6998`** (95% Clustered Bootstrap CI: `[0.6847, 0.7153]`)
- **Average Precision (PR AUC)**: **`0.2765`** (95% Clustered Bootstrap CI: `[0.2560, 0.2994]`)
- **Brier Score**: **`0.1211`** (95% Clustered Bootstrap CI: `[0.1170, 0.1252]`)
- **Brier Skill Score**: **`+0.0633`** (improvement over naive prevalence baseline)

### Probability Calibration
- **Expected Calibration Error (ECE)**: **`0.0115`** (1.15% average deviation across 10 uniform bins)
- **Maximum Calibration Error (MCE)**: **`0.0399`** (3.99% maximum bin error)
- **Calibration Slope**: **`0.9498`** (falls strictly within governed `[0.85, 1.15]` interval)
- **Calibration Intercept**: **`-0.1155`**

### Operational Review Queue Utility

| Review Queue | Cutoff Probability | Reviewed Accounts | True Lapses Caught | Precision (95% CI) | Recall (95% CI) | Lift (95% CI) | NNR |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Top 1%** | $p \ge 0.4542$ | 88 | 30 | **34.09%** `[23.33%, 43.68%]` | **2.24%** `[1.56%, 2.84%]` | **2.23x** `[1.55x, 2.85x]` | 2.93 |
| **Top 2%** | $p \ge 0.4050$ | 176 | 71 | **40.34%** `[32.40%, 46.82%]` | **5.30%** `[4.30%, 6.09%]` | **2.64x** `[2.15x, 3.03x]` | 2.48 |
| **Top 5%** | $p \ge 0.3459$ | 439 | 155 | **35.31%** `[30.47%, 39.77%]` | **11.57%** `[10.06%, 12.93%]` | **2.31x** `[2.01x, 2.59x]` | 2.83 |
| **Top 10%** | $p \ge 0.2976$ | 878 | 283 | **32.23%** `[29.45%, 35.75%]` | **21.12%** `[19.42%, 23.20%]` | **2.11x** `[1.94x, 2.32x]` | 3.10 |
| **Top 20%** | $p \ge 0.2402$ | 1,756 | 531 | **30.24%** `[28.09%, 32.56%]` | **39.63%** `[37.50%, 42.21%]` | **1.98x** `[1.87x, 2.11x]` | 3.31 |

*Note: Number Needed to Review (NNR) denotes caseworkers needed to intercept one true policy lapse.*

---

## Ethical Considerations & Fairness Disclosures

### 1. Synthetic Data Provenance
All training, calibration, and evaluation datasets were generated using synthetic statistical processes designed to simulate policy lifecycle dynamics and payment behaviors. No personal identifiable information (PII), customer records, or proprietary carrier data were utilized.

### 2. Absence of Demographic Subgroup Fairness Assessment
**CRITICAL DISCLOSURE**: The synthetic modeling corpus intentionally does not contain demographic attributes (such as race, ethnicity, biological sex, gender identity, age, health status, disability, national origin, or socio-economic indicators). Consequently:
- **No subgroup fairness, disparate impact, or equality of odds analysis was performed.**
- **No claim of algorithmic fairness or unbiased real-world behavior is made.**
- Prior to adapting this architecture for real-world life insurance conservation, operators must perform a rigorous demographic fairness and bias assessment conforming to state and federal insurance regulations (e.g., NAIC Model Bulletin on AI, Colorado SB 21-169).

### 3. Action-Authority Governance (ADR 0002)
To safeguard consumers against automated adverse actions, the model operates under strict four-tier governance boundaries:
- **Tier 1 (Perception Layer)**: The model and its explainability attributions only provide situational awareness.
- **Tier 2 (Deterministic Rule Validation)**: Any account flagged for conservation outreach must independently pass strict business rules (grace period verification, communication frequency limits, opt-out status).
- **Tier 4 (Licensed Human Review)**: Every substantive conservation decision requires review and final authorization by a licensed human conservation specialist. Autonomous customer cancellation, outreach, or policy alteration is architecturally prohibited.

---

## Caveats and Limitations

1. **Synthetic Environment Generalization**: Because the model was optimized to recover mechanisms from the Generation v6 bounded hazard simulator, its learned weights reflect simulated distributions rather than actual market lapse dynamics.
2. **Simplified Product Portfolio**: Evaluates fictional term and whole life products with standard billing cadences. Complex universal life products (cash value accumulation, shadow accounts, policy loans, index options) are not modeled.
3. **Macroeconomic Stationarity**: Assumes stationary baseline lapse risk; macroeconomic fluctuations (interest rate shocks, inflation spikes, unemployment surges) are outside model scope.

---

## Technical Specifications & Environment

- **Python Version**: `3.11+`
- **Dependencies**: `numpy==2.2.3`, `scikit-learn==1.6.1`, `scipy==1.15.2`
- **Runtime Serving Engine**: Pure-NumPy `BundledInferenceEngine` with zero runtime `scikit-learn` dependency.
- **Bit-for-Bit Reproducibility**: Max probability delta upon serialized bundle reload is $2.22 \times 10^{-16} \le 1.00 \times 10^{-12}$.

