# Simulator

The simulator generates small, seeded, fictional policy-event histories that conform to policy-event contract version `1.0.0`. It is a clean-room engineering fixture, not a model of a real insurer or population.

R2-05 also provides a separately versioned v2 statistical-corpus path through `V2CorpusConfig` and `generate_v2_corpus`. V2 implements 24 issuance cohorts, recurring non-overlapping observations, approved behavioral variation, competing lapse and surrender hazards, named drift and missingness modes, and a physically separate protected oracle sidecar. It does not alter v1 reproduction.

Verify the merged R2-05 corpus evidence with:

```bash
python3 scripts/build_v2_modeling_corpus.py --check
```

The v2 final release holdout remains `not_materialized`. R2-05 does not create splits, fit models, publish performance evidence, calibrate probabilities, or generate explanations.

R2-09 adds a separately namespaced v3 path through `V3CorpusConfig` and `generate_v3_corpus`. It implements immutable event-first generation, dual effective/ingestion-time reconstruction, visible-event digests, per-feature lineage, stream-set/artifact identities, random-stream registry `1.0.0`, atomic scenarios, exact competing hazards, and protected conditional/observable oracle sidecars.

Verify the deterministic non-final evidence with:

```bash
python3 scripts/build_v3_modeling_corpus.py --check
```

R2-10 adds a separate v3.1 arrears-remediation namespace and the governed v3 evaluation pipeline. Verify its immutable historical failure and authoritative aggregate `3.2.0` evidence with:

```bash
python3 scripts/check_v3_evaluation_support.py --check
python3 scripts/build_v3_evaluation_pipeline.py --check
```

The pipeline regenerates public observations and matrices at runtime but commits only aggregate evidence and portable digests. It selects XGBoost from the selection role and creates no acceptance prediction, acceptance metric, oracle access, executable fitted object, or final holdout. R2-10 merged through PR #62; R2-11 protocol `2.2.0` is the next authorized increment.

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
from inforsight_simulator import GeneratorConfig, generate_policy_histories

config = GeneratorConfig(seed=20260817, run_namespace="local-demo")
histories = generate_policy_histories(config)
assert len(histories) == 100
```

`policy_count` defaults to 100 and accepts any positive integer. `run_namespace` is required, validated, and included in deterministic run identity so separately named corpora do not reuse generator-owned IDs. Each inner list is one ordered policy history, and every history begins with one `policy.issued` event.

## Policy-history validation

The simulator provides one public ingress for raw histories. It validates every event against the versioned envelope and selected payload JSON Schema before checking relationships across events:

```python
from inforsight_simulator import (
    GeneratorConfig,
    generate_policy_histories,
    validate_policy_history,
)

config = GeneratorConfig(
    seed=20260817,
    policy_count=1,
    run_namespace="validation-demo",
)
history = generate_policy_histories(config)[0]
validate_policy_history(history)  # Returns None; raises ValueError when invalid.
```

`validate_policy_history` is the composite boundary; callers do not need to invoke a schema validator separately. Invalid versions, identifiers, currencies, payload shapes, timestamps, and unexpected properties fail before semantic replay. Validation then sorts a private representation by `(effective_at, occurred_at, event_id)`. Caller-provided order is not authoritative, and the supplied list and event dictionaries are not mutated.

The package declares `jsonschema` and `referencing` as runtime dependencies. Contract resources are resolved from the repository distribution and never fetched over the network.

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
    GeneratorConfig,
    generate_policy_histories,
    reconstruct_policy_state,
)

config = GeneratorConfig(
    seed=20260817,
    policy_count=1,
    run_namespace="reconstruction-demo",
)
history = generate_policy_histories(config)[0]
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
  --policy-count 100 \
  --run-namespace local-demo
```

Write to a caller-selected path:

```bash
PYTHONPATH=simulator/src python3 -m inforsight_simulator \
  --seed 20260817 \
  --policy-count 100 \
  --run-namespace local-demo \
  --output /tmp/inforsight-policy-events.jsonl
```

The CLI refuses to overwrite an existing file. Event JSON is written to standard output or the requested file; generation provenance is written separately to standard error so it cannot corrupt the JSON Lines stream.

Historical generator `0.1.0` output is reproduced only through the explicit compatibility option:

```bash
PYTHONPATH=simulator/src python3 -m inforsight_simulator \
  --seed 20260817 \
  --policy-count 100 \
  --legacy-v1
```

`--legacy-v1` cannot be combined with a namespace or a changed simulation start. New datasets must use corrected namespaced generation.

## Determinism guarantee

For corrected generator `0.2.0`, the exact same seed, policy count, UTC simulation start, and run namespace produce structurally identical histories and byte-identical JSON Lines. Provenance contains a canonical configuration digest and deterministic run identity. Generation uses:

- A dedicated seeded pseudorandom-number generator.
- An explicit UTC simulation start date.
- Run-identity and counter-derived synthetic identifiers.
- Explicit history and event ordering.
- Stable compact JSON serialization with sorted keys.

It does not use wall-clock time, global random state, random UUIDs, Python hash values, or filesystem ordering. Provenance reports every generation input, generator version, event-schema version, canonicalization version, configuration digest, and run identity.

Generator-version changes may intentionally alter output. Consumers that require exact replay must retain the complete provenance record and reuse the same namespace. Historical v1 artifacts use separately named legacy APIs and remain byte reproducible; the compatibility path must not be used for new corpora.

## Fictional scenario mix

The default 100-policy corpus contains exactly 25 histories in each bounded scenario:

- Active and payment-current.
- Entered grace period and recovered.
- Lapsed after fictional nonpayment.
- Surrendered after a structured fictional inquiry.

These equal weights are transparent test inputs. They are not estimates of insurance-industry prevalence and must not be used to make performance or business claims.

## Dataset boundary

The 100-policy run is the deterministic development and acceptance corpus. This package can generate temporary larger runs, but large generated datasets should not be committed.

The repository publishes an eight-policy, 49-event [fictional sample](../datasets/sample-policy-events.jsonl), its machine-readable [manifest](../datasets/sample-manifest.json), and a detailed [data card](../datasets/DATA_CARD.md). The publication script generates the canonical 100-policy corpus with seed `20260817` and selects the first two complete histories from each scenario in generator order. This balanced sample is intended for inspection, contract validation, and replay demonstrations—not statistical inference or model evaluation.

Verify that the committed artifacts reproduce exactly:

```bash
python3 scripts/build_sample_dataset.py --check
```

## Aggregate synthetic-rate assessment

The repository publishes a deterministic [assessment report](../docs/experiments/phase-01-07-synthetic-rate-assessment.md) and [machine-readable result](../docs/experiments/phase-01-07-synthetic-rate-assessment.json) for the canonical seed-`20260817` 100-policy corpus. It measures the current scenario, outcome, grace, payment, contact, product, billing, premium, and timing behavior and documents comparison limits against cited public references.

Verify the derived result without rewriting it:

```bash
python3 scripts/assess_synthetic_rates.py --check
```

The assessment retains equal scenario weights as deterministic coverage inputs. Current policy proportions cover one generated scenario path, not policy-year exposure, so they are not annualized rates. Annual lapse or surrender calibration remains deferred until the simulator supports compatible duration, exposure, and product definitions. The assessment does not change generator version `0.1.0`, schema version `1.0.0`, or published sample bytes.

## Phase 2 observation construction

The simulator now builds versioned observation records under the [Phase 2.01 modeling contract](../docs/modeling/phase-02-01-modeling-contract.md). Version `1.0.0` creates one record per policy at the ingestion time of its first billing-due event:

```python
from datetime import timedelta
from inforsight_simulator import (
    GeneratorConfig,
    build_first_billing_observations,
    first_billing_observation_time,
    generate_policy_histories,
)

config = GeneratorConfig(seed=20260817, run_namespace="observation-demo")
histories = generate_policy_histories(config)
watermark = max(
    first_billing_observation_time(history) + timedelta(days=90)
    for history in histories
)
records = build_first_billing_observations(
    histories,
    follow_up_through=watermark,
)
```

Feature visibility requires both `effective_at <= as_of` and `ingested_at <= as_of`. Only active policies are eligible. The label horizon is `(as_of, as_of + 90 days]`; lapse and surrender map to a binary adverse-termination label while their distinct outcome types remain in audit provenance. Negative labels require complete follow-up through an explicit watermark. Incomplete follow-up is right-censored.

Identity, features, labels, label provenance, and visible event identifiers are structurally separated. Scenario identifiers, terminal outcomes, final status, policy IDs, event IDs, and label fields are not part of the feature surface.

Phase 2.02 adds a versioned, fail-closed [leakage and simulator-shortcut guard](../docs/modeling/phase-02-02-leakage-and-shortcut-guards.md). It recursively validates the explicit feature allowlist, normalizes key aliases, rejects direct simulator construction markers, and enforces observation and outcome-episode uniqueness. A separate review diagnostic reports exact deterministic feature-to-label mappings without automatically treating correlation as leakage. The canonical seed-`20260817` feature surface has no exact deterministic proxy under this diagnostic.

Verify the canonical data-sufficiency evidence without writing files:

```bash
python3 scripts/build_observations.py --check
```

The canonical 100-policy corpus produces 100 eligible first-billing observations, 50 positive labels, and 50 negative labels. That balance exactly reflects the engineered scenario fixture and is not a prevalence or model-performance estimate. The gate is `proceed_with_limitations`; model training remains separate work.

## Phase 2 temporal splits

Phase 2.03 assigns the guarded observations to deterministic policy-aware chronological partitions under the [temporal split contract](../docs/modeling/phase-02-03-temporal-split-contract.md). The canonical half-open UTC windows place observations before April 2024 in train, April through June in the embargo, July through September in validation, October through November in a calendar gap, and December 2024 onward in test.

The split validator requires both modeling classes in every modeling partition, prevents policy or outcome-episode ownership across partitions, accounts for every source observation, and enforces strict horizon separation:

```text
max(train.horizon_end) < min(validation.as_of)
max(validation.horizon_end) < min(test.as_of)
```

Equality is treated as overlap. No preprocessing, resampling, fitting, calibration, or threshold selection occurs during splitting.

Regenerate or verify the versioned manifest with:

```bash
python3 scripts/build_temporal_splits.py --write
python3 scripts/build_temporal_splits.py --check
```

The canonical split contains 26 train, 22 embargoed, 27 validation, and 25 test observations. Observation timing is strongly associated with billing frequency: train is monthly-only, the embargo is quarterly-only, validation is semiannual-only, and test is annual-only. This is a pipeline-engineering fixture, not evidence of temporal generalization or real-world model performance.

## Phase 2 feature pipeline

Phase 2.04 converts the guarded, frozen modeling partitions into deterministic numeric matrices under the [feature-pipeline contract](../docs/modeling/phase-02-04-feature-pipeline-contract.md). The machine-readable [feature dictionary](../docs/modeling/phase-02-04-feature-dictionary.json) covers all 12 approved observation fields and records each type, provenance, missingness rule, transformation, and keep-or-exclude decision.

Numeric z-score statistics and categorical vocabularies are fit from the 26 train observations only. Validation and test reuse the immutable fitted state. Every categorical block includes a predeclared `__unknown__` column, so semiannual validation and annual test billing frequencies do not expand or refit the monthly-only training schema. Missing required values fail closed. Constant `current_status` and `currency` fields are explicitly excluded.

Identity and targets remain sidecars outside model values. The committed manifest contains fitted metadata, output names, shapes, and digests but not raw or transformed rows:

```bash
python3 scripts/build_feature_pipeline.py --write
python3 scripts/build_feature_pipeline.py --check
make feature-pipeline-check
```

This remains a pipeline-engineering fixture under `LIM-002-001`. Phase 2.04 performs no model fitting, resampling, calibration, threshold selection, or test-guided choice.

## Phase 2 logistic baseline

Phase 2.05 fits one frozen [logistic-regression baseline](../docs/modeling/phase-02-05-logistic-baseline-contract.md) on the exact Phase 2.04 train matrix. The versioned specification pins scikit-learn `1.7.2` and uses its `liblinear` solver, L2 regularization with `C=1.0`, seed `20260817`, no class weighting, tolerance `1e-8`, and a 1,000-iteration convergence ceiling. Published floating-point evidence uses an explicit 10-decimal normalization boundary while runtime scoring retains full precision.

R2-03 experiment scoring requires `authorize_feature_pipeline(pipeline)` and passes the resulting exact train or validation `ScoringAuthorization` to logistic, boosted, comparison, and diagnostic APIs. The authorization binds membership, order, feature contract, labeled-matrix digest, fitted-preprocessor identity, and approved purpose; changing `ModelMatrix.partition` cannot grant access. `InferenceMatrix` and the `predict_logistic_inference` or `predict_boosted_inference` APIs are the separate unlabeled inference path and do not accept experiment partitions, targets, or compute metrics. These are local integrity controls, not security against someone who can modify repository code or files.

Fitted state is explicit JSON-compatible metadata: intercept, coefficients, feature order, training IDs and digest, dependency and contract versions, and convergence evidence. No executable pickle is committed. Train and validation probabilities can be reconstructed directly from the explicit state; the model API rejects canonical test scoring.

Regenerate or verify the manifest and report with:

```bash
python3 scripts/train_logistic_baseline.py --write
python3 scripts/train_logistic_baseline.py --check
make logistic-baseline-check
```

The published diagnostics are pipeline-engineering evidence only. `LIM-002-001` remains claim-blocking; no calibration, threshold selection, boosted-model comparison, temporal-generalization claim, or action authority is introduced.

## Phase 2 boosted-model comparison

Phase 2.06 fits one predeclared [XGBoost candidate](../docs/modeling/phase-02-06-boosted-model-comparison-contract.md) on the exact Phase 2.04 train matrix and compares it with the unchanged Phase 2.05 logistic benchmark on identical train and validation observations. Issue #26 freezes XGBoost `3.3.0`, 25 depth-2 exact-method trees, learning rate `0.1`, minimum child weight `2.0`, unit sampling, L2 regularization `1.0`, seed `20260817`, one worker, and no early stopping.

The candidate is reconstructed from XGBoost-native JSON model data with explicit provenance and digests; pickle and joblib are not used. Both models share the Phase 2.05 metric definitions and use unrounded probabilities. Candidate and comparison APIs reject canonical test scoring.

```bash
python3 scripts/train_boosted_comparison.py --write
python3 scripts/train_boosted_comparison.py --check
make boosted-comparison-check
```

The comparison is `pipeline_engineering_only`. With 26 monthly training observations and semiannual-only validation, it cannot establish production superiority, temporal generalization, calibration, or an operational threshold.

## Tests

From the repository root, with the contract test requirements installed:

```bash
python3 -m unittest discover -s simulator/tests -v
make check
```

The tests validate the complete default corpus against the event contracts and history validator. They check count, scenario coverage, identifier uniqueness, lifecycle transitions, terminal pairs, impossible cross-event dates, payment-to-billing integrity, deterministic serialization and replay, CLI behavior, point-in-time cutoff boundaries, invalid inputs, non-mutation, fictional-data boundaries, exact regeneration of the published sample and manifest, deterministic synthetic-rate calculations, dual-time observation visibility, eligibility, horizon boundaries, censoring, feature/label separation, observation-schema validation, and sufficiency-artifact regeneration.

Run the Phase 2.02 guard suite alone with:

```bash
make leakage-check
```

Run the Phase 2.03 split suite and manifest verification with:

```bash
python3 -m unittest discover -s simulator/tests -p 'test_temporal_splits.py' -v
make temporal-split-check
```

Run the Phase 2.04 feature-pipeline suite and artifact verification with:

```bash
make feature-pipeline-check
```

Run the Phase 2.05 logistic-baseline suite and sealed-test artifact verification with:

```bash
make logistic-baseline-check
```

Run the Phase 2.06 boosted-comparison suite and sealed-test artifact verification with:

```bash
make boosted-comparison-check
```

For the end-to-end implementation journey and current function-call map, see [`docs/simulator-process-flow.md`](../docs/simulator-process-flow.md).
