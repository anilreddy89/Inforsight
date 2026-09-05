# Phase 2.10: Model Bundle and Environment Reproducibility Contract

- **Contract Version**: `1.0.0`
- **Artifact Version**: `1.0.0`
- **Phase**: `P2-10`
- **Issue**: #100
- **Milestone**: `v0.2.0-risk-model`
- **Claim Boundary**: `model_bundle_and_environment_reproducibility_only`
- **Final Holdout Partition Status**: `not_materialized`

---

## 1. Context and Objective

Phase 2.10 specifies the immutable, portable **Release Model Bundle** for the frozen, Platt-calibrated candidate Logistic Regression model selected in Phase 2R.15, calibrated in Phase 2.08, and explained in Phase 2.09.

The purpose of this contract is to guarantee that the complete machine learning decision engine—from raw observation feature extraction through preprocessing, linear model inference, probability calibration, local attribution, and operational risk tiering—is encapsulated into an auditable, portable JSON asset that can be reloaded and executed independently with bit-for-bit numerical reproducibility.

---

## 2. Invariants and Architectural Guarantees

### 2.1 Safe Serialization Invariant (No Unsafe Pickling)
- The model bundle MUST be serialized exclusively as human-readable, schema-validated JSON (`allow_nan=False`, sorted keys).
- Arbitrary Python bytecode serialization (`pickle`, `cloudpickle`, `dill`) is strictly prohibited to eliminate remote code execution vulnerabilities and cross-environment deserialization failures.

### 2.2 Numerical Reproducibility Invariant
For every policy observation $x$ in the out-of-sample evaluation partition ($N = 8,782$ observations of seed `20280201`):
1. **Calibrated Probability Invariant**:
   $$\max_{i \in \text{eval}} |\hat{p}_{\text{bundled}}(x_i) - \hat{p}_{\text{cal}}(x_i)| < 10^{-12}$$
2. **Calibrated Logit Invariant**:
   $$\max_{i \in \text{eval}} |z_{\text{bundled}}(x_i) - z_{\text{cal}}(x_i)| < 10^{-12}$$
3. **Additive Attribution Invariant**:
   $$\max_{i \in \text{eval}} \max_{k \in 1..17} |\Phi_{k, \text{bundled}}(x_i) - \Phi_{k, \text{original}}(x_i)| < 10^{-12}$$
4. **Operational Tier Consistency**:
   $$\text{RiskTier}_{\text{bundled}}(x_i) \equiv \text{RiskTier}_{\text{original}}(x_i) \quad \forall i$$

### 2.3 Standalone Inference Capability
The bundled inference engine (`BundledInferenceEngine`) must execute inference using only standard Python and NumPy primitives, with zero reliance on:
- Scikit-learn runtime estimators.
- Historical training or calibration partition data.
- Oracle sidecars or internal random generators.

### 2.4 Cryptographic Lineage and Environment Provenance
The bundle manifest must cryptographically bind:
- Upstream candidate selection manifest (`phase-02r-15-v6-candidate-selection-manifest.json`).
- Upstream probability calibration manifest (`phase-02-08-probability-calibration-manifest.json`).
- Upstream explanations manifest (`phase-02-09-model-behavior-explanations-manifest.json`).
- Source code digests for preprocessor, bundle engine, and CLI runner.
- Dependency lock hash (`simulator/pyproject.toml`).
- Exact runtime platform, Python version, and library versions (`scikit-learn`, `numpy`, `scipy`).

---

## 3. Model Bundle Schema (Specification `1.0.0`)

The release model bundle (`docs/experiments/phase-02-10-model-bundle.json`) comprises six mandatory sections:

```json
{
  "bundle_version": "1.0.0",
  "bundle_id": "inforsight-v6-logistic-platt-20260817",
  "created_at": "ISO-8601 timestamp",
  "runtime_environment": {
    "python_version": "3.11.x",
    "platform": "macOS / Darwin",
    "library_versions": {
      "scikit-learn": "1.4.x",
      "numpy": "1.26.x",
      "scipy": "1.12.x"
    },
    "dependency_lock_sha256": "..."
  },
  "preprocessor": {
    "schema_version": "6.0.0",
    "feature_count": 27,
    "numeric_features": {
      "rolling_on_time_rate": { "impute_median": 1.0, "mean": 0.8872, "std": 0.1843 },
      "...": "..."
    },
    "categorical_features": {
      "billing_frequency": { "categories": ["annual", "monthly", "quarterly", "semiannual"], "unknown_policy": "all_zeros" },
      "...": "..."
    },
    "ordered_column_names": [
      "rolling_on_time_rate",
      "recent_delay_days",
      "...",
      "billing_frequency=annual",
      "..."
    ]
  },
  "base_model": {
    "family": "LogisticRegression",
    "penalty": "l2",
    "c_param": 1.0,
    "solver": "liblinear",
    "random_seed": 20260817,
    "raw_intercept": -0.707301,
    "raw_coefficients": {
      "rolling_on_time_rate": -0.639311,
      "recent_delay_days": 0.294723,
      "...": "..."
    }
  },
  "calibrator": {
    "method": "platt_scaling",
    "param_a": 0.961849,
    "param_b": -0.033420,
    "calibrated_intercept": -0.713702,
    "calibrated_coefficients": {
      "rolling_on_time_rate": -0.614921,
      "...": "..."
    }
  },
  "explainer_reference": {
    "background_observation_count": 8782,
    "base_value_logit": -0.710707,
    "base_value_probability": 0.329483,
    "background_column_means": {
      "rolling_on_time_rate": 0.0012,
      "...": "..."
    }
  },
  "operational_policy": {
    "risk_tiers": [
      { "name": "Tier 1: Low Risk", "threshold_range": [0.0, 0.10], "action": "standard_passive_billing" },
      { "name": "Tier 2: Moderate Risk", "threshold_range": [0.10, 0.25], "action": "digital_payment_reminder" },
      { "name": "Tier 3: High Risk", "threshold_range": [0.25, 0.50], "action": "proactive_conservation_triage" },
      { "name": "Tier 4: Critical Risk", "threshold_range": [0.50, 1.0], "action": "immediate_grace_period_intervention" }
    ],
    "review_queues": [
      { "capacity_percentile": 1.0, "cutoff_probability": 0.3409, "precision": 0.3409, "lift": 2.23 },
      { "capacity_percentile": 5.0, "cutoff_probability": 0.2289, "recall": 0.1157, "lift": 2.31 },
      { "capacity_percentile": 20.0, "cutoff_probability": 0.1654, "recall": 0.3664, "lift": 1.83 }
    ],
    "authority_boundaries": {
      "tier_1_perception_role": "Perception layer only; zero autonomous authority.",
      "non_causal_boundary": "Correlations (P(y|x)), not causal levers (P(y|do(x))).",
      "tier_2_deterministic_rules_required": "Deterministic grace period and frequency cap filters mandatory.",
      "tier_4_licensed_human_approval": "Licensed conservation specialists hold final authority."
    }
  }
}
```

---

## 4. Verification and Enforcement

The contract requires two levels of automated verification:

1. **Deterministic Bundle Generation (`--write`)**:
   ```bash
   python3 scripts/run_model_bundle.py --write
   ```
   Constructs `phase-02-10-model-bundle.json`, `phase-02-10-model-bundle-manifest.json`, and `phase-02-10-model-bundle-report.md`.

2. **Bit-for-Bit Reload Verification (`--check`)**:
   ```bash
   python3 scripts/run_model_bundle.py --check
   ```
   Loads the bundle from disk into a fresh `BundledInferenceEngine`, scores all 8,782 out-of-sample observations, and verifies that the maximum absolute divergence from original predictions is $< 10^{-12}$.

3. **Continuous Integration Target**:
   ```bash
   make model-bundle-check
   ```
   Executes bundle check and the complete unit test suite `simulator/tests/test_model_bundle.py`.

