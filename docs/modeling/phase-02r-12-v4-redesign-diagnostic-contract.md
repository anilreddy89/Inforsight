# Phase 2R.12 v4 Redesign Diagnostic Authorization Contract

## 1. Authority and status

| Field | Value |
| --- | --- |
| Phase | R2-12 |
| Issue | [#66](https://github.com/anilreddy89/Inforsight/issues/66) |
| Contract version | `1.0.0` |
| Status | Proposed; result-producing execution is prohibited until merge |
| Governing decision | ADR 0006 |
| Trigger evidence | R2-11 decision `redesign`, protocol `2.2.0` |
| Final holdout | `not_materialized` |

This contract authorizes R2-13 to diagnose the v3 signal-recovery failure on a
separate development block. It does not authorize v4 implementation, candidate
selection, replacement acceptance, calibration, thresholds, explanations, final
evaluation, or holdout creation.

## 2. Frozen information domains

| Domain | Seeds | Permitted use |
| --- | --- | --- |
| `v3_spent_acceptance` | `20261001..20261020` | Cite committed R2-11 aggregates only |
| `v4_development_diagnostic` | `20271101..20271120` | R2-13 diagnostic inventory only |
| `v4_future_acceptance` | `20271201..20271220` | One later acceptance execution after v4 freeze |

Ranges are inclusive integer sequences in ascending order. Each contains exactly
20 seeds and their pairwise intersections MUST be empty. A seed MUST NOT be
retried, replaced, omitted, or moved between domains because of output.

R2-12 MUST NOT generate either v4 domain. R2-13 MUST NOT generate, inspect, derive
membership for, or score `v4_future_acceptance`. Final-holdout seeds and identity
remain undefined and MUST NOT be inferred from these domains.

## 3. Immutable inputs

- R2-11 manifest, report, decision, execution contract, source, and tests.
- V3 simulator `3.1.0`, evaluation `3.2.0`, and protocol `2.2.0` evidence.
- The event-first dual-time visibility rule and matched-stream ownership.
- The 90-day union estimand, three rolling-origin folds, and policy ownership.
- The 17-feature registry, five driver groups, coefficient registry `1.0.0`,
  logistic specification, XGBoost specification, and selected XGBoost identity.

R2-13 may diagnose these inputs but MUST NOT overwrite or amend them. Any proposed
change belongs to a later versioned ADR and contract.

## 4. Hypothesis and diagnostic registry

Every executed diagnostic MUST have a registry entry below. Unregistered
exploratory output is unauthorized.

| ID | Hypothesis | Required diagnostics |
| --- | --- | --- |
| `H1_ORACLE_SEPARABILITY` | Observable signal is weak relative to baseline, frailty, or outcome noise | Observable- and conditional-oracle ROC AUC, AP lift, Brier skill, calibration, ordering, and aggregate signal-variance decomposition by seed/fold |
| `H2_DRIVER_SUPPORT` | Designed terms lack realized support | Missing/finite/unique/prevalence/quantile/clipping summaries by term, group, seed, fold, role, period, and class |
| `H3_TRANSFORM_PARITY` | Feature and mechanism transforms differ | Exact cutoff-value parity, mismatch count, maximum absolute error, and visibility/category/missingness/interaction/default mutation tests |
| `H4_EPISODE_DILUTION` | Episode construction or weights dilute policy signal | Observation/policy counts, episodes per policy, prevalence, weight concentration, and registered policy-versus-episode sensitivities |
| `H5_CANDIDATE_LEARNING` | Candidates fail on learnable observable signal | Contract-derived reference score/model and identical-membership logistic/XGBoost recovery, convergence, feature-use, and prediction-variance summaries |
| `H6_TEMPORAL_STABILITY` | Recovery or support is unstable by rolling origin | Fold oracle/reference/candidate metrics, time-indexed support/incidence, fold spread, and worst-fold summaries |

## 5. Frozen diagnostic execution

R2-13 MUST use all 20 development seeds, matched signal/null streams, and all three
governed folds unless readiness fails. It MUST record every planned unit and every
failure. Missing or invalid work remains in the denominator.

Metrics inherit their protocol `2.2.0` definitions. Numeric comparisons use full
runtime precision; committed floats use the existing canonical normalization.
Policy remains the resampling and grouping unit. Diagnostic sensitivities MUST NOT
be interpreted as a change to the estimand.

The diagnostic reference score is the exact observable log-risk ordering derived
from the frozen public cutoff terms. The correctly specified reference model uses
only those registered public terms and the frozen v3 functional form. Neither is
a release candidate. R2-13 MUST fit logistic and XGBoost with their frozen
specifications on identical authorized development memberships.

R2-13 MUST NOT tune a hyperparameter, coefficient, feature, fold, threshold,
tolerance, metric, aggregation, or hypothesis rule. An ambiguity stops execution
and returns to a reviewed contract amendment before output inspection.

## 6. Protected-intermediate boundary

Oracle sidecars, frailty, outcome uniforms, mechanism terms, matrices, row-level
targets, row-level predictions, fitted objects, bootstrap samples, and sensitivity
memberships are temporary protected intermediates.

Each diagnostic family requires purpose-bound authorization containing the domain,
seed, scenario, fold, ordered membership digest, input artifact digests, feature or
mechanism identity, model/reference identity where applicable, target digest, and
contract version. Cross-purpose reuse, substitution, reordering, or missing digest
MUST fail before computation.

Oracle, frailty, outcomes, and mechanism-only values MUST NOT enter ordinary model
features, preprocessing, candidate fitting, or candidate scoring. Committed output
MUST be aggregate and MUST suppress any cell with fewer than 10 unique policies.
Temporary intermediates MUST be removed after their aggregate digests are bound to
the manifest.

## 7. R2-13 readiness

Before result-producing access, R2-13 MUST prove:

- exact contract, code, dependency, command, and upstream artifact identities;
- exact 20-seed development inventory and zero overlap with spent and future
  acceptance domains;
- zero access to future acceptance or final-holdout identity and membership;
- dual-time lineage, chronology, embargo, role/policy/episode isolation, canonical
  order, finite matrices, and protected-concept exclusion;
- matched signal/null primitive streams outside the frozen intervention allowlist;
- complete diagnostic and hypothesis registries; and
- absence of preexisting development metrics or predictions.

Leakage, future-acceptance access, holdout access, oracle contamination, evidence
manipulation, or domain substitution yields `stop`. Other incomplete readiness
yields `redesign_required` and produces no diagnostic result.

## 8. Aggregate evidence schema

R2-13 MUST publish:

```text
docs/experiments/phase-02r-13-v4-redesign-diagnostic-manifest.json
docs/experiments/phase-02r-13-v4-redesign-diagnostic-report.md
docs/experiments/phase-02r-13-v4-redesign-hypothesis-disposition.md
```

Each manifest diagnostic record contains:

```text
diagnostic_id
hypothesis_id
domain
seed_scope
fold_scope
inputs
metric_or_check
aggregation
observed
status
failure_classification
evidence_digests
```

The manifest records the complete planned/executed inventory, failures, upstream
digests, authorization identities, aggregate evidence, hypothesis dispositions,
and `final_holdout: not_materialized`. Reports are deterministic projections of
the manifest. No protected intermediate is committed.

## 9. Hypothesis disposition

Each hypothesis receives exactly one disposition:

- `supported`: every required diagnostic exists and the evidence supports the
  stated failure mechanism under its predeclared interpretation;
- `rejected`: every required diagnostic exists and contradicts that mechanism;
- `unresolved`: evidence is mixed, incomplete, invalid, or insufficient.

R2-13 MUST NOT convert an unresolved result into a design choice. It may propose
only the response paired below:

| Finding | Permitted proposal |
| --- | --- |
| H1 supported | Versioned coefficient, frailty, incidence, or event-prevalence redesign |
| H2 supported | Versioned event-generation or eligibility redesign |
| H3 supported | Feature/observation contract repair plus exact parity tests |
| H4 supported | Reviewed estimand, sampling, or weighting amendment |
| H5 supported while H1 is rejected | Candidate or selection-rule redesign |
| H6 supported | Drift or fold redesign without outcome-conditioned membership |
| Mixed or unresolved | Another bounded reviewed diagnostic version; no guessed substrate change |

A proposal does not authorize implementation. R2-13 MUST freeze a superseding ADR,
v4 substrate contract, and protocol before R2-14 starts.

## 10. Compatibility and prohibited work

R2-12 changes no stochastic equation, coefficient, corpus, event, observation,
feature, preprocessing state, candidate, selection, fold, estimand, resampling,
metric, threshold, tolerance, or decision rule. It produces no corpus, fit,
prediction, bootstrap, oracle result, or performance metric.

P2-08/P2-09 remain paused; P2-10 through P2-12 remain blocked. The final holdout
remains `not_materialized`.

## 11. Verification

`python3 scripts/check_r2_12_diagnostic_contract.py` MUST verify required documents,
issue/version/status tokens, exact seed blocks and disjointness, six hypothesis
identities, artifact paths, prohibited-result language, R2-11 merge identity, and
final-holdout status. The check reads text only and MUST NOT import or call any
simulator, evaluation, feature, modeling, or acceptance runtime.
