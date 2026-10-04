# Inforsight API contracts

The visitor demo uses the opt-in Java REST API documented in
[`openapi/demo-journey-v1.yaml`](openapi/demo-journey-v1.yaml). Docker enables it
with the `persistence` profile and `INFORSIGHT_JOURNEY_ENABLED=true`. Its public
local gateway is **http://localhost:3000**; the gateway exposes only the demo
scenario/run routes, not the legacy case APIs.

| Endpoint | Persisted behavior |
| --- | --- |
| `GET /api/v1/demo/scenarios` | Lists the implemented fictional scenarios and safe input bounds. It is a capability catalog, not a health or qualification certificate. |
| `POST /api/v1/demo/runs` | Requires `Idempotency-Key`; persists the fictional source history, run, submission journal record, and Kafka outbox in one transaction. |
| `GET /api/v1/demo/runs/{correlation_id}` | Returns authoritative run state, stage evidence, and dossier artifacts for polling and resume. |
| `POST /api/v1/demo/runs/{correlation_id}/retry` | Resumes a failed run while preserving event identity, completed artifacts, and historical failed attempts. |
| `POST /api/v1/demo/runs/{correlation_id}/decision` | Persists `APPROVED`, `REJECTED`, or `REQUEST_MORE_INFORMATION` with expected case version, rationale, reviewer label, and idempotency key. |
| `GET /api/v1/demo/runs/{correlation_id}/audit` | Recomputes the SHA-256 chain, checks the PostgreSQL checkpoint, and binds displayed artifacts and case version to recorded evidence. |

Identical submission replay returns the same run. Reusing its key with different
input returns `409`. Review rejects stale versions, changed idempotent requests,
cases not ready for review, and failed integrity verification. Approval of an
agent abstention is rejected. Unknown fields and out-of-bounds inputs are
rejected rather than silently ignored. A missing source service returns `503`
without claiming an accepted event.

Reviewer IDs are **fictional labels, not authenticated real identities**.
Every decision retains `authorized_to_act: false` and
`external_execution_enabled: false`. Requesting information records a final
outcome for this run; a later evidence-submission/re-review loop is not built.
The API has no customer destination, credentials, external CRM, or telephony
operation. It is a loopback local demo, not a production authorization API.

## Event and internal service boundary

The Java worker publishes `inforsight.demo.event/1.0.0` envelopes to Kafka topic
`inforsight.demo.events.v1`, keyed by event ID. The consumer binds an envelope
to its persisted outbox source before inserting the deduplicated inbox record.
Malformed or unbound records are quarantined by digest and broker location.
The journal records publication/ingestion evidence and input/output digests.

The exact envelope fields are:

| Field | Contract |
| --- | --- |
| `schema_version` | Literal `inforsight.demo.event/1.0.0` |
| `event_id` | Submitted event identity; Kafka record key and inbox deduplication key |
| `policy_id` | Generated fictional policy identity |
| `correlation_id` | Persisted `run_<32 hex characters>` identity |
| `event_type` | Literal `fictional.policy_event_submitted` |
| `idempotency_key` | The accepted submission's request identity |
| `submitted_at` | Server UTC timestamp, separate from the observation cutoff |
| `fictional` | Literal `true` |
| `payload` | Exact stored source object: scenario/policy/event identities, `as_of`, triggering `source_event`, policy/payment/safety `history`, `fictional`, producer identity, and `authorized_to_act: false` |

The topic has one partition and replication factor one in this local topology.
Consumer group `inforsight-demo-journey-v1` commits offsets only after durable
inbox acceptance or quarantine. Broker replay may occur; the stored event
identity prevents duplicate case/decision effects. This is not a claim of
exactly-once broker delivery.

Java calls the private `demo-runtime` HTTP endpoints for fictional source
generation, dual-profile point-in-time projection, modeled valuation, and a
deterministic bounded draft. It calls the separate inference service's
`POST /v1/score` for the released score, validating bundle identity, cutoff,
preprocessing identity, and lack of action authority. There is no hash-adapter
fallback in this journey. **gRPC inference is not implemented.**

Stage states are `waiting`, `processing`, `completed`, `abstained`, `blocked`,
and `failed`. Completion has timestamps, attempt, producer, input/output links,
and committed evidence. An audit may validly verify a partial run; `valid: true`
alone does not mean a human decision or the whole journey is complete.

## Historical and other interfaces

- [`openapi/local-demo-v1.yaml`](openapi/local-demo-v1.yaml) describes the earlier
  P5-05 synchronous fictional handoff. It is separate from the Kafka journey.
- [`openapi/control-plane-v1.yaml`](openapi/control-plane-v1.yaml) describes the
  broader case API surface. Its legacy triage implementation creates an
  `abstain` recommendation and does not constitute the visitor allocation path.
- The repository's protobuf surface expresses an intended interface; it is not
  evidence of a running gRPC service.

Run examples and acceptance commands are in the
[local demo runbook](../docs/showcase/local-demo.md). Historical Phase 5 evidence
is preserved with its original scope; it must not be relabeled as acceptance
of the new Kafka/released-model path.
