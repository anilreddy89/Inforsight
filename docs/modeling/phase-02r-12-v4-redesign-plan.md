# Phase 2R v4 Signal-Recovery Redesign Plan

Status: R2-13 completed through issue #69 and PR #70, merge commit `7c4a1a7`;
R2-14 v4 implementation and development qualification are next.

## Trigger and objective

Phase R2-11 mechanically decided `redesign` under protocol `2.2.0`. Structural
readiness passed for all 20 signal/null pairs, but the selected candidate did not
recover the fictional signal: `0/20` signal seeds reached median-fold AUC `0.65`,
the across-seed median was `0.518869`, and `0/20` matched-null improvements reached
`0.10`. The median average-precision lift was `0.009834` and median Brier skill was
`-0.011851`.

The objective of the next workstream is to determine why observable signal is not
recoverable, approve a new versioned substrate with demonstrated design capacity,
and evaluate it once on a fresh acceptance seed block. It must not tune v3, rerun
selected v3 seeds, weaken a failed rule, or use the final release holdout.

## Non-negotiable boundaries

- R2-11 is merged as `76c8cd3`; start every dependent redesign branch from that
  updated `main` baseline.
- Preserve all v1, v2, and v3 contracts, code paths, manifests, and decisions as
  immutable historical evidence.
- Keep P2-08/P2-09 paused, P2-10 through P2-12 pending and blocked, and the final
  holdout `not_materialized` until a merged replacement acceptance decision is
  `proceed`.
- Treat the 20 R2-11 signal/null pairs as spent acceptance evidence. They may be
  summarized for failure classification but may not be used for coefficient,
  feature, candidate, or threshold selection.
- Use a separately named development seed block for redesign diagnostics and a
  disjoint, predeclared acceptance seed block for the final gate.
- Keep the estimand, three-fold rolling-origin structure, policy-cluster
  resampling, core metrics, and protocol `2.2.0` numeric acceptance thresholds by
  default. Any change requires an explicit reviewed version amendment before the
  new acceptance block is materialized.
- No raw matrix, row-level prediction, executable fitted object, oracle sidecar,
  bootstrap sample, or final holdout is committed.

## Failure hypotheses to distinguish

The redesign must test these explanations rather than assuming that larger
coefficients are the answer:

1. **Low oracle separability:** the observable component of the frozen v3 hazard
   may be too weak relative to frailty, baseline incidence, and outcome noise.
2. **Weak realized driver support:** nonzero driver terms may have insufficient
   variance or prevalence within governed folds, despite aggregate class support.
3. **Feature/mechanism mismatch:** model features may not reproduce the exact
   cutoff transforms, categories, interactions, or visibility semantics used by
   the outcome mechanism.
4. **Episode and weighting dilution:** repeated observations, episode construction,
   or fitting weights may obscure policy-level signal even though authorization
   and leakage controls pass.
5. **Candidate learning failure:** the frozen candidate or preprocessing may fail
   to learn signal that the observable oracle and a correctly specified reference
   model can recover.
6. **Temporal instability:** fold-specific prevalence or driver support may make a
   stable mechanism unrecoverable under the frozen rolling-origin design.

## Gated workstream

### R2-12 - Close out v3 and approve redesign diagnostics

Publish the merged R2-11 decision and a diagnostic contract. The contract must
define the development seed block, permitted aggregate outputs, protected oracle
handling, hypothesis tests, multiplicity/selection boundaries, and a rule that
diagnostic results cannot become replacement acceptance evidence.

Acceptance checks:

- R2-11 is merged, its issue is closed, and current status says `redesign`.
- The v3 decision and artifacts reproduce byte-for-byte.
- The diagnostic contract maps every proposed output to one of the six hypotheses.
- Development and future acceptance seed namespaces are disjoint and frozen.
- No simulator, coefficient, feature, candidate, protocol threshold, or final
  holdout changes occur in this increment.

### R2-13 - Execute bounded root-cause diagnostics and approve v4 design

Run only the reviewed diagnostics on the development block. Report, by seed and
fold, observable- and conditional-oracle discrimination, driver support and
variance, transform parity, reference-model recovery, candidate recovery,
policy/episode sensitivity, and temporal stability. Then supersede ADR 0005 with
a v4 decision and freeze the new substrate and protocol before acceptance seeds
exist.

The design review must use a causal decision table:

| Finding | Permitted design response |
| --- | --- |
| Observable oracle is weak | Rebalance observable coefficients, frailty, or incidence under a new coefficient registry |
| Drivers lack support | Change event-generation prevalence or eligibility under a new corpus version |
| Transform parity fails | Repair the feature/observation contract and add exact parity tests |
| Reference model succeeds but candidate fails | Revise the candidate set or selection rule before acceptance |
| Episode sensitivity dominates | Revise sampling/weighting with policy-level justification |
| Fold instability dominates | Revise drift or fold design without outcome-conditioned membership |

Acceptance checks:

- Each hypothesis has a supported, rejected, or unresolved disposition with
  aggregate evidence.
- The chosen response is the smallest coherent change supported by that evidence.
- A v4 contract freezes equations, coefficient provenance, stream ownership,
  corpus size, roles, folds, feature groups, candidates, selection, diagnostics,
  resampling, robustness variants, decision rules, and tolerances.
- Design-qualification gates are declared before v4 implementation output. At a
  minimum they cover observable-oracle recoverability, driver support, exact
  mechanism/feature parity, null behavior, and reference-model recovery.
- The fresh acceptance seed block remains unmaterialized.

### R2-14 - Implement and qualify the v4 substrate

Implement the approved v4 event/corpus/observation path and exact oracle, then run
only the predeclared development qualification gates. A failed qualification gate
returns to R2-13 under another reviewed version; it does not permit iterative use
of the acceptance block.

Acceptance checks:

- v4 has separate types, entry points, identities, schemas, and artifact paths.
- Point-in-time, dual-time, matched-stream, atomic-intervention, protected-oracle,
  deterministic replay, and mutation tests pass.
- All design-qualification gates pass on the development block.
- Historical artifacts remain byte-identical and the final holdout is absent.

### R2-15 - Freeze v4 evaluation and the release candidate

Build governed folds, features, preprocessing, diagnostics, authorization, and
candidates from the approved v4 design. Select once using the designated selection
role and freeze every fitted-state and membership digest needed for acceptance.

Acceptance checks:

- Every fold meets predeclared independent-policy, episode, class, category, and
  driver-support requirements without outcome-conditioned regeneration.
- Feature/mechanism transform parity and protected-concept rejection pass.
- Diagnostics authorize comparison and the deterministic rule selects exactly one
  candidate.
- Acceptance membership and outcomes have not been accessed or scored.

### R2-16 - Run fresh v4 statistical acceptance

Execute readiness first on the untouched acceptance block. If authorized, execute
all required signal, matched-null, shuffle, oracle-ordering, calibration-sanity,
learning, ablation, robustness, interval, and temporal families. Publish exactly
one mechanical `proceed`, `redesign`, or `stop` decision.

Acceptance checks:

- Readiness and scoring use only frozen R2-13 through R2-15 identities and digests.
- All required families run unless a predeclared decisive termination rule applies;
  incomplete required families remain failures.
- The manifest, report, and decision reproduce deterministically.
- Only a merged `proceed` resumes P2-08; `redesign` or `stop` creates another
  focused reviewed action and preserves the pause.

## Dependency order

```text
R2-11 merged as 76c8cd3
  -> R2-12 diagnostic authorization
  -> R2-13 diagnostics and v4 design approval
  -> R2-14 v4 implementation and qualification
  -> R2-15 evaluation and candidate freeze
  -> R2-16 fresh statistical acceptance
  -> resume governed Phase 2 work only on proceed
```

## Recommended immediate issue

Open R2-14 from updated `main` after the R2-13 merge. Implement substrate `4.0.0`
and run only the frozen development qualification gates. R2-14 must not access the
future acceptance seed block; any failed qualification returns to reviewed design.
