# Phase 2R.13 v4 Diagnostic Interpretation Amendment

## 1. Status and authority

| Field | Value |
| --- | --- |
| Phase | R2-13 |
| Issue | [#69](https://github.com/anilreddy89/Inforsight/issues/69) |
| Amendment version | `1.1.0` |
| Status | Accepted before development output and merged through PR #70 as `7c4a1a7` |
| Amends | R2-12 diagnostic authorization contract `1.0.0` |
| Governing decision | ADR 0006 |
| Result access | Authorized within contract `1.0.0` as amended by `1.1.0` |
| Future acceptance | `not_materialized` |
| Final holdout | `not_materialized` |

R2-12 contract `1.0.0` freezes the hypothesis names, diagnostic families, seed
domains, protected boundary, and allowed redesign responses. It does not freeze
the exact interpretation algorithms and thresholds needed to assign `supported`,
`rejected`, or `unresolved`. Contract section 5 requires ambiguity affecting a
metric, aggregation, tolerance, or hypothesis rule to stop execution before
output inspection. This amendment closes that pre-result ambiguity.

No R2-13 development corpus, prediction, oracle metric, reference-model metric,
candidate metric, driver summary, or sensitivity result existed when this
amendment was written.

## 2. Common execution and aggregation

- Seeds are exactly `20271101..20271120` and scenarios are `signal` and
  `matched_null`; all three frozen folds run for every seed/scenario pair.
- The simulator remains v3 `3.1.0` and evaluation remains `3.2.0`. The development
  namespace is `r2-13-v4-development-diagnostic` for both matched scenarios.
- Fold membership, targets, and public features come from the existing governed
  fold builder. All comparisons within a seed/fold use identical memberships.
- Metrics retain protocol `2.2.0` definitions. A seed summary is the median of its
  three fold values. An across-seed summary is the median of 20 seed summaries.
- A pass-count rule uses all 20 seeds; invalid or missing seeds remain failures.
- Full runtime precision determines comparisons. Committed floats use canonical
  12-decimal normalization. Equality parity uses absolute tolerance `1e-12`.
- Every small cell with fewer than 10 unique policies is suppressed and makes a
  required interpretation that depends on it `unresolved`.
- Any missing, non-finite, unauthorized, inconsistent, or incomplete required
  diagnostic makes its hypothesis `unresolved`; leakage, protected contamination,
  future-acceptance access, holdout access, substitution, or tampering yields
  `stop` and prevents all design selection.

## 3. Metric definitions

- `AP lift = average_precision - prevalence`.
- `Brier skill = 1 - brier_score / (prevalence * (1 - prevalence))`.
- `fold spread = maximum fold ROC AUC - minimum fold ROC AUC` for an identical
  score/model and seed.
- `near constant` means the most frequent finite value occupies at least `99%` of
  rows or numeric population standard deviation is at most `1e-12`.
- `clipping saturation` means at least `95%` of rows equal the mechanism term's
  declared lower or upper clipping boundary.
- `effective weight concentration` is the maximum policy row count divided by all
  rows in the membership.
- `policy sensitivity AUC` scores one row per policy using the maximum episode
  score and policy target; `episode AUC` uses all governed episode rows.
- The contract-derived reference score is `oracle_observable_union`.
- The conditional ceiling score is `oracle_conditional_union`.
- The correctly specified reference model is an unpenalized logistic calibration
  of the logit of the observable oracle, fit on the governed fit membership and
  scored on its paired evaluation membership. Probabilities are clipped only for
  the logit calculation to `[1e-12, 1 - 1e-12]`.

## 4. Hypothesis interpretation rules

### H1 — Observable-oracle separability

Required per seed/fold evidence is observable- and conditional-oracle ROC AUC, AP
lift, Brier skill, calibration intercept/slope, and public-versus-latent variance.

- `supported` when fewer than 16 of 20 signal seeds have median-fold observable
  oracle AUC at least `0.65`, or across-seed median observable-oracle AUC is below
  `0.68`.
- `rejected` when at least 16 seeds meet `0.65`, the across-seed median is at least
  `0.68`, median AP lift is at least `0.10`, and median Brier skill is positive.
- Otherwise `unresolved`.

These thresholds reuse the frozen R2-11 recovery expectations and do not inspect
development output to define a new success level.

### H2 — Realized driver support

Required evidence covers every registered mechanism term by seed/fold/role/class.

- `supported` when any nonzero mechanism term is absent, constant, near constant,
  or clipping-saturated in more than 4 of 20 signal seeds in any governed fold.
- `rejected` when every nonzero term avoids those conditions in at least 16 seeds
  in every fold and each categorical reference/active level has at least 10 unique
  policies wherever used.
- Otherwise `unresolved`.

### H3 — Mechanism/feature transform parity

- `supported` when any independently reconstructed public mechanism term has a
  mismatch count greater than zero or maximum absolute error above `1e-12`, or any
  required mutation test fails.
- `rejected` when all terms have zero mismatches within tolerance for all 20 seeds,
  both scenarios, and all folds, and every required mutation passes.
- Otherwise `unresolved`.

### H4 — Episode or weighting dilution

Required evidence includes row/policy counts, episodes per policy, prevalence,
weight concentration, episode AUC, and policy sensitivity AUC.

- `supported` when the absolute policy-versus-episode AUC difference is at least
  `0.05` in at least 16 signal seeds, or median effective weight concentration is
  at least `0.02` and the policy sensitivity improves AUC by at least `0.05`.
- `rejected` when fewer than 5 seeds have an absolute difference of `0.05` and the
  across-seed median absolute difference is below `0.025`.
- Otherwise `unresolved`.

The sensitivity remains diagnostic and cannot change the estimand in R2-13.

### H5 — Candidate learning failure

Required evidence compares reference score/model, logistic, and XGBoost on
identical memberships and records convergence, prediction variance, and feature
use.

- `supported` only when H1 is `rejected`, at least 16 signal seeds have
  median-fold reference-model AUC at least `0.65`, and fewer than 16 seeds have
  median-fold XGBoost AUC at least `0.65` or the across-seed median reference-minus-
  XGBoost AUC is at least `0.05`.
- `rejected` when H1 is `rejected` and the XGBoost pass count is at least 16 and
  median reference-minus-XGBoost AUC is below `0.05`.
- If H1 is supported or unresolved, H5 is `unresolved` because learnability cannot
  be separated from weak observable signal.

### H6 — Temporal instability

- `supported` when at least 16 signal seeds have observable-oracle or reference-
  model fold spread above `0.10`, or at least 16 seeds have a worst-fold AUC below
  `0.60` while their median-fold AUC is at least `0.65`.
- `rejected` when fewer than 5 seeds exceed `0.10`, the across-seed median spread
  is at most `0.05`, and at least 16 seeds have worst-fold AUC at least `0.60`.
- Otherwise `unresolved`.

## 5. Design response and precedence

If any readiness or protected-boundary `stop` occurs, publish `stop` and make no
design proposal. Otherwise derive all six dispositions, then apply:

1. H3 repair precedes substrate or candidate changes because parity failure makes
   later recovery evidence uninterpretable.
2. H1/H2 may jointly authorize the smallest coefficient/noise/incidence and event-
   support redesign necessary to address both supported mechanisms.
3. H5 may drive candidate changes only when H1 is rejected.
4. H4 or H6 may add only their specifically authorized estimand/weighting or
   drift/fold amendment.
5. Any mixed set that cannot be addressed without an unsupported change produces
   another bounded diagnostic proposal and keeps R2-14 blocked.

## 6. Acceptance required before execution

- [x] Review confirms all algorithms and thresholds were declared before output.
- [x] Contract consistency tests bind version `1.1.0` and this file's SHA-256.
- [x] ADR 0006 recognizes this interpretation layer.
- [x] Readiness requires the accepted amendment identity and fails closed if its
  status, version, digest, rules, or seed domains change.
- [ ] Hosted CI passes with the accepted interpretation identity.
- [x] User approval was recorded before the development diagnostic block runs.

This accepted amendment authorizes the R2-13 development diagnostic block only.
Future acceptance and final-holdout access remain prohibited.
