# Phase 2.02 Leakage and Simulator-Shortcut Guards

## Status

| Field | Value |
| --- | --- |
| Guard version | `1.0.0` |
| Observation contract | `1.0.0` |
| Canonical generator seed | `20260817` |
| Issue | [#18](https://github.com/anilreddy89/Inforsight/issues/18) |
| Pull request | [#19](https://github.com/anilreddy89/Inforsight/pull/19) |
| Status | Completed on 2026-08-19 |
| Merge commit | `5e2987b` |
| Boundary | Validation only; no feature transformation, splitting, or model training |

## Purpose

The Phase 2.02 guard validates the exact feature payload exposed by the current observation contract and collection-level episode invariants before later feature-building work begins. It fails closed when model-visible data contains unapproved fields, direct simulator construction metadata, future-information artifacts, labels, outcome provenance, identity, or duplicate episodes.

This is synthetic engineering evidence. It does not establish real-world predictive validity, fairness, prevalence, or business value.

## Field classification

| Class | Current fields | Model-visible |
| --- | --- | --- |
| Approved observation features | Current status, product variant, billing frequency, premium, currency, policy age, and visible event counts | Yes, through the explicit versioned allowlist |
| Identity | Observation ID and policy ID | No |
| Temporal and evaluation metadata | `as_of`, horizon timestamps, follow-up watermark, eligibility metadata | No |
| Label and audit provenance | Label status/value, outcome type, source event and timestamps, censoring reason | No |
| Event audit references | Visible event IDs | No |
| Simulator construction | Scenario, scenario assignment, seed, generator branch, and generator order | No |
| Contract provenance | Observation, label, generator, and event-schema versions | No |

The guard normalizes case and separators before checking prohibited concepts. It recursively inspects mappings and sequences so nesting cannot hide a prohibited key or known scenario/terminal marker. The current feature boundary is an explicit root allowlist; adding a feature therefore requires a deliberate reviewed change.

## Temporal invariants

Automated mutation tests prove that feature payloads remain unchanged when:

- A terminal outcome after `as_of` changes.
- An event is effective before but ingested after `as_of`.
- An event is ingested before but effective after `as_of`.

An event satisfying both visibility conditions exactly at `as_of` remains visible, preserving the Phase 2.01 inclusive cutoff contract:

```text
event.effective_at <= as_of
and
event.ingested_at <= as_of
```

Labels and audit metadata may legitimately use later information under the separate label policy. They never become part of the feature payload.

## Dataset and episode invariants

`validate_observation_records` rejects:

- Duplicate observation IDs.
- Duplicate `(policy_id, as_of)` observations.
- Reuse of one label-source event by more than one observation episode.
- Any record whose non-null feature payload violates the feature guard.

Checks are deterministic and independent of input order. Observation contract version `1.0.0` creates one observation per policy; recurring or overlapping episodes require a future versioned decision before these rules may change.

## Simulator-shortcut policy

Direct construction artifacts are always prohibited, including scenario names or IDs, assignment order, generator branch, generator seed, final status, terminal outcomes, and identity fields.

`find_exact_deterministic_proxies` is a review diagnostic for observable candidate features. It reports a field when each distinct feature value maps to exactly one target class in the supplied dataset. A report is not automatic proof of leakage: an observable field requires an explicit allow/exclude decision, while direct simulator construction metadata remains prohibited regardless of correlation.

For the canonical seed-`20260817` corpus:

- 100 eligible observation records pass the feature and collection guards.
- 50 labels are positive and 50 are negative because of engineered scenario coverage.
- No current approved feature is an exact deterministic proxy for the binary label under this diagnostic.

This finding is narrow. It does not rule out statistical shortcuts, interactions among fields, or shortcuts in a future expanded corpus or feature set. The diagnostic must be rerun when the allowed feature boundary, generator, observation contract, or corpus changes.

## Verification

Run the focused guard suite:

```bash
python3 -m unittest discover -s simulator/tests -p 'test_leakage_guards.py' -v
```

Run the complete repository checks:

```bash
make check
git diff --check
```

The focused tests cover recursive and normalized-key rejection, scenario and terminal marker values, temporal mutations, cutoff equality, current-feature negative controls, duplicate observations, duplicate outcome ownership, deterministic ordering, and exact-proxy diagnostics.

## Deferred work

- Policy-aware temporal train, validation, and test splits.
- A versioned feature pipeline, flattening contract, transformations, encodings, and missingness policy.
- Multivariate or statistical shortcut analysis during model experiments.
- Model training, calibration, evaluation, explanations, and release artifacts.
