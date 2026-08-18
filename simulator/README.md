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

Point-in-time reconstruction, exhaustive transition and impossible-date validation, aggregate-rate calibration, observation construction, and outcome-label derivation remain separate work.

## Tests

From the repository root, with the contract test requirements installed:

```bash
python3 -m unittest discover -s simulator/tests -v
make check
```

The tests validate the complete default corpus against the event contracts and check count, scenario coverage, identifier uniqueness, payment-to-billing integrity, deterministic serialization, CLI behavior, and fictional-data boundaries.
