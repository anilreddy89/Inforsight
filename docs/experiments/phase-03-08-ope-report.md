# Phase 3.08 — Offline Policy Evaluation (OPE) Report

## Executive Summary

This report documents the offline policy evaluation (OPE) of the **Inforsight Decision Engine** against four competing triage strategies on a simulated out-of-sample cohort of **3,600 policies** (evaluation seed `20280201`). All evaluations condition strictly on pre-cutoff information ($X_i \in \mathcal{F}_{t_0}$) with **zero future leakage** and enforce specialist capacity ($K = 50.0h$) and financial budget caps ($B = \$5,000.00$).

### Key Statistical & Business Findings

- **Net Preserved Annual Premium**: The Decision Engine preserves **\$13,764.43** (95% CI: [\$11,938.79, \$15,453.64]) in net annual premium after subtracting all direct caseworker and intervention expenses (\$4,707.50).
- **Return on Conservation Spend (ROCS)**: **2.92x** (95% CI: [2.28x, 3.77x])—generating \$2.92 in net preserved premium for every \$1.00 spent.
- **Lapse Rate Reduction**: Prevents an expected **11.7 policy lapses** (2.86% relative reduction across the portfolio).

### Pairwise Superiority Contrasts (vs. Competitor Policies)

| Competitor Baseline | Δ Net Preserved Value (95% CI) | Superiority p-value | Gate Status |
| :--- | :---: | :---: | :---: |
| **Naive ML Risk Ranking** | +\$14,494.00 [\$12,640.48, \$16,451.32] | `0.0000` | PASS (p < 0.01) |
| **Carrier Grace Period Heuristic** | +\$6,374.47 [\$4,710.22, \$8,039.80] | `0.0000` | PASS (p < 0.01) |
| **Random Outreach Baseline** | +\$8,907.44 [\$7,195.49, \$10,645.07] | `0.0000` | PASS (p < 0.01) |
| **Non-Intervention Control** | +\$13,779.86 [\$11,938.79, \$15,453.64] | `0.0000` | PASS (p < 0.01) |

## Comparative Policy Scorecard

| Policy | Lapses Prevented | Relative Lift | Spend ($) | Net Preserved ($) (95% CI) | CPCP ($) | ROCS (95% CI) | Spec. Hours |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Decision Engine (Inforsight)** | 11.7 | 2.9% | \$4,707.50 | \$13,764.43 [\$11,938.79, \$15,453.64] | \$403.70 | 2.92x [2.28x, 3.77x] | 50.0h |
| **Naive ML Risk Triage** | 10.3 | 2.5% | \$5,000.00 | \$-738.74 [\$-1,823.57, \$208.95] | \$486.37 | -0.15x [-0.31x, 0.05x] | 50.0h |
| **Carrier Grace Heuristic** | 16.0 | 3.9% | \$5,000.00 | \$7,427.87 [\$6,161.19, \$8,862.71] | \$312.81 | 1.49x [1.11x, 2.03x] | 50.0h |
| **Random Outreach** | 14.6 | 3.6% | \$5,000.00 | \$4,844.59 [\$3,765.81, \$5,921.66] | \$341.32 | 0.97x [0.68x, 1.33x] | 50.0h |
| **Non-Intervention Control** | 0.0 | 0.0% | \$0.00 | \$0.00 [\$0.00, \$0.00] | \$0.00 | 0.00x [0.00x, 0.00x] | 0.0h |

## Intervention Mix Allocation

| Policy | Specialist Outreach | Grace Consultation | Payment Fix | Courtesy Reminder | Abstain |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Decision Engine** | 50 | 0 | 583 | 0 | 2967 |
| **Naive ML** | 50 | 0 | 700 | 0 | 2850 |
| **Carrier Heuristic** | 50 | 0 | 700 | 0 | 2850 |
| **Random** | 36 | 28 | 654 | 650 | 2232 |
| **Control** | 0 | 0 | 0 | 0 | 3600 |

## Pre-Registered Acceptance Invariants

| Invariant Check | Target Criterion | Empirical Status |
| :--- | :--- | :---: |
| **Substrate Hazard Bound** | $\lambda_{\text{total}}(t) \le 0.1500 < 0.2000$ | PASS |
| **Zero Future Leakage** | Pre-cutoff conditioning ($X_i \in \mathcal{F}_{t_0}$) | PASS |
| **Superiority over Naive ML** | $\text{NPV}_{\text{engine}} > \text{NPV}_{\text{naive}}$ ($p < 0.01$) | PASS |
| **Superiority over Heuristic** | $\text{NPV}_{\text{engine}} > \text{NPV}_{\text{heuristic}}$ ($p < 0.01$) | PASS |
| **Specialist Capacity Adherence** | Specialist hours $\le 50.0h$ (0% overflow) | PASS |
| **Bootstrap Stability** | 1,000 cluster resamples with well-behaved CIs | PASS |

## Cryptographic Provenance

- **Manifest SHA-256 Digest**: `b77a5513fd97551debaca710eb1ed7c5fc7e49ff7187a1ff6fac5a97160f698c`
- **Timestamp (UTC)**: `2026-09-06T03:36:42.716261+00:00`
- **Random Seed**: `20280201`
- **Bootstrap Samples**: `1000`

