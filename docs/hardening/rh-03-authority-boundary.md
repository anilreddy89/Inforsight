# RH-03 local authority boundary

Status: Implemented for the bounded local reference runtime under issue #145.

## Trust boundary

`WorkflowService` accepts a `TrustedActorContext`, not a reviewer identifier from an execution request. The dashboard obtains that context through `LocalTrustedActorAdapter`, which represents identity already established by the trusted local Streamlit process. This adapter is suitable only for fictional local demonstrations and tests. It is not an identity provider, a production authentication mechanism, or evidence of network authorization. Production federation, session validation, RBAC administration, and service-to-service authentication remain Phase 4 work.

## Approval contract

`ApprovalBinding` uses schema identity `authority-approval/1.0.0` and binds:

- approval and idempotency identities;
- case identity and expected case version;
- reviewed snapshot, safety-evidence, eligibility, and requirements identities;
- selected action and its authoritative channel;
- recommendation and model-bundle identities;
- trusted actor identity; and
- review and expiration timestamps.

The approval identifier is a deterministic digest of the bound review inputs. It is not a bearer credential and does not replace the trusted actor context.

## Execution contract

The public `WorkflowService.dispatch_execution` operation is the common local execution boundary. A request supplies the case, trusted actor context, approval identity, idempotency key, expected case version, current eligibility set, outreach reference, and optional non-authoritative metadata.

Before committing `EXECUTED`, the operation holds the service lock and verifies:

1. compatible idempotent replay or unused idempotency identity;
2. an existing approval with matching approval and idempotency identities;
3. the same trusted actor who approved the action;
4. approval freshness and exact case version;
5. unchanged snapshot, safety-evidence, requirements, and complete eligibility digest;
6. continued eligibility of the exact approved action;
7. authoritative resource requirements and available hours/money; and
8. absence of protected authority fields in caller metadata.

The state machine's generic `transition` rejects every transition to `EXECUTED`. Its internal execution commit is used only after the service boundary completes the checks above. The approved action and channel, never caller metadata, populate the execution event.

## Stable failures

Authority failures use `AuthorityBoundaryError.code`. Current codes are:

| Code | Meaning |
| --- | --- |
| `AUTH_ACTOR_UNTRUSTED` | Actor context is unauthenticated or lacks a trust source |
| `AUTH_ACTOR_UNAUTHORIZED` | Actor lacks the conservation-specialist role |
| `AUTH_ACTOR_MISMATCH` | Executing actor differs from approving actor |
| `AUTH_APPROVAL_MISSING` | No bound approval exists |
| `AUTH_APPROVAL_MISMATCH` | Approval or idempotency identity differs |
| `AUTH_APPROVAL_EXPIRED` | Execution occurs after approval expiry |
| `AUTH_CASE_VERSION_STALE` | Current and approved case versions differ |
| `AUTH_EVIDENCE_UNBOUND` | Required reviewed evidence identity is absent |
| `AUTH_EVIDENCE_STALE` | Current evidence identity differs from reviewed evidence |
| `AUTH_ELIGIBILITY_STALE` | Current eligibility content or action differs |
| `AUTH_CHANNEL_UNBOUND` | Selected action has no authoritative channel |
| `AUTH_RESOURCE_UNBOUND` | Selected action has no authoritative resource units |
| `AUTH_CAPACITY_EXHAUSTED` | Hours or money are insufficient |
| `AUTH_METADATA_OVERRIDE` | Caller metadata attempts to set a protected field |
| `AUTH_IDEMPOTENCY_CONFLICT` | An idempotency key is reused with different input |
| `AUTH_TIME_INVALID` | Authority timestamp is not timezone-aware |

Messages contain identifiers and failure categories only; source safety payloads are not copied into errors.

## Resource and atomicity boundary

The local service serializes execution with an in-process re-entrant lock. Within that boundary, case-version verification, approval use, execution, audit handoff, resource decrement, and idempotency recording occur once. Compatible retries return the original event. Concurrent calls cannot reserve local capacity twice.

This is an in-process reference mechanism. Crash recovery, durable transactional state, writer coordination, and trusted external checkpoints are explicitly deferred to RH-10. No distributed exactly-once claim is made.

## Compatibility and evidence

Historical model, dataset, generator, and Phase 3 qualification artifacts remain unchanged. The Phase 3 runner now calls the common authority boundary with explicit synthetic evidence and trusted actor context; RH-03 adversarial behavior is established by focused workflow and qualification tests. P4-02 and P4-03 remain blocked until RH-13 records `PROCEED`.
