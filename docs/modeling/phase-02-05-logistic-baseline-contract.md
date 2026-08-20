# Phase 2.05 Seeded Logistic-Regression Baseline Contract

## Status

| Field | Value |
| --- | --- |
| Baseline-model version | `1.0.0` |
| Training-configuration version | `1.0.0` |
| Fit partition | Frozen Phase 2.04 train matrix only |
| Diagnostic partitions | Train and validation only |
| Test partition | Sealed; scoring is rejected |
| Decision | `pipeline_engineering_only` |
| Claim-blocking limitation | `LIM-002-001` |

## Purpose and boundary

This contract defines one transparent, deterministic logistic-regression benchmark. It consumes the exact ordered numeric matrix produced by Phase 2.04, fits on train only, reports predeclared train and validation diagnostics, and serializes explicit fitted parameters without executable model objects.

This phase does not tune a model, compare candidate algorithms, score the canonical test partition, calibrate probabilities, select an operational threshold, or authorize temporal-generalization, actuarial, fairness, customer-impact, or release claims.

## Frozen estimator

The version `1.0.0` configuration is fixed before model results are inspected:

| Parameter | Value |
| --- | --- |
| Estimator | `sklearn.linear_model.LogisticRegression` |
| Dependency | `scikit-learn==1.7.2` |
| Penalty | L2 |
| Regularization strength `C` | `1.0` |
| Solver | `liblinear` |
| Tolerance | `1e-8` |
| Maximum iterations | `1000` |
| Intercept | Enabled |
| Class weight | None |
| Random seed | `20260817` |

Alternative solvers, penalties, regularization values, class weighting, resampling, or retries based on observed metrics require a separately versioned experiment and are outside this phase. A convergence warning is an error rather than permission to alter the frozen configuration silently.

## Input validation and fit provenance

The fit API accepts only a `ModelMatrix` whose partition is exactly `train`. It requires nonempty, unique observation and feature names; aligned sidecars; rectangular finite numeric inputs; integer binary targets containing both classes; and the exact Phase 2.04 feature order.

Fitted state records the exact training observation IDs, training matrix SHA-256 digest, ordered feature names, contract versions, dependency version, estimator specification, intercept, coefficients, and iteration count. Validation and test rows never enter fitting. Phase 2.04 preprocessing is neither reconstructed nor refit by the model API.

## Scoring and sealed test

Only train and validation matrices may be scored. The scoring API rejects `test` and unknown partitions. Train rescoring additionally requires exact fitted membership and matrix digest equality. Every score is the positive-class probability for target `1`; estimator class order must be exactly `(0, 1)` during fitting.

The canonical artifact command never transforms or scores the test matrix through the model API. Its manifest records `sealed_not_scored` and contains no test metrics or prediction digest. Test evaluation remains deferred until the comparison and evaluation protocol is frozen.

## Predeclared diagnostics

Train and validation report:

- Record and class counts.
- Log loss.
- ROC AUC.
- Brier score.
- Average predicted probability.
- Observed positive fraction.

Metrics use unrounded probabilities. Both classes are required. No result is used to modify the estimator, preprocessing, calibration, or a threshold. A fixed classification threshold is intentionally omitted.

## Coefficients and interpretation

Every coefficient is bound positionally to the frozen Phase 2.04 feature name. The manifest also provides `exp(coefficient)` as a derived odds ratio. Numeric inputs are standardized and categorical inputs are frozen one-hot columns, including unknown-category columns.

These values describe associations inside a small, engineered synthetic corpus. Correlation, standardization, regularization, category confounding, and limited support prevent causal interpretation. Coefficients do not authorize customer contact or policy action.

## Safe explicit artifact

The fitted model is represented as canonical JSON-compatible values, not pickle, joblib, or another executable serialization format. Prediction reconstruction applies the stored intercept and coefficients using a numerically stable sigmoid. Loading fails for unsupported model, configuration, feature-contract, or scikit-learn versions; malformed, non-finite, incomplete, or misaligned state also fails closed.

The committed manifest includes upstream artifact digests, fitted-state digest, complete configuration and provenance, coefficient mapping, convergence evidence, permitted metrics, prediction digests, test-seal status, and limitations. It does not contain raw observation records or transformed row-level matrices. Floating-point artifact values and prediction-digest inputs are rounded to 10 decimal places before canonical serialization so insignificant platform-level solver differences do not create false drift; runtime scoring retains full precision.

## Deterministic artifacts

Run:

```bash
python3 scripts/train_logistic_baseline.py --write
python3 scripts/train_logistic_baseline.py --check
```

`--check` is read-only and fails for a missing or stale manifest or report. Repeated runs on a compatible environment must reproduce fitted parameters, prediction digests, and canonical artifact bytes.

## Acceptance boundary

Phase 2.05 passes when the exact frozen training matrix deterministically produces one compatible fitted baseline; explicit state reconstructs train and validation predictions without refitting; test scoring is rejected and absent from artifacts; coefficient alignment, convergence, failure behavior, and diagnostics are tested; all repository checks pass; and `LIM-002-001` remains prominent.

Passing this contract permits a separately frozen boosted-tree candidate and validation-protocol comparison. It does not permit test evaluation, calibration, threshold selection, temporal-generalization claims, or model release.
