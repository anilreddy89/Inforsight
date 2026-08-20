# Phase 2.06 Boosted-Model Comparison Report

## Decision

The frozen XGBoost candidate and Phase 2.05 logistic benchmark were compared reproducibly on identical train and validation observations. This is a `pipeline_engineering_only` result, not a declaration of production superiority. `LIM-002-001` remains unresolved, and the canonical test partition stayed `sealed_not_scored`.

## Frozen candidate

- Library: XGBoost `3.3.0`
- Estimator: `XGBClassifier`
- Trees, learning rate, maximum depth: `25`, `0.1`, `2`
- Minimum child weight and L2 penalty: `2.0`, `1.0`
- Tree method and workers: `exact`, `1`
- Seed: `20260817`
- Row and column sampling: `1.0` (no stochastic subsampling)
- Early stopping: disabled
- Fit partition: train only

## Predeclared comparison

| Partition | Model | Records | Positive | Log loss | ROC AUC | Brier score | Mean prediction | Observed fraction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | Logistic regression | 26 | 13 | 0.652595 | 0.642012 | 0.230997 | 0.499813 | 0.500000 |
| Train | XGBoost | 26 | 13 | 0.623910 | 0.739645 | 0.216213 | 0.503449 | 0.500000 |
| Validation | Logistic regression | 27 | 15 | 0.689351 | 0.563889 | 0.248559 | 0.550038 | 0.555556 |
| Validation | XGBoost | 27 | 15 | 0.704890 | 0.533333 | 0.255776 | 0.502328 | 0.555556 |

These values were not used to replace or tune the candidate, change features or preprocessing, calibrate probabilities, or select a threshold.

## Engineering disposition

The implementation demonstrates deterministic train-only fitting, native JSON model reconstruction, identical comparison membership and metrics, stable prediction digests, and enforcement of the canonical test seal. With only 26 monthly training observations and a semiannual-only validation partition, metric differences cannot establish that either model is generally superior.

## Limitations

- Billing frequency is confounded with observation time under `LIM-002-001`.
- The balanced fictional outcome mix is not a prevalence estimate.
- No test result, calibration assessment, operational threshold, fairness conclusion, or release claim is provided.
- XGBoost model behavior in this engineered corpus is not authority for customer action.

## Reproduction

```bash
python3 scripts/train_boosted_comparison.py --check
```
