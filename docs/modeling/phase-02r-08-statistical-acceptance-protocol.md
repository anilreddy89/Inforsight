# Phase 2R.08 Statistical Acceptance Protocol

## Protocol metadata

| Field | Value |
| --- | --- |
| Protocol version | `2.0.0` |
| Status | Proposed through issue #53; no v3 output inspected |
| Governing ADR | `docs/adr/0005-replace-v2-with-a-dual-time-matched-control-v3-statistical-substrate.md` |
| Substrate contract | `docs/modeling/phase-02r-08-v3-statistical-substrate-contract.md` |
| Execution owner | R2-11 |
| Preserves | Protocol `1.0.0` and R2-07 decision `stop` |
| Final release holdout | `not_materialized` |

## 1. Fixed replication design

R2-11 MUST account for all signal/null pairs using seeds `20261001` through `20261020`. Each pair shares the v3 `stream_set_id`; null changes only `signal_scale` from `1` to `0`. Each signal corpus uses all three frozen rolling-origin folds.

No seed or fold may be retried, replaced, or omitted. More than two structurally invalid signal replications yields `redesign`; one or two remain failures with denominator 20. A stop condition takes precedence.

## 2. Readiness-before-results gate

Before any model fit or prediction, every seed/fold MUST prove:

- exact configuration, identity, contract, command, and dependency lineage;
- event-first dual-time visibility and per-feature event lineage;
- exact equality of unaffected primitive draws and common event fields across paired variants;
- valid atomic-intervention allowlists;
- all roles/frequencies/classes and at least 500 eligible uncensored rows, 50 positives, and 50 negatives;
- right censoring at or below 25%;
- chronology, both 90-day embargoes, zero policy overlap, and zero episode overlap;
- recursive feature exclusions, fit-only preprocessing, and frozen unknown handling;
- two frozen candidates, one preselected candidate, five driver groups, strongest and zero-effect groups, and canonical coefficients;
- executable shuffle, bootstrap, learning-subset, ablation, and stress derivations; and
- final holdout status `not_materialized` with no seed, membership, or artifacts.

Leakage, oracle exposure, holdout access, scoring bypass, mismatched supposedly shared streams, or evidence manipulation yields `stop`. Other readiness failures yield `redesign`. Failure produces only readiness evidence; no model, prediction, bootstrap, or metric may be generated.

## 3. Frozen candidates and selection

R2-10 fits the unchanged R2-06 logistic and boosted specifications on identical governed fit rows and evaluates identical selection rows. Select higher ROC AUC; within `1e-12`, lower Brier; within `1e-12` again, logistic. Selection evidence and all digests freeze before acceptance access. R2-11 MUST NOT reselect by acceptance results.

## 4. Metrics and policy-cluster bootstrap

Metrics are ROC AUC, average precision with prevalence, Brier score, prevalence-only Brier skill, and uncalibrated calibration intercept/slope.

For seed `s`, fold `f`, metric `m`, and replicate `b=0..999`, sort unique policy IDs lexicographically. Draw `N` indices with replacement using domain `bootstrap` keys `(s,f,m,b,draw_index)`, mapping `floor(u*N)` to the sorted list. Include every row of each sampled policy with multiplicity. A replicate lacking either class or producing non-finite output is invalid and retained. Fewer than 950 valid replicates yields `redesign`.

Sort valid metric values ascending. The percentile 95% interval uses zero-based nearest-rank indices `floor(0.025*(B-1))` and `ceil(0.975*(B-1))`. Runtime calculations use full precision.

Across-seed summaries report median, Tukey-hinge IQR, minimum, maximum, and pass count. Median of an even count is the mean of the two central values. Pooled seed-balanced AUC gives every seed total weight `1/20`, each policy equal weight within seed, and bootstraps policies independently within every seed using the same 1,000 replicate indices.

## 5. Negative controls

For both candidates, at least 18 of 20 null replications MUST have a 95% AUC interval containing `0.50`; median AUC MUST be `[0.47,0.53]`; at most one may have AUC `>=0.60`.

For label shuffle, assign each policy the label vector of another policy by sorting policies by `(label_shuffle uniform, policy_id)` and cyclically rotating the sorted vectors by `1 + floor(u_seed*(N-1))`. Preserve each donor policy's repeated-row label sequence ordered by cutoff; differing sequence lengths are mapped by deterministic cyclic indexing. Perform once per seed/fold and use the same assignment for both candidates. At least 18 of 20 intervals per candidate MUST contain `0.50`, and median shuffled AUC MUST be `[0.47,0.53]`.

Contamination or leakage yields `stop`; numeric failure yields `redesign`.

## 6. Signal and oracle recovery

The preselected candidate MUST satisfy unchanged protocol `1.0.0` thresholds:

- at least 16/20 median-fold AUCs `>=0.65`;
- median AUC `>=0.68`;
- pooled seed-balanced AUC 95% lower bound `>0.60`;
- at least 16/20 matched-null AUC improvements `>=0.10`;
- median average-precision lift over fold prevalence `>=0.10`; and
- median Brier at least 5% below prevalence-only Brier.

On identical membership, `oracle_observable` MUST equal or outperform selected-candidate median AUC and Brier skill within `1e-12`; `oracle_conditional` MUST equal or outperform `oracle_observable`. Reversal yields `redesign` and an oracle/metric audit.

## 7. Calibration sanity

Using uncalibrated probabilities only, median slope MUST be `[0.75,1.25]`, absolute median intercept MUST be `<=0.20`, and at least 16/20 replications MUST have positive Brier skill. No calibration mapping or threshold is fit.

## 8. Nested learning behavior

For each seed/fold, sort fit policies by `(learning_order uniform, policy_id)`. Let `N` be policy count and subset sizes be `ceil(p*N)` for `p={0.25,0.50,0.75,1.00}`. Each prefix is nested. If a subset lacks a class or structural support it fails; it is not enlarged selectively. Refit preprocessing and the selected specification independently per subset and hold acceptance membership fixed.

Median AUC at 100% may be no more than `0.02` below 25%; median AUC interval width at 100% MUST be at least 20% narrower; median Brier at 100% may be no more than `0.01` worse. Only the AUC monotonicity rule may be marked `metric_ceiling` when 25% median AUC is at least `0.90`, the 100% result remains within `0.02`, and uncertainty-width passes.

## 9. Driver ablations

Use the five exact groups in the substrate contract. Derived matrices zero all standardized numeric columns and all one-hot columns of an ablated group after frozen preprocessing; no categories are refit. The all-designed-signal ablation removes `static`, `recent_payment`, `rolling_history`, and `service_notice`. The strongest ablation removes `recent_payment`. `missingness` is the zero-effect negative control.

All-signal removal MUST reduce median AUC by `>=0.10`. Strongest-group removal MUST reduce AUC or worsen Brier in at least 15/20 seeds. Missingness findings are reported but MUST NOT be described causally. Numeric failure yields `redesign`.

## 10. Atomic robustness gates

Every scenario MUST first pass stream/event equality against its allowlist. Metrics compare paired seeds on the same common eligible identities; membership divergence is reported and MUST NOT be hidden by forced survival.

| Scenario | Rule |
| --- | --- |
| Default missingness/delay | Median AUC degradation `<=0.03`; positive Brier skill in at least 16 seeds |
| Doubled missingness | Median AUC degradation `<=0.07`; no schema/preprocessing failure |
| Unknown-category arrival | Every row uses frozen unknown path; median degradation `<=0.05`; width unchanged |
| Moderate drift | Median degradation `<=0.05`; positive Brier skill in at least 15 seeds |
| Stress drift | Completes without leakage/runtime failure; degradation reported without moderate threshold |

Unauthorized field change, leakage, or role-derived behavior yields `stop`; numeric failure yields `redesign`.

## 11. Temporal stability

At least 16/20 stable seeds MUST have max-minus-min fold AUC `<=0.10`; no stable fold may lack a frequency or required class; median worst-fold AUC MUST be `>=0.62`. Failure yields `redesign`.

## 12. Machine-readable evidence and decision aggregation

Every rule record MUST contain `rule_id`, `scope`, `inputs`, `comparator`, `threshold`, `observed`, `status`, `failure_classification`, and evidence digests. Missing or non-finite required evidence is failure.

Decision precedence is:

1. any failed `stop` rule -> `stop`;
2. otherwise any failed/incomplete `redesign` rule -> `redesign`;
3. otherwise every required rule passed -> `proceed`.

No waiver or discretionary override exists. Only a merged R2-11 `proceed` decision may resume P2-08/P2-09.

## 13. Artifacts and exclusions

R2-11 publishes deterministic v3 manifest, report, and decision artifacts containing every seed/fold, identities, versions, counts, metrics, intervals, invalid replicates, controls, learning, ablations, robustness, rules, failures, limitation dispositions, commands, and final-holdout status.

Raw matrices, row-level predictions, oracle sidecars, bootstrap samples, and executable fitted objects MUST NOT be committed. The final release holdout MUST remain `not_materialized`.

## 14. Amendment rule

Before any v3 output is inspected, issue #53 may amend protocol `2.0.0` through review. After inspection, changing any seed, fold, method, candidate, selection rule, metric, interval, threshold, tolerance, stress, allowance, or aggregation requires a new reviewed protocol version. Original evidence remains immutable; failed seeds may not be replaced.

## 15. Rule registry

| Family | Required rules | Failure |
| --- | --- | --- |
| Readiness | lineage, dual time, matched streams, atomic variants, support, chronology, isolation, features, preprocessing, registries, authorization, holdout absence | `stop` for prohibited exposure/manipulation; otherwise `redesign` |
| Null and shuffle | interval, median, high-AUC counts | `stop` if contaminated; otherwise `redesign` |
| Signal/oracle | six recovery rules and oracle ordering | `redesign` |
| Calibration | slope, intercept, Brier skill | `redesign` |
| Learning | AUC, width, Brier | `redesign` |
| Ablation | all-signal and strongest direction | `redesign` |
| Robustness | five paired scenarios | `stop` for boundary violation; otherwise `redesign` |
| Temporal | range, support, worst fold | `redesign` |
