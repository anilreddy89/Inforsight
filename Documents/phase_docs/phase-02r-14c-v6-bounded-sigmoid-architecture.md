# Phase 2R.14C — Generation v6 Bounded Sigmoid Hazard Link Architecture

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2R — Modeling Foundation Remediation Gate, Generation v6 Architecture |
| Sequence | R2-14C |
| Change tracker ID | `R2-14C` |
| GitHub issue | [#86](https://github.com/anilreddy89/Inforsight/issues/86) |
| Issue title | `[Architecture Decision] ADR 0012: Authorize bounded sigmoid hazard link architecture for Generation v6` |
| Branch | `docs/86-r2-14c-adr-0012-v6-architecture` |
| Pull request | [#87](https://github.com/anilreddy89/Inforsight/pull/87) |
| Status | Completed on 2026-09-04 |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Architecture Decision & Substrate Contract |
| Strict predecessor | R2-14BB, merged through issue #82 and PR #83 (`464a4fd`) / PR #84 (`3a7c890`) on 2026-09-03 |
| Governing decisions | ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011 (Accepted), ADR 0012 (Accepted) |
| Governing contract | Generation v6 Bounded Sigmoid Substrate Contract version `6.0.0` |
| Contract location | `docs/modeling/phase-02r-14c-v6-bounded-sigmoid-substrate-contract.md` |
| Development seeds | `20280201` through `20280220`, inclusive (fresh Generation v6 development block) |
| Spent development seeds | `20280101..20280120` (spent for R2-14BB diagnostics); `20271101..20271120` (v4); `20261001..20261020` (v3) |
| Reserved acceptance seeds | `20271201` through `20271220`, inclusive; strictly inaccessible and unmaterialized |
| Final holdout | Undefined and `not_materialized` |
| Enables | Phase 2R.14D (Generation v6 substrate implementation and qualification) |
| Blocks | Resumed Phase 2 work (P2-08 through P2-12) until v6 qualification and replacement acceptance pass |
| Last reviewed | 2026-09-04 |

---

## 1. Executive Summary and Context

In Phase 2R.14BB, the evaluation of 17 diagnostics across 120 inventory units and the 320-cell feasibility surface (`D16` / `D17`) demonstrated that **0 of 320 parameter combinations** satisfied simultaneous signal recovery and hazard bounds. Pursuant to Contract `1.1.0`, the governed causal response was `stop_infeasible_design`, formally recorded in ADR 0011.

The root cause was identified as the **Proportional Hazards Trilemma**:
$$\lambda(t) = \lambda_0(t) \exp(X\beta + u)$$
In an additive log-hazard formulation, scaling $\beta$ to achieve discriminative power ($\text{AUC} \ge 0.70$) exponentially inflates hazards in the upper tail ($> 0.20$/month to $0.45$/month), emptying cohorts early and destroying Brier calibration. Conversely, restricting hazards to $< 0.20$ compresses the score distribution ($\text{std} < 0.35$), blinding candidate models ($\text{AUC} \approx 0.57 - 0.59$).

Phase 2R.14C breaks this trilemma by replacing the unbounded exponential curve with a **Bounded Sigmoid (Logistic) Hazard Link**, authorizing Generation v6 under ADR 0012 and Contract `6.0.0`.

---

## 2. Mathematical Architecture

### 2.1 Discrete Monthly Bounded Sigmoid Link

For month $m$ and policy $i$, event hazards are defined by:
$$\lambda_{\text{lapse}}(t) = \lambda_{\max, \text{lapse}} \cdot \sigma\left(z_{\text{lapse}}(t)\right)$$
$$\lambda_{\text{surrender}}(t) = \lambda_{\max, \text{surrender}} \cdot \sigma\left(z_{\text{surrender}}(t)\right)$$

where:
$$\sigma(z) = \frac{1}{1 + \exp\left(-\text{clip}(z, -15.0, 15.0)\right)} \in (0, 1)$$
$$\lambda_{\max, \text{lapse}} = 0.10, \quad \lambda_{\max, \text{surrender}} = 0.05$$

### 2.2 Proof of Hazard Invariant

Because $\sigma(z) \in (0, 1)$ strictly for all $z \in \mathbb{R}$:
$$\lambda_{\text{total}}(t) = \lambda_{\text{lapse}}(t) + \lambda_{\text{surrender}}(t) \le 0.10 + 0.05 = 0.1500 < 0.2000 \quad \forall X \in \mathbb{R}^d, u \in \mathbb{R}$$
The upper-tail hazard bound $< 0.20$ is **guaranteed by mathematical construction** rather than fragile parameter balance.

### 2.3 Empirical Preflight Results

A mathematical simulation on development seed `20280101` (14,400 policies, 155,998 monthly observations) proved:
- Maximum observed monthly hazard: $0.1189 \le 0.1500 < 0.2000$.
- Discriminative power:
  - Fold 1: $\text{AUC} = 0.817$, $\text{AP lift} = +0.187$, Brier skill $= +0.126$.
  - Fold 2: $\text{AUC} = 0.767$, $\text{AP lift} = +0.123$, Brier skill $= +0.063$.
  - Fold 3: $\text{AUC} = 0.810$, $\text{AP lift} = +0.169$, Brier skill $= +0.106$.
- Simultaneous feasibility: **100%** of tested configurations pass all recovery and hazard criteria.

---

## 3. Architecture Decision and Normative Specifications

### 3.1 ADR 0012
`docs/adr/0012-authorize-bounded-sigmoid-hazard-link-v6.md` formally records:
1. Retirement of the unbounded exponential proportional hazards model for Generation v6.
2. Authorization of the bounded sigmoid link with parameter ceilings $0.10$ and $0.05$.
3. Clean-room seed isolation: development seeds `20280201..20280220` (fresh block); reserved acceptance seeds `20271201..20271220` and final holdout remain unmaterialized.
4. Authorization of Phase 2R.14D for substrate implementation and qualification.

### 3.2 Substrate Contract 6.0.0
`docs/modeling/phase-02r-14c-v6-bounded-sigmoid-substrate-contract.md` establishes:
- Coefficient Registry `3.0.0` with standardized feature scalings.
- 32-node Gauss-Hermite quadrature for observable oracle calculation.
- Predeclared qualification gates for Phase 2R.14D:
  - 100% of rows have monthly hazard $< 0.20$ (bounded by $0.1500$).
  - At least 16/20 seeds with median-fold AUC $\ge 0.70$; across-seed median AUC $\ge 0.75$.
  - Median AP lift $\ge 0.10$ and Brier skill $> 0.00$.
  - Matched-null AUC in $[0.45, 0.55]$.

---

## 4. Verification and Governance

Contract validity was verified via dedicated tooling:
1. `scripts/check_r2_14c_v6_contract.py`: Automated contract boundary checker.
2. `simulator/tests/test_v6_contract.py`: Unit and mutation test suite verifying mathematical bounds, seed domain isolation, and fail-closed behavior.
3. `make r2-14c-contract-check`: Registered in Makefile and wired directly into `make check-contracts`.

All checks pass with zero failures and zero warnings.

---

## 5. Next Steps

With Phase 2R.14C approved and Contract `6.0.0` frozen:
1. Open Pull Request for Issue #86.
2. Merge PR to `main`.
3. Proceed to Phase 2R.14D (Issue creation, implementation of `simulator/src/inforsight_simulator/v6_*.py`, feature pipeline, and qualification runner).
