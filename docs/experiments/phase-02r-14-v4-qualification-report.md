# Phase 2R.14 v4 Development Qualification Report

Issue: #72

## Result

Mechanical decision: `redesign`.

## Qualification summary

| Measure | Observed |
| --- | ---: |
| `observable_oracle_auc_pass_count` | `0` |
| `median_observable_oracle_auc` | `0.5666277193591145` |
| `median_observable_oracle_ap_lift` | `0.021991623169585837` |
| `median_observable_oracle_brier_skill` | `0.0034835078850924406` |
| `reference_model_auc_pass_count` | `0` |
| `median_matched_null_oracle_auc` | `0.5` |
| `median_matched_null_candidate_auc` | `0.4998253417630266` |
| `parity_mismatch_count` | `0` |
| `maximum_monthly_terminal_hazard` | `0.21847588960475323` |

## Gates

| Gate | Status |
| --- | --- |
| `observable_seed_recovery` | `fail` |
| `observable_aggregate_recovery` | `fail` |
| `oracle_probability_quality` | `fail` |
| `driver_support` | `pass` |
| `transform_parity` | `pass` |
| `matched_null_behavior` | `pass` |
| `reference_recovery` | `fail` |
| `hazard_validity` | `fail` |
| `structural_controls` | `pass` |

This is development qualification of a fictional synthetic mechanism only.
Future acceptance and the final holdout remain `not_materialized`.
