# Phase 2R.10 v3.1 Candidate Selection

Both frozen candidates use identical governed fit and selection memberships.

| Candidate | Records | ROC AUC | Brier | Log loss |
| --- | ---: | ---: | ---: | ---: |
| logistic | 854 | 0.5075 | 0.1447 | 0.4656 |
| xgboost | 854 | 0.4511 | 0.1451 | 0.4664 |

Selected candidate: `logistic` by `higher_roc_auc`.

This is synthetic candidate-selection evidence only. No acceptance or final-holdout result was created.
