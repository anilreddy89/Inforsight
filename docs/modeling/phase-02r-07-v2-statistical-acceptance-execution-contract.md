# Phase 2R.07 v2 Statistical Acceptance Execution Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Execution contract version | `1.0.0` |
| Governing issue | [#51](https://github.com/anilreddy89/Inforsight/issues/51) |
| Acceptance protocol | `phase-02r-04-statistical-acceptance-protocol.md` version `1.0.0` |
| Simulator and observation contract | `phase-02r-04-v2-statistical-simulator-and-observation-contract.md` version `2.0.0` |
| Evaluation pipeline contract | `phase-02r-06-v2-evaluation-pipeline-contract.md` version `2.0.0` |
| Execution state | Readiness gate failed before R2-07 result generation |
| Required decision | `stop` |
| Final release holdout | `not_materialized` |

## Purpose

This contract turns the first step of the approved R2-07 protocol into a fail-closed executable readiness gate. It does not amend a seed, fold, metric, interval method, threshold, tolerance, stress magnitude, allowed failure count, or aggregation rule from protocol `1.0.0`.

The readiness gate must run before corpus replication, model fitting, prediction, bootstrap resampling, label shuffling, ablation, or robustness evaluation. Statistical execution is authorized only when every required input and paired-control invariant was frozen by R2-04 through R2-06 and can be reproduced without a new caller-controlled choice.

Protocol `1.0.0` states that an unexecutable protocol produces `redesign`. Because v2 output was inspected during R2-06, the protocol amendment rule prohibits filling material gaps after the fact and interpreting the resulting run as the original predeclared experiment.

## Frozen readiness rules

The readiness gate evaluates these rules from committed contracts, artifacts, and deterministic configuration behavior.

| Rule ID | Required condition | Failure classification |
| --- | --- | --- |
| `READINESS-SELECTED-CANDIDATE` | R2-06 evidence names one selected candidate before R2-07 acceptance data is used. | `redesign` |
| `READINESS-DRIVER-GROUPS` | R2-06 evidence freezes the five protocol macro groups, strongest group, expected direction, and a zero-effect control group. | `redesign` |
| `READINESS-COEFFICIENT-REGISTRY` | Canonical v2 provenance contains the intercept/coefficient registry required by the simulator contract. | `redesign` |
| `READINESS-MATCHED-NULL-STREAMS` | Changing only `signal_mode` preserves allocation, static, recurring behavior, frailty, outcome-draw, censoring, missingness, delay, correction, category, and temporal streams. | `redesign` |
| `READINESS-MATCHED-STRESS-STREAMS` | Changing an approved robustness setting preserves all random streams not owned by that intervention. | `redesign` |
| `READINESS-SHUFFLE-DOMAIN` | A versioned policy-level label-shuffle domain and derivation are frozen. | `redesign` |
| `READINESS-FOLD-SUPPORT` | Already-published R2-06 fold evidence satisfies the protocol's minimum 500 eligible rows, 50 positives, and 50 negatives per evaluated membership. | `redesign` |
| `READINESS-DUAL-TIME-VISIBILITY` | A focused non-final fixture proves that behavior features exclude events whose `ingested_at` is after the observation cutoff. | `stop` |
| `READINESS-HOLDOUT-ABSENCE` | Every upstream artifact and configuration reports the final holdout as `not_materialized`. | `stop` |

The current implementation derives all simulator random domains from `v2_run_identity(config)`, while canonical run identity includes `signal_mode`, `drift_scenario`, and `mcar_missingness_rate`. A null or stress configuration consequently changes every domain seed rather than preserving matched streams. This violates the fixed replication design and cannot be repaired within R2-07 without a versioned generator/protocol redesign.

The committed R2-06 artifacts also contain two frozen candidates but no selected-candidate field, per-source diagnostics but not the five protocol macro groups or strongest/zero-effect declarations, no canonical coefficient registry, and no label-shuffle random domain. These are prerequisites, not choices R2-07 may make after R2-06 results exist.

The current observation builder constructs behavior features before applying ingestion-time visibility to the behavior event. A deterministic five-policy readiness fixture contains observations whose owning behavior event has `ingested_at > as_of` and is absent from `visible_event_ids`, while the event payload is nevertheless present in the observation features. This is post-cutoff ingestion leakage. The fixture is a structural audit only: it fits no model and emits no row identity, raw row, prediction, or metric artifact.

The published seed-`20260901` acceptance fold counts are retained as additional structural evidence. Their positive counts are below 50 in all three folds. The readiness decision does not extrapolate those counts to ungenerated seeds and does not generate additional acceptance corpora.

## Decision aggregation

Each readiness rule emits `pass` or `fail` and exactly one failure classification. Decision precedence is:

1. any failed `stop` rule yields `stop`;
2. otherwise, any failed `redesign` rule yields `redesign`;
3. otherwise, all readiness rules passing authorizes the statistical runner to continue; and
4. an incomplete rule inventory yields `redesign`.

The present readiness evidence requires `stop` because the dual-time leakage rule fails. The redesign findings remain recorded but cannot lower the decision. All 20 planned seeds and their three folds must remain in the manifest with status `not_run_protocol_not_executable`; they are accounted for but are not statistical replications and cannot be counted as passed, failed, or structurally invalid runs.

## Artifact boundary

R2-07 publishes:

- `docs/experiments/phase-02r-07-v2-statistical-acceptance-manifest.json`;
- `docs/experiments/phase-02r-07-v2-statistical-acceptance-report.md`; and
- `docs/experiments/phase-02r-07-v2-statistical-acceptance-decision.md`.

The manifest binds this contract, protocol, simulator/observation contract, R2-05 corpus manifest, R2-06 split manifest, feature dictionary and pipeline manifest, diagnostics, and baseline comparison by SHA-256. It records every planned seed/fold, every readiness rule, the mechanically aggregated decision, limitation dispositions, reproduction command, and final-holdout status.

No raw history, observation, matrix, target, prediction, oracle record, fitted model, bootstrap sample, final-holdout seed, or final-holdout membership may be committed by this readiness decision. The only new generated data is the in-memory five-policy structural audit fixture; it is discarded after aggregate leakage counts are computed.

## Claim and limitation disposition

The `stop` decision establishes that protocol `1.0.0` cannot be executed against the current v2 implementation because the structural audit found post-cutoff ingestion leakage. It also records independent redesign findings that prevent a valid predeclared matched-control experiment.

- `LIM-002-001` remains scheduled and claim-blocking; no temporal-stability or robustness closure evidence was generated.
- `LIM-002-002` remains scheduled and claim-blocking; no valid falsification or signal-recovery evidence was generated.
- `LIM-002-003` remains scheduled and claim-blocking; its later one-shot final-holdout workflow was not exercised.
- P2-08 and P2-09 remain paused.

## Required redesign ownership

A new focused corrective issue must own the leakage repair and versioned redesign before R2-07 statistical execution can resume. At minimum it must:

- separate run/artifact identity from independently addressable random-stream identity so matched null and stress corpora preserve all required streams;
- freeze the selected candidate without using R2-acceptance results;
- freeze the five macro driver groups, strongest driver, directions, and zero-effect control;
- move the coefficient registry into canonical configuration and provenance;
- freeze label-shuffle, policy-cluster bootstrap, pooled seed-balanced interval, and nested learning-subset derivations;
- make missingness, category arrival, ingestion-delay stress, and drift interventions independently configurable and testable;
- ensure delayed information changes public point-in-time features rather than only audit event visibility;
- reassess corpus/fold support without weakening the 500/50/50 structural rule; and
- publish a new contract/protocol version while preserving the original protocol and this decision in the audit trail.

## Reproduction

```bash
python3 scripts/run_v2_statistical_acceptance.py --check
python3 -m unittest discover -s simulator/tests -p 'test_v2_acceptance.py' -v
```

No command in this contract authorizes a result-producing acceptance run or final-holdout access.
