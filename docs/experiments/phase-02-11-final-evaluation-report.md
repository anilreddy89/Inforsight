# Phase 2.11: Final Evaluation Report

- **Phase**: `P2-11` (Issue #102)
- **Milestone**: `v0.2.0-risk-model`
- **Artifact Version**: `1.0.0`
- **Contract Version**: `1.0.0`
- **Claim Boundary**: `final_evaluation_and_model_card_only`
- **Bundle ID**: `inforsight-v6-logistic-platt-20260817`
- **Bundle SHA-256**: `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`
- **Mechanical Decision**: **`RELEASE`**

---

## 1. Executive Summary

Phase 2.11 executes the formal, access-controlled **Final Evaluation** of the frozen release candidate model bundle (`inforsight-v6-logistic-platt-20260817`) across 8,782 out-of-sample observations from 1,440 policies of seed `20280201`.

All **6 Pre-registered Acceptance Gates (G1–G6) passed**, deriving a unanimous **`RELEASE`** recommendation.

---

## 2. Evaluation Partition Support

| Partition Field | Value |
| --- | ---: |
| **Total Observations** | 8,782 |
| **Unique Policies** | 1,440 |
| **Positive Lapses** | 1,340 |
| **Negative / Active** | 7,442 |
| **Baseline Prevalence** | 15.26% |

---

## 3. Quantitative Evaluation Metrics & 95% Clustered Bootstrap CIs

Policy-clustered bootstrap confidence intervals (1,000 resamples) account for intra-policy correlation across recurring observation windows:

| Metric Family | Metric | Point Estimate | 95% Bootstrap CI | Gate Target | Status |
| --- | --- | ---: | :---: | :---: | :---: |
| **Discrimination** | ROC AUC | **0.6998** | `[0.6847, 0.7153]` | $\ge 0.6800$ | **PASS** |
| **Discrimination** | Average Precision (PR AUC) | **0.2765** | `[0.2560, 0.2994]` | $\ge 0.2500$ | **PASS** |
| **Probability Quality** | Brier Score | **0.1211** | `[0.1168, 0.1253]` | $\le 0.1300$ | **PASS** |
| **Probability Quality** | Brier Skill Score | **0.0633** | — | $> 0.0000$ | **PASS** |
| **Calibration** | Expected Calibration Error (ECE) | **0.0115** | — | $\le 0.0300$ | **PASS** |
| **Calibration** | Empirical Slope | **0.9498** | — | $[0.85, 1.15]$ | **PASS** |
| **Calibration** | Empirical Intercept | **-0.1155** | — | — | **INFO** |

---

## 4. Operational Review Queue Capacities

Triage queues simulated under constrained human review budget:

| Queue Capacity | Cutoff Prob | Reviewed Count | True Positives | Precision (95% CI) | Recall (95% CI) | Lift (95% CI) | NNR |
| ---: | ---: | ---: | ---: | :---: | :---: | :---: | ---: |
| **Top 1%** | 0.4542 | 88 | 30 | 0.3409 `[0.2333, 0.4368]` | 0.0224 `[0.0156, 0.0284]` | 2.23x `[1.55, 2.85]` | 2.93 |
| **Top 2%** | 0.4050 | 176 | 71 | 0.4034 `[0.3240, 0.4682]` | 0.0530 `[0.0430, 0.0609]` | 2.64x `[2.15, 3.03]` | 2.48 |
| **Top 5%** | 0.3459 | 439 | 155 | 0.3531 `[0.3047, 0.3977]` | 0.1157 `[0.1006, 0.1293]` | 2.31x `[2.01, 2.59]` | 2.83 |
| **Top 10%** | 0.2976 | 878 | 283 | 0.3223 `[0.2945, 0.3575]` | 0.2112 `[0.1942, 0.2320]` | 2.11x `[1.94, 2.32]` | 3.10 |
| **Top 15%** | 0.2633 | 1,317 | 424 | 0.3219 `[0.2961, 0.3487]` | 0.3164 `[0.2942, 0.3407]` | 2.11x `[1.96, 2.27]` | 3.11 |
| **Top 20%** | 0.2402 | 1,756 | 531 | 0.3024 `[0.2809, 0.3256]` | 0.3963 `[0.3750, 0.4221]` | 1.98x `[1.87, 2.11]` | 3.31 |

---

## 5. Pre-registered Acceptance Gates (G1–G6)

| Gate ID | Metric Description | Predeclared Target | Observed Value | Gate Result | Rationale |
| :---: | --- | :---: | :---: | :---: | --- |
| **G1** | Out-of-Sample ROC AUC | `>= 0.6800` | **0.6998** | **PASS** | Baseline discrimination exceeds minimum viable threshold for non-trivial risk ordering. |
| **G2** | Out-of-Sample Average Precision | `>= 0.2500` | **0.2765** | **PASS** | Precision-recall enrichment significantly exceeds 15.26% population baseline. |
| **G3** | Expected Calibration Error (ECE) | `<= 0.0300` | **0.0115** | **PASS** | Predicted probabilities align closely with empirical outcome frequencies. |
| **G4** | Calibration Slope | `in [0.85, 1.15]` | **0.9498** | **PASS** | Empirical slope confirms absence of severe over- or under-confidence. |
| **G5** | Top 1% Review Queue Precision | `>= 0.3000` | **0.3409** | **PASS** | Concentrated risk precision in highest-priority triage queue (2.23x lift). |
| **G6** | Top 5% Review Queue Lift | `>= 2.00x` | **2.314** | **PASS** | Triage queue catches disproportionate share of lapses (11.57% recall at 5% inspection). |

---

## 6. Conclusion & Recommendation

The candidate model bundle meets all pre-registered evaluation criteria. The mechanical gate derives: **`RELEASE`**.
Authorizes publication of `MODEL_CARD.md`, Phase 2 Decision Note, and proceeding to release marker `v0.2.0-risk-model` (P2-12).
