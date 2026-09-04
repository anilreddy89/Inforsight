# Phase 2R.16 Generation v6 Statistical Acceptance Protocol Report

Issue: #92
Protocol Version: `3.0.0`
Substrate Contract: `6.0.0`
Selected Candidate: `logistic` (Logistic Regression)

## 1. Executive Summary & Mechanical Decision

Mechanical Decision: **`REDESIGN`**

| Summary Metric | Governed Target | Observed Value | Status |
| --- | --- | ---: | :---: |
| Across-seed Median Candidate ROC AUC | $\ge 0.6800$ | `0.7031` | PASS |
| Seed Consistency Pass Count | $\ge 16 / 20$ (AUC $\ge 0.65$) | `20 / 20` | PASS |
| Signal-Null AUC Improvement Pass Count | $\ge 16 / 20$ (lift $\ge 0.10$) | `20 / 20` | PASS |
| Median Average Precision Lift | $\ge 0.1000$ | `0.1344` | PASS |
| Median Brier Skill Score | $> 0.0000$ | `0.0658` | PASS |
| Median Calibration Slope | $[0.75, 1.25]$ | `0.9086` | PASS |
| Median Absolute Calibration Intercept | $\le 0.2000$ | `0.1726` | PASS |
| All-Designed-Signal Ablation AUC Drop | $\ge 0.1000$ | `0.2005` | PASS |
| Temporal Fold Spread Pass Count | $\ge 16 / 20$ (spread $\le 0.10$) | `20 / 20` | PASS |
| Median Worst-Fold AUC | $\ge 0.6200$ | `0.6709` | PASS |
| Pooled Seed-Balanced AUC 95% CI Lower Bound | $> 0.6000$ | `0.6012` | PASS |

---

## 2. Predeclared Acceptance Rules Evaluation

| Rule ID | Family | Threshold | Observed | Status | Classification |
| --- | --- | --- | ---: | :---: | :---: |
| `READINESS-IMMUTABLE-UPSTREAM` | `lineage` | `[]` | `[]` | **PASS** | `stop` |
| `READINESS-SEED-DOMAINS` | `lineage` | `True` | `{'reserved': 20, 'spent_count': 80}` | **PASS** | `stop` |
| `READINESS-FINAL-HOLDOUT` | `holdout` | `not_materialized` | `not_materialized` | **PASS** | `stop` |
| `READINESS-SELECTED-CANDIDATE` | `model` | `True` | `{'auc_tolerance': '0.000000000001', 'authorization_sha256': '572238427bf7716266925805a40309df86485ba56646a0073ca22d6bf9d38303', 'brier_tolerance': '0.000000000001', 'reason': 'higher_roc_auc', 'selected_candidate': 'logistic', 'selected_model_sha256': '5806fca59bd32033a94fe2d875caec676d4cd68ddfc08198e6fccc931da1b446'}` | **PASS** | `stop` |
| `READINESS-CONTRACT-AUTHORITY` | `lineage` | `[]` | `[]` | **PASS** | `stop` |
| `READINESS-INVENTORY` | `inventory` | `120` | `120` | **PASS** | `redesign` |
| `CTRL-NULL-MEDIAN-AUC` | `controls` | `[0.45, 0.55]` | `0.5123` | **PASS** | `redesign` |
| `CTRL-NULL-INTERVAL-COVERAGE` | `controls` | `18` | `16` | **FAIL** | `redesign` |
| `CTRL-SHUFFLE-MEDIAN-AUC` | `controls` | `[0.47, 0.53]` | `0.5029` | **PASS** | `redesign` |
| `CTRL-SHUFFLE-INTERVAL-COVERAGE` | `controls` | `18` | `17` | **FAIL** | `redesign` |
| `SIGNAL-MEDIAN-AUC` | `recovery` | `0.68` | `0.7031` | **PASS** | `redesign` |
| `SIGNAL-SEED-CONSISTENCY` | `recovery` | `16` | `20` | **PASS** | `redesign` |
| `SIGNAL-MATCHED-NULL-LIFT` | `recovery` | `16` | `20` | **PASS** | `redesign` |
| `SIGNAL-MEDIAN-AP-LIFT` | `recovery` | `0.1` | `0.1344` | **PASS** | `redesign` |
| `SIGNAL-MEDIAN-BRIER-SKILL` | `recovery` | `0.0` | `0.0658` | **PASS** | `redesign` |
| `ORACLE-OBSERVABLE-CEILING` | `oracle` | `0.02` | `0.0067` | **PASS** | `redesign` |
| `ORACLE-CONDITIONAL-ORDERING` | `oracle` | `1e-12` | `0.004482` | **FAIL** | `redesign` |
| `CALIBRATION-SLOPE` | `calibration` | `[0.75, 1.25]` | `0.9086` | **PASS** | `redesign` |
| `CALIBRATION-INTERCEPT` | `calibration` | `0.2` | `0.1726` | **PASS** | `redesign` |
| `CALIBRATION-BRIER-SKILL-COUNT` | `calibration` | `16` | `20` | **PASS** | `redesign` |
| `UNCERTAINTY-POOLED-AUC-LB` | `uncertainty` | `0.6` | `0.6012` | **PASS** | `redesign` |
| `LEARNING-AUC-MONOTONICITY` | `learning` | `0.02` | `-0.0027` | **PASS** | `redesign` |
| `LEARNING-VARIANCE-CONTRACTION` | `learning` | `0.2` | `0.0136` | **FAIL** | `redesign` |
| `LEARNING-BRIER-MONOTONICITY` | `learning` | `0.01` | `-0.0015` | **PASS** | `redesign` |
| `ABLATION-ALL-SIGNAL-DROP` | `ablation` | `0.1` | `0.2005` | **PASS** | `redesign` |
| `ABLATION-STRONGEST-DRIVER-DROP` | `ablation` | `15` | `60` | **PASS** | `redesign` |
| `ABLATION-DESIGNED-ZERO-CONTROL` | `ablation` | `0.02` | `0.0003` | **PASS** | `redesign` |
| `TEMPORAL-FOLD-SPREAD` | `temporal` | `16` | `20` | **PASS** | `redesign` |
| `TEMPORAL-WORST-FOLD-FLOOR` | `temporal` | `0.62` | `0.6709` | **PASS** | `redesign` |
| `TEMPORAL-BILLING-REPRESENTATION` | `temporal` | `True` | `True` | **PASS** | `redesign` |

---

## 3. Per-Seed Replications Summary

| Seed | Signal Median AUC | Matched Null AUC | Lift | Brier Skill | AP Lift | Fold Spread | Worst Fold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `20271201` | `0.6833` | `0.5047` | `0.1587` | `0.0488` | `0.1193` | `0.0507` | `0.6607` |
| `20271202` | `0.7027` | `0.5132` | `0.1882` | `0.0586` | `0.1297` | `0.0632` | `0.6708` |
| `20271203` | `0.6956` | `0.4769` | `0.2307` | `0.0516` | `0.1103` | `0.0285` | `0.6799` |
| `20271204` | `0.6987` | `0.5308` | `0.1679` | `0.0710` | `0.1408` | `0.0877` | `0.6645` |
| `20271205` | `0.7035` | `0.5166` | `0.1623` | `0.0640` | `0.1308` | `0.0545` | `0.6541` |
| `20271206` | `0.7132` | `0.4810` | `0.2175` | `0.0788` | `0.1403` | `0.0487` | `0.6985` |
| `20271207` | `0.7059` | `0.5080` | `0.1979` | `0.0736` | `0.1302` | `0.0411` | `0.6760` |
| `20271208` | `0.6788` | `0.5097` | `0.1742` | `0.0374` | `0.1011` | `0.0910` | `0.6517` |
| `20271209` | `0.6769` | `0.5496` | `0.1647` | `0.0378` | `0.1142` | `0.0716` | `0.6696` |
| `20271210` | `0.7172` | `0.4836` | `0.2518` | `0.0966` | `0.1654` | `0.0563` | `0.6994` |
| `20271211` | `0.7067` | `0.5127` | `0.1940` | `0.0730` | `0.1447` | `0.0565` | `0.6756` |
| `20271212` | `0.7042` | `0.5250` | `0.1648` | `0.0569` | `0.1224` | `0.0424` | `0.6710` |
| `20271213` | `0.7227` | `0.5274` | `0.2265` | `0.0897` | `0.1575` | `0.0833` | `0.6705` |
| `20271214` | `0.6941` | `0.5261` | `0.1829` | `0.0671` | `0.1398` | `0.0598` | `0.6904` |
| `20271215` | `0.7131` | `0.4999` | `0.2132` | `0.0852` | `0.1804` | `0.0084` | `0.7092` |
| `20271216` | `0.7151` | `0.4935` | `0.2447` | `0.0787` | `0.1507` | `0.0782` | `0.6696` |
| `20271217` | `0.6931` | `0.4719` | `0.2211` | `0.0542` | `0.1206` | `0.0334` | `0.6776` |
| `20271218` | `0.6982` | `0.5119` | `0.1852` | `0.0644` | `0.1381` | `0.0766` | `0.6587` |
| `20271219` | `0.7094` | `0.5157` | `0.1937` | `0.0687` | `0.1489` | `0.0626` | `0.6739` |
| `20271220` | `0.7006` | `0.5219` | `0.2217` | `0.0645` | `0.1273` | `0.0969` | `0.6467` |

---

## 4. Invariant and Clean-Room Protections

- **Final Holdout Status**: `not_materialized`.
- **Row-Level Intermediates**: No raw observations, individual predictions, or oracle sidecars are committed.
- **Historical Immutability**: All artifacts from v1 through v5 remain bitwise unchanged.
