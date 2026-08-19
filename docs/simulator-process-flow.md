# Simulator Process Flow

## Purpose

This is the living implementation map for the Inforsight simulator. It records how fictional policy histories move through configuration, deterministic generation, history validation, point-in-time reconstruction, serialization, sample publication, and aggregate assessment.

Update this document whenever a simulator feature adds or changes:

- A public entry point.
- A function call in the main processing path.
- A generated scenario or event type.
- An ordering, lifecycle, date, or reference invariant.
- A state field or cutoff rule.
- Serialization, provenance, or CLI behavior.
- Published sample selection, composition, or integrity behavior.
- Aggregate metric definitions, provenance, or assessment-artifact behavior.

The event JSON Schemas remain the source of truth for individual event structure. This document explains how the Python simulator composes and processes those events.

## Current journey at a glance

```text
Caller or CLI
    |
    +-- generate_policy_histories(seed, policy_count)
    |       |
    |       +-- GeneratorConfig validates reproducibility inputs
    |       +-- _generate_history builds one fictional policy timeline
    |       +-- add_event creates immutable event dictionaries
    |       +-- returns list[list[PolicyEvent]]
    |
    +-- validate_policy_history(history)
    |       |
    |       +-- _prepare_history validates replay fields and parses timestamps
    |       +-- deterministic sort by effective_at, occurred_at, event_id
    |       +-- _validate_timeline checks cross-event dates and references
    |       +-- _validate_statuses_and_outcomes checks lifecycle coherence
    |       +-- returns None or raises ValueError
    |
    +-- reconstruct_policy_state(history, as_of)
    |       |
    |       +-- validates cutoff
    |       +-- validates the complete history
    |       +-- selects effective_at <= as_of
    |       +-- replays issuance and status changes
    |       +-- returns PolicyState or None
    |
    +-- histories_to_jsonl(histories)
    |       |
    |       +-- stable event flattening
    |       +-- sorted JSON keys and compact separators
    |       +-- returns byte-stable JSON Lines text
    |
    +-- scripts/build_sample_dataset.py
    |       |
    |       +-- generate canonical seed-20260817 100-policy corpus
    |       +-- select first two complete histories per scenario
    |       +-- serialize eight histories to stable JSON Lines
    |       +-- build deterministic counts, provenance, and SHA-256 manifest
    |       +-- write artifacts explicitly or verify committed bytes
    |
    +-- scripts/assess_synthetic_rates.py
            |
            +-- generate and validate canonical 100-policy corpus
            +-- calculate explicit count, ratio, amount, and timing metrics
            +-- attach source, comparability, and calibration decisions
            +-- write or verify deterministic assessment JSON
```

Generation, validation, reconstruction, serialization, publication, and assessment are separate capabilities. A caller may generate and serialize without reconstructing state, or validate and reconstruct a history supplied from another schema-valid source. Publication and assessment are repository-maintenance paths rather than part of the simulator's public Python API.

## Main data shapes

### Generator configuration

`GeneratorConfig` is an immutable dataclass containing:

```text
seed
policy_count
simulation_start
```

The seed and count are explicit reproduction inputs. The simulation start is fixed and UTC-aware by default. Invalid types, nonpositive counts, naive timestamps, and non-UTC starts fail before generation.

### Policy event

The simulator currently uses dictionaries matching policy-event contract version `1.0.0`:

```python
{
    "schema_version": "1.0.0",
    "event_id": "evt_...",
    "policy_id": "pol_...",
    "event_type": "policy.issued",
    "occurred_at": "2024-01-01T10:00:00Z",
    "effective_at": "2024-01-01T10:00:00Z",
    "ingested_at": "2024-01-01T11:00:00Z",
    "payload": {...},
}
```

One policy history is `list[PolicyEvent]`. A generator run returns `list[list[PolicyEvent]]`.

### Prepared event

History validation creates a private immutable `PreparedEvent` for each supplied event. It keeps the original event dictionary and parsed UTC values for:

- `effective_at`
- `occurred_at`
- `ingested_at`

Prepared events prevent repeated timestamp parsing and provide the shared representation used by validation and reconstruction. Preparation and sorting do not mutate caller input.

### Reconstructed policy state

`PolicyState` is an immutable dataclass containing:

- Policy identity and requested `as_of` cutoff.
- Current lifecycle status.
- Stable issuance attributes.
- Effective issuance time.
- Applied-event count.
- Last-applied event ID and effective timestamp.

It represents effective-time state only. It is not an ingestion-time or bitemporal view.

## Journey 1: Python generation API

Public call:

```python
histories = generate_policy_histories(seed=20260817, policy_count=100)
```

Call chain:

```text
generate_policy_histories(seed, policy_count)
    |
    +-- GeneratorConfig(seed, policy_count)
    |       +-- __post_init__ validates seed, count, and UTC start
    |
    +-- random.Random(config.seed)
    |       +-- isolated seeded pseudorandom state
    |
    +-- build and deterministically shuffle scenario assignments
    |
    +-- _generate_history(...) once per policy
            |
            +-- derive policy ID and fictional issuance values
            +-- nested add_event(...)
            |       +-- derive event ID from stable counters
            |       +-- format UTC timestamps
            |       +-- set ingestion one hour after occurrence
            |       +-- append the event dictionary
            |
            +-- emit the selected bounded scenario
```

### Scenario branches

Every history begins with `policy.issued`, followed by `billing.premium_due`.

```text
active
    policy.issued
    -> billing.premium_due
    -> payment.received
    -> optional service.contact_recorded

recovered
    policy.issued
    -> billing.premium_due
    -> payment.failed
    -> notice.sent(payment_reminder)
    -> policy.status_changed(active -> grace_period)
    -> payment.received
    -> policy.status_changed(grace_period -> active)

lapsed
    policy.issued
    -> billing.premium_due
    -> payment.failed
    -> notice.sent(payment_reminder)
    -> policy.status_changed(active -> grace_period)
    -> notice.sent(lapse_warning)
    -> outcome.lapsed
    -> policy.status_changed(grace_period -> lapsed)

surrendered
    policy.issued
    -> billing.premium_due
    -> payment.received
    -> service.contact_recorded(surrender_inquiry)
    -> outcome.surrendered
    -> policy.status_changed(active -> surrendered)
```

Outcome and terminal status events share an effective timestamp. Stable event IDs provide the final tie-breaker.

### Generation guarantees

Generation does not use wall-clock time, global random state, random UUIDs, Python hashes, or filesystem order. Identical supported inputs produce structurally identical histories. When passed to stable serialization, they also produce byte-identical JSON Lines.

Generation itself does not call the history validator. Generator tests validate all 100 default histories, while callers can explicitly validate histories with `validate_policy_history`.

## Journey 2: History validation

Public call:

```python
validate_policy_history(history)
```

Call chain:

```text
validate_policy_history(history)
    |
    +-- prepare_and_validate_history(history)
            |
            +-- _prepare_history(history)
            |       +-- require a nonempty list of event dictionaries
            |       +-- require replay fields
            |       +-- verify one policy ID and unique event IDs
            |       +-- verify supported event types
            |       +-- parse timestamps with parse_utc_timestamp
            |       +-- reject ingestion before occurrence
            |       +-- require exactly one issuance event
            |
            +-- sorted(...)
            |       +-- key: (effective_at, occurred_at, event_id)
            |
            +-- _validate_timeline(ordered)
                    +-- validate issuance and cross-event timing
                    +-- index billing, failure, warning, inquiry, and outcome facts
                    +-- validate payment and notice relationships
                    +-- _validate_statuses_and_outcomes(...)
                    +-- validate lapse and surrender prerequisites
```

Success returns `None`. Failure raises `ValueError` with the violated invariant and, where useful, the event identifier.

### Why validation sorts first

Caller-provided list order is not authoritative. Validation creates a total replay order using:

```text
(effective_at, occurred_at, event_id)
```

This makes validation and reconstruction repeatable for shuffled copies of the same valid history. `effective_at` controls when a fact affects state; `occurred_at` and `event_id` resolve ties.

### Validation layers

```text
JSON Schema
    validates one event's fields, types, enums, patterns, and payload shape

History validator
    validates relationships, lifecycle, chronology, and references across events

Reconstructor
    selects the validated history prefix visible at an effective-time cutoff
```

The runtime validator does not duplicate complete JSON Schema validation.

### Lifecycle validation

The current supported transition table is:

```text
active       -> grace_period
grace_period -> active
grace_period -> lapsed
active       -> surrendered
```

For every `policy.status_changed` event:

1. `previous_status` must equal the replayed current state.
2. The previous/new pair must exist in the supported table.
3. The new state becomes current for the next transition.
4. Lapsed and surrendered become terminal.

Terminal status changes require the matching outcome at the same effective instant. Conflicting or repeated terminal outcomes are rejected. No later-effective activity is permitted.

### Temporal and reference validation

The current cross-event checks include:

- Ingestion does not precede occurrence.
- Non-issuance activity does not occur or become effective before issuance.
- Billing IDs are unique within a history.
- A billing due date equals the UTC calendar date of its `effective_at` timestamp.
- A payment references an already established billing item.
- A payment does not occur or become effective before its billing item.
- Payment-reminder and lapse-warning notices follow a failed payment.
- A lapse follows a failed payment and lapse warning.
- A surrender follows a structured surrender inquiry.
- Terminal outcome and status facts are complete and consistent.

The current contract intentionally allows `effective_at < occurred_at`, which can represent a retroactively effective fact. Correction and supersession semantics are not yet implemented.

## Journey 3: Point-in-time reconstruction

Public call:

```python
state = reconstruct_policy_state(history, as_of)
```

Call chain:

```text
reconstruct_policy_state(history, as_of)
    |
    +-- _parse_cutoff(as_of)
    |       +-- accept a UTC Z string or aware UTC datetime
    |
    +-- prepare_and_validate_history(history)
    |       +-- validate the complete supplied history
    |       +-- return deterministic prepared-event order
    |
    +-- select item.effective_at <= cutoff
    |
    +-- replay selected events
    |       +-- policy.issued -> _initial_state_values(...)
    |       +-- policy.status_changed -> replace current status
    |       +-- other events -> audit count/provenance only
    |
    +-- return PolicyState, or None before issuance
```

### Cutoff behavior

- The cutoff is inclusive.
- Events effective exactly at the cutoff are applied.
- Future-effective events are excluded from the returned state.
- A cutoff before issuance returns `None`.
- An invalid complete history raises `ValueError`, even when the invalid event is after the requested cutoff.

Valid repeated calls at the same cutoff return equal immutable state. Shuffling valid input does not change the result.

## Journey 4: Stable serialization

Public call:

```python
jsonl = histories_to_jsonl(histories)
```

Call chain:

```text
histories_to_jsonl(histories)
    |
    +-- iterate histories in supplied order
    +-- iterate events in supplied history order
    +-- json.dumps(...)
    |       +-- sort_keys=True
    |       +-- compact separators
    |       +-- ASCII-safe encoding
    +-- append one newline per event
    +-- return one string
```

Serialization preserves caller-supplied record order; it does not sort histories or events. The generator is responsible for producing their stable order. Changing generated event content, ordering, or serialization can change public bytes and may require a generator-version update.

## Journey 5: Command-line generation

Entry command:

```bash
PYTHONPATH=simulator/src python3 -m inforsight_simulator \
  --seed 20260817 \
  --policy-count 100 \
  --output /tmp/inforsight-policy-events.jsonl
```

Call chain:

```text
python -m inforsight_simulator
    |
    +-- __main__.main(argv)
            +-- build_parser()
            +-- parse --seed, --policy-count, --output
            +-- GeneratorConfig(...)
            +-- generate_policy_histories(...)
            +-- histories_to_jsonl(...)
            +-- generation_provenance(config)
            +-- write JSON Lines to stdout or exclusive-create output path
            +-- write provenance to stderr
            +-- return exit code 0
```

The CLI refuses to overwrite an existing file. JSON Lines and provenance use separate streams so diagnostic metadata cannot corrupt event output.

Current provenance contains:

- Generator version.
- Event-schema version.
- Seed.
- Policy count.
- Simulation start.

## Journey 6: Published sample dataset

Repository-maintenance commands:

```bash
python3 scripts/build_sample_dataset.py --check
python3 scripts/build_sample_dataset.py --write
```

Call chain:

```text
build_sample_dataset.py
    |
    +-- GeneratorConfig(seed=20260817, policy_count=100)
    +-- generate_policy_histories(...)
    +-- select_sample_histories(...)
    |       +-- classify structured event sequence
    |       +-- retain first two complete histories per scenario
    |       +-- fail unless all four scenarios are satisfied
    +-- histories_to_jsonl(selected)
    +-- compute scenario, event-type, and product counts
    +-- compute SHA-256 over exact JSONL bytes
    +-- serialize deterministic sample-manifest.json
    +-- --check compares both committed artifacts byte for byte
    +-- --write intentionally replaces both committed artifacts
```

The published sample contains eight complete histories and 49 events. It covers every current scenario and event type plus both fictional product variants. The manifest records dataset, generator, and schema versions; source inputs; selection rules; composition; and integrity metadata. The colocated `datasets/DATA_CARD.md` defines intended uses and limitations.

Publication does not alter generator behavior or expose a new simulator API. Exact regeneration protects the artifact from manual edits, stale provenance, newline changes, and other drift.

## Journey 7: Aggregate synthetic-rate assessment

Repository-maintenance commands:

```bash
python3 scripts/assess_synthetic_rates.py --check
python3 scripts/assess_synthetic_rates.py --write
```

Call chain:

```text
assess_synthetic_rates.py
    |
    +-- GeneratorConfig(seed=20260817, policy_count=100)
    +-- generate_policy_histories(...)
    +-- validate_policy_history(...) for every complete history
    +-- classify_scenario(...) from structured lifecycle events
    +-- assess_histories(...)
    |       +-- calculate policy and event counts
    |       +-- retain numerator and denominator for every proportion
    |       +-- summarize premium cents and effective-time intervals
    +-- attach fixed public-source metadata and precise locators
    +-- record comparable, directional_only, or not_comparable judgments
    +-- record retain, parameterize, defer, or no-change decisions
    +-- --check compares committed JSON byte for byte
    +-- --write intentionally replaces the derived JSON artifact
```

The assessment consumes the canonical 100-policy development corpus, not the balanced eight-policy published sample. It reports one-path synthetic proportions and does not annualize them. Public source values remain metadata and comparison context; they are not generator inputs. The maintained report at `docs/experiments/phase-01-07-synthetic-rate-assessment.md` explains why no reviewed measure is directly comparable and why generator and dataset versions remain unchanged.

## Failure journey

Failures are intentionally raised near the boundary that owns them:

| Boundary | Typical failure | Behavior |
| --- | --- | --- |
| Configuration | Invalid seed/count or non-UTC start | `TypeError` or `ValueError` |
| JSON Schema tests | Invalid individual event shape or payload | Schema validation error |
| History preparation | Missing replay field, invalid timestamp, duplicate event ID, mixed policies | `ValueError` |
| Timeline validation | Impossible date/reference relationship | `ValueError` |
| Lifecycle validation | Mismatched or unsupported transition, inconsistent terminal outcome | `ValueError` |
| Reconstruction cutoff | Naive, non-UTC, or malformed cutoff | `ValueError` |
| CLI output | Existing or unwritable output path | Argument-parser error and nonzero exit |
| Sample selection | Source corpus cannot supply two histories per scenario | `ValueError` |
| Sample verification | Missing or stale dataset or manifest bytes | Diagnostic and nonzero exit |
| Assessment input | Empty histories, invalid history, or unsupported scenario | `ValueError` |
| Assessment calculation | Zero denominator or non-whole-day timing assumption | `ValueError` |
| Assessment verification | Missing or stale committed result | Diagnostic and nonzero exit |

The simulator does not silently repair, reorder in place, or infer missing lifecycle facts.

## Public API map

The package exports these current simulator-facing functions and values:

| Public name | Responsibility |
| --- | --- |
| `GeneratorConfig` | Validate explicit deterministic generation inputs |
| `generate_policy_histories` | Produce fictional policy-event histories |
| `generation_provenance` | Describe the inputs and versions needed to identify a run |
| `validate_policy_history` | Validate cross-event history invariants |
| `reconstruct_policy_state` | Derive effective-time state at an inclusive cutoff |
| `PolicyState` | Hold immutable reconstructed state and audit metadata |
| `histories_to_jsonl` | Serialize events to stable JSON Lines |

## Test map

| Test module | Process boundary protected |
| --- | --- |
| `test_generator.py` | Counts, scenarios, schema validity, references, ordering, deterministic generation |
| `test_history_validation.py` | Lifecycle transitions, dates, references, terminal rules, shuffled and repeated replay |
| `test_reconstruction.py` | Cutoff semantics, returned state, invalid history inputs, non-mutation |
| `test_serialization.py` | JSON Lines stability and CLI stream/file behavior |
| `test_published_dataset.py` | Published schema/history validity, coverage, manifest integrity, and exact regeneration |
| `test_synthetic_rate_assessment.py` | Metric math, denominators, provenance, sources, decisions, and exact assessment regeneration |
| `test_scaffold.py` | Public clean-room project identity |
| `data-contracts/tests/test_policy_event_contract.py` | Individual envelope and payload contracts |

Run the full process verification from the repository root:

```bash
source .venv/bin/activate
make check
git diff --check
```

## Maintenance checklist

When the simulator process changes, update the relevant sections above and confirm:

- [ ] The current journey diagram includes the new or changed stage.
- [ ] The affected public and internal call chains are accurate.
- [ ] New event types or scenarios appear in the scenario branches.
- [ ] New lifecycle edges appear in the transition table.
- [ ] New cross-event invariants appear in the validation section.
- [ ] New state fields or cutoff semantics appear in reconstruction.
- [ ] Serialization or provenance changes are documented.
- [ ] The public API and test maps include new modules or entry points.
- [ ] Deferred behavior and authority boundaries remain explicit.
- [ ] Deterministic-output changes include an intentional version decision.
- [ ] `make check` and `git diff --check` pass.

## Known deferred extensions

The flow does not yet include:

- Ingestion-time or bitemporal known-at reconstruction.
- Corrections, supersession, retractions, or event authority resolution.
- Reinstatement or transitions out of terminal states.
- Configurable grace-period or notice calculations.
- Observation records, 90-day labels, features, or model inputs.
- Storage, services, messaging, or cloud execution.

Add these to the journey only when their contracts and implementation are introduced.
