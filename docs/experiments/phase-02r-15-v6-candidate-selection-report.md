# Phase 2R.15 Generation v6 Candidate Selection

Both frozen candidates use identical governed fit and selection memberships.

| Candidate | Records | ROC AUC | Brier | Log loss |
| --- | ---: | ---: | ---: | ---: |
| logistic | 996 | 0.7057 | 0.1287 | 0.4168 |
| xgboost | 996 | 0.6801 | 0.1354 | 0.4377 |

Selected candidate: `logistic` by `higher_roc_auc`.

This is synthetic candidate-selection evidence only. No acceptance or final-holdout result was created.
