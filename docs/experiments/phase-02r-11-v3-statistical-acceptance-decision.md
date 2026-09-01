# Phase 2R.11 Decision

Decision: `redesign`.

The decision is mechanical under protocol `2.2.0`. Readiness passed for all 20 signal/null pairs, but zero signal replications met the required median-fold AUC threshold and zero met the required matched-null improvement threshold. The across-seed median signal AUC also failed its frozen threshold.

No `stop` condition was observed. Unexecuted required families are recorded as incomplete `redesign` failures; they are not treated as passes or waived.

P2-08 and P2-09 remain paused. A new reviewed redesign must own any simulator, feature, candidate, or protocol change before another acceptance run. The final release holdout remains `not_materialized`.
