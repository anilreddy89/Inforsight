# ADR 0012: Authorize bounded sigmoid hazard link architecture for Generation v6

- Status: Accepted through [issue #86](https://github.com/anilreddy89/Inforsight/issues/86) and [PR #87](https://github.com/anilreddy89/Inforsight/pull/87), merge commit `18ce32f`
- Date: 2026-09-04
- Decision owner: Anil Jonnala
- Trigger: Causal response `stop_infeasible_design` from Phase 2R.14BB under ADR 0011
- Preserves: ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, and all historical v1 through v5 evidence as immutable audit records
- Enables: Phase 2R.14D (Generation v6 substrate implementation and qualification)
- Blocks: Resumed Phase 2 work (P2-08 through P2-12) until v6 qualification and replacement statistical acceptance succeed

## Context

Phase 2R.14BB evaluated all 17 post-v4 redesign diagnostics across 120 inventory units (development seeds `20280101..20280120`) and the exhaustive 320-cell feasibility surface (`D16` / `D17`) under Contract `1.1.0`. The evaluation mechanically demonstrated that:
1. Exactly **0 of 320 cells** satisfy simultaneous recovery ($\text{AUC} \ge 0.70$, $\text{AP lift} \ge 0.10$) and monthly hazard bounds ($< 0.20$).
2. The root cause is the **Proportional Hazards Trilemma**: in an additive hazard model with exponential link $\lambda(t) = \lambda_0(t) \exp(X\beta + u)$, scaling coefficients $\beta$ to separate high-risk and low-risk policies exponentially inflates upper-tail hazards ($> 0.20$/month to $0.45$/month), rapidly emptying the cohort and collapsing calibration. Conversely, restricting hazards to $< 0.20$ compresses the score distribution ($\text{std} < 0.35$), leaving the model blind ($\text{AUC} \approx 0.57 - 0.59$).

Pursuant to Contract `1.1.0` Section 10, the required causal response was `stop_infeasible_design`, recorded in ADR 0011. Phase 2R.14C (v5 substrate implementation) was halted because no parameterization of the v5 exponential formula is feasible.

Mathematical preflight on development seed `20280101` evaluated an alternative formulation: replacing the unbounded exponential curve with a **Bounded Sigmoid (Logistic) Hazard Link**. The simulation proved that:
- Maximum theoretical and observed monthly hazard is strictly capped at $\le 0.1500$ (well below the $0.20$ actuarial ceiling) for all policies.
- Coefficient scaling to $\beta \in [2.0, 4.0]$ yields high discrimination ($\text{AUC} = 0.76 - 0.82$, $\text{AP lift} = +0.12 - +0.19$, and Brier skill score $= +0.06 - +0.13$).
- Simultaneous feasibility is achieved across 100% of tested parameter configurations.

## Decision

1. **Retire Exponential Proportional Hazards for Generation v6**:
   Formally abandon the unbounded exponential formulation ($\exp(X\beta)$) for baseline and synthetic hazard generation.
2. **Authorize Bounded Sigmoid (Logistic) Hazard Link for Generation v6**:
   Adopt the bounded logistic link function for discrete monthly event hazards:
   $$\lambda_{\text{lapse}}(t) = \lambda_{\max, \text{lapse}} \cdot \sigma\left(\alpha_l + \delta_t + \beta_l^T \tilde{X} + u\right)$$
   $$\lambda_{\text{surrender}}(t) = \lambda_{\max, \text{surrender}} \cdot \sigma\left(\alpha_s + \delta_t + \beta_s^T \tilde{X} + 0.5 \cdot u\right)$$
   where:
   - $\sigma(z) = \frac{1}{1 + e^{-z}}$, clipped to $[-15.0, 15.0]$ for numerical stability.
   - $\lambda_{\max, \text{lapse}} = 0.10$ and $\lambda_{\max, \text{surrender}} = 0.05$, guaranteeing that total monthly event hazard can never exceed $0.1500$ under any combination of covariates or unobserved frailty:
     $$\lambda_{\text{total}}(t) \le 0.10 + 0.05 = 0.1500 < 0.2000 \quad \forall X \in \mathbb{R}^d, u \in \mathbb{R}$$
   - $\tilde{X}$ represents standardized observable feature vectors.
   - $u \sim \mathcal{N}(0, \sigma_u^2)$ represents latent unobserved policy frailty.
   - $\delta_t$ represents monthly duration and seasonal baseline offsets.
3. **Approve Generation v6 Substrate Contract**:
   Approve `docs/modeling/phase-02r-14c-v6-bounded-sigmoid-substrate-contract.md` as the normative design specification.
4. **Preserve Clean-Room and Seed Domain Invariants**:
   - Development seeds `20280101..20280120` remain spent for R2-14BB.
   - A fresh development seed block `20280201..20280220` is authorized for Generation v6 development and qualification.
   - Reserved acceptance seeds `20271201..20271220` and the final release holdout remain untouched, unassigned, and `not_materialized`.
5. **Phase Sequencing**:
   - Phase 2R.14C is closed with this architecture decision and contract specification.
   - Authorize Phase 2R.14D for v6 substrate implementation and qualification.

## Consequences

- The Proportional Hazards Trilemma (ADR 0011) is resolved by mathematical construction: the hazard ceiling $< 0.20$ cannot be breached.
- Generation v6 development is authorized to proceed with bounded logistic hazard dynamics.
- All historical evidence (v1 through v5, ADR 0001 through ADR 0011) remains immutable audit evidence.
- Resumed Phase 2 work (P2-08 through P2-12) remains paused until v6 qualification and replacement statistical acceptance pass.
