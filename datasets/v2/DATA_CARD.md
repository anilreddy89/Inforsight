# Inforsight v2 Synthetic Modeling Corpus Data Card

## Status and intended use

This is the specification card for the deterministic R2-05 non-final synthetic corpus. The corpus exists only to test recovery of a known fictional mechanism, recurring point-in-time observation construction, leakage resistance, and governed pipeline behavior. It is not evidence about any insurer, policyholder population, prevalence, actuarial assumption, causal effect, fairness property, operational outcome, or production performance.

The final release holdout is `not_materialized`. Its seed has not been chosen and it must not be generated, inspected, transformed, or scored through R2-07.

## Construction

- Simulator contract: `2.0.0`
- Observation contract: `2.0.0`
- Label policy: `2.0.0`
- Oracle sidecar: `1.0.0`
- Acceptance protocol: `1.0.0`
- Default seed: `20260901`
- Default namespace: `r2-05-default`
- Policies: 3,600 across 24 monthly issuance cohorts
- Observation cadence and horizon: non-overlapping 90-day episodes after 30-day seasoning
- Outcomes: seeded competing lapse and surrender hazards
- Data quality: MCAR and conditional missingness, bounded ingestion delay, immutable event history, category arrival, censoring, and named drift modes

Policies are assigned before outcome generation to mutually exclusive fit, selection, calibration, non-final-evaluation, and R2-acceptance role families. Role, identity, latent frailty, random draws, scenario values, outcomes, and oracle probabilities are not model features.

## Point-in-time and oracle boundaries

Public observations use facts only when both `effective_at <= as_of` and `ingested_at <= as_of`. Each outcome episode owns `(as_of, as_of + 90 days]`; episodes for one policy never overlap.

Conditional and observable oracle probabilities are generated into a separate protected sidecar. The sidecar is used only for verification and the later predeclared R2-07 acceptance gate. It must never enter feature discovery, preprocessing, fitting, or model selection.

## Reproduction

```bash
python3 scripts/build_v2_modeling_corpus.py --check
```

The committed manifest records deterministic counts and SHA-256 digests. Raw histories, observations, and protected oracle rows regenerate in memory and are intentionally not committed as source artifacts.

## Limitations

All entities and behavior are fictional. R2-05 implements the approved mechanism but does not close `LIM-002-001` or `LIM-002-002`; R2-06 and R2-07 own the required evaluation evidence. `LIM-002-003` remains open until a later authorized one-shot final-holdout workflow is proven.
