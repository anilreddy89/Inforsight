# Phase 2R.08 v3 Statistical Substrate Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Statistical simulator, event, observation, and label contracts | `3.0.0` |
| Random-stream registry | `1.0.0` |
| Evaluation split, feature, preprocessing, scoring-authorization, and candidate-selection contracts | `3.0.0` |
| Acceptance protocol | `2.0.0` |
| Status | Approved through issue #53 and PR #54, merge commit `09f678a`; no v3 output inspected |
| ADR | `docs/adr/0005-replace-v2-with-a-dual-time-matched-control-v3-statistical-substrate.md` |
| Acceptance protocol | `docs/modeling/phase-02r-08-statistical-acceptance-protocol.md` |
| Final release holdout | `not_materialized` |

Normative terms `MUST`, `MUST NOT`, `SHOULD`, and `MAY` have their usual requirements meaning. V1, v2, ADR 0004, protocol `1.0.0`, and the R2-07 `stop` evidence remain immutable historical records.

## 1. Intended use, estimand, and claim boundary

V3 MUST test whether the repository recovers a known fictional mechanism while preserving dual-time visibility, matched controls, temporal isolation, scoring authorization, and deterministic reproduction.

For an eligible active policy at UTC cutoff `t`, the primary estimand remains:

```text
P(lapse or surrender in (t, t + 90 elapsed days] |
  events with effective_at <= t and ingested_at <= t,
  policy active at t)
```

The start is exclusive and end inclusive. The observation is one eligible policy cutoff; policy is the resampling cluster. Lapse and surrender remain distinct in provenance and combine only for the binary target.

V3 MUST NOT support claims of insurer representativeness, prevalence, actuarial validity, causal effect, fairness, operational utility, customer impact, production readiness, or real-world prediction.

## 2. Event-first dual-time boundary

Generation MUST occur in this order:

1. create immutable event envelopes and payloads;
2. select the visible set `V(i,t) = {e: e.policy_id=i, e.effective_at<=t, e.ingested_at<=t}`;
3. validate the complete visible history;
4. reconstruct public state and features only from `V(i,t)`;
5. compute hazards from those reconstructed values plus governed latent frailty; and
6. create labels from visible terminal events and the evaluation watermark.

Every observation MUST record sorted `visible_event_ids`, a digest of canonical visible events, and per-feature lineage naming source event IDs or the literal `cutoff_derived`. A behavior feature with no admitted source MUST use its declared empty-history value.

Feature construction MUST NOT consume a generator working variable, scheduled-but-not-created event, event excluded from `V(i,t)`, oracle value, frailty, outcome uniform, scenario name, role, identifier token, future state, or label. Corrections MUST be new immutable events referencing an earlier event; reconstruction applies a correction only when both events are visible.

Mutation tests MUST move each source event independently across the effective and ingestion boundaries and prove the feature changes only when both predicates pass.

## 3. Eligibility, recurrence, and episodes

A policy is eligible when it is active under the visible history, has at least 30 elapsed days of visible history, has no open outcome episode, and has sufficient watermark information to distinguish observed from censored follow-up.

The first cutoff is 30 elapsed days after issuance. Later cutoffs begin only after the preceding 90-day episode closes. There is at most one observation per policy/cutoff and no overlapping episodes. Terminal outcomes end future eligibility.

`policy_id`, `event_id`, `observation_id`, and `outcome_episode_id` MUST derive from `stream_set_id`, stable entity keys, cutoff, and contract version. They are audit sidecars and prohibited features.

## 4. Frozen default corpus

| Parameter | Value |
| --- | --- |
| Policies per replication | `14,400` |
| Issuance cohorts | `24` monthly cohorts |
| Policies per cohort | `600` |
| Issuance dates | Month starts from `2022-01-01T00:00:00Z` through `2023-12-01T00:00:00Z` |
| Watermark | `2026-12-31T23:59:59Z` |
| Seasoning | `30` elapsed days |
| Episode/cadence | Non-overlapping `90` elapsed days |
| Billing frequencies | monthly, quarterly, semiannual, annual |
| Currency | USD |
| Role allocation within cohort/frequency | 50% fit, 10% selection, 10% calibration, 10% non-final evaluation, 20% acceptance |
| Acceptance replication seeds | `20261001` through `20261020` |

Allocation MUST be deterministic before risk draws, balanced within cohort and frequency where integer counts permit, and independent of outcomes. Roles have zero policy overlap. Every evaluated role/fold MUST contain all frequencies, at least 500 eligible uncensored observations, at least 50 positives, at least 50 negatives, and at most 25% right censoring. Realized failure is structural; generation MUST NOT force outcomes or replace a seed.

## 5. Identities and canonical provenance

V3 separates:

- `stream_set_id = SHA256(canonical(stream_registry_version, base_seed, namespace, structural_config))`;
- `artifact_id = SHA256(canonical(stream_set_id, complete_scenario_config, all_contract_versions))`; and
- `execution_id = SHA256(canonical(artifact_id, source_digest, dependency_lock_digest, command_digest, canonicalization_version))`.

`structural_config` contains cohort, entity-count, date, cadence, and role-allocation fields but excludes intervention values. `complete_scenario_config` contains every output-affecting field. Canonicalization is sorted-key UTF-8 JSON, NFC strings, UTC `Z` timestamps, finite decimal strings, and a trailing newline for files.

Changing an intervention MUST preserve `stream_set_id` and change `artifact_id`. Changing code/dependencies/command MUST change `execution_id`. Provenance MUST include all three and reject missing or inconsistent identities.

## 6. Random-stream registry 1.0.0

Every primitive uniform is derived as the first 64 bits of `HMAC-SHA256(stream_set_id, canonical(domain, keys))`, mapped to the open interval `(0,1)` by `(integer + 0.5)/2^64`. Normal draws use a versioned inverse-normal transform. Iteration order MUST NOT control a draw.

| Domain | Keys | Owner/reuse rule |
| --- | --- | --- |
| `entity_identity` | cohort, ordinal | Stable across all scenarios |
| `role_assignment` | policy | Stable across all scenarios |
| `static_covariate` | policy, field | Stable unless the named covariate-prevalence intervention owns the field |
| `lifecycle_timing` | policy, event kind, ordinal | Stable across scenarios |
| `behavior_value` | policy, event kind, ordinal, field | Stable across scenarios |
| `ingestion_delay` | event | Stable unless delay intervention owns the threshold transform |
| `missingness` | policy/event, field | Stable; scenario changes only its declared threshold |
| `correction` | event, field | Stable across scenarios |
| `frailty` | policy | Stable across signal/null/stress pairs |
| `outcome_uniform` | policy, episode, month | Stable across signal/null/stress pairs |
| `label_shuffle` | seed, fold, policy | Used only by protocol 2.0.0 |
| `bootstrap` | seed, fold, metric, replicate, draw | Used only by protocol 2.0.0 |
| `learning_order` | seed, fold, policy | Used only by protocol 2.0.0 |

An intervention manifest MUST list the only fields/transforms it may alter. Pair validation MUST compare all unaffected primitive draws and canonical event fields exactly. Different hazards MAY cause later survival-dependent events or memberships to diverge; comparisons then apply through the last common eligible identity/time and report divergence explicitly.

## 7. Public feature and driver-group registry

Every model input belongs to exactly one group:

| Group ID | Approved content | Designed status |
| --- | --- | --- |
| `static` | tenure, log premium, product, billing frequency | Nonzero |
| `recent_payment` | most recent due-to-paid delay, 90-day failure/retry/recovery counts, arrears days | Nonzero; strongest group |
| `rolling_history` | 365-day on-time rate and payment count | Nonzero |
| `service_notice` | 90-day notice/contact counts and frozen categories | Nonzero |
| `missingness` | approved visible missingness indicators | Zero effect in stable signal scenario |

The feature dictionary in R2-10 MUST map each feature exactly once and recursively reject protected concepts.

## 8. Frozen stochastic mechanism

For policy `i`, episode cutoff `t`, and modeled month `m=1,2,3`, reconstruct standardized public vector `z(i,t)` from visible events. Continuous transforms and scales are frozen in the coefficient registry below. Categories use the named reference level and additive contrasts.

```text
eta_lapse(i,t,m) = -3.35 + month_offset[m] + 1.00 * frailty(i)
                   + signal_scale * score_lapse(z(i,t)) + drift_lapse(t)

eta_surrender(i,t,m) = -4.05 + month_offset[m] + 0.50 * frailty(i)
                       + signal_scale * score_surrender(z(i,t)) + drift_surrender(t)

h_lapse = exp(eta_lapse) / (1 + exp(eta_lapse) + exp(eta_surrender))
h_surrender = exp(eta_surrender) / (1 + exp(eta_lapse) + exp(eta_surrender))
h_continue = 1 - h_lapse - h_surrender
```

`month_offset = {1: -0.08, 2: 0.00, 3: 0.08}`. `frailty ~ Normal(0, 0.35)` through domain `frailty`. `signal_scale=1` for signal scenarios and `0` for null. Each monthly outcome uses `outcome_uniform(policy, episode, month)` with intervals `[0,h_lapse)`, `[h_lapse,h_lapse+h_surrender)`, and continuation otherwise. Total terminal hazard MUST be finite and below `0.20`; violation is structural.

### Canonical coefficient registry 1.0.0

| Term | Transform/reference | Lapse | Surrender | Group |
| --- | --- | ---: | ---: | --- |
| tenure | clip(days/365, 0, 5) | `-0.08` | `0.04` | static |
| premium | clip(log1p(USD)/5, 0, 2) | `0.12` | `0.18` | static |
| quarterly | reference monthly | `0.06` | `0.04` | static |
| semiannual | reference monthly | `0.10` | `0.06` | static |
| annual | reference monthly | `0.14` | `0.08` | static |
| recent delay | clip(days/30, 0, 3), empty `0` | `0.42` | `0.12` | recent_payment |
| failed payments | clip(count/3, 0, 2) | `0.70` | `0.20` | recent_payment |
| retries | clip(count/3, 0, 2) | `0.18` | `0.05` | recent_payment |
| recoveries | clip(count/3, 0, 2) | `-0.30` | `-0.08` | recent_payment |
| arrears | clip(days/60, 0, 2) | `0.55` | `0.15` | recent_payment |
| on-time rate | value in `[0,1]`, empty `0.5` | `-0.45` | `-0.12` | rolling_history |
| rolling payments | clip(count/12, 0, 2) | `-0.10` | `-0.04` | rolling_history |
| notices | clip(count/3, 0, 2) | `0.24` | `0.18` | service_notice |
| contacts | clip(count/3, 0, 2) | `0.12` | `0.22` | service_notice |
| failed × arrears | product of transformed terms | `0.22` | `0.08` | recent_payment |
| all missingness indicators | binary | `0.00` | `0.00` | missingness |

R2-09 MUST implement these values exactly. No coefficient may be tuned after output inspection.

## 9. Oracle and labels

For each eligible observation, v3 MUST calculate exact three-month cumulative incidence for lapse, surrender, and union from the frozen cutoff vector. `oracle_conditional` conditions on frailty. `oracle_observable` integrates frailty with the same fixed 32-node Gauss-Hermite nodes, weights, ordering, and normalization preserved from contract `2.0.0`.

Oracle records are protected sidecars keyed by observation and artifact identity. They MUST be unavailable to feature discovery, preprocessing, fitting, selection, or ordinary scoring. Direct and nested-key mutation tests MUST prove rejection.

A positive label requires a qualifying visible terminal event in the episode. A negative requires watermark coverage through the episode end and no qualifying event. Otherwise the row is right-censored and excluded from fitting/metrics but counted in structural evidence.

## 10. Missingness, delay, corrections, categories, and drift

Stable/default uses 5% MCAR for approved optional attributes, the v2 bounded delay mixture (90% `[0,24h]`, 9% `(24h,7d]`, 1% `(7d,30d]`), immutable correction events, and the predeclared post-fit category arrival.

Atomic variants are:

| Variant | Only permitted change |
| --- | --- |
| `null_signal` | `signal_scale: 1 -> 0` |
| `doubled_missingness` | MCAR threshold `0.05 -> 0.10` |
| `unknown_category_arrival` | declared service category maps from known to new after `2024-01-01` |
| `moderate_drift` | baseline log-odds `+0.20` after `2024-01-01`; one declared covariate threshold shifts prevalence by no more than 0.15 |
| `stress_drift` | baseline log-odds `+0.50`, MCAR `0.10`, delay thresholds yielding 80%/15%/5% mixture after `2024-01-01` |

Scenario construction MUST reuse primitive uniforms and change only the listed threshold/transform. Role and outcome values MUST never drive missingness, delay, category, or drift.

## 11. Evaluation roles, folds, and embargoes

Role permissions remain fit, selection, calibration, non-final evaluation, acceptance, and future final release. Selection uses fit cutoffs through `2024-03-31T23:59:59Z` and selection cutoffs `2024-07-01` through `2024-09-30` UTC.

The three acceptance folds remain:

| Fold | Fit through | Acceptance interval, inclusive |
| --- | --- | --- |
| `fold_1` | `2023-03-31T23:59:59Z` | `2023-07-01T00:00:00Z` to `2023-09-30T23:59:59Z` |
| `fold_2` | `2023-09-30T23:59:59Z` | `2024-01-01T00:00:00Z` to `2024-03-31T23:59:59Z` |
| `fold_3` | `2024-03-31T23:59:59Z` | `2024-07-01T00:00:00Z` to `2024-09-30T23:59:59Z` |

Every boundary MUST prove strict cutoff chronology, a full 90-day outcome embargo, zero policy overlap, zero episode overlap, and fit-only preprocessing. Caller order normalizes by `(as_of, policy_id, observation_id)`.

## 12. Candidate selection and scoring authorization

The candidates retain the R2-06 specifications and dependency pins. Selection fits both on identical governed fit rows and scores identical selection rows. Select higher ROC AUC; if absolute AUC difference is at most `1e-12`, select lower Brier; if both differ by at most `1e-12`, select logistic. The selected name, specification, memberships, metrics, and digests MUST be frozen before acceptance-role access.

Authorization `3.0.0` binds purpose, fold, role, ordered observation IDs, feature names, complete matrix/target digest, fit matrix digest, preprocessing digest, model digest, artifact identity, and contract versions. Relabeling, reordering, substitution, derivation, or tampering MUST fail before prediction.

## 13. Artifacts, determinism, and implementation ownership

V3 paths and filenames MUST contain `v3`; no old public API may silently adopt v3 semantics. Artifacts bind all upstream identities/digests, use finite canonical JSON, and exclude raw matrices, row-level oracle sidecars, predictions, bootstrap samples, and executable model objects.

R2-09 owns event/corpus/observation implementation and dual-time/matched-stream tests. R2-10 owns folds, features, preprocessing, diagnostics, candidates, selection, authorization, and deterministic non-final evidence. R2-11 owns readiness and protocol `2.0.0` execution.

## 14. Final release holdout

Status remains `not_materialized`. R2-08 through R2-11 MUST NOT choose its seed, generate identity or membership, inspect distributions, construct features, transform, predict, or score it. A later dedicated one-shot issue may authorize creation only after every release-candidate digest is frozen under the existing audited retry boundary.

## 15. Amendment and exit policy

Before any v3 output is inspected, issue #53 may amend this proposal through review. After inspection, changing a frozen setting or procedure requires a reviewed contract/protocol version increment; failed or inconvenient replications may not be omitted or regenerated.

Merge authorizes R2-09 only. It does not resolve a limitation, establish acceptance, resume P2-08/P2-09, or authorize holdout access.

## 16. R2-07 finding traceability

| R2-07 finding | Normative correction | Evidence owner |
| --- | --- | --- |
| Post-cutoff ingestion leakage | Sections 2 and 9 event-first dual-time reconstruction | R2-09 mutation tests; R2-11 readiness |
| Unmatched null streams | Sections 5, 6, and 10 identities/registry/atomic null | R2-09 equality tests |
| Unmatched stress streams | Sections 6 and 10 atomic variants | R2-09 equality tests; R2-11 readiness |
| No selected candidate | Section 12 deterministic selection | R2-10 frozen evidence |
| No driver/strongest/zero registry | Sections 7 and 8 | R2-10 dictionary and diagnostics |
| No canonical coefficients | Section 8 | R2-09 equation tests |
| No shuffle domain | Section 6 and protocol 2.0.0 | R2-11 tests |
| Insufficient fold support | Sections 4 and 11 enlarged capacity plus unchanged fail-closed counts | R2-10 split evidence; R2-11 readiness |
