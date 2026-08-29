# Phase 2R.05 v2 Corpus Implementation Contract

## Status

Implementation version `1.0.0` implements the R2-04 simulator and observation contracts `2.0.0`, label policy `2.0.0`, protected oracle sidecar `1.0.0`, and acceptance protocol reference `1.0.0`. Issue #45 closed when PR #46 merged as `25c370d` on 2026-08-29. Hosted CI passed, R2-06 is unblocked, and the final holdout remains `not_materialized`.

## Runtime boundary

`V2CorpusConfig` is the sole authority for a v2 corpus. Its canonical representation binds seed, namespace, corpus dimensions, dates, cadence, censoring, missingness, signal and drift modes, frozen contract versions, role proportions, random-domain registry, and the `not_materialized` final-holdout status. V2 generation is separate from the immutable v1 compatibility paths.

`generate_v2_corpus` returns separately typed histories, public recurring observations, protected oracle records, and provenance. Policies belong to one deterministic outcome-independent role family. Observations use non-overlapping 90-day episodes after 30-day seasoning, and a terminal event ends future eligibility.

## Statistical mechanism

The implementation uses the approved monthly competing-risk softmax with observable static, recent-payment, rolling-history, and interaction drivers; one seeded policy frailty draw; and stable, moderate-drift, stress-drift, and null-signal modes. Observable state freezes at episode opening. Exact three-month cause-specific and union cumulative incidence is recorded. `oracle_observable` marginalizes frailty using versioned 32-node Gauss-Hermite quadrature.

## Point-in-time and protected data

Visible event identity requires both `effective_at <= as_of` and `ingested_at <= as_of`. Bounded delay, MCAR and cutoff-visible conditional missingness, immutable referencing corrections, grace entry/recovery, event-driven and administrative censoring, and post-fit category arrival are independently seeded.

The oracle sidecar is not embedded in public observations. The frozen v2 feature validator rejects extra fields and direct or nested oracle, frailty, draw, scenario, role, outcome, identifier, and event-ID concepts.

## Artifacts

`scripts/build_v2_modeling_corpus.py` regenerates the default 3,600-policy corpus and verifies `docs/experiments/phase-02r-05-v2-corpus-manifest.json`. The manifest records structural counts and independent SHA-256 digests for histories, public observations, and the protected sidecar. Large raw rows and protected oracle values are deliberately regenerated rather than committed.

Computed floating-point values use canonical finite JSON serialization rounded to 10 decimal places before artifact hashing. Runtime calculations retain full precision. This normalization prevents platform-specific NumPy/libm differences from changing provenance bytes without weakening the numeric reference tests.

The data card is `datasets/v2/DATA_CARD.md`. No temporal split, feature matrix, fitted model, metric report, calibration, explanation, R2-07 decision, or final holdout is produced by R2-05.

## Reproduction

```bash
PATH="$PWD/.venv/bin:$PATH" make check
```
