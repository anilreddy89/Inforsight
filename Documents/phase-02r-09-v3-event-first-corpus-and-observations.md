# Phase 2R.09 — v3 Event-First Corpus and Observations

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2R — Modeling Foundation Remediation Gate |
| Sequence | R2-09 |
| Change tracker ID | `R2-09` |
| GitHub issue | [#56](https://github.com/anilreddy89/Inforsight/issues/56) |
| Issue title | `[Implementation] R2-09: Implement the v3 event-first corpus and observations` |
| Branch | `feat/56-r2-09-v3-event-first-corpus` |
| Pull request | [#57](https://github.com/anilreddy89/Inforsight/pull/57) |
| Status | Completed on 2026-08-30; merged as `89c2291` |
| Merge commit | `89c2291` |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Modeling-foundation remediation / versioned capability |
| Strict predecessor | R2-08, completed through issue #53 and PR #54, merge commit `09f678a` |
| Blocks | R2-10 — rebuild v3 evaluation, features, candidates, and deterministic selection |
| Governing decision | ADR 0005 |
| Governing substrate | `docs/modeling/phase-02r-08-v3-statistical-substrate-contract.md`, contract `3.0.0` |
| Governing acceptance protocol | `docs/modeling/phase-02r-08-statistical-acceptance-protocol.md`, version `2.0.0` |
| Random-stream registry | `1.0.0` |
| Final holdout | Must remain `not_materialized` throughout R2-09 |
| Last reviewed | 2026-08-30 |

## Objective

Implement the approved v3 event-first statistical substrate through deterministic, separately namespaced corpus and recurring-observation code. The implementation must construct immutable dual-time events before reconstructing any public state, derive hazards only from the visible event set plus governed latent frailty, preserve matched primitive streams across signal and atomic intervention variants, and publish reproducible non-final structural evidence without fitting or evaluating a model.

R2-09 owns event, corpus, observation, oracle-sidecar, identity, random-stream, intervention, lineage, and deterministic verification behavior. It does not own temporal folds, the v3 feature dictionary or matrix pipeline, preprocessing, diagnostics, model candidates, candidate selection, scoring authorization, acceptance execution, calibration, explanations, or a final release holdout.

## Completion evidence

Issue #56 closed when PR #57 merged to `main` as `89c2291` on 2026-08-30. The merged implementation publishes closed v3 event, observation, and protected oracle-sidecar schemas; event-first dual-time generation; stream-set, artifact, and execution identities; random-stream registry `1.0.0`; immutable corrections; complete visible-event lineage; frozen competing hazards; conditional and observable oracle sidecars; atomic scenario ownership; and deterministic non-final corpus evidence.

The default manifest records 14,400 policies, 76,545 recurring observations, 13,431 observed positives, and 63,114 observed negatives. Seventeen focused v3 tests, 12 contract tests, 258 simulator tests, all historical artifact checks, repository-boundary checks, and hosted CI pass. PR #57 also normalized the committed numeric evidence boundary for cross-platform reproduction and increased the hosted CI timeout without reducing verification coverage. No model, prediction, acceptance metric, or final release holdout was created.

## Why this work is next

R2-07 stopped before model fitting because the v2 observation boundary could include behavior derived from an event ingested after the observation cutoff. The same readiness audit found unmatched scenario streams, incompletely specified interventions, no canonical coefficient implementation, and insufficient fold support.

R2-08 resolved those design gaps before any v3 output existed. It approved ADR 0005, substrate contract `3.0.0`, random-stream registry `1.0.0`, and acceptance protocol `2.0.0`. The approved contract explicitly assigns event/corpus/observation implementation and dual-time/matched-stream tests to R2-09. R2-10 cannot construct governed evaluation data until this implementation is merged.

## Immutable boundaries inherited from R2-08

- V1 and v2 code, schemas, artifacts, reports, and the R2-07 `stop` decision remain immutable historical evidence.
- V3 paths, schemas, runtime types, commands, manifests, and artifacts must contain `v3`; no existing public API may silently adopt v3 semantics.
- The default corpus is 14,400 policies across 24 monthly cohorts of 600 policies, with issuance from 2022-01-01 through 2023-12-01 and watermark `2026-12-31T23:59:59Z`.
- Roles are assigned before risk draws, balanced within cohort and billing frequency where integers permit, mutually exclusive, and independent of outcomes.
- Observations begin after 30 elapsed days, use non-overlapping 90-day episodes, and stop after a terminal outcome.
- Event visibility requires both `effective_at <= cutoff` and `ingested_at <= cutoff`.
- Every public feature value must be reconstructed from visible immutable events or be explicitly `cutoff_derived`; generator working variables and protected values are forbidden.
- Stream-set, artifact, and execution identities remain separate and must obey the canonical identity formulas in contract `3.0.0`.
- Every primitive draw uses random-stream registry `1.0.0`; iteration order must not control randomness.
- The coefficient registry, equations, frailty distribution, month offsets, hazard interpretation, oracle definitions, scenario variants, and atomic intervention ownership are frozen exactly as approved.
- The final release holdout remains `not_materialized`. R2-09 must not choose its seed, generate identity or membership, inspect its distribution, or create any holdout artifact.
- Inspecting non-final v3 structural output for implementation verification is allowed. Tuning coefficients, thresholds, seeds, or scenarios after inspection is not.

## Required changes

### 1. Add separately versioned v3 data contracts

Add closed JSON Schemas under `data-contracts/v3/` for:

```text
data-contracts/v3/policy-event.schema.json
data-contracts/v3/observation-record.schema.json
data-contracts/v3/oracle-sidecar.schema.json
```

The schemas must:

- use explicit v3 schema/contract identifiers and reject v1/v2 versions;
- preserve immutable event envelopes with UTC effective and ingestion timestamps;
- represent every event and payload required by the approved v3 lifecycle without altering v1/v2 schemas in place;
- require sorted `visible_event_ids`, canonical visible-event digest, outcome-episode identity, artifact identity, censoring state, and per-feature lineage on observations;
- keep frailty, primitive draws, oracle values, scenario configuration, protected identifiers, and other sidecar-only values out of the public observation schema;
- bind oracle sidecars to exact observation and artifact identity; and
- reject unknown properties, inconsistent label/censoring states, unsupported enums, malformed timestamps, and non-finite numeric values.

Add v3 schema tests in `data-contracts/tests/test_v3_contracts.py`, including valid fixtures and negative mutation cases. Update `data-contracts/README.md` to explain the v3 namespace and compatibility boundary.

### 2. Implement v3 configuration, canonicalization, identities, and stream registry

Add a dedicated runtime module, expected as:

```text
simulator/src/inforsight_simulator/v3_config.py
```

It must implement and validate:

- the frozen 14,400-policy structural configuration, cohort calendar, cadence, watermark, billing-frequency allocation, role proportions, and non-final seed inputs;
- complete scenario configuration for `stable`, `null_signal`, `doubled_missingness`, `unknown_category_arrival`, `moderate_drift`, and `stress_drift`;
- finite canonical JSON with sorted keys, NFC strings, UTC `Z` timestamps, decimal-string numeric representation where required, and trailing-newline file serialization;
- `stream_set_id`, `artifact_id`, and `execution_id` with the exact field ownership defined by contract `3.0.0`;
- HMAC-SHA256 primitive uniforms using the first 64 bits and `(integer + 0.5) / 2^64`;
- the versioned inverse-normal transform; and
- every random domain and key tuple in registry `1.0.0`.

Validation must reject missing, extra, inconsistent, caller-selected, or non-finite configuration; unknown random domains; intervention fields outside the declared owner; identity substitution; and any final-holdout configuration.

### 3. Implement immutable event-first v3 generation

Add a separate v3 corpus module, expected as:

```text
simulator/src/inforsight_simulator/v3_corpus.py
```

It must:

- create immutable canonical event envelopes and payloads before observation reconstruction or hazard evaluation;
- generate 24 monthly cohorts, 600 policies per cohort, and all four billing frequencies with deterministic pre-outcome role allocation;
- derive policy and event IDs from `stream_set_id`, stable entity keys, timestamps/ordinals, and contract version;
- generate lifecycle, billing, payment, retry, recovery, arrears, notice, service-contact, correction, missingness, ingestion-delay, category-arrival, and drift behavior using only the assigned random domains;
- create corrections as new immutable events referencing earlier events;
- preserve unaffected primitive draws and canonical event fields across matched scenarios;
- allow survival-dependent divergence only after the last common eligible identity/time and report that boundary explicitly;
- forbid role, outcome, label, scenario token, identifier token, oracle value, or future state from driving public behavior; and
- fail closed on invalid histories, identity collisions, non-finite values, out-of-contract hazards, unsupported event sequences, or intervention leakage.

The v3 implementation may reuse audited generic helpers only when their semantics are unchanged and tests prove the version boundary. V2 entry points and generated evidence must remain unchanged.

### 4. Implement visible-history reconstruction and feature lineage

For each policy and cutoff, the implementation must:

1. select `V(i,t)` using both effective-time and ingestion-time predicates;
2. validate the complete visible history;
3. reconstruct public state and hazard inputs only from `V(i,t)`;
4. record sorted visible event IDs and a digest of canonical visible-event bytes; and
5. record per-value lineage listing source event IDs or the literal `cutoff_derived`.

Behavior with no visible source must use its frozen empty-history value. A correction affects reconstruction only when both the original and correction events are visible. Scheduled-but-not-created events, events outside either time boundary, generator working variables, role, scenario, latent values, oracle values, outcome uniforms, future state, and labels must not enter public reconstruction.

Lineage validation must reject missing sources, invisible sources, duplicated or unsorted source IDs, incorrect visible-event digests, substitution, deletion, and lineage that names protected or nonexistent data.

### 5. Implement eligibility, recurring episodes, labels, and censoring

The v3 observation builder must:

- require visible active status, at least 30 elapsed days of visible history, no open episode, and sufficient watermark information;
- open the first cutoff 30 elapsed days after issuance and later cutoffs only after the prior 90-day episode closes;
- derive observation and outcome-episode IDs from `stream_set_id`, stable entity keys, cutoff, and contract version;
- prevent duplicate policy/cutoff observations and all overlapping episodes;
- stop future observations after lapse or surrender;
- create a positive label only from a qualifying visible terminal event in `(cutoff, cutoff + 90 days]`;
- create a negative only with watermark coverage through episode end and no qualifying event; and
- otherwise mark the row right-censored, retain it in structural evidence, and exclude it from future fitting/metric eligibility.

### 6. Implement the frozen hazards and exact oracle sidecars

Implement the coefficient registry `1.0.0` and the lapse/surrender/continue equations from substrate contract `3.0.0` exactly, including:

- intercepts `-3.35` and `-4.05`;
- month offsets `{-0.08, 0.00, 0.08}`;
- frailty `Normal(0, 0.35)` with coefficients `1.00` and `0.50`;
- every transform, reference category, interaction, coefficient, empty-history value, and group assignment in the approved table;
- `signal_scale=1` for signal scenarios and `0` for null;
- the shared `outcome_uniform(policy, episode, month)` interval interpretation; and
- finite total terminal hazard strictly below `0.20` for every eligible generated state.

For every observation, calculate exact three-month cumulative incidence for lapse, surrender, and their union. Produce both frailty-conditional oracle values and observable oracle values integrated with the fixed 32-node Gauss-Hermite nodes, weights, ordering, and normalization preserved from contract `2.0.0`.

Oracle records must remain protected sidecars. Public observation construction, feature discovery, preprocessing, modeling, selection, and ordinary scoring interfaces must reject them directly and when nested.

### 7. Implement atomic matched interventions

Implement these variants without caller discretion:

| Variant | Only permitted change |
| --- | --- |
| `null_signal` | `signal_scale: 1 -> 0` |
| `doubled_missingness` | MCAR threshold `0.05 -> 0.10` |
| `unknown_category_arrival` | Declared service category becomes new after `2024-01-01` |
| `moderate_drift` | Baseline log-odds `+0.20` after `2024-01-01` and one declared covariate threshold shifts prevalence by no more than `0.15` |
| `stress_drift` | Baseline log-odds `+0.50`, MCAR `0.10`, and post-2024 delay thresholds producing the approved 80%/15%/5% mixture |

Each intervention manifest must enumerate its only permitted fields/transforms. Pair verification must prove identical `stream_set_id`, different `artifact_id`, exact equality of unaffected primitive draws and event fields through the common comparison boundary, and no change driven by role or outcomes.

### 8. Add deterministic non-final corpus evidence

Add a build/check command, expected as:

```text
scripts/build_v3_modeling_corpus.py
```

Add a reproducible integrity manifest and v3 data card, expected as:

```text
docs/experiments/phase-02r-09-v3-corpus-manifest.json
datasets/v3/DATA_CARD.md
```

The command must regenerate the approved default non-final corpus and verify committed evidence without committing large raw histories, public observation rows, row-level oracle sidecars, or protected draws. The manifest must include:

- phase, artifact, contract, registry, canonicalization, source, dependency, and command versions/digests;
- stream-set, artifact, and execution identities;
- complete structural configuration and scenario name;
- deterministic counts by cohort, billing frequency, role, event type, observation eligibility, outcome, and censoring state;
- visible-history, observation, oracle-sidecar, and protected-data digests without exposing protected row values;
- identity uniqueness, recurrence, episode-isolation, role-isolation, and structural-validation results;
- matched-pair equality summaries and explicit survival-divergence boundaries for each atomic variant;
- finite-value and hazard-bound evidence;
- final-holdout status `not_materialized`; and
- the synthetic-only claim boundary.

The data card must document generation and check commands, schema and contract versions, intended use, prohibited claims, corpus structure, dual-time behavior, protected sidecars, known limitations, compatibility, and the R2-10 dependency boundary.

### 9. Integrate repository checks without disturbing historical evidence

Update:

```text
Makefile
scripts/check_repository_boundaries.sh
simulator/README.md
docs/experiments/README.md
docs/backlog.md
docs/limitations.md
README.md
PROJECT_PROGRESS.md
Documents/Inforsight_Change_Tracker.md
Documents/phase-02r-09-v3-event-first-corpus-and-observations.md
```

Add a `v3-corpus-check` target to the full repository gate. Boundary checks must require the approved v3 contracts/evidence, reject forbidden final-holdout paths or values, and continue reproducing every governed v1/v2 artifact unchanged.

During implementation, update issue, branch, pull-request, verification, and completion metadata only when that evidence exists. On merge, mark R2-09 complete, link the issue/PR/merge commit, and make R2-10 ready without claiming statistical acceptance.

## Anticipated file plan

### Files to add

```text
data-contracts/v3/policy-event.schema.json
data-contracts/v3/observation-record.schema.json
data-contracts/v3/oracle-sidecar.schema.json
data-contracts/tests/test_v3_contracts.py
simulator/src/inforsight_simulator/v3_config.py
simulator/src/inforsight_simulator/v3_corpus.py
simulator/tests/test_v3_config.py
simulator/tests/test_v3_corpus.py
scripts/build_v3_modeling_corpus.py
docs/experiments/phase-02r-09-v3-corpus-manifest.json
datasets/v3/DATA_CARD.md
Documents/phase-02r-09-v3-event-first-corpus-and-observations.md
```

Additional focused v3 modules or test files may be added when they make identity, stream, reconstruction, risk, or sidecar boundaries easier to audit. Any such module must remain v3-namespaced and inside this issue's scope.

### Files expected to update

```text
Makefile
data-contracts/README.md
scripts/check_repository_boundaries.sh
simulator/src/inforsight_simulator/__init__.py (only if a public v3 export is required)
simulator/README.md
docs/experiments/README.md
docs/backlog.md
docs/limitations.md
README.md
PROJECT_PROGRESS.md
Documents/Inforsight_Change_Tracker.md
Documents/phase-02r-09-v3-event-first-corpus-and-observations.md
```

Historical v1/v2 source files should be updated only when a shared, version-neutral defect makes it unavoidable. Any such change requires explicit compatibility tests and must not change historical artifact bytes or conclusions.

## Required tests

### Configuration, canonicalization, identity, and random streams

- Reject invalid types, booleans-as-integers, dates, time zones, proportions, counts, versions, finite-number violations, unknown scenarios, and unsupported values.
- Verify exact frozen default configuration and role allocations.
- Verify canonical serialization rules and stable configuration bytes.
- Verify `stream_set_id`, `artifact_id`, and `execution_id` against independent reference fixtures.
- Prove intervention changes preserve stream-set identity and change artifact identity.
- Prove code, dependency-lock, source, and command changes affect execution identity only as specified.
- Verify every registry domain/key tuple, open-interval uniform mapping, and inverse-normal fixture independently.
- Prove iteration reordering does not alter primitive draws or output bytes.
- Reject unknown domains, missing provenance, identity substitution, and final-holdout configuration.

### Event-first dual-time reconstruction

- Prove events exist before feature/hazard reconstruction and no generator working variable is accepted as a public source.
- Move each source event independently across the effective-time boundary and ingestion-time boundary; a derived value may change only when both predicates admit the event.
- Verify visible-event IDs are complete, sorted, unique, and digest-bound.
- Verify every reconstructed value has valid source-event lineage or `cutoff_derived`.
- Verify empty-history values exactly match the frozen registry.
- Verify corrections change state only after both original and correction are visible.
- Reject scheduled, future, invisible, nonexistent, protected, duplicated, reordered, or substituted lineage.

### Cohorts, roles, events, recurrence, labels, and censoring

- Verify exactly 24 cohorts, 600 policies per cohort, 14,400 unique policies, and balanced billing-frequency allocation.
- Verify role allocation occurs before risk draws and is mutually exclusive, deterministic, balanced, and outcome-independent.
- Verify immutable event references, event ordering, correction semantics, and all approved lifecycle/behavior event types.
- Verify the 30-day seasoning rule, non-overlapping 90-day episodes, one observation per policy/cutoff, and no post-terminal observations.
- Cover observed lapse, observed surrender, observed negative, right censoring, insufficient watermark, and terminal ineligibility.
- Verify right-censored rows are never negative and remain counted in structural evidence.
- Verify policy, event, observation, and episode identities are unique and namespace/version bound.

### Risk equations and oracle calculations

- Unit-test every transformed coefficient term and the interaction against hand-calculated fixtures.
- Unit-test lapse, surrender, and continue probabilities for each modeled month against an independent implementation.
- Verify one stable frailty draw per policy and the approved frailty coefficients.
- Verify `signal_scale=0` removes every observable coefficient contribution without rerandomizing frailty, outcomes, or unaffected events.
- Verify the outcome-uniform interval mapping at boundary-adjacent fixtures.
- Verify all hazards are finite and total terminal hazard is below `0.20`.
- Verify exact conditional three-month cumulative incidence.
- Verify observable oracle integration against the frozen 32-node Gauss-Hermite reference values and strict tolerances.
- Reject direct and recursively nested oracle/frailty/draw values from public and downstream-compatible inputs.

### Atomic intervention and matched-stream equality

- Verify each scenario manifest names all and only its permitted changes.
- Compare stable/signal with null and every stress pair for exact equality of unaffected primitive draws.
- Compare canonical events field by field through the last common eligible identity/time.
- Verify and report survival-dependent divergence rather than misclassifying it as unmatched randomness.
- Verify doubled missingness changes only the approved threshold.
- Verify unknown-category arrival changes only the declared post-2024 mapping.
- Verify moderate drift obeys its log-odds and prevalence-shift bounds.
- Verify stress drift obeys its log-odds, missingness, and delay-threshold changes.
- Prove role and outcome values never drive missingness, delay, category, or drift.

### Determinism, schemas, artifacts, and compatibility

- Rebuild every committed R2-09 evidence file twice and compare bytes and SHA-256 digests.
- Verify schema/runtime agreement with positive and negative fixtures.
- Verify manifest digests fail closed after upstream, ordering, identity, or artifact mutation.
- Verify no raw matrix, prediction, bootstrap sample, executable model, or row-level protected sidecar is committed.
- Verify all governed v1 and v2 artifact bytes and conclusions remain unchanged.
- Run focused v3 tests, all contract tests, all simulator tests, every artifact check, repository-boundary checks, `make check`, and `git diff --check`.
- Audit the repository for final-holdout seed, identity, membership, corpus, observation, feature, matrix, prediction, or metric materialization and require none.

## Acceptance checks

- [x] Closed v3 event, observation, and oracle-sidecar schemas are added under `data-contracts/v3/` without modifying v1/v2 semantics.
- [x] The frozen 14,400-policy, 24-cohort configuration and deterministic pre-outcome role allocation are implemented exactly.
- [x] Stream-set, artifact, and execution identities follow contract `3.0.0` and fail closed on missing, inconsistent, or substituted provenance.
- [x] Random-stream registry `1.0.0`, HMAC uniform mapping, inverse-normal transform, domain keys, and iteration independence match independent reference tests.
- [x] Immutable events are generated before observations or hazards, and public values are reconstructed only from events visible in both effective and ingestion time.
- [x] Every public reconstructed value has valid event lineage or `cutoff_derived`, and every observation binds sorted visible IDs and canonical visible-event digest.
- [x] Effective-time and ingestion-time mutation tests prove a source changes an observation only when both visibility predicates pass.
- [x] Recurring observations obey seasoning, active-policy eligibility, non-overlapping episodes, unique cutoff identity, watermark, censoring, and terminal-ineligibility rules.
- [x] Every approved coefficient, transform, interaction, month offset, frailty rule, hazard equation, and outcome interval is implemented exactly with no post-output tuning.
- [x] Conditional and observable oracle probabilities match independent numeric fixtures and remain isolated in protected sidecars.
- [x] Direct and recursively nested protected values are rejected from public observations and downstream-compatible feature/model inputs.
- [x] Null, missingness, category, moderate-drift, and stress-drift variants change only their declared thresholds/transforms and reuse every unaffected primitive stream.
- [x] Matched-pair tests compare unaffected draws and event fields exactly and explicitly delimit permitted survival-dependent divergence.
- [x] The deterministic v3 manifest and data card publish structural and lineage evidence without committing large raw rows or protected row-level data.
- [x] Every v1/v2 contract, artifact, report, and historical conclusion remains unchanged and reproducible.
- [x] No fold, feature dictionary/matrix pipeline, preprocessing, diagnostic, model, candidate selection, scoring authorization, acceptance result, calibration, or explanation is created.
- [x] The final release holdout remains `not_materialized`, with no seed, identity, membership, distribution, observation, feature, prediction, or metric created or inspected.
- [x] Focused tests, all contract and simulator tests, deterministic artifact checks, repository-boundary checks, `make check`, and `git diff --check` pass.
- [x] Documentation records exact versions, commands, claim boundaries, compatibility, issue/PR evidence, and R2-10 as the only work enabled at closure.
- [x] Pull-request review completes, the R2-09 issue closes on merge, and merged evidence is recorded before R2-10 begins.

## Evidence required in the pull request

- Focused v3 schema/config/corpus test names, counts, and representative negative cases.
- Full `make check` output and `git diff --check` result.
- Two clean v3 evidence rebuilds with byte-identical files and matching SHA-256 digests.
- Independent reference fixtures for identity construction, HMAC uniform mapping, inverse-normal transformation, coefficients, hazards, and both oracle calculations.
- Structural summaries by cohort, billing frequency, role, event type, observation outcome, and censoring state.
- Effective-time and ingestion-time mutation evidence for every source-bearing reconstructed value.
- Direct and nested protected-field rejection evidence.
- Matched scenario comparisons showing identical stream-set identity, distinct artifact identity, unchanged primitive draws/event fields, and explicit survival-divergence boundaries.
- Byte-digest proof that governed v1/v2 artifacts are unchanged.
- File/path and manifest audit proving final-holdout status remains `not_materialized`.
- Version and compatibility table for new schemas, runtime contracts, commands, and artifacts.
- Links to the v3 manifest, data card, governing ADR/contract/protocol, and this phase document.

## Explicitly out of scope

- Changing any frozen R2-08 coefficient, transform, threshold, seed block, cohort, cadence, identity rule, stream domain, scenario, role proportion, or protocol rule after v3 output inspection.
- Implementing R2-10 temporal folds, embargo evidence, v3 feature dictionary, matrix construction, preprocessing, diagnostics, logistic or boosted candidates, selection, authorization, model artifacts, or non-final metrics.
- Executing any R2-11 readiness, null/shuffle control, signal-recovery, learning, ablation, robustness, bootstrap, uncertainty, stability, or decision rule.
- Choosing, generating, or accessing a final-release-holdout seed, identity, membership, distribution, event, observation, feature, matrix, prediction, or metric.
- Closing `LIM-002-001`, `LIM-002-002`, or `LIM-002-003`; R2-09 supplies implementation evidence only.
- Resuming P2-08 calibration or P2-09 explanation work.
- Rewriting or deleting v1/v2 schemas, source paths, artifacts, reports, decisions, or historical conclusions.
- Adding new lifecycle fields, real data, SQL persistence, services, Kafka, cloud infrastructure, agents, or RAG.
- Making insurer-representativeness, prevalence, actuarial, causal, fairness, operational-utility, business-value, customer-impact, production-readiness, or real-world predictive claims.

## Dependency and exit boundary

R2-09 may begin only from updated `main` containing R2-08 merge commit `09f678a`. The implementation issue must use the existing `v0.2.0-risk-model` milestone and remain a single focused dependency-gated increment.

R2-09 is complete on `main` through issue #56 and PR #57, merge commit `89c2291`. Completion authorizes R2-10 only. It does not authorize acceptance-role metrics, limitation closure, calibration, explanation, release claims, or final-holdout access.

## Copy-ready GitHub issue content

Use `.github/ISSUE_TEMPLATE/implementation.yml` and enter the following content.

### Title

```text
[Implementation] R2-09: Implement the v3 event-first corpus and observations
```

### Work metadata

```text
Backlog work ID: R2-09
Classification: Modeling-foundation remediation / versioned capability
Priority: Release blocking
Milestone: v0.2.0-risk-model
```

### Outcome

```text
A separately versioned deterministic v3 event-first corpus and recurring-observation implementation conforms to substrate contract 3.0.0, reconstructs every public value only from dual-time-visible immutable events, preserves matched primitive streams across atomic scenarios, isolates exact oracle sidecars, publishes reproducible non-final structural evidence, and leaves models and the final release holdout unmaterialized.
```

### Context

```text
R2-08 completed through issue #53 and PR #54, merged as 09f678a, approving ADR 0005, v3 substrate contract 3.0.0, random-stream registry 1.0.0, and statistical acceptance protocol 2.0.0 before any v3 output was generated or inspected. R2-09 is the next strict Phase 2R increment and implements only the event, corpus, recurring-observation, oracle, identity, stream, intervention, lineage, and deterministic-evidence layer of that frozen design. The complete implementation plan and test inventory are in Documents/phase-02r-09-v3-event-first-corpus-and-observations.md. V1/v2 evidence remains immutable; R2-10, R2-11, P2-08, and P2-09 remain blocked.
```

### In scope and out of scope

```text
In scope:
- Closed v3 event, observation, and protected oracle-sidecar schemas.
- Frozen 14,400-policy/24-cohort configuration, canonical identities, random-stream registry 1.0.0, immutable event-first generation, and pre-outcome role allocation.
- Dual effective/ingestion-time reconstruction, visible-event digests, per-value lineage, recurring non-overlapping episodes, labels, and censoring.
- Exact frozen coefficients, competing hazards, conditional/observable oracle probabilities, and atomic matched interventions.
- Deterministic non-final v3 corpus manifest, data card, build/check command, boundary integration, compatibility tests, and documentation.

Out of scope:
- R2-10 folds, features, preprocessing, diagnostics, candidates, selection, authorization, model artifacts, or metrics.
- R2-11 acceptance execution or decision; P2-08 calibration; P2-09 explanations; limitation closure.
- Any change to frozen R2-08 statistical choices after inspecting output.
- Any final-release-holdout seed, identity, membership, materialization, inspection, transformation, prediction, or evaluation.
- Rewriting v1/v2 evidence or adding unapproved lifecycle/infrastructure scope.
```

### Claim, limitation, contract, and artifact impact

```text
Allowed while open: Implement and inspect non-final v3 structural output solely to verify contract, determinism, lineage, numeric correctness, and matched-stream invariants.
Blocked while open: R2-10 and R2-11; model fitting/selection/evaluation; calibration; explanations; limitation closure; release/performance claims; all final-holdout access.
Limitations affected: Supplies corrective implementation evidence for LIM-002-001 and LIM-002-002 without closing them. LIM-002-003 remains open.
Downstream work resumed at closure: R2-10 only.
Contract or version change: Add separately namespaced v3 event, observation, label, oracle-sidecar, identity, and corpus runtime/schema implementations for substrate contract 3.0.0 and random-stream registry 1.0.0. Do not modify v1/v2 semantics in place.
Artifact migration or compatibility: Add a deterministic non-final v3 corpus manifest and v3 data card; large raw rows and protected row-level sidecars remain regenerated rather than committed. Every v1/v2 artifact remains byte-identical. Final holdout remains not_materialized.
```

### Acceptance checks

Copy the checklist from this document's **Acceptance checks** section into the issue unchanged.

### Evidence

```text
- Focused v3 and full repository test output, including make check and git diff --check.
- Matching bytes and SHA-256 digests from two clean v3 evidence rebuilds.
- Independent numeric fixtures for identities, random streams, transforms, hazards, and oracle probabilities.
- Structural summaries by cohort, frequency, role, event type, outcome, and censoring.
- Dual-time mutation and complete lineage-validation evidence.
- Direct and nested protected-field rejection evidence.
- Atomic matched-scenario equality reports with explicit survival-divergence boundaries.
- Byte-digest proof that governed v1/v2 artifacts are unchanged.
- Version/compatibility table and final-holdout absence audit.
- Links to the v3 manifest, data card, governing ADR/contract/protocol, and phase document.
```

### Dependencies

```text
Must merge first: R2-08 — issue #53 and PR #54, merged as 09f678a (complete).
Blocks: R2-10. R2-11, P2-08, and P2-09 remain transitively blocked.
Related decisions or limitations: ADR 0005; v3 substrate contract 3.0.0; random-stream registry 1.0.0; acceptance protocol 2.0.0; R2-07 stop decision; LIM-002-001, LIM-002-002, and LIM-002-003.
```

Select every required boundary checkbox in the template. R2-09 uses fictional clean-room data, preserves dual-time and authority boundaries, has an explicit version/compatibility plan, and must not access or materialize a final holdout.
