# ADR 0011: Record post-v4 redesign diagnostic findings, v5 design infeasibility, and stop

- Status: Proposed through [issue #82](https://github.com/anilreddy89/Inforsight/issues/82)
- Date: 2026-09-03
- Decision owner: Anil Jonnala
- Trigger: Execution of bounded post-v4 redesign diagnostics under Contract `1.1.0` and ADR 0010
- Preserves: ADR 0007, ADR 0008, ADR 0009, ADR 0010, and all historical v1 through v4 evidence as immutable records
- Enables: Governed closeout of Phase 2R.14BB and architectural assessment of parametric constraints
- Blocks: Phase 2R.14C and all downstream performance-dependent model work

## Context

Phase 2R.14BA approved ADR 0010 and amended diagnostic authorization contract `1.1.0`
(merge commit `627e698`), establishing complete, frozen, quantitative truth tables for
hypotheses `H1` through `H5` and the 320-cell feasibility surface (`D16` / `D17`).

Under Issue #82, Phase 2R.14BB executed all 17 diagnostics (`D1` through `D17`) on the
20 unspent development seeds `20280101..20280120` across two scenarios (`signal` and
`matched_null`) and three temporal folds (`fold_1`, `fold_2`, `fold_3`), representing
120 fully executed inventory units. Intermediate row-level outputs were purged immediately,
retaining only governed aggregate statistics with a minimum 10-policy privacy suppression
threshold.

## Findings and Mechanical Dispositions

All hypothesis dispositions were derived mechanically by the automated runner according
to the pre-registered Contract `1.1.0` truth tables without caller or analyst discretion:

1. **`H1_LOG_HAZARD_SPREAD`**: `supported`
   - Observable public score cross-policy standard deviation is `0.3408` for lapse and
     `0.1746` for surrender, both strictly `< 0.35`.
   - The public observable feature combinations do not provide sufficient log-hazard spread
     to separate high-risk and low-risk policies.

2. **`H2_HORIZON_ATTENUATION`**: `unresolved`
   - Evaluated across three temporal folds.

3. **`H3_PROBABILITY_SCALE`**: `rejected`
   - Mean observable-oracle AUC is `0.5684` across the executed units (strictly `< 0.60`
     across 100% of units, well exceeding the `>= 80%` rejection threshold).
   - This demonstrates an underlying ranking/separation failure rather than probability
     scale compression.

4. **`H4_REFERENCE_SPECIFICATION`**: `rejected`
   - The delta between the empirical reference model and the oracle observable score is
     `0.003` (strictly `< 0.02`). The functional reference specification is sound and
     does not introduce model misspecification error.

5. **`H5_HAZARD_TAIL`**: `rejected`
   - Zero observations exceed the monthly hazard ceiling of `>= 0.20` in the baseline
     specification.

6. **`H6_DESIGN_FEASIBILITY`**: `infeasible`
   - The 320-cell Cartesian parameter surface across `public_coefficient_scale` (5 levels),
     `frailty_standard_deviation` (4 levels), `lapse_intercept_delta` (4 levels), and
     `surrender_intercept_delta` (4 levels) was evaluated exhaustively against simultaneous
     recovery targets (AUC >= 0.70 and average precision lift >= 0.10) and the monthly
     hazard bound (< 0.20).
   - Exactly **0 of 320 cells** satisfy simultaneous constraints:
     - Cells that respect the < 0.20 monthly hazard ceiling fail discrimination recovery
       (AUC ~ 0.59 < 0.70, AP lift ~ 0.04 < 0.10).
     - Cells that scale coefficients sufficiently to approach recovery thresholds breach the
       < 0.20 hazard bound and severely degrade probability calibration and Brier skill.

## Decision

1. **Adopt Causal Response `stop_infeasible_design`**:
   Pursuant to Contract `1.1.0` Section 10, when `H6_DESIGN_FEASIBILITY` is `infeasible`,
   the required response is `stop_infeasible_design`. The current additive proportional
   hazards specification cannot simultaneously achieve signal recovery and respect actuarial
   monthly hazard bounds.
2. **Halt Substrate Implementation (Phase 2R.14C)**:
   Phase 2R.14C is not authorized and remains blocked. No synthetic data, corpus, or candidate
   models will be generated for an infeasible design.
3. **Preserve Clean-Room and Seed Integrity**:
   - Development seeds `20280101..20280120` are recorded as spent for R2-14BB diagnostics.
   - Reserved acceptance seeds `20271201..20271220` and the final release holdout remain
     strictly unaccessed, unassigned, and `not_materialized`.
4. **Maintain Pipeline Engineering Distinction**:
   Inforsight retains its sound v1 pipeline-engineering, leakage-guard, temporal-split,
   and scoring-authorization foundation, while recording the empirical mathematical
   boundaries of synthetic hazard calibration.

## Consequences

- Phase 2R.14BB is completed with full reproducible evidence:
  - `docs/experiments/phase-02r-14bb-v5-redesign-diagnostic-manifest.json`
  - `docs/experiments/phase-02r-14bb-v5-redesign-diagnostic-report.md`
  - `docs/experiments/phase-02r-14bb-v5-hypothesis-disposition.md`
- Phase 2R.14C (v5 substrate qualification), Phase 2R.15, Phase 2R.16, and Phase 2 resumed
  work (P2-08 through P2-12) remain paused behind this architectural boundary.
- Prevents wasteful expenditure of compute and reserved holdout data on mathematically
  incompatible parameter regimes.

## Alternatives Considered

### Relaxing the < 0.20 Monthly Hazard Ceiling

Rejected because monthly event hazards exceeding 20% violate basic life insurance actuarial
realism and cause massive early cohort attrition, distorting policy duration dynamics.

### Lowering the Recovery Thresholds (AUC < 0.70)

Rejected because accepting AUC ~ 0.58 would validate a synthetic data generator that
fails to provide learnable signal above random noise, rendering downstream modeling benchmarks
meaningless.
