# Feature-Sanity and Shortcut-Diagnostics Report

## Decision

The frozen train and validation matrices were screened reproducibly without opening the canonical test partition. Results remain `pipeline_engineering_only`: a flag prioritizes review and does not by itself prove leakage. `LIM-002-001` remains unresolved.

## Training-only mutual information

| Source feature | Maximum univariate MI |
| --- | ---: |
| `premium_amount_cents` | 0.090510 |
| `policy_age_days` | 0.146400 |
| `visible_event_count` | 0.061923 |
| `visible_billing_count` | 0.084970 |
| `visible_failed_payment_count` | 0.008459 |
| `visible_received_payment_count` | 0.000000 |
| `visible_notice_count` | 0.044356 |
| `visible_service_contact_count` | 0.049271 |
| `product_variant` | 0.011954 |
| `billing_frequency` | 0.000000 |

## Train-fit, validation-scored shallow models

| Source feature | Log loss | ROC AUC | Brier score |
| --- | ---: | ---: | ---: |
| `premium_amount_cents` | 7.142189 | 0.458333 | 0.357897 |
| `policy_age_days` | 0.693147 | 0.500000 | 0.250000 |
| `visible_event_count` | 0.693147 | 0.500000 | 0.250000 |
| `visible_billing_count` | 0.693147 | 0.500000 | 0.250000 |
| `visible_failed_payment_count` | 0.693147 | 0.500000 | 0.250000 |
| `visible_received_payment_count` | 0.693147 | 0.500000 | 0.250000 |
| `visible_notice_count` | 0.693147 | 0.500000 | 0.250000 |
| `visible_service_contact_count` | 0.693147 | 0.500000 | 0.250000 |
| `product_variant` | 0.663185 | 0.641667 | 0.235130 |
| `billing_frequency` | 0.693147 | 0.500000 | 0.250000 |

## Flags and dispositions

| Source feature | Triggered rules | Disposition | Follow-up |
| --- | --- | --- | --- |
| `premium_amount_cents` | None | not_flagged | No action from this screen. |
| `policy_age_days` | constant | allow | Retain under the existing leakage guards and re-evaluate after the corpus limitation is resolved. |
| `visible_event_count` | constant | allow | Retain under the existing leakage guards and re-evaluate after the corpus limitation is resolved. |
| `visible_billing_count` | constant | allow | Retain under the existing leakage guards and re-evaluate after the corpus limitation is resolved. |
| `visible_failed_payment_count` | constant | allow | Retain under the existing leakage guards and re-evaluate after the corpus limitation is resolved. |
| `visible_received_payment_count` | constant | allow | Retain under the existing leakage guards and re-evaluate after the corpus limitation is resolved. |
| `visible_notice_count` | constant | allow | Retain under the existing leakage guards and re-evaluate after the corpus limitation is resolved. |
| `visible_service_contact_count` | constant | allow | Retain under the existing leakage guards and re-evaluate after the corpus limitation is resolved. |
| `product_variant` | None | not_flagged | No action from this screen. |
| `billing_frequency` | constant | investigate | Resolve or explicitly disposition LIM-002-001 before the Phase 2 evaluation gate. |

Identifier/cardinality checks and deterministic targeted validation permutations are recorded in the machine-readable manifest. One-hot outputs are reviewed as source-feature groups. Observation IDs and targets remain sidecars.

## Integrity and limitations

- Test status: `sealed_not_scored`.
- Frozen preprocessing, logistic-regression state, and XGBoost state remained unchanged.
- Phase 2.04, Phase 2.05, and Phase 2.06 artifacts remained byte-identical.
- The small synthetic corpus makes mutual information, shallow-model scores, and permutation changes unstable.
- Billing frequency is confounded with observation time under `LIM-002-001`.
- No feature exclusion, model retraining, tuning, calibration, threshold selection, explanation, or release decision occurred.

## Reproduction

```bash
python3 scripts/run_feature_diagnostics.py --check
```
