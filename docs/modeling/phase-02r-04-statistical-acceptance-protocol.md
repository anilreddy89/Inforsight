# Phase 2R.04 Statistical Acceptance Protocol

## Protocol metadata

| Field | Value |
| --- | --- |
| Protocol version | `1.0.0` |
| Status | Predeclared; no v2 result inspected |
| Governing issue | [#42](https://github.com/anilreddy89/Inforsight/issues/42) |
| Simulator/observation contract | `phase-02r-04-v2-statistical-simulator-and-observation-contract.md` |
| Decision point | R2-07 |

## 1. Fixed replication design

R2-07 MUST evaluate 20 independently seeded signal-present corpora and 20 matching null-signal corpora. Seeds MUST be the integers `20260901` through `20260920`; the null corpus for a seed reuses cohort, exposure, missingness, delay, and latent-noise streams and sets observable-driver coefficients to zero.

Each signal corpus MUST use the three rolling-origin folds and exact date windows frozen in the simulator and observation contract. R2-06 implements those windows without changing them and MUST satisfy the contract's chronology and embargo checks. A replication is valid only when every evaluated fold satisfies the minimum counts in the contract.

No invalid replication may be silently dropped. If more than two of 20 signal replications are structurally invalid, the result is `redesign`. If one or two are invalid, all valid replications are reported and every aggregate rule still uses a denominator of 20, treating invalid replications as failures.

## 2. Frozen candidates and metrics

R2-06 MUST freeze one regularized logistic candidate and one shallow boosted-tree candidate before R2-07. Both use identical feature contracts, fold membership, and train-only preprocessing.

Primary metrics:

- ROC AUC for discrimination;
- average precision with fold prevalence reported beside it;
- Brier score for probability error; and
- calibration intercept and slope from a policy-cluster-aware evaluation procedure.

Uncertainty MUST use a policy-cluster bootstrap with 1,000 resamples per reported fold aggregate and percentile 95% intervals. Across-seed summaries MUST report median, interquartile range, minimum, maximum, and the count satisfying each gate. No observation-level bootstrap is permitted.

## 3. Structural gate

Every seed/fold MUST pass all of these before performance interpretation:

- exact configuration and artifact lineage verification;
- at least 500 eligible observations, 50 positives, and 50 negatives in each non-final evaluated role;
- every billing frequency present in every required role;
- right-censoring at or below 25%;
- strict chronology and both 90-day horizon embargoes;
- zero prohibited policy overlap and zero outcome-episode overlap;
- train-only preprocessing and unknown-category handling;
- recursive exclusion of oracle, latent, draw, scenario, identifier, outcome, post-cutoff, and role fields; and
- final holdout status `not_materialized`.

Any leakage, oracle-sidecar exposure, holdout materialization, or scoring-authorization bypass yields `stop`. Other structural failures yield `redesign`.

## 4. Negative controls

### Null-signal control

For both frozen candidates, at least 18 of 20 null replications MUST have a 95% bootstrap interval for ROC AUC containing `0.50`, and the across-seed median AUC MUST lie in `[0.47, 0.53]`. No candidate may have more than one null replication with AUC at or above `0.60`.

### Label-shuffle control

For each signal corpus, labels MUST be permuted once at policy level within fold using the protocol's domain-separated shuffle seed. At least 18 of 20 shuffled replications for each candidate MUST have a 95% AUC interval containing `0.50`; across-seed median shuffled AUC MUST lie in `[0.47, 0.53]`.

Failure of either negative control yields `stop` when there is evidence of leakage or control contamination; otherwise it yields `redesign`.

## 5. Signal-recovery gate

The selected candidate MUST satisfy all of the following on stable signal-present corpora:

- at least 16 of 20 replications have median-fold ROC AUC at or above `0.65`;
- across-seed median ROC AUC is at or above `0.68`;
- the lower bound of the across-policy bootstrap 95% interval around the pooled, seed-balanced AUC is above `0.60`;
- at least 16 of 20 replications outperform their matched null AUC by at least `0.10`;
- across-seed median average precision exceeds median fold prevalence by at least `0.10`; and
- across-seed median Brier score is at least 5% lower than the prevalence-only predictor's Brier score.

The `oracle_observable` score MUST outperform or equal the selected candidate's median AUC and Brier skill within a numerical tolerance of `1e-12`. The `oracle_conditional` score MUST be at least as strong as `oracle_observable` within the same tolerance. An apparent reversal outside tolerance yields `redesign` and requires an oracle, quadrature, or metric audit.

These thresholds validate recovery of the synthetic mechanism; they are not production targets.

## 6. Calibration gate

Using uncalibrated probabilities only, the selected candidate MUST have:

- across-seed median calibration slope in `[0.75, 1.25]`;
- across-seed median absolute calibration intercept at or below `0.20`; and
- at least 16 of 20 replications with positive Brier skill against prevalence.

This is a simulator/model sanity check, not P2-08 calibration fitting. No calibration mapping or operational threshold may be chosen in R2-07.

## 7. Learning behavior

For each seed, train at 25%, 50%, 75%, and 100% of eligible fit policies using deterministic policy-level subsampling. Report AUC and Brier intervals at every size.

Acceptance requires:

- the across-seed median AUC at 100% is no lower than the median at 25% by more than `0.02`;
- the median AUC interval width at 100% is at least 20% narrower than at 25%; and
- median Brier score at 100% is no worse than at 25% by more than `0.01`.

Failure yields `redesign` unless a documented metric ceiling explains only the monotonicity check while the uncertainty-width check passes.

## 8. Driver ablation

R2-06 MUST freeze source-feature groups for static, recent-payment, rolling-history, service/notice, and missingness features. R2-07 MUST ablate each group without refitting preprocessing categories from evaluation data.

Removing all designed-signal groups MUST reduce across-seed median AUC by at least `0.10`. Removing the predeclared strongest driver group MUST reduce median AUC or worsen median Brier score in the direction declared by the coefficient registry in at least 15 of 20 seeds. A group with zero configured effect MUST NOT be described as causally important regardless of fitted attribution.

Failure yields `redesign`.

## 9. Robustness gates

Relative to each seed's stable scenario:

| Scenario | Acceptance rule |
| --- | --- |
| Default missingness and delay | Median AUC degradation no more than `0.03`; positive Brier skill in at least 16 seeds |
| Doubled missingness stress | Median AUC degradation no more than `0.07`; no schema or preprocessing failures |
| Unknown-category arrival | All rows score through the frozen unknown path; median AUC degradation no more than `0.05` |
| Moderate temporal drift | Median AUC degradation no more than `0.05`; positive Brier skill in at least 15 seeds |
| Stress drift | Must complete without leakage or runtime failure; degradation is reported as a failure case and is not required to meet the moderate-drift threshold |

Any leakage or role-derived behavior yields `stop`. Failure of a numeric robustness rule yields `redesign`.

## 10. Temporal stability

Across the three rolling-origin folds:

- at least 16 of 20 seeds MUST have a maximum-minus-minimum AUC no greater than `0.10` under `stable`;
- no stable fold may lack a billing frequency or required outcome class; and
- the across-seed median worst-fold AUC MUST be at least `0.62`.

Failure yields `redesign`.

## 11. Decision aggregation

R2-07 records exactly one decision:

- `proceed`: every structural, negative-control, signal, calibration, learning, ablation, robustness, and temporal rule passes with no prohibited access;
- `redesign`: no stop condition occurred, but one or more required rules failed or the protocol could not be executed as written; or
- `stop`: leakage, oracle exposure, unauthorized scoring, final-holdout materialization/access, falsified negative controls indicating contamination, selective seed omission, or evidence manipulation occurred.

There is no discretionary override from a failed required rule to `proceed`. P2-08 and P2-09 resume only after a merged `proceed` decision.

## 12. Artifacts and reporting

R2-07 MUST publish a deterministic manifest, human-readable report, and decision note containing:

- every seed and fold, including invalid or failed runs;
- exact configs, contract versions, dependency versions, and upstream digests;
- per-seed/fold counts, metrics, intervals, controls, ablations, and stresses;
- each rule's computed value and pass/fail result;
- failure cases without selective omission;
- final-holdout status;
- limitation dispositions for `LIM-002-001` and `LIM-002-002`; and
- reproduction commands.

Raw observation matrices, oracle sidecars, and executable fitted objects MUST NOT be committed.

## 13. Amendment rule

Before any v2 output is inspected, issue #42 may amend this protocol through review. After inspection, changing a seed, fold, metric, interval method, threshold, tolerance, stress magnitude, allowed failure count, or aggregation rule requires a new protocol version and the current gate decision `redesign`. The original protocol and results remain in the audit trail.
