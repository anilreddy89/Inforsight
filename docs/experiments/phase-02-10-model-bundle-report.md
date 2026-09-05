# Phase 2.10: Model Bundle and Environment Reproducibility Report

- **Phase**: `P2-10` (Issue #100)
- **Milestone**: `v0.2.0-risk-model`
- **Artifact Version**: `1.0.0`
- **Contract Version**: `1.0.0`
- **Claim Boundary**: `model_bundle_and_environment_reproducibility_only`
- **Final Holdout Partition**: `not_materialized` (strictly isolated and unmaterialized)

---

## 1. Executive Summary & Core Objectives

Phase 2.10 creates an immutable, portable, schema-validated **Release Model Bundle** (`phase-02-10-model-bundle.json`) unifying fitted preprocessing transformations, linear model weights, Platt probability calibrator parameters, explainer background baselines, and operational decision policies.

### Key Accomplishments
1. **Safe Pure-JSON Serialization**: Eliminated all binary pickling (`pickle`) risks by encoding complete mathematical state into transparent JSON.
2. **Bit-for-Bit Reload Invariant**: Standalone inference engine reloads exclusively from the bundle and reproduces predictions across 8,782 observations with zero meaningful divergence (max prob delta: `2.22e-16` <= 1.00e-12).
3. **Operational Tier Concordance (100%)**: 100.0% concordance across Risk Tiers 1 through 4 and high-lift review queues.
4. **Exact Additive Logit Reconstruction**: Attributions recomputed from bundle parameters reconstruct calibrated logits with machine precision.
5. **Environment Provenance Locking**: Locked Python runtime, dependency lock hashes, and library versions (`scikit-learn`, `numpy`, `scipy`).

---

## 2. Model Bundle Component Architecture

| Component | Key Specifications | Parameter Count / Dimensions |
| --- | --- | ---: |
| **Preprocessor** | 13 numeric standard scalers + 4 categorical one-hot encoders | 28 total features |
| **Base Model** | LogisticRegression ($L_2, C=1.0$, solver=`liblinear`, seed=20260817) | 28 weights + 1 intercept |
| **Calibrator** | platt_scaling ($A=0.961760, B=-0.033416$) | 2 parameters |
| **Explainer Reference** | Evaluation cohort baseline ($N=8,782$, $\mathbb{E}[z]=-1.876371$, $\mathbb{E}[p]=0.132806$) | 28 column means |
| **Operational Policy** | 4 Risk Tiers + 3 Review Queues (Top 1%, 5%, 20%) | 7 policy rules |

---

## 3. Bit-for-Bit Reload Verification Results

A standalone `BundledInferenceEngine` loaded exclusively from `phase-02-10-model-bundle.json` without access to training data, fitting scripts, or scikit-learn estimators, and scored all out-of-sample observations:

| Verification Invariant | Target Scope | Observed Maximum Divergence | Tolerance | Status |
| --- | :---: | :---: | :---: | :---: |
| **Calibrated Probability** | 8,782 out-of-sample observations | `2.22e-16` | `1.00e-12` | **PASS** |
| **Linear Logit ($z$)** | 8,782 out-of-sample observations | `8.88e-16` | `1.00e-12` | **PASS** |
| **Additive Logit Reconstruction** | 8,782 out-of-sample observations | `8.88e-16` | `1.00e-12` | **PASS** |
| **Risk Tier Concordance** | 8,782 out-of-sample observations | `100.00%` (8,782 / 8,782) | `100.0%` | **PASS** |

---

## 4. Encapsulated Operational Policies

### Risk Tiers
| Tier Name | Probability Range | Action Protocol |
| --- | :---: | --- |
| **Tier 1: Low Risk** | `[0.00, 0.10)` | `standard_passive_billing` |
| **Tier 2: Moderate Risk** | `[0.10, 0.25)` | `digital_payment_reminder` |
| **Tier 3: High Risk** | `[0.25, 0.50)` | `proactive_conservation_triage` |
| **Tier 4: Critical Risk** | `[0.50, 1.00)` | `immediate_grace_period_intervention` |

### Review Queue Capacities
| Capacity Tier | Cutoff Probability | Precision | Recall | Lift |
| :---: | :---: | :---: | :---: | :---: |
| **Top 1%** | `p >= 0.3409` | `34.09%` | `2.42%` | `2.23x` |
| **Top 5%** | `p >= 0.2289` | `35.31%` | `11.57%` | `2.31x` |
| **Top 20%** | `p >= 0.1654` | `27.97%` | `36.64%` | `1.83x` |

---

## 5. Runtime Environment & Dependency Specifications

- **Python Version**: `3.12.2`
- **Host Platform**: `Darwin 25.6.0 (arm64)`
- **scikit-learn**: `1.7.2`
- **numpy**: `2.5.2`
- **scipy**: `1.18.0`
- **pyproject.toml Digest**: `ecea8433959b514ccb74f8111d66445401e95c0822be9a7789c9bc2d577be482`

---

## 6. Cryptographic Lineage & Integrity Invariants

- **Model Bundle Digest**: `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`
- **Upstream Candidate Manifest**: `5fc28797a47f1321ca141d814fc33b37018e05f99779053b6789ebef3dca7803`
- **Upstream Calibration Manifest**: `ff196d6b78e803eef6e51a2cb439070673d4150fa98ace5bb6f03696f933c06b`
- **Upstream Explanations Manifest**: `d2c58d727632846130d30393a7f860c7c4e60f04516f2cb496b50d85bbb2f064`
- **Bundle Contract Digest**: `a81f5e5c8f32bdb2f5eac555cd663d225d89fbb56f53bd88e1b2ff3eeece8e35`
- **Source Code Digest**: `c61915e35560efa8da246cefd9969913e42407f32a801abb4bc0869b2ecc43fa`
- **Final Holdout Status**: `not_materialized` (Clean-room intact)

