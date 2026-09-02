# Phase 2R.13 v4 Statistical Acceptance Protocol

## Protocol metadata

| Field | Value |
| --- | --- |
| Protocol version | `3.0.0` |
| Substrate | v4 contract `4.0.0` |
| Authority | ADR 0007 and R2-13 issue #69 |
| Development qualification | R2-14, seeds `20271101..20271120` |
| Future acceptance | R2-16, seeds `20271201..20271220` |
| Final holdout | `not_materialized` |

## 1. Dependency and access order

```text
R2-13 design freeze -> R2-14 implementation/qualification
 -> R2-15 evaluation/candidate freeze -> R2-16 one acceptance execution
```

R2-14 may access development seeds only. R2-15 may construct evaluation and
selection evidence from the approved development substrate but MUST NOT generate
or score future acceptance outcomes. R2-16 runs only after every upstream identity
and digest is frozen and merged.

## 2. Preserved evaluation design

The 90-day union estimand, three rolling-origin folds, policy isolation, embargo,
17-feature registry, five driver groups, fit-only preprocessing, logistic and
XGBoost candidate specifications, policy-cluster resampling, canonical ordering,
numeric normalization, and protected-oracle authorization remain unchanged from
effective v3 protocol `2.2.0` unless this protocol explicitly changes them.

R2-15 selects exactly one candidate using the frozen selection role. It may not
tune candidates or use acceptance evidence.

## 3. Readiness

Before R2-16 result access, readiness MUST verify exact v4 substrate, qualification,
evaluation, feature, preprocessing, diagnostic, selected-candidate, authorization,
dependency, command, membership, and artifact digests; all 20 seeds and three
folds; matched signal/null streams; chronology, embargo, policy and episode
isolation; protected-concept exclusion; and absence of prior acceptance output.

Leakage, oracle contamination, future-block substitution, evidence tampering, or
final-holdout access yields `stop`. Other incompleteness yields `redesign` without
result-producing execution.

## 4. Acceptance families and rules

Execute signal and matched-null candidate discrimination, observable/conditional
oracle ordering, calibration sanity, 1,000-replicate policy-cluster intervals,
policy label shuffle, nested learning subsets, driver-group ablations, doubled
missingness, unknown-category arrival, moderate/stress drift, and temporal
worst-fold/spread evidence inherited from protocol `2.2.0`.

Primary recovery requires:

- at least 16/20 signal seeds with median-fold candidate AUC `>=0.65`;
- across-seed median candidate AUC `>=0.68`;
- at least 16/20 matched pairs with signal-minus-null AUC `>=0.10`;
- median AP lift `>=0.10` and median Brier skill `>0`;
- candidate AUC no greater than observable-oracle AUC plus `0.02` tolerance; and
- null logistic and XGBoost median AUC in `[0.45,0.55]`.

All interval, learning, ablation, robustness, and temporal rules retain their
effective protocol `2.2.0` thresholds and failure accounting. Missing required
families are failures; no seed/fold may be retried, replaced, or omitted.

## 5. Decision precedence

`stop` overrides `redesign`, which overrides `proceed`. Publish exactly one
mechanical decision. Only a merged `proceed` may resume P2-08. `redesign` or
`stop` preserves all pauses and creates a focused reviewed action.

## 6. Evidence and protection

The manifest is authoritative; report and decision are deterministic projections.
Commit aggregate evidence only. Do not commit histories, matrices, targets,
predictions, oracle sidecars, fitted executable objects, bootstrap samples,
shuffle maps, frailty, uniforms, or final-holdout material.

## 7. Claim boundary

Acceptance tests recovery of a predeclared fictional mechanism only. It does not
establish real-world performance, actuarial validity, causality, fairness,
operational utility, production readiness, or release readiness.
