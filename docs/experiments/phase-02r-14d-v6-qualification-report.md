# Phase 2R.14D Generation v6 Development Qualification Report

Issue: #88

## Result

Mechanical decision: `qualified`.

## Qualification summary

| Measure | Observed |
| --- | ---: |
| `observable_oracle_auc_pass_count` | `16` |
| `median_observable_oracle_auc` | `0.7085905976950702` |
| `median_observable_oracle_ap_lift` | `0.13984798509821808` |
| `median_observable_oracle_brier_skill` | `0.07453937139686051` |
| `reference_model_auc_pass_count` | `20` |
| `median_matched_null_oracle_auc` | `0.5` |
| `median_matched_null_candidate_auc` | `0.5040247432366816` |
| `parity_mismatch_count` | `0` |
| `maximum_monthly_terminal_hazard` | `0.1499864601986411` |

## Gates

| Gate | Status |
| --- | --- |
| `observable_seed_recovery` | `pass` |
| `observable_aggregate_recovery` | `pass` |
| `oracle_probability_quality` | `pass` |
| `driver_support` | `pass` |
| `transform_parity` | `pass` |
| `matched_null_behavior` | `pass` |
| `reference_recovery` | `pass` |
| `hazard_validity` | `pass` |
| `structural_controls` | `pass` |

This is development qualification of the Generation v6 bounded sigmoid substrate.
Future acceptance and the final holdout remain `not_materialized`.
