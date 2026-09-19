# Phase 4.05 — CRM and Contact-Center Connector Boundaries

P4-05 adds governed connector contracts between the completed persistence
control plane and enterprise CRM/contact-center systems. It establishes
deterministic, testable task and dialer-sync seams while keeping all external
actions disabled and `authorized_to_act: false`.

| Field | Value |
| --- | --- |
| Phase | Phase 4 — Enterprise Integration & Scale |
| Milestone | `v0.4.0-enterprise-scale` (Milestone #5) |
| Status | Implementation issue open |
| Depends on | P4-03, P4-04, ADR 0002 human authority boundary |
| Blocks | P4-06 |
| Tracking issue | [#190](https://github.com/anilreddy89/Inforsight/issues/190) |
| Pull request | TBD |

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

- [ ] Connector contracts have explicit version, point-in-time identity,
  idempotency, and authority fields.
- [ ] Salesforce FSC and Genesys/Twilio adapter interfaces compile with fake
  implementations only; no live transport is included.
- [ ] Connector preflight fails closed for missing human decision, consent,
  legal hold, cooldown, quiet hours, duplicate idempotency key, or stale case
  version.
- [ ] Every connector outcome retains `authorized_to_act: false` and reports
  that external execution is disabled.
- [ ] Connector preflight records are persisted and auditable without granting
  external execution authority.
- [ ] Tests prove deterministic payloads, idempotency behavior, and all
  fail-closed guardrail paths using fictional clean-room inputs.
- [ ] `make p4-05-check`, relevant Java checks, and PR CI pass.
- [ ] Documentation, tracker, issue, PR, and final limitation statement are
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

To be completed after implementation: issue number, PR number, merge commit,
focused test output, required CI results, fake-adapter evidence, audit record
evidence, and the final no-external-execution limitation statement.
