# Machine Learning (`ml/`)

This directory is reserved for **Phase 5: Direct Causal Machine Learning & Advanced Uplift Modeling**.

### Background
During Phase 2 (Baseline ML) and Phase 3 (Conservation Decision Engine), the risk perception model (`inforsight-v6-logistic-platt-20260817`) was implemented within `simulator/src/inforsight_simulator/` and served via `serving/` to guarantee point-in-time state reconstruction invariants, sub-millisecond scoring, and zero deserialization hazards.

### Phase 5 Planned Scope
When enterprise intervention outcome histories are integrated, direct causal estimators will be developed and benchmarked in this directory:
- **Causal Uplift Models:** Two-model approaches (T-Learners, X-Learners, R-Learners) and Causal Forests directly estimating heterogeneous treatment effects:
  $$\tau(x) = \mathbb{E}[Y(1) - Y(0) \mid X = x]$$
- **Double Machine Learning (DML):** Semi-parametric causal inference separating high-dimensional confounding from policy intervention effects.
- **Model Registry & Governance:** Formal model packaging, reproducible benchmarks, and integration with the enterprise control plane (`services/control-plane`).
