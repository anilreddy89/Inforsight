# Phase 2.05 Logistic-Regression Baseline Report

## Decision

This seeded logistic-regression run is a reproducible pipeline-engineering benchmark only. `LIM-002-001` remains unresolved, and the canonical test partition stayed sealed.

## Frozen configuration

- Baseline version: `1.0.0`
- Training configuration: `1.0.0`
- Seed: `20260817`
- Solver: `liblinear`
- Penalty and C: `l2`, `1.0`
- scikit-learn: `1.7.2`
- Fit partition: train only
- Test status: sealed and not scored

## Predeclared diagnostics

| Partition | Records | Positive | Log loss | ROC AUC | Brier score | Mean prediction | Observed fraction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 26 | 13 | 0.652595 | 0.642012 | 0.230997 | 0.499813 | 0.500000 |
| Validation | 27 | 15 | 0.689351 | 0.563889 | 0.248559 | 0.550038 | 0.555556 |

These values were not used to tune the estimator, preprocessing, calibration, or a decision threshold.

## Coefficients

| Frozen transformed feature | Coefficient | Odds ratio |
| --- | ---: | ---: |
| `premium_amount_cents` | 0.4613097888 | 1.586150147 |
| `policy_age_days` | 0 | 1 |
| `visible_event_count` | 0 | 1 |
| `visible_billing_count` | 0 | 1 |
| `visible_failed_payment_count` | 0 | 1 |
| `visible_received_payment_count` | 0 | 1 |
| `visible_notice_count` | 0 | 1 |
| `visible_service_contact_count` | 0 | 1 |
| `product_variant=fictional_term_life` | -0.120860845 | 0.8861572643 |
| `product_variant=fictional_whole_life` | 0.1257102053 | 1.133953507 |
| `product_variant=__unknown__` | 0 | 1 |
| `billing_frequency=monthly` | 0.0048493603 | 1.004861138 |
| `billing_frequency=__unknown__` | 0 | 1 |

Coefficients operate on standardized numeric fields and frozen one-hot columns. They are associations in a small, deliberately engineered synthetic corpus; they are not causal effects, actuarial factors, customer-impact evidence, or authority for conservation action.

## Limitations

- Billing frequency is confounded with first-billing observation time: train is monthly-only and validation is semiannual-only.
- Unseen held-out categories use the Phase 2.04 frozen unknown-category columns.
- The balanced fictional outcome mix is not a prevalence estimate.
- No canonical test result, calibration assessment, threshold, capacity analysis, fairness conclusion, or production claim is provided.

## Reproduction

```bash
python3 scripts/train_logistic_baseline.py --check
```
