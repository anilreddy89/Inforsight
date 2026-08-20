# Experiments

Record each meaningful experiment with its question, data version, observation boundary, method, result, limitations, and decision. Retain failed and rejected experiments when they explain project direction.

Current machine-readable experiment evidence includes:

- `phase-01-07-synthetic-rate-assessment.json` — deterministic Phase 1 aggregate assessment.
- `phase-02-01-observation-sufficiency.json` — deterministic observation counts, contract boundary, field inventory, limitations, and the Phase 2 proceed-with-limitations decision.
- `phase-02-03-temporal-split-manifest.json` — versioned chronological assignments, embargo accounting, class and billing-frequency distributions, source digest, isolation checks, and the pipeline-engineering-only decision.
- `phase-02-04-feature-pipeline-manifest.json` — training-only preprocessing state, exact fit IDs, frozen output columns, partition shapes and digests, upstream provenance, and the continuing pipeline-engineering-only limitation without raw or transformed rows.
- `phase-02-05-logistic-baseline-manifest.json` — frozen estimator configuration, exact train-only provenance, explicit fitted parameters, train and validation diagnostics, prediction digests, and sealed-test evidence.
- `phase-02-05-logistic-baseline-report.md` — human-readable benchmark configuration, diagnostics, coefficient table, interpretation boundaries, and limitations.

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

The baseline command fits the frozen train matrix and scores train and validation only. The canonical test partition remains sealed.
