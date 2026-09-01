# Phase 2R.10 v3.2 Candidate Selection

Both frozen candidates use identical governed fit and selection memberships.

| Candidate | Records | ROC AUC | Brier | Log loss |
| --- | ---: | ---: | ---: | ---: |
| logistic | 1498 | 0.5293 | 0.0885 | 0.3214 |
| xgboost | 1498 | 0.5415 | 0.0891 | 0.3240 |

Selected candidate: `xgboost` by `higher_roc_auc`.

This is synthetic candidate-selection evidence only. No acceptance or final-holdout result was created.
