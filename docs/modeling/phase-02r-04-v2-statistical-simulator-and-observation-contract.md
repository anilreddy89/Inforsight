# Phase 2R.04 v2 Statistical Simulator and Observation Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Statistical simulator contract | `2.0.0` |
| Observation contract | `2.0.0` |
| Label policy | `2.0.0` |
| Evaluation protocol | `1.0.0` |
| Status | Approved through issue #42 and PR #43, merge commit `1fc48ad`; no v2 result has been generated |
| ADR | `docs/adr/0004-versioned-v2-statistical-simulator-and-evaluation-design.md` |
| Acceptance protocol | `docs/modeling/phase-02r-04-statistical-acceptance-protocol.md` |

## 1. Intended use and prohibited claims

The v2 corpus MUST test synthetic signal recovery, temporal-evaluation mechanics, leakage resistance, deterministic reproduction, and declared robustness scenarios. It MUST use fictional entities and original clean-room logic.

The corpus MUST NOT be presented as representative of an insurer, a population prevalence estimate, an actuarial study, causal evidence, a fairness assessment, operational readiness, customer impact, or production performance. A successful gate establishes behavior only for the versioned synthetic mechanism.

## 2. Estimand and time boundary

For every eligible observation at UTC time `t`, the primary estimand is:

```text
P(lapse or surrender in (t, t + 90 elapsed days] |
  information with effective_at <= t and ingested_at <= t,
  policy active at t)
```

The start is exclusive and the end is inclusive. Lapse and surrender MUST remain distinct in outcome provenance and combine only for the primary binary estimand. R2-05 MAY retain cause-specific oracle hazards for diagnostics, but R2-06 MUST NOT silently change the primary target to a cause-specific estimand.

An observation is eligible only when the policy:

- has been issued and is active under dual-time visibility at `t`;
- has at least 30 elapsed days of visible history;
- is not already assigned to an open 90-day outcome episode; and
- has a valid evaluation watermark or an explicit right-censoring state.

The unit of observation is one eligible policy cutoff. The unit of resampling and uncertainty is the policy, because one policy can contribute repeated observations.

## 3. Recurring observations and outcome episodes

The default cadence MUST be every 30 elapsed days after the 30-day seasoning point while the policy remains eligible. There MUST be at most one observation per policy per UTC cutoff.

After an observation is created, its outcome episode owns `(as_of, as_of + 90 days]`. The next observation for that policy MUST NOT be created until the prior episode ends. This non-overlapping 90-day cadence prevents the same realized outcome from being counted in multiple evaluation rows. A terminal event ends future eligibility.

Each observation MUST carry a deterministic `observation_id` and `outcome_episode_id` derived from the v2 run identity, policy identity, cutoff, and contract version. These identifiers are audit sidecars and MUST NOT enter features.

## 4. Default corpus configuration

R2-05 MUST implement these default planning values unless an amendment is merged before any v2 result is inspected:

| Parameter | Frozen value |
| --- | --- |
| Policies per replicated corpus | `3,600` |
| Independent issuance cohorts | `24` monthly cohorts |
| Policies per cohort | `150` |
| Issuance span | `2022-01-01T00:00:00Z` through monthly cohort starts ending `2023-12-01T00:00:00Z` |
| Follow-up watermark | `2026-12-31T23:59:59Z` |
| Observation seasoning | `30` elapsed days |
| Observation cadence | Non-overlapping `90`-day outcome episodes after the first eligible cutoff |
| Label horizon | `90` elapsed days |
| Billing frequencies | monthly, quarterly, semiannual, annual |
| Default frequency allocation | Deterministic balanced assignment within every cohort |
| Currency | USD |

The implementation MUST report counts by cohort, billing frequency, role, outcome, and censoring state. A valid non-final role MUST contain all four billing frequencies, at least 500 eligible observations, at least 50 positive labels, at least 50 negative labels, and no more than 25% right-censored observations. Failure is structural and blocks model fitting.

The corpus size is an engineering design input, not a real-world prevalence or power claim. R2-07 learning curves will test whether conclusions depend materially on this size.

Within every cohort, policies MUST be assigned deterministically before event generation to mutually exclusive role families: 50% `fit`, 10% `selection`, 10% `calibration`, 10% `non_final_evaluation`, and 20% `r2_acceptance`. Assignment MUST use the namespaced policy identity and a versioned hash rule, remain balanced by billing frequency within one policy where integer counts permit, and be independent of outcomes and all risk draws. Zero policy identity overlap is required between role families.

## 5. Observable state and approved drivers

V2 approves the following pre-cutoff driver groups:

- policy tenure and fictional premium amount;
- product type and billing frequency;
- due-to-paid delay and rolling on-time-payment rate;
- recent failed-payment count, retry count, recovery count, and arrears duration;
- recent notice count and fictional notice category;
- recent service-contact count and fictional contact category;
- visible grace-period entries and recoveries; and
- approved missingness indicators derived only from fields visible at the cutoff.

R2-05 MUST add only the event fields and lifecycle transitions needed to construct those groups. Payment retries, recoveries, recurring billing, and reinstatement from a nonterminal grace state are approved. Loans, cash value, maturity benefits, conservation interventions, acquisition channel, demographic attributes, free text, and production procedure concepts remain deferred.

Every approved feature MUST have an event/schema owner, a dual-time visibility rule, and a reconstruction test. Current status, terminal outcomes, generator scenario, raw random values, oracle risk, latent frailty, future scheduled events, and identifiers MUST NOT be features.

## 6. Stochastic mechanism

V2 uses monthly discrete-time competing hazards. For policy `i` and month `m`, before either terminal outcome occurs:

```text
eta_lapse(i,m) = alpha_lapse(m)
               + beta_lapse · x(i,m)
               + frailty(i)
               + drift_lapse(m)

eta_surrender(i,m) = alpha_surrender(m)
                   + beta_surrender · x(i,m)
                   + 0.5 * frailty(i)
                   + drift_surrender(m)

h_lapse = exp(eta_lapse) / (1 + exp(eta_lapse) + exp(eta_surrender))
h_surrender = exp(eta_surrender) / (1 + exp(eta_lapse) + exp(eta_surrender))
h_continue = 1 - h_lapse - h_surrender
```

`x(i,m)` MUST contain only state observable by the modeled monthly cutoff. `frailty(i)` MUST be one seeded normal draw with mean `0` and standard deviation `0.35`, fixed for a policy and prohibited from features.

For one 90-day outcome episode, observable driver values are frozen at the episode's opening cutoff for outcome generation. Events occurring during that episode affect the next eligible episode, not the already-open probability. This rule makes the fixed-horizon probability exact and avoids conditioning an oracle on a realized future feature path.

The signal-present default MUST use an intercept and coefficient registry stored in canonical configuration. It MUST include at least one static driver, one recent-payment driver, one rolling-history driver, and one nonlinear or interaction term. Each nonzero coefficient MUST declare its sign, scale, transformation, and applicable cause. The implementation MUST validate finite values and monthly total terminal probability below `0.20` for every generated eligible state.

The null-signal configuration MUST set all observable-driver coefficients and interactions to zero while preserving event volume, missingness, calendar structure, and latent noise. The label-shuffle control MUST permute labels at policy level within evaluation fold and seed, never individual repeated observations.

### Oracle sidecar

For each eligible observation, the generator MUST compute the exact 90-day cumulative incidence of lapse, surrender, and their union implied by the three monthly hazards. It MUST publish two governed oracle values: `oracle_conditional`, which conditions on generator-only frailty and is the attainable full-data ceiling, and `oracle_observable`, which marginalizes frailty with fixed 32-node Gauss-Hermite quadrature and represents the probability conditional on approved observable drivers. Quadrature nodes, weights, ordering, and numeric normalization MUST be versioned. The sidecar MUST include only observation identity, contract/run identity, oracle probabilities, latent/scenario audit values, and realized draw provenance required for verification.

The oracle sidecar MUST be stored separately from public observation records, rejected by feature discovery recursively, excluded from preprocessing inputs, and unavailable to model fitting or selection code. R2-05 tests MUST prove these boundaries using direct and nested-key mutations.

## 7. Censoring and follow-up

A positive label requires a visible terminal event inside the horizon. A negative label requires an evaluation watermark at or beyond the horizon end and no qualifying visible event. Otherwise the observation is right-censored and MUST NOT be converted to zero.

Administrative censoring occurs at the corpus watermark. Event-driven censoring MAY represent a declared loss of observable follow-up but MUST be configured separately from terminal outcomes. The default corpus MUST include 5% independently seeded event-driven censoring, capped so the per-role structural requirement remains satisfied.

Censoring reason, censoring time, and label provenance MUST satisfy mutually exclusive schema and runtime variants building on R2-02.

## 8. Missingness, ingestion delay, corrections, and categories

The default signal-present corpus MUST implement:

- 5% MCAR missingness for approved nonrequired contact/payment attributes;
- one conditionally missing scenario in which missingness depends only on cutoff-visible product and billing attributes;
- ingestion delay drawn from a versioned bounded mixture: 90% in `[0, 24h]`, 9% in `(24h, 7d]`, and 1% in `(7d, 30d]`;
- corrections represented as new immutable events referencing the corrected event, never in-place mutation; and
- one predeclared category that first appears after the fitting interval to exercise frozen unknown-category handling.

Random draws MUST be seed- and namespace-derived with explicit domain separation. Delay and correction behavior MUST preserve `ingested_at >= occurred_at`; retroactive effective times remain allowed only under declared semantics. Missingness, delay, correction, or category values MUST NOT encode role, partition, outcome, or oracle probability.

## 9. Temporal drift scenarios

The protocol defines three named configurations:

- `stable`: no calendar drift beyond cohort composition;
- `moderate_drift`: baseline log-odds shift of at most `0.20`, one approved covariate prevalence change of at most 15 percentage points, and the declared category arrival; and
- `stress_drift`: baseline log-odds shift of `0.50` plus missingness and ingestion-delay increases defined in the acceptance protocol.

Drift parameters MUST be configuration fields included in canonical provenance. They MUST never be inferred from the requested evaluation role.

## 10. Dataset roles and temporal isolation

The v2 timeline MUST be divided chronologically into these logical roles:

| Role | Permitted use |
| --- | --- |
| `fit` | Fit preprocessing and model parameters |
| `selection` | Compare frozen candidates and feature-contract decisions |
| `calibration` | Fit a calibration mapping only after candidate selection |
| `non_final_evaluation` | Evaluate frozen non-final thresholds and robustness; cannot alter the selected model |
| `r2_acceptance` | Run the predeclared multi-seed/fold gate without final holdout |
| `final_release_holdout` | Future one-shot release evaluation only; not materialized through R2-07 |

The three R2 acceptance rolling-origin folds are frozen as follows:

| Fold | Fit cutoffs, inclusive | Acceptance cutoffs, inclusive |
| --- | --- | --- |
| `fold_1` | Through `2023-03-31T23:59:59Z` | `2023-07-01T00:00:00Z` through `2023-09-30T23:59:59Z` |
| `fold_2` | Through `2023-09-30T23:59:59Z` | `2024-01-01T00:00:00Z` through `2024-03-31T23:59:59Z` |
| `fold_3` | Through `2024-03-31T23:59:59Z` | `2024-07-01T00:00:00Z` through `2024-09-30T23:59:59Z` |

The fit side uses only `fit` policies and each acceptance side uses only `r2_acceptance` policies. Selection, calibration, and non-final-evaluation policies remain unavailable to R2-07 except for their separately authorized future purposes. The final release holdout is a future separately generated corpus, not a subset of these 3,600 policies.

Between adjacent time windows and roles R2-06 MUST enforce:

1. no feature cutoff in the later role at or before the latest earlier cutoff;
2. no earlier 90-day outcome horizon crossing the later role's first cutoff;
3. zero policy identity overlap between role families;
4. no outcome-episode overlap in all cases; and
5. preprocessing fit only on `fit` for the applicable temporal fold.

R2-06 may use rolling-origin folds within the non-final interval. It MUST NOT weaken chronology to satisfy category or outcome counts. Structural failure requires redesign.

## 11. Final release holdout

The holdout status is `not_materialized`. R2-04 through R2-07 MUST NOT choose its seed, generate its policies, build its observations, inspect its distributions, transform it, or score it.

A later dedicated release-evaluation issue MAY authorize materialization only after generator, observation, split, feature, preprocessing, candidate model, calibration, threshold, dependency, and command digests are frozen. The authorization record MUST name the accessor, purpose, UTC timestamp, one permitted command, input digests, environment lock digest, output location, and result digest.

One successful execution is permitted. A retry is allowed only for a documented infrastructure failure that produced no readable predictions or metrics; the retry MUST use identical inputs and record both attempts. An unfavorable or surprising result is not a retry reason and MUST NOT trigger model changes followed by re-evaluation on the same holdout.

These are audit and misuse controls, not a secrecy guarantee against a maintainer who can change public code.

## 12. Determinism, identity, and artifact rules

The exact config, namespace, seed, contract versions, dependency versions, and canonicalization version MUST determine histories, observations, sidecars, and provenance byte for byte. Random streams MUST use named domains so adding an unrelated mechanism does not silently change existing draws without a version change.

All v2 artifacts MUST include `v2` and their contract version in the path or filename, bind upstream SHA-256 digests, normalize numeric serialization, reject NaN/infinity, and avoid executable model serialization. No v1 artifact may change.

## 13. Required R2-05 and R2-06 tests

R2-05 MUST cover configuration validation, exact regeneration, cross-namespace identity separation, cohort balance, recurring observations, non-overlapping episodes, stochastic equations, oracle calculations, sidecar exclusion, point-in-time mutation, censoring variants, missingness, delay, correction, category arrival, drift, and unchanged v1 bytes.

R2-06 MUST cover chronological roles, both horizon embargoes, policy and episode isolation, role-bound scoring authorization, train-only preprocessing, unknown categories, feature prohibitions, artifact lineage, and the `not_materialized` final-holdout status.

## 14. Amendment policy

Before any v2 output is inspected, a change may amend this contract through issue #42 and its reviewed pull request. After any v2 output is inspected, a change to an equation, default parameter, role rule, metric, uncertainty method, threshold, or allowed failure requires a new contract/protocol version and an R2-07 `redesign` outcome. Failed or inconvenient replications MUST NOT be selectively omitted.

## 15. Exit boundary

Acceptance and merge authorize R2-05 implementation only. They do not resolve a limitation, authorize model evaluation, or resume P2-08/P2-09.

## 16. Requirement traceability

| Obligation | R2-04 decision | Implementation/evidence owner |
| --- | --- | --- |
| Resolve billing-frequency/time confounding design (`LIM-002-001`) | Multiple cohorts, balanced frequency allocation, recurring episodes, exclusive role families, fixed chronological folds | R2-05 implements; R2-06 verifies partitions; R2-07 evaluates stability |
| Add recoverable pre-cutoff statistical signal (`LIM-002-002`) | Transparent competing hazards, approved visible drivers, latent frailty, conditional and observable oracles, null controls | R2-05 implements; R2-07 runs recovery and falsification gates |
| Establish a future final-holdout boundary (`LIM-002-003`) | `not_materialized` through R2-07; later frozen-candidate, one-shot authorization and audit | R2-06 verifies absence; later dedicated release issue proves workflow |
| Preserve point-in-time validity | Dual effective/ingestion visibility, immutable corrections, episode ownership, both embargoes | R2-05 mutation tests; R2-06 split and feature tests |
| Prevent selection leakage | Exclusive role families, fixed folds, train-only preprocessing, role-bound scoring authorization | R2-06 |
| Predeclare statistical acceptance | Protocol `1.0.0`, fixed seeds, metrics, uncertainty, thresholds, allowed failures, decision aggregation | R2-07 executes without amendment |
