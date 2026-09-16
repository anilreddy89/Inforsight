# RH-07 — Make Monitoring States Evidence-Bearing

## Issue metadata

| Field | Value |
| --- | --- |
| Initiative | Review hardening — post-Phase 3 maintenance and correctness |
| Stable work ID | `RH-07` |
| Delivery type | Implementation task |
| Status | Implemented locally; uncommitted |
| GitHub issue | [#129](https://github.com/anilreddy89/Inforsight/issues/129), open |
| Branch | `fix/129-rh-07-evidence-bearing-monitoring` |
| Milestone | [`v0.3.1-decision-engine-hardening`](https://github.com/anilreddy89/Inforsight/milestone/6) (Milestone #6) |
| Classification | Current defect / test gap |
| Priority | High; mandatory for the hardening release |
| Strict predecessor | RH-06I [issue #162](https://github.com/anilreddy89/Inforsight/issues/162), [PR #163](https://github.com/anilreddy89/Inforsight/pull/163), merge `df69910` |
| Governing backlog | [RH-07](../../docs/backlog.md#rh-07---make-monitoring-states-evidence-bearing) |
| Source finding | [Project review finding 6](../Project_Review_Through_P4-01.md#6-high--monitoring-appears-healthy-without-evidence) |
| Related limitation | [LIM-RH-001](../../docs/limitations.md#lim-rh-001--review-findings-constrain-current-product-evidence-and-phase-4-claims) |
| Started | 2026-09-16 |
| Verification | Full `make check` passed on 2026-09-16; 507 simulator tests plus all contract, serving, dashboard, and qualification gates; protected historical artifacts restored unchanged |

## 1. Outcome

Repair the bounded local monitoring path so diagnostics describe evidence actually observed by the serving runtime. Actual scoring traffic must populate bounded feature windows keyed by the accepted model identity. Resolved outcomes must enter through an exposed operational interface and join only the corresponding policy, observation, and model version. Until the applicable evidence window is adequate, diagnostics must return an explicit `insufficient_data` state rather than a favorable drift, calibration, or skill conclusion.

RH-07 closes only after the focused evidence path, version-safe outcome ingestion, diagnostics contract, and adversarial tests are implemented and verified. It does not retrain the frozen model, manufacture observations or outcomes, change action authority, regenerate historical evidence, or establish production monitoring infrastructure.

## 2. Starting state and defect

P3-04A supplied monitoring calculations, telemetry, and `GET /v1/diagnostics`, but its state can appear healthy without real scored traffic or resolved outcomes. A metric formula is not monitoring evidence when its input window is empty, undersized, synthetic by default, or joined across model identities.

RH-06 has now supplied the independently installable inference runtime and canonical HTTP image. RH-07 begins from updated `main` after merge `df69910`; it must use that runtime's trusted bundle/model identity rather than recreate model loading or a parallel scoring boundary.

The original degradation-transition proposal in issue #129 overlaps the RH-03 authority boundary. RH-07 retains only evidence-bearing monitoring. Low-density overconfidence detection and multi-scenario stress reporting are not RH-07 release gates unless a later governed amendment predeclares them.

## 3. Governing invariants

1. A drift window receives feature values only from successful, accepted scoring requests; no default, fixture, startup, diagnostics-read, or synthetic record may populate it.
2. Every retained score record binds the policy identifier, observation identifier, model/bundle version or immutable identity, score timestamp, and the feature values needed for the declared drift calculation.
3. Retention is bounded and deterministic. Eviction and window limits are documented; diagnostics expose the retained evidence count and applicable identity.
4. Drift is evaluated only against scoring records for the requested/current model identity and only after its declared minimum sample threshold is reached.
5. A resolved outcome joins only one previously retained score using the exact `(policy_id, observation_id, model_version)` key. Unknown, ambiguous, duplicate-conflicting, and cross-version joins fail explicitly and do not mutate calibration state.
6. Outcome ingestion is idempotent for the same immutable outcome payload. A repeated submission cannot inflate counts or metrics.
7. Calibration and skill calculations consume only joined score/outcome pairs. Empty or undersized windows report `insufficient_data`; they must not report `well_calibrated`, perfect skill, absence of drift, or a favorable alert summary.
8. Diagnostics state meanings, thresholds, counts, time bounds, and identity/version fields are serialized explicitly. Compatibility changes are versioned or bridged deliberately.
9. Monitoring is observational. It has no action authority and cannot alter scores, tiers, cases, approvals, workflow transitions, model bytes, or model selection.
10. Historical artifacts remain immutable. RH-07 uses focused fictional/public/clean-room-safe fixtures and does not access the final holdout.

## 4. In scope

- Integrate a bounded, model-version-keyed scored-feature retention path with successful single and batch serving scores.
- Define score-record identity, retention limit, eviction behavior, minimum drift and calibration evidence thresholds, and explicit monitoring states.
- Expose a bounded operational resolved-outcome ingestion interface, with validation, idempotency, and stable failures for missing, ambiguous, duplicate-conflicting, and cross-version joins.
- Update `GET /v1/diagnostics` and its schemas/tests to expose evidence counts, identity, window status, and `insufficient_data` semantics.
- Add focused unit, route, and integration tests proving no-evidence behavior, traffic-populated drift, joined-outcome calibration, duplicate handling, version isolation, and bounded retention.
- Document the accepted thresholds, retention bounds, interface, claim boundaries, and compatibility disposition.

## 5. Out of scope

- Retraining, recalibrating, replacing, or otherwise changing the frozen release model, feature contract, bundle, or thresholds.
- Inventing default feature observations, outcomes, labels, or favorable metric values.
- Action-authority, approval, degradation-transition, or workflow semantics owned by RH-03.
- Mandatory overconfidence detection, scenario stress generation, production alerting, databases, Kafka, cloud deployment, or external monitoring connectors.
- Rewriting or regenerating historical Phase 2/3 artifacts; RH-12 owns coordinated evidence regeneration and documentation reconciliation.
- Final-holdout access, real customer data, credentials, or Phase 4 implementation. P4-02/P4-03 remain blocked until RH-13 records `PROCEED`.

## 6. Acceptance checks

- [x] Successful scoring traffic populates bounded drift windows keyed by trusted model identity.
- [x] Window retention and eviction are bounded, deterministic, documented, and visible through diagnostics evidence counts.
- [x] An exposed resolved-outcome interface joins exact policy, observation, and model-version identities.
- [x] Outcome ingestion is idempotent and rejects missing, ambiguous, duplicate-conflicting, and cross-version joins without mutating metrics.
- [x] Empty and undersized drift/calibration windows return `insufficient_data`, never `well_calibrated`, perfect skill, or absence-of-drift claims.
- [x] Diagnostics serialize evidence counts, thresholds/statuses, time bounds, and relevant model identity/version; changed response meaning is versioned as schema 1.1.0.
- [x] Tests demonstrate detectable drift only after actual scoring traffic and calibration metrics only after adequate resolved outcomes.
- [x] Monitoring remains observational and cannot change scores, tiers, cases, approvals, or workflow transitions.
- [x] Focused suites, affected serving/runtime suites, `make check`, repository-boundary checks, and `git diff --check` pass.
- [x] Historical protected artifacts remain unchanged; no final holdout is accessed or materialized.
- [x] Backlog, tracker, limitation register, roadmap, and this phase document agree on implementation status and remaining hardening gates.

## 7. Required review evidence

The implementing pull request must include:

- the score-record and resolved-outcome interface/schema, retention limits, thresholds, state vocabulary, and compatibility decision;
- proof that diagnostics before traffic and before adequate outcomes return `insufficient_data` with truthful evidence counts;
- score-traffic fixtures showing version-keyed drift windows populate and an intentionally shifted feature distribution produces the declared drift state only after the threshold;
- outcome fixtures showing an exact join, idempotent replay, rejection of unknown/ambiguous/cross-version/conflicting inputs, and calibration only after adequate joined outcomes;
- evidence that window eviction is bounded and deterministic, including batch-score behavior;
- route/contract evidence for diagnostics and outcome ingestion, plus affected serving and runtime suite results;
- full headless `make check`, repository-boundary, `git diff --check`, and protected-artifact clean-diff results; and
- a reviewed-scope statement confirming observational-only behavior, frozen model/bundle, clean-room inputs, no final holdout, and unchanged Phase 4 pause.

## 8. Dependencies and downstream gates

RH-06 is satisfied through issue #162 and PR #163, merge `df69910`. RH-07 blocks the monitoring-evidence component of RH-11 qualification. It remains subject to the initiative-wide claim restrictions in LIM-RH-001.

RH-03 continues to own authority and transition enforcement. RH-12 continues to own corrected-evidence regeneration and public-documentation reconciliation. RH-09, RH-10, P4-02, and P4-03 receive no authority from this work; P4-02/P4-03 remain paused until RH-13 records `PROCEED`.

## 9. Execution sequence

1. Update local `main` and create the implementation branch from the RH-06I successor state; replace this document's status and branch/PR fields when implementation begins.
2. Inventory current scoring hooks, monitoring state, diagnostics schema, and test seams; add failing no-evidence and version-isolation regressions first.
3. Define the bounded score record, model identity, retention/eviction policy, thresholds, and explicit state vocabulary before consumer changes.
4. Wire successful serving scores into the version-keyed window and expose validated outcome ingestion with idempotent joins.
5. Update diagnostics serialization and alert aggregation so every conclusion is evidence-qualified.
6. Add traffic, drift, outcome, calibration, duplicate, cross-version, eviction, and route integration tests.
7. Run focused suites and the full review gate, inspect any generated changes, and preserve protected historical artifacts.
8. Open one implementation PR titled `RH-07: Make monitoring states evidence-bearing`, include `Closes #129`, and record merge evidence here and in the trackers after required checks pass.

## 10. Verification commands

Use the project virtual environment and a headless plotting backend. Select focused test paths after the implementation creates them, then run the project gate:

```bash
source .venv/bin/activate

# Run focused serving monitoring, diagnostics, and outcome-ingestion tests.
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/inforsight-mpl make check
./scripts/check_repository_boundaries.sh
git diff --check
git status --short
git diff --stat
```

Do not materialize or inspect a final holdout, refit/recalibrate the model, regenerate historical evidence, or accept unintended generated changes without exact diff inspection and restoration.

## 11. GitHub issue reconciliation

Issue [#129](https://github.com/anilreddy89/Inforsight/issues/129) is the canonical RH-07 implementation issue. Its accepted scope is this document's bounded evidence path: score traffic, version-keyed retention, exact resolved-outcome joins, idempotency, explicit insufficient-data semantics, diagnostics evidence counts, and focused proof. The issue's original degradation-transition and optional stress/overconfidence ideas are explicitly excluded unless a separate governed amendment is accepted.

The implementation is complete in the local uncommitted worktree and all repository gates pass. Issue closure, pull-request evidence, and the final merged commit remain intentionally pending because this work was requested without committing.
