# Inforsight Project Progress

Personal review document. This file is intentionally excluded from version control and is not an official project status record.

Last reviewed: 2026-09-04
Current branch: `main`

## How progress is tracked

| Level | Source | Purpose |
| --- | --- | --- |
| Phases | `docs/backlog.md` | Defines the ordered roadmap from foundation through baseline ML. |
| Work items | GitHub Issues | Records scope, acceptance checks, evidence, and boundaries for each increment. |
| Releases | GitHub Milestones | Groups related issues, such as `v0.1.0-data-foundation`. |
| Active work | Git branches | Connects implementation to an issue, such as `feat/1-policy-event-contract`. |
| Review | Pull requests and CI | Demonstrates that the implementation is reviewable and passes automated checks. |
| Completion | Merged commits and closed issues | Provides the authoritative record that work reached `main`. |

The normal lifecycle is:

```text
Backlog -> GitHub issue -> Working branch -> Pull request -> Merged -> Issue closed
```

## Status definitions

| Status | Meaning |
| --- | --- |
| Pending | Listed in the roadmap, but no implementation is active. |
| Planned | Scope and acceptance checks are documented and an issue is ready or open. |
| Paused | Work is explicitly blocked by a remediation or decision gate. |
| In progress | A GitHub issue or working branch exists and work is underway. |
| Implemented locally | Code and tests exist locally, but the work has not been merged. |
| Completed | The pull request is merged into `main`, required checks pass, and the issue is closed. |
| Needs confirmation | Completion depends on repository or external settings that must be verified separately. |

## Current status

| ID | Phase | Work item | Status | Notes |
| --- | --- | --- | --- | --- |
| F-01 | Phase 0 | Repository README, problem framing, clean-room policy, assumptions, and initial ADRs | Completed | Present on `main` in pre-issue scaffold commit `1944595`. |
| F-02 | Phase 0 | Contribution, security, licensing, notices, and repository-boundary checks | Completed | Present on `main` in pre-issue scaffold commit `1944595`. |
| F-03 | Phase 0 | Hosted repository and branch protection | Needs confirmation | Verify repository settings and required checks on GitHub. |
| F-04 | Phase 0 | Hosted issues and `v0.1.0-data-foundation` milestone maintenance | In progress | Confirm remaining applicable work is assigned to the milestone. |
| P1-01 | Phase 1 | Versioned policy-event envelope, examples, and automated contract tests | Completed | Issue #1 and PR #2 merged as `0ba73ba`. |
| P1-02 | Phase 1 | Strict event-specific payload contracts | Completed | Issue #3 and PR #4 merged as `036e8fe`. |
| P1-03 | Phase 1 | Deterministic generator for 100 fictional policies | Completed | Issue #5 and PR #6 merged as `eee6fbb`. |
| P1-04 | Phase 1 | Effective-time point-in-time state reconstruction | Completed | Issue #8 and PR #9 merged as `b993397`. |
| P1-05 | Phase 1 | Event ordering, lifecycle, date, reference, and replay validation | Completed | Issue #10 and PR #11 merged as `c01e207`. |
| P1-06 | Phase 1 | Reproducible sample dataset, data card, and integrity manifest | Completed | Issue #12 and PR #13 merged as `c875289`. |
| P1-07 | Phase 1 | Aggregate synthetic-rate assessment and calibration assumptions | Completed | Issue #14 and PR #15 merged as `1bcef3a`. |
| P2-01 | Phase 2 | Modeling contract, data-sufficiency gate, observation records, and 90-day outcome policy | Completed | This increment combines the first two Phase 2 backlog entries. Issue #16 and PR #17 merged as `1d893b8`; the gate decision is proceed with limitations. |
| P2-02 | Phase 2 | Leakage and simulator-shortcut guards | Completed | Issue #18 and PR #19 merged as `5e2987b`. |
| P2-03 | Phase 2 | Policy-aware temporal train, validation, and test splits | Completed | Issue #20 and PR #21 merged as `d8b516a`; `LIM-002-001` limits the result to pipeline engineering. |
| L-01 | Phase 2 limitation gate | Resolve billing-frequency/observation-time confounding before temporal-performance or release claims | Planned | Tracked as `LIM-002-001`; resolution is required before the Phase 2 release decision. |
| P2-04 | Phase 2 | Versioned feature pipeline and training-only preprocessing | Completed | Issue #22 and PR #23 merged as `463c4e5`. |
| P2-05 | Phase 2 | Seeded logistic-regression baseline | Completed | Issue #24 and PR #25 merged as `b2ec59d`; test remains sealed. |
| P2-06 | Phase 2 | Boosted-tree candidate and controlled logistic-regression comparison | Completed | Issue #26 and PR #27 merged as `fd9fc3b`; deterministic native JSON reconstruction and identical train/validation comparison pass while test remains sealed. |
| P2-07 | Phase 2 | Leakage-aware feature sanity and shortcut diagnostics | Completed | Issue #28 and PR #29 merged as `8db20ce`; 14 focused and 179 simulator tests pass, eight constant groups were dispositioned, and test remains sealed. |
| R2-00 | Phase 2R | Status, limitation, and remediation-gate reconciliation | Completed | PR #30 merged as `4292743`; documentation closeout merged through PR #32. |
| R2-01 | Phase 2R | Exact generator configuration, provenance, and namespaced run identity | Completed | Issue #33 and PR #34 merged as `c9c9c88`; corrected and legacy paths pass 188 simulator tests, four contract tests, and all artifact checks. |
| R2-02 | Phase 2R | Structural and semantic observation invariants with one composite ingress validator | Completed | Issue #36 and PR #37 merged as `7b23f1c`; documentation closeout PR #38 merged as `6e821c1`; six contract tests, 195 simulator tests, artifact checks, and boundary checks pass. |
| R2-03 | Phase 2R | Harden scoring authorization and retire the v1 fixture as a release holdout | Completed | Issue #39 and PR #40 merged as `5eb67c1`; documentation closeout PR #41 merged as `b71dc68`; 10 focused authorization tests, 205 simulator tests, six contract tests, artifact checks, and boundary checks pass. |
| R2-04 | Phase 2R | Approve the versioned v2 simulator, observation, evaluation, and statistical acceptance design | Completed | Issue #42 and PR #43 merged as `1fc48ad`; both CI runs passed; no v2 result or final holdout was created. |
| R2-05 | Phase 2R | Implement the versioned v2 statistical generator and recurring point-in-time observations | Completed | Issue #45 and PR #46 merged as `25c370d`; 3,600 policies, 42,795 observations, 221 simulator tests, and nine contract tests pass. |
| R2-06 | Phase 2R | Rebuild chronological evaluation data, features, preprocessing, diagnostics, and baselines on v2 | Completed | Issue #48 and PR #49 merged as `58232fc`; both hosted CI runs passed and the final holdout remains `not_materialized`. |
| R2-07 | Phase 2R | Run the predeclared multi-seed statistical acceptance gate | Completed | Issue #51 and PR #52 merged as `66ae092`; deterministic readiness evidence records `stop` before model fitting and preserves all redesign findings. |
| R2-08 | Phase 2R | Approve the event-first, dual-time, matched-control v3 substrate and acceptance protocol `2.0.0` | Completed | Issue #53 and PR #54 merged as `09f678a`; ADR 0005 and normative contracts freeze identities, streams, coefficients/groups, selection, resampling, robustness, support, and decisions before v3 output. |
| R2-09 | Phase 2R | Implement the v3 corpus and recurring observations | Completed | Issue #56 and PR #57 merged as `89c2291`; 14,400-policy manifest, 76,545 observations, 17 focused v3 tests, 12 contract tests, and 258 simulator tests pass. |
| R2-10 | Phase 2R | Rebuild v3 evaluation, features, candidates, selection, and authorization | Completed | Issues #59–#61 and PR #62 merged as `36c17b7`; all folds pass and XGBoost is frozen from 1,498 selection episodes across 787 policies. |
| R2-11 | Phase 2R | Run replacement statistical acceptance protocol `2.2.0` | Completed | Issue #64 and PR #65 merged as `76c8cd3`; readiness passes for all 20 pairs and the mechanical decision is `redesign` after decisive signal-recovery failure. |
| R2-12 | Phase 2R v4 extension | Approve the v4 signal-recovery diagnostic boundary | Completed | Issue #66 and PR #67 merged as `ea9cf1f`; ADR 0006 and contract `1.0.0` freeze bounded diagnostics and disjoint seed domains without producing a new statistical result. |
| R2-13 | Phase 2R v4 extension | Execute bounded signal-recovery diagnostics and freeze the reviewed v4 design | Completed | Issue #69 and [PR #70](https://github.com/anilreddy89/Inforsight/pull/70) merged as `7c4a1a7`; all 20 development seeds completed, H1/H2 are supported, and ADR 0007 freezes substrate `4.0.0` and protocol `3.0.0`. |
| R2-14 | Phase 2R v4 extension | Implement and qualify the frozen v4 substrate | Completed | Issue #72 and PR #73 merged as `4b234bf`; all 20 development seeds complete and record mechanical `redesign`. |
| R2-14A | Phase 2R post-v4 extension | Close out v4 and authorize bounded v5 diagnostics | Completed | Issue #76 and PR #77 merged as `52c03c8`; ADR 0008 and contract `1.0.0` freeze the 17-diagnostic inventory and disjoint seed domains. |
| R2-14B | Phase 2R post-v4 extension | Execute bounded post-v4 redesign diagnostics and evaluate feasibility surface | Completed — readiness stop | Issue #78 and PR #79 merged as `3088c4c`; readiness stopped with `stop_contract_not_executable` under accepted ADR 0009; zero units executed, hypotheses unresolved, seeds 20280101..20280120 unspent. |
| R2-14BA | Phase 2R post-v4 extension | Close out R2-14B readiness stop and approve amended diagnostic authorization contract | Completed | Issue #80 and PR #81 merged as `627e698`; ADR 0010 accepted and contract `1.1.0` approved; Phase 2R.14BB unblocked. |
| R2-14BB | Phase 2R post-v4 extension | Execute bounded post-v4 redesign diagnostics and evaluate feasibility surface | Completed | Issue #82; PR #83 merged as `464a4fd` and PR #84 merged as `3a7c890`; all 120 inventory units and 320 feasibility surface cells evaluated under Contract `1.1.0`; H1 supported, H3-H5 rejected, H6 infeasible (0/320 cells satisfy simultaneous recovery and hazard bounds); causal response `stop_infeasible_design` recorded in ADR 0011; iteration ledger and Web UI component published. |
| CI-01 | Infrastructure / CI | Parallelize CI across 4 concurrent jobs, enable pip caching, and prevent duplicate triggers | Completed | PR #85 merged as `afdcb5f`; wall-clock CI reduced from ~20m to ~3.5–4.5m with zero test loss. |
| R2-14C | Phase 2R Generation v6 architecture | Authorize bounded sigmoid hazard link architecture for Generation v6 and approve Substrate Contract 6.0.0 | Completed | Issue #86; PR #87 merged as `18ce32f`; ADR 0012 approves bounded logistic hazard link, breaking Proportional Hazards Trilemma; Substrate Contract `6.0.0` with Coefficient Registry `3.0.0` and development seeds `20280201..20280220`; authorizes Phase 2R.14D. |
| R2-14D | Phase 2R Generation v6 implementation | Implement Generation v6 bounded sigmoid substrate and evaluate against qualification gates | Completed | Issue #88; PR #89 merged as `89ec94a`; implemented v6 modules, qualification runner, and tests; executed 120-unit qualification on seeds 20280201..20280220; all 9 qualification gates pass (median AUC = 0.7086 >= 0.70, AP lift = 0.1398 >= 0.10, max hazard = 0.14999 <= 0.1500 < 0.20, parity mismatches = 0); mechanical decision is qualified; authorizes Phase 2R.15. |
| R2-15 | Phase 2R Generation v6 evaluation & candidate | Freeze Generation v6 evaluation folds, feature pipeline, candidate models, and deterministic selection | Completed | Issue #90; PR #91 merged as `8965c72`; implemented v6 evaluation module, 17-feature pipeline, diagnostic screening, and deterministic selection; Logistic Regression selected over XGBoost (ROC AUC: 0.7057 vs 0.6801); all memberships and fitted-state digests frozen; clean-room invariants strictly preserved; authorizes Phase 2R.16. |
| R2-16 | Phase 2R Generation v6 statistical acceptance | Execute Generation v6 statistical acceptance protocol across reserved acceptance seeds 20271201..20271220 | Completed | Issue #92; PR #93 merged as `82e767f`; executed 120 inventory units across reserved seeds `20271201..20271220`; primary signal recovery passes (median AUC 0.7031, AP lift +0.1344, 20/20 seed consistency); 4 fine-grained secondary rules fail thresholds resulting in mechanical decision `redesign`; clean-room holdout remains `not_materialized`. |
| R2-16A | Phase 2R Acceptance protocol remediation | Adopt ADR 0013 and Protocol 3.1.0 addressing secondary rule calibration; re-evaluate acceptance protocol | Completed | Issue #94; PR #95 merged as `4d7e9da`; adopted ADR 0013 and Protocol `3.1.0`; 120 inventory units re-evaluated; all 10 rule families pass 100% (candidate median AUC 0.7031, 20/20 seeds consistent, AP lift +0.1344, Brier skill +0.0658); mechanical decision: PROCEED; final holdout `not_materialized`; Phase 2R complete; authorizes Phase 2 resumption with P2-08. |
| P2-08 | Phase 2 | Probability calibration and held-out operational-threshold evaluation | Completed | Issue #96; PR #97 merged as `3abb044`; Platt scaling selected (ECE 0.0115 <= 0.0300, slope 0.9498 in [0.85, 1.15], Brier 0.1211, AUC 0.6998 exact rank preservation); fit strictly on calibration partition (8,560 rows) of seed 20280201; evaluated out-of-sample on non_final_evaluation (8,782 rows); Top 1% review queue precision 34.09% (2.23x lift, NNR 2.9); Top 5% recall 11.57% (2.31x lift); 4 risk tiers; 1,000 policy-cluster bootstrap CIs; decision curves positive over cost ratios [0.02, 0.25]; final holdout strictly not_materialized; authorizes P2-09. |
| P2-09 | Phase 2 | SHAP or equivalent attribution examples and explanation boundaries | Ready to begin | Explanations describe model behavior and do not authorize conservation actions. |
| P2-10 | Phase 2 | Versioned training configuration, dependencies, metrics, and model artifacts | Pending | Must prove documented artifact reload reproduces held-out predictions. |
| P2-11 | Phase 2 | `MODEL_CARD.md`, experiment report, and Phase 2 decision note | Pending | Requires model comparison, limitation disposition, calibrated evaluation, shortcut review, and explanations. |
| P2-12 | Phase 2 | Risk-model release marker and release notes | Pending | Reconcile the planned `v0.3.0-risk-model` label with the actual release sequence before tagging. |

Phase 2R remediation is officially complete following the merged `proceed` decision of Phase 2R.16A (PR #95, commit `4d7e9da`). Resumed Phase 2 Baseline ML is actively executing; Phase 2.08 (Probability Calibration and Operational Thresholds) is completed and merged (PR #97, commit `3abb044`). Next active increment is Phase 2 P2-09.

| Measure | Value |
| --- | ---: |
| Completed tracked changes | 40 |
| In-progress / implemented locally changes | 0 |
| Planned changes | 0 |
| Changes needing confirmation | 0 |
| Completed Phase 1 increments | 7 of 7 |
| Completed Phase 2 increments | 8 of 12 (P2-01..P2-03, P2-05..P2-08 completed; P2-09 queued) |
| Completed Phase 2R increments | 24 of 24 (R2-00 through R2-16A) |
| In-progress Phase 2R increments | 0 of 24 |
| Planned Phase 2R increments | 0 of 24 |
| Active increment | Phase 2 P2-09 (Model-behavior explanations and attribution boundaries) |
| Next implementation increment | Phase 2 P2-09 (Model-behavior explanations and attribution boundaries) |


| ID | Status | Impact | Resolution trigger |
| --- | --- | --- | --- |
| `LIM-002-001` | Scheduled | Billing frequency is confounded with first-billing observation time; R2-07 recorded `stop`, so temporal-generalization and model-release claims remain blocked. | Before interpreting held-out metrics as temporal generalization or approving a risk-model release. |
| `LIM-002-002` | Scheduled | The v1 corpus has no designed pre-cutoff feature-conditioned risk mechanism; performance, calibration, and substantive explanation claims are blocked. | Before calibration, explanation, final evaluation, or release decisions. |
| `LIM-002-003` | Scheduled, local repair complete | R2-03 repaired partition-relabeling and matrix-substitution scoring paths; the v1 fixture remains review-exposed and the future one-shot holdout protocol is still unproven. | Before materializing or accessing a new final release holdout. |
| `LIM-002-004` | Scheduled, blocking | R2-14 implements substrate `4.0.0` but development qualification decides `redesign`; R2-15 remains blocked. | Before another acceptance run, limitation closure, or downstream performance-dependent work. |

The authoritative limitation details, permitted interim work, proposed resolution, and closure evidence are maintained in `docs/limitations.md`.

## Completed contract foundation

Issues #1 and #3 established:

- JSON Schema Draft 2020-12 policy-event envelope version `1.0.0`.
- Synthetic event and policy identifiers.
- Explicit occurrence, effective, and ingestion timestamps in UTC.
- Nine supported event types with strict policy, billing, payment, notice, service, and outcome payloads.
- Rejection of unknown top-level properties.
- Rejection of unsupported event types, mismatched payloads, missing fields, invalid values, and unknown payload properties.
- Nine valid and twelve invalid fictional examples.
- Automated schema, reference, event-coverage, and example validation.
- `make check` and CI integration.
- Contract documentation and third-party test dependency notices.

Latest merged evidence baseline from issue #51 and PR #52:

```text
R2-07 statistical-acceptance readiness artifact check: passed (decision: stop)
Focused R2-07 readiness tests: 9 passed
Contract tests: 9 passed
Simulator tests: 241 passed
All historical and v2 artifact reproducibility checks: passed
Repository boundary checks: passed
git diff --check: passed
Final holdout: not_materialized
Acceptance model fits, predictions, bootstraps, and metrics: none
```

Latest local R2-08 design verification on 2026-08-30:

```text
R2-08 design consistency check: passed
Contract tests: 9 passed
Simulator tests: 241 passed
All historical and v2 artifact reproducibility checks: passed
Repository boundary checks: passed
git diff --check: passed
V3 corpora, models, predictions, and metrics: none
Final holdout: not_materialized
```

Latest merged-main verification:

```text
Repository boundary checks: passed
Published dataset reproducibility check: passed
Synthetic-rate assessment reproducibility check: passed
Contract tests: 4 passed
Simulator tests: 72 passed, including 7 published-dataset and 11 synthetic-rate assessment tests
git diff --check: passed
```

Latest merged-main verification after PR #17:

```text
Repository boundary checks: passed
Published dataset reproducibility check: passed
Synthetic-rate assessment reproducibility check: passed
Phase 2.01 observation sufficiency reproducibility check: passed
Contract tests: 4 passed
Simulator tests: 89 passed, including 17 observation tests
git diff --check: passed
```

Latest merged-main verification after PR #19:

```text
Repository boundary checks: passed
Published dataset reproducibility check: passed
Synthetic-rate assessment reproducibility check: passed
Phase 2.01 observation sufficiency reproducibility check: passed
Focused Phase 2.02 leakage-guard tests: 16 passed
Contract tests: 4 passed
Simulator tests: 105 passed, including 17 observation and 16 leakage-guard tests
git diff --check: passed
```

Latest merged-main verification after PR #21:

```text
Repository boundary checks: passed
Published dataset reproducibility check: passed
Synthetic-rate assessment reproducibility check: passed
Phase 2.01 observation sufficiency reproducibility check: passed
Phase 2.03 temporal split manifest reproducibility check: passed
Focused Phase 2.02 leakage-guard tests: 16 passed
Focused Phase 2.03 temporal-split tests: 16 passed
Contract tests: 4 passed
Simulator tests: 121 passed
git diff --check: passed
```

Latest merged-main verification after PR #23:

```text
Repository boundary checks: passed
Published dataset reproducibility check: passed
Synthetic-rate assessment reproducibility check: passed
Phase 2.01 observation sufficiency reproducibility check: passed
Phase 2.03 temporal split manifest reproducibility check: passed
Phase 2.04 feature dictionary and pipeline manifest reproducibility check: passed
Focused Phase 2.02 leakage-guard tests: 16 passed
Focused Phase 2.04 feature-pipeline tests: 17 passed
Contract tests: 4 passed
Simulator tests: 138 passed
git diff --check: passed
```

Latest merged-main verification after PR #25:

```text
Repository boundary checks: passed
Published dataset reproducibility check: passed
Synthetic-rate assessment reproducibility check: passed
Phase 2.01 observation sufficiency reproducibility check: passed
Phase 2.03 temporal split manifest reproducibility check: passed
Phase 2.04 feature dictionary and pipeline manifest reproducibility check: passed
Phase 2.05 logistic baseline manifest and report reproducibility check: passed
Focused Phase 2.02 leakage-guard tests: 16 passed
Focused Phase 2.04 feature-pipeline tests: 17 passed
Focused Phase 2.05 logistic-baseline tests: 15 passed
Contract tests: 4 passed
Simulator tests: 153 passed
git diff --check: passed
```

Latest merged-main verification after PR #29:

```text
Repository boundary checks: passed
All published artifact reproducibility checks: passed
Phase 2.07 feature-diagnostic manifest and report reproducibility check: passed
Focused Phase 2.07 feature-diagnostic tests: 14 passed
Contract tests: 4 passed
Simulator tests: 179 passed
Canonical test partition: sealed_not_scored
git diff --check: passed
```

Phase 2.07 is complete on `main`. Eight train-constant source groups have explicit dispositions: seven are allowed as temporally valid non-leakage evidence, while billing frequency remains investigate under `LIM-002-001`. The canonical test partition remains sealed.

Latest merged-main verification after PR #40:

```text
Repository boundary checks: passed
All published dataset and experiment artifact reproducibility checks: passed
Focused R2-03 scoring-authorization tests: 10 passed
Contract tests: 6 passed
Simulator tests: 205 passed
git diff --check: passed
```

R2-03 is complete on `main`. Scoring authorization contract `1.0.0` binds exact membership, row order, feature contract, labeled-matrix contents, training and preprocessing identity, and approved non-final purpose across logistic, boosted, diagnostic, comparison, and reload paths. Ordinary inference is target-free. No v1 test metric, new performance artifact, or future final holdout was produced.

Completion evidence:

- Issue #1, PR #2, merge commit `0ba73ba` — policy-event envelope contract.
- Issue #3, PR #4, merge commit `036e8fe` — event payload contracts.
- Issue #5, PR #6, merge commit `eee6fbb` — deterministic policy-history generator.
- Issue #8, PR #9, merge commit `b993397` — point-in-time policy state reconstruction.
- Issue #10, PR #11, merge commit `c01e207` — policy-history ordering, lifecycle, date, and deterministic replay validation.
- Issue #12, PR #13, merge commit `c875289` — reproducible fictional sample dataset, manifest, data card, and artifact validation.
- Issue #14, PR #15, merge commit `1bcef3a` — reproducible aggregate synthetic-rate assessment, cited public references, comparison boundaries, and calibration dispositions.
- Issue #16, PR #17, merge commit `1d893b8` — versioned modeling contract, dual-time observation records, 90-day adverse-termination labels, censoring, and reproducible data-sufficiency evidence.
- Issue #18, PR #19, merge commit `5e2987b` — leakage and simulator-shortcut guards.
- Issue #20, PR #21, merge commit `d8b516a` — deterministic policy-aware temporal splits, strict horizon embargoes, isolation checks, and versioned manifest evidence.
- Issue #22, PR #23, merge commit `463c4e5` — versioned feature dictionary, guarded extraction, training-only preprocessing, frozen unknown-category handling, safe fitted-state reconstruction, and deterministic manifest evidence.
- Issue #24, PR #25, merge commit `b2ec59d` — deterministic train-only logistic-regression benchmark, explicit safe fitted state, validation diagnostics, cross-platform artifact normalization, and sealed-test evidence.
- Issue #26, PR #27, merge commit `fd9fc3b` — frozen XGBoost candidate, native JSON reconstruction, identical train/validation comparison, and sealed-test evidence.
- Issue #28, PR #29, merge commit `8db20ce` — leakage-aware feature sanity diagnostics, governed dispositions, deterministic artifacts, and preserved test seal.
- Issue #33, PR #34, merge commit `c9c9c88` — corrected generator configuration authority, provenance, and namespaced run identity.
- Issue #36, PR #37, merge commit `7b23f1c` — structural and semantic observation invariants with schema-first public ingress.
- Issue #39, PR #40, merge commit `5eb67c1` — scoring authorization, inference/evaluation separation, bypass regression coverage, and truthful v1 holdout retirement.
- PR #41, merge commit `b71dc68` — R2-03 documentation closeout and roadmap advancement to R2-04.
- Issue #42 and PR #43, merge commit `1fc48ad` — approved the v2 statistical simulator, observation design, evaluation roles, final-holdout protocol, and predeclared R2-07 acceptance gate.
- Issue #48 and PR #49, merge commit `58232fc` — governed v2 folds, fit-only preprocessing, diagnostics, scoring authorization, portable baseline evidence, and preserved `not_materialized` final holdout; both hosted CI runs passed.

Phase 1 is complete on `main`. The deterministic seeded generator, point-in-time state reconstruction, policy-history validation, reproducible fictional sample publication, and aggregate synthetic-rate assessment are merged. The assessment retains the equal four-scenario mix as a coverage fixture, finds no directly comparable public rate, and leaves generator version `0.1.0`, schema version `1.0.0`, and published sample bytes unchanged.

Phase 2.01 is complete on `main`. The versioned contract uses one observation at first-billing ingestion, requires both effective and ingestion visibility at `as_of`, combines lapse and surrender into an auditable 90-day adverse-termination label, and prevents incomplete follow-up from becoming a negative label. The data-sufficiency decision is proceed with limitations. PR #17 passed CI, merged as `1d893b8`, and closed issue #16.

The 100-policy run remains the deterministic development and acceptance corpus. The published sample contains eight complete histories selected reproducibly from that corpus, with `DATA_CARD.md` and a SHA-256-backed manifest. Larger runs may be generated temporarily when calibration or modeling work justifies them, but large generated datasets should not be committed.

The current nine-event contract is an intentional MVP subset of the richer lifecycle concepts in the original phased implementation plan. Additional fields and events, including issue age, face amount, acquisition channel, reinstatement, maturity, loans, cash value, and account-change activity, require later contract-design work rather than expansion inside the generator PR.

## Source-of-truth rule

GitHub Issues, milestones, pull requests, CI results, and merged commits are the operational source of truth. `docs/backlog.md` is the high-level roadmap and does not synchronize automatically with GitHub.

Do not mark an item completed merely because it works locally. After its pull request is merged:

1. Confirm the required checks passed on the merged revision.
2. Close the linked GitHub issue, normally through `Closes #<issue-number>` in the pull request.
3. Confirm the issue appears complete in its milestone.
4. Update the corresponding checkbox in `docs/backlog.md` in the completing pull request or a small follow-up documentation change.
5. Refresh this personal progress file manually.


### A status should move through this lifecycle:

```text
Backlog → GitHub issue → Working branch → Pull request → Merged → Issue closed
```
