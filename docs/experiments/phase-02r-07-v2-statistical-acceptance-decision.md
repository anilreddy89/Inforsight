# Phase 2R.07 Decision

Decision: `stop`.

The decision is mechanical under protocol `1.0.0`: the structural readiness audit found that cutoff features contain behavior values whose owning event was ingested after the cutoff and was absent from the observation's visible-event membership. Leakage is a `stop` condition and takes precedence over the independent `redesign` findings.

Failed stop rules: `READINESS-DUAL-TIME-VISIBILITY`.
All failed readiness rules: `READINESS-SELECTED-CANDIDATE`, `READINESS-DRIVER-GROUPS`, `READINESS-COEFFICIENT-REGISTRY`, `READINESS-MATCHED-NULL-STREAMS`, `READINESS-MATCHED-STRESS-STREAMS`, `READINESS-SHUFFLE-DOMAIN`, `READINESS-FOLD-SUPPORT`, `READINESS-DUAL-TIME-VISIBILITY`.

No R2-07 statistical acceptance run occurred. No model was fitted, no predictions or metrics were produced, and the final holdout remains `not_materialized`.

P2-08 and P2-09 remain paused. A focused corrective issue must repair the dual-time feature boundary and own the versioned matched-control/protocol redesign before acceptance execution can resume. `LIM-002-001` through `LIM-002-004` remain open.
