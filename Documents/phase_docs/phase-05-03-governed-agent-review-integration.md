# Phase 5.03 — Governed Agent Draft and Human-Review Integration

P5-03 connects review-only agent output to an existing control-plane case without
creating a second decision authority. The Java service records a bounded,
untrusted draft for a specialist to inspect. Only the existing versioned human
decision endpoint can change case state; an agent draft cannot approve, override,
or execute an action.

| Field | Value |
| --- | --- |
| Status | In progress |
| Milestone | [v0.5.0-agent-workflow](https://github.com/anilreddy89/Inforsight/milestone/7) |
| Issue | [#202](https://github.com/anilreddy89/Inforsight/issues/202) |
| Branch | `implementation/p5-03-governed-agent-review-integration` |
| Predecessors | P5-01 PR #198; P5-02 PR #200 and closeout PR #201 |
| Additive API contract | `api/openapi/control-plane-v1.yaml` v1.1.0; draft payload contract v1.0.0 |

## Boundary and data flow

1. The caller produces a `ReviewDraft` using P5-01/P5-02 offline logic. An
   opt-in Python bridge serializes that contract for a local-only control-plane
   transport; there is no automatic provider or external network call.
2. The service accepts only a review-only draft for an existing case and exact
   current case version. It derives the case/snapshot binding server-side and
   records a bounded draft with idempotent replay protection.
3. Persistence-profile writes the draft and hash-chained `AGENT_DRAFT_RECORDED`
   audit event in one transaction. A review read is side-effect-free.
4. Specialist rejection/override/approval remains at the existing human
   decision endpoint and is independently versioned/audited. Agent draft
   content is never consumed as an approval token or connector preflight.

An HTTP caller is not trusted merely because it names P5-01/P5-02. The Java
service cannot independently re-run Python evidence/rule checks or authenticate
their provenance; therefore a submitted action/citation is displayed as an
**untrusted advisory**, not reclassified as eligible. Production caller identity,
attestation, live ADK/provider security, and richer decision-request validation
remain explicit follow-up requirements. No live external action is enabled.

## Acceptance

- [x] Submission rejects missing/oversized fields, authority flags, wrong
  case identity, stale version, and replay-key payload mismatch.
- [x] An agent draft does not change `control_case` state/version or
  `authorized_to_act`; human review remains a separate call.
- [x] Persisted draft plus audit append is transactional and case/snapshot-bound.
- [x] Focused Java and persistence integration tests cover rejection, replay,
  human decision separation, and audit evidence.
- [ ] Required CI passes on the final reviewed commit; docs/tracker/roadmap
  state only evidenced completion.
- [ ] No final holdout, real customer data, credentials, protected artifacts,
  or P4-07 release claim changes.

## Scope exclusions

No live ADK model calls, authentication federation, CRM/telephony action,
production deployment, or P4-07 E1–E6 qualification. Phase 5 milestone remains
open until the integrated acceptance and review are completed.

## Local evidence and remaining review

`make p5-03-check`, `make p5-03-integration-check` (Docker Desktop with Docker
API 1.44), full control-plane `mvn test`, the RH-09 contract consistency check,
roadmap JavaScript syntax check, and `git diff --check` passed locally. Required
PR CI on the final commit is still pending. The existing decision endpoint is
not changed by this increment; its reviewer identity is request data rather
than authenticated production identity. Override authorization semantics need
separate qualification before any production or end-to-end safety claim.
