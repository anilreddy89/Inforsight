# Phase 2R.06 v2 Baseline Comparison

Both frozen candidates use identical governed fit and selection memberships.

| Model | Records | ROC AUC | Log loss | Brier score |
| --- | ---: | ---: | ---: | ---: |
| logistic | 269 | 0.542700 | 0.199700 | 0.046500 |
| xgboost | 269 | 0.551400 | 0.201400 | 0.047300 |

The comparison is synthetic pipeline-engineering evidence only.
The final release holdout remains `not_materialized`.
