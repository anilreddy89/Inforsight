# Data Contracts

This directory contains versioned JSON Schema definitions and small valid and invalid fictional examples.

## Version 3 event-first statistical-corpus contracts

[`v3/`](v3/) contains the closed event, recurring-observation, and protected oracle-sidecar schemas for substrate contract `3.0.0`, implemented through R2-09 issue #56. V3 observations bind a scenario-specific artifact identity, sorted dual-time-visible event IDs, a canonical visible-history digest, and complete per-feature lineage. V1/v2 schemas remain unchanged, and v3 protected sidecars cannot satisfy the public observation contract.

## Version 2 statistical-corpus contracts

[`v2/`](v2/) contains the separately versioned policy-event `2.0.0`, recurring-observation `2.0.0`, and protected oracle-sidecar `1.0.0` schemas implemented through R2-05 issue #45 and PR #46. These contracts support the non-final synthetic modeling corpus without changing the v1 envelope, payload, or observation bytes. Oracle, latent, draw, scenario, role, identifier, outcome, and post-cutoff concepts remain outside the model-visible feature surface.

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

The schemas define individual event structure. The simulator's public `validate_policy_history` ingress applies those envelope and payload schemas first and then enforces cross-event ordering, lifecycle-transition, terminal-pair, reference, and date invariants. Internal semantic helpers do not replace the public composite boundary. Correction semantics and configurable grace-period calculations remain separate work. Outcome events are facts; the Phase 2.01 modeling contract derives labels from eligible future outcomes without exposing them as features.

## Observation-record contract

[`observation-record.schema.json`](observation-record.schema.json) defines version `1.0.0` of the strict nested observation shape. Identity and cutoff metadata, feature-visible values, labels, audit provenance, and visible-event identifiers occupy separate fields. Eligible feature visibility requires both `effective_at <= as_of` and `ingested_at <= as_of`.

The schema uses mutually exclusive variants:

| Status | Value | Outcome provenance | Censoring reason |
| --- | ---: | --- | --- |
| `observed_positive` | `1` | Required | `null` |
| `observed_negative` | `0` | All `null` | `null` |
| `right_censored` | `null` | All `null` | Required supported reason |
| `not_applicable` | `null` | All `null` | `null` |

Eligible records require `eligible_active`, non-null active-policy features, and an observed or censored label. Ineligible records require null features, a supported ineligibility reason, and `not_applicable`. Contract version `1.0.0` accepts only its frozen versions, identifier shapes, and `USD` currency. Tightening states that were always invalid by the modeling contract does not change valid v1 serialization.

The simulator domain objects additionally enforce temporal relations that JSON Schema cannot express, including the exact 90-day horizon and positive source-event timing. See the [modeling contract](../docs/modeling/phase-02-01-modeling-contract.md) for the complete semantics.

## Validate the contract

Install the test-only dependency and run the contract tests:

```bash
python3 -m pip install -r data-contracts/requirements-test.txt
python3 -m unittest discover -s data-contracts/tests -v
```

The test suite checks that the envelope, payload, and observation schemas are valid JSON Schema Draft 2020-12. It covers every event type, the event examples, all four valid observation-label variants, and contradictory label, eligibility, version, currency, and type states.
