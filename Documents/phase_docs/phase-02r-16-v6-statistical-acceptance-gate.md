# Phase 2R.16 — Generation v6 Statistical Acceptance Gate

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2R — Modeling Foundation Remediation Gate, Generation v6 Statistical Acceptance |
| Sequence | R2-16 |
| Change tracker ID | `R2-16` |
| GitHub issue | [#92](https://github.com/anilreddy89/Inforsight/issues/92) |
| Issue title | `[Implementation] R2-16: Execute Generation v6 statistical acceptance protocol` |
| Branch | `feat/92-r2-16-v6-statistical-acceptance` |
| Pull request | TBD |
| Status | Implemented on branch feat/92-r2-16-v6-statistical-acceptance; mechanical decision: redesign |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Governed experiment and mechanical decision gate |
| Strict predecessor | R2-15, completed through issue #90 and PR #91, merge commit `8965c72` |
| Governing decisions | ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, ADR 0012 |
| Governing substrate | Generation v6 Bounded Sigmoid Substrate Contract version `6.0.0` |
| Governing evaluation contract | Generation v6 Evaluation Pipeline Implementation Contract version `6.0.0` |
| Frozen selected candidate | Logistic Regression ($L_2$ regularization, $C=1.0$, `liblinear`, seed `20260817`), selected by R2-15 Manifest version `6.0.0` |
| Governing acceptance protocol | Protocol `3.0.0` (from `docs/modeling/phase-02r-13-v4-statistical-acceptance-protocol.md`, adapted for v6 bounded sigmoid substrate) |
| Development qualification seeds | `20280201` through `20280220`, inclusive (spent during R2-14D qualification and R2-15 evaluation) |
| Reserved acceptance seeds | `20271201` through `20271220`, inclusive (strictly unmaterialized and untouched prior to R2-16 readiness pass) |
| Final holdout | Strictly undefined and `not_materialized` |
| Enables | Phase 2 Resumed Baseline ML (P2-08 Probability Calibration and Operational Thresholds, followed by P2-09 Model-behavior Explanations) if and only if merged decision is `proceed` |
| Blocks | Resumed Phase 2 work (P2-08 through P2-12) until statistical acceptance merges with mechanical decision `proceed` |
| Last reviewed | 2026-09-04 |

---

## 1. Objective and Executive Summary

Phase 2R.16 executes the complete, frozen **Generation v6 Statistical Acceptance Protocol** across all 20 reserved acceptance seed pairs (`20271201..20271220`) and three rolling-origin temporal acceptance folds (`fold_1`, `fold_2`, `fold_3`).

The experiment subjects the frozen release candidate—**Logistic Regression** (selected in Phase 2R.15 over XGBoost under frozen selection rules)—to rigorous statistical scrutiny without discretionary retries, moving thresholds, or post-hoc seed selection.

### Core Execution Principles:
1. **Readiness Before Results**: Enforce fail-closed verification of all upstream cryptographic digests, data contracts, fold structural support, lineage, and clean-room isolation before generating or scoring acceptance data.
2. **Untouched Acceptance Domain**: Transition seeds `20271201..20271220` from reserved/unmaterialized status into execution only through authorized runners.
3. **Fail-Closed Mechanical Decision**: Derive exactly one decision (`proceed`, `redesign`, or `stop`) using strict precedence (`stop` > `redesign` > `proceed`).
4. **Resumption Gate**: Only a pull request merged to `main` with a mechanical `proceed` decision authorizes resuming paused Phase 2 work (P2-08 Probability Calibration).
5. **Clean-Room Integrity**: The final release holdout remains strictly `not_materialized`.

Phase 2R.16 tests whether the Generation v6 bounded sigmoid hazard link architecture and feature extraction pipeline recover the designed data-generating mechanism under non-trivial temporal and behavioral stress. It does **not** make claims of prospective real-world performance, actuarial equivalence, causality, fairness, or production readiness.

---

## 2. Governed Upstream Lineage & Invariant Boundaries

### 2.1 Frozen Upstream Contracts & Evidence
- **ADR 0012**: Authorizes the bounded sigmoid hazard link $\lambda(t) = \lambda_{\max}\sigma(z)$, mathematically guaranteeing maximum monthly hazard $\le 0.1500 < 0.2000$.
- **Generation v6 Substrate Contract `6.0.0`**: Defines discrete competing hazards (lapse ceiling 0.10, surrender ceiling 0.05), centered linear predictors with $6.0\times$ dynamic range scaling, and 32-node Gauss-Hermite quadrature observable oracle.
- **Generation v6 Evaluation Pipeline Implementation Contract `6.0.0`**: Establishes 3 rolling-origin temporal acceptance folds, strict 90-day embargoes, fit-only preprocessing, 17 point-in-time features with zero leakage, and cryptographic scoring authorizations.
- **Candidate Selection Manifest `6.0.0`**: Formally selected Logistic Regression as the single release candidate (ROC AUC: 0.7057 vs XGBoost: 0.6801, Brier score: 0.1287 vs 0.1354).
- **Protocol `3.0.0`**: Predeclares all acceptance rule families, thresholds, tolerances, bootstrap methods, and decision precedence.

### 2.2 Seed Domain Disjointness
- **Spent Historical Seeds**: `20261001..20261020` (v3), `20271101..20271120` (v4), `20280101..20280120` (v5 diagnostics).
- **Spent Development Seeds**: `20280201..20280220` (v6 substrate qualification in R2-14D, evaluation and candidate selection in R2-15).
- **Governed Acceptance Seeds**: `20271201..20271220` (20 signal seeds and 20 matched-null seeds).
- **Final Release Holdout**: Undefined, unassigned, and strictly `not_materialized`.

### 2.3 Acceptance Folds Structure
Every acceptance fold maintains a strict 90-day post-cutoff embargo and full class and billing frequency support:

| Fold | Role | Fit Cutoff (`as_of`) | Evaluation Start | Evaluation End |
| --- | --- | --- | --- | --- |
| `fold_1` | acceptance | `2023-03-31T23:59:59Z` | `2023-07-01T00:00:00Z` | `2023-09-30T23:59:59Z` |
| `fold_2` | acceptance | `2023-09-30T23:59:59Z` | `2024-01-01T00:00:00Z` | `2024-03-31T23:59:59Z` |
| `fold_3` | acceptance | `2024-03-31T23:59:59Z` | `2024-07-01T00:00:00Z` | `2024-09-30T23:59:59Z` |

Each fold must satisfy:
- $\ge 500$ eligible uncensored observations.
- $\ge 50$ positive outcomes and $\ge 50$ negative outcomes.
- All four billing frequencies (`monthly`, `quarterly`, `semiannual`, `annual`) represented.
- $0\%$ right-censoring in the evaluation window.

---

## 3. Predeclared Acceptance Rule Families & Thresholds

Execution evaluates 10 mandatory rule families across all 20 acceptance seeds:

### 3.1 Readiness Before Results
Before generating or scoring acceptance data, the runner verifies:
- SHA-256 match for Substrate Contract `6.0.0`, Evaluation Contract `6.0.0`, Candidate Manifest `6.0.0`, Feature Dictionary `6.0.0`, and Coefficient Registry `3.0.0`.
- All 20 signal/null seed pairs accounted for without replacement or omission.
- Strict cutoff chronology, 90-day embargoes, zero policy overlap across folds.
- Event lineage: $t_{\text{effective}} \le t_{\text{as\_of}}$ and $t_{\text{ingested}} \le t_{\text{as\_of}}$ for all features.
- Fail-closed structural support in all 3 folds across all 20 seeds.
- Clean-room invariants: zero simulator-internal leakage, oracle sidecars strictly isolated, and final holdout `not_materialized`.

### 3.2 Null-Signal & Label-Shuffle Placebo Controls
- **Matched Null Control**: Evaluate model on matched null corpus (`signal_scale = 0` with identical calendar, exposure, and noise draws). Median null AUC must be in $[0.45, 0.55]$, and $\ge 18/20$ null seed intervals must cover $0.50$.
- **Policy-Level Label Shuffle**: Permute outcome vectors grouped by policy. Candidate median shuffled AUC must be in $[0.47, 0.53]$, with $\ge 18/20$ shuffled intervals covering $0.50$.

### 3.3 Signal Recovery & Discrimination
- **Candidate Discrimination**: Across-seed median ROC AUC $\ge 0.68$.
- **Seed Consistency**: At least 16 of 20 seeds must have median-fold candidate AUC $\ge 0.65$.
- **Matched-Null Lift**: At least 16 of 20 seeds must demonstrate signal-minus-null AUC improvement $\ge 0.10$.
- **Average Precision Lift**: Across-seed median AP lift $\ge 0.10$ over fold event prevalence.
- **Brier Skill Score**: Across-seed median Brier skill score $> 0.00$ relative to prevalence baseline.

### 3.4 Oracle Ordering & Supernatural Guard
- Joined only inside purpose-bound authorization boundary:
  $$\text{AUC}(\text{candidate}) \le \text{AUC}(\text{oracle\_observable}) + 0.02$$
  $$\text{AUC}(\text{oracle\_observable}) \le \text{AUC}(\text{oracle\_conditional})$$
- Prevents candidate model from exhibiting impossible ("supernatural") predictive power exceeding the theoretical ceiling of observable information.

### 3.5 Calibration Sanity (Uncalibrated)
- Median calibration slope must be in $[0.75, 1.25]$.
- Absolute median calibration intercept must be $\le 0.20$.
- At least 16 of 20 seeds must have positive Brier skill score.
- *Note*: No calibration mapping (e.g. Platt scaling, isotonic regression) or operational decision threshold is fit in this phase.

### 3.6 Policy-Cluster Resampling & Uncertainty
- Compute 1,000 deterministic policy-cluster bootstrap replicates per seed/fold (all recurring observations for a sampled policy move together).
- Pooled seed-balanced AUC (each seed weighted equally at $1/20$).
- 95% bootstrap confidence interval lower bound for pooled seed-balanced AUC must exceed $0.60$.

### 3.7 Nested Learning Curves
- Refit model on nested policy subsets: 25%, 50%, 75%, and 100% of fit data.
- 100% median AUC must be no more than $0.02$ below 25% subset AUC.
- 100% median AUC interval width must be $\ge 20\%$ narrower than 25% subset interval.
- 100% median Brier score must be no more than $0.01$ worse than 25% subset.

### 3.8 Feature Driver Group Ablations
Zero out driver groups in standardized feature space without refitting encoders:
- **All-Designed-Signal Ablation**: Zeroing `static`, `recent_payment`, `rolling_history`, and `service_notice` must cause median AUC to drop by $\ge 0.10$.
- **Strongest Driver Ablation**: Zeroing `recent_payment` must cause AUC degradation or Brier score worsening in $\ge 15/20$ seeds.
- **Designed-Zero Negative Control**: Zeroing `missingness` must show negligible impact without assigning causal interpretations.

### 3.9 Robustness Scenarios
Evaluate paired intervention scenarios:
- **Default Missingness / Notification Delay**: Median AUC drop $\le 0.03$; positive Brier skill in $\ge 16/20$ seeds.
- **Doubled Missingness**: Median AUC drop $\le 0.07$; zero preprocessing/schema failure.
- **Unknown-Category Arrival**: All unseen categories mapped to frozen unknown column; median AUC drop $\le 0.05$; matrix width invariant.
- **Moderate Behavioral Drift**: Median AUC drop $\le 0.05$; positive Brier skill in $\ge 15/20$ seeds.
- **Stress Drift**: Executes without runtime crash or data leakage (reported for sensitivity).

### 3.10 Temporal Stability Across Folds
- Spread: Max-minus-min fold AUC $\le 0.10$ in at least 16 of 20 seeds.
- Worst-Fold Floor: Across-seed median worst-fold AUC $\ge 0.62$.
- All folds maintain non-zero representation of all 4 billing frequencies.

---

## 4. Mechanical Decision Precedence

Every acceptance rule emits a structured machine-readable result. The final decision is calculated automatically:

```text
1. Any failed rule classified as STOP      ==> STOP
2. Otherwise, any failed rule (REDESIGN)   ==> REDESIGN
3. Otherwise, 100% of rules PASSED        ==> PROCEED
```

- **STOP Trigger**: Data leakage, oracle leakage into feature matrix, scoring authorization bypass, stream mismatch between signal/null pairs, or holdout exposure. Requires investigative halt and audit.
- **REDESIGN Trigger**: Any statistical threshold miss, missing evaluation units, or incomplete rule evaluations. Requires formal redesign under a new backlog item.
- **PROCEED Trigger**: Every rule passed with mathematical and statistical certainty. Unlocks Phase 2 resumption (P2-08 Probability Calibration).

No manual overrides, threshold softening, seed cherry-picking, or post-hoc exclusions are permitted.

---

## 5. Artifacts and Implementation Surface

### 5.1 Artifacts to Produce
```text
docs/modeling/phase-02r-16-v6-statistical-acceptance-execution-contract.md
docs/experiments/phase-02r-16-v6-statistical-acceptance-manifest.json
docs/experiments/phase-02r-16-v6-statistical-acceptance-report.md
docs/experiments/phase-02r-16-v6-statistical-acceptance-decision.md
simulator/src/inforsight_simulator/v6_acceptance.py
simulator/tests/test_v6_acceptance.py
scripts/run_v6_statistical_acceptance.py
```

### 5.2 Repository Integration
- Add CLI runner `scripts/run_v6_statistical_acceptance.py` supporting `--readiness-check`, `--write`, and `--check`.
- Add `v6-acceptance-check` to `Makefile` and wire into `make check` and hosted CI.
- Verify byte-for-byte reproducibility across two clean builds.
- Ensure all historical artifacts (v1 through v5, ADR 0001 through ADR 0012, Phase 2R.14D, Phase 2R.15) remain bitwise identical.

---

## 6. Copy-ready GitHub Issue Content

Use `.github/ISSUE_TEMPLATE/implementation.yml` with the following content.

### Work metadata
```text
Backlog work ID: R2-16
Classification: Governed experiment and mechanical decision gate
Priority: Release blocking
Milestone: v0.2.0-risk-model
```

### Title
```text
[Implementation] R2-16: Execute Generation v6 statistical acceptance protocol
```

### Outcome
```text
Execute the complete frozen 20-seed, three-fold Generation v6 statistical acceptance protocol against reserved acceptance seeds 20271201..20271220 after fail-closed readiness verification. Evaluate all 10 predeclared rule families (readiness, matched-null controls, label shuffles, signal recovery, oracle ordering, calibration sanity, 1,000-replicate policy-cluster uncertainty, nested learning curves, driver ablations, robustness scenarios, and temporal stability) using the frozen Logistic Regression release candidate. Publish deterministic manifest, report, and decision artifacts with exactly one mechanically derived decision: proceed, redesign, or stop. Only a merged proceed resumes Phase 2 work (P2-08); the final release holdout remains strictly not_materialized.
```

### Context
```text
Phase 2R.14C (ADR 0012) resolved the Proportional Hazards Trilemma by establishing the Bounded Sigmoid Substrate Contract 6.0.0, and Phase 2R.14D qualified the v6 engine across 120 evaluation units (all 9 gates passed, median AUC 0.7086, AP lift +0.1398, max hazard 0.14999). Phase 2R.15 (Issue #90, PR #91, commit 8965c72) established the governed chronological folds (fold_1..fold_3, selection), fit-only preprocessing, 17-feature point-in-time extraction with zero leakage, and deterministically selected Logistic Regression over XGBoost (ROC AUC: 0.7057 vs 0.6801, Brier: 0.1287 vs 0.1354), freezing all states and authorizations into cryptographic digests.

Phase 2R.16 is the final remediation gate in Phase 2R. It executes Protocol 3.0.0 against the reserved, previously untouched acceptance seeds 20271201..20271220 to determine whether the Generation v6 modeling foundation earns statistical acceptance.
```

### In scope and out of scope
```text
In scope:
- Publish executable R2-16 execution contract binding Substrate 6.0.0, Evaluation Contract 6.0.0, Candidate Manifest 6.0.0, and Protocol 3.0.0 digests.
- Enforce fail-closed readiness-before-results across all 20 seed pairs, 3 folds, lineage, and structural support.
- Execute complete 20-seed acceptance inventory for frozen Logistic Regression candidate and controls.
- Compute ROC AUC, AP lift, Brier skill, uncalibrated calibration slope/intercept, 1,000-replicate policy-cluster bootstrap CIs, and pooled seed-balanced AUC.
- Execute matched-null controls, policy-level label shuffles, 32-node Gauss-Hermite oracle ordering checks, nested learning (25%, 50%, 75%, 100%), driver ablations, paired robustness scenarios, and 3-fold temporal stability checks.
- Produce deterministic manifest, markdown report, and decision note with automated mechanical precedence (stop > redesign > proceed).
- Add scripts/run_v6_statistical_acceptance.py, simulator/src/inforsight_simulator/v6_acceptance.py, unit/mutation tests, and Makefile/CI integration.

Out of scope:
- Touching, generating, or materializing the final release holdout.
- Modifying any seed, fold, feature, candidate specification, coefficient, threshold, tolerance, or rule in response to observed results.
- Hyperparameter tuning, candidate reselection, or post-hoc model tweaks.
- Fitting probability calibration models or operational decision thresholds (deferred to P2-08).
- Publishing SHAP or model explanation artifacts (deferred to P2-09).
- Committing row-level raw observations, feature matrices, predictions, or oracle sidecars.
- Modifying any historical evidence from v1 through v5, ADR 0001 through ADR 0012, or Phase 2R.14D / 2R.15.
```

### Claim, limitation, contract, and artifact impact
```text
Allowed while open:
- Running readiness verification and executing the frozen R2-16 runner against authorized acceptance seeds 20271201..20271220.

Blocked while open:
- Resuming P2-08 (probability calibration) or P2-09 (model interpretations).
- Materializing or accessing the final release holdout.
- Making real-world performance, actuarial, causal, fairness, or release claims.

Limitations affected:
- LIM-002-001 (billing-frequency confounding), LIM-002-002 (post-cutoff leakage), and LIM-002-004 (synthetic signal recovery) can receive bounded closure evidence only upon a merged proceed decision.
- LIM-002-003 (final holdout integrity) remains open until a dedicated final holdout gate.

Downstream work resumed at closure:
- If proceed: Phase 2R closes; P2-08 is authorized to begin on main.
- If redesign or stop: Phase 2 remains paused; a new focused remediation issue is required.

Contract or version change:
- Publishes Phase 2R.16 Execution Contract under Protocol 3.0.0 and Substrate 6.0.0.

Artifact migration or compatibility:
- Publishes phase-02r-16 manifest, report, and decision; all historical artifacts remain bitwise immutable.
```

### Acceptance checks
```text
- [x] Executable R2-16 execution contract binds all upstream digests, 20 seed pairs, 3 folds, derivations, and rules before result access.
- [x] Readiness verification executes before model scoring; any failure halts execution with readiness evidence only.
- [x] All 20 signal/null seed pairs (20271201..20271220) and all 3 temporal folds are accounted for with zero omissions or retries.
- [x] Every valid seed/fold passes chronology, 90-day embargoes, policy/episode isolation, and structural support (>=500 observations, >=50 positives, >=50 negatives, 4 billing frequencies, 0% right censoring).
- [x] The frozen Logistic Regression candidate from R2-15 is evaluated without retuning or reselection.
- [x] Matched null controls and policy-level label shuffle controls pass frozen chance boundaries.
- [x] 1,000 deterministic policy-cluster bootstrap replicates per seed/fold compute 95% CIs and pooled seed-balanced AUC.
- [x] Signal recovery, AP lift, Brier skill, and observable/conditional oracle ordering gates are evaluated.
- [x] Uncalibrated calibration sanity and nested learning curves (25%, 50%, 75%, 100%) evaluate cleanly.
- [x] Feature driver ablations (all-signal, recent_payment, missingness) pass required degradation and control rules.
- [x] Robustness scenarios (missingness, delay, unknown category, drift) and temporal stability rules execute cleanly.
- [x] Machine-readable rule records evaluate to exactly one mechanical decision: stop > redesign > proceed without manual override.
- [x] Manifest, report, and decision regenerate byte-for-byte; make check passes locally and in hosted CI.
- [x] Final release holdout remains strictly not_materialized.
```

### Evidence
```text
- docs/modeling/phase-02r-16-v6-statistical-acceptance-execution-contract.md
- docs/experiments/phase-02r-16-v6-statistical-acceptance-manifest.json
- docs/experiments/phase-02r-16-v6-statistical-acceptance-report.md
- docs/experiments/phase-02r-16-v6-statistical-acceptance-decision.md
- simulator/tests/test_v6_acceptance.py test execution logs demonstrating 100% pass rate
- Two byte-identical verification runs via scripts/run_v6_statistical_acceptance.py --check
- Passing make check output with contract, simulator, and repository boundary checks
```

### Dependencies
```text
Must merge first:
- Phase 2R.15 merged through PR #91 as commit 8965c72.

Blocks:
- P2-08 (probability calibration) and P2-09 (explanations) remain paused unless merged decision is proceed.

Related decisions or limitations:
- ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, ADR 0012.
- LIM-002-001, LIM-002-002, LIM-002-003, LIM-002-004.
```
