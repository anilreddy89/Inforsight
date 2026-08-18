# Data Contracts

This directory contains versioned JSON Schema definitions and small valid and invalid fictional examples.

## Policy-event envelope

[`policy-event.schema.json`](policy-event.schema.json) defines version `1.0.0` of the shared envelope for immutable events in a fictional policy history. The envelope selects a strict schema under [`payloads/`](payloads/) according to `event_type`. Unsupported event types, mismatched payloads, missing required fields, and unknown payload properties are rejected.

The envelope distinguishes three UTC timestamps:

- `occurred_at`: when the fictional event happened.
- `effective_at`: when the event begins affecting reconstructed policy state.
- `ingested_at`: when Inforsight learned about the event.

Keeping these meanings separate supports later point-in-time reconstruction. A state or feature computed as of an observation time must not use an event that was not yet available under the applicable reconstruction rule.

Corrections must be represented as new immutable events rather than edits to an existing event. All identifiers and example values are synthetic and cannot be joined to external records.

## Supported event types

| Event type | Payload purpose |
| --- | --- |
| `policy.issued` | Establish product variant, active status, billing frequency, and premium. |
| `policy.status_changed` | Record the previous and new lifecycle status with a structured reason. |
| `billing.premium_due` | Record a fictional billing identifier, due date, and amount. |
| `payment.received` | Record a successful fictional payment against a billing item. |
| `payment.failed` | Record an unsuccessful fictional payment attempt and structured reason. |
| `notice.sent` | Record notice type and delivery channel without message content. |
| `service.contact_recorded` | Record a structured fictional interaction without personal or free-form content. |
| `outcome.lapsed` | Record a fictional nonpayment lapse and outstanding amount. |
| `outcome.surrendered` | Record a fictional surrender reason and value. |

Amounts are integer cents and the initial currency is fixed to `USD`. Payload dates are ISO 8601 calendar dates; event times remain UTC timestamps in the envelope. Identifiers use synthetic, type-specific prefixes. Enum values are project-local fictional terms rather than representations of insurer procedures.

These schemas validate individual event structure only. The simulator's `validate_policy_history` API separately enforces the current cross-event ordering, lifecycle-transition, terminal-pair, reference, and date invariants. Correction semantics, configurable grace-period calculations, and label derivation remain separate work. Outcome events are facts; the later ML contract will derive prediction labels from eligible future outcome events.

## Validate the contract

Install the test-only dependency and run the contract tests:

```bash
python3 -m pip install -r data-contracts/requirements-test.txt
python3 -m unittest discover -s data-contracts/tests -v
```

The test suite checks that the envelope and every payload schema are valid JSON Schema Draft 2020-12 with unique identifiers. It proves that every supported event type has a valid example, every file under `examples/policy-event/valid` passes, and every file under `examples/policy-event/invalid` fails for its intended reason.
