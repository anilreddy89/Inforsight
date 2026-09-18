# RH-12 Evidence Reconciliation Report 1.0.0

- **Artifact:** `inforsight.rh12.evidence-reconciliation` / `1.0.0`
- **Evidence digest:** `47ac6e06793e66b20601a05486fbb24fe24ff91bbffc4acda8e4523853527933`
- **Evaluation seed:** `20280201`
- **Cohort:** `3,600` unique synthetic policies
- **Cutoff:** `2026-09-08T00:00:00Z`; horizon `90` days
- **Final holdout:** `not_accessed`

## Disposition

This is corrected, versioned evidence generated after the RH-04 economics/resource and RH-05 allocation repairs. The historical Phase 3.08 OPE manifest and report remain unchanged. Results are synthetic and conditional on the frozen Generation v6 model, potential-outcome simulator, eligibility rules, catalog, economics contract, and allocator.

The primary estimand is **new-portfolio allocation-procedure performance**. A separate fixed-assignment sampling estimand is reported below; the two are not pooled.

## Contracts and comparison context

- Economics: `inforsight.synthetic-economics-resource` version `1.0.0` digest `568cbd4f30fbbc7f5b1db5afcacd06ce965b2a237212275b047df7ab19170b20`.
- Allocation: `inforsight.portfolio-allocation` version `1.0.0`.
- Model bundle: `inforsight-v6-logistic-platt-20260817` version `1.0.0`.
- Budget capacity: `5000000000` USD micros.
- Personnel capacity: `180000` seconds; display-only equivalent `50` hours.

All four strategies use the same cohort, cutoff, eligibility results, semantic catalog, economics identity, budget capacity, and personnel capacity.

| Strategy | Selected | Abstain | Net value | Signed effect | Expected harm | Modeled recall | Non-beneficial contacts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Non-intervention | 0 | 3600 | $0.00 | 0.000000 | 0.000000 | 0.0000% | 0 |
| Rules-only | 2031 | 1569 | $8,734.27 | 19.581199 | 0.000000 | 2.5699% | 0 |
| Risk-ranked | 1974 | 1626 | $11,288.39 | 24.143563 | 0.000000 | 3.1687% | 0 |
| Allocation engine | 1832 | 1768 | $20,825.76 | 25.496352 | 0.000000 | 3.3462% | 0 |

## Estimand 1 — frozen-assignment sampling uncertainty

Each replicate draws exactly the original number of unique `policy_id` clusters with replacement. The already selected action assignment is retained for each sampled occurrence. Duplicate occurrences contribute separately to totals. Resource totals may exceed the original capacity because allocation is not rerun.

| Strategy | Net value median [95% interval] | Signed effect median [95% interval] | Expected harm median [95% interval] |
| --- | ---: | ---: | ---: |
| Non-intervention | $0.00 [$0.00, $0.00] | 0.000000 [0.000000, 0.000000] | 0.000000 [0.000000, 0.000000] |
| Rules-only | $8,715.49 [$8,188.60, $9,304.84] | 19.586780 [18.828719, 20.297531] | 0.000000 [0.000000, 0.000000] |
| Risk-ranked | $11,275.97 [$10,591.02, $12,017.86] | 24.144081 [23.149099, 25.115080] | 0.000000 [0.000000, 0.000000] |
| Allocation engine | $20,772.26 [$19,172.33, $22,552.86] | 25.474497 [24.251410, 26.721586] | 0.000000 [0.000000, 0.000000] |

## Estimand 2 — new-portfolio allocation-procedure performance

Each replicate retains source policy facts and frozen scores/effects, assigns duplicate occurrence identities as `policy_id#draw_index`, reruns the four-strategy comparison, and holds the original total budget micros and personnel seconds fixed. No model refit, calibration refit, or effect re-estimation occurs.

| Strategy | Net value median [95% interval] | Signed effect median [95% interval] | Expected harm median [95% interval] |
| --- | ---: | ---: | ---: |
| Non-intervention | $0.00 [$0.00, $0.00] | 0.000000 [0.000000, 0.000000] | 0.000000 [0.000000, 0.000000] |
| Rules-only | $8,734.28 [$8,171.32, $9,250.88] | 19.567823 [18.898438, 20.313364] | 0.000000 [0.000000, 0.000000] |
| Risk-ranked | $11,269.75 [$10,599.34, $11,917.23] | 24.128382 [23.387571, 24.842525] | 0.000000 [0.000000, 0.000000] |
| Allocation engine | $20,811.18 [$19,491.06, $22,030.53] | 25.465516 [24.795321, 26.165001] | 0.000000 [0.000000, 0.000000] |

## Metric and claim boundaries

- `modeled_expected_annual_premium_preserved_usd_micros` is a signed modeled value under RH-04's synthetic one-year annual-premium basis. It is not realized premium, revenue, margin, profit, or causal value.
- `signed_combined_termination_effect_90d` is the combined lapse-or-surrender probability difference. It does not identify separate causal lapse and surrender treatment effects.
- `modeled_recall_at_capacity` is an expected-effect ratio, not observed-outcome recall. The current counterfactual artifact supports no intervention-time lead-time estimate, so lead time is explicitly `not_supported`.
- The synthetic corpus has no demographic attributes; no fairness or disparate-impact claim is made.
- The v5 infeasibility result remains bounded to its examined design/search space and is not a universal impossibility claim.
- Protocol 3.1.0 and acceptance-seed reuse remain visible. Fresh-seed confirmation was not run and requires a separate predeclared experiment issue.

## Independent issue #130

Disposition: **defer**. Fresh simulator stress variants are not required for the RH-12 core reconciliation. If later incorporated, variants, thresholds, estimand, seeds, and artifact versions must be predeclared before results are inspected; unfavorable results remain valid evidence.

## Historical artifact preservation

- Legacy manifest SHA-256: `4779e0d3326caf07636929169342febca9777162aac84adb8af9c73104dfb88e`
- Legacy report SHA-256: `efba4c70d7a35f7641a2c6386c1a0330d7702ae7b2ab6dac8672e442408d4047`
- The legacy files were read only and were not rewritten by this run.

## Verification

This artifact is generated with the repository's synthetic Generation v6 corpus, RH-04 contract 1.0.0, RH-05 allocator 1.0.0, and the verified model bundle. `--check` regenerates the manifest and compares the evidence digest without rewriting the published JSON or report.
