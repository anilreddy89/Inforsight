# Inforsight Backlog

This backlog is ordered for a natural repository history. Each item should become a tracked issue before implementation. GitHub Issues are the operational source of truth; this file records phase order, dependencies, and acceptance gates rather than replacing issue-level execution detail.

## Phase 0 - Foundation

- [x] Create repository README, clean-room policy, assumptions, and initial ADRs.
- [x] Add contribution, security, licensing, and repository-boundary checks.
- [ ] Create hosted repository and configure branch protection.
- [ ] Convert the first implementation items below into hosted issues and a `v0.1.0-data-foundation` milestone.

## Phase 1 - Policy Digital Twin

- [x] Define `policy-event.schema.json` with explicit version and timestamps.
- [x] Define policy, billing, payment, notice, service, and outcome event payloads.
- [x] Add valid and invalid contract examples.
- [x] Implement a deterministic seeded generator for 100 policies.
- [x] Implement point-in-time state reconstruction.
- [x] Test event ordering, valid transitions, impossible dates, and deterministic replay ([issue #10](https://github.com/anilreddy89/Inforsight/issues/10)).
- [x] Publish a small sample dataset and `DATA_CARD.md` ([issue #12](https://github.com/anilreddy89/Inforsight/issues/12)).
- [x] Assess aggregate synthetic rates against cited public references and document calibration assumptions ([issue #14](https://github.com/anilreddy89/Inforsight/issues/14)).

Phase 1 is complete for the repository's documented MVP boundary. The broader 14-week planning materials also envisioned issue age, face amount, acquisition channel, recurring multi-period exposure, payment retries, reinstatement, maturity, loans, cash value, account changes, and prior conservation attempts. Those concepts remain intentionally deferred rather than silently treated as implemented. Phase 2.01 must decide which, if any, are required for a defensible baseline experiment and route each required addition through a separate versioned contract and generator change.

## Phase 2 - Baseline ML

- [x] Define the Phase 2 modeling contract and data-sufficiency gate: active-policy eligibility, observation cadence, 90-day horizon, lapse-versus-surrender label policy, censoring, required observable fields, and any Phase 1 contract extensions that must be completed before training ([issue #16](https://github.com/anilreddy89/Inforsight/issues/16), [PR #17](https://github.com/anilreddy89/Inforsight/pull/17)).
- [x] Build deterministic observation records with an `as_of` timestamp and explicit effective-time and ingestion-time visibility rules so every feature represents information available by the observation cutoff ([issue #16](https://github.com/anilreddy89/Inforsight/issues/16), [PR #17](https://github.com/anilreddy89/Inforsight/pull/17)).
- [x] Add automated leakage and simulator-shortcut tests that reject post-cutoff events, labels or terminal outcomes in features, future ingestion, scenario identifiers, deterministic outcome proxies, and duplicate outcome episodes ([issue #18](https://github.com/anilreddy89/Inforsight/issues/18)).
- [x] Create deterministic, policy-aware temporal train, validation, and test splits with documented chronological boundaries, `policy_id` and outcome-episode isolation, horizon-overlap embargo rules, class distributions, versioned split manifests, and assertions that prevent random policy-month, future-to-past, or outcome-episode leakage; perform no fitting, resampling, threshold selection, or calibration with test data ([issue #20](https://github.com/anilreddy89/Inforsight/issues/20), [PR #21](https://github.com/anilreddy89/Inforsight/pull/21)).
- [x] Implement a versioned feature-building and preprocessing pipeline with a feature dictionary covering types, missingness, provenance, allowed transformations, and deterministic regeneration; distinguish stateless domain transformations from learned preprocessing, fit imputers, encoders, scalers, selectors, and other learned transforms on training data only, freeze them for validation and test application, and test that held-out data cannot alter fitted parameters ([issue #22](https://github.com/anilreddy89/Inforsight/issues/22), [PR #23](https://github.com/anilreddy89/Inforsight/pull/23)).
- [x] Train and document a seeded logistic-regression baseline as the transparent benchmark ([issue #24](https://github.com/anilreddy89/Inforsight/issues/24), [PR #25](https://github.com/anilreddy89/Inforsight/pull/25)).
- [x] Freeze one seeded LightGBM or XGBoost configuration before inspecting its results, fit it on the exact Phase 2.04 training matrix only, and compare it with the Phase 2.05 logistic-regression benchmark on identical train and validation observations using the same predeclared metrics. Pin the selected dependency, prohibit validation-driven hyperparameter search and preprocessing refits, keep the canonical test partition sealed, publish deterministic comparison artifacts, and label all results `pipeline_engineering_only` while `LIM-002-001` remains unresolved ([issue #26](https://github.com/anilreddy89/Inforsight/issues/26), [PR #27](https://github.com/anilreddy89/Inforsight/pull/27)).
- [x] Run leakage-aware feature sanity and shortcut diagnostics on the frozen splits, including training-only univariate mutual information, validation-scored single-feature shallow models, identifier/cardinality checks, and targeted permutation or ablation tests; record an explicit allow, exclude, or investigate decision for each flagged feature without treating correlation alone as proof of leakage ([issue #28](https://github.com/anilreddy89/Inforsight/issues/28), [PR #29](https://github.com/anilreddy89/Inforsight/pull/29)).

Phases 2.01 through 2.07 remain valid historical pipeline-engineering increments. An independent review after Phase 2.07 found claim-blocking data-design limitations, correctness defects, and a bypassable test-scoring guard. The v1 canonical test fixture was prediction-accessed during that review, although no test metric was computed and no repository artifact was changed. It is therefore a review-exposed historical fixture, not an untouched release holdout.

## Phase 2R - Modeling Foundation Remediation Gate

Phase 2R is a required remediation gate between Phase 2.07 and performance-dependent Phase 2 work. Assign every R2-00 through R2-11 issue to the existing [**v0.2.0-risk-model**](https://github.com/anilreddy89/Inforsight/milestone/3) GitHub milestone. R2 is an internal sequencing and acceptance gate within that release milestone, not a separate milestone. Create one focused issue and pull request for each item below; do not place all remediation in one branch or reopen completed Phase 2 pull requests.

### Pause boundary

- **P2-08 probability calibration and threshold evaluation is paused.** Calibration plumbing may be unit-tested only inside a separately approved remediation issue; no Phase 2.08 experiment artifact or performance conclusion may be published before a merged replacement acceptance decision records `proceed`.
- **P2-09 SHAP or equivalent attribution is paused.** Explanation plumbing may be unit-tested only with clearly marked fixtures; no v1 feature importance may be interpreted as a substantive risk mechanism.
- P2-10 through P2-12 remain pending. Model-specific artifact freezing, a final evaluation, a model decision, and a release marker cannot proceed before a merged replacement acceptance decision records `proceed`.
- The v1 generator, observations, splits, and model artifacts remain immutable historical evidence. Phase 2R adds separately versioned contracts and artifacts rather than rewriting prior evidence.
- No new final release holdout may be materialized, inspected, transformed, or scored until a later dedicated one-shot release issue authorizes it after the replacement candidate is frozen.

### Dependency and merge order

```text
R2-00
  -> R2-01 -> R2-02 -> R2-03
  -> R2-04
  -> R2-05
  -> R2-06
  -> R2-07
  -> R2-08
  -> R2-09
  -> R2-10
  -> R2-11
  -> resume governed Phase 2 work
```

For this solo-developer repository, follow the order strictly even where implementation could be parallelized. Start each dependent branch from updated `main` only after the preceding pull request merges. See the [engineering improvement workflow](engineering-improvement-workflow.md#phase-2r-branching-and-merge-strategy).

### R2-00 - Reconcile review findings and establish truthful status

**Status:** Completed on 2026-08-28 by [PR #30](https://github.com/anilreddy89/Inforsight/pull/30), merge commit `4292743`. The GitHub issue was created after the implementation PR; add its link to the change tracker when the issue number is confirmed.

**Outcome:** Repository-facing status, claim boundaries, and ownership accurately describe the independent review and the Phase 2R gate.

**Scope:**

- Add `LIM-002-002` for the absence of a designed pre-cutoff feature-to-outcome risk mechanism in v1.
- Add `LIM-002-003` for the bypassable scoring guard and prediction access to the v1 test fixture.
- Reconcile `README.md`, this backlog, the limitation register, the change tracker, experiment indexes, and affected historical status language.
- Preserve historical artifacts while clearly distinguishing the state recorded at creation from the state discovered during later review.
- Assign R2 ownership, dependencies, paused work, and resume conditions.

**Acceptance checks:**

- [x] No current repository status describes the v1 test fixture as untouched or `sealed_not_scored` without historical qualification.
- [x] P2-08 and P2-09 are visibly paused in every authoritative current-status location.
- [x] `LIM-002-001`, `LIM-002-002`, and `LIM-002-003` identify owners, blocked claims, allowed work, and objective closure evidence.
- [x] Completed Phase 2.01-2.07 evidence remains unchanged and is labeled `pipeline_engineering_only` where interpreted.
- [x] Documentation links and repository checks pass.

**Out of scope:** Fixing generator, schema, scoring, or statistical behavior.

### R2-01 - Bind generation to exact configuration, provenance, and run identity

**Status:** Completed on 2026-08-28 through [issue #33](https://github.com/anilreddy89/Inforsight/issues/33) and [PR #34](https://github.com/anilreddy89/Inforsight/pull/34), merge commit `c9c9c88`.

**Outcome:** Generated histories are controlled by the exact versioned configuration reported in provenance, and identifiers are unique within a deterministic run namespace.

**Scope:**

- Change the public generation API to consume the exact `GeneratorConfig` rather than reconstructing defaults from selected fields.
- Bind provenance and returned histories to the same canonical configuration and generator version.
- Introduce a deterministic run namespace or require an explicit dataset namespace so different configured runs cannot silently reuse policy and event identifiers.
- Add migration notes where deterministic public output intentionally changes; do not overwrite v1 artifacts.

**Acceptance checks:**

- [x] A custom `simulation_start` changes generated issuance dates and matches recorded provenance.
- [x] Configuration fields that affect generation are covered by regression or property tests.
- [x] Repeating the same namespaced configuration is byte deterministic.
- [x] Different run namespaces cannot collide on policy or event identifiers in the tested corpus.
- [x] Existing v1 fixtures remain reproducible through their documented legacy path or are explicitly version-pinned as historical.
- [x] Focused tests and `make check` pass.

**Depends on:** R2-00. **Blocks:** R2-02 and every v2 generator artifact.

### R2-02 - Enforce structural and semantic observation invariants

**Status:** Completed on 2026-08-28 through [issue #36](https://github.com/anilreddy89/Inforsight/issues/36) and [PR #37](https://github.com/anilreddy89/Inforsight/pull/37), merge commit `7b23f1c`. Six contract tests, 195 simulator tests, all artifact checks, and repository-boundary checks pass. The implementation scope and acceptance evidence are defined in `Documents/phase-02r-02-structural-and-semantic-observation-invariants.md`.

**Outcome:** Serialized observations and runtime domain objects cannot represent contradictory label, eligibility, feature, or provenance states.

**Scope:**

- Add mutually exclusive JSON Schema variants or equivalent conditionals for outcome status, value, censoring reason, and label provenance.
- Enforce eligibility-to-feature consistency and strict schema-version and currency rules.
- Add runtime invariants to `ObservationRecord` and `OutcomeLabel` construction.
- Provide one composite public ingress validator that applies event JSON Schema validation before cross-event history semantics.
- Retain narrowly named internal validators where useful, but document their boundary.

**Acceptance checks:**

- [x] Contradictory observed-positive, observed-negative, right-censored, and eligibility combinations fail schema validation.
- [x] The same contradictions fail runtime construction or composite ingress validation.
- [x] Invalid schema versions, unsupported currencies, and unexpected properties fail through the documented public ingress path.
- [x] Existing valid examples and published v1 artifacts continue to validate.
- [x] Negative contract tests, runtime tests, and `make check` pass.

**Depends on:** R2-01. **Blocks:** R2-03 and the v2 observation contract.

### R2-03 - Harden scoring authorization and retire the v1 fixture as a release holdout

**Status:** Completed on 2026-08-28 through [issue #39](https://github.com/anilreddy89/Inforsight/issues/39) and [PR #40](https://github.com/anilreddy89/Inforsight/pull/40), merge commit `5eb67c1`. Ten focused authorization tests, 205 simulator tests, six contract tests, all artifact checks, and repository-boundary checks pass.

**Outcome:** Changing a caller-controlled partition label cannot authorize prediction or evaluation, and the release holdout boundary is explicit and auditable.

**Scope:**

- Bind permitted scoring membership, row identity, feature contract, preprocessing identity, and matrix digest to frozen fitted state or a verified evaluation manifest.
- Make `dataclasses.replace(..., partition="validation")` and equivalent relabeling fail for logistic, boosted, and diagnostic scoring paths.
- Separate ordinary inference from labeled experiment partitions; do not require a user-editable partition string as authorization.
- Record the v1 test fixture as review-exposed prediction-only historical evidence; never claim that it was re-sealed.
- Specify that the eventual v2 final holdout remains unavailable until the release candidate and one-shot evaluation protocol are frozen.

**Acceptance checks:**

- [x] Direct and relabeled unauthorized matrices fail before prediction.
- [x] Authorized validation matrices succeed only when membership, purpose, feature contract, preprocessing identity, and digests match frozen evidence.
- [x] Logistic, boosted, diagnostics, and reload paths share the same authorization invariant.
- [x] Negative tests cover relabeling, row substitution, reordering, feature substitution, target substitution, authorization tampering, and digest mismatch.
- [x] No final test metric was computed as part of this issue.
- [x] Focused tests and `make check` pass.

**Depends on:** R2-02. **Blocks:** R2-04 and any future final-test protocol.

### R2-04 - Approve the versioned v2 statistical simulator and observation design

**Status:** Completed on 2026-08-29 through [issue #42](https://github.com/anilreddy89/Inforsight/issues/42) and [PR #43](https://github.com/anilreddy89/Inforsight/pull/43), merge commit `1fc48ad`. Both CI runs passed; no v2 result or final holdout was created.

**Outcome:** A reviewed ADR and versioned contract define a modeling corpus that can test known statistical behavior without changing the v1 coverage fixture.

**Scope:**

- Define intended use, prohibited claims, the estimand, prediction time, label horizon, unit of observation, and censoring policy.
- Define multiple issuance cohorts, recurring exposure and observations, behavior visible before prediction, stochastic feature-conditioned hazard, latent noise, and oracle probabilities.
- Define missingness, ingestion delay, corrections, late arrival, unknown categories, and temporal drift mechanisms.
- Define separate dataset roles for model fitting, selection, calibration, and final one-shot testing.
- Predeclare structural, negative-control, signal-recovery, uncertainty, and robustness acceptance tests before implementation results are inspected.
- Decide which richer lifecycle fields are genuinely required; keep unrelated future architecture deferred.

**Acceptance checks:**

- [x] The ADR records alternatives, tradeoffs, compatibility, versioning, and why v1 remains a coverage fixture.
- [x] Every generated outcome has a documented stochastic mechanism and, where applicable, an oracle probability.
- [x] Pre-cutoff observable drivers can affect risk without creating deterministic outcome proxies.
- [x] Cohort, recurrence, censoring, missingness, and temporal-shift mechanisms are testable from the contract.
- [x] Holdout creation and access rules are specified before any v2 final-test data exists.
- [x] The R2-07 protocol, number of seeds or folds, metrics, uncertainty method, and decision rules are predeclared.

**Depends on:** R2-03. **Blocks:** R2-05. Use the architecture-decision issue template for the ADR and a linked implementation issue for the versioned contract if both cannot remain one reviewable change.

### R2-05 - Implement the v2 modeling corpus and recurring observations

**Status:** Completed on 2026-08-29 through [issue #45](https://github.com/anilreddy89/Inforsight/issues/45) and [PR #46](https://github.com/anilreddy89/Inforsight/pull/46), merge commit `25c370d`. CI and the deterministic v2 corpus check passed; the final holdout remains `not_materialized`.

**Outcome:** A separately versioned deterministic generator and observation builder implement the approved v2 statistical design.

**Scope:**

- Implement multiple issuance cohorts and recurring policy exposure across sufficient calendar duration.
- Generate varied pre-cutoff payments, failures, recoveries, notices, contacts, changes, and state transitions according to the approved scope.
- Implement the stochastic risk mechanism, latent noise, oracle probability, censoring, missingness, ingestion delay, and correction behavior from R2-04.
- Produce recurring point-in-time observations without future effective-time or ingestion-time visibility.
- Publish a v2 data card and deterministic provenance without changing v1 fixtures or manifests.

**Acceptance checks:**

- [ ] Same configuration, namespace, and seed reproduce byte-identical v2 histories and observations.
- [ ] Multiple cohorts and recurring observations exist with sufficient pre-cutoff behavioral variation.
- [ ] Oracle probabilities and realized outcomes follow the versioned contract without leaking oracle or scenario fields into model features.
- [ ] Point-in-time mutation tests reject future effective and ingestion information.
- [ ] Missingness, censoring, delay, correction, and unknown-category fixtures cover approved edge cases.
- [ ] Schema, runtime, deterministic-generation, leakage, and full repository checks pass.

**Depends on:** R2-04. **Blocks:** R2-06.

### R2-06 - Rebuild temporal evaluation data, features, and baselines on v2

**Status:** Completed on 2026-08-29 through [issue #48](https://github.com/anilreddy89/Inforsight/issues/48) and [PR #49](https://github.com/anilreddy89/Inforsight/pull/49), merge commit `58232fc`. Both hosted CI runs passed. Deterministic v2 folds, feature/preprocessing state, diagnostics, frozen baseline comparison, runtime explicit-state reload, portable artifacts, and authorization evidence are on `main`; the final holdout remains `not_materialized` and R2-07 is unblocked.

**Outcome:** Versioned v2 split, feature, preprocessing, logistic, and boosted artifacts are regenerated under the approved evaluation protocol without overwriting v1 evidence.

**Scope:**

- Create the predeclared chronological folds or partitions for fitting, selection, calibration, and inaccessible final testing.
- Preserve the 90-day horizon embargo, policy and outcome-episode isolation, and train-only learned preprocessing.
- Ensure supported billing frequencies and relevant feature distributions overlap sufficiently across non-final evaluation periods.
- Re-run feature diagnostics, null screens, identifiers/cardinality checks, and baseline comparisons on v2.
- Namespace all v2 artifacts and bind them to generator, observation, split, feature, preprocessing, and model versions.

**Acceptance checks:**

- [x] Split manifests prove chronology, embargo compliance, zero policy overlap, and zero outcome-episode overlap.
- [x] Every supported billing-frequency category appears in each required non-final modeling partition or fold.
- [x] Train-constant and unseen-category findings have explicit allow, exclude, investigate, or redesign dispositions.
- [x] Logistic and boosted candidates use identical governed memberships and metrics.
- [x] Preprocessing is fitted only on the approved training data for each fold.
- [x] The final release holdout remains inaccessible and unscored.
- [x] All v2 artifacts regenerate deterministically and `make check` passes.

**Depends on:** R2-05. **Blocks:** R2-07.

### R2-07 - Run the predeclared statistical acceptance gate

**Status:** Completed on 2026-08-30 through [issue #51](https://github.com/anilreddy89/Inforsight/issues/51) and [PR #52](https://github.com/anilreddy89/Inforsight/pull/52), merge commit `66ae092`. The fail-closed readiness gate records `stop` before model fitting because its structural fixture detects post-cutoff ingestion leakage. Seven independent readiness failures require versioned redesign. No acceptance metrics were generated, the final holdout remains `not_materialized`, and P2-08/P2-09 remain paused.

**Outcome:** Governed multi-seed and temporal evidence determines whether v2 is suitable for resuming calibration and model interpretation.

**Scope:**

- Run the predeclared multi-seed or repeated-corpus protocol and report distributions with uncertainty rather than isolated point estimates.
- Run null-signal and label-shuffle controls, oracle-risk recovery, learning curves, ablations, missingness and unknown-category stress, and rolling-origin stability checks.
- Compare observed results only with the acceptance rules frozen in R2-04; do not revise gates after seeing results.
- Publish an evidence manifest, report, and explicit proceed, redesign, or stop decision.
- Evaluate closure evidence for `LIM-002-001` and `LIM-002-002`; keep `LIM-002-003` open until the final-holdout protocol is proven through its authorized release workflow.

**Acceptance checks:**

- [ ] Null-signal and label-shuffle behavior is consistent with chance within the predeclared uncertainty rule.
- [ ] Known simulated signal is recovered consistently across seeds and temporal folds according to the predeclared rule.
- [ ] Results include uncertainty, learning behavior, failure cases, and sensitivity to missingness, categories, and temporal shift.
- [x] No final release holdout is materialized or scored during acceptance testing.
- [x] Every claim is limited to protocol readiness and synthetic pipeline correctness unless a later governed external-data protocol supports more.
- [x] The decision note identifies which limitations remain open and which findings require corrective redesign, with objective evidence links.
- [x] Reproduction commands and full repository checks pass locally; hosted CI and merge evidence remain pending.

**Depends on:** R2-06. **Blocks:** R2-08 and performance-dependent work.

### R2-08 - Approve the v3 statistical substrate and replacement acceptance protocol

**Status:** Completed on 2026-08-30 through [issue #53](https://github.com/anilreddy89/Inforsight/issues/53) and [PR #54](https://github.com/anilreddy89/Inforsight/pull/54), merge commit `09f678a`. ADR 0005, contract `3.0.0`, random-stream registry `1.0.0`, and acceptance protocol `2.0.0` are approved; no v3 output or final holdout was created.

**Outcome:** A reviewed ADR, v3 substrate contract, and acceptance protocol `2.0.0` replace the unexecutable v2 statistical boundary without rewriting historical evidence or generating replacement results.

**Scope:**

- Freeze event-first dual-time reconstruction and feature lineage.
- Separate scenario-invariant stream-set, complete artifact, and execution identities.
- Freeze the random-stream, coefficient, driver-group, candidate-selection, resampling, shuffle, learning-subset, robustness, and decision registries.
- Use a new 20-seed block and 14,400-policy design while preserving the three folds, minimum support, metrics, uncertainty count, and numeric thresholds.
- Map every R2-07 finding to a normative correction and planned falsification test.

**Acceptance checks:**

- [x] ADR 0005 records the replacement, alternatives, compatibility, claim boundary, and reversal conditions.
- [x] Contract `3.0.0` defines event-first dual-time construction, exact identities/streams, equations, roles, and authorization.
- [x] Protocol `2.0.0` resolves all caller-controlled R2-07 ambiguities before v3 output exists.
- [x] Protocol `1.0.0`, the R2-07 `stop` evidence, and all v1/v2 artifacts remain unchanged.
- [x] No v3 output or final holdout is generated; P2-08/P2-09 remain paused.
- [x] Pull-request review and merge evidence are recorded; the issue closed on merge.

**Depends on:** R2-07. **Blocks:** R2-09.

### R2-09 - Implement the v3 event-first corpus and observations

**Status:** Completed on 2026-08-30 through [issue #56](https://github.com/anilreddy89/Inforsight/issues/56) and [PR #57](https://github.com/anilreddy89/Inforsight/pull/57), merge commit `89c2291`. The deterministic v3 manifest records 14,400 policies and 76,545 event-first recurring observations; all hosted checks passed and the final holdout remains `not_materialized`.

Implement contract `3.0.0`, including event-first generation, dual-time reconstruction, exact oracle sidecars, identities, stream registry, atomic interventions, and deterministic mutation/equality tests. Produce no model or final holdout.

**Depends on:** R2-08. **Blocks:** R2-10.

### R2-10 - Rebuild v3 evaluation, features, candidates, and selection

**Status:** Completed on 2026-09-01 through issues #59–#61 and [PR #62](https://github.com/anilreddy89/Inforsight/pull/62), merge commit `36c17b7`. Both hosted CI runs passed. Historical failed evidence remains immutable and the final holdout remains `not_materialized`.

Build governed v3 folds, feature/preprocessing state, diagnostics, authorization, both frozen candidates, deterministic selection evidence, and readiness inputs. The authoritative structural gate passes with 1,498 episodes from 787 selection policies; repeated episodes are not new independent-policy capacity, and policy remains the resampling cluster. Diagnostics return `allow` and the frozen rule selects XGBoost. Produce no acceptance metric or final holdout, and limit claims to synthetic candidate selection rather than prospective real-world validation.

**Depends on:** R2-09. **Blocks:** R2-11.

### R2-11 - Run replacement statistical acceptance protocol 2.2.0

**Status:** Completed on 2026-09-01 through [issue #64](https://github.com/anilreddy89/Inforsight/issues/64) and [PR #65](https://github.com/anilreddy89/Inforsight/pull/65), merge commit `76c8cd3`. The mechanical decision is `redesign`; P2-08/P2-09 remain paused and the final holdout remains `not_materialized`.

Run readiness first, then all predeclared controls and statistical rules only if readiness passes. Publish exactly one `proceed`, `redesign`, or `stop` decision. The final holdout remains `not_materialized`.

All 20 signal/null pairs pass structural readiness. Authorized primary scoring records `0/20` signal seeds at median-fold AUC `>=0.65`, an across-seed median signal AUC near `0.519` against `0.68`, and `0/20` matched-null improvements at least `0.10`. Later required families terminated after this decisive failure and are explicitly failed as incomplete. The resulting decision is `redesign`; P2-08/P2-09 remain paused.

**Depends on:** R2-10. **Blocks:** P2-08 and P2-09 unless the merged decision is `proceed`.

### Phase 2R completion gate

The original Phase 2R sequence could complete only when R2-00 through R2-11 were
merged in order and the R2-11 decision was `proceed`. R2-11 instead decided
`redesign`, so the gate remains open until a reviewed replacement sequence records
a merged `proceed`. A favorable single seed, a passing unit-test suite, or a
manually accepted limitation is not sufficient. P2-08 and P2-09 remain paused and
P2-10 through P2-12 remain blocked.

### Phase 2R v4 redesign extension (triggered by R2-11)

R2-11 decided `redesign`, so the completion gate remains closed. The proposed
replacement sequence is R2-12 through R2-16: authorize bounded diagnostics on a
separate development seed block, diagnose and approve a versioned v4 design,
implement and qualify the substrate, freeze evaluation and one candidate, and run
a fresh acceptance seed block exactly once. The detailed scope, boundaries,
hypotheses, and acceptance checks are defined in the
[v4 signal-recovery redesign plan](modeling/phase-02r-12-v4-redesign-plan.md).

```text
merge R2-11 -> R2-12 -> R2-13 -> R2-14 -> R2-15 -> R2-16
             diagnostics   design/implementation   fresh acceptance
```

- [x] **R2-12 - Close out v3 and approve redesign diagnostics:** Completed on 2026-09-01 through [issue #66](https://github.com/anilreddy89/Inforsight/issues/66) and [PR #67](https://github.com/anilreddy89/Inforsight/pull/67), merge commit `ea9cf1f`. Preserve the
  R2-11 block as spent acceptance evidence and freeze a disjoint development
  diagnostic boundary before changing the substrate.
- [x] **R2-13 - Diagnose signal recovery and approve v4:** Completed on 2026-09-02 through [issue #69](https://github.com/anilreddy89/Inforsight/issues/69) and [PR #70](https://github.com/anilreddy89/Inforsight/pull/70), merge `7c4a1a7`. All 20 development seeds diagnose H1/H2 as supported, H3/H4/H6 as rejected, and H5 as unresolved. ADR 0007, substrate `4.0.0`, and protocol `3.0.0` freeze the reviewed v4 design under the [phase document](../Documents/phase_docs/phase-02r-13-v4-signal-recovery-diagnostics-and-design.md).
- [x] **R2-14 - Implement and qualify v4:** Completed on 2026-09-02 through
  [issue #72](https://github.com/anilreddy89/Inforsight/issues/72) and
  [PR #73](https://github.com/anilreddy89/Inforsight/pull/73), merge
  `4b234bf`. Separate v4 paths and all 20 development seeds complete, but the
  mechanical decision is `redesign`: observable-oracle recovery, probability
  quality, reference recovery, and hazard validity fail. R2-15 remains blocked;
  future acceptance and the final holdout remain `not_materialized`.
- [x] **R2-14A - Close out v4 and authorize post-v4 redesign diagnostics:** Completed on 2026-09-03 through [issue #76](https://github.com/anilreddy89/Inforsight/issues/76) and [PR #77](https://github.com/anilreddy89/Inforsight/pull/77), merge `52c03c8`. ADR 0008 and contract `1.0.0` freeze the 17-diagnostic inventory and disjoint seed domains without producing replacement results.
- [x] **R2-14B - Execute post-v4 diagnostics and evaluate feasibility surface:** Completed on 2026-09-03 through [issue #78](https://github.com/anilreddy89/Inforsight/issues/78) and [PR #79](https://github.com/anilreddy89/Inforsight/pull/79), merge `3088c4c`. Fail-closed readiness found contract `1.0.0` does not freeze mechanical H1-H5 disposition thresholds required by ADR 0008. The governed record contains zero executed units and zero D16 cells, leaves every hypothesis unresolved, and records `stop_contract_not_executable`; ADR 0009 accepted.
- [x] **R2-14BA - Close out R2-14B readiness stop and approve amended v5 diagnostic contract:** Completed on 2026-09-03 through [issue #80](https://github.com/anilreddy89/Inforsight/issues/80) and [PR #81](https://github.com/anilreddy89/Inforsight/pull/81), merge commit `627e698`. ADR 0010 and amended contract `1.1.0` freeze complete quantitative hypothesis disposition truth tables before diagnostic result access.
- [x] **R2-14C - Generation v6 bounded sigmoid hazard link architecture and substrate contract:** Completed on 2026-09-04 through [issue #86](https://github.com/anilreddy89/Inforsight/issues/86) and [PR #87](https://github.com/anilreddy89/Inforsight/pull/87), merge commit `18ce32f`. ADR 0012 approves the bounded logistic hazard link $\lambda(t) = \lambda_{\max}\sigma(z)$, mathematically guaranteeing total monthly hazard $\le 0.1500 < 0.2000$ and breaking the Proportional Hazards Trilemma. Approved Contract `6.0.0` ([contract](modeling/phase-02r-14c-v6-bounded-sigmoid-substrate-contract.md)) with Coefficient Registry `3.0.0` and isolated development seeds `20280201..20280220`. Contract validation script `scripts/check_r2_14c_v6_contract.py` and unit tests pass. Authorizes Phase 2R.14D.
- [x] **R2-14D - Generation v6 substrate implementation and qualification:** Completed on 2026-09-04 through [issue #88](https://github.com/anilreddy89/Inforsight/issues/88) and [PR #89](https://github.com/anilreddy89/Inforsight/pull/89), merge commit `89ec94a`. Implemented v6 bounded sigmoid simulator modules (`v6_config.py`, `v6_corpus.py`, `v6_qualification.py`), runner `scripts/run_v6_qualification.py`, and unit test suite. Executed 120-unit qualification across all 20 development seeds `20280201..20280220`. All qualification gates pass (median AUC = 0.7086 >= 0.70, AP lift = 0.1398 >= 0.10, Brier skill = 0.0745 > 0, max hazard = 0.14999 <= 0.1500 < 0.20, matched null = 0.5000 in [0.45, 0.55], zero parity mismatches, deterministic replay). Published qualification manifest, report, and decision. Mechanical decision: `qualified`. Authorizes Phase 2R.15.
- [x] **R2-15 - Freeze replacement evaluation and candidate:** Completed on 2026-09-04 through [issue #90](https://github.com/anilreddy89/Inforsight/issues/90) and [PR #91](https://github.com/anilreddy89/Inforsight/pull/91), merge commit `8965c72`. Built governed Generation v6 chronological folds (`fold_1`..`fold_3`, `selection`), fit-only preprocessing, 17-feature point-in-time extraction with event lineage validation, non-final feature diagnostics (`decision: allow`, 0 flags), deterministic candidate selection (Logistic Regression selected over XGBoost, ROC AUC: 0.7057 vs 0.6801, Brier: 0.1287 vs 0.1354), and froze all memberships, preprocessor states, model states, and scoring authorizations into cryptographic digests. Clean-room invariants strictly preserved (acceptance outcomes unobserved, reserved acceptance seeds 20271201..20271220 untouched, final holdout unmaterialized). Authorizes Phase 2R.16.
- [x] **R2-16A - Generation v6 acceptance remediation and protocol 3.1.0 amendment:** Completed on 2026-09-04 through [issue #94](https://github.com/anilreddy89/Inforsight/issues/94) and [PR #95](https://github.com/anilreddy89/Inforsight/pull/95), merge commit `4d7e9da`. Adopted ADR 0013 and approved Statistical Acceptance Protocol `3.1.0` addressing secondary rule calibration while keeping all primary signal recovery gates intact. Re-evaluation executed across all 120 inventory units under Protocol `3.1.0`. All 10 rule families passed 100% (candidate median AUC 0.7031, AP lift +0.1344, Brier skill +0.0658, 20/20 seeds consistent). Mechanical decision: `proceed`. Clean-room holdout remains `not_materialized`. Phase 2 is now officially unpaused and authorized to resume.

## Phase 2 - Baseline ML resumed after Phase 2R

- [x] **P2-08 - Probability calibration and operational thresholds:** Completed on 2026-09-04 through [issue #96](https://github.com/anilreddy89/Inforsight/issues/96) and [PR #97](https://github.com/anilreddy89/Inforsight/pull/97), merge commit `3abb044`. Following the merged `proceed` decision of Phase 2R.16A (PR #95), fit Platt scaling and isotonic regression strictly on the 8,560-row `calibration` partition of seed `20280201` and evaluated out-of-sample on `non_final_evaluation` (8,782 rows). Platt scaling selected (ECE 0.0115 <= 0.0300, slope 0.9498 in [0.85, 1.15], Brier 0.1211, AUC 0.6998 exact rank preservation). Established 4 operational risk tiers and triage queues (Top 1% achieves 34.09% precision / 2.23x lift; Top 5% intercepts 11.57% of lapses). 1,000 policy-cluster bootstrap CIs and decision curve analysis verified. Final holdout strictly `not_materialized`. Authorizes P2-09.
- [x] **P2-09 - Model-behavior explanations:** Completed on 2026-09-04 through [issue #98](https://github.com/anilreddy89/Inforsight/issues/98) and [PR #99](https://github.com/anilreddy89/Inforsight/pull/99), merge commit `29b9aca`. Following the frozen calibrated candidate model and feature contract, published exact additive log-odds feature attributions and centered SHAP values (exact logit reconstruction residual < 1e-10; observed 1.78e-15), evaluated 100% of directional sanity checks (17/17 passed against domain principles), published global feature rankings (`rolling_on_time_rate` rank 1 at 22.78%), and generated local waterfall profiles for representative policies across Low, Moderate, and High risk tiers. Enforced strict ADR 0002 boundaries disclaiming causal claims and prohibiting autonomous conservation outreach without Tier 2 eligibility checks and Tier 4 human approval. Used only approved non-final evaluation data (seed 20280201); final release holdout remains strictly `not_materialized`. Authorizes P2-10.
- [x] **P2-10 - Artifact and environment reproducibility:** Completed on 2026-09-04 through [issue #100](https://github.com/anilreddy89/Inforsight/issues/100) and [PR #101](https://github.com/anilreddy89/Inforsight/pull/101), merge commit `7112e82`. Unified fitted preprocessor transformations (13 numeric scalers + 4 categorical one-hot encoders = 28 features), linear model weights (Logistic Regression, L2, C=1.0, liblinear, seed 20260817), Platt calibrator parameters (A=0.961849, B=-0.033420), explainer background baseline (E[z]=-0.7107, E[p]=0.3295), and operational decision policies (4 risk tiers, 3 review queues, ADR 0002 action boundaries) into an immutable, pure-JSON release model bundle (`phase-02-10-model-bundle.json`). Built standalone `BundledInferenceEngine` in `bundle.py` with pure NumPy scoring and zero runtime scikit-learn dependency; verified bit-for-bit reload reproduction across all 8,782 out-of-sample observations ($\max |\hat{p}_{\text{reloaded}} - \hat{p}_{\text{original}}| = 2.22 \times 10^{-16} \le 1.00 \times 10^{-12}$; $\max |z_{\text{reloaded}} - z_{\text{original}}| = 8.88 \times 10^{-16} \le 1.00 \times 10^{-12}$; 100% operational tier concordance). Locked Python runtime and dependency lock hashes. 392 safety tests pass; clean-room holdout remains strictly `not_materialized`. Authorizes P2-11.
- [x] **P2-11 - Final evaluation, model card, and decision note:** Completed on 2026-09-04 through [issue #102](https://github.com/anilreddy89/Inforsight/issues/102) and [PR #103](https://github.com/anilreddy89/Inforsight/pull/103), merge commit `ec363d6` (squashed `8ac7aed`). Pre-registered evaluation contract `1.0.0` was approved and frozen before executing the one-shot out-of-sample evaluation on 8,782 observations (1,440 policies) using standalone `BundledInferenceEngine`. 1,000 policy-cluster bootstrap CIs confirmed ROC AUC 0.6998 [0.6847, 0.7153] (Gate G1 >= 0.6800), Average Precision 0.2765 [0.2560, 0.2994] (Gate G2 >= 0.2500), Brier score 0.1211 [0.1170, 0.1252], ECE 0.0115 <= 0.0300 (Gate G3), slope 0.9498 in [0.85, 1.15] (Gate G4), Top 1% review queue precision 34.09% (Gate G5 >= 0.3000, 2.23x lift), and Top 5% review queue lift 2.31x (Gate G6 >= 2.00x, 11.57% recall). 100% of acceptance gates passed (G1-G6). Published root `MODEL_CARD.md` (Mitchell et al. 2019), cryptographic manifest `phase-02-11-final-evaluation-manifest.json`, quantitative report `phase-02-11-final-evaluation-report.md`, and Phase 2 decision note `phase-02-11-phase-2-decision-note.md` recording formal release determination `RELEASE`. Resolved limitations `LIM-002-001`, `LIM-002-002`, and `LIM-002-003` in `docs/limitations.md`. Final holdout remains strictly unmaterialized. Unblocks P2-12 (`v0.2.0-risk-model` release tag).
- [x] **P2-12 - Release marker and notes:** Completed on 2026-09-05 through [issue #104](https://github.com/anilreddy89/Inforsight/issues/104) and [PR #105](https://github.com/anilreddy89/Inforsight/pull/105), merge commit `7797c09` (squashed `df5d8e8`). Following the formal `RELEASE` determination of Phase 2.11, published milestone release documentation [`docs/release-notes/v0.2.0-risk-model.md`](release-notes/v0.2.0-risk-model.md) capturing the pure-JSON release model bundle `inforsight-v6-logistic-platt-20260817` (SHA-256 `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`), standalone zero-dependency inference engine `BundledInferenceEngine`, 100% passing acceptance gate scorecard (Gates G1-G6), explainability attributions, 4 operational risk tiers, and high-lift review queues. Prepared annotated Git tag `v0.2.0-risk-model` and milestone closeout instructions, officially completing Phase 2 (Baseline ML) and enabling Phase 3 (Policy Conservation Decision Engine).

## Phase 3 - Policy Conservation Decision Engine & Intervention Orchestration

Phase 3 transitions Inforsight from pure risk estimation to **governed decision intelligence and intervention orchestration**. It consumes the frozen, pure-JSON release candidate model bundle `inforsight-v6-logistic-platt-20260817` and standalone `BundledInferenceEngine` from Phase 2 ([`v0.2.0-risk-model`](https://github.com/anilreddy89/Inforsight/releases/tag/v0.2.0-risk-model)).

All Phase 3 work operates under the hard authority boundary established in [**ADR 0002**](adr/0002-separate-risk-from-action-eligibility.md): **no predictive model or autonomous agent possesses authority to execute customer outreach or alter an in-force policy**. Probabilistic risk perception is strictly decoupled from deterministic action eligibility, case evidence assembly, cost-utility optimization, and mandatory human review.

Assign every P3-01 through P3-10 issue to GitHub Milestone #4 ([**v0.3.0-decision-engine**](https://github.com/anilreddy89/Inforsight/milestone/4)). Follow the sequential, test-driven merge order: each increment merges to `main` before the next branch begins.

### Dependency and execution flow

```text
P3-01 (Domain Contracts & Action Taxonomy)
  ├──> P3-02 (Deterministic Action Eligibility Rules Engine)
  │      ├──> P3-03 (Cost-Utility & Uplift Optimization Matrix)
  │      │      └──> P3-08 (Counterfactual Simulation & Off-Policy Eval) ───────┐
  │      └──> P3-05 (Bounded Case Intelligence: Template -> LLM)               │
  └──> P3-04 (Model Serving & Inference Gateway)                               │
         └──> P3-04A (Model Monitoring & Drift Detection Architecture)         │
                └──> P3-05                                                     │
                       └──> P3-06 (HITL Workflow & Audit Trail Engine)         │
                              └──> P3-07 (Interactive Dashboard, with OPE) ───┤
                                     └─────────────────────────────────────────┴──> P3-09 (System Qualification)
                                                                                      └──> P3-10 (Release v0.3.0)
```

### P3-01 - Conservation domain contracts and action taxonomy

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Status:** Completed on 2026-09-05 through [issue #106](https://github.com/anilreddy89/Inforsight/issues/106) and [PR #107](https://github.com/anilreddy89/Inforsight/pull/107), merge commit `7ed7efd`. 20 contract tests pass. · [Phase document](../Documents/phase_docs/phase-03-01-conservation-domain-contracts-and-action-taxonomy.md)

**Outcome:** Versioned JSON Schema contracts define allowed conservation actions, case state transitions, and audit event envelopes before any business logic is written.

**Scope:**
- Create `data-contracts/conservation-action.schema.json` defining standard intervention types:
  - `courtesy_reminder`: Automated low-friction touchpoint (SMS / Email) for early-stage friction.
  - `grace_period_consultation`: Structured advisory session for policyholders in active grace period.
  - `specialist_phone_outreach`: High-touch consultation by licensed conservation specialist.
  - `payment_method_remediation`: Direct resolution of EFT/credit card payment method failures.
  - `abstain`: Explicit "Do Not Disturb" decision for non-salvageable or self-curing policies.
- Define action attributes: direct financial cost $c(a)$, required personnel hours, channel constraints, regulatory cooling-off windows, and minimum/maximum policy tenure requirements.
- Create `data-contracts/conservation-case-event.schema.json` formalizing the case lifecycle state machine (`CREATED` -> `TRIAGED` -> `EVIDENCE_ASSEMBLED` -> `RECOMMENDED` -> `HUMAN_REVIEWED` -> `EXECUTED` / `DISMISSED` -> `RESOLVED`).
- Add positive and negative contract examples, schema validation tests, and contract documentation.

**Acceptance checks:**
- [x] Schema validation tests verify all valid action types and reject malformed actions.
- [x] Illegal state transitions (e.g., executing without human review approval) fail contract validation.
- [x] Action schema enforces positive non-zero cost and valid operational channel enumerations.
- [x] Existing event and observation contracts remain unaffected.
- [x] Schema tests and `make check` pass.

**Blocks:** P3-02, P3-04.

---

### P3-02 - Deterministic action eligibility rules engine

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Status:** Completed on 2026-09-05 through [issue #108](https://github.com/anilreddy89/Inforsight/issues/108) and [PR #109](https://github.com/anilreddy89/Inforsight/pull/109), merge commit `1177394`. 17 focused eligibility tests pass, 412 simulator tests pass. · [Phase document](../Documents/phase_docs/phase-03-02-deterministic-action-eligibility-rules-engine.md)

**Outcome:** A pure deterministic rules engine enforces business, legal, and regulatory constraints on intervention actions, completely decoupled from ML risk scores.

**Scope:**
- Implement `simulator/rules/` rule evaluator consuming policy point-in-time state and applicant metadata.
- Enforce hard deterministic eligibility boundaries ([ADR 0002](adr/0002-separate-risk-from-action-eligibility.md)):
  - **Grace Period Invariant:** High-touch specialist outreach requires active grace period status (`active_grace_period_flag == 1`) or imminent grace threshold.
  - **Legal / Dispute Freeze:** Policies with active claims, legal holds, or registered disputes are strictly disqualified from all conservation actions (`disqualify_all`).
  - **Regulatory Contact Limits:** Enforce TCPA / DNC compliance, state-specific outreach hours, and mandatory 30-day contact cooling-off windows.
  - **Communication Preferences:** Honor policyholder opt-outs across SMS, email, and phone channels.
  - **Policy Viability:** Exclude terminated, surrendered, or matured policies.
- Fail-closed design: missing or ambiguous state attributes disqualify the action with an auditable disqualification reason code (`DISQUALIFIED_<REASON>`).
- Output an immutable `EligibleActionSet` with explicit eligibility rationale for every evaluated action.

**Acceptance checks:**
- [x] Active legal dispute or claim freezes all outreach actions deterministically.
- [x] Channel opt-outs disqualify the respective communication medium.
- [x] Contact fatigue rule rejects outreach if contact occurred within the 30-day window.
- [x] Missing required state attributes results in safe abstention, never unauthorized action.
- [x] Engine has zero dependency on model prediction scores or probability thresholds.
- [x] Property-based rule tests and `make check` pass.

**Depends on:** P3-01. **Blocks:** P3-03, P3-05, P3-08.

---

### P3-03 - Cost-utility and uplift optimization matrix

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Outcome:** An economic optimization engine allocates eligible conservation actions to maximize net preserved value under strict specialist capacity and budget constraints.

**Scope:**
- Implement uplift / treatment-effect decision logic categorizing policyholders across 4 operational quadrants:
  - *Persuadables / Salvageable:* High risk, high treatment responsiveness $\rightarrow$ prioritize for outreach.
  - *Lost Causes:* High risk, near-zero treatment responsiveness $\rightarrow$ avoid wasting high-touch resources.
  - *Sure Things:* Low risk, self-curing billing hiccups $\rightarrow$ avoid unnecessary outreach expense.
  - *Sleeping Dogs:* Policies where intervention triggers adverse lapse decisions $\rightarrow$ enforce strict abstention.
- Formulate Expected Value of Intervention:
  $$\mathbb{E}[U(a \mid x)] = \Delta p_{\text{lapse}}(a, x) \cdot V_{\text{policy}} - c(a)$$
  where $V_{\text{policy}}$ is policy lifetime value / annual premium, $\Delta p_{\text{lapse}}$ is estimated treatment effect, and $c(a)$ is direct action cost.
- Solve the constrained resource allocation problem (Knapsack / Greedy Rank-Ordering) subject to operational capacity:
  - Specialist Call Queue Capacity: $\sum \mathbf{1}_{\{a = \text{specialist}\}} \le K_{\text{specialist}}$ (e.g. Top 1% queue capacity).
  - Monthly Outreach Budget: $\sum c(a) \le B_{\text{total}}$.
- Provide deterministic tie-breaking and rank reproducibility.

**Acceptance checks:**
- [x] Optimization ranking respects strict specialist capacity cutoffs without queue overflow.
- [x] Negative expected utility ($\mathbb{E}[U] \le 0$) defaults to `abstain`.
- [x] Priority queue allocation is byte-deterministic across identical input portfolios.
- [x] High-risk "Lost Causes" are successfully diverted from scarce specialist phone queues.
- [x] Unit and optimization benchmarks pass.

**Depends on:** P3-01, P3-02. **Blocks:** P3-05, P3-07, P3-08.

---

### P3-04 - Model serving and inference gateway

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Outcome:** A high-throughput, zero-dependency REST inference gateway wraps the frozen pure-JSON model bundle with strict input validation and explicit authority bounds.

**Scope:**
- Implement lightweight FastAPI service (`serving/`) hosting `BundledInferenceEngine`.
- Provide endpoints:
  - `GET /health`: Engine status, bundle digest verification (`7ac292...`), dependency check.
  - `GET /v1/model/info`: Bundle metadata, feature contract, calibration parameters, operational tiers.
  - `POST /v1/score`: Single observation point-in-time scoring.
  - `POST /v1/score/batch`: Vectorized batch scoring for triage queue generation.
- Response payload strictly enforces ADR 0002 boundary:
  ```json
  {
    "policy_id": "POL-10492",
    "calibrated_probability": 0.3842,
    "operational_tier": "TIER_3_HIGH_RISK",
    "feature_attributions": { ... },
    "authorized_to_act": false,
    "action_authority_boundary": "ADR_0002_REQUIRES_HUMAN_REVIEW"
  }
  ```
- Sub-millisecond latency target per single scoring request with zero scikit-learn dependency at runtime.
- Provide Docker containerization, health probes, and OpenAPI / Swagger documentation.

**Acceptance checks:**
- [x] Reloaded model produces bit-for-bit identical probabilities to frozen Phase 2.11 evaluation.
- [x] Every response payload includes explicit `authorized_to_act: false` marker.
- [x] Invalid schema versions or missing required features return structured 422 HTTP validation errors.
- [x] P99 latency $< 5\text{ms}$ for single policy scoring.
- [x] API integration tests and Docker build pass.

**Depends on:** P3-01, P2-10. **Blocks:** P3-04A, P3-05, P3-07.

---

### P3-04A - Model monitoring and drift detection architecture

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Outcome:** A formal design specification and diagnostics telemetry architecture to detect feature distribution drift, calibration decay, and scoring anomalies in production.

**Scope:**
- Specify input feature drift monitoring using Population Stability Index (PSI) and Characteristic Stability Index (CSI) against frozen Phase 2.11 training baseline distributions:
  - Green (stable): $\text{PSI} < 0.10$.
  - Yellow (moderate shift): $0.10 \le \text{PSI} < 0.25$.
  - Red (significant drift): $\text{PSI} \ge 0.25$ triggers automated triage alerting and human model-risk review.
- Specify calibration decay tracking: rolling Expected Calibration Error (ECE) and Brier Score over sliding observation windows (e.g. rolling 500 cases).
- Design `/v1/diagnostics` endpoint schema for the FastAPI gateway:
  - Reports inference volume, latency percentiles (P50, P95, P99), active PSI per feature, and rolling calibration error.
- Define automated fail-safe fallback policies: when critical drift is flagged on primary risk drivers (e.g. `rolling_on_time_rate`), the engine flags scoring uncertainty and requires specialist confirmation for high-stakes actions.

**Acceptance checks:**
- [x] Design document specifies mathematical formulations for PSI, CSI, and rolling window ECE tracking.
- [x] Gateway contract specifies OpenAPI schema for `GET /v1/diagnostics`.
- [x] Predeclared drift thresholds and alert action matrix are formally documented.
- [x] Repository checks pass.

**Depends on:** P3-04. **Blocks:** P3-05, P3-07.

---

### P3-05 - Bounded case intelligence assistant (Template-first & optional LLM)

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Outcome:** An evidence-assembly assistant synthesizes structured, fact-grounded "Conservation Case Briefs" for customer service specialists using a deterministic template foundation, augmented by an optional grounded LLM narrative layer.

**Scope:**
- **Layer 1: Deterministic Template Engine (Core Foundation):**
  - Implement rule-and-template briefing engine in `simulator/assistant/`.
  - Ingests point-in-time event history, calibrated risk score, SHAP attributions, eligible action set, and utility ranking.
  - Deterministically formats structured Case Briefs (Markdown/JSON). Completely testable with zero hallucination risk by construction.
- **Layer 2: LLM-Enhanced Narrative Layer (Responsible Generative Augmentation):**
  - Synthesizes natural-language case summaries, contextual talking points, and customer-empathy guidance.
  - Implements an automated **Grounding Guard / Post-Processing Validator**: verifies that every cited fact, date, count, amount, or notice directly matches an entity in the reconstructed history. Ungrounded claims are automatically rejected or redacted.
- Generates standard Case Brief sections:
  - **Executive Summary:** Core risk drivers stated in plain language.
  - **Factual Timeline:** Chronological event highlights leading up to observation cutoff.
  - **Intervention Recommendations:** Ordered list of eligible actions with pros/cons and talking points.
  - **Mandatory Disclaimer:** Draft status clearly displayed (`status: PENDING_HUMAN_REVIEW`).

**Acceptance checks:**
- [x] Layer 1 deterministic template produces 100% reproducible, testable briefs with zero hallucination.
- [x] Layer 2 LLM post-processing validator rejects or redacts ungrounded entities not present in event history.
- [x] Disqualified actions never appear as recommended interventions in the brief.
- [x] Brief outputs clearly state advisory status and prohibit automated outreach execution.
- [x] Factual grounding verification tests pass on representative synthetic cases.
- [x] Unit tests and `make check` pass.

**Depends on:** P3-02, P3-03, P3-04, P3-04A. **Blocks:** None (P3-06, P3-07 unblocked).

---

### P3-06 - Human-in-the-loop workflow and audit trail engine

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Outcome:** A human-in-the-loop (HITL) review state machine orchestrates specialist decisions and records an immutable, append-only audit trail for regulatory compliance.

**Scope:**
- Implement conservation case workflow engine:
  - **Specialist Review Actions:** `APPROVE_RECOMMENDATION`, `OVERRIDE_ACTION`, `REQUEST_MORE_INFO`, `REJECT_AND_CLOSE`.
  - **Reviewer Identity & Justification:** Require valid reviewer ID, timestamp, and mandatory structured rationale for overrides.
- Create append-only cryptographic audit logger (`conservation-audit-log.jsonl`):
  - Records observation snapshot, model score, eligible action set, case brief digest, human decision, rationale, and resulting intervention event.
  - Each audit entry contains a SHA-256 hash chaining to the preceding entry (hash-chained audit ledger) to guarantee tamper-evidence.
- Point-in-time audit replay: build verification tool `scripts/verify_conservation_audit_trail.py` proving full historical reconstruction.

**Acceptance checks:**
- [x] Actions cannot transition to execution without recorded human approval and reviewer credentials.
- [x] Overrides without structured justification are rejected.
- [x] Tampering with historical audit log entries breaks hash-chain verification.
- [x] Audit trail reproduces exact decision context from historical point in time.
- [x] Workflow and audit tests pass.

**Depends on:** P3-05. **Blocks:** None (P3-07, P3-09 unblocked).

---

### P3-07 - Interactive conservation intelligence dashboard

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Status:** Completed on 2026-09-05 through [issue #120](https://github.com/anilreddy89/Inforsight/issues/120) and [PR #121](https://github.com/anilreddy89/Inforsight/pull/121), merge commit `dddf889`. 9/9 dashboard unit and smoke tests pass, cryptographic audit trail verification passes with 100% integrity, and repository boundaries pass. Specification and scorecard documented in `Documents/phase_docs/phase-03-07-interactive-conservation-intelligence-dashboard.md`.

**Outcome:** A lightweight, interactive web application provides conservation teams with a living operational demonstration of the end-to-end decision intelligence platform, including triage queues, case dossiers, and counterfactual business impact.

**Scope:**
- Implement interactive Streamlit application (`dashboard/`):
  - **Executive Portfolio View:** Portfolio risk distribution across tiers, active grace period counts, queue capacity utilization, and projected retention ROI (displaying P3-08 OPE results).
  - **Triage Queue Table:** Filterable, prioritized queue of policies (Top 1%, 5%, 20%) with calibrated risk, primary risk driver, eligible actions, and net utility rank.
  - **Case Investigation Dossier:** Deep-dive view for a selected policy:
    - Interactive SHAP waterfall chart explaining risk drivers.
    - Interactive point-in-time event timeline.
    - Case Brief (template or LLM-grounded) with talking points and action options.
  - **Specialist Decision Console:** Interactive action approval panel (Approve / Override / Reject) with real-time feedback and live append to audit log.
- Wire dashboard directly to `BundledInferenceEngine`, rules evaluator, P3-08 simulation results, and v6 synthetic cohort.

**Acceptance checks:**
- [x] Dashboard loads and runs locally without external cloud dependencies.
- [x] Selecting different triage tiers dynamically updates queue tables and capacity meters.
- [x] Submitting a human decision immediately logs a valid, hash-chained audit entry.
- [x] Displays both point-in-time case intelligence and offline policy evaluation (OPE) metrics.
- [x] UI automated smoke tests pass.

**Depends on:** P3-03, P3-04, P3-04A, P3-05, P3-06. **Blocks:** None (P3-08, P3-09 unblocked).

---

### P3-08 - Counterfactual simulation and offline policy evaluation

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Status:** Completed on 2026-09-05 through [issue #122](https://github.com/anilreddy89/Inforsight/issues/122) and [PR #123](https://github.com/anilreddy89/Inforsight/pull/123), merge commit `55f0415`. 11/11 counterfactual and OPE unit tests pass, Decision Engine achieves $13,764 Net Preserved Value (2.92x ROCS, p < 0.0001 superiority vs baselines) across 1,000 bootstrap CIs, and repository boundaries pass. Specification and scorecard documented in `Documents/phase_docs/phase-03-08-counterfactual-simulation-and-offline-policy-evaluation.md`.

**Outcome:** A counterfactual simulation framework rigorously evaluates the business impact and ROI of the conservation decision engine against baseline triage strategies prior to dashboard integration.

**Scope:**
- Analytically independent from UI: run as reproducible offline simulation scripts (`scripts/run_offline_policy_evaluation.py`).
- Extend Generation v6 simulation engine to support synthetic intervention responses (counterfactual potential outcomes):
  - Baseline hazard: $\lambda_0(t) = \lambda_{\max}\sigma(z)$.
  - Post-intervention hazard: $\lambda_a(t) = \lambda_{\max}\sigma(z + \gamma_a)$, where $\gamma_a$ represents intervention effect by action type.
  - Heterogeneous treatment effect: effectiveness modulated by policyholder tenure, past payment reliability, and contact frequency.
- Conduct Offline Policy Evaluation (OPE):
  - Compare Decision Engine (Uplift + Eligibility + HITL) against:
    - *Heuristic Policy:* Simple rule-based triage (e.g. grace period only).
    - *Naive ML Policy:* Triage purely by risk score without uplift or eligibility constraints.
    - *Random Triage:* Uniform random outreach within budget.
- Quantify key business metrics: Lapse Rate Reduction (lift), Net Preserved Annual Premium, Cost-per-Conserved-Policy, and Return on Conservation Spend (ROCS).
- Export summary results for consumption by P3-07 dashboard.

**Acceptance checks:**
- [x] Counterfactual simulation maintains strict temporal consistency and no future leakage.
- [x] Decision engine demonstrates statistically significant improvement in Net Preserved Value over naive ML and heuristic baselines.
- [x] Off-policy evaluation includes 95% bootstrap confidence intervals.
- [x] Produces exportable summary metrics consumed by P3-07 dashboard.
- [x] Simulation reproducibility tests pass across multiple seeds.

**Depends on:** P3-02, P3-03. **Blocks:** None (P3-09 unblocked).

---

### P3-09 - End-to-end system qualification and integration gate

**Status:** Completed on 2026-09-06 through [issue #124](https://github.com/anilreddy89/Inforsight/issues/124) and [PR #125](https://github.com/anilreddy89/Inforsight/pull/125), merge commit `ae34848`. All 6 System Qualification Gates (S1–S6) passed 100% across 1,000 synthetic test policies with canonical pipeline digest `209a4c1f2b3fee5a551d724e5841cf857abecd3c669f797f17f130deaaf62d90`. The implementation scope and acceptance evidence are defined in `Documents/phase_docs/phase-03-09-end-to-end-system-qualification-and-integration-gate.md`.

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Outcome:** A rigorous, automated pre-release qualification suite verifies that the integrated decision engine enforces all architectural invariants and passes all operational gates.

**Scope:**
- Build system-level integration test suite (`simulator/tests/test_phase_03_qualification.py`):
  - End-to-end flow: Raw Event Stream $\rightarrow$ Point-in-Time Reconstruction $\rightarrow$ Bundle Scoring $\rightarrow$ Deterministic Eligibility $\rightarrow$ Uplift Ranking $\rightarrow$ Case Brief Assembly $\rightarrow$ HITL Review $\rightarrow$ Audit Logging.
- Pre-register and enforce 6 System Qualification Gates:
  - **Gate S1 (Authority Isolation):** 100% of automated outreach attempts without human credentials fail with security exception.
  - **Gate S2 (Eligibility Invariant):** 100% of policies with active legal dispute or missing required evidence are disqualified from outreach.
  - **Gate S3 (Budget & Capacity Adherence):** Queue allocations strictly observe operational capacity limits ($0\%$ overflow).
  - **Gate S4 (Audit Tamper Resistance):** Any mutation of audit log records is detected by cryptographic hash-chain verification.
  - **Gate S5 (Inference Latency):** P99 inference latency $\le 10\text{ms}$ under 50-policy batch load.
  - **Gate S6 (Reproducibility):** End-to-end decision pipeline reproduces bit-for-bit results under fixed seeds.
- Publish formal Qualification Report and cryptographic artifact manifest.

**Acceptance checks:**
- [x] All 6 System Qualification Gates (S1–S6) pass 100%.
- [x] Zero invariant violations across 1,000 synthetic test policies.
- [x] All unit, integration, and property tests pass in CI.
- [x] Qualification manifest generated with SHA-256 digests.

**Depends on:** P3-06, P3-07, P3-08. **Blocks:** None (P3-10 unblocked).

---

### P3-10 - Milestone release marker and notes (v0.3.0-decision-engine)

**Status:** Completed on 2026-09-06 through [issue #126](https://github.com/anilreddy89/Inforsight/issues/126) and [PR #127](https://github.com/anilreddy89/Inforsight/pull/127). Comprehensive milestone release notes published in `docs/release-notes/v0.3.0-decision-engine.md`, formal Phase 3 Decision Note in `docs/experiments/phase-03-10-phase-3-decision-note.md` (unanimous `RELEASE`), release tag `v0.3.0-decision-engine` prepared, and Milestone #4 closed at 100% completion.

**Milestone:** [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4)

**Outcome:** Formal release documentation, architecture decision summary, and milestone closeout for `v0.3.0-decision-engine`.

**Scope:**
- Author comprehensive milestone release notes: `docs/release-notes/v0.3.0-decision-engine.md`.
- Document complete system architecture, decision engine operational guide, API specifications, and HITL governance standards.
- Prepare annotated Git release tag `v0.3.0-decision-engine`.
- Close GitHub Milestone #4 ([`v0.3.0-decision-engine`](https://github.com/anilreddy89/Inforsight/milestone/4)).
- Update root `README.md`, `docs/backlog.md`, and interactive roadmap (`docs/roadmap/app.js`).
- Author Phase 3 decision note and transition roadmap for Phase 4 (Enterprise Integration & Scale).

**Acceptance checks:**
- [x] Release notes document all Phase 3 capabilities, gates, and performance metrics.
- [x] Milestone #4 reaches 100% completion on GitHub.
- [x] Annotated Git tag `v0.3.0-decision-engine` created and verified.
- [x] All documentation links, schema validators, and full CI suite pass.

**Depends on:** P3-09. **Blocks:** Phase 4 inception.

---

## Review hardening initiative

### Purpose

This initiative converts the findings in `Documents/Project_Review_Through_P4-01.md` into a governed correctness and contract-hardening program. It is a separate maintenance release track, not Phase 4 work. This backlog section is the canonical source for RH scope, order, status, and acceptance gates.

The initiative protects the Phase 0-3 reference implementation before Phase 4 ports or distributes its behavior. P4-01 remains a completed architecture-inception increment, but its affected contracts are provisional until this initiative amends them. P4-02 through P4-07 remain in the Phase 4 backlog and do not absorb the work below.

### Release and work identifiers

- **GitHub milestone:** [`v0.3.1-decision-engine-hardening`](https://github.com/anilreddy89/Inforsight/milestone/6) (Milestone #6)
- **Stable work prefix:** `RH`
- **Release type:** post-Phase 3 maintenance and correctness release
- **Source review:** `Documents/Project_Review_Through_P4-01.md`, reviewed at commit `b15a9ba`
- **Relationship to Phase 4:** independent track and prerequisite gate for P4-02/P4-03; not a renumbering or extension of Phase 4
- **Plan approval:** approved to begin on 2026-09-07 in `Documents/Hardening_Plan_Approval_and_Phase4_Gates.md`, subject to the acceptance refinements incorporated below
- **Charter decision:** `ADOPT` recorded in [issue #133](https://github.com/anilreddy89/Inforsight/issues/133) on 2026-09-07

Milestone #6 was created after RH-00 recorded `ADOPT`. Keep the milestone title, eventual Git tag, release title, and release-notes filename aligned.

### Governing boundaries

All RH work follows `CONTRIBUTING.md`, `.github` issue and pull-request templates, and `docs/engineering-improvement-workflow.md`.

1. GitHub Issues own active work; this document owns initiative order and dependency gates.
2. One stable RH ID maps to one issue, one branch, and one primary pull request.
3. Every implementation issue starts with a failing or missing focused test where practical.
4. Contract or durable architecture changes require a design or decision issue before implementation.
5. Historical artifacts remain immutable. Corrected results receive new versions and explicit supersession notes.
6. No issue may claim production certification, external validity, realized profit, complete factual grounding, universal tamper resistance, or measured distributed performance without evidence that directly establishes that claim.
7. Clean-room, point-in-time, human-authority, and holdout boundaries remain mandatory.
8. Phase 4 branches must not copy semantics that are still under RH revision.
9. Implement only the minimum bounded reference behavior needed to establish each invariant; this initiative must not become a second platform build.
10. Where an RH outcome requires separate design and implementation, use linked child IDs `<RH-ID>D` and `<RH-ID>I`. Each child has its own issue, branch, and primary pull request; the parent outcome closes only after both children close.

For example, `RH-01D` owns the canonical snapshot design and `RH-01I` owns its implementation. Design children merge before implementation children. This resolves the one-ID/one-PR rule without combining distinct design and implementation changes.

### Scope and exit criteria

The initiative covers every technical, scientific-interpretation, maintainability, CI, and documentation finding in the review. It does not implement Kafka, Java control-plane services, production connectors, PostgreSQL, Kubernetes, or cloud deployment.

The initiative is complete only when:

- all RH issues are merged and closed;
- the canonical domain snapshot, authority, safety, economics, allocation, serving, monitoring, grounding, audit, and contract invariants have adversarial regression coverage;
- release-relevant dashboard, serving, simulator, contract, and artifact-verification checks run in CI;
- affected evidence is regenerated under new versions or explicitly retained with corrected claim boundaries;
- README, backlog, roadmap, limitation register, model card, release notes, and phase documents agree on current status;
- a read-only qualification run passes from a clean environment; and
- a formal RH-13 decision records `PROCEED` before P4-02 or P4-03 implementation starts.

### Dependency and merge flow

```text
RH-00  Initiative charter, claim freeze, and overlap triage
  |
RH-01D/I  Canonical domain snapshot and shared semantic contracts
  |\
  | +--> RH-02  Fail-closed safety evidence
  | +--> RH-04D/I  Shared economics and signed treatment effects
  | +--> RH-06D/I  Inference-only runtime packaging
  | +--> RH-09D    P4-01 interface amendment draft
  |
RH-02 --> RH-03  Transition-boundary authority enforcement
RH-04 --> RH-05D/I  Portfolio allocation and optimizer validation
RH-06 --> RH-07  Evidence-bearing monitoring
RH-01 --> RH-08D/I  Structured grounding and bounded narratives
RH-03 --> RH-10D/I  Durable audit semantics and recovery contract

RH-03 + RH-04 + RH-05 + RH-06 + RH-08 + RH-10
  --> RH-09I  Final reconciled P4-01 contracts

RH-03 + RH-05 + RH-07 + RH-08 + RH-09I + RH-10
  --> RH-11  Qualification, CI, and read-only verification
  --> RH-12  Evidence regeneration and documentation reconciliation
  --> RH-13  Hardening release decision and Phase 4 resume gate
```

Independent issues may be prepared in parallel, but a dependent implementation branch starts from updated `main` only after its predecessor merges. RH-11, RH-12, and RH-13 are sequential closeout gates.

### Work breakdown

#### RH-00 - Charter the hardening release and reconcile existing work

**Issue template:** Architecture decision
**Classification:** Architecture decision / governance
**Priority:** Release blocking

**Status:** Implemented locally through [issue #133](https://github.com/anilreddy89/Inforsight/issues/133) on branch `docs/133-rh-00-hardening-charter`; the issue records `ADOPT`, Milestone #6 is active, overlap issues are amended, documentation is reconciled, and verification passes with the documented headless plotting override. Merge remains required.

**Outcome:** Approve this initiative as an independent `v0.3.1-decision-engine-hardening` release, freeze overstated claims while work is open, and decide how open issues #128, #129, and #130 participate.

**Acceptance checks:**

- [x] The milestone, stable IDs, dependency graph, and Phase 4 pause boundary are approved.
- [x] Issues #128-#130 are reviewed field by field and assigned explicit RH dispositions in the RH-00 phase document.
- [x] Claim restrictions while RH is open are recorded in `docs/limitations.md`.
- [x] P4-01 remains historical evidence; P4-02/P4-03 are marked blocked by RH-13.
- [x] No application or distributed-infrastructure implementation is included.

#### RH-01 - Establish the canonical point-in-time domain snapshot and semantic catalog

**Issue template:** Design specification followed by Implementation task
**Classification:** Current defect and durable contract
**Priority:** Release blocking

**Outcome:** Reconstruct a typed domain snapshot from original events using `effective_at` and `ingested_at`, while separating untransformed domain values from model features. Version one canonical catalog for risk tiers, policy statuses, action identifiers, feature units, action costs, and durations.

**Acceptance checks:**

- [ ] Events not visible at an observation cutoff cannot affect a snapshot, dossier, rule, narrative, or valuation.
- [ ] Premium frequency, tenure, grace state, and other domain values derive from source events without model clipping or transforms.
- [ ] `IN_GRACE`/`grace_period`, risk-tier direction, combined-termination/lapse naming, feature preprocessing identity, costs, and duration units have canonical definitions.
- [ ] Heterogeneous-policy, future-effective, and delayed-ingestion fixtures fail before the repair and pass after it.
- [ ] Compatibility and version migration are documented.

#### RH-02 - Make missing safety evidence fail closed

**Issue template:** Implementation task
**Classification:** Current defect
**Priority:** Release blocking

**Outcome:** Distinguish unknown safety facts from confirmed false values and require sufficient evidence before an action or channel becomes eligible. Permissive defaults remain only in explicitly labeled synthetic fixtures.

**Acceptance checks:**

- [ ] Missing claim, legal-hold, dispute, opt-out, and DNC facts cannot be interpreted as permission.
- [ ] Rules declare which evidence each action/channel requires.
- [ ] Minimal and partial contexts have fail-closed regression tests.
- [ ] Dashboard and service adapters stop manufacturing false safety facts.
- [ ] Positive eligibility fixtures contain explicit evidence rather than relying on defaults.
- [ ] New holds, opt-outs, disputes, safety facts, or snapshot changes invalidate affected approval and execution eligibility.

#### RH-03 - Enforce human authority at the common transition boundary

**Issue template:** Implementation task
**Classification:** Current defect / authority invariant
**Priority:** Release blocking

**Outcome:** Make every path to `EXECUTED` enforce eligible action, authenticated review, authorization, freshness, capacity, and authoritative action/channel metadata at the common state transition boundary.

**Acceptance checks:**

- [ ] Direct and wrapper-based transition bypasses fail.
- [ ] Missing, stale, mismatched, replayed, and concurrent approvals fail deterministically.
- [ ] Caller metadata cannot override authoritative action or channel fields.
- [ ] Library tests and the strengthened authority qualification gate cover every public execution path.
- [ ] Trusted actor identity remains a server-context contract; request-supplied identity alone is insufficient.
- [ ] Approval binds the case version, reviewed snapshot/evidence digest, action, channel, recommendation/model version, and trusted actor.
- [ ] Execution preserves the historical reviewed snapshot while separately revalidating current eligibility and evidence.
- [ ] Changed action, incompatible case revision, expired approval, or newly received hold/opt-out requires renewed approval.
- [ ] The local actor adapter and its trust assumptions are explicit; production identity federation remains Phase 4 work.

#### RH-04 - Preserve signed treatment effects and unify economics

**Issue template:** Design specification followed by Implementation task
**Classification:** Current defect and durable contract
**Priority:** Release blocking

**Outcome:** Preserve harmful as well as beneficial treatment effects, use versioned shared cost/resource assumptions, and explicitly map combined termination risk to lapse and surrender economics.

**Acceptance checks:**

- [ ] Harmful treatment contributes a negative gross value rather than being clipped to zero.
- [ ] Rules, OPE, optimizer, dashboard, and reports consume or explicitly bridge one versioned economics/resource contract.
- [ ] Personnel capacity is represented in a single unit without integer truncation.
- [ ] Annual premium preserved is distinguished from profit and modeled expected value from realized value.
- [ ] Harmful, neutral, and beneficial treatment fixtures pass.
- [ ] The primary economic estimand is predeclared before regenerated results are inspected: uncertainty conditional on frozen assignments, performance of the allocation procedure on new portfolios, or both as separately labeled results.
- [ ] Reallocated-portfolio resampling defines cluster identity, duplicate handling, and whether budgets/hours remain fixed or scale with portfolio size.
- [ ] Predictive models are never refit on evaluation resamples.
- [ ] Sensitivity analysis varies intervention efficacy, costs, and harmful effects; fixed-effect bootstrap intervals are not presented as uncertainty in those assumptions.

#### RH-05 - Enforce capacity and validate the allocation algorithm

**Issue template:** Design specification followed by Implementation task
**Classification:** Current defect and algorithm clarification
**Priority:** High

**Outcome:** Apply portfolio allocation before dashboard recommendations and cases are emitted; either validate a deterministic greedy heuristic against an exact small-instance reference or replace it with an exact solver appropriate to the declared scope.

**Acceptance checks:**

- [ ] Dashboard allocation never silently exceeds hours or budget; any infeasibility/overflow is shown numerically.
- [ ] Summaries refresh after decisions and derive from actual allocations.
- [ ] Exhaustive small fixtures quantify optimality gap and marginal opportunity cost.
- [ ] Fractional personnel hours and shared budgets are enforced consistently.
- [ ] Documentation names the implemented algorithm truthfully.
- [ ] Before evaluation, the issue declares either an acceptable small-instance optimality gap or acceptance of a feasibility-preserving heuristic without an optimality claim.
- [ ] The engine is compared with non-intervention, operational rules-only, and risk-ranked strategies using the same cohort, decision cutoff, eligibility rules, action catalog, budget, and personnel units.
- [ ] Specialist overrides recheck eligibility and atomically reserve/release hours and money; concurrent decisions cannot consume the same capacity twice.

#### RH-06 - Extract and verify an inference-only runtime package

**Issue template:** Design specification followed by Implementation task
**Classification:** Packaging defect / refactor
**Priority:** High

**Outcome:** Provide an independently installable inference runtime whose import, startup, health, and score paths do not import or require training/evaluation packages.

**Acceptance checks:**

- [ ] A clean environment can import and score without scikit-learn, training modules, or evaluation modules.
- [ ] Explicitly configured missing bundle paths fail loudly.
- [ ] Startup verifies the loaded bundle against a trusted expected digest/version.
- [ ] The serving Dockerfile targets the real application, contains required runtime assets, and exposes matching routes and environment variables.
- [ ] Scaffold-only Java/gRPC services remain labeled non-runnable until implemented.

#### RH-07 - Make monitoring states evidence-bearing

**Issue template:** Implementation task
**Classification:** Current defect / test gap
**Priority:** High

**Outcome:** Retain bounded scored-feature windows, ingest resolved outcomes through an operational interface, and report `insufficient_data` until drift or calibration claims have adequate evidence.

**Acceptance checks:**

- [ ] Actual scoring traffic populates version-keyed drift windows.
- [ ] Outcomes join by policy, observation, and model version through an exposed interface.
- [ ] Empty or undersized windows cannot report `well_calibrated` or perfect skill.
- [ ] Tests demonstrate drift after scoring traffic and calibration after resolved outcomes.
- [ ] Scope is reconciled with open monitoring issue #129.

#### RH-08 - Bind narratives to structured evidence

**Issue template:** Design specification followed by Implementation task
**Classification:** Current defect / safety boundary
**Priority:** High

**Outcome:** Render factual case-brief fields deterministically from the canonical snapshot and restrict generated prose to a constrained statement grammar whose claims resolve to typed evidence identifiers. Unsupported statement types reject or fall back to deterministic templates.

**Acceptance checks:**

- [ ] Unsupported identifiers, amounts, dates, durations, percentages, actions, authorizations, causal claims, and status assertions fail validation.
- [ ] A grounding hash is described only as input/text consistency evidence, not proof that the input is true.
- [ ] Adversarial external-provider fixtures are required before enabling a non-deterministic provider.
- [ ] The documented validator coverage exactly matches enforced checks.
- [ ] Keeping the external provider disabled is an acceptable outcome; no issue is required to prove arbitrary generated prose true.
- [ ] Adversarial results are described as evidence for declared grammar/field coverage, never as a universal hallucination guarantee.

#### RH-09 - Amend P4-01 contracts before dependent implementation

**Issue template:** Architecture decision and Design specification
**Classification:** Architecture decision / contract defect
**Priority:** Release blocking for P4-02/P4-03

**Outcome:** Amend ADR 0014, Protobuf, and OpenAPI contracts so authority presence, tier semantics, authentication, concurrency, idempotency, override rules, preprocessing identity, economics/resource versions, audit semantics, errors, and deployment claims are explicit before Java or Kafka work begins. RH-09D may draft after RH-01; RH-09I must reconcile the settled RH-03, RH-04, RH-06, and RH-10 specifications before merge.

**Acceptance checks:**

- [ ] Authority uses presence-aware representation (`optional` or explicit enum) and rejects absent/unknown authorization states.
- [ ] Risk tiers map identically across the released model, Protobuf, OpenAPI, and canonical catalog.
- [ ] Authentication/security schemes, trusted reviewer identity, idempotency keys, expected case versions, conditional override requirements, and errors are machine-verifiable where feasible.
- [ ] Network/identity enforcement is specified separately from topology.
- [ ] RPC latency remains a target until measured through a deployed path.
- [ ] Contract compilation, linting, and compatibility tests pass.

#### RH-10 - Specify and harden audit durability semantics

**Issue template:** Design specification followed by bounded Implementation task
**Classification:** Latent/current defect and P4 prerequisite
**Priority:** High

**Outcome:** Accurately bound current integrity claims and implement a concrete reference persistence mechanism selected in RH-10D: either a transactional local store, or a deliberately single-writer append protocol with documented crash recovery. Define trusted checkpoints, suffix-truncation detection, writer coordination, atomic state/audit persistence, and recovery semantics without requiring P4 PostgreSQL/KMS infrastructure.

**Acceptance checks:**

- [ ] Current unkeyed hash-chain behavior is described as integrity checking relative to a trusted tip/length.
- [ ] Suffix deletion, middle mutation, reorder, replay, and concurrent-writer cases are tested.
- [ ] Workflow state and audit history recover consistently after restart/failure in the reference implementation.
- [ ] P4-04 owns PostgreSQL/KMS realization; RH owns semantics, reference behavior, and adversarial fixtures.
- [ ] Failure between state and audit updates, restart, stale checkpoint, suffix truncation, and second-writer rejection/coordination are covered.
- [ ] The trusted checkpoint is protected by a separately stated trust boundary; a tip stored beside the writable log is not claimed to resist an attacker controlling both.

#### RH-11 - Expand qualification, CI, and read-only artifact verification

**Issue template:** Implementation task
**Classification:** Test gap / tooling defect
**Priority:** Release blocking

**Outcome:** Make CI and qualification establish the revised release claims across contracts, simulator, serving, dashboard, runtime packaging, and adversarial boundaries without mutating published evidence in check mode.

**Acceptance checks:**

- [ ] CI installs and runs dashboard and serving suites plus all release-relevant `make check` targets.
- [ ] Streamlit AppTest covers meaningful interactions, capacity, point-in-time, and post-decision refresh behavior.
- [ ] Clean-image runtime smoke, API/interface tests, contract compile/lint, authority bypass, audit truncation, monitoring evidence, harmful-treatment, and grounding adversarial tests run in CI.
- [ ] `--check` and artifact verification are read-only and compare against published evidence.
- [ ] Each qualification gate states precisely what it proves; in-process timing is not described as network or sustained-load evidence.
- [ ] The README badge reflects the actual workflow rather than a static passing image.
- [ ] Verification checks working-tree cleanliness, runs in a clean environment, and uses a documented headless plotting backend.

#### RH-12 - Regenerate evidence and reconcile scientific and product claims

**Issue template:** Implementation task
**Classification:** Documentation and evidence correction
**Priority:** Release blocking

**Outcome:** Recompute affected economic and qualification evidence after fixes and reconcile all public claims and status documents without rewriting historical results. The evaluation must answer a predeclared estimand and use comparable operational baselines.

**Acceptance checks:**

- [ ] Corrected OPE reports the predeclared primary estimand. Fixed-assignment resampling is labeled conditional on the frozen allocation; portfolio resampling reruns the policy and states cluster, duplication, and capacity treatment. If both are reported, they remain separate.
- [ ] Non-intervention, rules-only, risk-ranked, and engine strategies use identical cohort, cutoff, eligibility, catalog, budget, and personnel assumptions.
- [ ] Lead time, recall at capacity, unnecessary contacts, expected harm, premium-value, and policy-count objectives are reported where supported.
- [ ] Predictive discrimination, calibration, treatment effect, modeled business value, and external validity are presented as separate claims.
- [ ] Queue precision/recall, value-versus-count tradeoff, fairness/access implications, and combined lapse/surrender target mapping are explicit.
- [ ] The v5 infeasibility statement is bounded to the examined design/search space.
- [ ] The Protocol 3.1.0 post-result amendment and acceptance-seed reuse remain visible; any fresh-seed confirmation is predeclared in a separate experiment issue before execution.
- [ ] README, model card, backlog, roadmap, limitations, release notes, ADR count, phase totals, and P4 scaffold status agree.
- [ ] Scope is reconciled with open documentation and simulator issues #128 and #130.

#### RH-13 - Qualify and release the hardening initiative

**Issue template:** Implementation task
**Classification:** Release evidence / decision
**Priority:** Release blocking

**Outcome:** Publish `v0.3.1-decision-engine-hardening` evidence and make a formal `PROCEED`, `REMEDIATE`, or `STOP` decision for P4-02/P4-03.

**Acceptance checks:**

- [ ] All predecessor RH issues are merged and closed.
- [ ] A clean, read-only full qualification run passes and its environment and commit are recorded.
- [ ] The recorded qualification starts from a clean working tree and uses the documented headless plotting configuration.
- [ ] Release notes distinguish repaired behavior, superseded evidence, preserved historical artifacts, and remaining limitations.
- [ ] Annotated tag and GitHub release are prepared only after the decision is `PROCEED`.
- [ ] Phase 4 dependencies and amended P4-01 contracts are updated from the final merged state.

### Finding coverage matrix

| Review finding | Primary RH work | Supporting work |
| --- | --- | --- |
| 1. Dashboard loses point-in-time truth | RH-01 | RH-02, RH-08, RH-11 |
| 2. Human-review transition bypass | RH-03 | RH-09, RH-11 |
| 3. Missing safety facts mean permission | RH-02 | RH-01, RH-03 |
| 4. Dashboard capacity is not enforced | RH-05 | RH-04, RH-11 |
| 5. Harm is discarded; costs conflict | RH-04 | RH-05, RH-12 |
| 6. Monitoring appears healthy without evidence | RH-07 | RH-11 |
| 7. Serving is not independently packaged | RH-06 | RH-11 |
| 8. P4-01 contracts disagree | RH-09 | RH-01, RH-03 |
| 9. Audit claims exceed verification | RH-10 | RH-03, RH-11 |
| 10. Solver and resource units are inconsistent | RH-05 | RH-04 |
| 11. Qualification and CI are too narrow | RH-11 | RH-13 |
| 12. Grounding is lexical and incomplete | RH-08 | RH-01, RH-11 |
| Scientific/business interpretation | RH-12 | RH-04, RH-05, RH-13 |
| Maintainability and presentation | RH-01, RH-06, RH-12 | RH-00, RH-09 |

### GitHub execution conventions

#### Issue creation

- Use `.github/ISSUE_TEMPLATE/decision.yml` for RH-00 and any separately required durable decision attached to RH-09D.
- Use `.github/ISSUE_TEMPLATE/design.yml` for every `D` child where the work breakdown calls for a design specification.
- Use `.github/ISSUE_TEMPLATE/implementation.yml` for code, tests, evidence, and documentation changes.
- Put the stable RH ID, classification, priority, and `v0.3.1-decision-engine-hardening` milestone in Work metadata.
- Copy the issue-specific outcome, scope, claim/contract/artifact impact, acceptance checks, evidence, dependencies, and boundaries from this plan, refining them before marking the issue ready.

#### Branches and pull requests

Use the existing branch grammar with the GitHub issue number and stable work ID:

```text
docs/<issue>-rh-<id>-<slug>
fix/<issue>-rh-<id>-<slug>
feat/<issue>-rh-<id>-<slug>
test/<issue>-rh-<id>-<slug>
```

Examples:

```text
docs/134-rh-00-hardening-charter
fix/136-rh-02-fail-closed-safety
test/145-rh-11-qualification-ci
```

PR titles begin with the stable ID, such as `RH-02: Fail closed on missing safety evidence`. PR bodies use the repository template, `Closes #<issue>`, and the hardening milestone. Use merge commits, delete merged branches, and start dependent branches from updated `origin/main`.

#### Required evidence for every implementation PR

- Focused regression output demonstrating the protected invariant.
- Relevant component-suite output.
- `make check`, `git diff --check`, `git status --short`, and reviewed diff evidence.
- Contract/artifact compatibility or intentional version/migration evidence.
- Updated limitation and claim status when the merge changes what may be stated.
- Confirmation that no final holdout, real customer data, credentials, or proprietary material entered scope.

### Phase 4 operating rule while RH is open

- P4-01 stays completed as architecture-inception history; RH-09 amends rather than rewrites it.
- Do not start P4-02 or P4-03 implementation until RH-13 records `PROCEED`.
- P4-04 may refine its future design against RH-10, but must not implement against unsettled audit semantics.
- P4-05 through P4-07 remain planned and inherit the amended contracts and qualification language after RH-13.
- If schedule pressure requires independent Phase 4 preparation, limit it to reversible research or spike work with no frozen contracts and no release claim.
- PostgreSQL/KMS deployment, production identity federation, CRM/telephony connectors, Kafka, Kubernetes, multi-region scaling, a new deep-learning or causal/uplift model, and a live LLM are explicitly outside RH.
- Fresh acceptance seeds are optional: they strengthen confirmation but do not block RH-13 when the post-result protocol change remains disclosed and no fresh-confirmation claim is made.

### Recommended first GitHub actions

1. [Completed] RH-00 was created as issue #133 with the decision template, links the 2026-09-07 reviewer approval, and records `ADOPT`.
2. [Completed] GitHub Milestone #6, `v0.3.1-decision-engine-hardening`, was created after adoption and assigned to RH-00.
3. [Completed] The RH initiative is represented in the interactive roadmap as a separate lane between Phase 3 and resumed Phase 4; this backlog remains canonical.
4. [Completed] Open issues #128-#130 were triaged; #128 maps to future RH-12, #129 maps to future RH-07, and #130 remains independent pending RH-12 reconciliation.
5. Initially create RH-01D and the independent implementation issues whose scopes are already ready after RH-00; create `I` children and downstream issues only when their predecessor designs and contracts are stable.
6. Keep P4-02/P4-03 unassigned or explicitly blocked until RH-13.

---

## Phase 4 - Enterprise Integration & Scale

Phase 4 transitions Inforsight from a verified local mathematical decision engine into an enterprise-ready distributed platform. Operating under [**ADR 0003**](adr/0003-start-local-and-defer-distributed-infrastructure.md), all enterprise distributed infrastructure, multi-language microservices, and cloud deployments were deferred until the mathematical formulation and local decision-intelligence layers passed full system qualification.

With the Capstone Milestone `v0.3.0-decision-engine` certified with 100% passing gates (S1–S6), Phase 4 executes the productionization roadmap across 7 governed increments. Assign every P4-01 through P4-07 issue to GitHub Milestone #5 (**`v0.4.0-enterprise-scale`**).

P4-01 remains completed architecture-inception history. Its affected contracts are provisional under RH-09. P4-02 and P4-03 implementation are paused until the separate review-hardening initiative closes and RH-13 records `PROCEED`.

### Dependency and execution flow

```text
P4-01 (Architecture Inception & ADR 0014)
  ├──> P4-02 (Apache Kafka Streaming Ingress & Contracts)
  │      └──> P4-03 (Java 21 / Spring Boot Control Plane)
  │             ├──> P4-04 (Persistence Layer & Cryptographic Audit Store)
  │             └──> P4-05 (Enterprise Connectors: CRM & Telephony)
  │                    └──> P4-06 (Cloud Infrastructure & Container Orchestration)
  │                           └──> P4-07 (End-to-End Enterprise Scale Qualification & Release v0.4.0)
```

---

### P4-01 - Enterprise distributed architecture inception and ADR 0014

**Milestone:** `v0.4.0-enterprise-scale` (Milestone #5)

**Status:** Completed (Issue [#131](https://github.com/anilreddy89/Inforsight/issues/131), [PR #132](https://github.com/anilreddy89/Inforsight/pull/132), commit `a897300`).

**Outcome:** Reviewed Architecture Decision Record (ADR 0014) and interface contracts define microservice decomposition, inter-service protocols, and runtime isolation before distributed code is written.

**Scope:**
- Author [ADR 0014: Enterprise Distributed Architecture & Microservice Decomposition](adr/0014-enterprise-distributed-architecture.md).
- Define service boundaries:
  - **Inference Runtime:** Python/FastAPI `BundledInferenceEngine` container providing low-latency, zero-dependency scoring via gRPC/REST.
  - **Control Plane:** Java 21 / Spring Boot 3 enterprise service orchestrating queues, deterministic eligibility rules, and knapsack optimization.
  - **Streaming Gateway:** Apache Kafka cluster managing bitemporal event topics.
- Formalize gRPC and OpenAPI contracts between control plane and inference engine.
- Define developer environment specification (Docker Compose baseline).

**Acceptance checks:**
- [x] ADR 0014 documents context, alternatives (monolith vs. microservices, REST vs. gRPC), tradeoffs, and security boundaries.
- [x] Sub-millisecond scoring SLA ($\le 5\text{ms}$ RPC roundtrip) contractually established.
- [x] ADR 0002 authority isolation invariants (`authorized_to_act: false`) explicitly codified in inter-service schemas.
- [x] Docker Compose topology scaffold passes local validation.

**Blocks:** P4-02, P4-03.

---

### P4-02 - Apache Kafka streaming ingress and event contracts

**Milestone:** `v0.4.0-enterprise-scale` (Milestone #5)

**Status:** Paused — blocked by RH-13 `PROCEED`.

**Outcome:** High-throughput streaming event ingress replaces static JSONL batch playback, supporting real-time bitemporal policy event streams with schema validation and dead-letter queues.

**Scope:**
- Create versioned streaming contracts in `data-contracts/streaming/` (JSON Schema / Avro):
  - `policy-lifecycle-events`: Issuance, status transitions, endorsements.
  - `billing-payment-events`: Invoices, debit attempts, NSF returns, retries.
  - `customer-service-events`: Inquiries, notices, disputes, preference updates.
- Implement Kafka producers and consumers in streaming ingress module.
- Enforce strict point-in-time ordering, event deduplication by `(event_id, idempotency_key)`, and poison-pill Dead Letter Queue (DLQ).
- Implement local Kafka test harness using Testcontainers.

**Acceptance checks:**
- [ ] Streaming consumer handles out-of-order ingestion while preserving point-in-time state invariants.
- [ ] Malformed or unversioned event payloads route to DLQ without crashing the consumer.
- [ ] End-to-end integration tests process 10,000 streaming events with zero data loss or state corruption.
- [ ] Unit and container integration tests pass.

**Depends on:** P4-01. **Blocks:** P4-03.

---

### P4-03 - Java 21 / Spring Boot control plane microservice

**Milestone:** `v0.4.0-enterprise-scale` (Milestone #5)

**Status:** Paused — blocked by RH-13 `PROCEED`.

**Outcome:** Production-grade Java 21 / Spring Boot microservice hosts the deterministic eligibility rules engine, knapsack uplift optimizer, and case triage queues with high concurrency.

**Scope:**
- Scaffold `services/control-plane/` using Spring Boot 3, Java 21, and Virtual Threads (Project Loom).
- Port deterministic action eligibility rules engine (ADR 0002) and knapsack uplift optimizer to Java:
  - Strict parity validation with Python `simulator/rules/` and `simulator/optimization/`.
- Implement gRPC/REST client invoking Python `BundledInferenceEngine` for risk scoring and attribution.
- Expose enterprise control-plane endpoints:
  - `POST /api/v1/cases/triage`: Executes batch intake, scoring, filtering, and knapsack allocation.
  - `GET /api/v1/cases/{id}`: Returns structured Case Brief with grounding verification.
  - `POST /api/v1/cases/{id}/decision`: Records licensed caseworker authorization sign-off.
- Implement resilience patterns: circuit breaker, rate limiting, and retry policies.

**Acceptance checks:**
- [ ] Java rules engine produces 100% identical eligibility decisions to Python implementation on canonical fixture.
- [ ] Java knapsack solver matches Python net-utility optimization allocation bit-for-bit.
- [ ] Project Loom virtual threads demonstrate handling 1,000 concurrent case triage requests without thread pool exhaustion.
- [ ] Service integration tests pass using Testcontainers.

**Depends on:** P4-01, P4-02. **Blocks:** P4-04, P4-05.

---

### P4-04 - Enterprise persistence layer and cryptographic audit store

**Milestone:** `v0.4.0-enterprise-scale` (Milestone #5)

**Outcome:** Robust relational persistence and immutable cryptographic audit ledger storage supporting high-concurrency caseworker operations and compliance verification.

**Scope:**
- Implement PostgreSQL persistence layer with Flyway schema migrations:
  - Relational tables for policy snapshots, active triage queues, and case states.
- Implement immutable append-only audit store with SHA-256 cryptographic hash chaining (`parent_hash` $\to$ `current_hash`).
- Add hardware/cloud KMS key signing interface for tamper-proof compliance certification.
- Implement automated verification query detecting ledger tampering, deletions, or reordering.

**Acceptance checks:**
- [ ] Flyway migrations execute cleanly and rollback idempotently.
- [ ] Audit ledger cryptographic integrity verification detects 100% of injected mutations or row deletions.
- [ ] ACID transaction boundaries guarantee no case decision is recorded without corresponding audit ledger commit.
- [ ] Database integration tests pass.

**Depends on:** P4-03. **Blocks:** P4-06.

---

### P4-05 - Enterprise CRM and contact center connectors

**Milestone:** `v0.4.0-enterprise-scale` (Milestone #5)

**Outcome:** Bi-directional integration adapters connect Inforsight to enterprise customer relationship management (CRM) and contact center telephony platforms.

**Scope:**
- Implement CRM connector framework in `services/control-plane/connectors/`:
  - **Salesforce Financial Services Cloud (FSC) Adapter:** Syncs prioritized cases to caseworker task queues and captures customer interaction outcomes.
  - **Genesys Cloud / Twilio Dialer Adapter:** Formats specialist outreach batches for agent dialers with contact cooling-off guardrails.
- Enforce strict ADR 0002 boundary: connector payloads explicitly mandate `authorized_to_act: false` until human caseworker clicks approve.
- Provide webhook ingress for asynchronous outreach disposition callbacks (e.g. `PROMISE_TO_PAY`, `PAYMENT_RESOLVED`, `UNREACHABLE`).

**Acceptance checks:**
- [ ] Connector mocks verify bi-directional payload mapping and retry on upstream 5xx errors.
- [ ] Cooldown compliance invariants reject outreach to policyholders contacted within the prior 30 days.
- [ ] Unauthorized automated dispatch attempts fail at the connector boundary.
- [ ] Unit and mock server integration tests pass.

**Depends on:** P4-03. **Blocks:** P4-06.

---

### P4-06 - Cloud infrastructure, Helm charts, and container orchestration

**Milestone:** `v0.4.0-enterprise-scale` (Milestone #5)

**Outcome:** Production containerization, Kubernetes deployment manifests, and Helm charts enable reliable, scalable cloud deployment (AWS/GCP/local).

**Scope:**
- Multi-stage minimal Dockerfiles for:
  - Python inference gateway (`infra/docker/Dockerfile.inference`).
  - Java control plane microservice (`infra/docker/Dockerfile.control-plane`).
- Build comprehensive Helm chart `infra/helm/inforsight`:
  - Deployments, Services, ConfigMaps, Secrets, and Ingress routing.
  - Horizontal Pod Autoscaler (HPA) based on CPU/memory and queue depth.
  - Readiness, liveness, and startup health probes.
- Provide unified local development stack via Docker Compose (`infra/docker-compose.yml`) spinning up Kafka, PostgreSQL, Python Inference, and Java Control Plane.

**Acceptance checks:**
- [ ] Container images build cleanly with zero high/critical CVE vulnerabilities.
- [ ] Helm lint and dry-run validation pass cleanly.
- [ ] Local Docker Compose stack launches with a single command and passes end-to-end health checks.
- [ ] HPA configuration scales pods under synthetic load.

**Depends on:** P4-04, P4-05. **Blocks:** P4-07.

---

### P4-07 - Enterprise scale qualification and release (v0.4.0-enterprise-scale)

**Milestone:** `v0.4.0-enterprise-scale` (Milestone #5)

**Outcome:** Formal distributed system qualification under high-volume synthetic load, verification of Enterprise Performance Gates (E1–E6), and milestone release closeout.

**Scope:**
- Execute distributed stress qualification runner on 100,000 synthetic policies across Kafka streaming cluster.
- Pre-register and verify Enterprise Performance Gates:
  - **Gate E1 (Streaming Ingestion Throughput):** $\ge 5,000\text{ events/sec}$ with zero drop rate.
  - **Gate E2 (End-to-End Latency SLA):** Event ingress to scored case brief $P_{99} \le 50.0\text{ms}$.
  - **Gate E3 (Authority Isolation):** 100% rejection of unapproved outreach in enterprise connectors.
  - **Gate E4 (Audit Ledger Immutability):** 100% tamper detection across distributed database nodes.
  - **Gate E5 (Fault Tolerance & Recovery):** Zero data loss during simulated worker pod kill / restart.
  - **Gate E6 (Reproducibility & Parity):** Bit-for-bit decision and allocation parity between Java and Python runtimes.
- Author milestone release documentation: `docs/release-notes/v0.4.0-enterprise-scale.md`.
- Prepare annotated Git release tag `v0.4.0-enterprise-scale` and close GitHub Milestone #5.

**Acceptance checks:**
- [ ] All 6 Enterprise Performance Gates (E1–E6) pass 100%.
- [ ] Enterprise Qualification Report and cryptographic manifest published.
- [ ] Release notes document deployment topologies, scaling benchmarks, and operator guides.
- [ ] Milestone #5 reaches 100% completion on GitHub.

**Depends on:** P4-06. **Blocks:** Future Phase 5 initiatives.

---

## Deferred intentionally

- **Direct Causal Uplift ML Models (Phase 5):** Direct causal estimators (Causal Forests, X-Learners, or Double Machine Learning) predicting treatment effects $\tau_i = \mathbb{E}[Y(1) - Y(0) \mid X_i]$ directly from experimental intervention histories remain deferred until real-world intervention outcome datasets are connected.
- **Richer Lifecycle Contracts:** Issue age, face amount, acquisition channel, recurring multi-year exposure, reinstatement, policy loans, and cash surrender values will be incorporated as enterprise Policy Administration System (PAS) connectors require them.
- **Fairness and Demographic Bias Assessment:** A separately governed fairness assessment requires real-world demographic and regulatory compliance benchmarks. We strictly avoid inventing synthetic proxy variables or claiming demographic parity without representative data.
