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
| Owner | R2-04 issue [#42](https://github.com/anilreddy89/Inforsight/issues/42), followed by R2-05, R2-06, and R2-07 |
| Evidence | `docs/experiments/phase-02-03-temporal-split-manifest.json`; pipeline-only baseline evidence in `docs/experiments/phase-02-05-logistic-baseline-manifest.json`; feature-sanity evidence in `docs/experiments/phase-02-07-feature-diagnostics-manifest.json` |
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
- Phase 2.08 calibration or threshold artifacts and Phase 2.09 model-behavior explanations until R2-07 passes.
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

- [ ] A separately reviewed issue and versioned generator or observation-contract change are merged.
- [ ] Every supported billing frequency appears in train, validation, and test.
- [ ] Train, validation, and test remain strictly chronological.
- [ ] Both 90-day horizon embargo assertions pass.
- [ ] Policy and outcome-episode overlap remain zero.
- [ ] The regenerated versioned split manifest passes deterministic verification.
- [ ] Each modeling partition has an adequate, documented sample and outcome count for the intended claim.
- [ ] The model decision note either authorizes the narrower claim with evidence or records a stop decision.

### LIM-002-002 — The v1 corpus has no designed pre-cutoff feature-to-outcome risk mechanism

| Field | Value |
| --- | --- |
| Status | Scheduled |
| Severity | Claim-blocking |
| Discovered in | Independent ML engineering review after Phase 2.07 |
| Owner | R2-04 issue [#42](https://github.com/anilreddy89/Inforsight/issues/42), followed by R2-05, R2-06, and R2-07 |
| Evidence | `simulator/src/inforsight_simulator/generator.py`; `simulator/src/inforsight_simulator/observations.py`; `docs/experiments/phase-02-05-logistic-baseline-report.md`; `docs/experiments/phase-02-06-boosted-comparison-report.md`; `docs/experiments/phase-02-07-feature-diagnostics-report.md` |
| Detailed plan | R2-04 issue [#42](https://github.com/anilreddy89/Inforsight/issues/42), `docs/adr/0004-versioned-v2-statistical-simulator-and-evaluation-design.md`, the Phase 2R.04 modeling contract and acceptance protocol, and `docs/backlog.md` items R2-04 through R2-07 |
| Resolution trigger | Before probability calibration, substantive model explanations, final-test evaluation, or a risk-model release decision |

#### Finding

The v1 generator assigns coverage scenarios independently of the policy attributes and pre-cutoff observations available to the model. Outcome branches are driven by the assigned scenario after the observation cutoff, while the first-billing observation occurs before the behavioral events that would otherwise differentiate policy histories. Several behavioral feature groups are consequently constant in training.

The corpus is useful for exercising deterministic branches, contracts, point-in-time reconstruction, leakage controls, preprocessing, model serialization, and report generation. It does not provide a known feature-conditioned statistical relationship that a risk model can be expected to recover. Validation discrimination can therefore reflect finite-sample seed variation, temporal category composition, or other artifacts rather than learned risk.

#### Work that may continue

- R2-00 through R2-07 remediation work.
- Correctness, determinism, leakage, isolation, serialization, and scoring-interface tests.
- Historical v1 reproduction when labeled `pipeline_engineering_only`.
- Design-only model-card, calibration-interface, or explanation-interface work that publishes no performance or substantive interpretation.

#### Work or claims blocked

- Phase 2.08 probability-calibration and operational-threshold evidence.
- Phase 2.09 substantive SHAP or equivalent model-behavior interpretation.
- Claims that v1 model discrimination represents recoverable policy risk.
- Final-test performance reporting or risk-model release approval.
- Redesigning the generator to target a desired AUC after observing results without a predeclared acceptance protocol.

#### Proposed resolution

Preserve v1 as an immutable coverage fixture and introduce a separately versioned v2 statistical corpus with multiple cohorts, recurring exposure, varied pre-cutoff behavior, a stochastic feature-conditioned outcome mechanism, latent noise, oracle probabilities, censoring and missingness mechanisms, and predeclared multi-seed acceptance tests.

#### Closure evidence

- [ ] The R2-04 ADR and versioned statistical contract are approved before v2 results are inspected.
- [ ] The v2 generator exposes a documented stochastic risk mechanism and oracle probabilities without leaking them into model features.
- [ ] Recurring pre-cutoff observations contain adequate behavioral and feature variation.
- [ ] Null-signal and label-shuffle controls behave according to predeclared chance rules.
- [ ] Known simulated signal is recovered consistently across seeds and temporal folds with uncertainty.
- [ ] Learning, ablation, missingness, category, and temporal-stability evidence satisfies the predeclared R2-07 decision rules.
- [ ] The R2-07 decision note records `proceed`, `redesign`, or `stop`; only `proceed` permits P2-08 and P2-09 to resume.

### LIM-002-003 — The v1 test fixture is API-guarded and was prediction-accessed during review

| Field | Value |
| --- | --- |
| Status | Scheduled |
| Severity | Claim-blocking |
| Discovered in | Independent engineering review after Phase 2.07 |
| Owner | Local scoring repair completed by R2-03 issue #39 and PR #40; future final-holdout design is owned by R2-04 issue [#42](https://github.com/anilreddy89/Inforsight/issues/42) and the later authorized release workflow |
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

R2-03 completed through issue #39 and PR #40, merge commit `5eb67c1`. Scoring authorization contract `1.0.0` now binds exact membership, row order, feature contract, labeled-matrix contents, training-matrix identity, fitted-preprocessor identity, and approved purpose across logistic, boosted, diagnostic, comparison, and reload paths. Ordinary inference uses a separate target-free matrix. The v1 fixture remains review-exposed historical evidence and is not re-sealed.

The limitation remains `Scheduled` because the future v2 final-holdout protocol and one-shot release workflow are not yet approved or proven.

#### Closure evidence

- [x] Current repository status and affected reports describe the v1 fixture truthfully without rewriting historical artifacts.
- [x] Relabeling, row substitution, reordering, feature substitution, target substitution, authorization tampering, and digest mismatch fail across logistic, boosted, diagnostic, and reload paths.
- [x] Authorized non-final scoring succeeds only for verified membership, purpose, preprocessing identity, and fitted-state compatibility.
- [x] Unlabeled inference does not depend on experiment partition names or targets.
- [ ] The v2 final-holdout protocol is approved before holdout materialization or access.
- [ ] A later one-shot evaluation records the authorized accessor, frozen artifact digests, command, timestamp, and result without permitting iterative model changes.

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
