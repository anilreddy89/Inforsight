# Data Contracts

This directory contains versioned JSON Schema definitions and small valid and invalid fictional examples.

## Policy-event envelope

[`policy-event.schema.json`](policy-event.schema.json) defines version `1.0.0` of the shared envelope for immutable events in a fictional policy history. Event-specific billing, payment, notice, service, and outcome payload contracts are intentionally deferred. Until those contracts exist, `payload` accepts any JSON object.

The envelope distinguishes three UTC timestamps:

- `occurred_at`: when the fictional event happened.
- `effective_at`: when the event begins affecting reconstructed policy state.
- `ingested_at`: when Inforsight learned about the event.

Keeping these meanings separate supports later point-in-time reconstruction. A state or feature computed as of an observation time must not use an event that was not yet available under the applicable reconstruction rule.

Corrections must be represented as new immutable events rather than edits to an existing event. All identifiers and example values are synthetic and cannot be joined to external records.

## Validate the contract

Install the test-only dependency and run the contract tests:

```bash
python3 -m pip install -r data-contracts/requirements-test.txt
python3 -m unittest discover -s data-contracts/tests -v
```

The test suite first checks that the schema itself is valid JSON Schema Draft 2020-12. It then proves that every file under `examples/policy-event/valid` passes and every file under `examples/policy-event/invalid` fails.
