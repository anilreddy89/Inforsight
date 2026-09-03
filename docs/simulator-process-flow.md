# Simulator Process Flow

## Purpose

This is the living implementation map for the Inforsight simulator. It records how fictional policy histories move through configuration, deterministic generation, history validation, point-in-time reconstruction, observation construction, temporal splitting, serialization, sample publication, and aggregate assessment.

Update this document whenever a simulator feature adds or changes:

- A public entry point.
- A function call in the main processing path.
- A generated scenario or event type.
- An ordering, lifecycle, date, or reference invariant.
- A state field or cutoff rule.
- Serialization, provenance, or CLI behavior.
- Published sample selection, composition, or integrity behavior.
- Aggregate metric definitions, provenance, or assessment-artifact behavior.
- Observation eligibility, dual-time visibility, label, censoring, or sufficiency behavior.
- Temporal partition boundaries, embargo, policy isolation, episode isolation, or split-manifest behavior.

The event JSON Schemas remain the source of truth for individual event structure. This document explains how the Python simulator composes and processes those events.

## Current journey at a glance

```text
Caller or CLI
    |
    +-- generate_policy_histories(config)
    |       |
    |       +-- GeneratorConfig validates all reproducibility inputs
    |       +-- canonical config digest binds provenance and run identity
    |       +-- run namespace isolates generator-owned identifiers
    |       +-- _generate_history builds one fictional policy timeline
    |       +-- add_event creates immutable event dictionaries
    |       +-- returns list[list[PolicyEvent]]
    |
    +-- validate_policy_history(history)
    |       |
    |       +-- policy-event JSON Schema validates envelope fields
    |       +-- selected payload schema validates event-specific fields
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
    +-- build_observation(history, as_of, follow_up_through)
    |       |
    |       +-- validate complete history and cutoff inputs
    |       +-- require effective_at and ingested_at at or before as_of
    |       +-- derive active-policy eligibility and feature-visible values
    |       +-- derive the separate 90-day outcome label
    |       +-- OutcomeLabel validates one mutually exclusive label state
    |       +-- ObservationRecord validates eligibility, time, and provenance relations
    |       +-- return immutable validated ObservationRecord
    |
    +-- build_first_billing_observations(histories, follow_up_through)
    |       |
    |       +-- anchor one cutoff at first billing-due ingestion per policy
    |       +-- build observations and reject duplicate identifiers
    |       +-- sort records by as_of and policy_id
    |
    +-- assign_temporal_splits(records, specification)
    |       |
    |       +-- validate guarded observation records and contract versions
    |       +-- sort by as_of, policy_id, and observation_id
    |       +-- assign train, embargo, validation, gap, test, or exclusion
    |       +-- reject cross-partition policy or outcome-episode ownership
    |       +-- enforce strict 90-day horizon separation
    |       +-- return immutable TemporalSplitResult
    |
    +-- build_feature_pipeline(temporal_split_result)
    |       |
    |       +-- validate exact guarded feature payloads and modeling membership
    |       +-- fit numeric statistics and categorical vocabularies on train only
    |       +-- freeze unknown columns, output names, and partition identities
    |       +-- apply immutable state to train, validation, and test
    |       +-- return fitted state and matrices with identity/target sidecars
    |
    +-- fit_logistic_baseline(train_matrix)
    |       |
    |       +-- validate exact train partition, identities, targets, and finite values
    |       +-- fit the single frozen seeded logistic specification
    |       +-- reject convergence or class-order failures
    |       +-- bind coefficients to frozen feature names and training digest
    |       +-- return explicit immutable fitted state
    |
    +-- evaluate_logistic_baseline(fitted, train_or_validation_matrix)
    |       |
    |       +-- reconstruct positive-class probabilities from explicit state
    |       +-- reject canonical test or unsupported partition scoring
    |       +-- calculate predeclared metrics and prediction digest
    |       +-- preserve fitted model and preprocessing state unchanged
    |
    +-- fit_boosted_model(train_matrix)
    |       |
    |       +-- validate the exact train partition and frozen issue-#26 specification
    |       +-- fit one deterministic XGBoost candidate with no early stopping
    |       +-- export native JSON model state with provenance and digests
    |       +-- validate tree count, dependency version, and safe reconstruction
    |
    +-- compare_models(logistic, boosted, train_or_validation_matrix)
    |       |
    |       +-- enforce identical matrix membership and frozen metric definitions
    |       +-- calculate both prediction digests from unrounded probabilities
    |       +-- reject canonical test scoring at each model boundary
    |
    +-- feature diagnostics on train and validation
    |       |
    |       +-- group frozen output columns by reviewed source feature
    |       +-- calculate univariate mutual information on train only
    |       +-- fit decision stumps on train and score validation
    |       +-- screen identifiers, cardinality, constancy, and near constancy
    |       +-- permute mechanically flagged validation groups deterministically
    |       +-- require allow, exclude, or investigate dispositions for flags
    |       +-- reject canonical test access and preserve frozen model state
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
    |       |
    |       +-- generate and validate canonical 100-policy corpus
    |       +-- calculate explicit count, ratio, amount, and timing metrics
    |       +-- attach source, comparability, and calibration decisions
    |       +-- write or verify deterministic assessment JSON
    |
    +-- scripts/build_observations.py
    |       |
    |       +-- generate canonical seed-20260817 100-policy corpus
    |       +-- derive one first-billing cutoff per policy
    |       +-- set an explicit shared 90-day follow-up watermark
    |       +-- build records and deterministic sufficiency counts
    |       +-- write or verify deterministic gate evidence
    |
    +-- scripts/build_temporal_splits.py
    |       |
    |       +-- regenerate the canonical guarded observations
    |       +-- apply the frozen half-open UTC split specification
    |       +-- summarize assignments, labels, ranges, and billing frequencies
    |       +-- hash canonical source identity and temporal fields
    |       +-- write or verify the deterministic split manifest
    |
    +-- scripts/build_feature_pipeline.py
    |       |
    |       +-- regenerate canonical observations and frozen splits
    |       +-- publish or verify the complete feature dictionary
    |       +-- fit preprocessing from train observation IDs only
    |       +-- transform held-out partitions without mutating fitted state
    |       +-- write or verify metadata, fitted-state, and matrix digests
    |
    +-- scripts/train_logistic_baseline.py
    |       |
    |       +-- rebuild the frozen Phase 2.04 matrices
    |       +-- fit once on train and score train and validation only
    |       +-- keep canonical test sealed and absent from metrics
    |       +-- publish or verify explicit fitted state, diagnostics, and report
    |
    +-- scripts/train_boosted_comparison.py
    |       |
    |       +-- rebuild the same frozen matrices and unchanged logistic baseline
    |       +-- fit the single XGBoost candidate on train only
    |       +-- compare both models on identical train and validation membership
    |       +-- publish or verify safe fitted state, comparison evidence, and test seal
    |
    +-- scripts/run_feature_diagnostics.py
            |
            +-- rebuild frozen matrices and both unchanged frozen models
            +-- run train-only and validation-scored source-feature screens
            +-- perturb only mechanically flagged validation groups
            +-- publish flags, governed dispositions, upstream digests, and test seal
```

Generation, validation, reconstruction, observation construction, temporal splitting, feature preprocessing, baseline fitting, serialization, publication, and assessment are separate capabilities. A caller may generate and serialize without reconstructing state, or validate and reconstruct a history supplied from another schema-valid source. Publication and assessment are repository-maintenance paths rather than part of the simulator's public Python API.

## Main data shapes

### Generator configuration

`GeneratorConfig` is an immutable dataclass containing:

```text
seed
run_namespace
policy_count
simulation_start
```

All four fields are explicit corrected-generation inputs. The namespace is 1 to 64 canonical lowercase characters and isolates deterministic run identifiers. The simulation start is UTC-aware and defaults to the historical start. Invalid types, nonpositive counts, invalid namespaces, naive timestamps, and non-UTC starts fail before generation.

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

### Observation record

`ObservationRecord` is an immutable nested dataclass containing:

- Contract and label-policy versions.
- Stable observation and policy identifiers.
- UTC cutoff and 90-day horizon boundaries.
- Eligibility and its reason.
- A separate `ObservationFeatures` value for eligible records.
- A separate `OutcomeLabel` with censoring and source-event provenance.
- Dual-time-visible event identifiers for audit.
- Generator and event-schema versions.

The JSON representation follows `data-contracts/observation-record.schema.json`. Identity and audit fields are never placed in `features`.

### Temporal split result

`TemporalSplitResult` is an immutable collection of observations assigned to:

- Train.
- Embargo.
- Validation.
- Calendar gap.
- Test.
- Explicit exclusion.

`TemporalSplitSpecification` defines half-open UTC boundaries. Assignment is deterministic under reordered input. The validator requires complete accounting, both binary classes in each modeling partition, zero cross-partition policy and outcome-episode ownership, and strict separation between an earlier partition's latest label horizon and the next partition's earliest cutoff.

## Journey 1: Python generation API

Public call:

```python
config = GeneratorConfig(
    seed=20260817,
    policy_count=100,
    run_namespace="local-demo",
)
histories = generate_policy_histories(config)
```

Call chain:

```text
generate_policy_histories(config)
    |
    +-- use the exact caller-provided GeneratorConfig
    |       +-- __post_init__ validates seed, namespace, count, and UTC start
    |       +-- canonical_configuration includes every generation input and version
    |       +-- SHA-256 config digest produces the deterministic run identity
    |
    +-- random.Random(config.seed)
    |       +-- isolated seeded pseudorandom state
    |
    +-- build and deterministically shuffle scenario assignments
    |
    +-- _generate_history(...) once per policy
            |
            +-- derive namespaced policy ID and fictional issuance values
            +-- nested add_event(...)
            |       +-- derive event ID from run identity and stable counters
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
            +-- parse --seed, --policy-count, --run-namespace,
                --simulation-start, --legacy-v1, and --output
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
- Configuration canonicalization version.
- Seed.
- Run namespace.
- Policy count.
- Simulation start.
- SHA-256 configuration digest and digest algorithm.
- Deterministic run identity.
- Compatibility mode.

The explicit `--legacy-v1` CLI path and the separately named
`generate_legacy_policy_histories` and `legacy_generation_provenance` APIs reproduce
historical generator `0.1.0` bytes. They do not claim namespaced identity and must
not be used for new corpora.

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
    +-- generate_legacy_policy_histories(seed=20260817, policy_count=100)
    +-- legacy_generation_provenance(...)
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
    +-- generate_legacy_policy_histories(seed=20260817, policy_count=100)
    +-- legacy_generation_provenance(...)
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
| Feature guard | Unapproved, prohibited, nested, or simulator-only model-visible content | `ValueError` with offending path |
| Observation collection guard | Duplicate observation, policy/cutoff, or outcome episode | `ValueError` with record context |
| Feature extraction | Missing, extra, prohibited, null, wrongly typed, or negative source value | `ValueError` with feature context |
| Preprocessing fit/apply | Unsupported version or disposition, partition membership drift, or inconsistent fitted state | `ValueError` before matrix use |
| Feature artifact verification | Missing or stale dictionary or preprocessing manifest | Diagnostic and nonzero exit |
| Feature diagnostics | Partition, membership, feature-order, configuration, or disposition drift | `ValueError` before evidence publication |
| Diagnostic artifact verification | Missing, stale, unsafe, or nondeterministic manifest or report | Diagnostic and nonzero exit |

The simulator does not silently repair, reorder in place, or infer missing lifecycle facts.

## Public API map

The package exports these current simulator-facing functions and values:

| Public name | Responsibility |
| --- | --- |
| `GeneratorConfig` | Validate explicit deterministic generation inputs |
| `generate_policy_histories` | Produce corrected namespaced fictional histories from one exact config |
| `generation_provenance` | Bind corrected provenance to the canonical config and run identity |
| `generate_legacy_policy_histories` | Reproduce immutable generator `0.1.0` histories |
| `legacy_generation_provenance` | Report truthful generator `0.1.0` reproduction inputs |
| `validate_policy_history` | Validate cross-event history invariants |
| `reconstruct_policy_state` | Derive effective-time state at an inclusive cutoff |
| `PolicyState` | Hold immutable reconstructed state and audit metadata |
| `histories_to_jsonl` | Serialize events to stable JSON Lines |
| `build_observation` | Construct one dual-time-visible observation and separate 90-day label |
| `build_first_billing_observations` | Construct deterministic first-billing observations and validate collection integrity |
| `validate_feature_payload` | Enforce the versioned recursive model-visible feature boundary |
| `validate_observation_records` | Enforce feature separation and observation/episode uniqueness |
| `find_exact_deterministic_proxies` | Report exact single-field target mappings for review |
| `feature_dictionary` | Describe every approved source field and its Phase 2.04 disposition |
| `extract_feature_row` | Validate and extract stateless model-visible values with sidecars |
| `fit_preprocessor` | Fit immutable numeric and categorical state from the frozen train partition |
| `transform_partition` | Apply frozen state to an exact modeling partition without mutation |
| `build_feature_pipeline` | Fit train and construct frozen train, validation, and test matrices |
| `fit_logistic_baseline` | Fit the single frozen logistic specification on the exact train matrix |
| `predict_positive_probabilities` | Reconstruct scores for permitted train or validation matrices and reject test |
| `evaluate_logistic_baseline` | Calculate predeclared diagnostics and a prediction digest without mutation |
| `coefficient_summary` | Bind coefficients and derived odds ratios to frozen feature names |
| `fit_boosted_model` | Fit the single frozen XGBoost specification on the exact train matrix |
| `predict_boosted_probabilities` | Reconstruct XGBoost from native JSON and score permitted matrices only |
| `evaluate_boosted_model` | Calculate the frozen metrics and prediction digest without mutation |
| `compare_models` | Compare logistic regression and XGBoost on identical train or validation membership |
| `source_feature_groups` | Map frozen transformed outputs to reviewed source-feature groups |
| `training_mutual_information` | Calculate deterministic train-only univariate mutual information |
| `shallow_feature_models` | Fit source-feature decision stumps on train and score validation |
| `identifier_and_cardinality_checks` | Screen identifier tokens, uniqueness, cardinality, and constancy |
| `targeted_permutation_checks` | Perturb flagged validation groups against unchanged frozen models |
| `validate_dispositions` | Require a complete governed decision for every diagnostic flag |

### Phase 2R v2 evaluation path

R2-06 keeps the historical v1 path immutable and adds a separately versioned path:

```text
R2-05 public recurring observations
  -> frozen chronological role/fold membership
  -> dual 90-day embargo and policy/episode isolation checks
  -> exact v2 feature validation
  -> fold-local fit-only preprocessing
  -> role/fold/purpose-bound scoring authorization
  -> diagnostics and governed dispositions
  -> identical-membership logistic/XGBoost comparison
  -> deterministic namespaced manifests and reports
```

The protected oracle sidecar cannot enter this path. Calibration, non-final evaluation, and R2-acceptance roles cannot influence candidate selection. The future final release holdout remains `not_materialized`.

### Phase 2R v2 acceptance-readiness path

R2-07 runs a structural readiness gate before any acceptance model fit or score:

```text
R2-04 protocol + R2-05/R2-06 contracts and artifacts
  -> selected-candidate and driver-registry readiness
  -> matched null/stress stream-identity readiness
  -> published fold-support readiness
  -> five-policy dual-time visibility audit
  -> stop > redesign > proceed decision aggregation
  -> deterministic manifest, report, and decision note
```

The current audit finds behavior values in cutoff features even when their owning behavior event is
ingested after the cutoff and absent from `visible_event_ids`. Protocol `1.0.0` therefore records
`stop` before model fitting. Independent redesign failures also prevent matched null/stress
replications and show that candidate/group registries and structural fold support were not frozen as
required. All planned seeds and folds remain `not_run_protocol_not_executable`; the final holdout
remains `not_materialized`.

### Phase 2R v3 replacement-design path

R2-08 is documentation-only and freezes the replacement boundary before v3 output exists:

```text
R2-07 immutable stop evidence
  -> ADR 0005 replacement decision
  -> event-first immutable v3 events
  -> effective-time AND ingestion-time visible-event filtering
  -> public features reconstructed only from admitted events
  -> stream-set identity separated from artifact/execution identity
  -> matched primitive streams and atomic interventions
  -> frozen coefficients, driver groups, candidates, and selection
  -> executable bootstrap, shuffle, learning, robustness, and decision rules
  -> R2-09 historical implementation -> R2-10 versioned remediation/evaluation -> R2-11 protocol 2.2.0
```

R2-08 generates no corpus, model, prediction, metric, or holdout. Protocol `1.0.0` and the R2-07
decision remain unchanged. The final holdout remains `not_materialized`, and only a later merged
R2-11 `proceed` decision can resume P2-08 and P2-09.

### Phase 2R v4 implementation and qualification path

```text
R2-13 ADR 0007 + substrate 4.0.0
  -> separate v4 configuration, identities, schemas, events, observations, and oracle
  -> billing-frequency scheduled payment opportunities
  -> matched signal/null stream set with atomic signal-scale intervention
  -> readiness over 20 development seeds x 2 scenarios x 3 folds
  -> aggregate-only nine-gate qualification evidence
  -> mechanical redesign (R2-15 remains blocked)
```

R2-14 issue #72 runs only seeds `20271101..20271120`. Exact feature/mechanism
parity, driver support, null behavior, and structural controls pass. Observable
recovery, AP/Brier quality, reference recovery, and the monthly hazard bound fail,
so no candidate freeze or future acceptance is authorized. Seeds
`20271201..20271220` and the final holdout remain `not_materialized`.

R2-14A issue #76 is a documentation-only boundary after that failure. ADR 0008
and contract `1.0.0` freeze seeds `20280101..20280120` for later R2-14B
development diagnostics, preserve `20271201..20271220` as unassigned and
unmaterialized, and predeclare 17 diagnostics plus a non-selective 320-cell
feasibility surface.

R2-14B issue #78 stopped at readiness because contract `1.0.0` did not freeze
mechanical H1-H5 disposition thresholds. PR #79 merged commit `3088c4c`,
recording the governed readiness stop `stop_contract_not_executable` under accepted
ADR 0009 with zero executed units and all hypotheses unresolved.

Phase 2R.14BA issue #80 establishes ADR 0010 and amended contract `1.1.0`, freezing
complete quantitative disposition truth tables before successor increment Phase 2R.14BB
executes the 17 diagnostics on unspent seeds `20280101..20280120`. R2-14C, R2-15, R2-16,
and resumed Phase 2 remain blocked. Reserved acceptance seeds and the final holdout
remain `not_materialized`.

## Test map

| Test module | Process boundary protected |
| --- | --- |
| `test_generator.py` | Counts, scenarios, schema validity, references, ordering, deterministic generation |
| `test_history_validation.py` | Lifecycle transitions, dates, references, terminal rules, shuffled and repeated replay |
| `test_reconstruction.py` | Cutoff semantics, returned state, invalid history inputs, non-mutation |
| `test_serialization.py` | JSON Lines stability and CLI stream/file behavior |
| `test_published_dataset.py` | Published schema/history validity, coverage, manifest integrity, and exact regeneration |
| `test_synthetic_rate_assessment.py` | Metric math, denominators, provenance, sources, decisions, and exact assessment regeneration |
| `test_observations.py` | Dual-time visibility, eligibility, labels, censoring, schema conformance, and deterministic observations |
| `test_leakage_guards.py` | Adversarial future-data mutations, recursive feature separation, simulator proxies, and episode uniqueness |
| `test_temporal_splits.py` | Chronology, embargo, isolation, accounting, and split-manifest regeneration |
| `test_feature_pipeline.py` | Dictionary drift, train-only fitting, held-out invariance, unknown categories, and artifact regeneration |
| `test_logistic_baseline.py` | Train-only fitting, deterministic explicit state, sealed test, compatibility, coefficient alignment, and scoring invariants |
| `test_boosted_comparison.py` | Frozen XGBoost fit, safe JSON reconstruction, identical comparison membership, determinism, artifact safety, and sealed test |
| `test_feature_diagnostics.py` | Train-only diagnostics, source grouping, identifier/cardinality screens, deterministic perturbation, dispositions, artifact safety, and sealed test |
| `test_v2_evaluation.py` | v2 folds, both embargoes, role/policy/episode isolation, fit-only preprocessing, unknown categories, authorization mutations, diagnostics, lineage, explicit-state reload, and final-holdout absence |
| `test_v2_acceptance.py` | R2-07 readiness rules, matched-stream failures, dual-time leakage detection, decision precedence, seed/fold accounting, artifact lineage, payload safety, and final-holdout absence |
| `test_v4_config.py` | v4 registry versions, event-support contract, matched-stream identity, and scheduled-opportunity domain |
| `test_v4_corpus.py` | separate v4 types, scheduled cadence, exact reconstruction, frozen hazards, oracle, and holdout absence |
| `test_v4_qualification.py` | development/future domain separation, complete inventory, readiness, and nine frozen gates |
| `test_v5_diagnostic_contract.py` | R2-14A seed-domain separation, inventory completeness, frozen feasibility surface, and holdout boundary |
| `test_v5_diagnostics.py` | R2-14B readiness rules, inventory completeness, domain disjointness, 320-cell grid exactness, suppression, and artifact reproduction |
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
- Probability calibration, threshold selection, or explanations.
- Storage, services, messaging, or cloud execution.

Add these to the journey only when their contracts and implementation are introduced.
