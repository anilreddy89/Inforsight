# Phase 2R.15 — Generation v6 Evaluation Pipeline, Features, Candidates, and Selection

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2R — Modeling Foundation Remediation Gate, Generation v6 Evaluation & Candidate Selection |
| Sequence | R2-15 |
| Change tracker ID | `R2-15` |
| GitHub issue | [#90](https://github.com/anilreddy89/Inforsight/issues/90) |
| Issue title | `[Implementation] R2-15: Freeze Generation v6 evaluation pipeline and release candidate` |
| Branch | `feat/90-r2-15-v6-evaluation-and-candidate` |
| Pull request | [#91](https://github.com/anilreddy89/Inforsight/pull/91) |
| Status | Completed on 2026-09-04, merge commit `8965c72` |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Capability / Remediation |
| Strict predecessor | R2-14D, completed through issue #88 and PR #89, merge commit `89ec94a` |
| Governing decisions | ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, ADR 0012 |
| Governing substrate | Generation v6 Bounded Sigmoid Substrate Contract version `6.0.0` |
| Governing evaluation contract | Generation v6 Evaluation Pipeline Implementation Contract version `6.0.0` |
| Governing candidate selection | Candidate Selection Manifest version `6.0.0` |
| Evaluation seed | `20280201` (primary development and candidate selection seed) |
| Reserved acceptance seeds | `20271201` through `20271220`, inclusive; strictly unmaterialized and untouched |
| Final holdout | Undefined and `not_materialized` |
| Enables | Phase 2R.16 (Replacement Statistical Acceptance Protocol execution) |
| Blocks | Resumed Phase 2 work (P2-08 through P2-12) until statistical acceptance succeeds |
| Last reviewed | 2026-09-04 |

---

## 1. Executive Summary

Phase 2R.15 implements the **Generation v6 Evaluation Pipeline**, feature engineering, diagnostics, and deterministic candidate selection, operationalizing the qualified substrate of Phase 2R.14D (ADR 0012, Substrate Contract `6.0.0`).

Before fresh acceptance testing (Phase 2R.16) can be authorized, Phase 2R.15 establishes a tamper-proof boundary:
1. **Governed Chronological Folds**: Rolling-origin temporal evaluation folds and selection folds partitioned by policy and observation time with strict 90-day embargoes.
2. **Fit-Only Preprocessing**: Statistical standardizers and one-hot encoders fitted strictly on designated training/fit observations.
3. **Point-in-Time Feature Lineage**: Validating that all 17 public feature definitions satisfy $t_{\text{effective}} \le t_{\text{as\_of}}$ and $t_{\text{ingested}} \le t_{\text{as\_of}}$.
4. **Leakage & Protected-Concept Guards**: Screening feature spaces against simulator internals (frailty, oracle records, scenarios, identifiers) and confirming zero leakage.
5. **Candidate Comparison**: Evaluating Logistic Regression baseline vs. XGBoost comparator on identical selection folds.
6. **Deterministic Selection**: Applying frozen selection rules (ROC AUC maximization, Brier score tiebreaker, Logistic tiebreaker) to select exactly one model.
7. **Cryptographic Digest Freeze**: Locking fold memberships, fitted transformer states, candidate model artifacts, and scoring authorizations into SHA-256 digests before Phase 2R.16 acceptance access.

---

## 2. Governed Folds & Structural Support

### 2.1 Chronological Folds Structure

| Fold | Role | Fit Through (as_of) | Evaluation Start | Evaluation End | Purpose |
| --- | --- | --- | --- | --- | --- |
| `fold_1` | acceptance | `2023-03-31T23:59:59Z` | `2023-07-01T00:00:00Z` | `2023-09-30T23:59:59Z` | Rolling temporal evaluation 1 |
| `fold_2` | acceptance | `2023-09-30T23:59:59Z` | `2024-01-01T00:00:00Z` | `2024-03-31T23:59:59Z` | Rolling temporal evaluation 2 |
| `fold_3` | acceptance | `2024-03-31T23:59:59Z` | `2024-07-01T00:00:00Z` | `2024-09-30T23:59:59Z` | Rolling temporal evaluation 3 |
| `selection` | selection | `2024-03-31T23:59:59Z` | `2024-07-01T00:00:00Z` | `2024-12-31T23:59:59Z` | Candidate model selection |

### 2.2 Predeclared Structural Support Invariants

Every fold must pass fail-closed structural support:
- $\ge 500$ eligible uncensored observations.
- $\ge 50$ positive outcomes and $\ge 50$ negative outcomes.
- All four billing frequencies (`monthly`, `quarterly`, `semiannual`, `annual`) represented.
- $0\%$ right-censoring in the evaluation window.

---

## 3. Public Feature Surface & Lineage

The public model input surface consists of 17 features:

1. **Static (4)**: `tenure_days`, `premium_amount_cents`, `product_type`, `billing_frequency`.
2. **Recent Payment (5)**: `recent_delay_days`, `recent_failed_payment_count`, `recent_retry_count`, `recent_recovery_count`, `arrears_duration_days`.
3. **Rolling History (2)**: `rolling_on_time_rate`, `rolling_payment_count`.
4. **Service & Notices (4)**: `recent_notice_count`, `notice_category`, `recent_contact_count`, `contact_category`.
5. **Missingness Indicators (2)**: `payment_attribute_missing`, `contact_attribute_missing`.

---

## 4. Deterministic Candidate Selection Protocol

Two candidate models are trained on the governed fit fold:
1. **Logistic Regression Baseline**: $L_2$ regularization, $C=1.0$, `liblinear` solver, deterministic seed `20260817`.
2. **XGBoost Comparator**: `n_estimators=25`, `max_depth=2`, `learning_rate=0.1`, `min_child_weight=2.0`, `tree_method=exact`, `n_jobs=1`, seed `20260817`.

**Selection Rule**:
- The model with higher ROC AUC on the selection fold is chosen (tolerance $10^{-12}$).
- In case of AUC tie, the model with lower Brier score is chosen.
- If both AUC and Brier score tie, Logistic Regression is chosen by default.

---

## 5. Clean-Room and Invariant Protections

- **Acceptance Isolation**: Acceptance fold labels and outcomes are NOT accessed, scored, or predicted during candidate selection.
- **Reserved Acceptance Seeds**: Seeds `20271201..20271220` remain strictly unmaterialized and untouched.
- **Final Holdout**: Unmaterialized.
- **Audit Lineage**: All historical artifacts (v1 through v5, ADR 0001 through ADR 0012, Phase 2R.14D) remain immutable.
