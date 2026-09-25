# ADR 0017 — Verify the committed audit chain across PostgreSQL sequence gaps

- Status: Proposed in P4-07; acceptance requires review of the P4-07 change
- Date: 2026-09-22
- Owner: Anil Jonnala
- Related: P4-04 audit ledger, P4-07 enterprise qualification, ADR 0002 human authority

## Context

`audit_ledger.ledger_sequence` is a PostgreSQL `BIGSERIAL`. PostgreSQL sequence
allocation is not rolled back when an insert transaction fails. During the
P4-07 frozen 100,000-policy workload, a duplicate `(case_id, case_version,
event_type)` in the qualification harness caused one batch insert to fail. The
committed ledger still ended at sequence 233900, while the database sequence
had advanced to 233903. A later valid append therefore receives a higher
number even though no committed ledger row was deleted.

The original verifier required every committed sequence number to differ by
exactly one. This would misclassify a rolled-back insert as tampering. Ledger
ordering, parent hashes, and a separately retained head checkpoint are the
relevant integrity evidence.

## Decision

Verify that committed ledger sequence numbers are strictly increasing. Verify
every parent hash against the preceding committed entry and recompute every
current hash from the canonical payload. Verify the final sequence and hash
against a separately retained head checkpoint. A numerical gap alone is not a
failure; duplicate or reordered sequence numbers are.

The repository still appends in a transaction and retains its database
append-only trigger. This decision changes verification semantics only. It
does not grant external action authority or weaken the human decision boundary.

## Alternatives considered

1. Keep a gapless requirement. Rejected: failed inserts consume `BIGSERIAL`
   values without committing rows, so a valid ledger can fail verification.
2. Replace `BIGSERIAL` with a transactional counter. Deferred: it would require
   a schema migration and a serialized allocation lock. It may be appropriate
   if contiguous display numbers become a business requirement, but they are
   not required for hash-chain integrity.
3. Check monotonic sequence, chained hashes, and an independent head checkpoint.
   Selected: this distinguishes unused sequence values from deletion of a
   committed interior or tail row without changing stored ledger records.

## Consequences and verification

- A missing interior committed row breaks the next row's parent-hash link.
- A missing committed tail row changes the head relative to the retained
  checkpoint. Without an independently retained checkpoint, tail deletion
  cannot be proven from the remaining rows alone.
- Legitimate sequence gaps from rolled-back inserts remain valid, while
  duplicates and reordering fail.
- P4-07 tests must cover a legitimate gap, an interior deletion, a tail
  deletion with checkpoint, and a failed writer that does not deadlock the
  Kafka consumer. The full E4 gate still needs a bound distributed tamper run
  and trusted checkpoint custody.
