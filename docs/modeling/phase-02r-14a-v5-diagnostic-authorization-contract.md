# Phase 2R.14A v5 Diagnostic Authorization Contract

## 1. Authority and status

| Field | Value |
| --- | --- |
| Phase | R2-14A |
| Issue | [#76](https://github.com/anilreddy89/Inforsight/issues/76) |
| Contract version | `1.0.0` |
| Status | Proposed; result-producing execution remains blocked until merge |
| Governing decision | ADR 0008 |
| Trigger evidence | R2-14 decision `redesign`, protocol `3.0.0`, merge `4b234bf` |
| Final holdout | `not_materialized` |

This contract authorizes only a later R2-14B execution against the exact inventory
below. R2-14A runs no diagnostic and changes no simulator, feature, candidate,
estimand, fold, metric, threshold, or stochastic mechanism.

Normative terms `MUST`, `MUST NOT`, and `SHALL` are fail-closed requirements.

## 2. Frozen information domains

| Domain | Seeds | Permitted use |
| --- | --- | --- |
| `v3_spent_acceptance` | `20261001..20261020` | Cite committed aggregates only |
| `v4_spent_qualification` | `20271101..20271120` | Cite committed aggregates only |
| `v4_reserved_acceptance` | `20271201..20271220` | No access, assignment, generation, or scoring |
| `v5_diagnostic_development` | `20280101..20280120` | R2-14B inventory only |

Ranges are inclusive ascending integer sequences of exactly 20 seeds. Every pair
MUST be disjoint. Seeds MUST NOT be retried, replaced, omitted, or reassigned
because of output. R2-14A materializes no domain. Final-holdout identity and seed
remain undefined and MUST NOT be inferred from these ranges.

## 3. Immutable inputs

- R2-14 merge `4b234bf` and qualification manifest, report, and decision.
- V4 substrate `4.0.0`, coefficient and stream registries `2.0.0`, and protocol
  `3.0.0` as historical evidence.
- The 90-day union estimand, three rolling-origin folds, policy ownership,
  dual-time visibility, matched streams, protected oracle, and frozen v4 gates.

R2-14B may diagnose these inputs but MUST NOT amend or overwrite them. A proposed
successor requires a new ADR, substrate version, registry version, and protocol.

## 4. Hypothesis and diagnostic registry

Every output MUST carry one of these IDs; unregistered exploration is prohibited.

| ID | Hypothesis | Required diagnostics |
| --- | --- | --- |
| `H1_LOG_HAZARD_SPREAD` | Observable public score spread is insufficient | `D1_LINEAR_PREDICTOR_DISTRIBUTION`, `D2_TERM_CONTRIBUTION_COVARIANCE`, `D3_SIGNAL_VARIANCE_RATIO` |
| `H2_HORIZON_ATTENUATION` | Survival or competing risks attenuate monthly signal | `D4_CUMULATIVE_INCIDENCE_DECOMPOSITION`, `D5_CAUSE_UNION_ORDERING`, `D6_ATTENUATION_BY_FOLD` |
| `H3_PROBABILITY_SCALE` | Realized prevalence limits probability quality | `D7_ORACLE_METRIC_DECOMPOSITION`, `D8_RELIABILITY_SUMMARY`, `D9_ORACLE_ORDERING` |
| `H4_REFERENCE_SPECIFICATION` | Governed reference form is misspecified | `D10_EXACT_SCORE_RECOVERY`, `D11_EXACT_HAZARD_REFERENCE`, `D12_CURRENT_REFERENCE_COMPARISON` |
| `H5_HAZARD_TAIL` | Rare joint configurations breach the hazard ceiling | `D13_HAZARD_QUANTILES`, `D14_EXCEEDANCE_ATTRIBUTION`, `D15_TAIL_SUPPORT` |
| `H6_DESIGN_FEASIBILITY` | Recovery and hazard targets may be incompatible | `D16_FROZEN_FEASIBILITY_SURFACE`, `D17_SIMULTANEOUS_CONSTRAINT_STATUS` |

All 17 diagnostics are required. Missing, invalid, suppressed-at-required-scope, or
non-finite evidence yields `unresolved`; selective rerun yields `stop`.

## 5. Frozen execution and algorithms

R2-14B MUST use all 20 v5 development seeds, matched signal/null scenarios, and
all three v4 fold definitions. Missing units remain in denominators.

For continuous values, a distribution means count, finite count, mean, population
standard deviation, minimum, and quantiles at `0.01,0.05,0.25,0.50,0.75,0.95,0.99`,
computed by NumPy linear quantiles in canonical row order. Covariance uses
population normalization (`ddof=0`). Variance ratios divide public-score variance
by baseline-plus-frailty variance; a zero denominator is invalid.

Cumulative-incidence decomposition MUST use the exact registered monthly lapse and
surrender hazards, survival recursion, and three-month union probability from
contract `4.0.0`. D5 reports cause-specific and union ROC AUC on identical rows.
D6 reports monthly-to-union AUC change and maximum-minus-minimum fold spread.

D7 inherits protocol `3.0.0` ROC AUC, AP lift, Brier score, and Brier skill
definitions. D8 uses ten fixed probability bins `[0,.1),...,[.9,1]`, reporting
count, unique-policy count, mean prediction, and outcome rate. D9 compares
conditional and observable oracle AUC and requires conditional AUC not lower than
observable AUC beyond `1e-12`.

D10 ranks the exact registered public score. D11 uses the exact discrete-time
cause-specific hazard link, competing-risk normalization, and 90-day union
aggregation. D12 uses the unchanged v4 governed reference. All references use
identical memberships; convergence and prediction variance are mandatory.

D13 reports the frozen distribution summary for lapse, surrender, and total
monthly hazard. D14 counts total-hazard values `>=0.20` and reports aggregate
registered-term contributions for exceedances versus non-exceedances. D15 reports
unique-policy support and joint registered-term frequencies, suppressing small
cells.

## 6. Frozen feasibility surface

D16 evaluates this complete Cartesian grid in lexicographic order:

```text
public_coefficient_scale = [1.0, 1.5, 2.0, 2.5, 3.0]
frailty_standard_deviation = [0.00, 0.10, 0.20, 0.30]
lapse_intercept_delta = [-0.50, -0.25, 0.00, 0.25]
surrender_intercept_delta = [-0.50, -0.25, 0.00, 0.25]
```

The base is frozen v4. The grid contains exactly 320 cells and MUST NOT expand,
refine, stop early, or select a winning point after output. Each cell uses all 20
development seeds and three folds with common primitive streams.

D17 reports `feasible` only if at least one cell simultaneously meets every
unchanged v4 recovery, AP-lift, positive-Brier-skill, reference-recovery, driver,
null, parity, structural, and `<0.20` hazard rule. It reports `infeasible` only if
all 320 valid cells fail simultaneous constraints, otherwise `unresolved`.
Feasibility does not authorize choosing any cell as v5.

## 7. Protected execution boundary

Each diagnostic authorization MUST bind domain, seed, scenario, fold, ordered
membership digest, input artifact digests, target digest, mechanism/reference
identity, contract version, diagnostic ID, and permitted aggregate schema.

Oracle values, frailty, uniforms, mechanism terms, matrices, row targets,
predictions, fitted objects, and feasibility rows are temporary protected
intermediates. They MUST NOT enter ordinary feature or candidate paths and MUST be
deleted after aggregate digests are bound. Cross-purpose reuse, substitution,
reordering, stale authorization, or missing digests MUST fail before computation.

Committed output is aggregate only. Any cell with fewer than 10 unique policies
MUST be replaced by a suppression record containing count category and reason, not
values.

## 8. Readiness and decision precedence

Before results, R2-14B MUST verify exact contract, code, dependency, command, seed,
scenario, fold, membership, upstream artifact, metric, grid, and output-schema
identities; complete inventory; domain disjointness; absence of reserved acceptance
and holdout material; canonical ordering; protected-concept exclusion; and absence
of preexisting partial results.

Leakage, protected contamination, domain substitution, reserved-acceptance access,
holdout access, historical mutation, selective execution, evidence tampering, or
grid drift yields `stop`. Other incomplete readiness yields `redesign_required`
and produces no result.

Each hypothesis receives `supported`, `rejected`, or `unresolved`. `stop` overrides
`redesign_required`, which overrides `diagnostics_complete`.

## 9. Causal response table

| Finding | Only permitted proposal |
| --- | --- |
| H1 supported | Versioned public-score, frailty, baseline, incidence, or event-support redesign constrained by H5/H6 |
| H2 supported | Versioned competing-risk, horizon, estimand, or mechanism redesign with interpretation impact |
| H3 supported | Versioned probability mechanism redesign; no post-hoc calibration claim |
| H4 supported while oracle is recoverable | Correct the diagnostic/reference specification before candidate interpretation |
| H5 supported | Versioned tail control preserving the frozen hazard ceiling |
| H6 feasible | Propose the smallest independently justified design, not the best grid point |
| H6 infeasible | `stop` or separately review estimand/threshold foundations |
| Mixed, invalid, or unresolved | Reviewed diagnostic amendment or `stop`; no guessed design |

A proposal never authorizes implementation. R2-14C requires a later accepted ADR
and separately versioned substrate and protocol.

## 10. Evidence schema and prohibited work

R2-14B is expected to publish deterministic projections at:

```text
docs/experiments/phase-02r-14b-v5-redesign-diagnostic-manifest.json
docs/experiments/phase-02r-14b-v5-redesign-diagnostic-report.md
docs/experiments/phase-02r-14b-v5-hypothesis-disposition.md
```

The manifest records identities, planned and executed inventory, failures,
suppression, aggregate evidence, dispositions, permitted response, protected
cleanup, `reserved_acceptance: not_materialized`, and
`final_holdout: not_materialized`. Reports are generated from the manifest.

R2-14A and this contract produce no corpus, fit, prediction, oracle metric,
feasibility result, or acceptance result. R2-15/R2-16 and P2-08 through P2-12
remain blocked.

## 11. Verification

`python3 scripts/check_r2_14a_diagnostic_contract.py` MUST validate required
documents, issue and merge identities, versions, exact seed domains and
disjointness, the six hypothesis IDs, all 17 diagnostic IDs, the 320-cell frozen
grid, evidence paths, causal responses, prohibited-result language, reserved
acceptance absence, and final-holdout status. It reads text only and MUST NOT
import or call simulator, feature, modeling, oracle, or evaluation runtime code.

