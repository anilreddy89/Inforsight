# Phase 2R.13 v4 Statistical Substrate Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Contract version | `4.0.0` |
| Coefficient registry | `2.0.0` |
| Random-stream registry | `2.0.0` |
| Authority | ADR 0007 and R2-13 issue #69 |
| Implementation phase | R2-14 |
| Development seeds | `20271101..20271120` |
| Future acceptance | `20271201..20271220`, unmaterialized |
| Final holdout | `not_materialized` |

## 1. Preserved boundaries

V4 MUST preserve the event-first dual-time rule, immutable corrections, recurring
non-overlapping 90-day episodes, lapse-or-surrender union target, five policy roles,
three rolling-origin folds, policy grouping, protected oracle sidecar, matched
signal/null construction, deterministic replay, and public 17-feature surface.

V4 MUST use separate module, type, schema, identity, manifest, and artifact paths.
No v1, v2, or v3 file may be overwritten.

## 2. Corpus and event support

The default remains 14,400 policies, 24 monthly cohorts of 600, issuance from
2022-01 through 2023-12, watermark `2026-12-31T23:59:59Z`, 30-day seasoning, and
non-overlapping 90-day episodes.

Billing and payment opportunities MUST follow billing frequency:

| Billing frequency | Scheduled opportunities per 365 days |
| --- | ---: |
| monthly | 12 |
| quarterly | 4 |
| semiannual | 2 |
| annual | 1 |

Each scheduled opportunity owns one deterministic lifecycle-timing draw and its
associated behavior draws. A missing or failed payment remains represented by an
event outcome rather than deletion of the opportunity. Rolling payment count is
the number of visible recorded opportunities in `(t-365d, t]`.

## 3. Stochastic mechanism

For month `m`:

```text
eta_lapse = -4.85 + month_offset[m] + frailty
            + signal_scale * score_lapse_v4(z)
eta_surrender = -5.55 + month_offset[m] + 0.50 * frailty
                + signal_scale * score_surrender_v4(z)
```

`month_offset={-0.08,0.00,0.08}` and `frailty ~ Normal(0,0.20)`. Competing-risk
normalization and three-month cumulative incidence remain unchanged. Generated
monthly total terminal hazard MUST be finite and below `0.20`.

Coefficient registry `2.0.0` doubles every nonzero v3 public coefficient and keeps
missingness at zero:

| Term | Lapse | Surrender |
| --- | ---: | ---: |
| tenure | `-0.16` | `0.08` |
| premium | `0.24` | `0.36` |
| quarterly | `0.12` | `0.08` |
| semiannual | `0.20` | `0.12` |
| annual | `0.28` | `0.16` |
| recent delay | `0.84` | `0.24` |
| failed payments | `1.40` | `0.40` |
| retries | `0.36` | `0.10` |
| recoveries | `-0.60` | `-0.16` |
| arrears | `1.10` | `0.30` |
| on-time rate | `-0.90` | `-0.24` |
| rolling payments | `-0.20` | `-0.08` |
| notices | `0.48` | `0.36` |
| contacts | `0.24` | `0.44` |
| failed × arrears | `0.44` | `0.16` |
| missingness indicators | `0.00` | `0.00` |

Transforms, clipping, references, empty-history values, and interaction definition
remain exactly those in the v3 registry.

## 4. Identities and streams

V4 random-stream registry `2.0.0` retains all v3 domains and adds
`scheduled_payment_opportunity(policy, due_ordinal)`. Scenario interventions own
only their declared transforms. Signal and matched null MUST share the stream-set
identity; null changes only `signal_scale` from `1` to `0`.

`stream_set_id`, `artifact_id`, and `execution_id` retain canonical SHA-256 roles,
but include contract `4.0.0`, registry `2.0.0`, coefficient registry `2.0.0`, and
the complete event-support configuration.

## 5. Protected oracle

Conditional oracle uses the exact v4 frailty draw. Observable oracle integrates
frailty with frozen 32-node Gauss-Hermite quadrature at standard deviation `0.20`.
Oracle values, frailty, and outcome uniforms remain protected and prohibited from
ordinary features, preprocessing, fitting, selection, and scoring.

## 6. R2-14 qualification gates

All 20 development seeds and three folds run once. Every required gate must pass:

- at least 16 seeds have median-fold observable-oracle AUC `>=0.65`;
- across-seed median observable-oracle AUC `>=0.68`;
- median observable-oracle AP lift `>=0.10` and Brier skill `>0`;
- every nonzero term avoids absence/near-constancy/clipping saturation in at least
  16 seeds per fold;
- exact mechanism/feature parity has zero mismatches within `1e-12`;
- matched-null oracle and candidate median AUC are in `[0.45,0.55]`;
- at least 16 seeds have median-fold reference-model AUC `>=0.65`;
- monthly total hazard is finite and `<0.20` for every generated row; and
- dual-time, matched-stream, atomic-intervention, lineage, protected-oracle,
  deterministic replay, and final-holdout-absence tests pass.

Any failure blocks R2-15 and returns to reviewed R2-13 design. No coefficient,
event rate, seed, fold, or threshold may be changed after qualification output.

## 7. Claim boundary

V4 remains fictional synthetic evidence. Qualification cannot establish
prospective performance, actuarial validity, causal effect, fairness, operational
value, production readiness, or release readiness.
