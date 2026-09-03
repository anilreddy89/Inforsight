# Phase 2R — Post-v4 Qualification Redesign Plan

Status: R2-14A is active through
[issue #76](https://github.com/anilreddy89/Inforsight/issues/76) after R2-14
mechanically decided `redesign` on the complete development qualification block.
This plan does not itself authorize implementation or result-producing execution.

## Trigger and objective

R2-14 implemented substrate `4.0.0` and ran the frozen qualification protocol on
all 20 development seeds. Structural controls, driver support, exact transform
parity, and matched-null behavior passed. Observable recovery, aggregate recovery,
probability quality, reference recovery, and hazard validity failed:

- `0/20` seeds reached median-fold observable-oracle AUC `>=0.65`;
- across-seed median observable-oracle AUC was `0.5666277193591145`, below
  `0.68`;
- median AP lift was `0.021991623169585837`, below `0.10`;
- median Brier skill was positive but only `0.0034835078850924406`;
- `0/20` seeds reached the reference-model recovery rule; and
- maximum monthly terminal hazard was `0.21847588960475323`, above `<0.20`.

The objective is to explain those failures using a separately governed diagnostic
boundary, approve the smallest coherent versioned correction, and demonstrate
design capacity on development data before R2-15 is allowed to begin.

## Non-negotiable boundaries

- Preserve v1 through v4 contracts, code paths, artifacts, and decisions as
  immutable historical evidence.
- Treat R2-14 qualification output as spent design evidence. It may be summarized
  and used to define hypotheses, but row-level results must not drive iterative
  parameter search.
- Do not alter the frozen qualification thresholds merely because v4 failed them.
  A threshold change requires independent scientific justification and an
  explicit reviewed protocol amendment.
- Do not generate, inspect, score, or derive membership for seeds
  `20271201..20271220`. Preserve that namespace as untouched and unmaterialized
  until a later reviewed decision explicitly assigns or retires it.
- Keep the final release holdout undefined and `not_materialized`.
- Keep P2-08/P2-09 paused and P2-10 through P2-12 blocked.
- Do not modify v4 in place. Any approved mechanism change must use new contract,
  registry, schema, identity, artifact, and entry-point versions.
- Commit no raw matrix, row-level prediction, fitted model, oracle sidecar,
  frailty draw, outcome uniform, or bootstrap sample.

## Failure hypotheses

The follow-up must distinguish these explanations before choosing a design:

1. **Insufficient observable log-hazard spread.** Doubling coefficients improved
   median oracle AUC from the v3 diagnostic result near `0.5333` to `0.5666`, but
   not enough to meet the frozen recovery boundary.
2. **Competing-risk or horizon attenuation.** Monthly signal may not translate to
   adequate 90-day union-label separation after survival and competing-risk
   aggregation.
3. **Probability-scale misspecification.** The observable oracle may rank some
   outcomes while producing too little AP lift or Brier improvement at the
   realized prevalence.
4. **Reference-model specification mismatch.** Exact feature parity passes, but
   the governed reference form may not represent the nonlinear discrete-time
   hazard and 90-day union transformation closely enough.
5. **Hazard-tail concentration.** The coefficient/intercept combination creates a
   small region above the `<0.20` monthly hazard ceiling even though aggregate
   recovery remains weak.
6. **Qualification target/design incompatibility.** The fixed estimand, prevalence,
   and thresholds may be mutually infeasible under acceptable hazard bounds. This
   may be concluded only from a predeclared feasibility analysis, not from lowering
   a failed threshold after inspection.

## Proposed gated sequence

### R2-14A — Close out v4 and authorize diagnostics

This is a documentation-and-contract increment. It must:

- record the R2-14 merge, issue closure, reproducible evidence, and mechanical
  `redesign` decision across README, backlog, limitations, and change tracking;
- supersede ADR 0007 for future development while preserving it historically;
- freeze exact diagnostic algorithms, aggregate-only outputs, tolerances,
  suppression/cleanup rules, and stop conditions for each hypothesis;
- assign a new development-only seed namespace disjoint from every historical or
  reserved acceptance namespace; and
- declare a causal decision table mapping each possible finding to permitted v5
  changes before any new diagnostic result exists.

No simulator, coefficient, candidate, feature, fold, threshold, or corpus change
is allowed in R2-14A.

Exit gate: the diagnostic contract is reviewed, digest-bound, reproducible, and
contains no ambiguity capable of changing a result or disposition.

### R2-14B — Execute bounded diagnostics and approve v5

Run the frozen diagnostic inventory exactly once on the complete new development
block. At minimum, publish aggregate evidence for:

- monthly linear-predictor and cause-specific hazard distributions by fold;
- exact 90-day cumulative-incidence decomposition with competing-risk attenuation;
- oracle AUC, AP lift, calibration, and Brier decomposition by seed and fold;
- reference models that separately test exact hazard-form recovery and the current
  governed approximation;
- hazard-tail attribution by registered term and interaction; and
- a constrained feasibility surface declared before execution, reporting whether
  the recovery and hazard gates can be satisfied simultaneously.

Every hypothesis must receive exactly one `supported`, `rejected`, or `unresolved`
disposition. A new ADR may approve only the smallest coherent response allowed by
the pre-result decision table. It must freeze v5 equations, coefficients,
intercepts, event support, estimand, features, reference specification, candidates,
folds, qualification rules, versions, and identities before implementation.

Exit gate: an accepted v5 ADR and contract exist, or the work records `stop` if no
defensible design satisfies the frozen scientific and safety constraints.

### R2-14C — Implement and qualify v5

Implement the approved v5 substrate on separate paths and execute its development
qualification once. Required controls include:

- exact simulator/oracle/feature transform parity;
- dual-time, matched-stream, atomic-intervention, lineage, protected-oracle, and
  deterministic replay invariants;
- observable-oracle seed and aggregate recovery;
- AP-lift and Brier-skill probability quality;
- reference-model recovery;
- driver support and null behavior;
- finite monthly hazards below the frozen ceiling; and
- historical artifact immutability plus acceptance/holdout absence.

Any required failure returns `redesign` or `stop`; it does not authorize tuning,
threshold weakening, R2-15, or acceptance access.

Exit gate: all frozen development qualification rules pass and artifacts reproduce
byte-for-byte.

### R2-15 and R2-16 — Preserve existing intent

Only after R2-14C passes may R2-15 freeze governed evaluation, memberships,
preprocessing, candidate selection, and fitted-state digests. Only after R2-15
merges may R2-16 access a separately authorized untouched acceptance block once.
Only a merged R2-16 `proceed` decision resumes governed Phase 2 work.

## Dependency order

```text
R2-14 merged with redesign
  -> R2-14A closeout and diagnostic authorization
  -> R2-14B bounded diagnostics and v5 design approval
  -> R2-14C v5 implementation and development qualification
  -> R2-15 evaluation and candidate freeze
  -> R2-16 one-shot fresh acceptance
  -> resume Phase 2 only on proceed
```

## Recommended immediate issue

Create one documentation/governance issue for R2-14A in the
`v0.2.0-risk-model` milestone. The issue should be release-blocking and should use
a branch named `docs/<issue>-r2-14a-v4-closeout-v5-diagnostics`. Its pull request
must not contain simulator or result-producing changes.
