# Phase 2R.14D — Generation v6 Bounded Sigmoid Substrate Implementation and Qualification

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2R — Modeling Foundation Remediation Gate, Generation v6 Implementation & Qualification |
| Sequence | R2-14D |
| Change tracker ID | `R2-14D` |
| GitHub issue | [#88](https://github.com/anilreddy89/Inforsight/issues/88) |
| Issue title | `[Substrate Qualification] Phase 2R.14D: Implement and qualify Generation v6 bounded sigmoid hazard link substrate` |
| Branch | `feat/88-r2-14d-v6-substrate-qualification` |
| Pull request | [#89](https://github.com/anilreddy89/Inforsight/pull/89), merge commit `89ec94a` |
| Status | Completed on 2026-09-04 |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Simulator Implementation & Substrate Qualification |
| Strict predecessor | R2-14C, merged through issue #86 and PR #87 (`18ce32f`) on 2026-09-04 |
| Governing decisions | ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, ADR 0012 |
| Governing contract | Generation v6 Bounded Sigmoid Substrate Contract version `6.0.0` |
| Contract location | `docs/modeling/phase-02r-14c-v6-bounded-sigmoid-substrate-contract.md` |
| Development seeds | `20280201` through `20280220`, inclusive (20 seeds, 120 inventory units) |
| Spent development seeds | `20280101..20280120` (v5 diagnostics); `20271101..20271120` (v4); `20261001..20261020` (v3) |
| Reserved acceptance seeds | `20271201` through `20271220`, inclusive; strictly unmaterialized and untouched |
| Final holdout | Undefined and `not_materialized` |
| Mechanical decision | `qualified` |
| Enables | Phase 2R.15 (Generation v6 evaluation construction and candidate freeze) |
| Blocks | Resumed Phase 2 work (P2-08 through P2-12) until v6 evaluation and replacement acceptance pass |
| Last reviewed | 2026-09-04 |

---

## 1. Executive Summary

Phase 2R.14D implements and qualifies the **Generation v6 Bounded Sigmoid Hazard Link Substrate**, operationalizing the architectural authorization of ADR 0012 and Contract `6.0.0` to resolve the Proportional Hazards Trilemma.

The qualification evaluation executed across all 20 development seeds (`20280201..20280220`) for 120 governed evaluation units (3 temporal folds per seed, evaluated under matched signal and matched null scenarios).

**Mechanical Decision**: `qualified` (100% of qualification gates passed).

### Summary of Observed vs Governed Metrics

| Measure | Target / Boundary | Observed Value | Status |
| --- | --- | ---: | :---: |
| **Maximum Monthly Hazard** | $< 0.2000$ (ceiling $\le 0.1500$) | `0.14999` | **PASS** |
| **Observable Oracle AUC (Seed Recovery)** | $\ge 0.68$ in $\ge 16/20$ seeds | `16 / 20` | **PASS** |
| **Median Observable Oracle AUC** | $\ge 0.7000$ across seeds | `0.7086` | **PASS** |
| **Median Observable Oracle AP Lift** | $\ge 0.1000$ over baseline | `0.1398` | **PASS** |
| **Median Observable Oracle Brier Skill** | $> 0.0000$ | `0.0745` | **PASS** |
| **Reference Model AUC Pass Count** | $\ge 0.65$ in $\ge 16/20$ seeds | `20 / 20` | **PASS** |
| **Matched Null Oracle AUC** | $[0.4500, 0.5500]$ | `0.5000` | **PASS** |
| **Matched Null Candidate AUC** | $[0.4500, 0.5500]$ | `0.5040` | **PASS** |
| **Feature Transform Parity Mismatches** | `= 0` | `0` | **PASS** |
| **Driver Support (Nonzero Features)** | $15/15$ drivers active in all folds | `Pass (100%)` | **PASS** |
| **Structural Controls & Replay** | 100% deterministic replay | `Pass (authorized)` | **PASS** |

---

## 2. Mathematical Substrate & Centered Linear Predictors

### 2.1 Bounded Sigmoid Formulation

For month $m \in \{1, 2, 3\}$ and policy $i$:
$$\lambda_{\text{lapse}}(t) = 0.10 \cdot \sigma\left(z_{\text{lapse}}(t)\right)$$
$$\lambda_{\text{surrender}}(t) = 0.05 \cdot \sigma\left(z_{\text{surrender}}(t)\right)$$
$$\lambda_{\text{total}}(t) = \lambda_{\text{lapse}}(t) + \lambda_{\text{surrender}}(t) \le 0.1500 < 0.2000$$

### 2.2 Centering and Dynamic Range Scaling

In the discrete logistic link, $\sigma'(0) = 0.25$ provides maximal discriminative sensitivity around $z = 0$. Empirical analysis revealed that raw score terms had non-zero expectations ($\mu_l \approx 0.21$, $\mu_s \approx 0.20$) and standard deviations $\approx 0.46$.

Generation v6 centers the score terms and applies a scale factor of $6.0$:
$$z_{\text{lapse}}(t) = \alpha_l + \delta_t + u_i + 6.0 \cdot \left(\beta_l^T \tilde{X}(t) - 0.21\right) \cdot \text{scale}_{\text{signal}}$$
$$z_{\text{surrender}}(t) = \alpha_s + \delta_t + 0.50 \cdot u_i + 6.0 \cdot \left(\beta_s^T \tilde{X}(t) - 0.20\right) \cdot \text{scale}_{\text{signal}}$$

This ensures:
1. The linear predictor centers directly in the steep, linear portion of the sigmoid.
2. Signal separation is magnified by $6.0\times$, producing median AUC of $0.7086$ and AP lift of $+0.1398$ (a $6\times$ improvement over Generation v4).
3. The absolute ceiling remains strictly $\le 0.1500$, preserving the actuarial bound for 100% of records.

---

## 3. Implemented Modules and Governance Tools

- `simulator/src/inforsight_simulator/v6_config.py`: Authoritative frozen configuration for Generation v6 contracts (`6.0.0`, `3.0.0`, `3.0.0`), deterministic stream set hashes, and artifact lineage.
- `simulator/src/inforsight_simulator/v6_corpus.py`: Discrete event engine implementing bounded competing hazards, 32-node Gauss-Hermite quadrature observable oracle, sidecar isolation, and feature reconstruction.
- `simulator/src/inforsight_simulator/v6_qualification.py`: Readiness validator, planned inventory of 120 units, seed runner, metric aggregation, and mechanical gate evaluation.
- `scripts/run_v6_qualification.py`: Governed CLI supporting `--readiness-check`, `--seed`, `--write`, and `--check`.
- `simulator/tests/test_v6_config.py`, `simulator/tests/test_v6_corpus.py`, `simulator/tests/test_v6_qualification.py`: Comprehensive test suites covering all architectural invariants.
- `Makefile`: Wired `r2-14d-qualification-check` into `check-v4-v5` and `check`.

---

## 4. Lineage and Invariant Protection

- **Spent Domain Isolation**: Development seeds `20280201..20280220` are now formally spent as development qualification evidence.
- **Future Acceptance Protection**: Reserved acceptance seeds `20271201..20271220` remain strictly unmaterialized and untouched.
- **Final Holdout**: Unmaterialized.
- **Historical Evidence**: All previous artifacts (v1 through v5, ADR 0001 through ADR 0012) remain preserved and immutable.

---

## 5. Next Steps

With the mechanical decision of `qualified`, Phase 2R.14D is complete. Phase 2R.15 (candidate model freeze and evaluation construction on Generation v6) is now formally authorized.
