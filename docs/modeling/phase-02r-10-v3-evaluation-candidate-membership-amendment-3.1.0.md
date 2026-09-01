# Phase 2R.10 v3 Evaluation and Candidate-Membership Amendment 3.1.0

## Amendment metadata

| Field | Value |
| --- | --- |
| Evaluation split contract | `3.1.0` |
| Candidate-selection membership contract | `3.1.0` |
| Decision | [Issue #60 approved decision](https://github.com/anilreddy89/Inforsight/issues/60#issuecomment-5483754137), 2026-08-31 |
| Base substrate contract | `docs/modeling/phase-02r-08-v3-statistical-substrate-contract.md`, version `3.0.0` |
| Base R2-10 implementation contract | `docs/modeling/phase-02r-10-v3-evaluation-pipeline-contract.md`, version `3.0.0` |
| Acceptance protocol | `docs/modeling/phase-02r-10-statistical-acceptance-protocol-amendment-2.1.0.md`, version `2.1.0` |
| R2-09 corpus | Immutable artifact produced under its recorded `3.0.0` contracts and registry `1.0.0` |
| Final release holdout | `not_materialized` |
| Status | Approved; implementation and post-amendment structural evidence required before preprocessing or fitting |

Normative terms `MUST`, `MUST NOT`, `SHOULD`, and `MAY` have their usual requirements meaning. This document is a narrow, post-output amendment. It inherits the base contracts except where it explicitly changes selection membership and the downstream version lineage that identifies that membership.

## 1. Scope and precedence

Issue #60 approved one change: extend the selection cutoff interval by one complete calendar-quarter block. When this document conflicts with the selection interval or its downstream version in either base contract, this document controls. All other frozen `3.0.0` statistical choices remain in force, including:

- the statistical simulator, event, observation, and label contracts;
- random-stream registry `1.0.0`, seeds, namespaces, identities, role allocation, and scenarios;
- eligibility, recurrence, 90-day outcome episodes, dual-time visibility, and censoring rules;
- all three acceptance-fold memberships;
- public features, driver groups, preprocessing rules, candidate specifications, metrics, and tie breakers;
- scoring-authorization semantics other than the additional version bindings required here; and
- the final-release-holdout prohibition.

The existing `3.0.0` contract files remain normative historical records and MUST NOT be edited to make this amendment appear predeclared.

## 2. Amended selection membership

The only authorized candidate-selection membership is:

| Boundary | Inclusive value |
| --- | --- |
| Fit cutoffs | Through `2024-03-31T23:59:59Z` |
| Outcome embargo | No selection cutoff before `2024-07-01T00:00:00Z`; the full 90-day embargo remains mandatory |
| Selection cutoffs | `2024-07-01T00:00:00Z` through `2024-12-31T23:59:59Z` |
| Evaluation role | `selection` only |
| Row order | Canonical `(as_of, policy_id, observation_id)` |

The `2024-12-31T23:59:59Z` boundary was published before its post-proposal capacity check. It is now frozen. Implementations MUST NOT shorten it to the first date that crosses a support threshold, extend it again, change role allocation, replace a seed, force an outcome, or otherwise condition membership on the observed result.

Selection continues to require:

- at least 500 eligible uncensored observations;
- at least 50 positive and 50 negative observations;
- all four billing frequencies;
- at most 25% right censoring;
- strict cutoff chronology and the full 90-day outcome embargo;
- zero policy overlap across exclusive role families;
- zero outcome-episode overlap across governed memberships; and
- canonical caller-order normalization.

These are observation-level support requirements. The estimand remains an eligible policy-cutoff observation. Nothing in this amendment changes a row, label, role, outcome episode, or eligibility rule in the R2-09 corpus.

## 3. Acceptance folds are unchanged

The three acceptance folds remain exactly as defined under `3.0.0`:

| Fold | Fit through | Acceptance interval, inclusive |
| --- | --- | --- |
| `fold_1` | `2023-03-31T23:59:59Z` | `2023-07-01T00:00:00Z` through `2023-09-30T23:59:59Z` |
| `fold_2` | `2023-09-30T23:59:59Z` | `2024-01-01T00:00:00Z` through `2024-03-31T23:59:59Z` |
| `fold_3` | `2024-03-31T23:59:59Z` | `2024-07-01T00:00:00Z` through `2024-09-30T23:59:59Z` |

Post-amendment evidence MUST prove that the ordered acceptance membership and its digest for every fold are identical to the pre-amendment definition. The extended selection interval does not authorize acceptance-role preprocessing, fitting, prediction, metric computation, or candidate reselection.

## 4. R2-09 identity and compatibility boundary

The merged R2-09 histories, observations, protected sidecars, roles, seeds, stream identities, artifact identities, execution identities, and manifest are immutable. They remain governed by the contract versions recorded when they were generated.

In particular:

- implementations MUST NOT change `V3_ACCEPTANCE_PROTOCOL_VERSION` or any other R2-09 identity input to reproduce this downstream amendment;
- the R2-09 corpus MUST NOT be regenerated, relabeled, reassigned, or rewritten;
- evaluation `3.1.0` MUST consume the already validated R2-09 public observations; and
- each R2-10 split, preprocessing, candidate-selection, model-state, and scoring-authorization artifact MUST bind the immutable R2-09 artifact identity, evaluation contract `3.1.0`, and acceptance protocol `2.1.0` as separate fields.

This separation prevents a downstream membership amendment from falsely changing the identity of historical generated data.

## 5. Evidence preservation and new artifacts

The original selection failure is immutable pre-amendment `3.0.0` evidence. These files MUST retain their current bytes:

| Historical evidence | SHA-256 |
| --- | --- |
| `docs/experiments/phase-02r-10-v3-structural-support.json` | `611406e6eb3057217d305c3fd6b36832dc7e2b74017202db33874bd626ab1636` |
| `docs/experiments/phase-02r-10-v3-structural-support.md` | `f94250ec0acdb49e85cf185987465ca3dceccd40da1ab7f4cc8619239cf13f0a` |

Their 467 eligible observations, 80 positives, 387 negatives, and selection membership digest `74070d9ecd14e80c2379e365e542f72c8c4b6a31053d206a6d67f90a73a51122` remain a retained failure, not a result to overwrite or reinterpret.

The amended audit MUST publish distinct versioned artifacts:

```text
docs/experiments/phase-02r-10-v3-structural-support-3.1.0.json
docs/experiments/phase-02r-10-v3-structural-support-3.1.0.md
```

Those artifacts MUST identify the immutable pre-amendment evidence and its digests, bind the unchanged R2-09 artifact identity, and report every original structural check plus the amended interval and versions. Later R2-10 split, feature, preprocessing, diagnostic, candidate-selection, model-state, and authorization artifacts derived from selection membership MUST likewise bind `3.1.0` and `2.1.0`.

## 6. Required post-amendment gate

Before preprocessing, candidate fitting, prediction, or candidate selection resumes, one deterministic regeneration MUST prove:

- every `3.1.0` selection support rule passes;
- strict chronology and the full 90-day embargo pass;
- policy overlap and outcome-episode overlap remain zero;
- caller order is canonical;
- all acceptance folds are membership-identical to their pre-amendment definitions;
- no acceptance-role prediction or model metric exists;
- protected oracle sidecars remain inaccessible; and
- the final release holdout remains `not_materialized`, with no seed, identity, membership, artifact, or result.

If any structural gate fails, R2-10 MUST stop and return for another reviewed contract version. No additional ad hoc interval change is authorized.

## 7. Capacity and claim boundary

The read-only capacity check recorded in issue #60 found 854 eligible observations, including 149 positives and 705 negatives, all four billing frequencies, and zero censoring. This is review context, not a substitute for the required deterministic `3.1.0` evidence.

Those 854 observations represent 467 unique selection-role policies. The added rows are later, non-overlapping episodes for existing policies; they do not increase independent-policy capacity. Every amended report MUST disclose both observation and unique-policy counts and MUST NOT describe the interval extension as adding independent policies. Policy remains the resampling cluster wherever resampling applies.

Because selection now extends beyond the last acceptance-fold endpoint, this governed exercise is not a pure prospective forward backtest. Its permitted interpretation is limited to role-isolated synthetic mechanism recovery. It cannot establish real-world temporal generalization, operational readiness, actuarial validity, production performance, conservation efficacy, or release readiness.

## 8. Authorization and exit condition

Scoring authorization remains semantically `3.0.0`, but every authorization derived from the amended membership MUST include evaluation and candidate-membership contract `3.1.0` and protocol `2.1.0`. Authorization for selection MUST NOT authorize acceptance scoring.

This amendment authorizes only implementation and structural verification of the reviewed membership. Candidate work may resume only after the post-amendment gate passes. R2-11 remains blocked until all R2-10 artifacts are reviewed and merged, and the final release holdout remains `not_materialized`.
