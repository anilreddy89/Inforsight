# Experiments

Record each meaningful experiment with its question, data version, observation boundary, method, result, limitations, and decision. Retain failed and rejected experiments when they explain project direction.

Current machine-readable experiment evidence includes:

The Phase 2.05 through Phase 2.07 files below are immutable historical v1 pipeline evidence. Their recorded `sealed_not_scored` state describes the artifact-generation runs at the time. Independent review after Phase 2.07 later generated predictions from the v1 test fixture through a partition-relabeling bypass; no test metric was computed. R2-03 repaired the local scoring boundary through issue #39 and PR #40 without changing these artifacts. The fixture remains review-exposed historical evidence, while the future one-shot holdout obligation remains governed by `LIM-002-003`.

- `phase-01-07-synthetic-rate-assessment.json` — deterministic Phase 1 aggregate assessment.
- `phase-02-01-observation-sufficiency.json` — deterministic observation counts, contract boundary, field inventory, limitations, and the Phase 2 proceed-with-limitations decision.
- `phase-02-03-temporal-split-manifest.json` — versioned chronological assignments, embargo accounting, class and billing-frequency distributions, source digest, isolation checks, and the pipeline-engineering-only decision.
- `phase-02-04-feature-pipeline-manifest.json` — training-only preprocessing state, exact fit IDs, frozen output columns, partition shapes and digests, upstream provenance, and the continuing pipeline-engineering-only limitation without raw or transformed rows.
- `phase-02-05-logistic-baseline-manifest.json` — frozen estimator configuration, exact train-only provenance, explicit fitted parameters, train and validation diagnostics, prediction digests, and sealed-test evidence.
- `phase-02-05-logistic-baseline-report.md` — human-readable benchmark configuration, diagnostics, coefficient table, interpretation boundaries, and limitations.
- `phase-02-06-boosted-comparison-manifest.json` — frozen XGBoost configuration, native JSON fitted state, exact train-only provenance, identical model-comparison membership, prediction digests, and sealed-test evidence.
- `phase-02-06-boosted-comparison-report.md` — bounded train and validation comparison with configuration, metrics, engineering disposition, and claim limitations.
- `phase-02-07-feature-diagnostics-manifest.json` — frozen diagnostic configuration, source-feature grouping, train-only mutual information, validation-scored shallow models, identifier/cardinality screens, targeted permutation evidence, flags, dispositions, upstream digests, and sealed-test evidence.
- `phase-02-07-feature-diagnostics-report.md` — human-readable feature-sanity results, governed dispositions, integrity checks, and interpretation boundaries.
- `phase-02r-05-v2-corpus-manifest.json` — deterministic non-final v2 corpus provenance, structural counts, role and billing-frequency coverage, protected-sidecar digest, and `not_materialized` final-holdout evidence.
- `phase-02r-06-v2-*.json` and `phase-02r-06-v2-*.md` — governed chronological folds, fit-only v2 preprocessing, diagnostics, frozen baseline comparison, complete lineage, and `not_materialized` final-holdout evidence.
- `phase-02r-07-v2-statistical-acceptance-*` — fail-closed readiness evidence, complete planned seed/fold accounting, a mechanical `stop` decision for post-cutoff ingestion leakage, independent redesign findings, and confirmation that no statistical run or final-holdout access occurred.

Regenerate or verify the Phase 2R.06 evidence with:

```bash
python3 scripts/build_v2_evaluation_pipeline.py --write
python3 scripts/build_v2_evaluation_pipeline.py --check
```

Run or verify the Phase 2R.07 readiness decision evidence with:

```bash
python3 scripts/run_v2_statistical_acceptance.py --write
python3 scripts/run_v2_statistical_acceptance.py --check
```

The R2-07 command is deliberately a fail-closed readiness preflight. It records the protocol
`1.0.0` decision `stop` before model fitting because the structural audit detects post-cutoff
ingestion leakage. It also records independent redesign blockers in the matched-control identity,
candidate-selection, driver-group, coefficient-registry, shuffle-domain, and fold-support
boundaries. It does not run acceptance metrics or materialize a final release holdout.

Regenerate or verify the Phase 2.04 evidence with:

```bash
python3 scripts/build_feature_pipeline.py --write
python3 scripts/build_feature_pipeline.py --check
```

Regenerate or verify the Phase 2.05 evidence with:

```bash
python3 scripts/train_logistic_baseline.py --write
python3 scripts/train_logistic_baseline.py --check
```

The baseline command reproduces the historical Phase 2.05 run: it fits the frozen train matrix and scores train and validation only. It does not make the later review-exposed v1 fixture an untouched release holdout.

Regenerate or verify the Phase 2.06 evidence with:

```bash
python3 scripts/train_boosted_comparison.py --write
python3 scripts/train_boosted_comparison.py --check
```

The comparison command fits the single issue-#26 XGBoost candidate on train only and compares it with the unchanged logistic benchmark on identical train and validation observations. It does not score test, tune the candidate, calibrate probabilities, or select a threshold.

Regenerate or verify the Phase 2.07 evidence with:

```bash
python3 scripts/run_feature_diagnostics.py --write
python3 scripts/run_feature_diagnostics.py --check
```

The diagnostic command computes mutual information from train only, fits shallow source-feature models on train and scores validation, and perturbs only mechanically flagged validation feature groups against unchanged frozen models. It rejects canonical test access and does not change features, refit preprocessing, tune models, calibrate probabilities, or select a threshold.

Regenerate or verify the R2-05 v2 corpus evidence with:

```bash
python3 scripts/build_v2_modeling_corpus.py
python3 scripts/build_v2_modeling_corpus.py --check
```

The R2-05 command verifies the approved non-final synthetic corpus and protected oracle-sidecar digests. It does not create temporal model folds, fit a model, run R2-07, or materialize a final release holdout.
