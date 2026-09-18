# P4-02 — Kafka streaming ingress and event contracts

P4-02 introduces the versioned event boundary used when Inforsight moves from
static JSONL playback to live event ingestion. The first increment is broker-
independent: it freezes the value contracts and makes validation,
deduplication, and dead-letter routing testable without Docker.

Tracking issue: [#184](https://github.com/anilreddy89/Inforsight/issues/184).

## Topics

| Topic | Contract | Event families |
| --- | --- | --- |
| `policy.lifecycle.v1` | `policy-lifecycle-events/1.0.0` | Issuance, status changes, endorsements |
| `billing.payment.v1` | `billing-payment-events/1.0.0` | Invoices, premium due, payments, retries |
| `customer.service.v1` | `customer-service-events/1.0.0` | Contacts, notices, disputes, preferences |

Each topic has a matching `<topic>.dlq` destination for malformed, unversioned,
or domain-mismatched values. Every accepted value includes an immutable
`event_id` and producer-scoped `idempotency_key`; duplicate pairs are ignored
before downstream processing.

## Current boundary

`inforsight_simulator.streaming.StreamingIngress` is the safety boundary that a
future Kafka adapter will call. It does not claim broker delivery, offset
commit, ordering, or exactly-once processing. Those behaviors remain acceptance
work for the Kafka integration slice.

## Completion evidence

- The local Kafka-only harness is `infra/docker-compose.kafka.yml`; start it
  with `docker compose -f infra/docker-compose.kafka.yml up -d`.
- The optional Python client and Testcontainers dependencies are listed in
  `simulator/requirements-p4-02-integration.txt`.
- `KafkaStreamingAdapter` publishes event IDs as Kafka keys, validates consumed
  JSON through the ingress boundary, and routes malformed values to DLQ.
- `make streaming-check` passes with unit coverage for validation,
  deduplication, late-ingestion visibility, conflicting event IDs, and DLQ
  behavior.
- `make streaming-integration-check` passes with 10,000 valid events arriving
  in reverse order, one malformed event, zero loss, canonical replay order, and
  one matching DLQ record.
- `make p4-02-check` runs the focused fast path; use
  `make p4-02-integration-check` to include the Docker/Testcontainers gate.

P4-02 implementation is complete on the issue branch; the pull request and
merge into `main` remain the release workflow’s final steps. P4-03 remains
blocked until that merge.
