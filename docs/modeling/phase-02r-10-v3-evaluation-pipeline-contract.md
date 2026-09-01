# Phase 2R.10 v3 Evaluation Pipeline Implementation Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Phase | R2-10 |
| Implementation issue | [#59](https://github.com/anilreddy89/Inforsight/issues/59) |
| Membership decision | [#60](https://github.com/anilreddy89/Inforsight/issues/60) |
| Remediation decision | [#61](https://github.com/anilreddy89/Inforsight/issues/61) |
| Simulator contract | `3.1.0` |
| Evaluation and candidate-selection membership | `3.2.0` |
| Feature dictionary, feature pipeline, candidates, authorization | `3.0.0` |
| Acceptance protocol | `2.2.0`; execution remains R2-11 work |
| Final release holdout | `not_materialized` |
| Status | Completed through PR #62, merge `36c17b7`, with two successful hosted CI runs |

This contract implements the engineering boundary assigned to R2-10. The issue-#61 amendment is documented in `phase-02r-10-v3-arrears-remediation-contract-3.1.0.md`. Historical simulator contract `3.0.0`, R2-09 identity, the original 467-row support failure, and the invalidated first `3.1.0` attempt remain immutable.

## Frozen implementation

The `inforsight_simulator.v3_evaluation` namespace provides:

- three rolling-origin acceptance folds and the amended July–December selection fold;
- canonical ordering, strict cutoff chronology, full 90-day outcome embargo, and role, policy, and episode isolation;
- fail-closed structural support of at least 500 eligible observations, 50 positives, 50 negatives, all billing frequencies, and zero censoring;
- an exactly-once 17-feature registry, visible-event lineage checks, recursive protected-concept rejection, coefficient transforms, fit-only preprocessing, and frozen unknown-category columns;
- deterministic logistic and XGBoost candidates using identical fit and selection memberships;
- exact AUC, Brier, then logistic tie-breaking and portable fitted-state reload verification; and
- scoring authorization bound to purpose, fold, role, membership, feature names, matrix, target, fit matrix, preprocessing, model, artifact, and contract digests.

Acceptance rows are inspected only for predeclared aggregate support. They do not enter preprocessing, diagnostics, candidate fitting, selection, predictions, or metrics in R2-10.

## Evidence

The authoritative `3.2.0` artifacts are:

```text
docs/experiments/phase-02r-10-v3-structural-support-3.2.0.json
docs/experiments/phase-02r-10-v3-structural-support-3.2.0.md
docs/experiments/phase-02r-10-v3-split-manifest-3.2.0.json
docs/experiments/phase-02r-10-v3-feature-pipeline-manifest-3.2.0.json
docs/experiments/phase-02r-10-v3-feature-diagnostics-manifest-3.2.0.json
docs/experiments/phase-02r-10-v3-feature-diagnostics-report-3.2.0.md
docs/experiments/phase-02r-10-v3-candidate-selection-manifest-3.2.0.json
docs/experiments/phase-02r-10-v3-candidate-selection-report-3.2.0.md
```

All governed memberships pass. The selection membership contains 1,498 eligible episodes from 787 unique policies, including 147 positives and 1,351 negatives. Repeated episodes do not increase independent-policy capacity; policy remains the R2-11 resampling cluster. Diagnostics return `allow`, retain `recent_payment` as the strongest group and `missingness` as the designed-zero group, and give every mechanical flag an explicit disposition. XGBoost is selected by higher ROC AUC (`0.5415` versus `0.5293`); this is synthetic candidate-selection evidence, not acceptance or real-world performance evidence.

## Reproduction and boundaries

```bash
python3 scripts/check_v3_evaluation_support.py --check
python3 scripts/build_v3_evaluation_pipeline.py --write
python3 scripts/build_v3_evaluation_pipeline.py --check
make v3-evaluation-check
```

The build commits only aggregate manifests, reports, portable state digests, and authorization digests. Raw observations, matrices, row-level predictions, executable fitted objects, oracle sidecars, acceptance results, and final-holdout material are not committed. `--check` must reproduce every authoritative byte, while the immutable-evidence check protects the original support failure.

R2-10 enables only R2-11 after merge. It does not authorize calibration, thresholding, explanations, operational action, limitation closure, or any real-world, actuarial, temporal-validation, or release claim.
