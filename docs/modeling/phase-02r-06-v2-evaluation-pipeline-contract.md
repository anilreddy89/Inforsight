# Phase 2R.06 v2 Evaluation Pipeline Contract

## Frozen versions and specifications

| Boundary | Version |
| --- | --- |
| Evaluation split | `2.0.0` |
| Feature dictionary | `2.0.0` |
| Feature pipeline | `2.0.0` |
| Scoring authorization | `2.0.0` |
| Diagnostics | `2.0.0` |
| Baseline comparison | `2.0.0` |
| Numeric metric normalization | 10 decimal places |
| Native XGBoost JSON normalization | 4 decimal places before committed serialization and reload verification |
| Diagnostic and baseline committed-evidence portability boundary | 4 decimal places; runtime calculations retain full precision |

R2-06 consumes only R2-05 public observations from corpus contract `2.0.0`. The primary target remains lapse-or-surrender in `(as_of, as_of + 90 elapsed days]`. Right-censored observations are accounted for but excluded from fitting and metrics. Protected oracle records are not accepted by this pipeline.

The logistic candidate retains the frozen v1 estimator specification: scikit-learn logistic regression, L2 penalty, `C=1.0`, `liblinear`, tolerance `1e-8`, 1,000 maximum iterations, intercept enabled, no class weights, and seed `20260817`. The boosted candidate retains the frozen v1 XGBoost specification: 25 depth-2 exact-method trees, learning rate `0.1`, minimum child weight `2.0`, unit row and column sampling, L2 `1.0`, one worker, no early stopping, and seed `20260817`. Dependency pins remain `scikit-learn==1.7.2` and `xgboost==3.3.0`. These specifications may not change in response to R2-06 results.

## Membership and chronology

Policy roles assigned by R2-05 are immutable and mutually exclusive. Selection comparison uses eligible `fit` observations through `2024-03-31T23:59:59Z` and eligible `selection` observations from `2024-07-01T00:00:00Z` through `2024-09-30T23:59:59Z`. The gap enforces the full 90-day outcome-horizon embargo. Calibration, non-final evaluation, and R2-acceptance policies remain unavailable to candidate selection.

The three R2-acceptance folds remain exactly those frozen by R2-04. Fold fit rows use only `fit` policies and acceptance rows only `r2_acceptance` policies. Every boundary must prove strict cutoff chronology, no earlier outcome horizon crossing the later start, zero policy overlap, and zero outcome-episode overlap. Caller input order is normalized by `(as_of, policy_id, observation_id)`.

## Features and preprocessing

The machine-readable dictionary is `docs/modeling/phase-02r-06-v2-feature-dictionary.json`. Input must match the exact `V2Features` surface and pass the R2-05 recursive protected-concept validator. Identity, role, cohort, cutoff, horizon, outcome, censoring, label provenance, visible event IDs, generator state, latent values, and oracle values remain sidecars.

Numeric fields use fit-only mean and population-standard-deviation scaling, with scale `1.0` for a fit constant. Categorical fields use sorted fit-only vocabularies plus a predeclared `__unknown__` column. Nullable payment delay uses a deterministic zero fill paired with its approved missingness indicator. No held-out row may change fitted state, output width, feature names, or category vocabulary.

## Scoring authority and model comparison

Authorization binds version, purpose, fold, role, ordered observation membership, feature names, complete labeled-matrix digest, training-matrix digest, and fitted-preprocessor digest. A caller-editable partition or role label is not authority. Relabeling, substitution, reordering, cross-fold use, feature/target mutation, or digest tampering must fail before prediction.

Both candidates fit the identical governed fit matrix and compare on the identical governed selection matrix. Metrics are record and class counts, log loss, ROC AUC, Brier score, average predicted probability, and observed positive fraction. No tuning, retry, resampling, feature selection, calibration, or threshold selection is permitted.

## Diagnostics and dispositions

R2-06 reports category support, missingness, fit constants, near constants, identifier-token checks, and one-feature association screens. Every flag receives exactly one `allow`, `exclude`, `investigate`, or `redesign` disposition. Full multi-seed null-signal, label-shuffle, signal-recovery, learning-curve, uncertainty, and robustness decisions remain R2-07 work.

## Artifact and holdout boundary

All R2-06 artifacts include `phase-02r-06-v2`, bind the R2-05 public-observation digest and stable downstream contract, membership, preprocessing, and authorization digests, use finite canonical JSON, and exclude raw observations, full matrices, protected sidecars, and executable serialized objects. Existing v1 artifacts must remain unchanged. Because native solver and tree bytes are not cross-platform stable, explicit logistic and XGBoost state is regenerated and reload-verified at runtime but is not committed. The portable baseline manifest records specifications, membership and matrix lineage, convergence/tree-count evidence, reload success, and four-decimal metrics without platform-specific parameter or prediction hashes.

The final release holdout status is `not_materialized`. R2-06 must not choose its seed, generate membership, inspect distributions, build features, transform, predict, or score it. Passing R2-06 authorizes only execution of the frozen R2-07 acceptance protocol.
