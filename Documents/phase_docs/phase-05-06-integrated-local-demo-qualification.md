# Phase 5.06 — Integrated Local Demo Qualification

| Field | Value |
| --- | --- |
| Status | Local qualification passed on merged `main` baseline `d8b193c`; PR review and CI pending |
| Issue | [#208](https://github.com/anilreddy89/Inforsight/issues/208) |
| Baseline | `d8b193c` (PR #209 merge), including P5-05 merge `63fcd9b` |
| Milestone | `v0.5.0-agent-workflow` (#7), open until review and CI pass |
| Date | 2026-10-03 ET |

## Qualification evidence

The checkout was clean before branching from updated `main`. Docker Engine 29.8.1 was available. These commands passed:

| Command | Result |
| --- | --- |
| `make p5-05-check` | Seven Python workflow tests and six Java tests passed. Covers abstention, authority, action allowlist, citation/procedure, and controller behavior. |
| `make p5-05-integration-check` | PostgreSQL 16 Testcontainers integration passed, with Flyway migrations V1–V5 applied. |
| `mvn -f services/control-plane/pom.xml test` | 39 tests, zero failures or errors, 14 skipped by their separate integration or P4-07 gates. |
| `docker compose -f infra/docker-compose.yml up --build -d` | All services started; inference runtime, PostgreSQL, and Kafka reported healthy. |
| `make p5-05-demo-check` | End-to-end fictional walkthrough passed; evidence below. |
| `docker compose -f infra/docker-compose.yml down` | Demo containers and network removed. |

The walkthrough returned:

```json
{
  "audit_verified": true,
  "authorized_to_act": false,
  "case_id": "case_fc4b790b-f106-4b61-b11d-f9a44d5fe211",
  "draft_action": "courtesy_reminder",
  "event_id": "fictional-event-774c88f36e674f9aa69b7ea433c7591c",
  "human_decision": "REJECTED",
  "snapshot_id": "snapshot_0d965f88c56a35f2933c6377b1cd44313993ac6d7e9b222977dc61276fe0a282"
}
```

The demo is reproducible with newly generated IDs; these IDs identify this run only. The event, score, rules, case snapshot, bounded draft, human rejection, and audit verification are exercised by the merged walkthrough. Negative authority and provenance paths are covered by the focused and PostgreSQL tests. CI must repeat the gate on the qualification PR before closure.

## Milestone decision

Local qualification passes for the **fictional, bounded Phase 5 demonstration**. Milestone #7 remains open until the qualification PR passes required CI and review; issue #208 remains open for that decision. No contract or artifact version changes are introduced here.

This evidence does not qualify a production event consumer, released model scoring, a live model provider, external action, cloud deployment, or P4-07 enterprise-scale readiness. The local Compose topology includes Kafka and an HTTP inference runtime, but this walkthrough uses the opt-in fictional event endpoint and bounded local inference adapter. Phase 6 owns the selective cloud demo. Final holdout and historical model artifacts were not accessed or changed.
