# Phase 2.08 Probability Calibration and Operational Thresholds Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Contract Version | `1.0.0` |
| Phase | Phase 2 — Baseline ML (Resumed) |
| Backlog Work ID | `P2-08` |
| GitHub Issue | [#96](https://github.com/anilreddy89/Inforsight/issues/96) |
| Governing Predecessors | ADR 0007 through ADR 0013, Phase 2R.16A ([PR #95](https://github.com/anilreddy89/Inforsight/pull/95), `4d7e9da`) |
| Governing Substrate | Generation v6 Bounded Sigmoid Substrate Contract version `6.0.0` |
| Governing Evaluation Pipeline | Generation v6 Evaluation Pipeline Implementation Contract version `6.0.0` |
| Frozen Candidate Model | Logistic Regression ($L_2$, $C=1.0$, `liblinear`, seed `20260817`), selected by R2-15 Manifest `6.0.0` |
| Calibration Partition Role | `calibration` (10% of cohort policies, strictly isolated from candidate `fit`) |
| Evaluation Partition Role | `non_final_evaluation` (10% of cohort policies) and temporal evaluation folds |
| Primary Development Seed | `20280201` |
| Reserved Acceptance Seeds | `20271201..20271220` (spent in R2-16/16A; strictly isolated) |
| Final Release Holdout Status | `not_materialized` |
| Status | In progress under Issue #96 |

---

## 1. Governing Upstream Lineage & Invariant Boundaries

This contract defines the authoritative engineering, statistical, and operational requirements for **Phase 2.08**.

1. **Candidate Model Immutability**: The upstream release candidate Logistic Regression coefficients ($W \in \mathbb{R}^{17}$, $b \in \mathbb{R}$) selected in Phase 2R.15 are frozen. Calibration fits only a scalar probability mapping $g: \hat{f} \to [0, 1]$; base weights are never refitted.
2. **Partition Isolation**: Calibrators must be fitted exclusively on the designated `calibration` role partition of seed `20280201`. The candidate model `fit` partition must not be used for calibration fitting.
3. **Clean-Room Holdout Protection**: The final release holdout remains strictly `not_materialized`, unassigned, and untouched. No threshold or calibrator is selected or verified using final holdout data.

---

## 2. Probability Calibration Specifications

### 2.1 Candidate Calibrator Formulations

Two post-hoc calibrators are evaluated against uncalibrated model scores:

#### A. Platt Scaling (Sigmoid Calibrator) — Governed Primary
Fits a univariate logistic function over raw model logits $\hat{z}_i$:
$$\hat{p}_i = \sigma(A \cdot \hat{z}_i + B) = \frac{1}{1 + \exp(-(A \cdot \hat{z}_i + B))}$$
where scalar parameters $A, B \in \mathbb{R}$ are determined by maximum likelihood (minimizing binary cross-entropy log loss) on the designated `calibration` partition.

- **Monotonicity**: $A > 0$ guarantees strict monotonicity, preserving ROC AUC exactly ($\Delta \le 10^{-6}$).
- **Regularization**: Low parameter degrees of freedom ($\text{df} = 2$) prevents overfitting on moderate cluster-sampled data.

#### B. Isotonic Regression — Governed Comparator
Fits a piecewise-constant, monotonically non-decreasing step function:
$$\min_{m} \sum_{i=1}^{N_{\text{cal}}} \left(y_i - m(\hat{f}_i)\right)^2 \quad \text{subject to } m(\hat{f}_{(1)}) \le m(\hat{f}_{(2)}) \le \dots \le m(\hat{f}_{(N)})$$
solved via the Pairwise Adjacent Violators (PAV) algorithm.

- **Monotonicity**: Weakly monotonic; can introduce tied prediction values along flat steps.

### 2.2 Calibration Evaluation Metrics and Targets

All metrics are evaluated out-of-sample on the `non_final_evaluation` partition:

| Metric | Target / Acceptance Bound |
| --- | ---: |
| **Calibration Slope** | $\beta_1 \in [0.85, 1.15]$ from $\text{logit}(y) = \beta_0 + \beta_1 \text{logit}(\hat{p})$ |
| **Calibration Intercept** | $|\beta_0| \le 0.10$ at $\text{logit}(\hat{p}) = 0$ |
| **Expected Calibration Error (ECE)** | $\le 0.0300$ across 10 quantile bins |
| **Maximum Calibration Error (MCE)** | $\le 0.0800$ across 10 quantile bins |
| **Brier Score ($BS$)** | $\le 0.1250$ |
| **Brier Skill Score ($BSS$)** | $> 0.0000$ relative to prevalence climatology |
| **Brier Murphy Decomposition** | $BS = REL - RES + UNC$, with Reliability $REL \le 0.0050$ |
| **ROC AUC Preservation** | $\|\text{AUC}_{\text{calibrated}} - \text{AUC}_{\text{raw}}\| \le 10^{-6}$ for Platt scaling |
| **Log Loss** | Lower than uncalibrated candidate log loss |

---

## 3. Operational Decision Threshold Framework

### 3.1 Deprecation of 0.50 Classification Threshold
Because the baseline monthly lapse probability is $\sim 5\%\text{--}10\%$, a fixed cutoff $\tau = 0.50$ produces degenerate operational outcomes ($\text{Recall} \approx 0$). Phase 2.08 mandates parameterized operational review capacities.

### 3.2 Review Capacity-Constrained Operating Points
For a monthly active policy population of size $N$, the operational review capacity $K \in (0, 1)$ establishes the threshold cutoff:
$$\tau_K = \text{Quantile}_{1 - K}\left(\{\hat{p}_i\}_{i=1}^N\right)$$

Performance must be reported across six predeclared review capacities:
1. **Top 1%** Review Volume (Executive / Senior Specialist Queue)
2. **Top 2%** Review Volume (Dedicated Specialist Queue)
3. **Top 5%** Review Volume (Standard Retention Outreach)
4. **Top 10%** Review Volume (Multi-Channel Outreach)
5. **Top 15%** Review Volume (Targeted Direct Mail & Digital Alerts)
6. **Top 20%** Review Volume (Broad Digital Campaign)

For each capacity cutoff, the evaluation engine computes:
- **Precision (Positive Predictive Value)**: $\frac{\text{TP}}{\text{TP} + \text{FP}}$
- **Recall (Sensitivity)**: $\frac{\text{TP}}{\text{TP} + \text{FN}}$
- **Enrichment Lift**: $\frac{\text{Precision}}{\text{Base Prevalence}}$
- **Number Needed to Review (NNR)**: $\frac{1}{\text{Precision}}$
- **Net Benefit**: Net benefit under defined cost ratio.

### 3.3 Risk-Stratified Operating Tiers
1. **Tier 1: Low Risk** ($\hat{p} < \tau_{\text{low}}$) $\to$ Standard automated servicing.
2. **Tier 2: Moderate Risk** ($\tau_{\text{low}} \le \hat{p} < \tau_{\text{high}}$) $\to$ Automated digital touchpoint / reminder.
3. **Tier 3: High Risk** ($\hat{p} \ge \tau_{\text{high}}$) $\to$ Specialist conservation intervention.

### 3.4 Decision Curve Analysis (Cost-Benefit Utility)
Operating utility is parameterized by the cost ratio:
$$r = \frac{C_{\text{FP}}}{C_{\text{FN}}}$$
where $C_{\text{FP}}$ is the outreach cost (\$15–\$50) and $C_{\text{FN}}$ is the lost customer lifetime value (\$300–\$1,500).
The Net Benefit curve is evaluated across $\tau \in [0.02, 0.30]$:
$$\text{Net Benefit}(\tau) = \frac{\text{TP}}{N} - \frac{\text{FP}}{N} \left(\frac{\tau}{1 - \tau}\right)$$
The calibrated model must demonstrate positive net benefit superior to both "Intervene on All" and "Intervene on None" across the operational cost spectrum.

### 3.5 Uncertainty Quantification
Intra-policy correlation is accounted for via **1,000 policy-cluster bootstrap replicates**, generating two-sided 95% confidence intervals for all operational metrics.

---

## 4. Evidence Artifacts

Phase 2.08 produces the following authoritative artifacts:

```text
docs/experiments/phase-02-08-probability-calibration-manifest.json
docs/experiments/phase-02-08-probability-calibration-report.md
```

- The **Manifest** records input digests, fitted parameters, calibration metrics, the operational threshold trade-off table with bootstrap CIs, and confirmation that the final holdout status is `not_materialized`.
- The **Report** provides ASCII reliability curves, calibrator comparisons, review capacity trade-off plots, utility curves, and operational boundaries.

---

## 5. Reproduction Commands

```bash
python3 scripts/run_probability_calibration.py --write
python3 scripts/run_probability_calibration.py --check
make probability-calibration-check
```

`--check` must execute in read-only mode and verify bit-for-bit reproducibility of both artifacts.

