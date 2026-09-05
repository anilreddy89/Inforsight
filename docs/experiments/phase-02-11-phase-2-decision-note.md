# Phase 2 Decision Note: Formal Model Release Determination

- **Phase**: `Phase 2 — Baseline ML` (Cap-stone Gate P2-11)
- **Issue**: #102
- **Date**: 2026-09-04
- **Milestone**: `v0.2.0-risk-model`
- **Governing Protocol**: Final Evaluation Contract version `1.0.0`
- **Evaluated Model Bundle**: `inforsight-v6-logistic-platt-20260817`
- **Bundle SHA-256**: `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`
- **Final Release Determination**: **`RELEASE`**

---

## 1. Background and Context

Phase 2 evaluated baseline machine learning for life insurance policy conservation risk. Early iterations exposed critical modeling pitfalls: temporal confounding (LIM-002-001), lack of a pre-cutoff behavioral hazard mechanism (LIM-002-002), and improper holdout API guarding (LIM-002-003).

Through Phase 2R, Inforsight underwent comprehensive architectural redesign:
1. **Generation v6 Bounded Sigmoid Hazard Architecture** (ADR 0012, Substrate Contract `6.0.0`): Solved the Proportional Hazards Trilemma by bounding maximum monthly hazard to $\le 0.1500 < 0.2000$.
2. **Pre-declared Statistical Acceptance Gate** (Protocol 3.1.0, ADR 0013): Passed 100% of 120 inventory units across 20 acceptance seeds (`20271201..20271220`), achieving median AUC 0.7031 and unpausing Phase 2 with a mechanical `proceed` decision.
3. **Resumed Capabilities**: Calibrated probabilities using Platt scaling (P2-08, ECE 0.0115), published exact additive attributions and centered SHAP values (P2-09, 100% directional sanity), and unified the system into an immutable pure-JSON release model bundle (P2-10).

---

## 2. Gate Verification Summary

All 6 pre-registered gates passed unconditionally on out-of-sample data:

1. **G1 (ROC AUC >= 0.6800)**: Observed **0.6998** (95% CI `[0.6847, 0.7153]`). **PASS**.
2. **G2 (Average Precision >= 0.2500)**: Observed **0.2765** (95% CI `[0.2560, 0.2994]`). **PASS**.
3. **G3 (Expected Calibration Error <= 0.0300)**: Observed **0.0115** (1.15%). **PASS**.
4. **G4 (Calibration Slope in [0.85, 1.15])**: Observed **0.9498**. **PASS**.
5. **G5 (Top 1% Review Precision >= 0.3000)**: Observed **0.3409** (2.23x lift). **PASS**.
6. **G6 (Top 5% Review Lift >= 2.00x)**: Observed **2.31x** lift (11.57% recall). **PASS**.

---

## 3. Limitation Closure Determinations

The completion of Phase 2.11 provides objective closure evidence for:
- **LIM-002-001 (Billing frequency confounding)**: Resolved. Multi-cohort design and rolling-origin temporal folds evaluate all 4 billing frequencies with zero confounding.
- **LIM-002-002 (Simulator hazard mechanism)**: Resolved. The bounded sigmoid hazard link recovers pre-cutoff behavioral patterns across development and acceptance cohorts.
- **LIM-002-003 (Holdout integrity)**: Resolved. The access-controlled one-shot execution protocol and standalone pure-JSON bundle eliminate partition relabeling and ensure immutable reproducibility.

---

## 4. Release Decision and Authorization

Based on objective evidence satisfying all statistical, engineering, and architectural governance requirements:

### Final Determination: **`RELEASE`**

**Actions Authorized**:
1. Publish `MODEL_CARD.md` at repository root.
2. Mark active limitations `LIM-002-001`, `LIM-002-002`, and `LIM-002-003` as **Resolved** in `docs/limitations.md`.
3. Complete Phase 2.11 in `docs/backlog.md`.
4. Authorize Phase 2.12: Publish milestone release tag `v0.2.0-risk-model`.
