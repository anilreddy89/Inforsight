# Phase 2.10 — Artifact and Environment Reproducibility

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2 — Baseline ML (Resumed after Phase 2R Acceptance Gate) |
| Sequence | 10 |
| Change tracker ID | `P2-10` |
| GitHub issue | [#100](https://github.com/anilreddy89/Inforsight/issues/100) |
| Issue title | `[Implementation] P2-10: Version training configuration, dependencies, metrics, and model artifacts` |
| Branch | `feat/100-p2-10-artifact-and-environment-reproducibility` |
| Pull request | [#101](https://github.com/anilreddy89/Inforsight/pull/101) |
| Status | Completed; merged in commit `7112e82` |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Engineering / Model Governance / Reproducibility |
| Strict predecessors | Phase 2R.16A (PR #95), Phase 2.08 (PR #97), Phase 2.09 (PR #99) |
| Governing predecessor decisions | ADR 0001 (Clean Room), ADR 0002 (Authority Model), ADR 0003 (Local Execution), ADR 0012 (Bounded Sigmoid), ADR 0013 (Protocol 3.1.0) |
| Governing substrate | Generation v6 Bounded Sigmoid Substrate Contract version `6.0.0` |
| Governing evaluation contract | Generation v6 Evaluation Pipeline Implementation Contract version `6.0.0` |
| Frozen selected candidate | Logistic Regression ($L_2$ regularization, $C=1.0$, `liblinear`, seed `20260817`), selected by R2-15 Manifest version `6.0.0` |
| Selected calibrator | Platt Scaling ($A=0.961849, B=-0.033420$, fit on calibration partition of seed `20280201`), selected by P2-08 Manifest version `1.0.0` |
| Explainer engine | `ModelExplainer` (Exact additive log-odds and centered SHAP), certified by P2-09 Manifest version `1.0.0` |
| Primary development seed | `20280201` |
| Spent acceptance seeds | `20271201` through `20271220`, inclusive (spent in R2-16/16A acceptance; strictly isolated) |
| Evaluation partition | Designated `non_final_evaluation` role policies (8,782 observations of seed `20280201`) |
| Final holdout | Strictly undefined, unassigned, and `not_materialized` |
| Enables | Phase 2 Baseline ML: P2-11 (`MODEL_CARD.md`, final evaluation, and Phase 2 decision note) |
| Blocks | P2-12 (`v0.2.0-risk-model` release marker and release notes) |
| Last reviewed | 2026-09-04 |

---

## 1. Executive Summary and Problem Statement

### 1.1 Context and Authorization
Phase 2R.16A cleared all statistical acceptance requirements with a mechanical `PROCEED` decision under ADR 0013 and Protocol `3.1.0`. Following Phase 2 resumption:
- **Phase 2.08** successfully calibrated the frozen candidate Logistic Regression model using Platt scaling ($A=0.961849, B=-0.033420$), bringing ECE to $0.0115 \le 0.0300$, slope to $0.9498 \in [0.85, 1.15]$, and defining 4 operational risk tiers with high-lift review queues.
- **Phase 2.09** mathematically decomposed calibrated predictions into exact additive log-odds attributions and centered SHAP values (residual $< 10^{-14}$), passed 100% of directional sanity checks (17/17), and codified ADR 0002 action-authority boundaries.

With model selection, calibration, and explainability complete, Phase 2.10 addresses **reproducibility, artifact bundling, and environment encapsulation**.

### 1.2 The Problem: Ephemeral Runtimes vs. Immutable Deployment Assets
Machine learning models often suffer from the "works on my machine" anti-pattern where predictions cannot be reproduced outside the original training script due to:
1. **Unversioned Environment Drift**: Implicit dependency updates (e.g., minor scikit-learn or numpy releases) altering numerical tolerances, solver convergence, or tie-breaking logic.
2. **Scattered Fitted State**: Preprocessor transformations (imputation medians, standard scaler means/stds, one-hot category maps), base estimator weights, and calibrator parameters stored in separate memory spaces without unified cryptographic binding.
3. **Insecure Deserialization Hazards**: Reliance on unrestricted binary pickling (`pickle`), creating security risks and portability barriers across systems.

### 1.3 Objective: Deterministic Model Bundle and Reload Verification
Phase 2.10 establishes an immutable, versioned, portable JSON-based **Release Model Bundle** containing:
1. **Fitted Preprocessing Specification**: Exact numerical imputation medians, standard scaler means and standard deviations, and ordered categorical level maps.
2. **Candidate Estimator Specification**: Frozen intercept $\beta_0$, coefficient vector $\beta \in \mathbb{R}^{27}$, solver configuration, and seed `20260817`.
3. **Platt Calibrator Parameters**: Slope $A=0.961849$, intercept $B=-0.033420$, and calibration digest.
4. **Attribution & Explainer Reference**: Empirical background mean vector $\bar{x} \in \mathbb{R}^{27}$ and baseline logit $\mathbb{E}[z] = -0.7107$.
5. **Operational Decision Thresholds**: Tiers 1 through 4 cutoffs ($0.10, 0.25, 0.50$) and review queue capacities (Top 1%, 5%, 20%).
6. **Reload-and-Score Invariant**: A standalone inference runner loading exclusively from the serialized bundle must reproduce predictions across out-of-sample observations with zero error:
   $$\max_{i} |\hat{p}_{\text{reloaded}}(x_i) - \hat{p}_{\text{cal}}(x_i)| < 10^{-12}$$

---

## 2. Technical Architecture & Bundle Specification

### 2.1 Bundle Schema
The bundle will be serialized as `docs/experiments/phase-02-10-model-bundle.json` conforming to a strict JSON Schema:
- `bundle_version`: `"1.0.0"`
- `model_id`: `"inforsight-v6-logistic-platt-20260817"`
- `runtime_environment`:
  - `python_version`: Version tuple
  - `dependency_digests`: `pyproject.toml` and lockfile SHA-256
  - `library_versions`: `scikit-learn`, `numpy`, `scipy`
- `feature_contract`:
  - 13 numeric features with imputers and scalers
  - 4 categorical features with explicit one-hot encoding dictionaries
  - Total column dimension $D=27$
- `fitted_parameters`:
  - `raw_intercept`: float
  - `raw_coefficients`: mapping of column name to float weight
  - `calibrator`: `{ "type": "platt_scaling", "slope": float, "intercept": float }`
- `explainer_reference`:
  - `background_mean`: mapping of column name to float mean
  - `base_value_logit`: float
  - `base_value_probability`: float
- `operational_policy`:
  - Risk tier thresholds: Low ($<0.10$), Moderate ($0.10-0.25$), High ($0.25-0.50$), Critical ($\ge 0.50$)
  - Review queue percentiles: 1% ($p \ge 0.3409$), 5% ($p \ge 0.2289$), 20% ($p \ge 0.1654$)

### 2.2 Standalone Scoring Engine
A dedicated production-grade scoring class `BundledInferenceEngine`:
- Ingests raw observation dictionaries.
- Applies preprocessor transforms deterministically in pure Python/NumPy (zero scikit-learn dependency required at scoring time).
- Evaluates linear dot product and Platt sigmoid calibration.
- Yields calibrated probability, operational tier, top risk/protective drivers, and audit trace.

---

## 3. Acceptance Criteria & Gates

1. **Deterministic Artifact Packaging**:
   - `scripts/build_model_bundle.py --write` builds the complete model bundle JSON and manifest.
   - All input manifests (R2-15, P2-08, P2-09) and contracts bound via SHA-256 digests.
2. **Reload-and-Score Bit-for-Bit Verification**:
   - `scripts/verify_model_bundle.py --check` reloads the bundle and executes inference on all 8,782 out-of-sample observations.
   - Max absolute probability divergence: $\max |\hat{p}_{\text{bundle}} - \hat{p}_{\text{cal}}| < 10^{-12}$.
   - Max absolute logit divergence: $\max |z_{\text{bundle}} - z_{\text{cal}}| < 10^{-12}$.
3. **Environment & Dependency Lock Check**:
   - Explicit recording and assertion of all package dependencies and Python environment hashes.
4. **Test Suite & Clean-Room Boundary**:
   - 100% of unit tests pass under `make check` and `make model-bundle-check`.
   - `check_repository_boundaries.sh` passes with zero violations.
   - Final release holdout remains strictly `not_materialized`.

---

## 4. Work Breakdown & Execution Plan

- [x] Create Model Bundle Contract: `docs/modeling/phase-02-10-model-bundle-and-reproducibility-contract.md`.
- [x] Implement Bundle Exporter and Bundled Scoring Engine in `simulator/src/inforsight_simulator/bundle.py`.
- [x] Build CLI runner `scripts/run_model_bundle.py` with `--write` and `--check` modes.
- [x] Generate deterministic artifacts:
  - `docs/experiments/phase-02-10-model-bundle.json`
  - `docs/experiments/phase-02-10-model-bundle-manifest.json`
  - `docs/experiments/phase-02-10-model-bundle-report.md`
- [x] Implement unit test suite `simulator/tests/test_model_bundle.py` (8 new tests, 392 total).
- [x] Wire `model-bundle-check` target into `Makefile`.
- [x] Update documentation, trackers, and Web UI (`docs/roadmap/app.js`, `docs/roadmap/index.html`).

---

## 5. Verification & Invariant Results

1. **Bit-for-Bit Reload Invariance**:
   - $\max_{i} |\hat{p}_{\text{bundle}}(x_i) - \hat{p}_{\text{cal}}(x_i)| = 2.22 \times 10^{-16} \le 1.00 \times 10^{-12}$ (**PASS**)
   - $\max_{i} |z_{\text{bundle}}(x_i) - z_{\text{cal}}(x_i)| = 8.88 \times 10^{-16} \le 1.00 \times 10^{-12}$ (**PASS**)
   - $\max_{i} |z_{\text{reconstructed}}(x_i) - z_{\text{cal}}(x_i)| = 8.88 \times 10^{-16} \le 1.00 \times 10^{-12}$ (**PASS**)
2. **Operational Decision Concordance**:
   - Risk Tier Concordance: 8,782 / 8,782 (**100.00%**)
   - Review Queue Concordance: 8,782 / 8,782 (**100.00%**)
3. **Engineering Rigor**:
   - Unit tests: 392 / 392 passed (`make check`, `make model-bundle-check`).
   - Repository boundaries: `check_repository_boundaries.sh` passed.
   - Clean-room holdout isolation: `final_holdout_status` strictly `not_materialized`.

