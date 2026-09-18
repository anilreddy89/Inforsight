# RH-10D: Audit durability and recovery contract 1.0.0

Status: complete and merged
Evidence: issue [#173](https://github.com/anilreddy89/Inforsight/issues/173), PR [#175](https://github.com/anilreddy89/Inforsight/pull/175), merge `538dc0e`
Release: `v0.3.1-decision-engine-hardening`  
Scope: bounded local reference runtime only  
Selected model: single-writer append protocol

## 1. Decision

The reference runtime uses a single-writer append protocol for the audit log. A
writer acquires an exclusive operating-system file lock, appends a canonical
JSONL record, flushes and `fsync`s the log, then atomically replaces a sidecar
checkpoint and `fsync`s its containing directory. A writer does not claim a
state transition committed until both the state commit and the audit commit
follow the workflow protocol defined below.

The checkpoint records the last committed log prefix. A crash after the log
write and before checkpoint replacement leaves an uncheckpointed suffix. On
restart, that suffix is discarded after the committed prefix is verified. A
log shorter than the checkpoint, a malformed checkpoint, or a checkpoint that
does not match the verified prefix fails closed.

This model is intentionally narrower than a database transaction. It provides
a deterministic local recovery boundary and explicit single-writer
coordination without pretending to provide distributed transactions,
multi-writer availability, or external authenticity.

## 2. Alternatives considered

### 2.1 Transactional local store

A local database could place workflow state, audit entries, and the checkpoint
in one transaction and use database locking for writer coordination.

Advantages:

- One transaction can commit state and audit rows together.
- Locking, recovery, and constraint enforcement are available from the store.
- A later PostgreSQL implementation has a familiar migration path.

Costs and boundary concerns:

- It introduces a database dependency into the local reference runtime.
- SQLite or another embedded store would still not establish the P4
  PostgreSQL/KMS operational boundary.
- The existing JSONL audit artifacts and verifier would need a larger adapter
  surface before the semantics were settled.

### 2.2 Single-writer append protocol — selected

The existing ledger already has canonical records, a SHA-256 chain, and an
append-oriented JSONL representation. Adding a lock and durable checkpoint
establishes the required local ordering and recovery semantics with a small,
inspectable surface.

The costs are accepted explicitly: state and audit atomicity require a
workflow-level prepare/commit protocol, crash recovery can preserve or discard
only according to the checkpoint boundary, and the checkpoint is not an
external trust anchor. P4-04 may later replace this adapter with PostgreSQL
and KMS without changing the semantic requirements.

## 3. Terminology and data artifacts

For a log path `<log>.jsonl`, the reference implementation uses:

| Artifact | Meaning | Durability rule |
| --- | --- | --- |
| `<log>.jsonl` | Ordered canonical audit records | Record bytes are flushed and `fsync`ed before checkpoint commit. |
| `<log>.jsonl.checkpoint` | Last committed prefix metadata | Written to a temporary file, `fsync`ed, atomically renamed, and directory-synced. |
| `<log>.jsonl.lock` | Local single-writer coordination handle | Held exclusively for append and recovery truncation. |

The checkpoint schema is `audit-checkpoint/1.0.0`:

```json
{
  "entry_count": 12,
  "log_bytes": 18432,
  "sequence_number": 11,
  "tip_hash": "<sha256>",
  "version": "audit-checkpoint/1.0.0"
}
```

`entry_count` is zero-based compatible with `sequence_number == -1` for an
empty ledger. `tip_hash` is `GENESIS_HASH` for an empty ledger. `log_bytes` is
the exact UTF-8 byte offset at the end of the committed prefix, not a count of
characters or lines.

The audit record hash is computed from the canonical record payload without
`entry_hash`, prefixed by the previous hash. The hash chain proves continuity
only relative to a trusted genesis value and checkpoint.

## 4. Trust boundary and claim limits

The local process trusts:

- the configured genesis constant;
- the operating system's file-lock behavior for this local process boundary;
- successful `fsync` and atomic rename semantics of the local filesystem; and
- a checkpoint that is obtained from a separately protected or independently
  reviewed boundary when a tamper-evidence claim is required.

The reference implementation does not protect the checkpoint from an attacker
who can modify both the log and its sidecar. Therefore it may claim:

- detection of changes relative to the trusted checkpoint;
- detection of committed-prefix truncation;
- detection of hash-chain discontinuity, mutation, reorder, and invalid replay;
- deterministic local recovery of an uncheckpointed suffix; and
- rejection of a stale local writer.

It may not claim:

- authenticity or non-repudiation;
- tamper resistance against an attacker controlling the log and checkpoint;
- immutable storage;
- distributed exactly-once behavior;
- multi-process availability under concurrent writers;
- protection from a compromised host or filesystem administrator; or
- PostgreSQL, KMS, cloud, network, or multi-region durability.

## 5. Writer protocol

### 5.1 Open and recover

1. Acquire the exclusive writer lock before truncation or checkpoint repair.
2. Read and validate the checkpoint if it exists.
3. Fail closed if the log is shorter than `log_bytes`.
4. If the log is longer than `log_bytes`, inspect the suffix:
   - a complete valid suffix is treated as an uncheckpointed write and is
     discarded;
   - a newline-terminated malformed suffix is corruption and fails closed;
   - an incomplete final line is a torn write and is discarded.
5. Parse and hash-verify the committed prefix from genesis through the stated
   sequence and tip hash.
6. Fail closed on any sequence, required-field, timestamp, chain, or digest
   mismatch.

### 5.2 Append

1. Acquire the exclusive writer lock without blocking indefinitely. A second
   writer receives a stable writer-busy failure.
2. Re-read the checkpoint and compare it with the writer's in-memory entry
   count, sequence, tip hash, and log byte length. A stale instance fails
   closed and must be reopened.
3. Construct the next record using the current tip and canonical serialization.
4. Append one complete UTF-8 JSONL record, flush, and `fsync` the log.
5. Atomically replace and directory-sync the checkpoint for the new prefix.
6. Release the lock and expose the new in-memory tip.

If the log write fails before `fsync`, no audit commit is acknowledged. If the
log is durable but checkpoint replacement fails, the next open discards the
uncheckpointed suffix and reports recovery diagnostics. If checkpoint
replacement succeeds, the prefix is the committed audit boundary.

## 6. Workflow state and audit ordering

The workflow service must use a prepare/commit boundary for mutations that
change both state and audit history:

1. Validate authority, case version, idempotency, eligibility, and resource
   invariants while holding the service lock.
2. Prepare the next state and complete audit record without exposing either as
   committed.
3. Commit the audit record through the writer protocol.
4. Commit the corresponding workflow state and idempotency/resource outcome.
5. Return the committed event only after both commits succeed.

The local implementation must make recovery deterministic for the two failure
orders:

| Failure point | Required recovery result |
| --- | --- |
| Before audit `fsync` | Neither state nor audit transition is committed. |
| After audit `fsync`, before checkpoint replacement | Uncheckpointed audit suffix is discarded; state remains uncommitted. |
| After checkpoint replacement, before state commit | Recovery detects the committed audit intent and either completes the bound state commit or fails closed with an explicit recoverable pending transition. It must never silently apply a different state. |
| After state and audit commit | Restart reproduces the same state, event identity, case version, idempotency result, and audit tip. |

RH-10I implements the third row with the versioned `workflow-state/1.0.0`
local state store. It atomically replaces a committed workflow snapshot and
can retain one pending transition containing the target snapshot and audit
event identity. On restart, the pending transition is promoted only when the
audit event is present; otherwise the committed snapshot is retained. This is
an explicit recovery protocol, not a database transaction.

## 7. Adversarial and recovery test matrix

RH-10I must implement focused tests for the following predeclared cases:

| Case | Expected result |
| --- | --- |
| Middle-record field mutation | Verification fails at the mutated sequence. |
| Middle-record deletion | Sequence or chain verification fails. |
| Suffix deletion through the checkpoint | Open fails closed because the log is shorter than the trusted prefix. |
| Reorder | Chain or sequence verification fails. |
| Complete malformed suffix | Open fails closed. |
| Torn incomplete suffix | Restart truncates to the checkpoint and recovers the committed prefix. |
| Valid uncheckpointed suffix | Restart truncates it and recovers the committed prefix. |
| Duplicate/replayed append | Stable identity or chain validation rejects it. |
| Stale writer instance | Append is rejected without changing the log or checkpoint. |
| Concurrent second writer | One writer succeeds; the other receives writer-busy or stale-writer failure. |
| Checkpoint version mismatch | Open fails closed. |
| Checkpoint tip/hash mismatch | Open fails closed. |
| Failure before audit `fsync` | No committed transition is exposed. |
| Failure between audit checkpoint and state commit | Pending intent or fail-closed recovery is deterministic and tested. |
| Restart after successful commit | State, idempotency, and audit tip agree. |

Tests must use temporary fictional data and must not modify published audit,
qualification, model, or dataset artifacts.

## 8. Compatibility and migration

The existing audit record shape and genesis seed remain compatible. The
checkpoint is additive and versioned as `audit-checkpoint/1.0.0`. A ledger
opened with an existing JSONL file and no checkpoint may create an initial
checkpoint only after the entire existing log verifies successfully; it must
not rewrite the log.

Any incompatible audit record, state snapshot, or pending-intent change
requires a new version, a migration/read compatibility path, and a focused
fixture. Historical JSONL files remain immutable evidence.

The checkpoint sidecar is operational state, not a historical experiment
artifact. It may be regenerated only from a fully verified log and only under
the documented trust boundary.

## 9. Downstream ownership

- **RH-10I:** implement this local protocol, state/audit recovery behavior,
  adversarial fixtures, and claim-boundary evidence.
- **RH-09I:** carry settled audit semantics into final P4-01 contract surfaces
  where required.
- **RH-11:** qualify truncation, recovery, read-only verification, and CI
  behavior.
- **RH-12:** reconcile affected public claims and evidence without rewriting
  historical results.
- **P4-04:** realize PostgreSQL, KMS, external checkpointing, and production
  persistence semantics.

RH-10D does not authorize P4-02/P4-03 implementation or any production
deployment claim.
