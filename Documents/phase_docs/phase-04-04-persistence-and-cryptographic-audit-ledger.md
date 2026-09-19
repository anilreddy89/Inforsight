# Phase 4.04 — Persistence and Cryptographic Audit Ledger

P4-04 adds durable persistence and tamper-evident audit storage beneath the
completed Java control plane. It introduces PostgreSQL-backed case and queue
state, versioned Flyway migrations, and an append-only SHA-256 hash-chained
ledger that records human decision transitions without granting autonomous
execution authority.

| Field | Value |
| --- | --- |
| Phase | Phase 4 — Enterprise Integration & Scale |
| Milestone | `v0.4.0-enterprise-scale` (Milestone #5) |
| Status | Implementation in progress |
| Depends on | P4-01, P4-02, P4-03, RH-13 `PROCEED` |
| Blocks | P4-05, P4-06 |
| Tracking issue | [#188](https://github.com/anilreddy89/Inforsight/issues/188) |
| Pull request | TBD |

## Current implementation evidence

- Branch `implementation/p4-04-persistence-audit-ledger` starts from the P4-03
  merge and owns the P4-04 implementation for issue #188.
- Flyway migration `V1__p4_04_control_plane_persistence.sql` defines durable
  policy snapshots, cases, triage queues, idempotency records, and audit-ledger
  storage.
- The initial ledger adapter canonicalizes audit payloads, persists the exact
  canonical string, and chains entries with lowercase SHA-256 hashes. The
  payload is stored as text deliberately: PostgreSQL `JSONB` key normalization
  would otherwise invalidate byte-for-byte hash verification.
- `make p4-04-integration-check` passes with PostgreSQL 16 in Testcontainers:
  Flyway migrates an empty database, chained entries verify, and a direct
  payload mutation is detected as `CURRENT_HASH_MISMATCH`.
- `PersistentCaseRepository` now persists case creation and performs a human
  decision transition, ledger append, and idempotency-record write in one
  PostgreSQL transaction. The focused integration test proves replay returns
  the original result without another ledger entry, mismatched key reuse and
  stale versions are rejected, and a simulated audit failure rolls back the
  case transition.
- Ledger verification accepts a separately retained head checkpoint, so tail
  deletion is detectable; it also rejects sequence gaps and reordered input.
  A versioned `AuditLedgerSigner` boundary and deterministic local HMAC adapter
  are test-only/development seams, not a production KMS or key-custody claim.
- The explicit Spring `persistence` profile selects `PersistentCaseRepository`
  for the REST workflow and returns the committed audit hash with a decision.
  Its Testcontainers REST test proves Flyway startup, persisted triage, and a
  human decision response with a 64-character ledger hash. The default profile
  remains database-free and selects the P4-03 in-memory workflow.
- Persistent case creation derives a deterministic point-in-time snapshot
  identity from the evaluated policy, timestamp, and bundle evidence, stores it
  in `policy_snapshot`, and binds the case through a non-null foreign key. This
  is local snapshot evidence only; it does not claim a production evidence
  source or historical reconstruction service.
- The same creation transaction writes a `PENDING_REVIEW` triage-queue entry
  with deterministic local priority metadata. This persists queue state but is
  not a production allocation scheduler or connector integration.
- The PostgreSQL integration suite rebuilds the repository adapter after a
  committed decision and rehydrates both case state and audit hash from the
  database. This is a local durability proof, not an operations/SLA claim.
- The default P4-03 local profile keeps datasource/Flyway autoconfiguration
  disabled while the persistent runtime profile and repository adapter are
  implemented; existing no-database control-plane tests remain runnable.

## Objective

Replace the P4-03 in-memory case store with durable relational persistence and
provide a verifiable, append-only audit ledger for case decisions and workflow
transitions. The implementation must preserve case-version concurrency,
idempotency, point-in-time evidence identities, and the ADR 0002 human
authority boundary.

## Scope

- Add PostgreSQL schema migrations managed by Flyway for:
  - Policy snapshots and evidence identities.
  - Case records, case versions, recommendations, and decision state.
  - Active triage queues and allocation metadata.
  - Idempotency keys and replay results.
  - Append-only audit ledger entries.
- Implement repository adapters for the P4-03 control-plane case and decision
  workflows.
- Implement an audit record containing the event payload, actor/workflow
  identity, case/version binding, timestamp, `parent_hash`, and `current_hash`.
- Compute canonical SHA-256 ledger hashes with deterministic serialization.
- Add a verification operation that detects mutation, deletion, duplication, or
  reordering of ledger entries.
- Couple a decision state transition and its audit record in one ACID
  transaction.
- Add a KMS signing interface and bounded local implementation seam without
  claiming a production KMS integration.
- Add Testcontainers-backed PostgreSQL integration tests and migration checks.
- Update service documentation, phase evidence, backlog, tracker, and roadmap.

## Explicit non-goals

- No production cloud KMS integration or key custody claim.
- No production identity federation or authentication provider integration.
- No CRM, telephony, Kubernetes, or cloud deployment work.
- No autonomous action execution or customer-facing side effects.
- No rewrite of historical qualification artifacts or model bundles.
- No distributed exactly-once claim beyond the tested database transaction
  boundary.
- No final-holdout access or production customer data.

## Acceptance checks

- [x] PostgreSQL migrations execute cleanly from an empty database and are
  idempotently verifiable from a clean checkout.
- [x] Schema constraints preserve case identity, optimistic case versions,
  idempotency keys, point-in-time evidence identities, and append-only ledger
  ordering.
- [x] P4-03 case creation, retrieval, and human decision transitions persist
  across service restarts in PostgreSQL.
- [x] A decision and its corresponding audit record commit atomically, with no
  durable decision state when the audit write fails.
- [x] Ledger hashes are deterministic and verification detects injected field
  mutation, checkpointed row deletion, duplication/sequence gaps, or
  reordering.
- [x] Compatible idempotent retries return the original committed result without
  creating duplicate decisions or audit entries.
- [x] Stale case versions fail with a stable conflict error and do not append a
  new audit entry.
- [x] The KMS signing interface is versioned and testable while remaining an
  explicit local seam rather than a production integration.
- [x] PostgreSQL Testcontainers integration tests pass with Docker Desktop and
  the repository's focused P4-04 make target.
- [ ] Focused Java checks, relevant Python checks, and repository CI pass
  without rewriting protected historical artifacts.
- [ ] README, backlog, change tracker, roadmap, and this phase document are
  updated with issue/PR/merge evidence at closeout.

## Evidence and issue workflow

The implementation issue must identify the completed P4-03 merge (PR #187,
`05580203f53b95a392c9523075343ce11bbc300e`) as its prerequisite. The issue
must preserve the distinction between durable local persistence evidence and
production database, KMS, identity, or deployment readiness.

The implementation branch should start from updated `main` and use a stable
name such as `implementation/p4-04-persistence-audit-ledger`.

## Initial design decisions

- Flyway owns forward-only schema versioning; destructive migration behavior is
  prohibited in the initial phase.
- PostgreSQL transactions are the source of truth for case-version compare and
  set plus audit append.
- Ledger hashes use canonical JSON with explicit field ordering and UTC
  timestamps; hash inputs and algorithm identifiers are persisted.
- Audit entries are append-only at the application and database permission
  boundaries; verification reports the first broken link and failure class.
- KMS signing is represented by an interface and deterministic local adapter;
  production key management is deferred to the deployment/security phase.

## Closeout evidence

To be completed after implementation: issue number, PR number, merge commit,
CI results, migration output, PostgreSQL integration output, ledger mutation
verification output, and the final limitation statement.
