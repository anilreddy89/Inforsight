# Inforsight Change Tracker

Last reviewed: 2026-08-29  
Current repository branch: `docs/57-r2-09-closeout`

## Purpose

This tracker records what changed, what is planned, when work completed or is expected, and the GitHub issue and pull request that provide implementation evidence. It complements `docs/backlog.md`, the phase implementation documents, and the existing Excel execution trackers.

GitHub Issues and merged pull requests remain the authoritative work-item record. Update this tracker after an issue is created, implementation begins, a pull request opens, and the pull request merges.

Current release milestone: [**v0.2.0-risk-model**](https://github.com/anilreddy89/Inforsight/milestone/3). R2-00 through R2-11 are internal release gates within this milestone, not a separate milestone.

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
| R2-10 | Phase 2R — Evaluation data | Rebuild v3 folds, features, preprocessing, diagnostics, candidates, selection, and authorization. | In progress | [#59](https://github.com/anilreddy89/Inforsight/issues/59) | TBD | 2026-08-30 | — | Deterministic readiness inputs and frozen selected candidate | Focused scope is frozen in the phase plan; no acceptance result or final holdout. |
| R2-11 | Phase 2R — Evidence gate | Run acceptance protocol `2.0.0` after readiness passes. | Pending | TBD | TBD | After R2-10 merge | — | Multi-seed controls, recovery, uncertainty, robustness, and decision evidence | Only merged `proceed` resumes P2-08/P2-09. |
| P2-08 | Phase 2 — Baseline ML | Calibrate probabilities and evaluate non-final operational thresholds. | Paused | TBD | TBD | After R2-11 proceed decision | — | Calibration, discrimination, review-capacity precision, high-risk recall, threshold, uncertainty, and false-positive-cost evidence | Paused by `LIM-002-001` and `LIM-002-002`; final holdout is not selection data. |
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
12. R2-07 records `stop` before model fitting; R2-08 predeclares the v3 correction and protocol `2.0.0`; R2-09 implements the corrected substrate; P2-08 and P2-09 remain paused through R2-11.

In one sentence: Inforsight now has a reproducible event-first v3 corpus that corrects the v2 dual-time and matched-stream implementation boundary, but no performance-dependent work may resume until R2-10 constructs governed evaluation evidence and R2-11 records `proceed`.

R2-00 through R2-09 are complete through PR #57, merge commit `89c2291`. R2-10 is in progress through issue #59. R2-00 through R2-11 belong to the existing [**v0.2.0-risk-model**](https://github.com/anilreddy89/Inforsight/milestone/3) milestone. P2-08 probability calibration and P2-09 explanations remain paused until R2-11 records a merged `proceed` decision.

| Measure | Value |
| --- | ---: |
| Completed tracked changes | 26 |
| Planned changes | 1 |
| Paused changes | 2 |
| In-progress changes | 1 |
| Implemented-locally changes | 0 |
| Changes needing confirmation | 1 |
| Pending changes | 5 |
| Completed Phase 1 increments | 7 of 7 |
| Completed Phase 2 increments | 7 of 12, with P2-08 and P2-09 paused |
| Completed Phase 2R increments | 10 of 12 |
| Planned Phase 2R increments | 2 of 12 |
| Next implementation increment | R2-10 v3 evaluation, features, candidates, selection, and authorization |

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
- Issue #59 opened R2-10 with a focused v3 evaluation, feature, candidate-selection, and authorization boundary; R2-11 remains blocked.

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
