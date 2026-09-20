# Phase 4.05 — CRM and Contact-Center Connector Boundaries

P4-05 adds governed connector contracts between the completed persistence
control plane and enterprise CRM/contact-center systems. It establishes
deterministic, testable task and dialer-sync seams while keeping all external
actions disabled and `authorized_to_act: false`.

| Field | Value |
| --- | --- |
| Phase | Phase 4 — Enterprise Integration & Scale |
| Milestone | `v0.4.0-enterprise-scale` (Milestone #5) |
| Status | Completed |
| Depends on | P4-03, P4-04, ADR 0002 human authority boundary |
| Blocks | P4-06 |
| Tracking issue | [#190](https://github.com/anilreddy89/Inforsight/issues/190) |
| Pull request | [#191](https://github.com/anilreddy89/Inforsight/pull/191) |

## Current implementation evidence

- Versioned `connector-preflight/1.0.0` JSON Schema and a fictional example
  require case/version, snapshot, audit, idempotency, target, and explicit
  `authorized_to_act: false` / `external_execution_disabled: true` markers.
- Java preflight contracts and deterministic fake adapters cover Salesforce FSC,
  Genesys, and Twilio target types without a transport client or credentials.
- `ConnectorPreflightService` rejects missing human review or consent, legal
  hold, quiet hours, and cooldown; a ready preflight emits an
  authority-neutral audit event and idempotent replay does not append again.
- `make p4-05-check` passes with fictional clean-room inputs only.

## Objective

Define and implement bounded CRM-task and contact-center synchronization ports
for the Java control plane. A connector may construct and validate a requested
handoff, but it must not create a customer task, initiate a dial, modify a CRM
record, or otherwise cause an external side effect.

## Scope

- Add versioned connector-domain contracts for:
  - CRM case/task handoff payloads with case, snapshot, policy, and audit
    identities.
  - Contact-center queue/dialer synchronization intents.
  - Idempotency, external-reference, and point-in-time evidence fields.
  - Explicit dry-run/preflight outcome states.
- Add bounded adapter interfaces and fake adapters for Salesforce Financial
  Services Cloud and Genesys/Twilio-style contact-center integrations.
- Enforce deterministic connector preflight rules, including:
  - `authorized_to_act: false` on every connector output.
  - No outbound connector transport in the default or test profiles.
  - Human-review, consent, quiet-hour, cooldown, legal-hold, and duplicate-key
    denial paths before a handoff can be represented.
- Persist connector preflight attempts and outcomes as authority-neutral audit
  events through the P4-04 persistence boundary.
- Add focused Java tests and a `make p4-05-check` target using fake adapters
  only.
- Update phase evidence, tracker, and implementation issue/PR records.

## Explicit non-goals

- No Salesforce, Genesys, Twilio, CRM, or telephony credentials.
- No live OAuth, webhooks, API calls, dialer calls, messages, or task creation.
- No customer or production CRM/contact-center data.
- No identity federation, production secret management, or cloud deployment.
- No autonomous external action; human authority remains required and external
  execution remains disabled.
- No changes to protected model bundles, historical qualification artifacts, or
  final-holdout data.

## Acceptance checks

- [x] Connector contracts have explicit version, point-in-time identity,
  idempotency, and authority fields.
- [x] Salesforce FSC and Genesys/Twilio adapter interfaces compile with fake
  implementations only; no live transport is included.
- [x] Connector preflight fails closed for missing human decision, consent,
  legal hold, cooldown, quiet hours, duplicate idempotency key, or stale case
  version.
- [x] Every connector outcome retains `authorized_to_act: false` and reports
  that external execution is disabled.
- [x] Connector preflight records are persisted and auditable without granting
  external execution authority.
- [x] Tests prove deterministic payloads, idempotency behavior, and all
  fail-closed guardrail paths using fictional clean-room inputs.
- [x] `make p4-05-check`, relevant Java checks, and PR CI pass.
- [x] Documentation, tracker, issue, PR, and final limitation statement are
  updated at closeout.

## Evidence plan

- Versioned connector payload examples built only from fictional policy/case
  records.
- Unit and integration tests against fake connector adapters; network access is
  prohibited in those tests.
- P4-04 PostgreSQL audit evidence for persisted preflight outcomes.
- `git diff --check`, focused make target output, and required PR CI results.

## Issue workflow

Open one implementation issue titled:

`[Implementation] P4-05: Governed CRM and contact-center connector boundaries`

Use the repository implementation template with backlog work ID `P4-05`,
classification `New capability / enterprise integration boundary`, priority
`Milestone blocking`, and milestone `v0.4.0-enterprise-scale`. The issue must
state that P4-04 is merged through PR #189 and that live connector execution is
explicitly out of scope.

## Initial design decisions

- Connector interfaces represent preflight/handoff construction rather than
  execution commands.
- An adapter cannot override a control-plane authority result; connector output
  always remains `authorized_to_act: false`.
- Stable idempotency keys bind a case/version, target-system type, and
  point-in-time snapshot identity.
- Fake adapters are the only implementations enabled in this phase. Any live
  transport requires a later, separately reviewed scope with credentials and
  deployment controls.

## Closeout evidence

- Tracking issue [#190](https://github.com/anilreddy89/Inforsight/issues/190)
  and implementation PR [#191](https://github.com/anilreddy89/Inforsight/pull/191)
  are closed and merged to `main` at `b59f9ab`.
- `make p4-05-check`, the focused Java suite, the PostgreSQL/Testcontainers
  persistence evidence, and required PR CI checks passed before merge.
- The successful persisted preflight path records
  `CONNECTOR_PREFLIGHT_RECORDED` in the audit ledger; compatible idempotency
  replay adds no duplicate record and an incompatible reuse is rejected.
- Fake adapters remain the only connector implementations. No transport,
  credential, CRM mutation, telephony call, message, task creation, or
  autonomous external execution was added; every outcome remains
  `authorized_to_act: false` with external execution disabled.
