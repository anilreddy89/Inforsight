# Phase 2R.16 Generation v6 Statistical Acceptance Execution Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Phase | R2-16 |
| Implementation issue | [#92](https://github.com/anilreddy89/Inforsight/issues/92) |
| Simulator contract | `6.0.0` |
| Evaluation contract | `6.0.0` |
| Candidate selection manifest | `6.0.0` |
| Acceptance protocol | `3.0.0` |
| Selected candidate | R2-15 frozen Logistic Regression ($L_2$, $C=1.0$, `liblinear`, seed `20260817`) |
| Seeds | `20271201` through `20271220` (20 reserved acceptance seed pairs) |
| Acceptance folds | `fold_1`, `fold_2`, `fold_3` |
| Final release holdout | `not_materialized` |
| Status | Frozen before R2-16 result-producing execution |

This contract implements the execution boundary assigned to R2-16. It binds the Generation v6 Bounded Sigmoid Substrate Contract `6.0.0` (ADR 0012), Generation v6 Evaluation Pipeline Implementation Contract `6.0.0` (PR #91, `8965c72`), and Acceptance Protocol `3.0.0` (`docs/modeling/phase-02r-13-v4-statistical-acceptance-protocol.md`). Historical evidence (v1 through v5, ADR 0001 through ADR 0012) remains immutable.

## Readiness state transition

The runner first verifies the complete 20-seed inventory and evaluates every readiness rule before any result-producing operation:
1. Verify SHA-256 digests of upstream artifacts (Substrate Contract `6.0.0`, Evaluation Contract `6.0.0`, Candidate Selection Manifest `6.0.0`, Feature Dictionary `6.0.0`, and Coefficient Registry `3.0.0`).
2. Verify that all 20 reserved acceptance seed pairs (`20271201..20271220`) are accounted for with no omissions, substitutions, or retries.
3. Verify fold structural support: $\ge 500$ eligible uncensored observations, $\ge 50$ positive and $\ge 50$ negative outcomes, all four billing frequencies (`monthly`, `quarterly`, `semiannual`, `annual`), and $0\%$ right-censoring in the evaluation window across all three folds.
4. Verify point-in-time feature lineage: $t_{\text{effective}} \le t_{\text{as\_of}}$ and $t_{\text{ingested}} \le t_{\text{as\_of}}$ for all 17 public feature definitions.
5. Verify clean-room isolation: zero leakage of simulator internals (frailty, oracle records, scenarios, identifiers), oracle sidecars isolated inside purpose-bound boundaries, and final holdout status `not_materialized`.

Leakage, oracle contamination, scoring authorization bypass, mismatched shared streams between signal and null pairs, selective omission, or final-holdout access yields `stop`. Other incomplete readiness yields `redesign` without generating acceptance metrics.

## Frozen execution

- Signal and matched-null corpora are generated for seeds `20271201..20271220`; the null variant alters only `signal_scale: 1.0 -> 0.0` while sharing all other primitive streams.
- Every valid signal replication evaluates all three frozen rolling-origin temporal acceptance folds (`fold_1`, `fold_2`, `fold_3`) under strict 90-day embargoes.
- Preprocessing standardizers and one-hot encoders are fitted strictly on designated fold training observations.
- The frozen Logistic Regression candidate is scored exclusively on authorized matrices carrying purpose-bound cryptographic digests.
- Placebo controls evaluate matched-null candidate discrimination and policy-level label shuffles.
- Policies serve as independent resampling clusters; all recurring observations for a sampled policy move together. Uncertainty intervals use 1,000 deterministic policy-cluster bootstrap replicates.
- Primary recovery requires across-seed median candidate AUC $\ge 0.68$, at least 16 of 20 seeds with median-fold AUC $\ge 0.65$, signal-minus-null AUC lift $\ge 0.10$ in $\ge 16/20$ seeds, median AP lift $\ge 0.10$, and median Brier skill $> 0.00$.
- Oracle ordering requires candidate AUC $\le$ observable-oracle AUC $+ 0.02$, with observable oracle $\le$ conditional oracle.
- Uncalibrated calibration sanity requires median slope in $[0.75, 1.25]$ and intercept in $[-0.20, 0.20]$.
- Nested learning curves evaluate 25%, 50%, 75%, and 100% subsets.
- Driver ablations evaluate all-designed-signal (drop $\ge 0.10$), strongest group (`recent_payment`), and designed-zero (`missingness`) groups.
- Robustness scenarios test default missingness, doubled missingness, unknown-category arrival, moderate drift, and stress drift.
- Temporal stability requires max-min fold spread $\le 0.10$ in $\ge 16/20$ seeds and median worst-fold AUC $\ge 0.62$.

## Rule and decision schema

Every rule record contains `rule_id`, `family`, `scope`, `inputs`, `comparator`, `threshold`, `observed`, `status`, `failure_classification`, and `evidence_digests`. Missing or non-finite required evidence fails.

The mechanical decision is derived with strict precedence:
1. `stop` if any rule classified as `stop` fails.
2. `redesign` if any other rule fails.
3. `proceed` if and only if 100% of required rules pass.

No waivers, post-hoc threshold softening, or manual overrides exist.

## Artifacts

```text
docs/experiments/phase-02r-16-v6-statistical-acceptance-manifest.json
docs/experiments/phase-02r-16-v6-statistical-acceptance-report.md
docs/experiments/phase-02r-16-v6-statistical-acceptance-decision.md
```

Generated via `python3 scripts/run_v6_statistical_acceptance.py --write` and validated via `--check`. Committed artifacts contain aggregate statistics, rule evaluations, and cryptographic digests only. Raw observations, matrices, row-level predictions, oracle sidecars, bootstrap replicates, and fitted objects are excluded.

## Claim and exit boundary

A `proceed` decision proves only that the Generation v6 bounded sigmoid substrate and feature pipeline recover the designed synthetic mechanism under Protocol `3.0.0`. It does not establish real-world predictive accuracy, actuarial validity, causality, fairness, or production readiness.

Only a pull request merged to `main` with a mechanical `proceed` decision authorizes Phase 2 work to resume (beginning with P2-08 Probability Calibration). A `redesign` or `stop` decision leaves Phase 2 paused and requires a dedicated remediation item.
