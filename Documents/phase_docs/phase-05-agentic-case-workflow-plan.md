# Phase 5 — Bounded Agentic Case Workflow Plan

The 14-week [Natural Build Plan](../14-week-plan/Inforsight_Natural_Build_Plan.pdf)
and [Phased Implementation Plan](../14-week-plan/Inforsight_Phased_Implementation_and_GitHub_Plan.pdf)
define Phase 5 as a bounded evidence, procedure, and conservation-planning
workflow (Weeks 10–11). Cloud deployment is Phase 6. The later Phase 4
enterprise-scale qualification remains open in [issue #195](https://github.com/anilreddy89/Inforsight/issues/195).
The partial [PR #196](https://github.com/anilreddy89/Inforsight/pull/196) has merged;
starting Phase 5 neither passes E1–E6 nor authorizes a release. Phase 6's
cloud environment may later provide the production-matched P4-07 test bed.

| Field | Value |
| --- | --- |
| Status | In progress; P5-01 and P5-02 merged, P5-03 remains |
| First increment | [P5-01 issue #197](https://github.com/anilreddy89/Inforsight/issues/197) |
| P5-01 merged pull request | [#198](https://github.com/anilreddy89/Inforsight/pull/198), merge `1a327f4` |
| P5-02 closeout | [issue #199](https://github.com/anilreddy89/Inforsight/issues/199) closed; [PR #200](https://github.com/anilreddy89/Inforsight/pull/200) merged as `89a291c`; [phase document](phase-05-02-bounded-google-adk-orchestration.md) |
| Active increment | [P5-03 issue #202](https://github.com/anilreddy89/Inforsight/issues/202), [phase document](phase-05-03-governed-agent-review-integration.md), branch `implementation/p5-03-governed-agent-review-integration` |
| Authority | ADR 0002; deterministic rules and human approval remain authoritative |

## Goal and design

Produce structured, reviewable, auditable assistance for fictional cases.
The workflow is `trusted case snapshot + deterministic allowed actions →
evidence → versioned procedure citations → draft recommendation/abstention →
human review`. Agent output cannot execute or authorize a financial or
customer-facing action. Procedure documents are data, not instructions.

| Increment | Deliverable | Acceptance |
| --- | --- | --- |
| P5-01 | Typed contract v1, deterministic evidence/procedure/planner seams, focused adversarial tests | Missing/conflicting/future evidence, stale procedure, prompt injection, timeout, low confidence, or no rule-allowed cited action abstains; recommendation remains review-only. |
| P5-02 | Google ADK adapter with bounded tools and structured outputs | Agent calls cannot expand tool permissions or invent actions; model/procedure output is validated against the P5-01 contract; deterministic offline tests and prompt-injection evaluations pass. |
| P5-03 | Control-plane/HITL integration, audit, and end-to-end evaluation | Human reject/override is respected through the governed decision boundary; agent drafts have provenance and are never treated as approval; fail-closed replay and timeout tests pass. |

P5-01 and P5-02 establish the deterministic foundation and optional, pinned
ADK adapter; neither completes Phase 5. P5-02 used `google-adk==2.9.2` and
passed offline fake-model CI, not a live-provider safety qualification.
P5-03 should use existing P4-03/P4-04 case and audit contracts, not introduce
another action authority. Do not touch the final holdout, real customer data,
live CRM/telephony, or protected historical artifacts.

## P5-01 implementation boundary

`agents/workflow.py` accepts only explicit, point-in-time facts, fictional
versioned procedures, and a rules-supplied allowlist. It returns either
`DRAFT_FOR_REVIEW` with a cited allowed action or `ABSTAIN` with reason codes.
Every result fixes `authorized_to_act=false` and `human_review_required=true`.
The caller must provide the trusted rules result; P5-01 does not authenticate
that provenance or connect to production workflow. Procedure injection
screening is a conservative local check, not a complete LLM security proof.

## Verification and remaining gates

- [x] Phase 5 scope reconciled to the 14-week plan and P4-07 kept open.
- [x] P5-01 issue #197 closed by merged PR #198; branch and focused evidence
  are preserved in the merged history.
- [x] `make p5-01-check` passes (seven deterministic tests, including the
  governed human-review state-machine boundary).
- [x] P5-01 required PR CI passed on the final commit and merged; full local
  `make check` was not claimed as a separate pass.
- [x] P5-02 bounded ADK adapter and offline evaluation merged in PR #200;
  required CI passed and issue #199 closed.
- [ ] P5-03 issue #202 governed draft/HITL service integration and audit
  completed; implementation and qualification are in progress.
- [ ] Full Phase 5 qualification and review/CI pass before any milestone claim.

The selective GCP demo remains Phase 6; dedicated-cloud P4-07 qualification
must still freeze topology, arrivals, persistent-case measurement, and E1–E6
evidence before the enterprise-scale release can close.
