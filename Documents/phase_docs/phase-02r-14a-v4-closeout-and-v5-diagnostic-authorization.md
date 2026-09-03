# Phase 2R.14A — v4 Closeout and v5 Diagnostic Authorization

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2R — Modeling Foundation Remediation Gate, post-v4 redesign extension |
| Sequence | R2-14A |
| Change tracker ID | `R2-14A` |
| GitHub issue | [#76](https://github.com/anilreddy89/Inforsight/issues/76) |
| Issue title | `ADR: R2-14A close out v4 and authorize bounded v5 redesign diagnostics` |
| Branch | `docs/76-r2-14a-v4-closeout-v5-diagnostics` |
| Pull request | [#77](https://github.com/anilreddy89/Inforsight/pull/77) |
| Status | Completed on 2026-09-03 through PR #77, merge commit `52c03c8`; R2-14B diagnostic execution is authorized, but v5 implementation remains blocked |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Evidence closeout, architecture decision, and diagnostic governance |
| Strict predecessor | R2-14, merged through issue #72 and PR #73 as merge commit `4b234bf` on 2026-09-02 |
| Blocks | R2-14B bounded diagnostics and v5 design; R2-14C v5 implementation and qualification; R2-15/R2-16; P2-08 through P2-12 remain blocked |
| Governing evidence | R2-14 v4 qualification manifest, report, decision, and mechanical `redesign` result |
| Historical substrate/evaluation | v4 substrate `4.0.0`, coefficient registry `2.0.0`, stream registry `2.0.0`, protocol `3.0.0` |
| Spent development seeds | `20271101` through `20271120`, inclusive; aggregate evidence only |
| Reserved acceptance seeds | `20271201` through `20271220`, inclusive; must remain unmaterialized and inaccessible |
| Final holdout | Must remain undefined and `not_materialized` throughout R2-14A |
| Last reviewed | 2026-09-03 |

## Objective

Close out the merged R2-14 v4 development qualification result and approve a
fail-closed, versioned boundary for post-v4 diagnostics before any v5 simulator,
coefficient, event-support, feature, reference-model, candidate, fold, estimand,
or protocol change is designed or implemented.

R2-14A must reconcile current-facing repository status with the authoritative v4
evidence, preserve the failed v4 block as immutable historical evidence, define
the exact hypotheses and diagnostic inventory permitted in R2-14B, freeze a new
development-only information domain, and predeclare how diagnostic findings may
map to a successor design.

R2-14A is a documentation and governance increment. It produces no new corpus,
observation, oracle value, fitted model, prediction, metric, coefficient search,
feasibility result, candidate selection, acceptance artifact, or final holdout.

## Why this work is next

R2-14 implemented the exact v4 substrate approved by ADR 0007 and completed the
frozen qualification inventory across all 20 development seeds and three folds.
The result was mechanically `redesign`:

| Gate or measure | Observed | Required | Result |
| --- | ---: | ---: | --- |
| Seed-level observable-oracle recovery | `0/20` | At least `16/20` at median-fold AUC `>=0.65` | Fail |
| Aggregate observable-oracle recovery | `0.5666277193591145` | Across-seed median AUC `>=0.68` | Fail |
| Observable-oracle AP lift | `0.021991623169585837` | Median `>=0.10` | Fail |
| Observable-oracle Brier skill | `0.0034835078850924406` | Median `>0` | Pass component, insufficient family result |
| Reference-model recovery | `0/20` | At least `16/20` at median-fold AUC `>=0.65` | Fail |
| Maximum monthly terminal hazard | `0.21847588960475323` | Finite and `<0.20` for every row | Fail |
| Driver support | Complete pass counts across registered terms and folds | Frozen support rules | Pass |
| Transform parity | `0` mismatches | Zero within `1e-12` | Pass |
| Matched-null oracle AUC | `0.5` | `[0.45,0.55]` | Pass |
| Matched-null candidate AUC | `0.4998253417630266` | `[0.45,0.55]` | Pass |
| Structural controls | All required controls pass | Complete pass | Pass |

V4 improved median observable-oracle AUC over the v3 diagnostic value near
`0.5333`, but the improvement remained far below the frozen recovery rules and
introduced a hazard-cap violation. Exact parity and driver support passing rule
out two previously suspected implementation explanations. The failed result does
not, however, distinguish insufficient public score spread, competing-risk or
horizon attenuation, probability-scale behavior, reference specification,
hazard-tail concentration, or incompatibility among the frozen design targets.

ADR 0007 explicitly requires supersession when v4 fails a frozen qualification
gate. R2-15 therefore cannot begin. Another coefficient adjustment or selected
rerun without a reviewed diagnostic boundary would turn qualification data into
an informal tuning loop and weaken the interpretation of any later acceptance.

## Immutable evidence and boundaries

- R2-14 is merged on `main` through PR #73 and merge commit `4b234bf`. Its v4
  configuration, code, tests, manifest, report, decision, and mechanical
  `redesign` result are historical evidence.
- ADR 0007 remains the historical authority for v4 implementation. R2-14A may
  supersede it only for future development; it must not rewrite its rationale or
  reinterpret the failed result.
- V1, v2, v3, and v4 types, modules, contracts, registries, schemas, corpora,
  observations, artifacts, reports, and decisions must not be overwritten or
  reclassified.
- Seeds `20261001..20261020` remain spent v3 acceptance evidence.
- Seeds `20271101..20271120` are now spent v4 development qualification evidence.
  R2-14A and later design work may cite committed aggregates but must not use
  protected row-level outcomes, predictions, oracle values, or fitted state for
  parameter search or selective redesign.
- Seeds `20271201..20271220` remain reserved, unmaterialized, and inaccessible.
  R2-14A must not assign them to v5, retire them, derive membership, generate
  outcomes, fit or score models, or publish any result about them.
- The final holdout seed, identity, membership, distribution, rows, transforms,
  predictions, and metrics remain undefined and `not_materialized`.
- P2-08/P2-09 remain paused. P2-10 through P2-12 remain pending and blocked.
- No frozen v4 threshold may be weakened because v4 failed it. Any later threshold
  amendment requires independent scientific justification, versioning, and
  review before successor development output.
- No synthetic result establishes prospective performance, actuarial validity,
  causality, fairness, operational value, customer impact, conservation efficacy,
  production readiness, or release readiness.

## Governed diagnostic hypotheses

R2-14A must authorize only diagnostics that resolve one of these hypotheses.
Unregistered exploratory output is prohibited.

### H1 — Insufficient observable log-hazard spread

The v4 public linear predictor may have too little between-policy and within-fold
variation to produce the frozen 90-day ranking target while satisfying the hazard
ceiling.

Required R2-14B evidence:

- aggregate linear-predictor distributions by cause, seed, fold, and scenario;
- registered-term contribution and covariance summaries;
- signal-to-baseline and signal-to-frailty variance ratios; and
- monotonicity and saturation summaries that do not disclose row-level values.

### H2 — Competing-risk or horizon attenuation

Monthly cause-specific signal may be attenuated when converted through survival,
competing-risk normalization, and the three-month union target.

Required R2-14B evidence:

- exact aggregate decomposition from monthly logits to monthly hazards and
  90-day cumulative incidence;
- cause-specific versus union-label oracle discrimination;
- survival and competing-event attenuation summaries; and
- fold-level incidence and censoring decomposition under unchanged memberships.

### H3 — Probability-scale behavior

The observable oracle may provide limited rank separation and too little
probability-quality improvement at realized prevalence even when Brier skill is
slightly positive.

Required R2-14B evidence:

- full frozen ROC AUC, AP lift, Brier, and calibration decomposition by seed and
  fold;
- prevalence-normalized and prevalence-sensitive components clearly separated;
- conditional-oracle versus observable-oracle ordering; and
- deterministic aggregate reliability summaries with protected cells suppressed.

### H4 — Reference-model specification mismatch

Feature/mechanism transform parity passes, but the governed reference model may
not reproduce the nonlinear discrete-time competing-risk transformation used by
the oracle.

Required R2-14B evidence:

- exact contract-derived score recovery;
- a reference that reproduces the hazard form and horizon aggregation exactly;
- the current governed reference on identical memberships; and
- convergence, coefficient-recovery, prediction-variance, and ordering summaries
  sufficient to distinguish reference misspecification from weak oracle signal.

Reference diagnostics remain purpose-bound. They cannot silently become ordinary
candidates or enter R2-15 selection.

### H5 — Hazard-tail concentration

A limited combination of coefficients, interactions, baseline offsets, or rare
driver configurations may create the observed `0.21847588960475323` maximum even
though aggregate recovery remains weak.

Required R2-14B evidence:

- aggregate hazard quantiles and exceedance counts by cause, seed, fold, and
  scenario;
- tail attribution to registered terms and interactions;
- clipping and joint-support summaries for tail-driving configurations; and
- proof that protected or small cells are suppressed.

### H6 — Qualification target/design incompatibility

The fixed estimand, realized prevalence, recovery thresholds, AP-lift target, and
monthly hazard ceiling may be mutually infeasible under the allowed mechanism
class.

Required R2-14B evidence:

- a constrained feasibility procedure fully specified before execution;
- a bounded, deterministic design grid or analytic surface whose axes and limits
  do not change after results are observed;
- simultaneous reporting of recovery, probability-quality, incidence, and hazard
  constraints; and
- a mechanical `feasible`, `infeasible`, or `unresolved` disposition that cannot
  lower a failed threshold.

The feasibility family is diagnostic evidence, not authorization to select the
best-performing grid point as v5.

## Required changes

### 1. Reconcile the R2-14 closeout

Update current-facing status to record issue #72, PR #73, merge `4b234bf`, the
complete qualification inventory, and the mechanical `redesign` decision. At
minimum reconcile:

```text
README.md
PROJECT_PROGRESS.md
docs/backlog.md
docs/limitations.md
docs/experiments/README.md
docs/simulator-process-flow.md
Documents/tracker/Inforsight_Change_Tracker.md
Documents/phase_docs/phase-02r-14-v4-substrate-implementation-and-qualification.md
```

Historical-at-creation documents remain unchanged. Status updates must distinguish
merged evidence from proposed successor work.

### 2. Publish the R2-14A diagnostic authorization contract

Add a normative contract under `docs/modeling/` that freezes:

- the six hypotheses and exact diagnostic inventory;
- a new development-only seed namespace disjoint from historical, spent, reserved
  acceptance, and final-holdout domains;
- scenario pairing, roles, folds, memberships, transforms, references, metrics,
  aggregations, tolerances, and canonical numeric normalization;
- the constrained feasibility procedure, including axes, bounds, resolution,
  ordering, stopping, multiplicity, and interpretation;
- authorization identities and digests for every protected diagnostic purpose;
- permitted committed aggregates, minimum-cell suppression, and protected
  cleanup rules;
- planned-versus-executed inventory accounting and denominator preservation;
- failure, ambiguity, incompleteness, non-finite, tampering, and unexpected-result
  behavior;
- mechanical hypothesis-disposition rules; and
- versioning, reproduction, resource, compatibility, and claim boundaries.

The contract must be executable without analyst or caller discretion. Any material
choice that cannot be frozen from existing aggregate evidence and first principles
must remain unresolved and block R2-14B.

### 3. Freeze information-domain separation

Define at least these non-overlapping domains:

| Domain | Permitted use | Status after R2-14A |
| --- | --- | --- |
| Historical v3 acceptance | Cite committed aggregate failure evidence | Spent and immutable |
| Historical v4 development qualification | Cite committed aggregate evidence and define hypotheses | Spent and immutable |
| New v5 diagnostic development | Execute only the frozen R2-14B inventory | Namespace and derivation frozen; not materialized by R2-14A |
| Reserved seeds `20271201..20271220` | No use until a later reviewed assignment or retirement | Unmaterialized and inaccessible |
| Final release holdout | No use | Undefined and `not_materialized` |

The new development namespace must be frozen before result-producing execution,
must not overlap any previous domain, and must prohibit replacement, retry, or
selective exclusion based on results.

### 4. Define purpose-bound protected execution

R2-14B may compute protected row-level intermediates only inside a purpose-bound,
non-committed execution. The contract must specify:

- exact upstream inputs and digest validation;
- separate authorization for oracle, mechanism decomposition, reference-model,
  hazard-tail, and feasibility families;
- canonical ordering and membership verification before every join or score;
- strict exclusion of oracle, frailty, outcome-uniform, mechanism-only, and target
  concepts from ordinary features and candidate fitting;
- aggregate projection schemas and suppression for cells with fewer than the
  frozen minimum number of unique policies; and
- cleanup plus evidence-digest behavior for every temporary intermediate.

### 5. Predeclare the R2-14B evidence package

Freeze the expected successor package before diagnostic access. Proposed paths:

```text
docs/modeling/phase-02r-14a-v5-diagnostic-authorization-contract.md
docs/experiments/phase-02r-14b-v5-redesign-diagnostic-manifest.json
docs/experiments/phase-02r-14b-v5-redesign-diagnostic-report.md
docs/experiments/phase-02r-14b-v5-hypothesis-disposition.md
```

The future manifest must be authoritative and bind identities, versions, inputs,
planned and executed inventory, aggregate evidence, suppression and failure
accounting, hypothesis dispositions, selected permitted response, downstream
status, reserved-acceptance absence, and `final_holdout: not_materialized`.
Reports and dispositions must be deterministic projections of the manifest.

### 6. Freeze the causal redesign decision table

R2-14A must authorize only evidence-linked successor responses:

| Diagnostic finding | Only permitted R2-14B proposal |
| --- | --- |
| H1 supported | Versioned public-score, frailty, baseline, incidence, or event-support redesign constrained by H5/H6 evidence |
| H2 supported | Versioned competing-risk, horizon, estimand, or mechanism redesign with explicit interpretation impact |
| H3 supported | Versioned probability mechanism or calibration-of-generator redesign; no post-hoc model calibration claim |
| H4 supported while observable oracle is recoverable | Correct the diagnostic/reference specification before candidate interpretation |
| H5 supported | Versioned tail-control or coefficient/intercept redesign that preserves predeclared hazard validity |
| H6 feasible | Approve only the smallest coherent point justified independently of result maximization and freeze it before implementation |
| H6 infeasible | Record `stop` or approve a fundamental estimand/threshold review; do not weaken gates within the same increment |
| Mixed, invalid, or unresolved | Another reviewed diagnostic amendment or `stop`; no guessed v5 design |

When multiple hypotheses are supported, the proposal must explain why every
included change is necessary and why a smaller response cannot address the
evidence. Diagnostic output never directly authorizes implementation.

### 7. Supersede ADR 0007 for future development

Add a new ADR that:

- records the authoritative R2-14 failure without changing its interpretation;
- preserves ADR 0007 and all v4 evidence historically;
- approves only the R2-14B diagnostic boundary;
- records rejected alternatives, including in-place v4 tuning, threshold
  weakening, selected seed reruns, immediate R2-15 entry, and acceptance access;
- defines the conditions for v5 design approval, `redesign`, and `stop`; and
- states that no successor implementation is authorized until a later reviewed
  ADR freezes the v5 design.

### 8. Integrate validation and current status

Add deterministic contract validation for hypothesis coverage, diagnostic
inventory completeness, domain disjointness, authorization identity, aggregate
projection, suppression, cleanup, decision-table completeness, and holdout
absence. Mutation tests must cover omitted diagnostics, overlapping domains,
reserved-acceptance access, stale digests, row reordering, purpose substitution,
oracle leakage, threshold drift, grid expansion, selective result omission,
historical mutation, and attempted holdout creation.

Add the read-only R2-14A contract check to normal repository checks and hosted CI.
Current-facing documentation must say that R2-14A authorizes diagnostics only and
that R2-14B, R2-14C, R2-15, R2-16, and resumed Phase 2 remain blocked.

## Out of scope

- Running any R2-14B diagnostic or feasibility result.
- Choosing v5 coefficients, intercepts, frailty, event rates, mechanism equations,
  feature surface, estimand, folds, candidates, thresholds, or corpus size.
- Modifying v4 code, contracts, registries, artifacts, or qualification evidence.
- Reusing protected R2-14 rows, predictions, oracle values, or fitted state as a
  tuning set.
- Materializing, assigning, retiring, inspecting, or scoring reserved acceptance
  seeds `20271201..20271220`.
- Creating any final-holdout identity, membership, distribution, row, transform,
  prediction, or metric.
- Candidate tuning or selection, R2-15 fitted-state freeze, R2-16 acceptance,
  calibration, operational threshold selection, or model explanations.
- Resuming P2-08/P2-09 or claiming real-world performance, actuarial validity,
  causal effect, fairness, operational utility, production readiness, or release
  readiness.

## Anticipated implementation surface

Expected new or updated paths include:

```text
docs/adr/0008-authorize-post-v4-redesign-diagnostics.md
docs/modeling/phase-02r-14a-v5-diagnostic-authorization-contract.md
scripts/check_r2_14a_diagnostic_contract.py
simulator/tests/test_v5_diagnostic_contract.py
Makefile
.github/workflows/ci.yml
docs/experiments/README.md
docs/simulator-process-flow.md
docs/backlog.md
docs/limitations.md
PROJECT_PROGRESS.md
README.md
Documents/Inforsight_Change_Tracker.md
Documents/phase_docs/phase-02r-14-v4-substrate-implementation-and-qualification.md
Documents/phase_docs/phase-02r-14a-v4-closeout-and-v5-diagnostic-authorization.md
```

Exact normative artifact and validation-script names may be adjusted during issue
review, but the documentation-only boundary, information separation, protected
execution rules, and diagnostic inventory must not drift after approval.

## Acceptance checks

- [x] Issue and branch metadata are filled from an approved R2-14A issue assigned
  to the `v0.2.0-risk-model` milestone.
- [x] R2-14 issue #72, PR #73, merge `4b234bf`, artifact identities, protocol
  `3.0.0`, and mechanical `redesign` decision are recorded accurately.
- [x] README, backlog, limitations, experiment navigation, process flow, progress,
  change tracker, and R2-14 phase status agree on the merged result.
- [x] ADR 0007 remains immutable historical authority for v4 and is superseded
  only for future development.
- [x] The new ADR authorizes diagnostics only and rejects in-place tuning,
  threshold weakening, selective reruns, immediate R2-15, and acceptance access.
- [x] Every permitted diagnostic maps to exactly one or more H1-H6 hypotheses and
  every hypothesis has complete required evidence.
- [x] The diagnostic algorithms, inputs, roles, folds, metrics, aggregations,
  tolerances, suppression, cleanup, and failure behavior are executable without
  caller discretion.
- [x] The constrained feasibility procedure freezes all axes, bounds, resolution,
  ordering, stopping, multiplicity, and interpretation before output.
- [x] A new development-only seed domain is frozen and proven disjoint from spent,
  reserved acceptance, and final-holdout domains.
- [x] Seeds `20271201..20271220` remain unassigned, unmaterialized, and
  inaccessible; the final holdout remains undefined and `not_materialized`.
- [x] Purpose-bound authorization prevents cross-family reuse, membership or model
  substitution, row reordering, stale inputs, oracle leakage, and raw-output
  publication.
- [x] The future R2-14B manifest schema preserves complete planned-versus-executed
  inventory and denominator accounting.
- [x] The causal decision table maps every supported, rejected, unresolved,
  invalid, feasible, and infeasible outcome to an allowed response.
- [x] No v5 simulator, coefficient, event, corpus, observation, feature, model,
  prediction, diagnostic result, or acceptance artifact is produced.
- [x] Historical v1-v4 artifacts remain byte-identical.
- [x] P2-08/P2-09 remain paused and all downstream performance-dependent work
  remains blocked.
- [x] Focused contract and mutation tests, repository-boundary checks,
  `make check`, and `git diff --check` pass locally and in hosted CI.
- [x] Pull-request review and hosted CI complete before R2-14B begins.

## Required pull-request evidence

- R2-14 merge and artifact identity verification.
- Reproduction output for the committed v4 qualification evidence.
- Current-status reconciliation diff and stale-status search results.
- Complete H1-H6 diagnostic inventory and hypothesis coverage report.
- Seed-domain disjointness and reserved-acceptance/final-holdout absence proof.
- Purpose-authorization, aggregate projection, suppression, and cleanup contract
  validation.
- Mechanical causal-decision-table completeness evidence.
- Mutation results for ambiguity, domain overlap, acceptance access, threshold or
  feasibility-grid drift, protected substitution, selective omission, and
  historical tampering.
- Proof that no result-producing v5 path or artifact exists.
- Final focused tests, full `make check`, `git diff --check`, hosted CI, and review
  output.

## Proposed implementation order

1. Review this phase document and open one R2-14A governance issue in the existing
   release milestone.
2. Create `docs/<issue>-r2-14a-v4-closeout-v5-diagnostics` from updated `main` and
   fill the issue, branch, and status metadata above.
3. Bind the R2-14 merge and artifact identities; capture a historical digest
   baseline before editing current-facing documentation.
4. Reconcile R2-14 closeout status across the repository without changing
   historical-at-creation evidence.
5. Draft the successor ADR and normative diagnostic authorization contract,
   including exact H1-H6 algorithms and the causal decision table.
6. Freeze the new development seed namespace, protected execution model,
   aggregate schemas, suppression, cleanup, and reserved-domain absence rules.
7. Add deterministic validation and mutation tests, then wire the read-only check
   into `make check` and hosted CI.
8. Run focused checks, two clean contract reproductions, the full repository
   suite, boundary validation, stale-status searches, and `git diff --check`.
9. Open the R2-14A pull request with required evidence. Do not create an R2-14B
   branch until R2-14A is reviewed and merged.

## Stop conditions

Stop R2-14A and do not authorize R2-14B if:

- the v4 evidence cannot reproduce or its authoritative identity is ambiguous;
- any proposed diagnostic depends on protected R2-14 row-level inspection;
- the new development domain overlaps a spent, reserved acceptance, or holdout
  domain;
- the feasibility analysis retains post-result discretion over its grid, bounds,
  stopping, or interpretation;
- a hypothesis, diagnostic, disposition, or causal response remains materially
  ambiguous;
- the proposed contract permits changing frozen gates because v4 failed them;
- current status implies that R2-15, acceptance, calibration, or performance work
  is authorized; or
- any reserved acceptance or final-holdout material is found to exist.

## Completion record

Complete only after merge:

| Field | Value |
| --- | --- |
| Issue | [#76](https://github.com/anilreddy89/Inforsight/issues/76) |
| Pull request | [#77](https://github.com/anilreddy89/Inforsight/pull/77) |
| Merge commit | `52c03c8` |
| Merge date | 2026-09-03 |
| Final decision | `diagnostics_authorized` under ADR 0008 |
| Diagnostic contract version | `1.0.0` |
| New development domain | Seeds `20280101..20280120`, frozen for the complete R2-14B inventory and not materialized by R2-14A |
| Reserved acceptance | Seeds `20271201..20271220` remain `not_materialized` and inaccessible |
| Final holdout | Undefined and `not_materialized` |
| Hosted verification | Both PR #77 CI runs passed before merge |
