# Phase 2R.14C Generation v6 Bounded Sigmoid Substrate Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Contract version | `6.0.0` |
| Coefficient registry | `3.0.0` |
| Random-stream registry | `3.0.0` |
| Authority | ADR 0012 and Issue #86 |
| Implementation phase | R2-14D |
| Development seeds | `20280201..20280220` (20 seeds) |
| Future acceptance seeds | `20271201..20271220`, unmaterialized |
| Final holdout | `not_materialized` |

## 1. Preserved boundaries

Generation v6 MUST preserve the core architectural invariants established across Phases 1 and 2:
1. **Dual-Time and Event-First Rule**: Strict separation of calendar/observation time $t$ from policy age/tenure $\tau$. Events are recorded in the month they occur.
2. **Evaluation Window**: Non-overlapping 90-day evaluation episodes with 30-day seasoning.
3. **Union Target**: Binary outcome $Y \in \{0, 1\}$ indicating lapse or surrender occurring within 90 days of evaluation date.
4. **Temporal Cross-Validation**: Three rolling-origin folds (`fold_1`, `fold_2`, `fold_3`) with strict policy grouping (no cross-fold leakage).
5. **Clean-Room and Sidecar Isolation**: Protected oracle quantities (unobserved frailty $u$, true latent hazards $\lambda$, oracle survival curves) reside strictly in the protected sidecar and are prohibited from candidate model feature matrices.
6. **Matched Signal / Matched Null Pairings**: Each seed produces identical policy cohorts and lifecycle draws for both signal and matched null scenarios; matched null sets feature signal scale to zero.
7. **Deterministic Replay**: Given base seed, scenario, and configuration, output is bit-for-bit identical across runs.
8. **Public Feature Surface**: The standard 17-feature observable surface is preserved without altering schema definitions or leaking future data.
9. **Code and Artifact Isolation**: V6 implementation MUST reside in dedicated modules (`simulator/src/inforsight_simulator/v6_*.py`), schemas (`data-contracts/v6/`), and artifact directories. No v1, v2, v3, v4, or v5 file may be overwritten or modified.

## 2. Seed domain isolation

Seed domains are strictly partitioned. No seed may be reused across development, diagnostic, or acceptance phases:

| Domain | Seeds | Status / Role |
| --- | --- | --- |
| `v3_spent_acceptance` | `20261001..20261020` | Spent acceptance (R2-11) |
| `v4_spent_qualification` | `20271101..20271120` | Spent qualification (R2-14) |
| `v4_reserved_acceptance` | `20271201..20271220` | Reserved acceptance, unmaterialized |
| `v5_diagnostic_development` | `20280101..20280120` | Spent diagnostic inventory (R2-14BB) |
| `v6_development` | `20280201..20280220` | Active Generation v6 development domain |
| `final_holdout` | `not_materialized` | Locked release holdout |

## 3. Stochastic mechanism: Bounded Sigmoid Link

Generation v6 replaces the unbounded exponential hazard link $\lambda_0(t)\exp(X\beta + u)$ with the **Bounded Sigmoid (Logistic) Hazard Link**, resolving the Proportional Hazards Trilemma (ADR 0011, ADR 0012).

### 3.1 Discrete monthly event hazards

For month $m \in \{1, \dots, T\}$ and policy $i$:

$$\lambda_{\text{lapse}}(t) = \lambda_{\max, \text{lapse}} \cdot \sigma\left(z_{\text{lapse}}(t)\right)$$
$$\lambda_{\text{surrender}}(t) = \lambda_{\max, \text{surrender}} \cdot \sigma\left(z_{\text{surrender}}(t)\right)$$

where:
- $\sigma(z) = \frac{1}{1 + e^{-\text{clip}(z, -15.0, 15.0)}}$ is the logistic link, bounded in $(0, 1)$.
- $\lambda_{\max, \text{lapse}} = 0.10$ (monthly lapse hazard upper bound).
- $\lambda_{\max, \text{surrender}} = 0.05$ (monthly surrender hazard upper bound).
- Total monthly hazard is mathematically bounded for all policies and all covariates:
  $$\lambda_{\text{total}}(t) = \lambda_{\text{lapse}}(t) + \lambda_{\text{surrender}}(t) \le 0.10 + 0.05 = 0.1500 < 0.2000 \quad \forall X \in \mathbb{R}^d, u \in \mathbb{R}$$

### 3.2 Linear predictor specifications

$$z_{\text{lapse}}(t) = \alpha_l + \delta_t + \beta_l^T \tilde{X}(t) + u$$
$$z_{\text{surrender}}(t) = \alpha_s + \delta_t + \beta_s^T \tilde{X}(t) + 0.50 \cdot u$$

Parameters:
- Intercepts: $\alpha_l = -2.20$, $\alpha_s = -2.80$.
- Seasonal/duration baseline offset: $\delta_t \in \{-0.08, 0.00, 0.08\}$ by calendar quarter / policy month.
- Unobserved policy frailty: $u \sim \mathcal{N}(0, \sigma_u^2)$ with $\sigma_u = 0.20$, drawn once per policy at issuance.
- Feature vectors: $\tilde{X}(t)$ standardized observables with transforms and clipping defined in Coefficient Registry `3.0.0`.
- Signal scaling: In signal scenario, $\beta$ terms apply at full scale ($1.0$). In matched null scenario, $\beta$ scale $= 0.0$.

### 3.3 Coefficient registry 3.0.0

The public coefficient vectors $\beta_l$ and $\beta_s$ are specified as follows:

| Term | Lapse $\beta_l$ | Surrender $\beta_s$ |
| --- | ---: | ---: |
| tenure | `-0.20` | `0.10` |
| premium | `0.30` | `0.45` |
| quarterly billing | `0.15` | `0.10` |
| semiannual billing | `0.25` | `0.15` |
| annual billing | `0.35` | `0.20` |
| recent payment delay | `1.20` | `0.35` |
| failed payments (12m) | `1.80` | `0.50` |
| payment retries | `0.50` | `0.15` |
| payment recoveries | `-0.80` | `-0.20` |
| arrears amount | `1.50` | `0.40` |
| on-time payment rate | `-1.20` | `-0.30` |
| rolling payment count | `-0.25` | `-0.10` |
| notice count (90d) | `0.65` | `0.50` |
| contact count (90d) | `0.35` | `0.60` |
| failed $\times$ arrears interaction | `0.60` | `0.20` |
| missingness indicators | `0.00` | `0.00` |

### 3.4 Competing-risk incidence and 90-day target

At each month $m$, conditional on survival to month $m$:
1. Total exit probability: $p_{\text{exit}}(m) = \lambda_{\text{total}}(m) = \lambda_{\text{lapse}}(m) + \lambda_{\text{surrender}}(m) \le 0.1500$.
2. Relative branch probabilities:
   $$P(\text{lapse} \mid \text{exit}) = \frac{\lambda_{\text{lapse}}(m)}{\lambda_{\text{total}}(m)}, \quad P(\text{surrender} \mid \text{exit}) = \frac{\lambda_{\text{surrender}}(m)}{\lambda_{\text{total}}(m)}$$
3. Discrete 3-month survival probability from observation month $t$:
   $$S(t, t+3) = \prod_{k=1}^3 \left(1 - \lambda_{\text{total}}(t+k)\right)$$
   Cumulative 90-day union event probability:
   $$P(Y = 1 \mid t) = 1 - S(t, t+3)$$

## 4. Protected oracle sidecar and quadrature

The protected oracle sidecar stores true event risks without leakage:
1. **Conditional Oracle Risk**: Computed using the true drawn frailty $u_i$ and true linear predictors.
2. **Observable Oracle Risk**: Integrates out the unobserved frailty $u$ using a deterministic 32-node Gauss-Hermite quadrature:
   $$P_{\text{obs}}(Y = 1 \mid \tilde{X}) = \int_{-\infty}^{\infty} P(Y = 1 \mid \tilde{X}, u) \frac{1}{\sqrt{2\pi}\sigma_u} e^{-\frac{u^2}{2\sigma_u^2}} du$$
   approximated via $\frac{1}{\sqrt{\pi}} \sum_{j=1}^{32} w_j P\left(Y = 1 \mid \tilde{X}, \sqrt{2}\sigma_u \xi_j\right)$ where $\xi_j, w_j$ are Gauss-Hermite roots and weights.

## 5. Generation v6 qualification gates (R2-14D)

To achieve formal qualification, Generation v6 must satisfy all of the following predeclared criteria on the 20 development seeds `20280201..20280220` across 3 temporal folds (60 evaluations per scenario):

1. **Upper-Tail Hazard Bound**: Monthly total hazard $\lambda_{\text{total}} < 0.2000$ strictly for **100%** of generated rows (theoretical ceiling $\le 0.1500$).
2. **Discriminative Power**:
   - At least 16 of 20 development seeds have median-fold observable-oracle AUC $\ge 0.70$.
   - Across-seed median observable-oracle AUC $\ge 0.75$.
3. **Precision and Calibration**:
   - Across-seed median observable-oracle Average Precision (AP) lift over baseline rate $\ge 0.10$.
   - Across-seed median observable-oracle Brier skill score $> 0.00$.
4. **Matched-Null Parity**:
   - Matched-null observable-oracle and candidate median AUC strictly within $[0.45, 0.55]$.
5. **Feature Sanity**:
   - Zero constant or degenerately clipped features.
   - Nonzero features maintain positive correlation with target in the expected direction.
6. **Governance and Lineage**:
   - 100% deterministic replay on all seeds.
   - Exact parity check between simulated events and observation records.
   - Final holdout remaining `not_materialized`.
   - Reserved acceptance seeds `20271201..20271220` remaining untouched.

## 6. Claim boundary

Generation v6 provides clean-room synthetic data for training and evaluating retention prioritization models. Passing qualification validates mathematical consistency and statistical signal recovery within the synthetic environment; it does not constitute clinical, legal, or prospective commercial validation without real-world telemetry calibration.
