# Phase 2.09 — Model-Behavior Explanations and Action-Authority Boundaries Contract

**Contract Version**: `1.0.0`
**Phase**: `P2-09`
**Issue**: `#98`
**Milestone**: `v0.2.0-risk-model`
**Strict Predecessors**: Phase 2R.16A (PR #95, commit `4d7e9da`) & Phase 2.08 (PR #97, commit `3abb044`)
**Governing ADRs**: ADR 0001 (Clean-Room), ADR 0002 (Authority Separation), ADR 0012 (Bounded Sigmoid), ADR 0013 (Protocol 3.1.0)
**Governing Substrate Contract**: Substrate Contract version `6.0.0`
**Governing Evaluation Contract**: Evaluation Pipeline Contract version `6.0.0`
**Governing Calibration Contract**: Probability Calibration Contract version `1.0.0`
**Status**: `Active`

---

## 1. Scope and Objective

This contract specifies the mathematical definitions, verification invariants, directional sanity gates, and architectural authority boundaries for **Phase 2.09: Model-Behavior Explanations and Action-Authority Boundaries**.

The primary objective is to make the risk perception of the frozen, calibrated release candidate transparent to business actuaries and conservation operations while strictly prohibiting causal misinterpretation and unauthorized autonomous action.

---

## 2. Frozen Release Candidate & Preprocessing Invariants

### 2.1 Candidate Immutability
- **Candidate Model**: Logistic Regression ($L_2$ regularization, $C=1.0$, `liblinear` solver, tolerance $10^{-8}$, maximum iterations $1000$, `fit_intercept=True`, random seed `20260817`), selected under R2-15 Manifest version `6.0.0`.
- **Weight Immutability**: All 27 feature coefficients $\beta_j$ and intercept $\beta_0$ must remain strictly identical to their frozen state. Zero retraining or weight updates are permitted.

### 2.2 Calibrator Immutability
- **Selected Calibrator**: Platt Scaling ($A = 0.961849, B = -0.033420$), fit strictly on the $8,560$ observations of the `calibration` role partition of seed `20280201` under P2-08 Manifest version `1.0.0`.
- **Parameter Immutability**: Scaling parameters $A$ and $B$ are immutable constants.

### 2.3 Feature Pipeline Immutability
- **Feature Dictionary**: `6.0.0` defining 17 root features (13 standard-scaled numerics, 4 one-hot categoricals expanding to 27 transformed columns).
- **Preprocessor State**: Mean $\mu_j$ and scale $\sigma_j$ from `V6Preprocessor` fitted on selection fold fit partition.

### 2.4 Holdout Clean-Room Invariant
- **Final Release Holdout**: Must remain strictly undefined, unassigned, unread, and `not_materialized`. All explanations are computed strictly on non-test partitions (`calibration` and `non_final_evaluation`).

---

## 3. Mathematical Attribution Formulations

### 3.1 Calibrated Log-Odds Function
For transformed observation vector $x \in \mathbb{R}^{27}$, the calibrated log-odds is:
$$z_{\text{cal}}(x) = A \cdot \left(\beta_0 + \sum_{j=1}^{27} \beta_j \cdot x_j\right) + B = \phi_0 + \sum_{j=1}^{27} \beta_j^{\text{cal}} \cdot x_j$$
where:
$$\phi_0 = A \cdot \beta_0 + B$$
$$\beta_j^{\text{cal}} = A \cdot \beta_j$$

### 3.2 Additive Column-Level Attributions
For column $j \in \{1, \dots, 27\}$:
$$\phi_j(x) = \beta_j^{\text{cal}} \cdot x_j$$

**Invariant (Exact Column Additivity)**:
$$\left| z_{\text{cal}}(x) - \left( \phi_0 + \sum_{j=1}^{27} \phi_j(x) \right) \right| < 10^{-12} \quad \forall x$$

### 3.3 Grouped 17-Feature Root Attributions
Let $C(k) \subset \{1, \dots, 27\}$ denote the column indices corresponding to root feature $k \in \{1, \dots, 17\}$. The root attribution is:
$$\Phi_k(x) = \sum_{j \in C(k)} \phi_j(x)$$

**Invariant (Exact Root Feature Additivity)**:
$$\left| z_{\text{cal}}(x) - \left( \phi_0 + \sum_{k=1}^{17} \Phi_k(x) \right) \right| < 10^{-12} \quad \forall x$$

### 3.4 Centered Shapley Value Efficiency
With respect to the background evaluation distribution mean $\bar{x} = \mathbb{E}[x]$:
$$\text{Base Value} = \mathbb{E}[z_{\text{cal}}] = \phi_0 + \sum_{j=1}^{27} \beta_j^{\text{cal}} \cdot \bar{x}_j$$
$$\text{SHAP}_k(x) = \sum_{j \in C(k)} \beta_j^{\text{cal}} \cdot (x_j - \bar{x}_j)$$

**Invariant (Exact SHAP Efficiency)**:
$$\left| z_{\text{cal}}(x) - \left( \text{Base Value} + \sum_{k=1}^{17} \text{SHAP}_k(x) \right) \right| < 10^{-12} \quad \forall x$$

### 3.5 Global Importance Metric
Global feature importance is measured by mean absolute attribution across the evaluation partition:
$$\bar{\Phi}_k = \frac{1}{N} \sum_{i=1}^N |\Phi_k(x^{(i)})|$$
$$\text{Relative Importance } \%_k = \frac{\bar{\Phi}_k}{\sum_{m=1}^{17} \bar{\Phi}_m} \times 100\%$$

---

## 4. Directional Sanity Check Requirements

All 17 features must be evaluated against predeclared directional expectations:

1. **Payment Reliability Signals**:
   - `rolling_on_time_rate`: Expected $\beta < 0$ (Protective).
   - `recent_delay_days`: Expected $\beta > 0$ (Risk driver).
   - `recent_failed_payment_count`: Expected $\beta > 0$ (Risk driver).
   - `arrears_duration_days`: Expected $\beta > 0$ (Risk driver).
   - `recent_retry_count`: Expected $\beta > 0$ (Risk driver).
   - `recent_recovery_count`: Expected $\beta < 0$ (Protective).
2. **Policy Equity & Engagement Signals**:
   - `rolling_payment_count`: Expected $\beta < 0$ (Protective).
   - `tenure_days`: Expected $\beta < 0$ (Protective).
   - `premium_amount_cents`: Expected $\beta > 0$ (Higher commitment stress).
3. **Operational Contact & Notice Signals**:
   - `recent_notice_count`: Expected $\beta > 0$ (Risk driver).
   - `recent_contact_count`: Expected $\beta > 0$ (Risk driver).
   - `notice_category=none`: Expected $\beta < 0$ (Protective relative to active notice).
   - `contact_category=none`: Expected $\beta < 0$ (Protective relative to dispute).
4. **Billing Structure Signals**:
   - `billing_frequency=annual`: Expected higher hazard than `monthly` due to lump-sum payment shock.

**Gate Requirement**: 100% of directional sanity checks must be computed, verified, and explicitly dispositioned in the experiment report.

---

## 5. Local Representative Case Studies

The experiment must generate local waterfall profiles for 3 distinct, governed policy cases from the out-of-sample partition:
1. **Tier 1 Case (Low Risk, $p < 0.10$)**: Exemplifying strong protective payment history, zero arrears, and clean contact records.
2. **Tier 2 Case (Moderate Risk, $0.10 \le p < 0.25$)**: Exemplifying emerging friction (e.g., minor billing delay or annual billing structure).
3. **Tier 3 Case (High Risk, $0.25 \le p < 0.50$)**: Exemplifying severe arrears, failed payments, and multiple notices.

Each case must report:
- Observation and policy ID.
- Calibrated risk score $\hat{p}_{\text{cal}}$ and risk tier.
- Exact feature values, transformed values, and directional root attributions $\Phi_k$.
- Top 3 risk contributors (increasing log-odds) and top 3 protective contributors (decreasing log-odds).

---

## 6. ADR 0002 Action-Authority Boundaries (Mandatory Governance)

All generated artifacts, code documentation, and UI displays must strictly uphold the 4-tier authority hierarchy defined in **ADR 0002**:

1. **Tier 1 (Perception Layer)**:
   - Attributions explain *observational feature weighting* within the perception model.
   - Attributions have **zero autonomous authority** to trigger workflows, alter premiums, or send communications.
2. **Strict Non-Causal Boundary**:
   - Explanations describe statistical associations ($\hat{p}(y \mid x)$).
   - They do **not** assert causal counterfactuals ($\hat{p}(y \mid \text{do}(x))$). Operators must never claim that manually altering an observed feature will directly eliminate customer lapse risk.
3. **Tier 2 (Deterministic Rule Engine Gate)**:
   - Even if an explanation flags severe billing arrears, no outreach may occur without automated rule verification of grace period state, active legal disputes, communication frequency caps, and opt-out registries.
4. **Tier 4 (Licensed Human Officer Decision)**:
   - Licensed conservation specialists make all final decisions regarding customer offers, premium restructuring, or policy adjustments. Explanations serve strictly as decision support.

---

## 7. Execution and Verification Commands

The implementation must provide a CLI runner supporting reproducible execution:
```bash
# Write mode: execute evaluation and write manifest + report
python3 scripts/run_model_explanations.py --write

# Check mode: verify byte-for-byte reproducibility
python3 scripts/run_model_explanations.py --check
```

The verification suite must be integrated into `Makefile` as:
```makefile
model-explanations-check:
	$(PYTHON) scripts/run_model_explanations.py --check
	$(PYTHON) -m unittest simulator.tests.test_model_explanations -v
```

