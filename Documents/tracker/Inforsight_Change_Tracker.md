# Inforsight Change Tracker

Last reviewed: 2026-09-03
Current repository branch: `main`

## Purpose

This tracker records what changed, what is planned, when work completed or is expected, and the GitHub issue and pull request that provide implementation evidence. It complements `docs/backlog.md`, the phase implementation documents, and the existing Excel execution trackers.

GitHub Issues and merged pull requests remain the authoritative work-item record. Update this tracker after an issue is created, implementation begins, a pull request opens, and the pull request merges.

Current release milestone: [**v0.2.0-risk-model**](https://github.com/anilreddy89/Inforsight/milestone/3). R2-00 through R2-11 and the focused R2-12 through R2-16 redesign extension are internal release gates within this milestone, not a separate milestone.

## Status definitions

| Status | Meaning |
| --- | --- |
| Pending | Roadmap work exists, but no implementation issue or branch is active. |
| Planned | Scope and acceptance checks are documented and an issue is ready or open. |
| Paused | Work is intentionally stopped behind a documented dependency or claim gate. |
| In progress | Implementation is underway on an issue-linked branch. |
| Implemented locally | Code and tests are complete locally but not merged. |
| Completed | The pull request is merged to `main`, checks pass, and the issue is closed. |
| Needs confirmation | Completion depends on repository or external settings that must be verified separately. |

## Change register

| ID | Phase | Change | Status | Issue | PR | Completion / planned date | Merge commit | Primary evidence | Dependencies / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-01 | Phase 0 — Foundation | Create repository README, problem framing, clean-room policy, assumptions, and initial ADRs. | Completed | Pre-issue scaffold | — | 2026-08-17 | `1944595` | `README.md`, `docs/problem-statement.md`, `docs/clean-room-policy.md`, `docs/assumptions.md`, `docs/adr/` | Established the clean-room repository boundary. |
| F-02 | Phase 0 — Foundation | Add contribution, security, licensing, notices, and repository-boundary checks. | Completed | Pre-issue scaffold | — | 2026-08-17 | `1944595` | `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, `scripts/check_repository_boundaries.sh` | Present on `main`; included in `make check`. |
| F-03 | Phase 0 — Foundation | Create hosted repository and configure branch protection. | Needs confirmation | TBD | TBD | TBD | — | GitHub repository settings | Verify protection and required checks in GitHub before marking complete. |
| F-04 | Phase 0 — Foundation | Convert implementation work into hosted issues and maintain the `v0.1.0-data-foundation` milestone. | In progress | Multiple | Multiple | Ongoing | — | GitHub Issues and milestone | Confirm remaining Phase 1 work is assigned to the milestone. |
| P1-01 | Phase 1 — Policy Digital Twin | Define the versioned policy-event envelope, timestamps, valid/invalid examples, and automated contract tests. | Completed | [#1](https://github.com/anilreddy89/Inforsight/issues/1) | [#2](https://github.com/anilreddy89/Inforsight/pull/2) | 2026-08-17 | `0ba73ba` | `data-contracts/policy-event.schema.json`, contract examples and tests | Foundation for all event-specific payloads. |
| P1-02 | Phase 1 — Policy Digital Twin | Define strict policy, billing, payment, notice, service, and outcome payload contracts. | Completed | [#3](https://github.com/anilreddy89/Inforsight/issues/3) | [#4](https://github.com/anilreddy89/Inforsight/pull/4) | 2026-08-17 | `036e8fe` | `data-contracts/payloads/`, nine valid event examples | Depends on P1-01. |
| P1-03 | Phase 1 — Policy Digital Twin | Implement the deterministic seeded generator for 100 fictional policy histories. | Completed | [#5](https://github.com/anilreddy89/Inforsight/issues/5) | [#6](https://github.com/anilreddy89/Inforsight/pull/6) | 2026-08-17 | `eee6fbb` | `simulator/src/inforsight_simulator/generator.py`, generator and serialization tests | Depends on P1-01 and P1-02. |
| P1-04 | Phase 1 — Policy Digital Twin | Implement effective-time point-in-time policy-state reconstruction. | Completed | [#8](https://github.com/anilreddy89/Inforsight/issues/8) | [#9](https://github.com/anilreddy89/Inforsight/pull/9) | 2026-08-18 | `b993397` | `simulator/src/inforsight_simulator/reconstruction.py`, reconstruction tests | Depends on P1-01 through P1-03. |
| P1-05 | Phase 1 — Policy Digital Twin | Validate event ordering, lifecycle transitions, impossible dates, cross-event references, and deterministic replay. | Completed | [#10](https://github.com/anilreddy89/Inforsight/issues/10) | [#11](https://github.com/anilreddy89/Inforsight/pull/11) | 2026-08-18 | `c01e207` | `simulator/src/inforsight_simulator/validation.py`, 21 history-validation tests | Depends on P1-01 through P1-04. |
| P1-06 | Phase 1 — Policy Digital Twin | Publish a reproducible fictional sample dataset, data card, integrity manifest, and artifact-level tests. | Completed | [#12](https://github.com/anilreddy89/Inforsight/issues/12) | [#13](https://github.com/anilreddy89/Inforsight/pull/13) | 2026-08-18 | `c875289` | `datasets/`, `scripts/build_sample_dataset.py`, 7 published-dataset tests | Eight policies, 49 events; depends on P1-01 through P1-05. |
| P1-07 | Phase 1 — Policy Digital Twin | Assess aggregate synthetic rates against cited public references and document calibration assumptions. | Completed | [#14](https://github.com/anilreddy89/Inforsight/issues/14) | [#15](https://github.com/anilreddy89/Inforsight/pull/15) | 2026-08-18 | `1bcef3a` | `scripts/assess_synthetic_rates.py`, `docs/experiments/phase-01-07-synthetic-rate-assessment.*`, 11 focused tests | No reviewed public measure was directly comparable; equal scenarios remain a coverage fixture and generator and published sample remain unchanged. |
| P2-01 | Phase 2 — Baseline ML | Define the modeling contract and data-sufficiency gate, then build deterministic observation records with effective-time and ingestion-time visibility at each `as_of` cutoff. | Completed | [#16](https://github.com/anilreddy89/Inforsight/issues/16) | [#17](https://github.com/anilreddy89/Inforsight/pull/17) | 2026-08-18 | `1d893b8` | `docs/modeling/phase-02-01-modeling-contract.md`, `docs/experiments/phase-02-01-observation-sufficiency.json`, `data-contracts/observation-record.schema.json`, `simulator/src/inforsight_simulator/observations.py`, 17 focused tests | This implementation increment combines the first two Phase 2 backlog items. Gate decision is proceed with limitations; observations use one first-billing cutoff with explicit 90-day follow-up and censoring. |
| P2-02 | Phase 2 — Baseline ML | Add automated future-leakage and simulator-shortcut tests. | Completed | [#18](https://github.com/anilreddy89/Inforsight/issues/18) | [#19](https://github.com/anilreddy89/Inforsight/pull/19) | 2026-08-19 | `5e2987b` | `simulator/src/inforsight_simulator/leakage.py`, `simulator/tests/test_leakage_guards.py`, `docs/modeling/phase-02-02-leakage-and-shortcut-guards.md`, 16 focused tests | Recursive feature boundary, temporal mutations, direct simulator-marker rejection, exact-proxy diagnostics, and observation/episode uniqueness; depends on P2-01. |
| P2-03 | Phase 2 — Baseline ML | Create policy-aware temporal train, validation, and test splits with grouping or embargo rules and distribution evidence. | Completed | [#20](https://github.com/anilreddy89/Inforsight/issues/20) | [#21](https://github.com/anilreddy89/Inforsight/pull/21) | 2026-08-19 | `d8b516a` | `simulator/src/inforsight_simulator/splitting.py`, `scripts/build_temporal_splits.py`, `docs/experiments/phase-02-03-temporal-split-manifest.json`, 16 focused tests | Strict 90-day embargo and zero cross-partition policy or outcome-episode ownership; billing-frequency/time confounding limits results to pipeline engineering. Depends on P2-01 and P2-02. |
| L-01 | Phase 2 — Limitation gate | Track and resolve billing-frequency/observation-time confounding before temporal-performance or model-release claims. | Planned | R2 issues TBD | TBD | Through R2-07 | — | `docs/limitations.md` (`LIM-002-001`) | Scheduled for R2-04 through R2-07; blocks P2-08 and P2-09 evidence. |
| P2-04 | Phase 2 — Baseline ML | Implement a versioned deterministic feature pipeline, feature dictionary, and training-only preprocessing. | Completed | [#22](https://github.com/anilreddy89/Inforsight/issues/22) | [#23](https://github.com/anilreddy89/Inforsight/pull/23) | 2026-08-19 | `463c4e5` | `simulator/src/inforsight_simulator/features.py`, `preprocessing.py`, `scripts/build_feature_pipeline.py`, Phase 2.04 contract, dictionary, manifest, and 17 focused tests | Train-only fitted state, frozen unknown-category handling, safe state reconstruction, and deterministic partition digests pass on `main`; depends on P2-01 through P2-03. |
| P2-05 | Phase 2 — Baseline ML | Train and document a seeded logistic-regression baseline. | Completed | [#24](https://github.com/anilreddy89/Inforsight/issues/24) | [#25](https://github.com/anilreddy89/Inforsight/pull/25) | 2026-08-19 | `b2ec59d` | Phase 2.05 contract, manifest, report, modeling module, artifact command, and 15 focused tests | Historical v1 engineering evidence. At completion the manifest recorded the test as sealed; later review prediction-accessed that fixture through the R2-03 bypass. |
| P2-06 | Phase 2 — Baseline ML | Freeze one XGBoost candidate and compare it with logistic regression on identical frozen train and validation data. | Completed | [#26](https://github.com/anilreddy89/Inforsight/issues/26) | [#27](https://github.com/anilreddy89/Inforsight/pull/27) | 2026-08-20 | `fd9fc3b` | Phase 2.06 contract, XGBoost `3.3.0` model module, deterministic comparison artifacts, command, and 12 focused tests | Historical v1 engineering evidence; native JSON state reproduces validation predictions. The v1 test fixture is now review-exposed, not a release holdout. |
| P2-07 | Phase 2 — Baseline ML | Run leakage-aware feature sanity and shortcut diagnostics on the frozen splits and record an allow, exclude, or investigate decision for each flagged feature. | Completed | [#28](https://github.com/anilreddy89/Inforsight/issues/28) | [#29](https://github.com/anilreddy89/Inforsight/pull/29) | 2026-08-20 | `8db20ce` | Phase 2.07 contract, diagnostic module, deterministic artifacts, command, and 14 focused tests | Historical v1 engineering evidence. Eight train-constant groups were flagged; the later review added claim-blocking R2 work and exposed the test-scoring guard. |
| R2-00 | Phase 2R — Remediation gate | Reconcile review findings, current status, limitations, pause boundaries, and historical test-fixture language. | Completed | Issue created post-merge; link pending confirmation | [#30](https://github.com/anilreddy89/Inforsight/pull/30) | 2026-08-28 | `4292743` | `docs/backlog.md`; `docs/limitations.md`; `README.md`; issue and PR templates; engineering workflow | Acceptance checks are present on `main`; R2-01 is unblocked. |
| R2-01 | Phase 2R — Correctness | Bind generated histories to exact configuration and provenance and namespace run identifiers. | Completed | [#33](https://github.com/anilreddy89/Inforsight/issues/33) | [#34](https://github.com/anilreddy89/Inforsight/pull/34) | 2026-08-28 | `c9c9c88` | Generator API, provenance, ID invariants, regression tests | 27 focused generator/CLI tests, 188 simulator tests, four contract tests, artifact checks, and boundary checks pass; issue #33 closed on merge. |
| R2-02 | Phase 2R — Correctness | Enforce observation/event structural and semantic invariants through one public ingress path. | Completed | [#36](https://github.com/anilreddy89/Inforsight/issues/36) | [#37](https://github.com/anilreddy89/Inforsight/pull/37) | 2026-08-28 | `7b23f1c` | Observation schema, runtime constructors, composite ingress, six contract tests, 195 simulator tests | All artifact and boundary checks pass; issue #36 closed automatically on merge; documentation closeout PR #38 merged as `6e821c1`. |
| R2-03 | Phase 2R — Evaluation boundary | Bind scoring authorization to verified membership and digests and retire the v1 fixture as a release holdout. | Completed | [#39](https://github.com/anilreddy89/Inforsight/issues/39) | [#40](https://github.com/anilreddy89/Inforsight/pull/40) | 2026-08-28 | `5eb67c1` | Scoring authorization contract `1.0.0`, inference/evaluation separation, 10 focused bypass tests, 205 simulator tests, six contract tests | All artifact and boundary checks pass; issue #39 closed on merge; documentation closeout PR #41 merged as `b71dc68`; no final metric produced; future one-shot holdout obligation remains open. |
| R2-04 | Phase 2R — Statistical design | Approve the versioned v2 simulator, observation, evaluation, and statistical acceptance contract. | Completed | [#42](https://github.com/anilreddy89/Inforsight/issues/42) | [#43](https://github.com/anilreddy89/Inforsight/pull/43) | 2026-08-29 | `1fc48ad` | ADR 0004, contracts `2.0.0`, acceptance protocol `1.0.0`, fixed seeds/folds/thresholds, and final-holdout design | Both CI runs passed; no v2 result or final holdout was created; R2-05 is unblocked. |
| R2-05 | Phase 2R — Modeling corpus | Implement the versioned v2 statistical generator and recurring point-in-time observations. | Completed | [#45](https://github.com/anilreddy89/Inforsight/issues/45) | [#46](https://github.com/anilreddy89/Inforsight/pull/46) | 2026-08-29 | `25c370d` | v2 contracts, 3,600-policy corpus, 42,795 observations, protected oracle sidecar, manifest, data card, 16 focused tests | Hosted CI passed with 221 simulator and nine contract tests; final holdout remains `not_materialized`; R2-06 is unblocked. |
| R2-06 | Phase 2R — Evaluation data | Rebuild chronological evaluation data, features, preprocessing, diagnostics, and baselines on v2. | Completed | [#48](https://github.com/anilreddy89/Inforsight/issues/48) | [#49](https://github.com/anilreddy89/Inforsight/pull/49) | 2026-08-29 | `58232fc` | v2 split, feature, preprocessing, diagnostic, authorization, and model-comparison artifacts | Both hosted CI runs passed; issue #48 closed on merge; portable evidence preserves runtime reload verification and the final release holdout remains `not_materialized`. |
| R2-07 | Phase 2R — Evidence gate | Run predeclared multi-seed, negative-control, signal-recovery, uncertainty, and temporal-robustness acceptance tests. | Completed | [#51](https://github.com/anilreddy89/Inforsight/issues/51) | [#52](https://github.com/anilreddy89/Inforsight/pull/52) | 2026-08-30 | `66ae092` | Execution contract, deterministic readiness manifest/report/decision, fail-closed runner, and nine focused tests | Mechanical decision `stop` before model fitting for post-cutoff ingestion leakage; seven independent findings require redesign; P2-08 and P2-09 remain paused. |
| R2-08 | Phase 2R — Statistical redesign | Approve the event-first, dual-time, matched-control v3 substrate and acceptance protocol `2.0.0`. | Completed | [#53](https://github.com/anilreddy89/Inforsight/issues/53) | [#54](https://github.com/anilreddy89/Inforsight/pull/54) | 2026-08-30 | `09f678a` | ADR 0005, substrate contract `3.0.0`, random-stream registry `1.0.0`, acceptance protocol `2.0.0`, and full R2-07 traceability | Documentation-only; no v3 result or holdout; issue closed on merge. |
| R2-09 | Phase 2R — Modeling corpus | Implement v3 event-first generation, dual-time observations, oracles, identities, and matched streams. | Completed | [#56](https://github.com/anilreddy89/Inforsight/issues/56) | [#57](https://github.com/anilreddy89/Inforsight/pull/57) | 2026-08-30 | `89c2291` | v3 contracts; 14,400-policy manifest; 76,545 observations; data card; 17 focused v3 tests; 12 contract and 258 simulator tests | Hosted CI passed; no model or final holdout; R2-10 is ready. |
| R2-10 | Phase 2R — Evaluation data | Rebuild v3 folds, features, preprocessing, diagnostics, candidates, selection, and authorization. | Completed | [#59](https://github.com/anilreddy89/Inforsight/issues/59) | [#62](https://github.com/anilreddy89/Inforsight/pull/62) | 2026-09-01 | `36c17b7` | Simulator `3.1.0`; evaluation `3.2.0`; all folds pass; XGBoost selected | Historical failures remain immutable; no final holdout. |
| R2-11 | Phase 2R — Evidence gate | Run acceptance protocol `2.2.0` after readiness passes. | Completed | [#64](https://github.com/anilreddy89/Inforsight/issues/64) | [#65](https://github.com/anilreddy89/Inforsight/pull/65) | 2026-09-01 | `76c8cd3` | All 20 pairs pass readiness; signal recovery fails; decision `redesign` | No stop condition or final holdout; later required families remain incomplete redesign failures. |
| R2-12 | Phase 2R — Diagnostic governance | Approve the v4 signal-recovery diagnostic boundary. | Completed | [#66](https://github.com/anilreddy89/Inforsight/issues/66) | [#67](https://github.com/anilreddy89/Inforsight/pull/67) | 2026-09-01 | `ea9cf1f` | ADR 0006, diagnostic contract `1.0.0`, seed-domain and consistency checks | Documentation-only; closeout merged through PR #68 as `e8857a7`; no new corpus, fit, prediction, metric, or holdout. |
| R2-13 | Phase 2R — Diagnostic execution and v4 design | Execute bounded signal-recovery diagnostics, disposition all six hypotheses, and freeze the reviewed v4 design. | Completed | [#69](https://github.com/anilreddy89/Inforsight/issues/69) | [#70](https://github.com/anilreddy89/Inforsight/pull/70) | 2026-09-02 | `7c4a1a7` | 20-seed aggregate evidence; H1/H2 supported; ADR 0007; substrate `4.0.0`; protocol `3.0.0`; [phase document](../phase_docs/phase-02r-13-v4-signal-recovery-diagnostics-and-design.md) | Hosted CI passed and PR merged; R2-14 is unblocked; future acceptance and final holdout remain unmaterialized. |
| R2-14 | Phase 2R — v4 implementation and qualification | Implement and qualify the frozen v4 substrate. | Completed | [#72](https://github.com/anilreddy89/Inforsight/issues/72) | [#73](https://github.com/anilreddy89/Inforsight/pull/73) | 2026-09-02 | `4b234bf` | V4 substrate `4.0.0`; complete 20-seed qualification; mechanical `redesign`; [phase document](../phase_docs/phase-02r-14-v4-substrate-implementation-and-qualification.md) | Recovery, probability quality, reference recovery, and hazard validity fail; R2-15 remains blocked. |
| R2-14A | Phase 2R — post-v4 diagnostic governance | Close out v4 and authorize bounded v5 diagnostics. | Completed | [#76](https://github.com/anilreddy89/Inforsight/issues/76) | [#77](https://github.com/anilreddy89/Inforsight/pull/77) | 2026-09-03 | `52c03c8` | ADR 0008; diagnostic contract `1.0.0`; [phase document](../phase_docs/phase-02r-14a-v4-closeout-and-v5-diagnostic-authorization.md) | Documentation-only closeout merged with both hosted CI runs passing; no diagnostic result, acceptance access, or final holdout. |
| R2-14B | Phase 2R — v5 diagnostic execution and design | Validate the frozen post-v4 diagnostic boundary before result-producing execution. | Completed — readiness stop | [#78](https://github.com/anilreddy89/Inforsight/issues/78) | [#79](https://github.com/anilreddy89/Inforsight/pull/79) | 2026-09-03 | `3088c4c` | Readiness-only manifest, report, hypothesis disposition, accepted ADR 0009; [phase document](../phase_docs/phase-02r-14b-v5-redesign-diagnostics-and-design.md) | Contract `1.0.0` lacked mechanical H1-H5 disposition thresholds; zero result units executed, all hypotheses unresolved, seeds 20280101..20280120 unspent. |
| R2-14BA | Phase 2R — diagnostic contract amendment | Close out R2-14B readiness stop and approve amended diagnostic authorization contract. | Completed | [#80](https://github.com/anilreddy89/Inforsight/issues/80) | [#81](https://github.com/anilreddy89/Inforsight/pull/81) | 2026-09-03 | `627e698` | ADR 0010; amended diagnostic contract `1.1.0`; [phase document](../phase_docs/phase-02r-14ba-r2-14b-closeout-and-diagnostic-contract-amendment.md) | Freezes mechanical H1-H5 disposition truth tables and quantitative thresholds; seeds `20280101..20280120` authorized for Phase 2R.14BB execution. |
| R2-14BB | Phase 2R — v5 diagnostic execution and design | Execute bounded post-v4 redesign diagnostics and evaluate feasibility surface. | Completed | [#82](https://github.com/anilreddy89/Inforsight/issues/82) | [#83](https://github.com/anilreddy89/Inforsight/pull/83), [#84](https://github.com/anilreddy89/Inforsight/pull/84) | 2026-09-03 | `464a4fd`, `3a7c890` | 120 inventory units, 320-cell feasibility surface, H1-H6 dispositions, ADR 0011, iteration ledger, Roadmap Web UI | Dispositions: `H1` supported, `H3`–`H5` rejected, `H6` infeasible (0/320 cells satisfy simultaneous recovery and hazard bounds); causal response `stop_infeasible_design` recorded in ADR 0011; iteration ledger and Web UI published. R2-14C unblocked with v6 bounded sigmoid architecture. |
| CI-01 | Infrastructure / CI | Parallelize CI across 4 concurrent jobs, enable pip caching, and prevent duplicate triggers. | Completed | — | [#85](https://github.com/anilreddy89/Inforsight/pull/85) | 2026-09-03 | `afdcb5f` | `.github/workflows/ci.yml`, `Makefile`, 4 parallel jobs + `scaffold-checks` gate | Reduces CI runtime from ~20m to ~3.5–4.5m with zero test loss; prevents duplicate push/PR runs. |
| R2-14C | Phase 2R — Generation v6 architecture | Authorize bounded sigmoid hazard link architecture for Generation v6 and approve Substrate Contract 6.0.0. | Completed | [#86](https://github.com/anilreddy89/Inforsight/issues/86) | [#87](https://github.com/anilreddy89/Inforsight/pull/87) | 2026-09-04 | `18ce32f` | ADR 0012, Substrate Contract `6.0.0`, `scripts/check_r2_14c_v6_contract.py`, `simulator/tests/test_v6_contract.py`, [phase document](../phase_docs/phase-02r-14c-v6-bounded-sigmoid-architecture.md) | Resolves Proportional Hazards Trilemma; guarantees total monthly hazard $\le 0.1500 < 0.2000$; authorizes fresh development seeds `20280201..20280220`; authorizes Phase 2R.14D. |
| R2-15 | Phase 2R — Generation v6 evaluation & candidate | Freeze Generation v6 evaluation folds, feature pipeline, candidate models, and deterministic selection. | Completed | [#90](https://github.com/anilreddy89/Inforsight/issues/90) | [#91](https://github.com/anilreddy89/Inforsight/pull/91) | 2026-09-04 | `8965c72` | Simulator module `v6_evaluation.py`, runner `scripts/build_v6_evaluation_pipeline.py`, fold split manifests, feature pipeline, diagnostics, candidate selection manifest, and [phase document](../phase_docs/phase-02r-15-v6-evaluation-and-candidate.md) | Authorizes candidate comparison, selects Logistic Regression (AUC: 0.7057 vs XGBoost: 0.6801), and freezes all memberships and fitted-state digests; clean-room invariants preserved; authorizes Phase 2R.16. |
| R2-16 | Phase 2R — Generation v6 statistical acceptance | Execute Generation v6 statistical acceptance protocol across reserved acceptance seeds 20271201..20271220. | Completed — mechanical redesign | [#92](https://github.com/anilreddy89/Inforsight/issues/92) | [#93](https://github.com/anilreddy89/Inforsight/pull/93) | 2026-09-04 | `82e767f` | Execution Contract `3.0.0`, acceptance manifest, report, decision, [phase document](../phase_docs/phase-02r-16-v6-statistical-acceptance-gate.md) | Executed 120 inventory units across reserved seeds `20271201..20271220`; primary signal recovery passes (median AUC 0.7031, AP lift +0.1344, 20/20 seed consistency); 4 fine-grained secondary rules fail thresholds resulting in mechanical decision `redesign`. Resumed Phase 2 remains paused pending remediation protocol. |
| R2-17 | Phase 2R — Acceptance protocol remediation | Adopt ADR 0013 and Protocol 3.1.0 addressing secondary rule calibration; re-evaluate acceptance protocol. | Planned | TBD | TBD | 2026-09-04 | — | ADR 0013, Protocol `3.1.0`, execution contract `3.1.0`, [phase document](../phase_docs/phase-02r-17-v6-acceptance-remediation-and-protocol-amendment.md) | Address finite-sample binomial coverage, quadrature discretization, and variance floor heuristics while leaving all primary signal recovery gates intact. Authorizes P2-08 if proceed. |
| P2-09 | Phase 2 — Baseline ML | Publish SHAP or equivalent attribution examples and feature sanity checks. | Paused | TBD | TBD | After R2-11 and P2-08 | — | Explanation examples with model-behavior and action-authority boundaries | Paused; do not substantively interpret v1 seed-noise behavior. |
| P2-10 | Phase 2 — Baseline ML | Version training configuration, dependencies, feature contract, split manifest, metrics, and model artifacts. | Pending | TBD | TBD | TBD | — | Reproducible training and scoring commands with artifact provenance | Applies to both baseline and boosted model. |
| P2-11 | Phase 2 — Baseline ML | Publish `MODEL_CARD.md`, experiment report, and Phase 2 model decision note. | Pending | TBD | TBD | TBD | — | Model comparison, limitations, calibration and threshold evidence, explanations, and acceptance-gate decision | Completes Phase 2 only when held-out temporal scoring is leakage-safe and reproducible. |
| P2-12 | Phase 2 — Baseline ML | Publish the agreed risk-model release marker and release notes. | Pending | TBD | TBD | TBD | — | `v0.2.0-risk-model` tag, GitHub release, version evidence, limitations, and reproduction entry points | Complete the existing [**v0.2.0-risk-model**](https://github.com/anilreddy89/Inforsight/milestone/3) milestone; keep milestone, tag, and release title aligned. |

## Current summary

### High-level achievement summary

Inforsight has a strong and repeatable v1 pipeline-engineering foundation. Phase 2R is now planned to repair correctness and statistical-design gaps before performance-dependent model work resumes:

1. The simulator creates deterministic fictional insurance-policy histories containing billing, payment, notice, service, lapse, and surrender events.
2. The same generation seed reproduces the same data, making tests and experiments repeatable.
3. Point-in-time reconstruction shows what was known about a policy on a specific date without using future information.
4. Modeling observations keep cutoff-visible policy information separate from the 90-day lapse-or-surrender label.
5. Leakage guards prevent future outcomes, identifiers, simulator scenarios, and other shortcuts from entering model features.
6. Policy-aware chronological train, validation, and test partitions include embargo controls that prevent time and outcome-episode overlap.
7. The versioned feature pipeline converts approved observations into fixed numeric model inputs and learns preprocessing rules from training data only.
8. `LIM-002-001` records that billing frequency is confounded with observation time, so the current corpus supports pipeline engineering but not realistic temporal-performance claims.
9. `LIM-002-002` records that v1 has no designed pre-cutoff feature-conditioned risk mechanism, so its model metrics cannot support calibration or substantive explanation claims.
10. `LIM-002-003` records that the v1 test fixture was prediction-accessed through a partition-relabeling bypass; no test metric was computed, but the fixture is not an untouched release holdout.
11. `LIM-002-004` records that the historical v2 behavior features can include post-cutoff ingested values; R2-09 implements the event-first v3 correction, while evaluation and acceptance evidence remain pending through R2-10/R2-11.
12. R2-07 records `stop` before model fitting; R2-08/R2-09 provide the historical v3.0 substrate; issues #60/#61 version remediation and downstream evidence to simulator `3.1.0`, evaluation `3.2.0`, and protocol `2.2.0`; P2-08 and P2-09 remain paused through R2-11.

In one sentence: Phase 2R.15 froze the Generation v6 evaluation pipeline and release candidate (Logistic Regression), and Phase 2R.16 is ready to execute replacement statistical acceptance testing.


| Measure | Value |
| --- | --- |
| Completed tracked changes | 39 |
| Implemented locally changes | 0 |
| Planned changes | 0 |
| Paused changes | 2 |
| In-progress changes | 0 |
| Completed Phase 1 increments | 7 of 7 |
| Completed Phase 2 increments | 7 of 12, with P2-08 and P2-09 paused |
| Completed Phase 2R increments | 22 of 22 (R2-00 through R2-15) |
| Active Phase 2R increment | Phase 2R.16 (Generation v6 replacement statistical acceptance gate) |
| Next implementation increment | Phase 2R.16 (Generation v6 replacement statistical acceptance gate) |

## Latest verification baseline

Latest merged verification baseline from issue #51 and PR #52:

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

Recorded after merge of PR #15 on 2026-08-18:

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

The following block is the historical verification record captured at Phase 2.07 completion. Its `sealed_not_scored` line describes the state asserted by that phase at the time; independent review later prediction-accessed the v1 test fixture through a relabeling bypass. No test metric was computed. Current status is governed by `LIM-002-003` and R2-03.

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

P2-07 is complete on `main` as historical v1 pipeline evidence. Eight train-constant source groups have recorded dispositions, while billing frequency remains under `LIM-002-001`. The later review established `LIM-002-002` and `LIM-002-003`; the v1 test fixture is review-exposed prediction-only evidence and must not be used for a final performance claim.

Latest merged-main verification after PR #37:

```text
Repository boundary checks: passed
All published dataset and experiment artifact reproducibility checks: passed
Contract tests: 6 passed
Simulator tests: 195 passed
git diff --check: passed
```

R2-02 is complete on `main`. The observation schema and runtime constructors reject contradictory label, eligibility, feature, temporal, version, identifier, and currency states. Public policy-history ingress validates event and payload JSON Schemas before cross-event semantics. No historical artifact bytes changed, and no v2 corpus or final-holdout evidence was produced.

Latest merged-main verification after PR #40:

```text
Repository boundary checks: passed
All published dataset and experiment artifact reproducibility checks: passed
Focused R2-03 scoring-authorization tests: 10 passed
Contract tests: 6 passed
Simulator tests: 205 passed
git diff --check: passed
```

R2-08 is complete on `main` through issue #53 and PR #54, merge commit `09f678a`. The approved v3 design authorizes R2-09 only; the final holdout remains `not_materialized`.

Completion evidence:

- Issue #16 closed when PR #17 merged.
- Both PR #17 CI runs completed successfully.
- Merge commit `1d893b8` is present on `origin/main`.
- Issue #20 closed when PR #21 merged.
- Merge commit `d8b516a` is present on `origin/main`.
- Issue #22 closed when PR #23 merged.
- Merge commit `463c4e5` is present on `main`.
- Issue #24 closed when PR #25 merged.
- Merge commit `b2ec59d` is present on `main`.
- Issue #28 closed when PR #29 merged.
- Merge commit `8db20ce` is present on `origin/main`.
- Issue #36 closed automatically when PR #37 merged.
- Merge commit `7b23f1c` is present on `origin/main`; R2-03 is unblocked.
- Documentation closeout PR #38 merged as `6e821c1` and is present on `origin/main`.
- Issue #39 closed when PR #40 merged as `5eb67c1`; R2-04 is unblocked.
- Documentation closeout PR #41 merged as `b71dc68` and is present on `main`; R2-03 records are reconciled.
- Issue #42 closed when PR #43 merged as `1fc48ad`; both CI runs passed and R2-05 is unblocked.
- Issue #45 closed when PR #46 merged as `25c370d`; hosted CI passed and R2-06 is unblocked.
- Issue #48 closed when PR #49 merged as `58232fc`; both hosted CI runs passed and R2-07 is unblocked.
- Issue #51 closed when PR #52 merged as `66ae092`; R2-07 preserves the mechanical `stop` decision and R2-08 is unblocked.
- Issue #53 closed when PR #54 merged as `09f678a`; R2-08 completed and R2-09 became ready.
- Issue #56 closed when PR #57 merged as `89c2291`; hosted CI passed, R2-09 is complete, and R2-10 is ready.
- Issue #59 opened R2-10; issue #60 amended the selection interval; issue #61 approved versioned arrears remediation. Local `3.2.0` evidence passes and selects XGBoost, while merge remains required before R2-11.

## Update procedure

For each change:

1. Add the row when the roadmap item is identified; use `Pending` and `TBD` for unknown issue, PR, and date values.
2. Add the GitHub issue link and planned date when scope and acceptance checks are approved; move to `Planned`.
3. Record the working branch in the corresponding phase document and move to `In progress` when implementation begins.
4. Add the PR link when opened; use `Implemented locally` only when implementation and verification are complete but unmerged.
5. After merge, record the completion date and merge commit, confirm the issue closed, and move to `Completed`.
6. Update `docs/backlog.md`, `README.md`, the relevant phase or contract document, `docs/limitations.md` when applicable, and this tracker together.
7. Record only evidence that exists on `main`; do not mark aspirational or local-only work complete.

## Deferred changes

The following remain intentionally deferred until a demonstrated consumer requires them:

- Richer lifecycle contracts such as issue age, face amount, acquisition channel, payment retries, reinstatement, maturity, loans, cash value, account changes, and prior conservation attempts.
- SQL persistence schemas.
- Java services, Kafka, cloud deployment, bounded agents, and RAG.

Create a focused GitHub issue and add a new tracker row before beginning any deferred change.
