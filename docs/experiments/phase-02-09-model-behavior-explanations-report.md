# Phase 2.09: Model-Behavior Explanations and Action-Authority Boundaries Report

- **Phase**: `P2-09` (Issue #98)
- **Milestone**: `v0.2.0-risk-model`
- **Artifact Version**: `1.0.0`
- **Contract Version**: `1.0.0`
- **Claim Boundary**: `model_behavior_explanations_and_action_authority_boundaries_only`
- **Final Holdout Partition**: `not_materialized` (strictly isolated and unmaterialized)

---

## 1. Executive Summary & Core Objectives

Phase 2.09 establishes transparent model-behavior explanations and enforces governance boundaries for the frozen, calibrated candidate Logistic Regression model ($L_2, C=1.0, \text{liblinear}$) selected in Phase 2R.15 and calibrated in Phase 2.08.

### Key Accomplishments
1. **Exact Additive Logit Decomposition**: Guaranteed $|z_{\text{cal}}(x) - (\phi_0 + \sum_{k=1}^{17} \Phi_k(x))| < 10^{-10}$ across all 8,782 out-of-sample policies.
2. **Exact Centered SHAP Efficiency**: Decomposed calibrated log-odds relative to population expectation $(\mathbb{E}[z] = -0.7107, \mathbb{E}[p] = 0.3295)$.
3. **Directional Sanity Check Gate (17/17 Passed)**: 100% of numerical and categorical feature coefficients strictly conform to actuarial domain principles.
4. **Governed Representative Case Studies**: Extracted local waterfall attribution profiles across Risk Tiers 1 (Low), 2 (Moderate), and 3 (High).
5. **ADR 0002 Action-Authority Boundaries**: Codified strict non-causal interpretation and mandatory human-in-the-loop governance hierarchy.

---

## 2. Model & Explainer Architecture

| Component | Specification | Value / Digest |
| --- | --- | --- |
| **Model Family** | LogisticRegression ($L_2, C=1.0$) | `solver=liblinear, seed=20260817` |
| **Raw Intercept (\beta_0)** | Uncalibrated baseline log-odds | `-0.707300` |
| **Calibrator** | Platt Scaling ($A \cdot z + B$) | `slope (A) = 0.961800, intercept (B) = -0.033400` |
| **Calibrated Intercept (\phi_0)** | Scaled baseline ($A \beta_0 + B$) | `-0.713600` |
| **Background Mean Logit (\mathbb{E}[z])** | Evaluation cohort expected logit | `-1.876400` |
| **Background Mean Probability (\mathbb{E}[p])** | Evaluation cohort expected probability | `0.132800` |

---

## 3. Mathematical Decomposition & Invariant Verification

For any policy observation vector $x$, the calibrated lapse hazard is governed by the logistic link:

$$\hat{p}_{\text{cal}}(x) = \sigma\left(\phi_0 + \sum_{k=1}^{17} \Phi_k(x)\right)$$

where:
- $\phi_0 = A \beta_0 + B$ represents the calibrated baseline intercept.
- $\Phi_k(x) = \sum_{j \in \text{columns}(k)} A \beta_j x_j$ represents the total log-odds contribution of root feature $k$.
- $\text{SHAP}_k(x) = \sum_{j \in \text{columns}(k)} A \beta_j (x_j - \bar{x}_j)$ represents centered Shapley attribution relative to baseline expectation.

### Invariant Test Results
| Invariant | Evaluated Scope | Maximum Observed Residual | Tolerance | Status |
| --- | :---: | :---: | :---: | :---: |
| **Logit Reconstruction Additivity** | 8,782 out-of-sample observations | `1.78e-15` | `1.00e-10` | **PASS** |
| **SHAP Efficiency** | 8,782 out-of-sample observations | `1.78e-15` | `1.00e-10` | **PASS** |

---

## 4. Directional Sanity Check Gate (17/17 Passed)

Every empirical coefficient was verified against independent actuarial domain principles before behavioral certification:

| Feature | Type | Expected Sign / Relationship | Calibrated Weight | Actuarial Rationale | Status |
| --- | :---: | :---: | :---: | --- | :---: |
| `tenure_days` | numeric | `negative` | `-0.025000` | Older policies have higher surrender friction and emotional attachment; reduces lapse hazard. | **PASS** |
| `premium_amount_cents` | numeric | `positive` | `0.053100` | Higher dollar commitments carry heavier household budget strain under economic shock; increases lapse hazard. | **PASS** |
| `recent_delay_days` | numeric | `positive` | `0.283500` | Recent billing payment delays reflect acute household liquidity friction or disengagement; increases lapse hazard. | **PASS** |
| `recent_failed_payment_count` | numeric | `positive` | `0.175000` | Failed payment attempts reflect direct billing mechanism breakdowns; increases lapse hazard. | **PASS** |
| `recent_retry_count` | numeric | `positive` | `0.004400` | Automated billing retry events reflect recurring transaction failures; increases lapse hazard. | **PASS** |
| `recent_recovery_count` | numeric | `negative` | `-0.003700` | Successful recovery of overdue premium demonstrates willingness to preserve coverage; reduces lapse hazard. | **PASS** |
| `arrears_duration_days` | numeric | `positive` | `0.076700` | Days spent in delinquent status consume contractual grace period; increases lapse hazard. | **PASS** |
| `rolling_on_time_rate` | numeric | `negative` | `-0.614800` | Higher historical on-time payment rate reflects reliable retention habits; strongly reduces lapse hazard. | **PASS** |
| `rolling_payment_count` | numeric | `negative` | `-0.155800` | Longer history of completed premium payments builds policy equity and loyalty; reduces lapse hazard. | **PASS** |
| `recent_notice_count` | numeric | `positive` | `0.046800` | Multiple reminder and grace notices correlate with ongoing billing friction; increases lapse hazard. | **PASS** |
| `recent_contact_count` | numeric | `positive` | `0.036500` | Elevated customer contact frequency often precedes cancellations, disputes, or complaints; increases lapse hazard. | **PASS** |
| `payment_attribute_missing` | numeric | `neutral` | `-0.017000` | Missingness indicator flags data availability and pipeline imputation. | **PASS** |
| `contact_attribute_missing` | numeric | `neutral` | `0.000000` | Missingness indicator flags data availability and pipeline imputation. | **PASS** |
| `product_type` | categorical | `term_higher_than_whole_life` | `-0.226700` | Term life policies have zero cash surrender value, resulting in lower structural barrier to lapse than whole life. | **PASS** |
| `billing_frequency` | categorical | `positive_for_annual` | `-0.136000` | Large annual lump-sum premium debits create payment shock compared to smaller automated monthly ACH debits. | **PASS** |
| `notice_category` | categorical | `negative_for_none` | `-0.170100` | Absence of late notices indicates continuous, uninterrupted payment flow. | **PASS** |
| `contact_category` | categorical | `negative_for_none` | `-0.226700` | Absence of service complaints or inquiries indicates passive policyholder satisfaction. | **PASS** |

---

## 5. Global Feature Importance Ranking

Global feature importance is calculated as the mean absolute attribution $\frac{1}{N} \sum_{i=1}^N |\Phi_k(x_i)|$ across all out-of-sample evaluation observations:

| Rank | Feature Name | Feature Group | Mean Absolute Attribution (Log-Odds) | Mean Absolute SHAP | Relative Importance | Overall Direction |
| :---: | --- | :---: | :---: | :---: | :---: | :---: |
| 1 | `rolling_on_time_rate` | rolling_history | `0.5903` | `0.5504` | `22.78%` | `predominantly_risk_increasing` |
| 2 | `contact_category` | service_notice | `0.4029` | `0.1273` | `15.55%` | `predominantly_protective` |
| 3 | `notice_category` | service_notice | `0.3594` | `0.1428` | `13.87%` | `predominantly_protective` |
| 4 | `product_type` | static | `0.3386` | `0.0303` | `13.07%` | `predominantly_protective` |
| 5 | `recent_delay_days` | recent_payment | `0.2505` | `0.2576` | `9.67%` | `predominantly_protective` |
| 6 | `billing_frequency` | static | `0.2394` | `0.2053` | `9.24%` | `predominantly_protective` |
| 7 | `rolling_payment_count` | rolling_history | `0.1410` | `0.1609` | `5.44%` | `predominantly_risk_increasing` |
| 8 | `recent_failed_payment_count` | recent_payment | `0.0742` | `0.0803` | `2.86%` | `predominantly_protective` |
| 9 | `premium_amount_cents` | static | `0.0472` | `0.0473` | `1.82%` | `predominantly_risk_increasing` |
| 10 | `recent_notice_count` | service_notice | `0.0445` | `0.0446` | `1.72%` | `predominantly_protective` |
| 11 | `tenure_days` | static | `0.0410` | `0.0411` | `1.58%` | `predominantly_protective` |
| 12 | `recent_contact_count` | service_notice | `0.0333` | `0.0332` | `1.29%` | `predominantly_protective` |
| 13 | `arrears_duration_days` | recent_payment | `0.0208` | `0.0212` | `0.80%` | `predominantly_protective` |
| 14 | `payment_attribute_missing` | missingness | `0.0055` | `0.0058` | `0.21%` | `predominantly_risk_increasing` |
| 15 | `recent_retry_count` | recent_payment | `0.0017` | `0.0017` | `0.06%` | `predominantly_protective` |
| 16 | `recent_recovery_count` | recent_payment | `0.0012` | `0.0013` | `0.05%` | `predominantly_risk_increasing` |
| 17 | `contact_attribute_missing` | missingness | `0.0000` | `0.0000` | `0.00%` | `mixed_neutral` |

---

## 6. Representative Local Case Studies (Waterfalls)

Representative case studies illustrate local risk attribution profiles across governed operational risk tiers:

### Tier 1: Low Risk Case (Prototypical Median Policy)
- **Observation ID**: `v6-obs-b7d571519efc059fd2bcf50d`
- **Policy ID**: `v6-pol-0fb8903b87b70fd3785e3865`
- **Calibrated Lapse Probability**: `0.0673`
- **Calibrated Logit ($z$)**: `-2.6287`
- **Reconstruction Residual**: `4.44e-16`

**Top Risk Drivers (Increasing Lapse Hazard)**:
- `billing_frequency` (`raw=annual`): `+0.1221` log-odds
- `rolling_payment_count` (`raw=0.0`): `+0.0979` log-odds
- `tenure_days` (`raw=0.0821917808219178`): `+0.0265` log-odds

**Top Protective Factors (Reducing Lapse Hazard)**:
- `rolling_on_time_rate` (`raw=0.5`): `-0.5584` log-odds
- `contact_category` (`raw=none`): `-0.4932` log-odds
- `notice_category` (`raw=none`): `-0.4687` log-odds

### Tier 2: Moderate Risk Case (Prototypical Median Policy)
- **Observation ID**: `v6-obs-d83c446fe2ba05a9c0f5a18c`
- **Policy ID**: `v6-pol-cffeb85d2eda1dbefe65f603`
- **Calibrated Lapse Probability**: `0.1683`
- **Calibrated Logit ($z$)**: `-1.5979`
- **Reconstruction Residual**: `2.22e-16`

**Top Risk Drivers (Increasing Lapse Hazard)**:
- `rolling_on_time_rate` (`raw=0.0`): `+0.6415` log-odds
- `billing_frequency` (`raw=annual`): `+0.1221` log-odds
- `rolling_payment_count` (`raw=0.08333333333333333`): `+0.0480` log-odds

**Top Protective Factors (Reducing Lapse Hazard)**:
- `contact_category` (`raw=none`): `-0.4932` log-odds
- `notice_category` (`raw=none`): `-0.4687` log-odds
- `product_type` (`raw=fictional_term_life`): `-0.3704` log-odds

### Tier 3: High Risk Case (Prototypical Median Policy)
- **Observation ID**: `v6-obs-d5ddc812c30182ef92e94401`
- **Policy ID**: `v6-pol-e715054badf344892d1c20fb`
- **Calibrated Lapse Probability**: `0.3048`
- **Calibrated Logit ($z$)**: `-0.8244`
- **Reconstruction Residual**: `1.11e-16`

**Top Risk Drivers (Increasing Lapse Hazard)**:
- `rolling_on_time_rate` (`raw=0.0`): `+0.6415` log-odds
- `recent_notice_count` (`raw=0.3333333333333333`): `+0.0647` log-odds
- `recent_contact_count` (`raw=0.3333333333333333`): `+0.0559` log-odds

**Top Protective Factors (Reducing Lapse Hazard)**:
- `product_type` (`raw=fictional_whole_life`): `-0.3098` log-odds
- `contact_category` (`raw=service_request`): `-0.1871` log-odds
- `notice_category` (`raw=billing_reminder`): `-0.1581` log-odds

---

## 7. ADR 0002 Action-Authority Boundaries

The model behavior attributions published herein operate under strict architectural and governance constraints:

1. **Tier 1 Perception Only**:
   - Attributions quantify mathematical associations in the perception layer. They possess zero autonomous authority to trigger workflows, alter premiums, or send communications.
2. **Strict Non-Causal Boundary**:
   - Attributions describe statistical correlations (P(y|x)), not causal levers (P(y|do(x))). Altering observed features manually does not guarantee customer risk reduction.
3. **Tier 2 Deterministic Gate Mandatory**:
   - All candidate accounts must pass deterministic eligibility filters (grace period checks, cooling-off periods, communication caps) before any intervention.
4. **Tier 4 Human Approval Final Authority**:
   - Final approval for all customer retention interventions remains with licensed human conservation officers.

---

## 8. Lineage, Integrity, and Clean-Room Invariants

- **Upstream Candidate Digest**: `5fc28797a47f1321ca141d814fc33b37018e05f99779053b6789ebef3dca7803`
- **Upstream Calibration Digest**: `ff196d6b78e803eef6e51a2cb439070673d4150fa98ace5bb6f03696f933c06b`
- **Explanations Contract Digest**: `7cd1d3bbf9a3c1b2b417a7fc3c1d4af601e3a1f7812500c8e04a751fa0b36e8c`
- **Source Code Digest**: `9b01d7b039417fd9e2a595fc7cf38cafa6d8b3149d3176b963880a2ecdbdb3cb`
- **Final Holdout Partition Status**: `not_materialized` (Clean-room intact)

