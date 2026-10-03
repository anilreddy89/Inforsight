# Phase 5.05 — Trusted Fictional Event-to-Agent Handoff

| Field | Value |
| --- | --- |
| Status | In progress on `implementation/p5-05-trusted-event-agent-handoff` |
| Issue | [#206](https://github.com/anilreddy89/Inforsight/issues/206) |
| Pull request | [#207](https://github.com/anilreddy89/Inforsight/pull/207), review and final CI pending |
| Predecessor | P5-04 [PR #205](https://github.com/anilreddy89/Inforsight/pull/205), merged as `67d051c` |
| Milestone | `v0.5.0-agent-workflow` (#7), open |

## Contract and authority

The opt-in local demo endpoint accepts one fictional, bounded event envelope.
The Java service checks event identity, point-in-time fields, and safety facts,
projects a fixed feature record, scores it, evaluates its own deterministic
rules, creates a versioned case, and stores a handoff tied to the server-owned
case snapshot. Handoff contract `1.0.0` is defined in
[`api/openapi/local-demo-v1.yaml`](../../api/openapi/local-demo-v1.yaml) and exposes only the resulting fictional
fact, eligible action IDs, and a fixed procedure citation to the local Python
agent. No HTTP field may supply an action allowlist or procedure text.

The existing draft endpoint must verify an action and citation against any
stored handoff for that case before recording it. Cases without a P5-05 handoff
remain untrusted advisory cases under the P5-03 boundary. A handoff cannot
grant approval or execution authority; only a separate human decision can
change case state. The local demo property is off by default and enabled only
in the Compose demo topology.

The event's payment status and tenure feed a fixed synthetic feature projection.
The Compose control plane uses the bounded local inference adapter, which is
deterministic but does not represent the released model bundle. The HTTP model
runtime is a separate service in the topology; claiming its model score in this
walkthrough would require a separately qualified feature adapter. The Java
service owns the rule result and fictional procedure text. The Python planner
remains a local client; the Java boundary verifies its submitted action,
evidence source, and citation against the stored handoff, but does not attest
that a specific Python process or model generated the draft.

## Run

1. `docker compose -f infra/docker-compose.yml up --build -d`
2. After the control plane is healthy, `make p5-05-demo-check`. The command
   prints event, case, snapshot, draft, decision, and audit verification IDs.
3. `docker compose -f infra/docker-compose.yml down`

Focused checks are `make p5-05-check` and `make p5-05-integration-check`.
The latter requires Docker Desktop or another Testcontainers-compatible
daemon. No cloud resources or external actions are used.

## Acceptance

- [x] A synthetic event, scored feature projection, eligibility, case,
  handoff, and draft share server-owned identities.
- [x] Missing/future/conflicting evidence and stale or mismatched submissions
  fail closed; a caller cannot add an action to the allowlist.
- [x] Human rejection and invalid override preserve the authority boundary,
  and persisted audit replay verifies the draft and decision.
- [x] Focused Java/Python checks, PostgreSQL integration, the full control-plane
  test suite, and the live Compose walkthrough pass locally on 2026-10-03.
- [ ] Required CI and review pass on the final commit.

This is a fictional local demonstration. It is not a Kafka policy-event
consumer, production event
projection, real-policyholder model validation, live provider integration, or
P4-07 scale qualification. The final holdout and historical model artifacts
remain untouched.
