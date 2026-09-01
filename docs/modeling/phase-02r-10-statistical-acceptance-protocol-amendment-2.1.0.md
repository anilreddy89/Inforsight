# Phase 2R.10 Statistical Acceptance Protocol Amendment 2.1.0

## Protocol metadata

| Field | Value |
| --- | --- |
| Protocol version | `2.1.0` |
| Decision | [Issue #60 approved decision](https://github.com/anilreddy89/Inforsight/issues/60#issuecomment-5483754137), 2026-08-31 |
| Inherits | `docs/modeling/phase-02r-08-statistical-acceptance-protocol.md`, version `2.0.0` |
| Evaluation amendment | `docs/modeling/phase-02r-10-v3-evaluation-candidate-membership-amendment-3.1.0.md` |
| R2-09 corpus | Immutable artifact produced under its recorded `3.0.0` contracts and registry `1.0.0` |
| Execution owner | R2-11 |
| Final release holdout | `not_materialized` |
| Status | Approved; execution remains blocked until amended R2-10 structural evidence and all R2-10 prerequisites pass |

Normative terms `MUST`, `MUST NOT`, `SHOULD`, and `MAY` have their usual requirements meaning. Protocol `2.1.0` inherits protocol `2.0.0` in full except for the selection-membership interval and corresponding version-lineage, readiness, evidence-preservation, and interpretation requirements below. The `2.0.0` file remains an immutable historical record.

## 1. Selection-membership amendment

Candidate selection under protocol `2.1.0` MUST use:

- fit cutoffs through `2024-03-31T23:59:59Z`;
- a full outcome embargo through `2024-06-30T23:59:59Z`;
- selection-role cutoffs from `2024-07-01T00:00:00Z` through `2024-12-31T23:59:59Z`, inclusive; and
- the unchanged minimums of 500 eligible uncensored observations, 50 positives, 50 negatives, all four billing frequencies, and at most 25% right censoring.

The two frozen candidates, fit membership, candidate specifications, preprocessing rules, ROC-AUC/Brier metrics, `1e-12` tolerances, logistic final tie breaker, and prohibition on acceptance-driven reselection remain unchanged. R2-11 MUST consume the candidate frozen by R2-10 and MUST NOT reselect using acceptance results.

The three acceptance folds and all replication seeds remain unchanged from protocol `2.0.0`.

## 2. Version and identity lineage

Every downstream R2-10 and R2-11 artifact MUST record, as distinct identities:

- the immutable R2-09 artifact and execution identities with the versions recorded at generation time;
- evaluation split and candidate-selection membership contract `3.1.0`; and
- acceptance protocol `2.1.0`.

Implementations MUST NOT change `V3_ACCEPTANCE_PROTOCOL_VERSION`, a corpus contract version, or another R2-09 identity input and then present the result as the merged R2-09 artifact. No R2-09 history, observation, oracle sidecar, role, seed, identity, or manifest may be regenerated or rewritten for this amendment.

## 3. Additional readiness requirements

Protocol `2.0.0` section 2 remains mandatory. Before any preprocessing, candidate fit, prediction, or R2-11 statistical execution, readiness MUST additionally prove:

- the versioned `3.1.0` selection membership passes every frozen support rule;
- chronology and the full 90-day embargo pass;
- policy and outcome-episode overlap remain zero;
- input rows use canonical `(as_of, policy_id, observation_id)` order;
- all three acceptance folds are ordered-membership and digest identical to the pre-amendment definitions;
- the pre-amendment `3.0.0` failure evidence retains its original bytes and digest;
- no acceptance-role prediction or model metric was produced during R2-10;
- protected oracle sidecars remained inaccessible; and
- the final release holdout remains `not_materialized` with no seed, identity, membership, or artifact.

Failure classification remains that of protocol `2.0.0`: prohibited exposure, manipulation, leakage, scoring bypass, or holdout access yields `stop`; other readiness failures yield `redesign`. A failed amended structural regeneration also returns R2-10 for another reviewed version and does not authorize a second ad hoc interval extension.

## 4. Evidence preservation

The original R2-10 structural-support JSON and Markdown are immutable `3.0.0` failure evidence. Protocol `2.1.0` MUST reference them and their digests without overwriting, deleting, or silently reinterpreting them.

New structural evidence MUST use the distinct `3.1.0` filenames declared by the evaluation amendment. Later candidate-selection and R2-11 evidence MUST identify both the retained failure and the passing amended evidence so the post-output change remains auditable.

## 5. Observation and policy accounting

Issue #60 records a post-declaration capacity check of 854 eligible selection observations, 149 positives, 705 negatives, all four billing frequencies, and zero censoring. These observations represent 467 unique selection-role policies because the additional rows are later non-overlapping episodes for existing policies.

The support threshold is defined in eligible policy-cutoff observations, so repeated non-overlapping episodes may satisfy it. Reports MUST nevertheless publish unique-policy counts and MUST NOT characterize the amendment as increasing independent-policy capacity. Policy remains the cluster for every protocol `2.0.0` bootstrap or other policy-clustered procedure inherited by `2.1.0`.

## 6. Interpretation boundary

Selection under `3.1.0` extends beyond the final acceptance-fold endpoint. Therefore protocol `2.1.0` is not a pure prospective forward backtest. Even a `proceed` decision may support only the bounded conclusion that the role-isolated synthetic experiment recovered its designed mechanism under the frozen protocol.

No R2-10 or R2-11 artifact may use this evidence to claim real-world temporal generalization, operational readiness, actuarial validity, production performance, conservation efficacy, or release readiness. Protocol execution still does not authorize calibration, operational threshold selection, explanations, or final-release-holdout access.

## 7. Unchanged protocol provisions

Except for the express amendments above, protocol `2.0.0` remains unchanged, including:

- seeds `20261001` through `20261020` and all signal/null pairing requirements;
- acceptance folds, candidates, metrics, policy-cluster bootstrap, and numeric rules;
- null and shuffle controls, signal/oracle recovery, calibration sanity, nested learning, driver ablations, robustness, and temporal stability;
- machine-readable rule records and `stop` / `redesign` / `proceed` precedence;
- artifact exclusions and the prohibition on raw matrices, row-level predictions, oracle sidecars, bootstrap samples, and executable fitted objects; and
- the amendment rule that inspected output may be changed only through a new reviewed version while original evidence remains immutable.

## 8. Exit condition

Protocol `2.1.0` execution remains R2-11 work. R2-11 may begin only after the `3.1.0` amendment, immutable-evidence checks, post-amendment structural evidence, selected candidate, and all other R2-10 prerequisites are reviewed and merged. The final release holdout MUST remain `not_materialized` throughout.
