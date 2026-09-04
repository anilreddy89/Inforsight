# Phase 2R.14BB v5 Redesign Diagnostic Report

Issue: #82
Phase: R2-14BB
Predecessor merge: `627e698`
Diagnostic contract: `1.1.0`

## Diagnostic Results Summary

- Executed inventory units: `120` across 20 seeds and 2 scenarios.
- Feasibility grid cells evaluated: `320` (320 Cartesian points).
- Feasible grid cells satisfying simultaneous constraints: `0`.
- Feasibility status: `infeasible`.

## Hypothesis Dispositions

| Hypothesis | Disposition | Quantitative Basis |
| --- | --- | --- |
| `H1_LOG_HAZARD_SPREAD` | `supported` | Cross-policy std (lapse=0.3408, surrender=0.1746) < 0.35 |
| `H2_HORIZON_ATTENUATION` | `unresolved` | Evaluated across 3 temporal folds |
| `H3_PROBABILITY_SCALE` | `rejected` | Observable-oracle AUC < 0.60 (mean 0.5684) indicates rank/separation failure |
| `H4_REFERENCE_SPECIFICATION` | `rejected` | Reference vs oracle AUC delta < 0.02; functional reference is not misspecified |
| `H5_HAZARD_TAIL` | `rejected` | Zero hazard exceedances >= 0.20 observed in baseline |
| `H6_DESIGN_FEASIBILITY` | `infeasible` | 0/320 cells satisfy simultaneous recovery (AUC >= 0.70, AP lift >= 0.10) and hazard (< 0.20) rules |

## Feasibility Surface Evaluation (D16 / D17)

All 320 cells of the frozen Cartesian surface were exhaustively evaluated across:
- `public_coefficient_scale`: `[1.0, 1.5, 2.0, 2.5, 3.0]`
- `frailty_standard_deviation`: `[0.00, 0.10, 0.20, 0.30]`
- `lapse_intercept_delta`: `[-0.50, -0.25, 0.00, 0.25]`
- `surrender_intercept_delta`: `[-0.50, -0.25, 0.00, 0.25]`

**Result**: Exactly 0 of 320 cells satisfy simultaneous constraints.
Cells that maintain the `<0.20` monthly hazard bound fail recovery (`AUC ~ 0.59`, `AP lift ~ 0.04 < 0.10`).
Cells that scale coefficients to increase AUC breach the `<0.20` hazard bound and destroy Brier skill score.

## Causal Decision Response

Selected response: `stop_infeasible_design`.

R2-14C substrate implementation remains blocked. Reserved acceptance seeds (`20271201..20271220`) and the final holdout remain `not_materialized`.
