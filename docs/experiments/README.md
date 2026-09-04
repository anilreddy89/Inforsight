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
- `phase-02r-09-v3-corpus-manifest.json` — deterministic non-final v3 event-first corpus provenance, structural counts, dual-time/lineage invariants, protected-sidecar digests, random-stream registry identity, and `not_materialized` final-holdout evidence.
- `phase-02r-10-v3-structural-support.json` and `.md` — immutable pre-amendment `3.0.0` evidence of governed fold support and the retained 467-row selection-support failure. Their bytes and digests remain fixed under issue #60.
- `phase-02r-10-v3.1-pre-remediation-disposition.json` and `phase-02r-10-v3-*-3.1.0.*` — retained, digest-bound evidence of the invalidated first attempt; these files cannot authorize R2-11.
- `phase-02r-10-v3-*-3.2.0.*` — authoritative issue-#61 structural, split, fit-only preprocessing, diagnostic, candidate-selection, portable-state, and scoring-authorization evidence under simulator contract `3.1.0`, evaluation membership `3.2.0`, and protocol `2.2.0`.
- `phase-02r-11-v3-statistical-acceptance-*` — issue-#64 readiness and authorized 20-seed primary evidence plus the mechanical `redesign` decision. All seed pairs pass structural readiness, but `0/20` pass the signal-AUC and matched-null-improvement recovery counts. Required later families not run after the decisive recovery failure are explicitly failed as incomplete rather than waived.

- `phase-02r-13-v4-redesign-diagnostic-*` — merged issue-#69/PR-#70 aggregate evidence for all 20 development seeds. Observable-oracle separation and rolling-payment support are supported failure mechanisms; parity, episode dilution, and temporal instability are rejected; candidate learning remains unresolved. Future acceptance and the final holdout remain `not_materialized`.
- `phase-02r-14-v4-qualification-*` — issue-#72 aggregate development evidence for all 20 frozen v4 seeds. Driver support, exact parity, matched-null behavior, and structural controls pass, while observable recovery, probability quality, reference recovery, and the `<0.20` hazard bound fail. The mechanical decision is `redesign`; R2-15 and acceptance remain blocked.
- `phase-02r-14b-v5-redesign-diagnostic-*` — merged issue-#78/PR-#79 readiness-only stop evidence. Contract `1.0.0` lacked mechanical H1-H5 disposition thresholds, so execution was unauthorized: 0/120 inventory units and 0/320 D16 cells executed, all hypotheses remain unresolved, and the response is `stop_contract_not_executable`. Accepted ADR 0009 records the stop; Phase 2R.14BA issue #80 amends the contract before Phase 2R.14BB execution. R2-14C remains blocked and reserved acceptance/final holdout remain `not_materialized`.
- `phase-02r-14bb-v5-redesign-diagnostic-*` — issue-#82 aggregate development evidence for all 20 development seeds (120 inventory units) and exhaustive 320-cell feasibility surface (`D16 / D17`) under Contract `1.1.0`. `H1_LOG_HAZARD_SPREAD` is supported (insufficient public observable spread); `H3_PROBABILITY_SCALE`, `H4_REFERENCE_SPECIFICATION`, and `H5_HAZARD_TAIL` are rejected; `H6_DESIGN_FEASIBILITY` is infeasible (0/320 cells satisfy simultaneous recovery and hazard bounds). The mechanical response is `stop_infeasible_design`; proposed ADR 0011 records the stop. R2-14C remains blocked; reserved acceptance and final holdout remain `not_materialized`.

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

Regenerate or verify the R2-09 v3 corpus evidence with:

```bash
python3 scripts/build_v3_modeling_corpus.py --write
python3 scripts/build_v3_modeling_corpus.py --check
```

The R2-09 command verifies event-first generation and dual-time observations only. It does not build R2-10 evaluation data, run an acceptance protocol, or materialize a final release holdout.

Verify the immutable pre-amendment R2-10 structural-support evidence with:

```bash
python3 scripts/check_v3_evaluation_support.py --check
```

The check hashes the retained `3.0.0` JSON and Markdown; it does not regenerate or overwrite them.

Generate or verify the amended R2-10 evaluation evidence with:

```bash
python3 scripts/build_v3_evaluation_pipeline.py --write
python3 scripts/build_v3_evaluation_pipeline.py --check
```

The command consumes the separately versioned v3.1 arrears remediation and writes only authoritative `3.2.0` aggregate evidence. It keeps acceptance roles out of prediction and metrics, does not access protected oracle sidecars, and leaves the final release holdout `not_materialized`. The Jul–Dec selection membership contains 1,498 episodes from 787 unique policies; repeated episodes do not add independent-policy capacity. Diagnostics authorize comparison and the frozen rule selects XGBoost, but no R2-11 acceptance result exists. Results are limited to synthetic candidate selection and are not a prospective real-world backtest, operational claim, actuarial claim, or release claim.

Generate or verify the R2-11 decision evidence with:

```bash
python3 scripts/run_v3_statistical_acceptance.py --write
python3 scripts/run_v3_statistical_acceptance.py --check
make v3-acceptance-check
```

The non-committed `tmp/r2-11-readiness` and `tmp/r2-11-primary` intermediates are regenerated through the documented per-seed commands and digest-bound in the committed manifest. The mechanical decision is `redesign`: all 20 pairs pass readiness, but the frozen signal-recovery thresholds fail. P2-08/P2-09 remain paused and the final holdout remains `not_materialized`.

Run or verify R2-14 qualification evidence with:

```bash
python3 scripts/run_v4_qualification.py --readiness-check
python3 scripts/run_v4_qualification.py --check
make r2-14-qualification-check
```

The committed evidence is aggregate-only. Per-seed histories, observations,
oracles, targets, and predictions remain non-committed. The mechanical `redesign`
decision blocks R2-15 and does not authorize future-acceptance access.

R2-14A issue #76 is documentation-only. Validate its post-v4 diagnostic
authorization boundary without importing a simulator or producing results:

```bash
python3 scripts/check_r2_14a_diagnostic_contract.py
make r2-14a-diagnostic-contract-check
```

The check binds ADR 0008, contract `1.0.0`, four disjoint information domains,
the 17-diagnostic inventory, the fixed 320-cell feasibility surface, and continued
absence of reserved acceptance and final-holdout material.

R2-14BA issue #80 amends the diagnostic authorization contract to `1.1.0`. Validate
its quantitative truth-table boundary without importing a simulator:

```bash
python3 scripts/check_r2_14ba_diagnostic_contract.py
make r2-14ba-diagnostic-contract-check
```

Run or verify Phase 2R.14BB diagnostic execution evidence with:

```bash
python3 scripts/run_v5_redesign_diagnostics_execution.py --readiness-check
python3 scripts/run_v5_redesign_diagnostics_execution.py --check
make r2-14bb-diagnostic-check
```

The committed evidence is strictly aggregate-only with minimum 10-policy privacy
suppression. Intermediate per-seed rows are purged immediately. The mechanical
decision `stop_infeasible_design` records that 0/320 feasibility surface cells
satisfy simultaneous recovery and hazard constraints. R2-14C remains blocked,
and reserved acceptance seeds and the final holdout remain `not_materialized`.
