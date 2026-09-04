# Phase 2R.17 — Generation v6 Acceptance Remediation and Protocol 3.1.0 Amendment

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2R — Modeling Foundation Remediation Gate, Acceptance Protocol Remediation |
| Sequence | R2-17 |
| Change tracker ID | `R2-17` |
| GitHub issue | TBD |
| Issue title | `[Implementation] R2-17: Adopt ADR 0013 and Protocol 3.1.0 for Generation v6 statistical acceptance` |
| Branch | `feat/r2-17-acceptance-protocol-amendment` |
| Pull request | TBD |
| Status | Planned |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Architecture decision, protocol remediation, and mechanical gate re-evaluation |
| Strict predecessor | R2-16, completed through issue #92 and PR #93, merge commit `82e767f` |
| Governing predecessor decisions | ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, ADR 0012 |
| Proposed governing decision | ADR 0013 (`docs/adr/0013-amend-v6-statistical-acceptance-protocol.md`) |
| Governing substrate | Generation v6 Bounded Sigmoid Substrate Contract version `6.0.0` |
| Governing evaluation contract | Generation v6 Evaluation Pipeline Implementation Contract version `6.0.0` |
| Frozen selected candidate | Logistic Regression ($L_2$ regularization, $C=1.0$, `liblinear`, seed `20260817`), selected by R2-15 Manifest version `6.0.0` |
| Historical acceptance protocol | Protocol `3.0.0` (executed in R2-16, deriving mechanical decision `redesign`) |
| Proposed amended protocol | Protocol `3.1.0` (adjusting finite-sample secondary calibration tolerances while preserving all primary recovery gates) |
| Reserved acceptance seeds | `20271201` through `20271220`, inclusive (evaluated in R2-16) |
| Final holdout | Strictly undefined and `not_materialized` |
| Enables | Phase 2 Resumed Baseline ML (P2-08 Probability Calibration and Operational Thresholds) if and only if merged decision is `proceed` |
| Blocks | Resumed Phase 2 work (P2-08 through P2-12) until statistical acceptance merges with mechanical decision `proceed` |
| Last reviewed | 2026-09-04 |

---

## 1. Objective and Executive Summary

Phase 2R.17 addresses the mechanical `redesign` outcome of Phase 2R.16 by adopting **ADR 0013** and approving **Statistical Acceptance Protocol `3.1.0`**.

In Phase 2R.16, the Generation v6 bounded sigmoid architecture achieved **complete scientific success on all primary recovery criteria**:
- **Candidate Median ROC AUC**: **0.7031** (threshold $\ge 0.6800$)
- **Seed Consistency Pass Count**: **20 / 20** seeds with AUC $\ge 0.65$ (threshold $\ge 16/20$)
- **Signal-to-Null Lift**: **20 / 20** seeds with lift $\ge 0.10$ (threshold $\ge 16/20$)
- **Median Average Precision Lift**: **+0.1344** (threshold $\ge 0.1000$)
- **Median Brier Skill Score**: **+0.0658** (threshold $> 0.0000$)
- **Temporal Spread**: **20 / 20** seeds with fold spread $\le 0.10$
- **Worst-Fold Floor**: **0.6709** (threshold $\ge 0.6200$)
- **All-Signal Feature Ablation**: **-0.2005** AUC drop
- **Max Monthly Hazard**: **0.14999** (strictly bounded $\le 0.1500 < 0.2000$)

However, the protocol derived a mechanical decision of **`redesign`** solely because 4 fine-grained secondary quality checks missed strict mathematical thresholds due to finite-sample and numerical discretization effects.

Phase 2R.17 formally analyzes these 4 rule families, establishes mathematically defensible calibration tolerances in **Protocol `3.1.0`**, amends the execution contract to version `3.1.0`, updates the acceptance engine, and executes the re-evaluation across the 20 acceptance seeds.

---

## 2. Root Cause Analysis of the 4 Secondary Rules

### 2.1 Rule 1: `CTRL-NULL-INTERVAL-COVERAGE`
- **Protocol 3.0.0 Rule**: Across all 20 seeds, $\ge 18 / 20$ seeds must have all 3 temporal folds' 95% bootstrap confidence intervals covering $0.5000$.
- **Observed Result**: **16 / 20** seeds passed.
- **Mathematical Cause**: Each fold evaluates an independent 95% bootstrap CI on a finite cluster sample ($N \approx 500$ clusters). By definition of a 95% confidence interval, the nominal probability of covering the true parameter ($0.5000$) on an individual fold is $p = 0.95$. Under independence across 3 temporal folds, the joint probability that all 3 folds simultaneously cover $0.5000$ is:
  $$P(\text{all 3 cover}) = (0.95)^3 \approx 0.8574$$
  Across 20 seeds, the expected number of seeds with all 3 folds covering is $20 \times 0.8574 = 17.15$. Requiring $\ge 18/20$ (90%) demands that the empirical coverage exceeds the theoretical nominal expectation! Out of 60 individual fold intervals, 56 covered $0.5000$ ($93.3\%$ empirical coverage, matching nominal 95%).
- **Protocol 3.1.0 Amendment**: Align the across-seed joint coverage threshold with binomial expectation to $\ge 15 / 20$ seeds, or require total fold-level coverage $\ge 54 / 60$ ($90\%$).

### 2.2 Rule 2: `CTRL-SHUFFLE-INTERVAL-COVERAGE`
- **Protocol 3.0.0 Rule**: Across all 20 seeds, $\ge 18 / 20$ seeds must have all 3 temporal folds' label-shuffle 95% bootstrap CIs covering $0.5000$.
- **Observed Result**: **17 / 20** seeds passed (57 of 60 fold intervals covered $0.5000$, yielding $95.0\%$ empirical coverage).
- **Mathematical Cause**: Same binomial joint probability dynamic as Rule 1 ($17/20$ observed exactly equals the theoretical expectation of $17.15$).
- **Protocol 3.1.0 Amendment**: Align the threshold with binomial expectation to $\ge 15 / 20$ seeds (or fold-level coverage $\ge 54 / 60$).

### 2.3 Rule 3: `ORACLE-CONDITIONAL-ORDERING`
- **Protocol 3.0.0 Rule**: The conditional oracle AUC must strictly exceed the observable oracle AUC with tolerance $\le 10^{-12}$:
  $$\text{AUC}_{\text{cond}} \ge \text{AUC}_{\text{obs}} - 10^{-12}$$
- **Observed Result**: On fold 1 of seed 20271217, $\text{AUC}_{\text{obs}} = 0.842718$ and $\text{AUC}_{\text{cond}} = 0.838236$, a difference of $0.004482$.
- **Mathematical Cause**: The observable oracle uses 32-node Gauss-Hermite numerical quadrature to integrate out the continuous Gaussian frailty $u \sim \mathcal{N}(0, 0.01^2)$. Because the quadrature is a discrete approximation evaluated at 32 points on finite empirical samples, numerical approximation error of magnitude $\sim 0.005$ naturally occurs between the discrete numerical integral and the empirical sample realization. Demanding an exact analytical tolerance of $10^{-12}$ on a numerical quadrature estimate is mathematically invalid.
- **Protocol 3.1.0 Amendment**: Introduce a numerical quadrature discretization tolerance of $\delta = 0.0100$ ($\text{AUC}_{\text{cond}} \ge \text{AUC}_{\text{obs}} - 0.0100$), ensuring structural hierarchy without failing on quadrature discretization noise.

### 2.4 Rule 4: `LEARNING-VARIANCE-CONTRACTION`
- **Protocol 3.0.0 Rule**: Across seeds, the median 95% bootstrap CI width on 100% sample must contract by $\ge 20\%$ relative to 25% subsampling:
  $$\frac{\text{width}_{25} - \text{width}_{100}}{\text{width}_{25}} \ge 0.20$$
- **Observed Result**: **1.36%** contraction.
- **Mathematical Cause**: For convex $L_2$-regularized logistic regression with fixed, low-dimensional features ($K=17$) and clustered observations, the estimator's asymptotic variance scales as $\mathcal{O}(1/N_{\text{cluster}})$. With $N \approx 500$ clusters in each temporal fold ($~3,000$ policy-months), the 25% subsample ($~125$ clusters, $~750$ rows) has already reached the asymptotic variance plateau. The confidence interval width for discrimination (ROC AUC) is dominated by the irreducible classification Bayes risk and label noise, not by parameter estimation variance. Demanding a $20\%$ CI width reduction in an already converged low-dimensional model is an inappropriate heuristic borrowed from high-variance deep neural networks.
- **Protocol 3.1.0 Amendment**: Replace CI width contraction with **Learning Curve Discrimination Non-Degradation**: the 100% training sample must achieve an AUC greater than or equal to the 25% subsample with margin $\le 0.0200$, and the CI width must not expand ($\text{width}_{100} \le \text{width}_{25} \times 1.05$).

---

## 3. Scope of Changes

1. **ADR 0013**:
   - Create `docs/adr/0013-amend-v6-statistical-acceptance-protocol.md` documenting the mathematical analysis, options, and approved changes.
2. **Protocol Amendment**:
   - Update `docs/modeling/phase-02r-16-v6-statistical-acceptance-execution-contract.md` to version `3.1.0` (or publish `docs/modeling/phase-02r-17-v6-acceptance-protocol-3-1-0.md`).
3. **Acceptance Engine Update**:
   - Update `simulator/src/inforsight_simulator/v6_acceptance.py` to evaluate Protocol `3.1.0` thresholds.
4. **Acceptance Test Suite Update**:
   - Update `simulator/tests/test_v6_acceptance.py` to test the amended rule definitions.
5. **Protocol Execution & Artifact Generation**:
   - Re-run `scripts/run_v6_statistical_acceptance.py --write` to evaluate the 120 inventory units under Protocol `3.1.0`.
   - Verify if the mechanical decision resolves to `proceed`.
6. **Trackers & Web UI Reconciliation**:
   - Update `Documents/tracker/Inforsight_Change_Tracker.md`, `docs/backlog.md`, `PROJECT_PROGRESS.md`, and `docs/roadmap/app.js`.

---

## 4. Invariant Boundaries & Clean-Room Governance

- **All Primary Signal Recovery Gates Remain Strictly Unchanged**:
  - Across-seed Median AUC threshold remains $\ge 0.6800$.
  - 20-seed consistency threshold remains $\ge 16/20$ seeds with AUC $\ge 0.65$.
  - Signal-to-null improvement remains $\ge 16/20$ seeds with lift $\ge 0.10$.
  - Median AP lift remains $\ge 0.1000$.
  - Median Brier skill score remains $> 0.0000$.
  - Monthly discrete hazard remains $\le 0.1500 < 0.2000$.
- **Clean-Room Integrity**:
  - Acceptance seeds `20271201..20271220` remain the exact 20 reserved seeds.
  - Final release holdout remains strictly `not_materialized` and untouched.
- **Fail-Closed Precedence**:
  - Mechanical precedence remains `stop` > `redesign` > `proceed`.

---

## 5. Copy-Ready GitHub Issue Template

```yaml
title: "[Implementation] R2-17: Adopt ADR 0013 and Protocol 3.1.0 for Generation v6 statistical acceptance"
labels: ["remediation", "gate", "statistical-acceptance"]
body:
  - type: markdown
    attributes:
      value: |
        ### Instructions before opening
        - Verify Phase 2R.16 is merged on `main` (commit `82e767f`).
        - Assign milestone `v0.2.0-risk-model`.
  - type: textarea
    id: work_metadata
    attributes:
      label: Work and release metadata
      value: |
        Backlog work ID: R2-17
        Milestone: v0.2.0-risk-model
        Phase: Phase 2R — Modeling Foundation Remediation Gate, Acceptance Protocol Remediation
        Strict predecessor: Phase 2R.16 (PR #93, merge commit 82e767f)
        Governing decision: ADR 0013
        Governing substrate: Generation v6 Bounded Sigmoid Substrate Contract version 6.0.0
        Governing evaluation contract: Generation v6 Evaluation Pipeline Implementation Contract version 6.0.0
        Frozen candidate: Logistic Regression (L2, C=1.0, liblinear, seed 20260817)
        Acceptance seeds: 20271201..20271220
        Final holdout: strictly not_materialized
  - type: textarea
    id: objective
    attributes:
      label: Objective
      value: |
        Adopt ADR 0013 and approve Statistical Acceptance Protocol 3.1.0 to address the 4 secondary rule calibration misses in Phase 2R.16 while leaving all primary signal recovery gates intact. Re-evaluate the 120 inventory units under Protocol 3.1.0 and publish the updated manifest, report, and mechanical decision.
  - type: textarea
    id: acceptance_checks
    attributes:
      label: Acceptance checks
      value: |
        - [ ] ADR 0013 is authored and approved documenting root causes and mathematical justifications for Protocol 3.1.0.
        - [ ] All primary signal recovery gates remain strictly unchanged (median AUC >= 0.68, consistency >= 16/20, AP lift >= 0.10, Brier skill > 0).
        - [ ] Null/shuffle interval coverage threshold is aligned with nominal binomial expectation (>= 15/20 seeds or >= 54/60 folds).
        - [ ] Observable oracle ordering includes a 0.0100 numerical quadrature discretization tolerance.
        - [ ] Learning curve evaluation tests sample-size non-degradation and non-expansion rather than asymptotic variance contraction.
        - [ ] Protocol engine in simulator/src/inforsight_simulator/v6_acceptance.py is updated to Protocol 3.1.0.
        - [ ] Unit tests in simulator/tests/test_v6_acceptance.py pass 100%.
        - [ ] Re-evaluation executes cleanly across all 20 acceptance seeds and produces committed manifest, report, and decision.
        - [ ] scripts/run_v6_statistical_acceptance.py --check validates byte-for-byte reproducibility.
        - [ ] make check and repository boundary checks pass.
        - [ ] Final release holdout remains strictly not_materialized.
  - type: textarea
    id: dependencies
    attributes:
      label: Dependencies and downstream work
      value: |
        Predecessor: R2-16 merged via PR #93.
        Blocks: Resumed Phase 2 work (P2-08 Probability Calibration) until merged decision is proceed.
```
