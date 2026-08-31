# Phase 2R.10 v3 Structural Support

Overall status: `fail`.

| Membership | Role | Eligible | Positive | Negative | Censored | Frequencies | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| fold_1 | acceptance | 1491 | 248 | 1243 | 0 | annual=363, monthly=381, quarterly=387, semiannual=360 | pass |
| fold_2 | acceptance | 1301 | 215 | 1086 | 0 | annual=303, monthly=354, quarterly=331, semiannual=313 | pass |
| fold_3 | acceptance | 900 | 163 | 737 | 0 | annual=210, monthly=252, quarterly=225, semiannual=213 | pass |
| selection | selection | 467 | 80 | 387 | 0 | annual=120, monthly=117, quarterly=110, semiannual=120 | fail |

## Failures

- `selection`: selection membership has fewer than 500 eligible observations

## Boundaries

This report contains structural counts and membership digests only. It does not fit preprocessing or models, produce predictions or model metrics, access protected oracle sidecars, or materialize a final release holdout.

The frozen selection support failure is retained as evidence. No date, role, seed, threshold, or corpus setting was changed in response.
