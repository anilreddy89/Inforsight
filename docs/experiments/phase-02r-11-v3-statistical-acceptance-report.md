# Phase 2R.11 v3 Statistical Acceptance Report

Decision: `redesign`.

All 20 signal/null pairs passed readiness across all three governed folds. Authorized primary scoring then failed the frozen signal-recovery rules.

## Primary results

- Seeds meeting median-fold AUC `>= 0.65`: `0/20` (required `16/20`).
- Across-seed median signal AUC: `0.518869` (required `>= 0.68`).
- Seeds meeting matched-null improvement `>= 0.10`: `0/20` (required `16/20`).
- Median matched-null improvement: `0.016097`.
- Median average-precision lift: `0.009834` (required `>= 0.10`).
- Median Brier skill: `-0.011851` (required positive).

The XGBoost and logistic null-control median AUC rules pass, but interval coverage and later protocol families were not run after the decisive recovery failure. Those required items are explicitly failed as incomplete and independently require `redesign`.

Failed redesign rules: `14`. Failed stop rules: `0`.

No raw matrix, row-level prediction, oracle sidecar, bootstrap sample, executable fitted object, or final holdout was committed. P2-08 and P2-09 remain paused.
