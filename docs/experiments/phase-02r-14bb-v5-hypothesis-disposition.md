# Phase 2R.14BB v5 Redesign Hypothesis Disposition

Dispositions derived strictly mechanically under Contract `1.1.0` truth tables:

- `H1_LOG_HAZARD_SPREAD`: `supported` (observable public score spread is insufficient; std < 0.35)
- `H2_HORIZON_ATTENUATION`: `unresolved`
- `H3_PROBABILITY_SCALE`: `rejected` (rank failure; AUC < 0.60 across >= 80% of units)
- `H4_REFERENCE_SPECIFICATION`: `rejected` (reference vs oracle delta < 0.02; reference specification is sound)
- `H5_HAZARD_TAIL`: `rejected` (zero exceedances >= 0.20)
- `H6_DESIGN_FEASIBILITY`: `infeasible` (0/320 cells satisfy simultaneous constraints)

**Causal response**: `stop_infeasible_design`. R2-14C remains blocked; reserved acceptance and final holdout remain `not_materialized`.
