# Phase 5.02 — Bounded Google ADK Orchestration

P5-02 adds an **opt-in, offline-testable** Google ADK seam around the P5-01
review-only contract. ADK may read fictional evidence, procedure, and
rule-allowlist data and propose a structured draft. The deterministic P5-01
validator must approve the action and citations before any draft is returned;
the adapter cannot create a human approval or execute an action.

| Field | Value |
| --- | --- |
| Status | In progress |
| Milestone | [v0.5.0-agent-workflow](https://github.com/anilreddy89/Inforsight/milestone/7) |
| Issue | [#199](https://github.com/anilreddy89/Inforsight/issues/199) |
| Branch | `implementation/p5-02-bounded-adk-orchestration` |
| Depends on | P5-01 [PR #198](https://github.com/anilreddy89/Inforsight/pull/198), ADR 0002 |
| Blocks | P5-03 governed service/HITL integration; not P4-07 qualification |

## Contract and topology

1. A caller supplies one fictional `CaseInput` already bounded by P5-01.
2. A scoped ADK agent has three read-only tools: point-in-time evidence,
   versioned procedures, and the deterministic rules allowlist. Tools expose
   no mutation, network, filesystem, CRM, payment, or execution capability.
3. ADK emits one structured candidate (`case_id`, proposed action, source IDs,
   procedure citations, review-only markers).
4. The adapter re-runs the P5-01 deterministic validator and requires exact
   action/source/citation/identity equality. Any discrepancy abstains.
5. Caller receives a `ReviewDraft` with `authorized_to_act=false` and
   `human_review_required=true`; P5-03 alone will connect this to the existing
   governed case workflow.

The model's output is untrusted data. Prompt injection in a fictional
procedure, extra or missing fields, unsupported action, invented citation,
wrong case ID, timeout, and model/tool error must fail closed. A successful
offline test is not evidence of live model safety or production readiness.

## Dependency and test boundary

Use optional `google-adk==2.9.2`, pinned to Google's
[v2.9.2 release](https://github.com/google/adk-python/releases/tag/v2.9.2).
Do not add it to the simulator or inference-runtime dependency surface.
`make p5-02-check` should test the P5-02 validator without ADK; an explicit
ADK integration target and CI job install the pinned extra and run a fake model
through the actual ADK runner. No API key, Vertex project, or model endpoint
is required. The fake-model result is not a production-provider claim.

## Acceptance checks

- [x] P5-01 closeout status is reconciled across docs, tracker, README, and
  roadmap; issue #197 is closed and PR #198 is merged.
- [x] Only bounded read-only tools are exposed to ADK; no generic function,
  shell, connector, or external-action tool is reachable.
- [x] Structured candidates are schema-validated and checked against the
  deterministic P5-01 action and citation result.
- [x] Malformed, injected, mismatched, overlong, timed-out, and model-error
  scenarios abstain without leaking input content into errors.
- [ ] Offline fake-model runner and focused checks pass against pinned ADK;
  CI remains to be verified on the final reviewed commit.
- [ ] No final holdout, real customer data, credentials, protected artifacts,
  live actions, or P4-07 release claim changed.

## Remaining limitations

P5-02 does not authenticate the upstream case/rules snapshot, connect to the
Java control plane, persist agent transcripts or human decisions, or establish
live provider security. Those belong to P5-03 and later operational work.
P4-07 E1–E6 and `v0.4.0-enterprise-scale` remain open.
