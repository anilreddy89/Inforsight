# Phase 2.04 Feature Pipeline and Training-Only Preprocessing Contract

## Status

| Field | Value |
| --- | --- |
| Feature-pipeline version | `1.0.0` |
| Feature-dictionary version | `1.0.0` |
| Input | Guarded Phase 2.01 observation features assigned by Phase 2.03 |
| Fit partition | Train only |
| Apply partitions | Frozen train, validation, and test memberships |
| Decision | `pipeline_engineering_only` |
| Claim-blocking limitation | `LIM-002-001` |

## Purpose

This contract defines the deterministic boundary between frozen observation records and later model training. It makes feature decisions explicit, separates stateless validation from learned preprocessing, and prevents validation or test data from changing learned parameters or the model-input schema.

It does not train a model, resample rows, calibrate probabilities, select thresholds, or authorize temporal-generalization claims.

## Input boundary

The pipeline consumes a validated `TemporalSplitResult`. Only the existing `train`, `validation`, and `test` dispositions may become model matrices. Embargoed, calendar-gap, excluded, ineligible, right-censored, null-label, and otherwise non-modeling records cannot enter this boundary.

Each accepted record must:

- Use the supported upstream contract and generator versions already enforced by temporal splitting.
- Be eligible with a non-null feature payload.
- Have label status `observed_negative` or `observed_positive` and target `0` or `1`.
- Contain exactly the 12 keys approved by the Phase 2.02 feature guard.
- Pass recursive leakage validation before extraction.
- Contain non-empty strings and nonnegative integer numeric values; booleans are not accepted as integers.

`observation_id` is retained only as an audit sidecar. Policy identity, cutoff timestamps, visible event IDs, labels, outcomes, label provenance, split names, and simulator construction metadata never become feature columns.

## Feature dictionary

The canonical machine-readable dictionary is `docs/modeling/phase-02-04-feature-dictionary.json`. Its 12 source entries must exactly match `ALLOWED_FEATURE_KEYS`; regeneration or tests fail if either surface drifts independently.

Version `1.0.0` makes these explicit decisions:

| Decision | Source features |
| --- | --- |
| Training-fitted z-score | Premium cents, policy age, and all six visible event counts |
| Training-fitted one-hot encoding | Product variant and billing frequency |
| Excluded as constant | Current status and currency |
| Missingness | Reject every missing or null value; no imputer is fit |
| Selection | No learned selector |

Premium remains in exact integer cents through stateless validation. No lossy currency conversion is performed.

## Stateless and learned stages

Stateless extraction:

1. Revalidates the feature dictionary and guarded payload.
2. Checks exact keys, types, nullability, and nonnegative numeric constraints.
3. Selects only fields marked `included`.
4. Returns identity and target as sidecars separate from the selected values.

Learned preprocessing:

1. Receives the already-frozen temporal split.
2. Reads only train rows when calculating parameters.
3. Fits population mean and population standard deviation for each numeric field.
4. Uses scale `1.0` when training variance is zero.
5. Fits sorted distinct training categories for each categorical field.
6. Appends a predeclared `__unknown__` category to every categorical output block.
7. Freezes parameter order, category order, partition membership, and output names in an immutable value object.

Output columns place numeric z-scores first in feature-dictionary order, followed by categorical one-hot blocks in feature-dictionary and category order.

## Unknown categories and missingness

An application value found in the fitted training vocabulary activates its named one-hot column. Any other non-empty string activates the predeclared `source_name=__unknown__` column and cannot expand the output schema.

This behavior is material for the canonical split: train contains monthly billing only, validation contains semiannual billing only, and test contains annual billing only. Semiannual and annual therefore map to the frozen billing-frequency unknown column.

Unknown handling makes transformation safe but does not resolve the time/frequency confounding in `LIM-002-001`. Missing values are different from unseen valid categories and fail closed in version `1.0.0`.

## Fit and apply lifecycle

`fit_preprocessor` accepts a complete validated `TemporalSplitResult`; callers cannot designate validation or test as the fitting partition. The fitted state records exact ordered observation IDs for train, validation, and test.

`transform_partition` accepts only `train`, `validation`, or `test`, and supplied IDs and order must exactly match the frozen membership. Transformation is pure with respect to the frozen fitted object. Canonical fitted-state bytes before and after validation and test application must be identical.

Changing held-out feature values while preserving valid membership cannot change fitted state. Changing a relevant training value must change the corresponding training-derived statistic. Both properties are tested.

## Output contract

A `ModelMatrix` contains the partition name, ordered observation-ID sidecar, frozen ordered feature names, a rectangular tuple of numeric feature rows, and an ordered binary-target sidecar. Identity and targets are deliberately not interleaved with matrix values.

## Deterministic artifacts

Run:

```bash
python3 scripts/build_feature_pipeline.py --write
python3 scripts/build_feature_pipeline.py --check
```

The command regenerates canonical observations and temporal assignments, fits on train, transforms the modeling partitions, and maintains:

- `docs/modeling/phase-02-04-feature-dictionary.json`
- `docs/experiments/phase-02-04-feature-pipeline-manifest.json`

Both use sorted, indented UTF-8 JSON with a trailing newline. The manifest records upstream versions and digests, exact training IDs, fitted numeric statistics, fitted categorical vocabularies, frozen output names, shapes, deterministic matrix digests, and limitations. It does not contain raw feature rows or transformed matrices.

The fitted state is represented as explicit JSON-compatible values instead of an executable pickle. A SHA-256 digest binds that state in the manifest.

## Failure behavior

The pipeline fails closed for feature-dictionary drift, unsupported versions, invalid values, ineligible or non-binary records, duplicate IDs, unsupported dispositions, partition identity or ordering drift, inconsistent fitted state, transformed-width drift, and missing or stale artifacts.

## Acceptance boundary

Phase 2.04 is complete when the dictionary and artifacts regenerate exactly; train alone determines learned state; held-out changes cannot alter that state; unseen categories cannot change output width; prohibited data remains outside matrix values; focused and repository-wide tests pass; and `LIM-002-001` remains visible.

Passing this contract permits the next phase to fit a seeded logistic-regression benchmark to these frozen inputs. It does not permit test-guided iteration, calibration, threshold selection, release approval, or real-world performance claims.
