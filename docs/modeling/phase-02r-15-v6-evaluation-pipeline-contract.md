# Phase 2R.15 Generation v6 Evaluation Pipeline Implementation Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Phase | R2-15 |
| Implementation issue | [#90](https://github.com/anilreddy89/Inforsight/issues/90) |
| Simulator contract | `6.0.0` |
| Evaluation and candidate-selection membership | `6.0.0` |
| Feature dictionary, feature pipeline, candidates, authorization | `6.0.0` |
| Coefficient registry | `3.0.0` |
| Acceptance protocol | `3.0.0`; execution remains R2-16 work |
| Final release holdout | `not_materialized` |
| Status | In progress under Issue #90 |

This contract implements the engineering boundary assigned to R2-15. Generation v6 Substrate Contract `6.0.0`, Coefficient Registry `3.0.0`, and qualification evidence from Phase 2R.14D (PR #89, `89ec94a`) govern this evaluation pipeline. All historical artifacts from v1 through v5 remain immutable.

## Frozen implementation

The `inforsight_simulator.v6_evaluation` namespace provides:

- Three rolling-origin temporal acceptance folds (`fold_1`, `fold_2`, `fold_3`) and the designated candidate selection fold (`selection`);
- Canonical ordering, strict cutoff chronology, full 90-day outcome embargo, and role, policy, and episode isolation;
- Fail-closed structural support of at least 500 eligible observations, 50 positives, 50 negatives, all four billing frequencies, and zero right-censoring;
- An exactly-once 17-feature registry, visible-event lineage checks, recursive protected-concept rejection, coefficient transforms, fit-only preprocessing, and frozen unknown-category columns;
- Deterministic Logistic Regression and XGBoost candidates using identical fit and selection memberships;
- Exact ROC AUC, Brier score, then logistic tie-breaking and portable fitted-state reload verification; and
- Scoring authorization cryptographically bound to purpose, fold, role, membership, feature names, matrix, target, fit matrix, preprocessing, model, artifact, and contract digests.

Acceptance rows are inspected only for predeclared aggregate support. They do not enter preprocessing, diagnostics, candidate fitting, selection, predictions, or metrics in R2-15.

## Evidence artifacts

The authoritative `6.0.0` artifacts are:

```text
docs/experiments/phase-02r-15-v6-structural-support.json
docs/experiments/phase-02r-15-v6-structural-support.md
docs/experiments/phase-02r-15-v6-split-manifest.json
docs/experiments/phase-02r-15-v6-feature-pipeline-manifest.json
docs/experiments/phase-02r-15-v6-feature-diagnostics-manifest.json
docs/experiments/phase-02r-15-v6-feature-diagnostics-report.md
docs/experiments/phase-02r-15-v6-candidate-selection-manifest.json
docs/experiments/phase-02r-15-v6-candidate-selection-report.md
```

## Reproduction and boundaries

```bash
python3 scripts/check_v6_evaluation_support.py --check
python3 scripts/build_v6_evaluation_pipeline.py --write
python3 scripts/build_v6_evaluation_pipeline.py --check
make v6-evaluation-check
```

The build commits only aggregate manifests, reports, portable state digests, and authorization digests. Raw observations, matrices, row-level predictions, executable fitted objects, oracle sidecars, acceptance results, and final-holdout material are not committed. `--check` must reproduce every authoritative byte.

R2-15 enables only R2-16 after merge. It does not authorize calibration, thresholding, explanations, operational action, limitation closure, or any real-world, actuarial, temporal-validation, or release claim.
