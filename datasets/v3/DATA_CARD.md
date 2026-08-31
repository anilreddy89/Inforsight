# Inforsight v3 Synthetic Modeling Corpus Data Card

## Status

This is a deterministic, fictional, non-final implementation corpus for Phase 2R.09 and issue #56. Large histories, public observations, and protected row-level oracle sidecars are regenerated rather than committed. The final release holdout is `not_materialized`.

## Design

The default corpus implements substrate contract `3.0.0`: 14,400 fictional policies, 24 monthly issuance cohorts, four billing frequencies, pre-outcome role allocation, 30-day seasoning, non-overlapping 90-day episodes, immutable events, and dual effective/ingestion-time reconstruction. Every public value has visible-event lineage or is explicitly cutoff-derived.

Randomness follows registry `1.0.0`. Stream-set identity is scenario invariant; artifact identity includes the complete scenario; execution identity additionally binds source, dependencies, and command. Atomic interventions reuse unaffected primitive draws.

## Protected data

Latent frailty, outcome uniforms, conditional oracle probabilities, and observable oracle probabilities are stored only in regenerated protected sidecars. They are prohibited from public feature discovery, preprocessing, fitting, selection, and ordinary scoring.

## Reproduction

```bash
python3 scripts/build_v3_modeling_corpus.py --write
python3 scripts/build_v3_modeling_corpus.py --check
```

The committed manifest is `docs/experiments/phase-02r-09-v3-corpus-manifest.json`.

## Intended use and limitations

The corpus supports verification that Inforsight can recover a predeclared fictional mechanism while preserving point-in-time, lineage, identity, and matched-stream invariants. It does not represent an insurer or population and supports no prevalence, actuarial, causal, fairness, operational, customer-impact, production-readiness, or real-world prediction claim.

R2-09 produces no folds, feature matrices, fitted models, predictions, acceptance metrics, calibration, explanations, or final holdout. R2-10 is the only downstream increment enabled after merge.
