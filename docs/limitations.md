# Limitation Register

## Purpose

This register tracks implementation findings that constrain what Inforsight can claim or safely do. It complements phase contracts, experiment artifacts, assumptions, and the backlog:

- Phase contracts and experiment artifacts contain the detailed evidence.
- `docs/assumptions.md` records stable project-wide constraints.
- This register records ownership, impact, resolution triggers, and closure evidence.
- `docs/backlog.md` schedules work when a limitation reaches its resolution trigger.

A limitation does not automatically block all subsequent work. Each entry must state what may continue, what is blocked, and the latest point at which resolution or an explicit stop decision is required.

## Status lifecycle

```text
Open -> Accepted temporarily -> Scheduled -> Resolved
                                   |
                                   +-> Superseded
```

| Status | Meaning |
| --- | --- |
| Open | Verified limitation without an approved temporary disposition or scheduled resolution. |
| Accepted temporarily | Work may continue within explicit boundaries until the recorded trigger. |
| Scheduled | A backlog item or issue owns the resolution work. |
| Resolved | Objective closure evidence satisfies the acceptance criteria. |
| Superseded | A later contract or decision replaces the limitation; the replacement is linked. |

## Severity

| Severity | Meaning |
| --- | --- |
| Blocking | Current work cannot continue safely or validly. |
| Claim-blocking | Engineering may continue, but specified evaluation, readiness, or performance claims are prohibited. |
| Material | The limitation affects design or interpretation and must remain visible. |
| Informational | Useful context without a current acceptance-gate impact. |

## Active limitations

### LIM-002-001 — Billing frequency is confounded with observation time

| Field | Value |
| --- | --- |
| Status | Scheduled |
| Severity | Claim-blocking |
| Discovered in | Phase 2.03 policy-aware temporal splits |
| Owner | Historical v2 corpus issue [#56](https://github.com/anilreddy89/Inforsight/issues/56) and later v3/v4 work are complete; R2-14A [issue #76](https://github.com/anilreddy89/Inforsight/issues/76) merged as `52c03c8`; R2-14B [issue #78](https://github.com/anilreddy89/Inforsight/issues/78) stopped at readiness because contract `1.0.0` lacks frozen H1-H5 disposition thresholds |
| Evidence | `docs/experiments/phase-02-03-temporal-split-manifest.json`; v2 corpus evidence in `docs/experiments/phase-02r-05-v2-corpus-manifest.json`; R2-07 readiness and `stop` evidence in `docs/experiments/phase-02r-07-v2-statistical-acceptance-manifest.json`; pipeline-only v1 baseline and feature-sanity evidence |
| Detailed contract | `docs/modeling/phase-02-03-temporal-split-contract.md` |
| Resolution trigger | Before interpreting held-out metrics as temporal generalization or approving a risk-model release |

#### Finding

Observation contract `1.0.0` creates one observation at first-billing ingestion. The canonical policies are issued during one short initial period, so billing frequency largely determines observation date. The strict chronological split consequently contains monthly policies in train, quarterly policies in the embargo, semiannual policies in validation, and annual policies in test.

Billing frequency is also entangled with policy age at the observation cutoff. A validation or test result therefore cannot distinguish temporal generalization from behavior on feature categories absent from training.

Phase 2.07 confirms that billing frequency and several first-billing event-count or age fields are constant in the training partition. Billing frequency therefore retains an `investigate` disposition; the other constant fields are temporally valid and retained as non-leakage screens, but they contribute no training variation in the current corpus.

#### Work that may continue

- Versioned feature construction and deterministic regeneration.
- Training-only preprocessing with explicit handling for unknown held-out categories.
- Seeded model training, artifact loading, and scoring-path reproducibility.
- Leakage, isolation, and separately scoped scoring-path or reporting-mechanics tests that do not publish Phase 2.08 or Phase 2.09 evidence.
- Synthetic metrics labeled strictly as pipeline demonstrations.
- Phase 2R correctness, contract, corpus, split, and statistical-gate work.

#### Work or claims blocked

- Claims that held-out results demonstrate temporal generalization.
- Claims of real-world predictive, actuarial, fairness, operational, or business performance.
- Model-release approval based on the current temporal split.
- Phase 2.08 calibration or threshold artifacts and Phase 2.09 model-behavior explanations until a replacement acceptance gate records a merged `proceed` decision.
- Changing to a random or stratified split to conceal the temporal confounding.
- Using validation or test results to redesign the existing split after results are observed.

#### Proposed resolution

Introduce a separately versioned generator and observation design with:

- multiple policy-issuance cohorts spread across sufficient calendar duration;
- every supported billing-frequency category represented in train, validation, and test;
- enough observations and outcomes in each chronological partition;
- unchanged dual-time feature visibility and policy/outcome-episode isolation; and
- a preserved 90-day label-horizon embargo.

#### Closure evidence

- [x] A separately reviewed issue and versioned generator or observation-contract change are merged through issue #45 and PR #46.
- [ ] Every supported billing frequency appears in train, validation, and test.
- [ ] Train, validation, and test remain strictly chronological.
- [ ] Both 90-day horizon embargo assertions pass.
- [ ] Policy and outcome-episode overlap remain zero.
- [ ] The regenerated versioned split manifest passes deterministic verification.
- [ ] Each modeling partition has an adequate, documented sample and outcome count for the intended claim.
- [x] The R2-07 decision note records `stop`; no narrower temporal-generalization claim is authorized.
- [x] R2-08 contract `3.0.0` and protocol `2.0.0` predeclare replacement cohorts, folds, support rules, and temporal-stability evidence before v3 output exists.

### LIM-002-002 — The v1 corpus has no designed pre-cutoff feature-to-outcome risk mechanism

| Field | Value |
| --- | --- |
| Status | Scheduled |
| Severity | Claim-blocking |
| Discovered in | Independent ML engineering review after Phase 2.07 |
| Owner | Historical work complete through R2-14 (`redesign`); R2-14A [issue #76](https://github.com/anilreddy89/Inforsight/issues/76) merged as `52c03c8`; R2-14B [issue #78](https://github.com/anilreddy89/Inforsight/issues/78) merged as `3088c4c` with readiness stop under accepted ADR 0009; R2-14BA [issue #80](https://github.com/anilreddy89/Inforsight/issues/80) merged as `627e698` approving amended contract `1.1.0` under ADR 0010 before R2-14BB execution |
| Evidence | Historical v1 generator and experiment reports; v2 implementation contract and `docs/experiments/phase-02r-05-v2-corpus-manifest.json`; R2-07 readiness and `stop` evidence in `docs/experiments/phase-02r-07-v2-statistical-acceptance-manifest.json` |
| Detailed plan | Historical v2 design remains in ADR 0004 and protocol `1.0.0`; v3 design and failed acceptance remain in ADR 0005 and R2-08 through R2-11; ADR 0006, issue #66, and backlog R2-12 through R2-16 own the replacement diagnostic and redesign sequence |
| Resolution trigger | Before probability calibration, substantive model explanations, final-test evaluation, or a risk-model release decision |

#### Finding

The v1 generator assigns coverage scenarios independently of the policy attributes and pre-cutoff observations available to the model. Outcome branches are driven by the assigned scenario after the observation cutoff, while the first-billing observation occurs before the behavioral events that would otherwise differentiate policy histories. Several behavioral feature groups are consequently constant in training.

The corpus is useful for exercising deterministic branches, contracts, point-in-time reconstruction, leakage controls, preprocessing, model serialization, and report generation. It does not provide a known feature-conditioned statistical relationship that a risk model can be expected to recover. Validation discrimination can therefore reflect finite-sample seed variation, temporal category composition, or other artifacts rather than learned risk.

#### Work that may continue

- R2-00 through R2-11 historical remediation and the R2-12 through R2-16 replacement sequence within each dependency boundary.
- Correctness, determinism, leakage, isolation, serialization, and scoring-interface tests.
- Historical v1 reproduction when labeled `pipeline_engineering_only`.
- Design-only model-card, calibration-interface, or explanation-interface work that publishes no performance or substantive interpretation.

#### Work or claims blocked

- Phase 2.08 probability-calibration and operational-threshold evidence.
- Phase 2.09 substantive SHAP or equivalent model-behavior interpretation.
- Claims that v1 model discrimination represents recoverable policy risk.
- Final-test performance reporting or risk-model release approval.
- Redesigning the generator to target a desired AUC after observing results without a predeclared acceptance protocol.

#### Approved replacement design

Preserve v1 and current v2 as immutable evidence and introduce a separately versioned v3 event-first statistical corpus with multiple cohorts, recurring exposure, varied dual-time-visible behavior, a stochastic feature-conditioned outcome mechanism, latent noise, oracle probabilities, matched controls, and predeclared multi-seed acceptance protocol `2.0.0`.

#### Closure evidence

- [x] The R2-04 ADR and versioned statistical contract were approved through issue #42 and PR #43 before v2 results were created or inspected.
- [ ] The v2 generator exposes a documented stochastic risk mechanism and oracle probabilities without leaking them into model features.
- [ ] Recurring pre-cutoff observations contain adequate behavioral and feature variation.
- [ ] Null-signal and label-shuffle controls behave according to predeclared chance rules.
- [ ] Known simulated signal is recovered consistently across seeds and temporal folds with uncertainty.
- [ ] Learning, ablation, missingness, category, and temporal-stability evidence satisfies the predeclared R2-07 decision rules.
- [x] The R2-07 decision note records `stop`; P2-08 and P2-09 remain paused.
- [x] R2-08 freezes the v3 mechanism, coefficient/group registries, matched streams, candidate selection, and executable protocol `2.0.0` before v3 output exists.

### LIM-002-003 — The v1 test fixture is API-guarded and was prediction-accessed during review

| Field | Value |
| --- | --- |
| Status | Scheduled |
| Severity | Claim-blocking |
| Discovered in | Independent engineering review after Phase 2.07 |
| Owner | Local scoring repair completed by R2-03 issue #39 and PR #40; future final-holdout design was approved by R2-04 issue #42 and PR #43, while proof remains owned by the later authorized release workflow |
| Evidence | `simulator/src/inforsight_simulator/modeling.py`; `simulator/src/inforsight_simulator/boosted_modeling.py`; `simulator/src/inforsight_simulator/diagnostics.py`; historical `sealed_not_scored` language in Phase 2.05-2.07 artifacts and tracker |
| Detailed plan | `docs/backlog.md`, Phase 2R items R2-00 and R2-03 |
| Resolution trigger | Before creating or accessing a new final release holdout or making a held-out performance claim |

#### Finding

Before R2-03, the scoring APIs authorized validation predictions primarily from a caller-controlled partition string and feature-name checks. Relabeling the immutable v1 test `ModelMatrix` as `validation` produced logistic and boosted predictions during adversarial review. No test metric was computed and no repository artifact was changed, but prediction access occurred. The v1 fixture must therefore be described as review-exposed prediction-only historical evidence, not untouched or `sealed_not_scored`.

R2-03 replaced that convention with a digest-bound local integrity and misuse guard. The deterministic corpus, split membership, and transformed matrices remain locally inspectable, so the repaired control is not a hard security or access-control boundary against a party who can modify repository code or files.

#### Work that may continue

- R2 statistical-design, corpus, evaluation-data, and acceptance-gate work.
- Reproduction of train and validation pipeline artifacts under their historical engineering-only claim.
- Design of a future access-controlled one-shot evaluation protocol.

#### Work or claims blocked

- Any claim that the v1 test fixture remained untouched after Phase 2.07 review.
- Computing or publishing v1 test metrics as final performance evidence.
- Treating a renamed partition or public deterministic fixture as an access-controlled release holdout.
- Creating a new final release holdout before the v2 evaluation protocol and release candidate are frozen.

#### Proposed resolution

Bind authorized scoring membership, row identity, feature contract, preprocessing identity, and matrix digests to verified fitted state or an evaluation manifest. Separate ordinary unlabeled inference from experiment evaluation. Preserve the v1 test fixture only as historical pipeline evidence, and create the future v2 release holdout under a predeclared access-controlled one-shot protocol.

R2-03 completed through issue #39 and PR #40, merge commit `5eb67c1`. Scoring authorization contract `1.0.0` now binds exact membership, row order, feature contract, labeled-matrix contents, training-matrix identity, fitted-preprocessor identity, and approved purpose across logistic, boosted, diagnostic, comparison, and reload paths. Ordinary inference uses a separate target-free matrix. The v1 fixture remains review-exposed historical evidence and is not re-sealed. R2-04 issue #42 and PR #43 subsequently approved the future one-shot holdout design while keeping its status `not_materialized` through R2-07.

The limitation remains `Scheduled` because the future v2 final-holdout protocol and one-shot release workflow are not yet approved or proven.

#### Closure evidence

- [x] Current repository status and affected reports describe the v1 fixture truthfully without rewriting historical artifacts.
- [x] Relabeling, row substitution, reordering, feature substitution, target substitution, authorization tampering, and digest mismatch fail across logistic, boosted, diagnostic, and reload paths.
- [x] Authorized non-final scoring succeeds only for verified membership, purpose, preprocessing identity, and fitted-state compatibility.
- [x] Unlabeled inference does not depend on experiment partition names or targets.
- [ ] The v2 final-holdout protocol is approved before holdout materialization or access.
- [ ] A later one-shot evaluation records the authorized accessor, frozen artifact digests, command, timestamp, and result without permitting iterative model changes.

### LIM-002-004 — The v2 acceptance substrate violates dual-time and matched-control requirements

| Field | Value |
| --- | --- |
| Status | Scheduled |
| Severity | Blocking |
| Discovered in | R2-07 readiness audit under issue [#51](https://github.com/anilreddy89/Inforsight/issues/51) |
| Owner | Historical work complete through R2-14 (`redesign`); R2-14A [issue #76](https://github.com/anilreddy89/Inforsight/issues/76) merged as `52c03c8`; R2-14B [issue #78](https://github.com/anilreddy89/Inforsight/issues/78) stopped at readiness because contract `1.0.0` lacks frozen H1-H5 disposition thresholds |
| Evidence | Historical R2-07 manifest/report/decision; R2-09/R2-10 v3 evidence; `docs/experiments/phase-02r-11-v3-statistical-acceptance-*`; `simulator/tests/test_v3_acceptance.py` |
| Detailed contract | Historical finding: `docs/modeling/phase-02r-07-v2-statistical-acceptance-execution-contract.md`; replacement: `docs/modeling/phase-02r-08-v3-statistical-substrate-contract.md` and protocol `2.0.0` |
| Resolution trigger | Before any replacement acceptance model fit, prediction, bootstrap, metric, limitation closure, or downstream performance-dependent work |

#### Finding

The v2 corpus builder constructs behavior features directly before applying ingestion-time visibility to the owning behavior event. The deterministic R2-07 structural fixture contains observations whose behavior event has `ingested_at > as_of` and is absent from `visible_event_ids`, while values from that event payload are present in the cutoff feature record. Protocol `1.0.0` classifies this post-cutoff ingestion leakage as `stop`.

Independent readiness checks also show that the current corpus API cannot produce the protocol's matched null or paired robustness scenarios. `signal_mode`, `drift_scenario`, and `mcar_missingness_rate` are part of run identity, and every random-domain seed derives from that identity, so changing any of them rerandomizes unaffected streams. R2-06 also did not freeze a selected candidate, the required five macro driver groups, strongest and zero-effect groups, or a canonical coefficient registry. The published seed's three acceptance folds have 23, 19, and 31 positives, below the protocol's minimum of 50 per evaluated membership.

#### Work that may continue

- R2-08 through R2-11 historical corrective work and the R2-12 through R2-16 replacement sequence within its governed boundaries.
- Structural, deterministic, dual-time, stream-pairing, authorization, and artifact tests that generate no acceptance metrics.
- Historical v1 and v2 reproduction when described according to their existing evidence and limitations.
- Documentation and audit-trail preservation.

#### Work or claims blocked

- R2-07 model fitting, prediction, bootstrap, negative controls, signal recovery, learning curves, ablations, robustness metrics, or temporal-stability metrics.
- Closure of `LIM-002-001` or `LIM-002-002` from current v2 evidence.
- P2-08 probability calibration and threshold evidence.
- P2-09 substantive model interpretation.
- Final-holdout materialization or any model-performance or release claim.
- Reclassifying `stop` as `redesign` or `proceed` by changing protocol rules after seeing v2 output.

#### Approved replacement design

Create the versioned v3 statistical substrate defined by ADR 0005 and contract `3.0.0`. It reconstructs every feature only from events satisfying both `effective_at <= as_of` and `ingested_at <= as_of`, separates stream-set, artifact, and execution identities, preserves matched primitive streams, freezes all selection and statistical procedures, and increases planned capacity without conditioning on realized outcomes.

#### Closure evidence

- [x] Focused issue #53 and stable work IDs R2-08 through R2-11 own the design, implementation, evaluation reconstruction, and replacement gate.
- [ ] Delayed-event mutation tests prove that an event with `ingested_at > as_of` cannot alter cutoff features or visible membership.
- [ ] Corrected observations and all downstream artifacts use new versions and preserve v1/current-v2 evidence unchanged.
- [ ] Matched null and robustness tests prove equality of every required unaffected random stream.
- [ ] Candidate, coefficient, driver-group, strongest-driver, zero-effect, shuffle, bootstrap, learning, and robustness specifications are frozen before replacement results.
- [x] R2-11 accounts for all 20 signal/null pairs, passes structural readiness, and records the failed primary recovery rules without accessing the final holdout.
- [ ] A reviewed redesign resolves the failed signal-recovery evidence before another acceptance run or downstream performance-dependent work.
- [ ] Every replacement acceptance membership meets the unchanged structural count rule or a new reviewed protocol records why the rule changed.
- [x] Replacement protocol `2.0.0` was approved through issue #53 and PR #54 without rewriting protocol `1.0.0` or the R2-07 `stop` decision.
- [ ] Full repository checks and hosted CI pass before statistical execution resumes.

## Register maintenance

When implementation reveals a new limitation:

1. Give it the next stable identifier in the form `LIM-<phase>-<sequence>`.
2. Record concrete evidence rather than a general concern.
3. State its severity, affected work, allowed work, and prohibited claims.
4. Define the resolution trigger and objective closure evidence.
5. Link the phase contract or experiment where it was discovered.
6. Add a backlog item when the trigger is approaching; create an issue when work is scheduled.
7. Never mark it resolved solely because later work completed or produced favorable metrics.

Resolved and superseded entries remain in this file as an audit trail.
