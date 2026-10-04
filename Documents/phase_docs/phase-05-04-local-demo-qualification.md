# Phase 5.04 — Local Demo Qualification and Closeout

| Field | Value |
| --- | --- |
| Status | Completed through PR #205, merged as `67d051c`; required CI passed |
| Issue | [#204](https://github.com/anilreddy89/Inforsight/issues/204) |
| Predecessor | [P5-03 PR #203](https://github.com/anilreddy89/Inforsight/pull/203), merged as `f05b09b`; required CI passed |
| Milestone | `v0.5.0-agent-workflow` (#7), still open |

## Goal

Make the fictional case review path repeatable and show its actual authority
boundary. The local demo creates a scored case through the control-plane API,
builds a bounded P5-01 abstention because no trusted rules allowlist or case
evidence was supplied to the Python workflow, records that draft, records a
human rejection, and checks the persisted decision audit hash. This is a
small, honest integrated demonstration, not yet the full policy-event-to-agent
workflow described in the 14-week plan.

## Run

1. Start the historical review-only persistence topology with
   `docker compose -f infra/docker-compose.yml -f infra/docker-compose.p5-04.yml up --build -d` and wait for the
   control-plane service to become ready.
2. Run `make p5-04-demo-check` from the repository root. It runs a focused
   offline test and the live HTTP walkthrough. Each run creates a new fictional
   case and prints its case ID, score, draft status, decision, and audit hash.
3. Stop with `docker compose -f infra/docker-compose.yml -f infra/docker-compose.p5-04.yml down`.

The explicit P5-04 overlay selects the bounded test scorer and disables the
new visitor journey. This harness supplies only a policy ID, not the features
required by released-model HTTP inference. Its result is review/persistence
qualification, not real-model or Kafka journey evidence. The default local and
public Compose files retain HTTP scoring; use `make demo-check` for the complete
released-model visitor journey. Do not apply the historical overlay to a public
deployment.

This command requires local ports 8080 and the Compose dependencies. The
PostgreSQL volume is retained by the stop command; remove it only intentionally.
No live model provider, external customer action, or customer data is used.

## Acceptance and remaining gap

- [x] P5-03 PR #203 merged, issue #202 closed, and required PR CI passed.
- [x] The local Compose walkthrough passed on 2026-10-03 with a real
  PostgreSQL-backed control plane: one scored case, `ABSTAIN` draft, human
  `REJECTED` decision, 64-character audit hash, and no action authority.
  Final PR CI and review passed in PR #205.
- [ ] A trusted event-to-score-to-rule-evidence adapter supplies the agent
  input from the same versioned case snapshot. The current triage path scores
  a supplied policy ID and calls eligibility, but persists `abstain` as its
  recommendation; the Python workflow cannot authenticate a caller-supplied
  rules allowlist. A fabricated allowlist must not be used to claim integration.
- [ ] Human override semantics and end-to-end replay are qualified against
  that trusted adapter before Phase 5 milestone closeout.
- [x] Documentation, trackers, final CI, and review were reconciled after merge.

The remaining integration gates are tracked by [P5-05 issue #206](https://github.com/anilreddy89/Inforsight/issues/206).

P4-07 enterprise-scale gates and Phase 6 cloud deployment are separate work.
