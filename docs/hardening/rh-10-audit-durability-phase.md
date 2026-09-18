# RH-10: Audit durability semantics and recovery contract

Status: RH-10D complete and merged; RH-10I complete locally
Release: `v0.3.1-decision-engine-hardening`  
Classification: latent/current defect and Phase 4 prerequisite  
Priority: high  
Dependencies: RH-03 complete; RH-09 complete  
Downstream: RH-09I contract reconciliation, RH-11 qualification, RH-12 evidence reconciliation, RH-13 release decision

## Purpose

RH-10 defines what the reference decision engine can truthfully claim about audit integrity and makes those semantics executable. The existing unkeyed hash-chain behavior may detect changes relative to a trusted tip and length, but it does not by itself provide authenticity, tamper resistance against an attacker who controls the log and checkpoint, distributed exactly-once behavior, or durable recovery.

RH-10 therefore has two separately reviewable children:

- **RH-10D — design specification:** choose and specify the bounded persistence and recovery model.
- **RH-10I — implementation task:** implement that model and its adversarial fixtures in the local reference runtime.

RH-10 does not implement PostgreSQL, KMS, Kafka, Java services, cloud deployment, or a production key-management boundary. P4-04 owns those realizations.

## Required outcome

The completed increment must provide a versioned audit-durability contract and a bounded local reference implementation that can:

- identify the trusted checkpoint and its trust boundary;
- detect suffix deletion, middle mutation, reordering, and replay;
- coordinate or reject a second writer according to the selected model;
- persist workflow state and audit history with defined atomicity and recovery behavior;
- detect stale or incompatible checkpoints;
- define behavior after restart and failures between state and audit updates; and
- state exactly which integrity, durability, authenticity, and availability claims remain unsupported.

## Design decision required in RH-10D

RH-10D must compare and select one bounded reference model:

1. **Transactional local store:** state and audit records share a local transaction boundary, with explicit locking and recovery semantics.
2. **Single-writer append protocol:** audit entries are appended under an exclusive writer lease/lock, with a separately protected checkpoint and documented crash-recovery scan/truncation rules.

The decision must explain why the selected model is sufficient for the local reference boundary, what failure modes it covers, and which cases remain deferred to P4-04. A checkpoint stored beside a writable log must not be described as attacker-resistant when the same attacker controls both.

## Scope

### RH-10D owns

- audit record, chain-link, checkpoint, writer, and recovery terminology;
- trust-boundary and threat assumptions;
- state/audit atomicity and ordering semantics;
- writer coordination and stale-writer behavior;
- crash, restart, partial-write, and recovery rules;
- adversarial test matrix and predeclared acceptance checks;
- compatibility/versioning and migration notes for RH-10I; and
- a design document at `docs/hardening/rh-10-audit-durability-contract.md` plus any ADR required by the selected durable boundary.

**RH-10D closeout:** The design contract is complete and merged in
`docs/hardening/rh-10-audit-durability-contract.md`. It selects the
single-writer append protocol, records the rejected transactional-store
alternative, defines the checkpoint and trust boundary, specifies state/audit
ordering and recovery outcomes, predeclares the RH-10I adversarial matrix, and
assigns PostgreSQL/KMS realization to P4-04. Issue #173 and PR #175 closed
with merge `538dc0e`.

### RH-10I owns

- the selected local persistence/reference protocol;
- focused failure-injection and adversarial regression tests;
- recovery and restart fixtures;
- claim-boundary documentation and implementation evidence; and
- integration with the existing RH-03 authority/audit handoff without changing historical evidence.

**RH-10I closeout:** The bounded implementation is complete locally. The audit
ledger now uses versioned checkpoints, exclusive writer locking, atomic
checkpoint replacement, stale-writer rejection, and deterministic suffix
recovery. `WorkflowService` supports an optional versioned local state store
with atomic committed snapshots and audit-backed pending-transition recovery.
Focused audit/workflow coverage and the complete 527-test simulator suite pass;
issue/PR closeout remains pending.

### Out of scope

- PostgreSQL or other distributed persistence;
- KMS, signing-service, external identity, or key rotation implementation;
- Kafka or cross-service exactly-once semantics;
- production deployment, load, availability, or network performance claims;
- rewriting historical audit artifacts; and
- unrelated refactoring or new decision workflow features.

## Dependency and merge order

```text
RH-03 (merged)
  -> RH-10D design issue and PR
  -> RH-10I implementation issue and PR
  -> RH-09I / RH-11 downstream qualification
```

RH-10D and RH-10I each receive their own issue, branch, and primary pull request. RH-10I starts from updated `main` only after RH-10D merges. The parent RH-10 outcome is complete only after both children close.

## Acceptance gate

RH-10 is complete only when all of the following are evidenced:

- [x] Current unkeyed hash-chain claims are bounded to verification relative to a trusted checkpoint/tip and length.
- [x] The selected persistence model and its version are documented, including alternatives and consequences.
- [x] Suffix deletion, middle mutation, reorder, replay, and concurrent-writer behavior have adversarial tests.
- [x] State and audit recovery after restart/failure is deterministic and documented.
- [x] Failure between state and audit updates has an explicit atomicity or recovery outcome.
- [x] Stale checkpoint, partial write, and second-writer cases are covered.
- [x] The checkpoint trust boundary is separate from the writable log in the claim language, even if the bounded implementation intentionally co-locates them.
- [x] P4-04 is identified as the owner of PostgreSQL/KMS realization.
- [x] Existing RH-03 authority, human-review, idempotency, and concurrency invariants remain intact.
- [x] Focused tests, repository boundary checks, simulator regression tests, and `git diff --check` pass.
- [x] No historical evidence is overwritten and no production or distributed-integrity claim is added without direct evidence.

## Issue creation map

Create two issues from the repository templates:

| Child | Template | Title | Label | Purpose |
| --- | --- | --- | --- | --- |
| RH-10D | Design specification | `[Design] Specify audit durability semantics and crash recovery` | `design` | Select and document the durable reference model. |
| RH-10I | Implementation task | `[Implementation] Implement bounded audit durability and recovery` | `implementation` | Implement the selected model and adversarial coverage. |

Use the exact field guidance in `docs/engineering-improvement-workflow.md` and the issue-body instructions supplied with each template. Assign both issues to `v0.3.1-decision-engine-hardening`.

## Claim and artifact impact

While RH-10 is open, distributed durability, authenticity, tamper resistance, and exactly-once claims remain blocked. The implementation may add versioned local fixtures and new evidence, but must not mutate historical artifacts. Any changed serialized contract or deterministic output requires an explicit compatibility and migration note in RH-10D before RH-10I implementation.

## Completion evidence

The RH-10 closeout should link:

- RH-10D and RH-10I issue and PR numbers;
- the selected design document and any ADR;
- focused adversarial/recovery test names and output;
- full `make check` and boundary-check output;
- a concise claim-boundary update; and
- confirmation that historical artifacts remain unchanged.
