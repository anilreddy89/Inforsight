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

- **P2-08 probability calibration and threshold evaluation is paused.** Calibration plumbing may be unit-tested only inside a separately approved remediation issue; no Phase 2.08 experiment artifact or performance conclusion may be published before R2-11 records `proceed`.
- **P2-09 SHAP or equivalent attribution is paused.** Explanation plumbing may be unit-tested only with clearly marked fixtures; no v1 feature importance may be interpreted as a substantive risk mechanism.
- P2-10 through P2-12 remain pending. Model-specific artifact freezing, a final evaluation, a model decision, and a release marker cannot proceed before R2-11 records `proceed`.
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

**Status:** Ready; R2-09 merged as `89c2291`. Create a focused implementation issue and branch from updated `main`.

Build governed v3 folds, feature/preprocessing state, diagnostics, authorization, both frozen candidates, deterministic selection evidence, and readiness inputs. Produce no acceptance metric or final holdout.

**Depends on:** R2-09. **Blocks:** R2-11.

### R2-11 - Run replacement statistical acceptance protocol 2.0.0

**Status:** Pending R2-10 merge.

Run readiness first, then all predeclared controls and statistical rules only if readiness passes. Publish exactly one `proceed`, `redesign`, or `stop` decision. The final holdout remains `not_materialized`.

**Depends on:** R2-10. **Blocks:** P2-08 and P2-09 unless the merged decision is `proceed`.

### Phase 2R completion gate

Phase 2R completes only when R2-00 through R2-11 are merged in order and the R2-11 decision is `proceed`. A favorable single seed, a passing unit-test suite, or a manually accepted limitation is not sufficient. If R2-11 decides `redesign` or `stop`, P2-08 and P2-09 remain paused and a new focused backlog item must own the next action.

## Phase 2 - Baseline ML resumed after Phase 2R

- [ ] **P2-08 - Probability calibration and operational thresholds (PAUSED):** After R2-11 records a merged `proceed`, fit calibration using the separately designated non-test calibration data and report discrimination, calibration, precision at operational review capacity, recall in high-risk bands, threshold tradeoffs, uncertainty, and explicit false-positive cost assumptions. Do not access the final release holdout for model or threshold selection.
- [ ] **P2-09 - Model-behavior explanations (PAUSED):** After the calibrated candidate and feature contract are frozen, publish SHAP or equivalent attribution examples with feature sanity checks and clear boundaries that explanations describe model behavior rather than authorize conservation actions. Use only approved non-final data for explanation development.
- [ ] **P2-10 - Artifact and environment reproducibility:** Version the training configuration, dependencies, feature contract, split manifest, fitted preprocessing and calibration pipelines, metrics, and model artifacts; bundle compatible objects or bind them through verified metadata, and prove that reloading the frozen release candidate reproduces authorized predictions from documented commands.
- [ ] **P2-11 - Final evaluation, model card, and decision note:** Freeze the release candidate and evaluation protocol before one access-controlled final test; then publish `MODEL_CARD.md`, the final experiment report, and a Phase 2 decision note that disclose limitations, uncertainty, synthetic-data boundaries, the absence of a meaningful subgroup-fairness assessment, and the release decision.
- [ ] **P2-12 - Release marker and notes:** After the Phase 2 decision gate passes, publish the `v0.2.0-risk-model` tag and GitHub release from the completed [**v0.2.0-risk-model**](https://github.com/anilreddy89/Inforsight/milestone/3) milestone. The tag, release title, and milestone capability name must remain aligned.

## Deferred intentionally

- Evaluate richer lifecycle contracts only when the Phase 2 data-sufficiency gate demonstrates that the MVP requires them: issue age, face amount, acquisition channel, recurring exposure, payment retries, reinstatement, maturity, loans, cash value, address and payment-method changes, and prior conservation attempts.
- Open a separately governed fairness and bias assessment only when a defined jurisdiction and use case, legitimate and privacy-reviewed subgroup data, governance approval, adequate subgroup sample sizes, uncertainty reporting, and impact-aware metrics make the assessment meaningful; do not invent demographic attributes or claim fairness from the current fictional corpus.
- Add SQL persistence schemas only when a storage consumer requires them.
- Java services, Kafka, cloud deployment, bounded agents, and RAG remain deferred until the data and baseline-model gates pass.
