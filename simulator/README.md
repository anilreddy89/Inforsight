# Simulator

The simulator generates small, seeded, fictional policy-event histories that conform to policy-event contract version `1.0.0`. It is a clean-room engineering fixture, not a model of a real insurer or population.

## Current event boundary

The generator uses the nine-event MVP taxonomy already defined under `data-contracts/`:

- Policy issuance and status changes.
- Premium due events.
- Successful and failed payments.
- Structured notices and service contacts.
- Lapse and surrender outcomes.

Issue age, face amount, acquisition channel, retries, reinstatement, maturity, loans, cash value, account changes, and prior conservation attempts remain deferred until a later contract-design issue demonstrates that the MVP needs them.

## Python API

Add `simulator/src` to the Python path or install the package, then call:

```python
from inforsight_simulator import generate_policy_histories

histories = generate_policy_histories(seed=20260817)
assert len(histories) == 100
```

`policy_count` defaults to 100 and accepts any positive integer. Each inner list is one ordered policy history, and every history begins with one `policy.issued` event.

## Policy-history validation

JSON Schema validates one event at a time. The simulator also provides a history-level validator for relationships that can only be checked across events:

```python
from inforsight_simulator import generate_policy_histories, validate_policy_history

history = generate_policy_histories(seed=20260817, policy_count=1)[0]
validate_policy_history(history)  # Returns None; raises ValueError when invalid.
```

Validation sorts a private representation by `(effective_at, occurred_at, event_id)`. Caller-provided order is not authoritative, and the supplied list and event dictionaries are not mutated.

The current fictional MVP transition graph is:

```text
policy.issued(initial_status=active)
    active -> grace_period
    grace_period -> active
    grace_period -> lapsed
    active -> surrendered
```

Each status change must declare the state produced by the preceding transition as its `previous_status`. No-op and other transition edges are rejected. `lapsed` and `surrendered` are terminal in this MVP, and their status changes must pair with the matching outcome at the same effective instant. Lapse also requires an earlier failed payment and lapse warning; surrender requires an earlier structured surrender inquiry.

The validator also enforces these temporal and reference invariants:

- All replay timestamps are valid UTC instants, and ingestion cannot precede occurrence.
- Activity cannot occur or become effective before issuance.
- A billing due date matches the UTC date on which that billing event becomes effective.
- A payment references an established billing item and cannot occur or become effective before it.
- Payment-reminder and lapse-warning notices cannot precede a failed payment.
- No event can become effective after a terminal state.

`effective_at` may precede `occurred_at`; that can represent a retroactively effective fact. Correction, supersession, and bitemporal known-at semantics remain deferred. The validator checks the complete supplied history, so an invalid future suffix is rejected even when reconstruction uses an earlier cutoff.

## Point-in-time state reconstruction

Reconstruction answers one question: given a policy's complete event history, what was its lifecycle state at a particular UTC time?

The public API is:

```python
reconstruct_policy_state(
    history: list[dict[str, object]],
    as_of: datetime | str,
) -> PolicyState | None
```

`history` must contain events for exactly one policy. `as_of` may be a contract-formatted string ending in `Z` or a timezone-aware UTC `datetime`.

### Basic use

Reconstruct one generated policy at an inclusive UTC effective-time cutoff:

```python
from inforsight_simulator import (
    generate_policy_histories,
    reconstruct_policy_state,
)

history = generate_policy_histories(seed=20260817, policy_count=1)[0]
state = reconstruct_policy_state(history, "2025-01-01T00:00:00Z")

if state is not None:
    print(state.policy_id, state.status, state.applied_event_count)
```

The same call using an aware `datetime` is:

```python
from datetime import datetime, timezone

state = reconstruct_policy_state(
    history,
    datetime(2025, 1, 1, tzinfo=timezone.utc),
)
```

Naive or non-UTC datetimes are rejected because their temporal meaning would be ambiguous.

### Replay flow

Reconstruction follows a small deterministic pipeline:

```text
Validate cutoff and complete history
        ↓
Parse event timestamps
        ↓
Select effective_at <= as_of
        ↓
Sort selected events deterministically
        ↓
Create state from policy.issued
        ↓
Apply policy.status_changed events
        ↓
Return immutable PolicyState
```

The cutoff comparison is inclusive. An event effective exactly at `as_of` is included; an event effective one instant later is excluded even though it is present in the supplied history. This is the point-in-time boundary that prevents future-effective events from changing an earlier result.

Selected events are sorted by:

```text
(effective_at, occurred_at, event_id)
```

`effective_at` determines when the fact changes state. `occurred_at` and `event_id` provide stable tie-breaking. Reconstruction sorts a copy, so differently ordered copies of the same valid history produce the same result and caller input is not mutated.

### How events affect state

`policy.issued` creates the initial state from its payload:

- Initial lifecycle status.
- Product variant.
- Billing frequency.
- Premium amount and currency.
- Effective issuance time.

Each selected `policy.status_changed` event then replaces the lifecycle status with its validated `new_status`. For example:

```text
policy.issued          → active
policy.status_changed  → grace_period
policy.status_changed  → active
```

A cutoff before the first status change returns `active`, a cutoff at the grace-period change returns `grace_period`, and a cutoff at recovery returns `active` again.

Billing, payment, notice, service-contact, and outcome events count as applied facts for audit metadata but do not directly change this narrow lifecycle state. The reconstructor does not infer a status from an outcome event or repair missing facts. It validates transition and outcome consistency before replay.

### Returned state

A successful call returns an immutable `PolicyState` with:

- `policy_id` and requested `as_of` cutoff.
- Current `status`.
- `product_variant`, `billing_frequency`, `premium_amount_cents`, and `currency` from issuance.
- Effective `issued_at` time.
- `applied_event_count`.
- `last_event_id` and `last_effective_at` provenance.

The frozen state object cannot be modified accidentally after reconstruction.

A valid cutoff before issuance returns `None` because the policy did not yet exist at that effective time:

```python
state = reconstruct_policy_state(history, "2020-01-01T00:00:00Z")
assert state is None
```

This differs from an invalid or ambiguous history, which raises `ValueError`.

### Validation boundary

The reconstructor validates the complete supplied history before selecting the cutoff prefix. It rejects inputs that cannot produce an unambiguous replay, including:

- Empty histories or non-event entries.
- Missing reconstruction fields.
- Events from more than one policy.
- Duplicate event identifiers.
- Unsupported event types.
- Invalid UTC timestamps or cutoffs.
- Missing or multiple issuance events.
- Activity before issuance or after a terminal state.
- Invalid lifecycle transitions or mismatched previous status.
- Missing or inconsistent terminal outcome/status pairs.
- Impossible billing, payment, notice, ingestion, or outcome timing.

Complete single-event payload validation remains the responsibility of the versioned JSON contracts. Runtime validation enforces the cross-event invariants needed by the current fictional histories without duplicating the JSON Schema validator.

### Effective time versus ingestion time

This API decides visibility using `effective_at`, not `ingested_at`. For example:

```text
effective_at = 2024-06-01T00:00:00Z
ingested_at  = 2024-06-05T00:00:00Z
as_of        = 2024-06-03T00:00:00Z
```

The event is included because it was effective by June 3. This API does not answer what Inforsight had received or knew by June 3. That would require a second ingestion-time cutoff. Late-arriving corrections and bitemporal known-at reconstruction remain deferred.

## Command line

Generate JSON Lines on standard output:

```bash
PYTHONPATH=simulator/src python3 -m inforsight_simulator \
  --seed 20260817 \
  --policy-count 100
```

Write to a caller-selected path:

```bash
PYTHONPATH=simulator/src python3 -m inforsight_simulator \
  --seed 20260817 \
  --policy-count 100 \
  --output /tmp/inforsight-policy-events.jsonl
```

The CLI refuses to overwrite an existing file. Event JSON is written to standard output or the requested file; generation provenance is written separately to standard error so it cannot corrupt the JSON Lines stream.

## Determinism guarantee

For a supported generator version, identical seed and policy-count inputs produce structurally identical histories and byte-identical JSON Lines. Generation uses:

- A dedicated seeded pseudorandom-number generator.
- A fixed UTC simulation start date.
- Counter-derived synthetic identifiers.
- Explicit history and event ordering.
- Stable compact JSON serialization with sorted keys.

It does not use wall-clock time, global random state, random UUIDs, Python hash values, or filesystem ordering. Provenance reports the seed, policy count, generator version, event-schema version, and simulation start.

Generator-version changes may intentionally alter output. Consumers that require exact replay must retain the complete provenance record.

## Fictional scenario mix

The default 100-policy corpus contains exactly 25 histories in each bounded scenario:

- Active and payment-current.
- Entered grace period and recovered.
- Lapsed after fictional nonpayment.
- Surrendered after a structured fictional inquiry.

These equal weights are transparent test inputs. They are not estimates of insurance-industry prevalence and must not be used to make performance or business claims.

## Dataset boundary

The 100-policy run is the deterministic development and acceptance corpus. This package can generate temporary larger runs, but large generated datasets should not be committed. A later issue will select a small, manually inspectable sample and publish its assumptions and limitations in `DATA_CARD.md`.

Aggregate-rate calibration, observation construction, and outcome-label derivation remain separate work.

## Tests

From the repository root, with the contract test requirements installed:

```bash
python3 -m unittest discover -s simulator/tests -v
make check
```

The tests validate the complete default corpus against the event contracts and history validator. They check count, scenario coverage, identifier uniqueness, lifecycle transitions, terminal pairs, impossible cross-event dates, payment-to-billing integrity, deterministic serialization and replay, CLI behavior, point-in-time cutoff boundaries, invalid inputs, non-mutation, and fictional-data boundaries.

For the end-to-end implementation journey and current function-call map, see [`docs/simulator-process-flow.md`](../docs/simulator-process-flow.md).
