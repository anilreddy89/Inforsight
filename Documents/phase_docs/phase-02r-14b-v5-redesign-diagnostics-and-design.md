# Phase 2R.14B — v5 Redesign Diagnostics and Design Approval

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2R — Modeling Foundation Remediation Gate, post-v4 redesign extension |
| Sequence | R2-14B |
| Change tracker ID | `R2-14B` |
| GitHub issue | [#78](https://github.com/anilreddy89/Inforsight/issues/78) |
| Issue title | `[Implementation] R2-14B: Execute bounded post-v4 redesign diagnostics and approve the v5 design` |
| Branch | `feat/78-r2-14b-v5-redesign-diagnostics` |
| Status | Implemented locally through issue #78; diagnostic manifest, report, hypothesis disposition, and proposed ADR 0009 stop recorded; R2-14C blocked |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Remediation diagnostic execution and successor design |
| Strict predecessor | R2-14A, merged through issue #76 and PR #77 as merge commit `52c03c8` on 2026-09-03 |
| Governing decision | ADR 0008 |
| Governing contract | Post-v4 diagnostic authorization contract `1.0.0` |
| Development seeds | `20280101` through `20280120`, inclusive |
| Reserved acceptance seeds | `20271201` through `20271220`, inclusive; inaccessible throughout R2-14B |
| Final holdout | Undefined and `not_materialized` throughout R2-14B |
| Blocks | R2-14C, R2-15, R2-16, and P2-08 through P2-12 |
| Last reviewed | 2026-09-03 |

## Objective

Execute the complete diagnostic inventory frozen by R2-14A on the newly
authorized development block, publish deterministic aggregate evidence, derive
exactly one mechanical disposition for each of six hypotheses, and select the
smallest successor response permitted by the causal decision table.

R2-14B must evaluate all 17 registered diagnostics, including the complete
320-cell feasibility surface, without in-place tuning, selective reruns, grid
expansion, early stopping, seed replacement, or denominator alteration. If the
evidence supports a coherent feasible successor, propose ADR 0009 and a
versioned v5 design specification for later R2-14C implementation. Otherwise,
record `stop` or keep R2-14C blocked as required by contract `1.0.0`.

## Why this work is next

R2-14 implemented substrate `4.0.0` and protocol `3.0.0`. Driver support,
transform parity, matched-null behavior, and structural controls passed, but all
20 development seeds failed observable recovery, probability quality, reference
recovery, and the monthly hazard ceiling. The mechanical result was `redesign`.

R2-14A closed that evidence block without rewriting it. ADR 0008 and contract
`1.0.0` freeze six causal hypotheses, diagnostics `D1` through `D17`, development
seeds `20280101..20280120`, protected execution rules, a non-selective feasibility
surface, mechanical dispositions, and the permitted successor responses.
R2-14B is the authorized evidence-producing step, not an implementation or
acceptance run.

## Immutable evidence and boundaries

- R2-14A is merged through PR #77 and merge commit `52c03c8`; ADR 0008 and
  contract `1.0.0` are the sole execution authority.
- V1, v2, v3, v4, R2-07, R2-11, R2-13, and R2-14 evidence remains immutable.
- Seeds `20261001..20261020` and `20271101..20271120` are spent. Their row-level
  results cannot be used for tuning, selective redesign, or replacement.
- Seeds `20280101..20280120` form the complete R2-14B development domain. All
  seeds, both scenarios, and all three folds remain in the denominator.
- Reserved seeds `20271201..20271220` must not be generated, inspected, assigned,
  scored, summarized, or otherwise accessed.
- Final-holdout identity, membership, distribution, rows, transforms,
  predictions, and metrics remain undefined and `not_materialized`.
- Temporary oracle, frailty, outcome, matrix, prediction, and tail-attribution
  values are protected. Only approved aggregates may be committed, and cells
  with fewer than 10 unique policies must be suppressed.
- No result authorizes prospective performance, actuarial, causal, fairness,
  operational, customer-impact, conservation, production, or release claims.

## Governed diagnostic inventory

| Hypothesis | Diagnostics | Question |
| --- | --- | --- |
| `H1_LOG_HAZARD_SPREAD` | `D1`–`D3` | Is public log-hazard spread too weak relative to baseline and frailty variation? |
| `H2_HORIZON_ATTENUATION` | `D4`–`D6` | Do survival, competing risks, or the 90-day union target attenuate recoverable signal? |
| `H3_PROBABILITY_SCALE` | `D7`–`D9` | Does probability-scale behavior explain weak ranking or probability-quality improvement? |
| `H4_REFERENCE_SPECIFICATION` | `D10`–`D12` | Is the governed reference misspecified relative to the exact competing-risk mechanism? |
| `H5_HAZARD_TAIL` | `D13`–`D15` | Which registered terms and joint-support cells drive the hazard-ceiling breach? |
| `H6_DESIGN_FEASIBILITY` | `D16`–`D17` | Can a frozen design cell satisfy recovery, quality, incidence, and hazard constraints simultaneously? |

Each hypothesis receives exactly one mechanically reproducible `supported`,
`rejected`, or `unresolved` disposition. A diagnostic failure is recorded as a
governed failure; it cannot trigger an ad hoc replacement or selective retry.

## Required changes

### 1. Implement fail-closed readiness

Add `scripts/run_v5_redesign_diagnostics.py` with a readiness path that binds
merge `52c03c8`, ADR 0008, contract `1.0.0`, upstream identities and digests,
dependency versions, seed domains, scenario pairing, fold membership, the
diagnostic registry, feasibility ordering, suppression, and output schemas
before result-producing access.

Readiness must construct the complete 20-seed, two-scenario, three-fold inventory
and prove that spent, development, reserved, and final-holdout domains are
disjoint. Any missing, unexpected, non-finite, ambiguous, or tampered input fails
closed.

### 2. Execute all registered diagnostics

Run `D1` through `D15` for the exact purposes authorized by contract `1.0.0`.
Run `D16` across all 320 lexicographically ordered cells and use `D17` to evaluate
simultaneous constraints. Do not stop when an informative cell appears, change
an axis or bound, add a cell, or reuse result-bearing output to tune the same run.

### 3. Enforce protected-intermediate handling

Validate canonical membership and ordering before every join, transform, fit,
prediction, and aggregation. Isolate ordinary candidate features from oracle,
mechanism-only, frailty, outcome-uniform, and target concepts. Aggregate only
into authorized schemas, suppress cells below 10 unique policies, and purge all
protected intermediates after computation, including on governed failure.

### 4. Publish deterministic aggregate evidence

Create these authoritative artifacts:

```text
docs/experiments/phase-02r-14b-v5-redesign-diagnostic-manifest.json
docs/experiments/phase-02r-14b-v5-redesign-diagnostic-report.md
docs/experiments/phase-02r-14b-v5-hypothesis-disposition.md
```

The manifest is authoritative. The report and disposition document must be
byte-reproducible projections of it and bind planned-versus-executed counts,
failures, suppression, dispositions, feasibility, selected response, downstream
status, reserved-acceptance absence, and `final_holdout: not_materialized`.

### 5. Derive dispositions and the successor response mechanically

Apply the frozen contract rules without analyst override. Map the six-hypothesis
vector and feasibility outcome to the smallest coherent response allowed by the
causal decision table. Do not treat the highest-performing D16 cell as an
automatically authorized design or weaken any failed v4 threshold.

Incomplete, contradictory, or unmapped evidence must yield `unresolved` and keep
R2-14C blocked.

### 6. Propose and freeze the v5 design

When evidence supports a permitted feasible response, draft ADR 0009 and a
versioned v5 specification freezing equations, coefficients, interactions,
baselines, transforms, streams, event support, compatibility, and predeclared
R2-14C qualification rules. Cite the manifest and preserve unaffected elements.

If the surface is infeasible or no coherent response is authorized, ADR 0009
must record `stop` and no v5 implementation may begin.

### 7. Add tests, commands, and status integration

Add focused tests for readiness, inventory completeness, deterministic ordering,
protected cleanup, suppression, disposition derivation, feasibility accounting,
artifact projection, and prohibited seed/holdout access. Add Makefile entry
points and read-only reproduction checks to `make check` and hosted CI. Reconcile
current-facing repository documents only after evidence and decision are known.

## Out of scope

- Implementing or modifying the v5 simulator runtime, corpus, observations, or
  feature pipeline; those changes belong to R2-14C.
- Accessing spent row-level R2-11 or R2-14 results for iterative tuning.
- Accessing or materializing reserved seeds `20271201..20271220`.
- Defining, generating, predicting, scoring, or measuring a final holdout.
- Unregistered exploration, selective reruns, grid expansion, early stopping,
  denominator changes, or post-result threshold amendments.
- Resuming P2-08/P2-09 or downstream performance-dependent work.
- Making external performance, actuarial, causal, fairness, production, or
  release-readiness claims.

## Anticipated implementation surface

```text
scripts/run_v5_redesign_diagnostics.py
simulator/src/inforsight_simulator/
simulator/tests/
tests/test_v5_diagnostic_contract.py
docs/experiments/phase-02r-14b-v5-redesign-diagnostic-manifest.json
docs/experiments/phase-02r-14b-v5-redesign-diagnostic-report.md
docs/experiments/phase-02r-14b-v5-hypothesis-disposition.md
docs/adr/0009-*.md
docs/modeling/
Makefile
README.md
PROJECT_PROGRESS.md
docs/backlog.md
docs/limitations.md
docs/experiments/README.md
docs/simulator-process-flow.md
Documents/tracker/Inforsight_Change_Tracker.md
Documents/phase_docs/phase-02r-14b-v5-redesign-diagnostics-and-design.md
```

Exact source and test filenames may be refined during implementation, but the
contract, evidence paths, protected boundaries, and phase outcome may not.

## Acceptance checks

- [x] Manifest binds R2-14A merge `52c03c8`, contract `1.0.0`, and ADR 0008.
- [x] Readiness passes before result access and constructs all 20 seeds, two
  scenarios, three folds, and 17 diagnostics.
- [x] Seed domains are disjoint; no reserved or final-holdout identity,
  membership, row, prediction, or result exists.
- [x] Every diagnostic `D1`–`D17` runs or records a governed failure without
  retry, replacement, selective exclusion, or denominator alteration.
- [x] D16 evaluates all 320 cells in frozen order without early stopping, and
  D17 evaluates all simultaneous constraints.
- [x] Protected values are purpose-bound, cells below 10 policies are suppressed,
  and all row-level intermediates are purged.
- [x] Every hypothesis receives exactly one reproducible disposition.
- [x] The selected response is the smallest response authorized by the causal
  decision table.
- [x] Manifest, report, and disposition projections reproduce byte-for-byte.
- [x] ADR 0009 and a versioned v5 specification freeze the successor and R2-14C
  gates, or evidence records `stop`/keeps R2-14C blocked.
- [x] Historical v1 through v4 artifacts remain unchanged.
- [x] Two clean evidence builds are byte-identical.
- [x] Focused tests, `make check`, `git diff --check`, and hosted CI pass.

## Required pull-request evidence

- Complete readiness output and planned-versus-executed inventory accounting.
- Proof of strict seed-domain separation and absent reserved/final-holdout data.
- The deterministic manifest, report, and hypothesis disposition artifacts.
- D16 accounting for all 320 ordered cells and the D17 constraint result.
- Suppression, protected cleanup, and governed-failure evidence.
- Evidence-to-response mapping under the causal decision table.
- Proposed ADR 0009 and versioned v5 specification, or an explicit `stop`.
- Two byte-identical clean evidence builds.
- Focused test, full `make check`, `git diff --check`, and hosted CI results.

## Proposed implementation order

1. Verify predecessor identities, clean-tree assumptions, and contract digests.
2. Implement fail-closed readiness and complete inventory construction.
3. Add protected execution, aggregation, suppression, and cleanup primitives.
4. Implement and test diagnostics `D1` through `D15`.
5. Implement the complete ordered D16 surface and D17 constraint evaluation.
6. Execute the inventory once on seeds `20280101..20280120`.
7. Generate the authoritative manifest and deterministic projections.
8. Mechanically derive dispositions and the permitted successor response.
9. Draft ADR 0009 and the v5 specification, or record `stop`.
10. Run two clean builds, focused tests, `make check`, and `git diff --check`.
11. Reconcile current-facing status and open the pull request with all evidence.

## Stop conditions

Stop and keep R2-14C blocked if readiness fails, a seed domain overlaps, an
authorization identity or digest mismatches, result access precedes readiness,
inventory denominators cannot be preserved, cleanup or suppression fails, D16
cannot complete all 320 cells, a disposition is ambiguous, the causal table does
not authorize a coherent response, or reserved/final-holdout data is discovered.

## Completion record

Complete only after merge:

| Field | Value |
| --- | --- |
| Issue | [#78](https://github.com/anilreddy89/Inforsight/issues/78) |
| Pull request | TBD |
| Merge commit | TBD |
| Merge date | TBD |
| Diagnostic manifest digest | `fe6fb12d4eea65542fd5a6f82e1d086181dbdf448c96042ecfc085138c291b13` |
| Hypothesis dispositions | H1: supported, H2: rejected, H3: supported, H4: rejected, H5: rejected, H6: supported |
| Feasibility decision | `infeasible` (0/320 cells meet simultaneous constraints) |
| ADR 0009 decision | `stop` (`stop_infeasible_foundation`) |
| V5 specification version | No v5 specification drafted; stop recorded in ADR 0009 |
| R2-14C status | Blocked until an independent foundational review is approved |
| Reserved acceptance | `not_materialized` |
| Final holdout | Undefined and `not_materialized` |
