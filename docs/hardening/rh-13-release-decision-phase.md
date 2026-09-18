# RH-13: Qualify and release the hardening initiative

Status: **Completed — PROCEED recorded on 2026-09-18** through [issue #182](https://github.com/anilreddy89/Inforsight/issues/182); qualification passed on clean `main` at `1924dfa`
Release: `v0.3.1-decision-engine-hardening`
Classification: release evidence / decision
Priority: release blocking
Dependencies: RH-00 through RH-12; RH-12 is merged to `main`
Downstream: P4-02/P4-03 resume only after an evidence-backed `PROCEED`

## Purpose

RH-13 is the final hardening release gate. It must qualify the merged state,
reconcile the release package, and record exactly one formal decision:
`PROCEED`, `REMEDIATE`, or `STOP`.

RH-13 does not implement Phase 4. It does not authorize Java, Kafka,
PostgreSQL, cloud deployment, production identity, real-policyholder use, or
any claim beyond the evidence already accepted by RH-00 through RH-12.

## Required outcome

The completed increment must provide a reproducible release decision package
that:

- starts from the final merged `main` commit in a clean working tree;
- reruns the guarded qualification path with the documented headless plotting
  configuration;
- verifies repository boundaries and read-only artifact checks;
- confirms every RH predecessor is merged, closed, and represented by its
  completion evidence;
- distinguishes repaired behavior, superseded historical interpretation,
  preserved historical artifacts, and remaining limitations;
- confirms the RH-12 evidence manifest/report, claim boundary, and issue #130
  deferred disposition are part of the release package;
- records the final decision before creating a tag or GitHub release; and
- updates the P4-02/P4-03 dependency state only according to that decision.

## Decision contract

The decision rules below are predeclared before the final qualification result
is reviewed.

### `PROCEED`

Record `PROCEED` only when all release gates pass:

- every declared predecessor through RH-12 is merged and closed;
- the clean merged-state qualification run passes;
- repository boundaries, read-only checks, and `git diff --check` pass;
- no historical artifact or final-holdout boundary was violated;
- release notes, limitations, README, model card, roadmap, backlog, and P4
  status agree;
- the supported claim set is limited to the evidence in the release package;
- issue #130 remains explicitly deferred or has separately approved evidence;
  and
- no release-blocking limitation remains unresolved.

Only after `PROCEED` may the annotated tag and GitHub release be created.

### `REMEDIATE`

Record `REMEDIATE` when the implementation and qualification evidence are
otherwise bounded, but a release-blocking documentation, packaging, or
qualification gap can be corrected without changing the settled runtime
contract or accessing the final holdout. The decision must name the exact gap,
owner, acceptance checks, and follow-up issue. P4-02/P4-03 remain blocked.

### `STOP`

Record `STOP` for any failed qualification gate, repository-boundary failure,
historical-artifact mutation, final-holdout access, unsupported claim,
unreconciled contract/version drift, or other blocker that invalidates the
release evidence. The stop reason must be preserved as immutable release
evidence, and P4-02/P4-03 remain blocked.

## Scope

### RH-13 owns

- the final clean-state qualification run and environment record;
- verification that RH-00 through RH-12 completion evidence is present;
- the release claim and limitation reconciliation;
- the formal `PROCEED`, `REMEDIATE`, or `STOP` decision;
- the final P4-02/P4-03 dependency status;
- the annotated tag and GitHub release preparation, only after `PROCEED`;
- release notes and closeout tracker updates; and
- issue, PR, merge-commit, artifact, and qualification links for the closeout.

### Out of scope

- P4-02/P4-03 implementation before `PROCEED`;
- new model training, recalibration, treatment-effect fitting, or economic
  assumption changes;
- fresh acceptance seeds or independent simulator stress variants unless a
  separate predeclared issue authorizes them;
- accessing, transforming, predicting, or evaluating the final holdout;
- rewriting historical Phase 2/Phase 3 artifacts;
- production deployment, real customer data, or production-readiness claims;
- changing RH-04, RH-05, RH-09, or RH-10 contracts; and
- reopening or rewriting merged predecessor PRs.

## Dependency and merge order

```text
RH-11 issue #179 / PR #180 (merged `33ffc9a`)
  -> RH-12 issue #128 / PR #181 (merged `1365ee5`)
  -> RH-13 release qualification and decision
  -> P4-02 / P4-03 only if RH-13 = PROCEED
```

RH-13 must start from updated `main`. The implementation issue should use a
new branch named from its GitHub issue number, for example
`test/<issue-number>-rh-13-release-decision`.

## Acceptance gate

- [x] A single RH-13 implementation issue is opened from `.github/ISSUE_TEMPLATE/implementation.yml`: issue #182.
- [x] All RH-00 through RH-12 predecessor issues and PRs are merged and closed; RH-12 is recorded as issue #128 / PR #181 / merge `1365ee5`.
- [x] The final qualification started from a clean working tree at `1924dfa` with the repository's documented headless plotting configuration.
- [x] `make check` passed without rewriting published artifacts: 532 tests passed in 384.070 seconds.
- [x] `make rh12-evidence-check` passed without rewriting the RH-12 manifest.
- [x] Repository boundary checks and `git diff --check` passed.
- [x] Final-holdout absence is verified; no final-holdout access occurred.
- [x] Release notes, README, model card, backlog, limitations, roadmap, phase docs, and P4 status agree.
- [x] The RH-12 evidence digest, historical artifact hashes, and issue #130 deferred disposition are carried into the release record.
- [x] The predeclared decision contract produced exactly one decision: `PROCEED`.
- [x] Release preparation is authorized only after `PROCEED`; the annotated tag is prepared locally after this decision record, while no GitHub release is published by this closeout.
- [x] P4-02/P4-03 are eligible to resume after `PROCEED`; RH-13 does not implement them.

## GitHub issue instructions

Before opening the issue, search open and closed issues for an existing RH-13
record. Do not create a duplicate. If none exists, use the repository's
`.github/ISSUE_TEMPLATE/implementation.yml` and enter:

| Field | Required content |
| --- | --- |
| Title | `[Implementation] RH-13: Qualify and release the hardening initiative` |
| Labels | `implementation` plus `testing` and/or `documentation` if configured |
| Milestone | `v0.3.1-decision-engine-hardening` |
| Work metadata | `Backlog work ID: RH-13`<br>`Classification: Release evidence / decision`<br>`Priority: Release blocking`<br>`Milestone: v0.3.1-decision-engine-hardening` |

Use the following content for the template fields:

### Outcome

Publish the final `v0.3.1-decision-engine-hardening` qualification evidence,
reconcile the release claim package, and record exactly one predeclared
`PROCEED`, `REMEDIATE`, or `STOP` decision for P4-02/P4-03. Create the tag and
GitHub release only after `PROCEED`.

### Context

RH-12 is merged through issue #128 and PR #181, merge `1365ee5`. It published
versioned corrected evidence with digest
`47ac6e06793e66b20601a05486fbb24fe24ff91bbffc4acda8e4523853527933`, preserved
the historical Phase 3.08 artifacts, and deferred issue #130. RH-13 is the
remaining release and Phase 4 resume gate.

### In scope and out of scope

```markdown
In scope:
- Clean merged-state qualification and read-only artifact verification
- Environment, commit, test, boundary, and final-holdout records
- Release claim/limitation reconciliation across active documentation
- Predeclared PROCEED, REMEDIATE, or STOP decision
- P4-02/P4-03 dependency update and release preparation after PROCEED

Out of scope:
- P4-02/P4-03 implementation before PROCEED
- New modeling, recalibration, economic-contract, or allocator changes
- Fresh seeds or stress variants without a separate predeclared issue
- Final-holdout access or historical-artifact rewriting
- Production deployment or real-policyholder evidence
```

### Claim, limitation, contract, and artifact impact

```markdown
Allowed while open:
- Final qualification, release-package reconciliation, and bounded decision evidence.

Blocked while open:
- P4-02/P4-03 implementation, production-readiness claims, tag/release creation before PROCEED, and final-holdout access.

Limitations affected:
- LIM-RH-001's RH release gate is resolved by this `PROCEED` decision; its remaining claim limitations continue to apply.

Downstream work resumed at closure:
- P4-02/P4-03 only when the recorded decision is PROCEED.

Contract or version change:
- None authorized. Any contract/version change requires a separate reviewed issue.

Artifact migration or compatibility:
- No historical artifact rewrite. Release artifacts must link the RH-12 version 1.0.0 manifest and preserve its hashes.
```

### Acceptance checks

Copy the phase acceptance gate above, retaining objective checkboxes for clean
qualification, read-only checks, documentation reconciliation, decision
recording, tag/release ordering, and P4 gating.

### Evidence

Require the PR to attach or link:

- clean merged-state `make check` output;
- `make rh12-evidence-check` output;
- repository boundary and `git diff --check` output;
- environment, commit, Python/dependency, and headless plotting details;
- the RH-12 report/manifest and digest;
- historical Phase 3.08 hash confirmation;
- final-holdout absence confirmation;
- the release claim/limitation reconciliation matrix;
- the formal decision record; and
- tag/release links only if the decision is `PROCEED`.

### Dependencies

```markdown
Must merge first:
- RH-12 issue #128 / PR #181 / merge 1365ee5

Blocks:
- P4-02 and P4-03 until RH-13 records `PROCEED` (now satisfied; implementation remains separately gated)

Related decisions or limitations:
- RH-00 through RH-12; LIM-RH-001; issue #130 deferred by RH-12
```

### Boundaries

Check every required boundary checkbox in the implementation template. In
particular, confirm fictional/public/original data only, no credentials or
customer information, preservation of point-in-time and human-review
boundaries, no final-holdout access, and explicit versioning for any proposed
deterministic-output or artifact change.

## Claim and artifact impact

RH-13 may add qualification logs, release metadata, decision records, and
documentation. It must not broaden the RH-12 synthetic/conditional claim
boundary, rewrite historical evidence, or turn local reference behavior into a
production claim. Any new serialized output, contract, or artifact version is
out of scope unless separately reviewed.

## Decision record

**Decision:** `PROCEED`
**Recorded:** 2026-09-18
**Implementation issue:** [#182](https://github.com/anilreddy89/Inforsight/issues/182)
**Qualification source commit:** `1924dfa`
**Qualification result:** `make check` passed with 532 tests; Phase 3 gates S1–S6 reported `RELEASE_QUALIFIED`.
**Pipeline digest:** `fdb3e3331b8376a93ed3531bd4837c9cfd6244cd997eb0fe126b2a3335b56f9`
**RH-12 evidence digest:** `47ac6e06793e66b20601a05486fbb24fe24ff91bbffc4acda8e4523853527933`
**Historical artifact hashes:** results `4779e0d3326caf07636929169342febca9777162aac84adb8af9c73104dfb88e`; report `efba4c70d7a35f7641a2c6386c1a0330d7702ae7b2ab6dac8672e442408d4047`.
**Issue #130:** remains deferred pending its own predeclared experiment.
**Downstream effect:** P4-02 and P4-03 may resume planning and implementation from the reconciled contracts; no Phase 4 implementation was performed in RH-13.
**Release preparation:** the annotated `v0.3.1-decision-engine-hardening` tag is prepared locally after this decision; GitHub release publication remains a separate external operation.

## Completion evidence

The closeout must link:

- RH-13 issue and PR numbers, merge commit, milestone, and required CI;
- the exact clean-state qualification commit and environment;
- all read-only and repository-boundary outputs;
- the formal decision and its objective gate results;
- the final release notes, tag, and GitHub release if `PROCEED`;
- P4-02/P4-03 status after the decision; and
- confirmation that historical artifacts and the final holdout boundary were
  preserved.
