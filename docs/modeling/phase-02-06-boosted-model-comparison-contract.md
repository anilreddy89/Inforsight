# Phase 2.06 Boosted-Model Comparison Contract

## Status

| Field | Value |
| --- | --- |
| Phase | Phase 2.06 |
| Tracker ID | `P2-06` |
| Status | Frozen for implementation in issue #26 |
| Candidate library | XGBoost `3.3.0` |
| Fit partition | Exact frozen Phase 2.04 train matrix only |
| Comparison partitions | Train and validation only |
| Test partition | Sealed; scoring remains rejected |
| Decision boundary | `pipeline_engineering_only` |
| Claim-blocking limitation | `LIM-002-001` |

## Purpose

Define one deterministic boosted-tree candidate and compare it with the frozen Phase 2.05 logistic-regression benchmark on identical inputs. This phase evaluates reproducible model-training and comparison mechanics. It does not establish temporal generalization or real-world predictive performance.

## Start gate

Before any candidate is trained or its results are inspected, the Phase 2.06 issue and implementation branch must freeze:

- Exactly one library and a pinned supported version.
- The estimator type and every effective hyperparameter.
- A single random seed and deterministic execution settings.
- The permitted train and validation metrics.
- Safe fitted-state serialization, reconstruction, and compatibility checks.
- Artifact names, schemas, versions, and floating-point normalization rules.

Changing the frozen candidate after inspecting its metrics requires a separately versioned experiment. Phase 2.06 does not conduct a hyperparameter search or compare multiple boosted configurations.

The issue #26 start gate freezes `XGBClassifier` with seed `20260817`, `binary:logistic`, 25 estimators, learning rate `0.1`, depth `2`, minimum child weight `2.0`, no gamma or L1 penalty, L2 penalty `1.0`, unit row and column sampling, unit class weighting, base score `0.5`, the exact CPU tree method, one worker, log-loss evaluation, no early stopping, and verbosity `0`. XGBoost-native JSON model data is the safe fitted-state representation. Published numeric evidence uses the existing 10-decimal artifact boundary; runtime probabilities retain full precision.

## Frozen inputs

The candidate must consume the exact ordered `ModelMatrix` objects produced by the committed Phase 2.04 pipeline:

- Fit only on the frozen train matrix.
- Apply the already-fitted preprocessing state unchanged.
- Preserve ordered feature names and observation identifiers.
- Record the training matrix digest and upstream feature-pipeline manifest digest.
- Reject fitting on validation, test, embargoed, or unknown partitions.
- Reject feature, row-membership, ordering, width, type, or digest mismatches.

The Phase 2.05 logistic benchmark must be reconstructed or regenerated from its committed configuration without changing its estimator, preprocessing, or published evidence.

## Comparison protocol

Both candidates must be evaluated on identical train and validation observation IDs using unrounded positive-class probabilities. The comparison reports:

- Record and class counts.
- Log loss.
- ROC AUC.
- Brier score.
- Average predicted probability.
- Observed positive fraction.
- Deterministic prediction digests.

Validation results may describe the controlled comparison but may not trigger candidate replacement, hyperparameter adjustment, feature changes, resampling, calibration, or threshold selection inside this phase. The report must show both models side by side and record a bounded engineering disposition without declaring production superiority.

## Canonical test seal

The canonical test partition remains sealed throughout Phase 2.06. Candidate and comparison APIs must reject test scoring, and committed artifacts must contain:

- `sealed_not_scored` test status;
- no test metrics;
- no test prediction digest; and
- no test-driven decision.

Test scoring remains deferred until the broader evaluation, calibration, reporting, and limitation-resolution protocol authorizes it. Fixtures may exercise generic scoring mechanics without using canonical test observations.

## Implementation boundaries

Shared metric and prediction-digest logic may be extracted from logistic-specific code into a model-neutral module only if Phase 2.05 manifest and report bytes remain unchanged. Library estimator objects must stay private. Committed fitted state must use explicit, validated, non-executable data rather than pickle, joblib, or another executable object format.

The implementation must provide deterministic `--write` and read-only `--check` commands, focused tests, Makefile integration, and CI coverage. Dependency licensing and third-party notices must be updated for the selected library.

## Required artifacts

Phase 2.06 will publish:

```text
docs/experiments/phase-02-06-boosted-comparison-manifest.json
docs/experiments/phase-02-06-boosted-comparison-report.md
```

The manifest must record candidate configuration, dependency version, upstream digests, exact fit provenance, safe fitted state and digest, convergence or training evidence, model-neutral comparison metrics, prediction digests, test-seal status, and limitations. It must not contain raw observation rows or complete transformed matrices.

## Exclusions

Phase 2.06 does not include:

- Multiple candidate or hyperparameter search.
- Validation-driven feature or preprocessing changes.
- Canonical test scoring.
- Probability calibration.
- Operational threshold selection or capacity analysis.
- SHAP or other explanation publication.
- Temporal-generalization, actuarial, fairness, business-value, or release claims.
- Resolution of `LIM-002-001`.

## Acceptance gate

Phase 2.06 passes only when one predeclared boosted candidate fits deterministically on the exact Phase 2.04 train matrix; both models are compared on identical permitted partitions and metrics; explicit fitted state reproduces candidate predictions without refitting; Phase 2.05 artifacts remain byte-identical; canonical test scoring is rejected and absent from artifacts; dependency, provenance, compatibility, and determinism are auditable; all checks pass; and `LIM-002-001` remains prominent.

Passing this gate authorizes the separate Phase 2.07 feature-sanity and shortcut-diagnostic increment. It does not authorize calibration, threshold selection, test evaluation, temporal-generalization claims, or model release.
