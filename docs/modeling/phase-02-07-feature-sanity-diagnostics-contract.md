# Phase 2.07 Feature-Sanity and Shortcut-Diagnostics Contract

## Status

| Field | Value |
| --- | --- |
| Phase | Phase 2.07 |
| Tracker ID | `P2-07` |
| Issue | [#28](https://github.com/anilreddy89/Inforsight/issues/28) |
| Status | Implemented locally for issue #28; awaiting pull request and merge |
| Diagnostic configuration | `1.0.0` |
| Seed | `20260817` |
| Fit partition | Exact frozen Phase 2.04 train matrix only |
| Scoring partition | Exact frozen Phase 2.04 validation matrix only |
| Test partition | Sealed; all diagnostic access is rejected |
| Decision boundary | `pipeline_engineering_only` |
| Claim-blocking limitation | `LIM-002-001` |

## Purpose

Define deterministic feature-sanity diagnostics that can reveal identifiers, excessive cardinality, constants, deterministic simulator shortcuts, and unexpectedly dominant feature groups without treating association or predictive strength alone as proof of leakage.

## Frozen inputs and grouping

Diagnostics consume the exact ordered matrices produced by the Phase 2.04 feature pipeline. Observation identifiers and targets remain audit sidecars and never become diagnostic inputs. Numeric output columns map to the same-named source feature. One-hot columns map to the source name before the first `=`; all categories, including `__unknown__`, are reviewed as one source-feature group.

The implementation must validate partition name, membership, ordering, feature names, width, values, targets, and matrix digest. Only `train` and `validation` are permitted. Test, embargoed, and unknown partitions are rejected.

## Frozen diagnostic configuration

- Dependency: scikit-learn `1.7.2` (already pinned).
- Seed: `20260817`.
- Artifact numeric boundary: 10 decimal places; runtime calculations retain full precision.
- Mutual information: `mutual_info_classif`, train only, `n_neighbors=3`, fixed random state; one-hot outputs are discrete and scaled numeric outputs are continuous. A source group receives the maximum output-column score.
- Shallow model: one `DecisionTreeClassifier(max_depth=1, criterion="log_loss", splitter="best", min_samples_leaf=2, random_state=20260817)` per source group, fit on train and scored on validation.
- Shallow metrics: log loss, ROC AUC, Brier score, and deterministic prediction digest.
- Cardinality: evaluate group row-pattern cardinality in train and validation; flag a nonconstant group when its training uniqueness ratio is at least `0.90`.
- Constancy: flag a group with one unique training row pattern. Flag near constancy when the most common training row pattern represents at least `0.95` but less than `1.0` of training rows.
- Identifier tokens: case-insensitive token matching for `id`, `uuid`, `guid`, `key`, `index`, `row`, `policy`, `observation`, `customer`, `account`, and `scenario` across source and output names. Exact reviewed source names take precedence over incidental substrings.
- Strong mutual-information screen: flag a source-group maximum of at least `0.50`.
- Strong shallow-model screen: flag validation ROC AUC of at least `0.90` or validation log loss of at most `0.40`.
- Targeted perturbation: deterministically permute all columns in a mechanically flagged group with one shared seeded row order, then score the unchanged frozen logistic and XGBoost models on validation.
- Material perturbation screen: flag an absolute ROC-AUC change of at least `0.10` or a log-loss increase of at least `0.10` for either model.

These screens prioritize review; they do not establish leakage. Small-sample instability, synthetic construction, and billing-frequency/time confounding must be considered in every disposition.

## Disposition rules

Each mechanically flagged source group must have exactly one decision:

- `allow`: temporally valid, contract-approved evidence with a documented non-leakage explanation;
- `exclude`: confirmed identifier, post-cutoff input, terminal-outcome proxy, simulator marker, or other contract violation; or
- `investigate`: suspicious or unstable evidence that is insufficient for exclusion.

Every decision records its flag IDs, rationale, owner, date, and follow-up. An `exclude` requires a separately versioned feature-pipeline change and downstream model regeneration. An `investigate` requires a follow-up issue or an explicit limitation disposition before the Phase 2 evaluation gate.

## Artifact boundary

Publish:

```text
docs/experiments/phase-02-07-feature-diagnostics-manifest.json
docs/experiments/phase-02-07-feature-diagnostics-report.md
```

The artifacts record configuration, upstream digests, permitted membership and matrix digests, source grouping, diagnostics, flags, dispositions, immutability evidence, and `sealed_not_scored`. They must not contain raw observations, complete transformed matrices, test evidence, or executable fitted state.

## Exclusions

This phase does not change features, refit preprocessing or frozen models in response to results, tune thresholds, calibrate probabilities, select operational thresholds, publish SHAP explanations, inspect test data, resolve `LIM-002-001`, or make temporal-generalization, actuarial, fairness, production, or customer-action claims.

## Acceptance gate

Phase 2.07 passes only when diagnostics reproduce byte for byte; all flagged source features have valid dispositions; test access is rejected; prior pipeline and model artifacts remain byte-identical; focused and repository checks pass; and the report clearly distinguishes screening evidence from leakage conclusions.
