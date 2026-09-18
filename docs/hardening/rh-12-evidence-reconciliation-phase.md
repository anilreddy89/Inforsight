# RH-12: Regenerate evidence and reconcile scientific and product claims

Status: complete and merged to `main` through [issue #128](https://github.com/anilreddy89/Inforsight/issues/128) and [PR #181](https://github.com/anilreddy89/Inforsight/pull/181), merge `1365ee5`
Release: `v0.3.1-decision-engine-hardening`  
Classification: documentation and evidence correction  
Priority: release blocking  
Dependencies: RH-01 through RH-11; RH-11 issue #179 / PR #180 merged as `33ffc9a`  
Downstream: RH-13 release disposition

## Purpose

RH-12 regenerates the economic and qualification evidence affected by the RH
contract repairs, then reconciles active scientific, product, maturity, and
release claims with the corrected evidence. Historical reports and manifests
remain immutable. Corrected results must be versioned or explicitly linked as
superseding context rather than silently replacing earlier bytes.

RH-12 reports synthetic, conditional modeled results honestly. It does not
establish causal treatment effects, realized profit, carrier validity, fairness
or demographic parity, external validity, production readiness, or Phase 4
readiness. RH-13 owns the final `PROCEED`, `REMEDIATE`, or `STOP` decision.

## Required outcome

The completed increment must provide a reproducible evidence and documentation
reconciliation that:

- answers a predeclared primary estimand;
- keeps frozen-assignment sampling uncertainty separate from
  new-portfolio allocation-procedure performance when both are reported;
- reruns the accepted RH-05 allocation procedure with identical cohort,
  cutoff, eligibility, catalog, economics, budget, and personnel assumptions;
- reports supported operational, queue, harm, value, and policy-count
  objectives with their exact meanings and limitations;
- separates predictive discrimination, calibration, treatment effect, modeled
  business value, and external-validity claims;
- makes queue precision/recall, value-versus-count tradeoffs,
  fairness/access limitations, and combined lapse/surrender mapping explicit;
- preserves the Protocol 3.1.0 post-result amendment and acceptance-seed reuse
  disclosure;
- reconciles the repository's public status documents and phase totals; and
- records whether independent simulator issue #130 is incorporated,
  superseded, or deferred.

## Scope

### RH-12 owns

- corrected OPE/economic and qualification evidence generated under the
  versioned RH-04 economics/resource contract and RH-05 allocation contract;
- the two RH-04 estimands:
  - **frozen-assignment sampling uncertainty:** policy-cluster resampling of
    already frozen assignments, scores, effects, and economics assumptions;
  - **new-portfolio allocation-procedure performance:** policy-cluster
    resampling that reruns the accepted allocator with the original total
    budget and personnel capacities held fixed;
- explicit policy-cluster bootstrap identity, duplicate-occurrence handling,
  capacity treatment, seed, resample count, source cohort, snapshot, model,
  allocator, and economics identities;
- identical-context comparison of non-intervention, rules-only, risk-ranked,
  and allocation-engine strategies;
- supported reporting of lead time, recall at capacity, unnecessary contacts,
  expected harm, modeled premium value, policy counts, queue metrics, and
  allocation feasibility;
- the bounded v5 infeasibility statement and the distinction between
  predictive, calibration, treatment-effect, value, and external-validity
  claims;
- updates to `README.md`, `MODEL_CARD.md`, `docs/backlog.md`, the roadmap,
  `docs/limitations.md`, release notes, ADR/phase totals, and P4 scaffold
  status;
- `docs/realism-boundary.md` and
  `docs/showcase/system-walkthrough.md`; and
- the final RH-12 disposition of issue #130.

### Out of scope

- rewriting or mutating historical Phase 3 reports, manifests, model bundles,
  or release artifacts;
- refitting predictive models, recalibrating on evaluation resamples, or
  re-estimating treatment effects during bootstrap;
- accessing, transforming, predicting, or evaluating a final holdout;
- fresh acceptance-seed confirmation unless it is predeclared in a separate
  experiment issue before execution;
- claiming real-carrier validity, realized profit, customers saved, causal
  uplift, demographic fairness, universal grounding, or production readiness;
- production deployment or P4-02/P4-03 implementation; and
- RH-13's final release decision.

## Dependency and merge order

```text
RH-04D / RH-04I (merged)
  -> RH-05D / RH-05I (merged)
  -> RH-06 through RH-10 (merged)
  -> RH-11 issue #179 / PR #180 (merged `33ffc9a`)
  -> RH-12 issue #128 / corrected evidence 1.0.0
  -> RH-13 release disposition
```

Issue #128 is the canonical RH-12 implementation issue. Its implementation is
merged to `main` through PR #181 as `1365ee5`, from branch
`test/128-rh-12-evidence-reconciliation`.

Independent issue #130 is deferred from experiment execution. RH-12 records
that fresh stress variants require a separate predeclared experiment issue and
do not authorize a favorable-result assumption or final-holdout access.

## Acceptance gate

- [x] RH-11 and all declared predecessors are merged and closed before evidence regeneration begins.
- [x] Corrected OPE reports a predeclared primary estimand; fixed-assignment and portfolio-reallocation results remain separate.
- [x] Portfolio resampling declares `policy_id` clustering, duplicate occurrence identities, and fixed-versus-scaled capacity treatment.
- [x] Non-intervention, rules-only, risk-ranked, and allocation-engine strategies use one identical comparison context.
- [x] Lead time is explicitly unsupported by the current counterfactual contract; modeled recall at capacity, modeled non-beneficial contacts, expected harm, modeled premium value, policy counts, and feasibility are reported where supported.
- [x] Predictive discrimination, calibration, treatment effect, modeled business value, and external validity are presented as separate claims.
- [x] Queue precision/recall, value-versus-count tradeoffs, fairness/access implications, and combined lapse/surrender target mapping are explicit.
- [x] The v5 infeasibility statement is bounded to the examined design and search space.
- [x] Protocol 3.1.0's post-result amendment and acceptance-seed reuse remain visible; fresh-seed confirmation is not run and requires a separate predeclared issue.
- [x] Issue #130 receives a documented defer disposition.
- [x] `README.md`, `MODEL_CARD.md`, backlog, roadmap, limitations, release notes, phase totals, and P4 status agree.
- [x] `docs/realism-boundary.md` distinguishes modeled, simplified, and excluded behavior.
- [x] `docs/showcase/system-walkthrough.md` documents the bounded reviewer journey.
- [x] Corrected artifacts are versioned and supersession-linked; historical artifacts remain byte-identical.
- [x] No final holdout is accessed, transformed, predicted, or evaluated.
- [x] Focused RH-12 tests, `make check`, `make rh12-evidence-check`, repository boundary checks, and `git diff --check` pass.

## Issue creation map

RH-12 already has its canonical open issue. Do not open a duplicate. If the
issue must be recreated because the existing issue is unavailable, use one
issue from `.github/ISSUE_TEMPLATE/implementation.yml`:

| Work | Template | Title | Required labels | Milestone |
| --- | --- | --- | --- | --- |
| RH-12 | Implementation task | `[Implementation] RH-12: Regenerate evidence and reconcile scientific and product claims` | `implementation`, plus `documentation` and/or `testing` if configured | `v0.3.1-decision-engine-hardening` |

Use the exact field guidance in `docs/engineering-improvement-workflow.md`.
The existing issue [#128](https://github.com/anilreddy89/Inforsight/issues/128)
already contains the RH-12 outcome, scope, claim boundary, acceptance checks,
dependencies, and repository-boundary confirmations.

## Claim and artifact impact

During RH-12 implementation, evidence regeneration and documentation
reconciliation remained within the existing RH claim freeze. The corrected
artifacts are now versioned and published; RH-13 subsequently recorded the
evidence-backed `PROCEED` release disposition. Any Phase 4 implementation must
still pass its own acceptance gates and must not broaden the reconciled claim
boundary.

RH-12 should not change a runtime contract or deterministic serialized output.
If corrected evidence changes bytes or meaning, assign a new artifact/report
version, write a manifest and supersession note, and preserve the original
artifact. Any newly discovered contract change requires a separately reviewed
versioning and migration decision before implementation.

## Completion evidence

The RH-12 closeout should link:

- issue #128, PR #181, merge commit `1365ee5`, milestone, and required CI;
- corrected report and manifest paths, versions, hashes, seeds, cohort/snapshot
  identities, and exact estimand definitions;
- the identical-context strategy comparison and supported objective metrics;
- the claim-reconciliation matrix across README, model card, backlog, roadmap,
  limitations, release notes, ADR/phase totals, and P4 status;
- the realism boundary and reviewer walkthrough;
- the issue #130 disposition and any separate predeclared experiment issue;
- proof that historical artifacts remain unchanged and no final holdout was
  accessed; and
- the exact bounded claims handed to RH-13.

**Closeout record:** RH-12 generated corrected evidence from the merged RH-11
mainline and merged to `main` through [PR #181](https://github.com/anilreddy89/Inforsight/pull/181)
as `1365ee5` on 2026-09-18. The manifest digest is
`47ac6e06793e66b20601a05486fbb24fe24ff91bbffc4acda8e4523853527933` and the
report/manifest are published at
`docs/experiments/phase-rh-12-evidence-reconciliation-1.0.0.{md,json}`. The
historical Phase 3.08 manifest/report hashes are recorded in the corrected
manifest and were not rewritten. Issue #130 is deferred. RH-13 remains the
release and Phase 4 resume decision.
