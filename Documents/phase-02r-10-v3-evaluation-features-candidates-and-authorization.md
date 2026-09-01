# Phase 2R.10 — v3 Evaluation, Features, Candidates, Selection, and Authorization

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 2R — Modeling Foundation Remediation Gate |
| Sequence | R2-10 |
| Change tracker ID | `R2-10` |
| GitHub issue | [#59](https://github.com/anilreddy89/Inforsight/issues/59) |
| Issue title | `[Implementation] R2-10: Rebuild v3 evaluation, features, candidates, selection, and authorization` |
| Recommended branch | `feat/59-r2-10-v3-evaluation-pipeline` |
| Pull request | TBD |
| Status | In progress since 2026-08-30; amended structural support passes, while diagnostic disposition and candidate authorization remain under review |
| Milestone | `v0.2.0-risk-model` |
| Priority | Release blocking |
| Classification | Modeling-foundation remediation / versioned capability |
| Strict predecessor | R2-09, completed through issue #56 and PR #57, merge commit `89c2291` |
| Blocks | R2-11 — execute statistical acceptance protocol `2.1.0` |
| Governing decision | ADR 0005 and [issue #60](https://github.com/anilreddy89/Inforsight/issues/60) |
| Governing substrate | Historical contract `3.0.0`; remediated simulator contract `3.1.0` through issue #61 |
| Governing evaluation amendment | Issue #60 amendment `3.1.0`, superseded for authoritative evidence by remediation-bound version `3.2.0` |
| Governing acceptance protocol | Base `2.0.0`, issue-#60 amendment `2.1.0`, effective remediation-bound version `2.2.0` |
| Governing corpus | Separately versioned v3.1 remediation; R2-09 v3.0 corpus remains immutable historical evidence |
| Final holdout | Must remain `not_materialized` throughout R2-10 |
| Last reviewed | 2026-08-31 |

Initial `3.0.0` implementation evidence remains immutable: the default corpus passes all three frozen acceptance-fold structural checks, while the original selection interval fails closed with 467 eligible observations (80 positive, 387 negative, zero right-censored, and all four billing frequencies represented) against the 500-row minimum. Issue #60 approved evaluation/candidate-membership amendment `3.1.0` and protocol `2.1.0`, extending selection through `2024-12-31T23:59:59Z` without changing a generated row, role, seed, threshold, or R2-09 identity. Distinct post-amendment structural evidence now passes with 854 eligible observations from 467 unique policies; later diagnostic and candidate artifacts remain non-final pending disposition review and do not yet authorize a selected candidate.

## Objective

Build the deterministic, separately versioned v3 evaluation boundary between the merged R2-09 corpus and R2-11. R2-10 must construct governed chronological folds, a closed public feature dictionary and matrix pipeline, fit-only preprocessing, leakage-aware diagnostics, the two frozen model candidates, deterministic candidate selection, digest-bound scoring authorization, and reproducible non-final readiness evidence.

R2-10 freezes the selected candidate and every input R2-11 needs before acceptance-role modeling access. It may inspect aggregate acceptance class counts only for the predeclared structural support gate. It does not execute protocol `2.2.0`, use acceptance rows for preprocessing, fitting, selection, prediction, or metrics, calibrate probabilities, choose operational thresholds, publish explanations, close limitations, materialize a final release holdout, or make a performance claim.

## Why this work is next

R2-07 stopped before fitting because the v2 feature boundary admitted post-cutoff-ingested behavior. R2-08 approved the event-first dual-time v3 replacement, matched controls, enlarged support, frozen driver groups, deterministic selection, and authorization contract. R2-09 then implemented the approved v3 corpus and recurring observations and merged as `89c2291` without producing a model or final-holdout result.

R2-10 is therefore the next strict increment. R2-11 cannot run readiness or statistical acceptance until the split, feature, preprocessing, candidate, selection, and authorization artifacts are frozen and merged.

## Immutable boundaries

- V1 and v2 source, contracts, artifacts, reports, and the R2-07 `stop` decision remain immutable historical evidence.
- Every new public contract, runtime path, command, and artifact must be explicitly v3-namespaced and preserve the immutable R2-09 `3.0.0` evidence separately from simulator contract `3.1.0`, evaluation/candidate-membership contract `3.2.0`, and protocol `2.2.0`.
- R2-09 histories, observations, sidecars, roles, seeds, identities, and manifests remain governed by their recorded versions. `V3_ACCEPTANCE_PROTOCOL_VERSION` and other R2-09 identity inputs must not change for the downstream amendment.
- Only validated R2-09 public observations may enter evaluation and feature construction. Oracle sidecars, latent values, protected draws, generator working state, roles, scenarios, identifiers, future state, and labels are prohibited model inputs.
- Feature visibility requires both `effective_at <= as_of` and `ingested_at <= as_of`; feature lineage and visible-event digests remain authoritative.
- Roles were assigned before risk draws and are mutually exclusive. R2-10 must not reassign policies, replace seeds, force outcomes, weaken chronology, or repair support based on observed results.
- Candidate specifications, metrics, and deterministic tie-breaking are frozen by contract `3.0.0`; no tuning, retry, or candidate proliferation is permitted.
- Acceptance-role membership and aggregate class counts may be checked only for structural support; row-level labels must remain unavailable to preprocessing, diagnostics, fitting, selection, and scoring, while acceptance predictions and metrics remain R2-11 work.
- The amended Jul–Dec selection capacity represents repeated non-overlapping observations from 467 unique policies, not additional independent policies. Policy remains the resampling cluster, and results are limited to role-isolated synthetic mechanism recovery rather than prospective real-world validation.
- The final release holdout remains `not_materialized`: no seed, identity, membership, distribution, row, feature, fitted transform, prediction, or metric may be created or inspected.

## Required changes

### 1. Publish the v3 evaluation implementation contract

Add a versioned R2-10 contract that freezes:

- split and fold membership rules, chronology, both embargo boundaries, row ordering, and support checks;
- the complete public feature dictionary, driver-group mapping, missingness handling, and recursive prohibited-concept registry;
- fold-local and purpose-local preprocessing ownership and safe fitted-state serialization;
- the inherited logistic and boosted candidate specifications and dependency pins;
- selection membership, metrics, numeric normalization, and the exact `1e-12` tie-break sequence;
- scoring purposes, authorization fields, digest formulas, failure behavior, and ordinary-inference separation; and
- committed versus regenerated artifacts, commands, versions, and compatibility boundaries.

The implementation contract must conform to the already approved substrate contract `3.0.0`; it may close implementation detail but must not change a frozen statistical choice after v3 output inspection.

Issue #60 is the reviewed exception required by that amendment rule. It changes only downstream evaluation and candidate-selection membership to `3.1.0` and the corresponding acceptance protocol to `2.1.0`; it does not amend the R2-09 corpus contracts or rewrite the original `3.0.0` implementation contract.

### 2. Build governed roles, folds, and embargo evidence

Consume validated, uncensored, model-eligible public v3 observations and preserve the preassigned role. Implement the three frozen acceptance folds:

| Fold | Fit cutoffs | Acceptance cutoffs |
| --- | --- | --- |
| `fold_1` | Through `2023-03-31T23:59:59Z` | `2023-07-01T00:00:00Z` through `2023-09-30T23:59:59Z` |
| `fold_2` | Through `2023-09-30T23:59:59Z` | `2024-01-01T00:00:00Z` through `2024-03-31T23:59:59Z` |
| `fold_3` | Through `2024-03-31T23:59:59Z` | `2024-07-01T00:00:00Z` through `2024-09-30T23:59:59Z` |

The three acceptance folds remain byte/membership identical under amendment `3.1.0`. Candidate selection uses fit cutoffs through `2024-03-31T23:59:59Z` and selection-role cutoffs from `2024-07-01T00:00:00Z` through `2024-12-31T23:59:59Z`, inclusive. The added quarter is frozen; failure of the amended structural gate must return for another reviewed version rather than another ad hoc extension.

Every boundary must prove:

- strict cutoff chronology and a full 90-day outcome embargo;
- zero policy overlap across exclusive role families and zero outcome-episode overlap across governed memberships;
- deterministic row normalization by `(as_of, policy_id, observation_id)`;
- exclusion of right-censored rows from fitting and metrics while retaining structural accounting; and
- all four billing frequencies, at least 500 eligible uncensored observations, at least 50 positives, at least 50 negatives, and no more than 25% right censoring in every contract-required role/fold.

Structural support failure must stop artifact construction. It must not trigger role reassignment, relaxed chronology, seed replacement, or outcome forcing.

### 3. Implement the closed v3 feature dictionary and extraction boundary

Create a machine-readable v3 feature dictionary covering the approved groups exactly once:

| Group | Approved content | Designed status |
| --- | --- | --- |
| `static` | tenure, log premium, product, billing frequency | Nonzero |
| `recent_payment` | most recent due-to-paid delay; 90-day failure, retry, recovery, and arrears values | Nonzero; strongest group |
| `rolling_history` | 365-day on-time rate and payment count | Nonzero |
| `service_notice` | 90-day notice/contact counts and frozen categories | Nonzero |
| `missingness` | approved visible missingness indicators | Zero effect in stable signal scenario |

For each feature, record its source owner, visibility rule, transform/type, empty-history behavior, missingness behavior, preprocessing decision, output names, and driver group. Extraction must validate observation identity, artifact identity, visible-event digest, and per-value lineage before constructing a row.

Recursively reject direct or nested oracle values, frailty, primitive draws, outcome uniforms, outcome/label provenance, scenario or role tokens, policy/event/observation/episode identifiers, future or scheduled state, generator working variables, and unregistered fields. Valid post-fit categories must use the frozen unknown path without changing width.

### 4. Implement fit-only preprocessing

- Fit numeric statistics, categorical vocabularies, and allowed missingness handling only on the governed fit membership for the applicable fold or purpose.
- Freeze output feature names, order, width, membership, row order, and fitted-state digest.
- Serialize explicit non-executable fitted state bound to corpus, split, feature dictionary, artifact identity, and contract versions.
- Prove held-out, selection, calibration, non-final evaluation, and acceptance rows cannot change learned values or schema.
- Reject substitution, reordering, cross-fold reuse, refitting, category-vocabulary expansion, width drift, non-finite values, and inconsistent provenance.

### 5. Run leakage-aware feature diagnostics

Run deterministic, authorized non-final diagnostics sufficient to freeze the feature boundary before R2-11, including identifier/protected-concept scans, cardinality, constants, missingness, category support, univariate checks, shallow-model/shortcut screens, lineage mutations, and targeted perturbations.

The diagnostics must:

- map every feature to one and only one driver group;
- confirm `recent_payment` is the predeclared strongest group and `missingness` is the designed-zero group without changing those declarations after results;
- assign every finding one explicit `allow`, `exclude`, `investigate`, or `redesign` disposition with rationale and downstream effect;
- treat a required exclusion or redesign as a versioned upstream change rather than silently dropping a feature; and
- avoid describing missingness associations causally.

Full multi-seed null, shuffle, signal-recovery, learning, ablation, robustness, uncertainty, and temporal-stability tests remain R2-11 work.

### 6. Fit the two frozen candidates and select deterministically

Retain the R2-06 logistic-regression and boosted-tree specifications and dependency pins exactly as adopted by contract `3.0.0`. Fit both candidates on identical governed fit rows and score identical selection rows.

Select the candidate by:

1. higher ROC AUC;
2. if absolute AUC difference is at most `1e-12`, lower Brier score; and
3. if both metric differences are at most `1e-12`, logistic regression.

Freeze the selected candidate name, complete specification, fit and selection memberships, feature/preprocessing identities, metrics, safe fitted state, model digest, prediction digest, dependencies, and numeric normalization before any acceptance-role access. Explicit non-executable state must reproduce identical authorized selection predictions without refitting.

No hyperparameter search, validation-guided retry, feature selection from candidate results, calibration, threshold selection, or use of calibration, non-final-evaluation, acceptance, or final-holdout data for candidate choice is allowed.

### 7. Implement scoring authorization `3.0.0`

Authorization must bind at least:

- purpose, fold, and role;
- ordered observation IDs and feature names;
- complete matrix and target digest;
- fit matrix, preprocessing, and model digests;
- artifact identity and all applicable contract versions.

Relabeling, row reordering, row/target/feature substitution, derivation, cross-fold reuse, digest tampering, model substitution, and authorization-field editing must fail before prediction. Selection authorization must not authorize acceptance scoring. Ordinary unlabeled inference must remain a separate interface and must not accept labeled evaluation authority by implication.

### 8. Publish deterministic non-final R2-10 evidence

Expected artifacts are:

```text
docs/modeling/phase-02r-10-v3-evaluation-pipeline-contract.md
docs/modeling/phase-02r-10-v3-evaluation-candidate-membership-amendment-3.1.0.md
docs/modeling/phase-02r-10-statistical-acceptance-protocol-amendment-2.1.0.md
docs/modeling/phase-02r-10-v3-arrears-remediation-contract-3.1.0.md
docs/modeling/phase-02r-10-v3-feature-dictionary.json
docs/experiments/phase-02r-10-v3.1-pre-remediation-disposition.json
docs/experiments/phase-02r-10-v3-structural-support-3.2.0.json
docs/experiments/phase-02r-10-v3-structural-support-3.2.0.md
docs/experiments/phase-02r-10-v3-split-manifest-3.2.0.json
docs/experiments/phase-02r-10-v3-feature-pipeline-manifest-3.2.0.json
docs/experiments/phase-02r-10-v3-feature-diagnostics-manifest-3.2.0.json
docs/experiments/phase-02r-10-v3-feature-diagnostics-report-3.2.0.md
docs/experiments/phase-02r-10-v3-candidate-selection-manifest-3.2.0.json
docs/experiments/phase-02r-10-v3-candidate-selection-report-3.2.0.md
```

Every authoritative artifact binds the historical R2-09 manifest digest, the remediated simulator identity, evaluation contract `3.2.0`, protocol `2.2.0`, the invalidated-attempt disposition, and its split, feature, preprocessing, model, dependency, canonicalization, and source versions.

The original structural-support files and all initial `3.1.0` artifacts are immutable failed evidence and must not be overwritten. The authoritative `3.2.0` evidence reports 1,498 episodes from 787 policies and must not describe repeated episodes as additional independent-policy capacity.

Evidence must record counts and class support by role, fold, period, billing frequency, and censoring disposition without committing raw observations, full matrices, row-level predictions, protected sidecars, or executable fitted objects. The selected candidate may be frozen from the governed selection role; acceptance-role predictions and metrics must not exist.

### 9. Add deterministic commands, tests, and repository integration

- Add documented `--write` and read-only `--check` commands, or one clearly bounded orchestrator, for every R2-10 artifact.
- Add read-only artifact reproduction to `Makefile`, hosted CI, and repository-boundary checks.
- Test chronology, both embargoes, role/policy/episode isolation, support, stable row order, dual-time lineage, recursive protected-field rejection, driver-group completeness, fit-only preprocessing, unknown categories, candidate identity, tie breakers, safe reload, authorization mutations, historical artifact immutability, and final-holdout absence.
- Prove two clean evidence builds are byte-identical and that governed v1/v2/R2-07/R2-09 historical artifacts remain unchanged.
- Update technical navigation, `docs/backlog.md`, `PROJECT_PROGRESS.md`, and `Documents/Inforsight_Change_Tracker.md` only with evidence that exists at each workflow stage.

## Anticipated implementation surface

Prefer separate v3 modules and tests under the existing modeling package rather than changing v1/v2 semantics in place. The implementation may add focused modules for splits, features, preprocessing, diagnostics, candidate state, and scoring authorization when that improves auditability.

Likely existing integration points include:

```text
modeling/src/inforsight_modeling/
modeling/tests/
scripts/
Makefile
scripts/check_repository_boundaries.sh
docs/experiments/README.md
docs/backlog.md
docs/limitations.md
PROJECT_PROGRESS.md
Documents/Inforsight_Change_Tracker.md
```

The implementation issue must finalize the file plan before broad edits and must preserve all unrelated and historical artifacts.

## Acceptance checks

- [x] A versioned R2-10 implementation and remediation contract freezes the effective `3.1.0`/`3.2.0`/`2.2.0` boundaries.
- [x] Historical R2-09, original support-failure, and invalidated `3.1.0` evidence remain immutable and explicitly dispositioned.
- [x] Split evidence proves strict chronology, the full 90-day embargo, zero policy overlap, and zero outcome-episode overlap for every governed membership.
- [x] Every required role/fold meets frozen observation, class, billing-frequency, and censoring support without reassignment, seed replacement, or relaxed chronology.
- [x] Only validated public v3 observations enter feature construction; artifact identity, visible-event digest, and per-value lineage are verified.
- [x] The v3 feature dictionary maps every feature exactly once and protected concepts fail closed.
- [x] Preprocessing is fit only on approved fit rows, with a frozen unknown-category path and matrix width.
- [x] Every diagnostic finding has one documented disposition; disallowed findings fail closed.
- [x] Logistic and boosted candidates use identical memberships and the exact frozen tie-break rule.
- [x] Portable non-executable fitted state reproduces authorized selection predictions without refitting.
- [x] The selected candidate, memberships, metrics, authorization, and all upstream/model digests are frozen before acceptance access.
- [x] Authorization `3.0.0` binds purpose, fold, role, membership, names, matrix/target, fit, preprocessing, model, artifact, and contract identities; mutation bypasses fail before prediction.
- [x] No acceptance-role prediction or metric and no R2-11 readiness/acceptance result is created.
- [x] Every authoritative artifact regenerates byte-for-byte without committed raw matrices, row-level predictions, oracle sidecars, or executable fitted objects.
- [x] Governed v1/v2 artifacts, R2-07 evidence, and R2-09 evidence remain unchanged.
- [x] Evidence reports 787 unique selection policies and limits interpretation to role-isolated synthetic mechanism recovery.
- [x] The final release holdout remains `not_materialized`, with no seed, identity, membership, distribution, row, feature, transform, prediction, or metric created or inspected.
- [ ] Focused tests, full repository checks, artifact checks, boundary checks, `make check`, and `git diff --check` pass locally and in hosted CI.
- [ ] The implementation PR merges to `main`, closes the R2-10 issue, records completion evidence, and leaves R2-11 as the only newly enabled increment.

## Evidence required in the pull request

- Version and compatibility table for v3 splits, features, preprocessing, candidates, authorization, commands, and artifacts.
- Structural membership summaries by role, fold, period, billing frequency, class, and censoring disposition.
- Chronology, 90-day embargo, policy-isolation, and episode-isolation proof.
- Feature lineage, dual-time boundary mutation, and recursive protected-concept rejection evidence.
- Fit-only preprocessing and frozen unknown-category mutation evidence.
- Complete diagnostic registry and dispositions.
- Candidate specifications, identical membership proof, deterministic metrics/tie-break evidence, frozen selected-candidate digest, and safe reload verification.
- Authorization mutation evidence for relabeling, reorder, substitution, derivation, cross-fold reuse, and tampering.
- Matching bytes and SHA-256 digests from two clean R2-10 evidence rebuilds.
- Byte-digest proof that governed historical artifacts are unchanged.
- File/path and manifest audit proving acceptance results are absent and final-holdout status remains `not_materialized`.
- Full `make check`, focused tests, hosted CI, artifact checks, repository-boundary checks, and `git diff --check` output.

## Explicitly out of scope

- Executing R2-11 readiness or any null, shuffle, signal-recovery, oracle, calibration, learning, ablation, robustness, bootstrap, uncertainty, temporal-stability, or decision rule from protocol `2.1.0`.
- Accessing acceptance-role labels for fitting, selection, diagnostics, prediction, or metrics; only structural membership/support validation is allowed.
- Changing frozen coefficients, transforms, seeds, folds, roles, scenarios, candidates, metrics, tie breakers, thresholds, resampling, or decision rules after v3 output inspection.
- Materializing or accessing any final-release-holdout seed, identity, membership, distribution, event, observation, feature, matrix, transform, prediction, or metric.
- Probability calibration or operational-threshold selection assigned to P2-08.
- SHAP or equivalent substantive explanations assigned to P2-09.
- Closing `LIM-002-001`, `LIM-002-002`, `LIM-002-003`, or `LIM-002-004`.
- Rewriting v1/v2 schemas, code, artifacts, reports, decisions, or historical conclusions.
- Real-world predictive, insurer-representativeness, prevalence, actuarial, causal, fairness, operational-utility, customer-impact, production-readiness, or release claims.
- Any conservation-action authority or automated adverse policy action.

## Dependency and exit boundary

R2-10 may begin only from updated `main` containing R2-09 merge commit `89c2291`. It must use the existing `v0.2.0-risk-model` milestone and remain a single dependency-gated implementation increment.

Completion authorizes R2-11 only. It does not establish statistical acceptance, close a limitation, resume P2-08/P2-09, authorize a final holdout, or support a release/performance claim. Only a later merged R2-11 `proceed` decision may resume performance-dependent work.

## Copy-ready GitHub issue content

Use `.github/ISSUE_TEMPLATE/implementation.yml` with the following content.

### Title

```text
[Implementation] R2-10: Rebuild v3 evaluation, features, candidates, selection, and authorization
```

### Work metadata

```text
Backlog work ID: R2-10
Classification: Modeling-foundation remediation / versioned capability
Priority: Release blocking
Milestone: v0.2.0-risk-model
```

### Outcome

```text
A deterministic, separately versioned v3 evaluation pipeline constructs governed folds, closed public features, fit-only preprocessing, leakage-aware diagnostics, the two frozen candidates, deterministic candidate selection, and digest-bound scoring authorization; freezes reproducible non-final R2-11 inputs; and leaves acceptance execution and the final release holdout unmaterialized.
```

### Context

```text
R2-09 completed through issue #56 and PR #57, merged as 89c2291, implementing the event-first dual-time v3 corpus and recurring observations without producing a model or final-holdout result. R2-10 is the next strict Phase 2R increment and implements the evaluation boundary assigned by ADR 0005 and substrate contract 3.0.0, as amended downstream by issue #60 through evaluation/candidate membership 3.1.0 and acceptance protocol 2.1.0. The complete scope and test inventory are in Documents/phase-02r-10-v3-evaluation-features-candidates-and-authorization.md. R2-11, P2-08, and P2-09 remain blocked.
```

### In scope and out of scope

```text
In scope:
- Governed v3 roles/folds, strict chronology, 90-day embargoes, isolation, support validation, and deterministic row order.
- Closed v3 feature dictionary, dual-time/lineage validation, recursive protected-concept rejection, fit-only preprocessing, and frozen unknown-category handling.
- Leakage-aware non-final diagnostics with complete driver-group mapping and dispositions.
- Frozen logistic and boosted candidates on identical fit/selection memberships, exact deterministic selection, safe state reload, and candidate freezing.
- Scoring authorization 3.0.0 bound separately to immutable R2-09 identity, evaluation/candidate membership 3.1.0, and protocol 2.1.0; deterministic non-final artifacts, tests, commands, repository checks, compatibility evidence, and documentation.

Out of scope:
- R2-11 readiness/acceptance execution, acceptance-role predictions or metrics, and any protocol 2.1.0 decision.
- Calibration, operational thresholds, explanations, limitation closure, or release/performance claims.
- Any frozen statistical-design change, final-release-holdout access, or rewrite of historical v1/v2/R2-07/R2-09 evidence.
```

### Claim, limitation, contract, and artifact impact

```text
Allowed while open: Inspect governed fit and selection outputs needed to verify the frozen pipeline and select between the two predeclared candidates; inspect acceptance membership only for structural support and isolation.
Blocked while open: Acceptance-role labels for modeling or metrics; R2-11 execution/decision; calibration; explanations; limitation closure; release/performance claims; all final-holdout access.
Limitations affected: Supplies evaluation-boundary evidence for LIM-002-001, LIM-002-002, and LIM-002-004 without closing them. LIM-002-003 and the one-shot final-holdout obligation remain open.
Downstream work resumed at closure: R2-11 only.
Contract or version change: Preserve the R2-09 corpus, feature, preprocessing, candidate-specification, and scoring-authorization contracts at their recorded 3.0.0 identities; implement issue-#60 evaluation/candidate membership 3.1.0 and acceptance protocol 2.1.0 as separate downstream bindings. Do not alter v1/v2 semantics or historical evidence.
Artifact migration or compatibility: Add deterministic non-final v3 split, feature, diagnostic, and candidate-selection evidence. Raw matrices, row-level predictions, protected sidecars, and executable fitted objects remain uncommitted. Historical artifacts remain byte-identical; final holdout remains not_materialized.
```

### Acceptance checks

Copy the checklist from this document's **Acceptance checks** section into the issue unchanged.

### Evidence

```text
- Version/compatibility table and deterministic split, feature, diagnostic, candidate-selection, and authorization artifacts.
- Membership support, chronology, 90-day embargo, policy-isolation, and episode-isolation evidence.
- Dual-time lineage mutations, recursive protected-field rejection, fit-only preprocessing, and unknown-category tests.
- Candidate specification/membership parity, exact tie-break, safe reload, frozen selected-candidate, and authorization-mutation evidence.
- Two byte-identical clean artifact rebuilds and proof that governed historical artifacts remain unchanged.
- Final-holdout absence and acceptance-result absence audits.
- Focused and full repository test output, make check, hosted CI, boundary checks, and git diff --check.
```

### Dependencies

```text
Must merge first: R2-09 — issue #56 and PR #57, merged as 89c2291 (complete).
Blocks: R2-11. P2-08 and P2-09 remain transitively blocked.
Related decisions or limitations: ADR 0005; issue #60; v3 substrate contract 3.0.0; evaluation/candidate-membership amendment 3.1.0; acceptance protocol 2.1.0; R2-07 stop decision; LIM-002-001 through LIM-002-004.
```

Select every required boundary checkbox in the implementation template. R2-10 uses fictional clean-room data, preserves point-in-time and authority boundaries, has an explicit version/compatibility plan, and must not access or materialize a final holdout.
