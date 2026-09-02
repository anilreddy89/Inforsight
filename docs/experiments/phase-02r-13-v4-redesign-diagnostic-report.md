# Phase 2R.13 v4 Redesign Diagnostic Report

Issue: #69

## Aggregate results

| Measure | Observed |
| --- | ---: |
| `observable_oracle_auc_pass_count` | `0` |
| `median_observable_oracle_auc` | `0.533299464504321` |
| `median_observable_oracle_ap_lift` | `0.01722074930657448` |
| `median_observable_oracle_brier_skill` | `0.001050124398119967` |
| `median_xgboost_auc` | `0.5215306739718962` |
| `median_logistic_auc` | `0.5262734156863189` |
| `median_policy_episode_auc_difference` | `0.0` |
| `median_oracle_fold_spread` | `0.03917027146857244` |
| `parity_mismatch_count` | `0` |
| `near_constant_public_terms` | `['rolling_payment_count']` |

## Hypothesis dispositions

| Hypothesis | Disposition |
| --- | --- |
| `H1_ORACLE_SEPARABILITY` | `supported` |
| `H2_DRIVER_SUPPORT` | `supported` |
| `H3_TRANSFORM_PARITY` | `rejected` |
| `H4_EPISODE_DILUTION` | `rejected` |
| `H5_CANDIDATE_LEARNING` | `unresolved` |
| `H6_TEMPORAL_STABILITY` | `rejected` |

## Decision boundary

Selected response: `versioned_coefficient_frailty_incidence_or_event_prevalence_redesign`.

This evidence diagnoses only recovery of a fictional synthetic mechanism. 
Future acceptance and the final holdout remain `not_materialized`.
