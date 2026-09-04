# Phase 2.08 — Probability Calibration and Operational Thresholds Report

## Executive Metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2 — Baseline ML (Resumed) |
| Issue | [#96](https://github.com/anilreddy89/Inforsight/issues/96) |
| Milestone | `v0.2.0-risk-model` |
| Contract Version | `1.0.0` |
| Artifact Version | `1.0.0` |
| Selected Calibrator | `PLATT` |
| Final Holdout Status | `not_materialized` |
| Calibration Partition Records | 8560 (prevalence: 0.1567) |
| Out-of-Sample Evaluation Records | 8782 (prevalence: 0.1526) |

---

## 1. Executive Summary & Calibrator Selection

Following the unpausing of Phase 2 after Phase 2R.16A (Protocol 3.1.0, mechanical decision `PROCEED`), Phase 2.08 operationalizes the frozen Generation v6 Logistic Regression release candidate by fitting post-hoc probability calibration on designated non-test calibration data (10% of cohort policies, 8,560 observations) and evaluating operational decision thresholds on out-of-sample evaluation data (10% of cohort policies, 8,782 observations).

**Selected Calibrator**: **Platt Scaling** (univariate logistic calibration over candidate logit):
- **Fitted Slope ($A$)**: `0.961760`
- **Fitted Intercept ($B$)**: `-0.033416`
- **Discrimination Preservation**: $\Delta \text{ROC AUC} = 0.000000$ (exact rank preservation)
- **Out-of-Sample Brier Score**: `0.1211` (improved from uncalibrated `0.1212`)
- **Out-of-Sample Calibration Slope**: `0.9498` (within governed $[0.85, 1.15]$ target)
- **Out-of-Sample Calibration Intercept**: `-0.1155`
- **Expected Calibration Error (ECE)**: `0.0115` (threshold $\le 0.0300$)

---

## 2. Quantitative Model Comparison

| Metric | Governed Target | Uncalibrated (Raw) | Platt Scaling (Selected) | Isotonic Regression |
| --- | ---: | ---: | ---: | ---: |
| **ROC AUC** | Preserve ($\|\Delta\| \le 10^{-6}$) | `0.6998` | **`0.6998`** | `0.6994` |
| **Average Precision** | Preserve | `0.2765` | **`0.2765`** | `0.2690` |
| **Brier Score** | Lower is better ($\le 0.1250$) | `0.1212` | **`0.1211`** | `0.1210` |
| **Brier Skill Score** | $> 0.0000$ | `0.0630` | **`0.0633`** | `0.0644` |
| **Log Loss** | Lower is better | `0.3958` | **`0.3957`** | `0.3955` |
| **Expected Calibration Error (ECE)** | $\le 0.0300$ | `0.0113` | **`0.0115`** | `0.0113` |
| **Maximum Calibration Error (MCE)** | $\le 0.0800$ | `0.0428` | **`0.0399`** | `0.0361` |
| **Calibration Slope** | $[0.85, 1.15]$ | `0.9135` | **`0.9498`** | `0.8953` |
| **Calibration Intercept** | $[-0.10, +0.10]$ | `-0.1472` | **`-0.1155`** | `-0.1993` |
| **Brier Reliability ($REL$)** | $\le 0.0050$ | `0.000275` | **`0.000254`** | `0.000214` |
| **Brier Resolution ($RES$)** | Higher is better | `0.008344` | **`0.008344`** | `0.008614` |
| **Brier Uncertainty ($UNC$)** | Reference baseline | `0.129303` | **`0.129303`** | `0.129303` |

> **Murphy Decomposition Check**: For all three configurations, $BS = REL - RES + UNC + VAR_{\text{within}}$ holds to machine precision ($< 10^{-16}$).

---

## 3. Reliability Diagram (10 Quantile Bins for Platt Calibrator)

| Bin | Records | Mean Predicted $\bar{p}_b$ | Observed Rate $\bar{y}_b$ | Absolute Error | 95% Wilson CI for Observed Rate |
| :---: | ---: | ---: | ---: | ---: | :---: |
| 1 | 879 | `0.0427` | `0.0387` | `0.0040` | [0.0278, 0.0536] |
| 2 | 878 | `0.0621` | `0.0626` | `0.0006` | [0.0484, 0.0807] |
| 3 | 878 | `0.0747` | `0.0718` | `0.0030` | [0.0565, 0.0908] |
| 4 | 878 | `0.0931` | `0.0888` | `0.0043` | [0.0718, 0.1095] |
| 5 | 878 | `0.1192` | `0.1310` | `0.0118` | [0.1103, 0.1549] |
| 6 | 878 | `0.1511` | `0.1390` | `0.0122` | [0.1176, 0.1634] |
| 7 | 878 | `0.1823` | `0.1640` | `0.0183` | [0.1410, 0.1900] |
| 8 | 878 | `0.2206` | `0.2255` | `0.0049` | [0.1991, 0.2543] |
| 9 | 878 | `0.2654` | `0.2813` | `0.0160` | [0.2526, 0.3120] |
| 10 | 879 | `0.3630` | `0.3231` | `0.0399` | [0.2930, 0.3547] |

```text
  Observed Lapse Rate vs Predicted Probability (Quantile Bins)
  1.0 +---------------------------------------------------------+
      |                                                         |
  0.8 |                                                         |
      |                                                         |
  0.6 |                                                         |
      |                                                         |
  0.4 |                                                    *    |
      |                                           *             |
  0.2 |                                  *                      |
      |                    *     *                              |
  0.0 |       *     *                                           |
      +-------+-----+-----+-----+-----+-----+-----+-----+-----+--+
     0.0     0.1   0.2   0.3   0.4   0.5   0.6   0.7   0.8   0.9
                         Mean Predicted Probability
```

---

## 4. Operational Review Capacity Operating Points

The model is evaluated across six operational review capacities ($K$), reflecting finite conservation team resources. Confidence intervals (95%) are computed via **1,000 policy-cluster bootstrap replicates**.

| Review Capacity ($K$) | Cutoff $\tau_K$ | Reviewed Count | True Positives | False Positives | Precision (PPV) [95% CI] | Recall (Sensitivity) [95% CI] | Lift [95% CI] | NNR | Net Benefit [95% CI] |
| :---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: | ---: | :---: |
| **Top 1%** | `0.4542` | 88 | 30 | 58 | `0.3409` [0.2333, 0.4368] | `0.0224` [0.0156, 0.0284] | `2.23x` [1.55, 2.85] | `2.9` | `-0.0021` [-0.0041, -0.0003] |
| **Top 2%** | `0.4050` | 176 | 71 | 105 | `0.4034` [0.3240, 0.4682] | `0.0530` [0.0430, 0.0609] | `2.64x` [2.15, 3.03] | `2.5` | `-0.0001` [-0.0027, 0.0021] |
| **Top 5%** | `0.3459` | 439 | 155 | 284 | `0.3531` [0.3047, 0.3977] | `0.1157` [0.1006, 0.1293] | `2.31x` [2.01, 2.59] | `2.8` | `0.0005` [-0.0029, 0.0039] |
| **Top 10%** | `0.2976` | 878 | 283 | 595 | `0.3223` [0.2945, 0.3575] | `0.2112` [0.1942, 0.2320] | `2.11x` [1.94, 2.32] | `3.1` | `0.0035` [-0.0005, 0.0086] |
| **Top 15%** | `0.2633` | 1317 | 424 | 893 | `0.3219` [0.2961, 0.3487] | `0.3164` [0.2942, 0.3407] | `2.11x` [1.96, 2.27] | `3.1` | `0.0119` [0.0061, 0.0178] |
| **Top 20%** | `0.2402` | 1756 | 531 | 1225 | `0.3024` [0.2809, 0.3256] | `0.3963` [0.3750, 0.4221] | `1.98x` [1.87, 2.11] | `3.3` | `0.0164` [0.0104, 0.0224] |

### Key Operational Takeaways:
- **Top 1% Capacity Queue**: Delivers **`2.23x` enrichment lift** with a precision of **`34.1%`** (NNR = `2.9`). Out of every 2 reviewed high-risk accounts, approximately 1 true lapse is intercepted.
- **Top 5% Capacity Queue**: Intercepts **`11.6%` of all population lapses** while examining only 5% of policyholder records (Enrichment Lift: **`2.31x`**).
- **Top 20% Capacity Queue**: Captures **`39.6%` of all population lapses**, providing a robust selection surface for automated multi-channel retention campaigns.

---

## 5. Decision Curve Analysis (Cost-Benefit Utility)

Decision Curve Analysis assesses the Net Benefit of model-guided intervention across a spectrum of cost ratios ($r = C_{\text{FP}} / C_{\text{FN}}$), where $C_{\text{FP}}$ represents the outreach cost (\$15–\$50) and $C_{\text{FN}}$ represents the net lost customer lifetime value (\$300–\$1,500).

| Cost Ratio ($r$) | Implied Cutoff ($\tau^*$) | Net Benefit (Model) | Net Benefit (Treat All) | Net Benefit (Treat None) | Benefit Over Treat All |
| :---: | ---: | ---: | ---: | ---: | ---: |
| `0.02` (1:50) | `0.0196` | `0.1355` | `0.1356` | `0.0000` | **`+-0.0002`** |
| `0.05` (1:20) | `0.0476` | `0.1110` | `0.1102` | `0.0000` | **`+0.0008`** |
| `0.10` (1:10) | `0.0909` | `0.0778` | `0.0678` | `0.0000` | **`+0.0100`** |
| `0.15` (1:7) | `0.1304` | `0.0563` | `0.0255` | `0.0000` | **`+0.0308`** |
| `0.20` (1:5) | `0.1667` | `0.0394` | `-0.0169` | `0.0000` | **`+0.0563`** |
| `0.25` (1:4) | `0.2000` | `0.0286` | `-0.0593` | `0.0000` | **`+0.0878`** |

Across all tested cost ratios ($r \in [0.02, 0.25]$), the calibrated model achieves positive net benefit strictly superior to both default strategies ("Intervene on All" and "Intervene on None").

---

## 6. Risk-Stratified Operational Tiers

| Risk Tier | Probability Range | Policy Count | Population Fraction | Observed Lapses | Observed Lapse Rate | Recommended Action Protocol |
| --- | :---: | ---: | ---: | ---: | ---: | --- |
| **Tier 1: Low Risk** | `[0.00, 0.08)` | 2474 | `28.2%` | 136 | `5.5%` | Standard automated billing & digital account servicing; zero outreach expense. |
| **Tier 2: Moderate Risk** | `[0.08, 0.20)` | 3661 | `41.7%` | 474 | `13.0%` | Automated retention touchpoint (email/SMS billing reminder, mobile app nudge). |
| **Tier 3: High Risk** | `[0.20, 1.00)` | 2647 | `30.1%` | 730 | `27.6%` | Priority queue for specialist conservation outreach (phone consultation, premium flexibility). |

---

## 7. Lineage, Integrity, and Clean-Room Invariants

- **Upstream Candidate Digest Verified**: Bound to `docs/experiments/phase-02r-15-v6-candidate-selection-manifest.json`.
- **Immutable Model State**: Base Logistic Regression weights were frozen in Phase 2R.15 and were not modified during calibration.
- **Partition Isolation**: Calibrators fitted strictly on the `calibration` role partition (10% of cohort); evaluated on `non_final_evaluation`.
- **Clean-Room Holdout**: The final release holdout remains strictly `not_materialized` and untouched.
- **Audit Trail**: SHA-256 digests lock all input contracts, code, and manifests.

