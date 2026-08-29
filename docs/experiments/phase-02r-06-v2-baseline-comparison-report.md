# Phase 2R.06 v2 Baseline Comparison

Both frozen candidates use identical governed fit and selection memberships.

| Model | Records | ROC AUC | Log loss | Brier score |
| --- | ---: | ---: | ---: | ---: |
| logistic | 269 | 0.542668 | 0.199702 | 0.046521 |
| xgboost | 269 | 0.551382 | 0.201358 | 0.047316 |

The comparison is synthetic pipeline-engineering evidence only.
The final release holdout remains `not_materialized`.
