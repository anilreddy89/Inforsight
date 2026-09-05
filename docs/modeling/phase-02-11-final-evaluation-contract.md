# Phase 2.11: Final Evaluation, Model Card, and Phase 2 Decision Note Contract

- **Contract Version**: `1.0.0`
- **Artifact Version**: `1.0.0`
- **Phase**: `P2-11`
- **Issue**: #102
- **Milestone**: `v0.2.0-risk-model`
- **Claim Boundary**: `final_evaluation_and_model_card_only`
- **Governing Architecture Decisions**: ADR 0001 (Clean Room & Synthetic Data), ADR 0002 (Perception vs Action Authority), ADR 0003 (Local Deterministic Execution), ADR 0012 (Bounded Sigmoid Hazard Link), ADR 0013 (Acceptance Protocol 3.1.0)
- **Governing Substrate Contract**: Generation v6 Bounded Sigmoid Substrate Contract version `6.0.0`
- **Governing Evaluation Contract**: Generation v6 Evaluation Pipeline Implementation Contract version `6.0.0`
- **Governing Calibration Contract**: Probability Calibration Contract version `1.0.0`
- **Governing Explanations Contract**: Model-Behavior Explanations Contract version `1.0.0`
- **Governing Model Bundle**: `docs/experiments/phase-02-10-model-bundle.json` (SHA-256: `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`)
- **Status**: Active

---

## 1. Context and Objective

Phase 2.11 constitutes the **final evaluation, transparent disclosure, and release decision milestone** of Phase 2 (Baseline Machine Learning).

Having established a statistically qualified substrate in Phase 2R (Protocol 3.1.0 `PROCEED` under ADR 0013), calibrated probabilities in Phase 2.08 (Platt scaling ECE = 0.0115, slope = 0.9498), published exact additive log-odds and centered SHAP attributions in Phase 2.09, and packaged the entire fitted system into an immutable pure-JSON release model bundle in Phase 2.10, Phase 2.11 conducts the final, access-controlled evaluation of the release bundle, authors `MODEL_CARD.md`, records the Phase 2 Decision Note, and resolves active limitations `LIM-002-001`, `LIM-002-002`, and `LIM-002-003`.

---

## 2. Invariants and Architectural Guarantees

### 2.1 Model Immutability Invariant (Zero Retraining / Zero Post-Hoc Tuning)
1. The release candidate Logistic Regression estimator coefficients ($\beta \in \mathbb{R}^{27}, \beta_0 \in \mathbb{R}$) are frozen by commit `7112e82` and bundle `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`.
2. The Platt calibrator parameters ($A = 0.961849, B = -0.033420$) are frozen.
3. Operational thresholds ($0.10, 0.25, 0.50$) and review queue cuts ($0.3409, 0.2289, 0.1654$) are frozen.
4. **Invariant**: No model weights, preprocessing statistics, calibrator parameters, or threshold cuts may be altered based on final evaluation metrics.

### 2.2 Access-Controlled Final Evaluation Protocol (Resolution of LIM-002-003)
Under `LIM-002-003`, historical partition-string checks allowed unintended prediction access during adversarial review. Phase 2.11 enforces a pre-registered, cryptographic one-shot evaluation protocol:
1. **Target Data Partition**: The final evaluation partition consists of the designated `non_final_evaluation` role observations (8,782 observations across 1,440 policies of seed `20280201`), strictly out-of-sample from both `fit` (43,590 rows) and `calibration` (8,560 rows).
2. **Scoring Authorization**: Final scoring executes through `BundledInferenceEngine` from the verified release bundle without scikit-learn dependency at runtime.
3. **Execution Record**: The evaluation harness records execution timestamp, caller identity, input hashes, command hash, and evaluation digest, ensuring reproducible verification without iterative tuning.

### 2.3 Statistical Performance Evaluation & Clustered Bootstrap
The final evaluation must compute and report:
1. **Discrimination**:
   - ROC AUC with 95% policy-clustered bootstrap confidence interval (1,000 resamples).
   - Average Precision (PR AUC) with 95% bootstrap CI.
2. **Calibration**:
   - Brier score and Brier skill score relative to baseline prevalence.
   - Expected Calibration Error (ECE) across 10 uniform probability bins.
   - Empirical calibration slope and intercept from logistic regression of true targets on calibrated logits.
3. **Operational Review Queues**:
   - Precision, Recall, Specificity, Lift, and Net Benefit at 1%, 5%, and 20% review queue capacities, each with 95% bootstrap CIs.
4. **Risk Tiers**:
   - Distribution, count, fraction, observed lapses, and observed rate across Tiers 1 through 4.

### 2.4 Ethical, Synthetic, and Fairness Boundaries
1. **Synthetic Data Disclosure**: The dataset consists exclusively of synthetic, mathematically generated policyholder histories. It does not represent any real-world insurer, insured population, or actual insurance contracts.
2. **Prohibition of Demographic Fairness Claims**: The synthetic corpus intentionally lacks real-world demographic attributes (race, gender, ethnicity, disability, income, geography). No subgroup fairness analysis is performed, and claims of real-world demographic fairness are strictly prohibited.
3. **ADR 0002 Action-Authority Boundary**: Model scores and explanations reside strictly in Tier 1 (Perception). Autonomous intervention, cancellation, pricing adjustment, or customer communication is prohibited. Interventions require passing deterministic business rules (Tier 2) and licensed human conservation specialist review (Tier 4).

---

## 3. Predeclared Final Acceptance Targets

To achieve a mechanical `RELEASE` decision in the Phase 2 Decision Note, the final evaluation must satisfy:

| Gate | Metric | Target Threshold | Rationale |
| --- | --- | ---: | --- |
| **G1: Discrimination Floor** | Out-of-Sample ROC AUC | $\ge 0.6800$ | Exceeds minimum acceptable baseline discrimination |
| **G2: PR Precision Lift** | Out-of-Sample Average Precision | $\ge 0.2500$ (Lift $\ge 0.1000$) | Strong enrichment over $\sim 0.15$ baseline prevalence |
| **G3: Probability Calibration** | Expected Calibration Error (ECE) | $\le 0.0300$ (3.0%) | Probabilities reflect empirical risk frequencies |
| **G4: Calibration Slope** | Empirical Calibration Slope | $\in [0.85, 1.15]$ | Absence of severe under- or over-confidence |
| **G5: Operational Utility** | Top 1% Review Queue Precision | $\ge 0.3000$ (Lift $\ge 2.00\times$) | Concentrated risk in highest priority triage tier |
| **G6: Operational Lift** | Top 5% Review Queue Lift | $\ge 2.00\times$ | Meaningful operational conservation intercept rate |
| **G7: Bundle Reproducibility** | Reload Invariance $\max \|\Delta p\|$ | $\le 1.00 \times 10^{-12}$ | Bit-for-bit numerical reproducibility verified |

---

## 4. Limitation Resolution Criteria

Phase 2.11 provides the final objective closure evidence for three long-standing project limitations:
1. **LIM-002-001 (Billing frequency confounding)**:
   - *Closure Evidence*: Generation v6 multi-cohort architecture verified; all four billing frequencies represented across all folds; no confounding between billing cycle and calendar observation time.
2. **LIM-002-002 (Simulator risk mechanism)**:
   - *Closure Evidence*: Generation v6 bounded sigmoid hazard link architecture and Coefficient Registry verified; recovery of designed pre-cutoff behavioral signals demonstrated across 20 acceptance seeds in Phase 2R.16A and verified on out-of-sample final evaluation.
3. **LIM-002-003 (Holdout integrity & prediction access)**:
   - *Closure Evidence*: Standalone release model bundle executed under pre-registered one-shot execution protocol with complete cryptographic digest binding, audit trail, and zero post-hoc tuning.

---

## 5. Required Deliverables

1. `docs/modeling/phase-02-11-final-evaluation-contract.md`: This document.
2. `scripts/run_final_evaluation.py`: Standalone CLI runner with `--check` and `--write` modes.
3. `simulator/tests/test_final_evaluation.py`: Unit test suite for evaluation protocol and reproducibility.
4. `docs/experiments/phase-02-11-final-evaluation-manifest.json`: Final evaluation manifest with cryptographic lineage.
5. `docs/experiments/phase-02-11-final-evaluation-report.md`: Final experiment report with all metrics and bootstrap CIs.
6. `MODEL_CARD.md`: Root-level comprehensive model card conforming to Mitchell et al. (2019).
7. `docs/experiments/phase-02-11-phase-2-decision-note.md`: Formal release governance decision (`RELEASE`).
8. `docs/limitations.md`: Limitation register update resolving LIM-002-001, LIM-002-002, and LIM-002-003.

