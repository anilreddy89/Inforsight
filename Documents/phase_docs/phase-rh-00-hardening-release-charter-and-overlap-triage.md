# RH-00 — Hardening Release Charter, Claim Freeze, and Overlap Triage

## Issue metadata

| Field | Value |
| --- | --- |
| Initiative | Review hardening — post-Phase 3 maintenance and correctness |
| Sequence | 00 |
| Stable work ID | `RH-00` |
| GitHub issue | [#133](https://github.com/anilreddy89/Inforsight/issues/133) |
| Issue title | `ADR: RH-00 — Charter the decision-engine hardening release` |
| Branch | `docs/133-rh-00-hardening-charter` |
| Pull request | Pending |
| Status | Implemented locally — `ADOPT` recorded; awaiting pull request |
| Milestone | [`v0.3.1-decision-engine-hardening`](https://github.com/anilreddy89/Inforsight/milestone/6) (Milestone #6) |
| Priority | Release blocking |
| Classification | Architecture decision / governance |
| Source review | `Documents/Project_Review_Through_P4-01.md`, reviewed at commit `b15a9ba` |
| Reviewer approval | `Documents/Hardening_Plan_Approval_and_Phase4_Gates.md` (2026-09-07) |
| Governing plan | `docs/backlog.md`, Review hardening initiative |
| Enables | RH-01D and other independent RH issues whose specifications are ready |
| Blocks | Creation of the hardening milestone and all dependent RH implementation work |
| Phase 4 boundary | P4-01 remains historical; P4-02/P4-03 implementation remains blocked through RH-13 |
| Last reviewed | 2026-09-07 |

---

## 1. Decision requested

Approve the review-hardening work in `docs/backlog.md` as a separate maintenance and correctness initiative with the stable prefix `RH` and proposed release identity `v0.3.1-decision-engine-hardening`.

Acceptance of RH-00 also:

1. freezes claims that exceed the evidence while hardening work remains open;
2. adopts the dependency and merge flow in the governing backlog;
3. preserves P4-01 as architecture-inception history while treating its affected contracts as provisional;
4. blocks P4-02 and P4-03 implementation until RH-13 records `PROCEED`; and
5. assigns a governed disposition to open issues #128, #129, and #130.

RH-00 is a governance and documentation decision. It does not fix the reviewed defects, change runtime behavior, regenerate evidence, or implement distributed infrastructure.

## 2. Context and evidence

The review at `Documents/Project_Review_Through_P4-01.md` found correctness, contract, evidence, and claim-boundary gaps in the Phase 0–3 reference implementation and the provisional Phase 4 interfaces. The follow-up assessment in `Documents/Hardening_Plan_Approval_and_Phase4_Gates.md` approved starting a bounded hardening initiative and incorporated six acceptance refinements into the backlog.

The canonical initiative plan is the **Review hardening initiative** section of `docs/backlog.md`. It defines RH-00 through RH-13, design/implementation child IDs, dependency gates, finding coverage, exit criteria, and exclusions. The supporting `Documents/review-hardening-initiative.md` is not the execution authority when it differs from the backlog.

The approval is deliberately narrow:

- it authorizes the hardening program, not a hardening release;
- it does not establish that any reviewed defect is fixed;
- it does not authorize production or customer-facing use;
- it does not convert synthetic results into external or causal evidence; and
- it does not resume P4-02 or P4-03.

## 3. Constraints and non-negotiable boundaries

1. GitHub issues own active work; `docs/backlog.md` owns RH order and dependency gates.
2. One stable RH ID maps to one issue, one branch, and one primary pull request. Where design and implementation must be separate, use the declared `D` and `I` child IDs.
3. Historical artifacts remain immutable. Corrected evidence receives a new version and an explicit supersession note.
4. Clean-room, dual-time/point-in-time, final-holdout, human-authority, and compatibility boundaries remain mandatory.
5. No RH artifact may claim production certification, external validity, realized profit, complete factual grounding, universal tamper resistance, or measured distributed performance without direct evidence.
6. Implement only the minimum bounded reference behavior required to establish each invariant.
7. Kafka, Java control-plane implementation, PostgreSQL/KMS deployment, Kubernetes, production identity federation, production connectors, multi-region scaling, a new causal/deep model, and a live LLM are outside RH.
8. P4-01 is amended through RH-09 rather than rewritten. P4-02/P4-03 implementation cannot begin before an RH-13 `PROCEED` decision.
9. The milestone, eventual tag, release title, and release-notes filename use `v0.3.1-decision-engine-hardening`.
10. The milestone is created only after RH-00 is accepted; consequently, the RH-00 issue is opened without a milestone and assigned immediately after the decision is recorded.

## 4. Options considered

### Option A — Adopt the bounded RH initiative (recommended)

Create a separate `v0.3.1-decision-engine-hardening` maintenance track, preserve Phase 4 numbering, freeze unsupported claims, and require RH-13 before resuming dependent Phase 4 implementation.

**Consequences:** Defects and claim corrections receive explicit owners and gates; historical evidence stays intact; Phase 4 schedule is subordinate to correctness; the initiative adds governance and release work.

### Option B — Absorb the findings into Phase 4

Fold review findings into P4-02 onward and repair behavior while porting it to distributed services.

**Rejected because:** unsettled semantics could be copied into new service and wire contracts, while correctness fixes become coupled to infrastructure scope.

### Option C — Treat findings as independent technical debt

Keep issues uncoordinated and allow Phase 4 to proceed without a release gate.

**Rejected because:** cross-component dependencies, evidence regeneration, and public claim corrections would have no common exit decision.

### Option D — Reopen or rewrite Phase 3 history

Modify previously published artifacts and qualification claims in place.

**Rejected because:** this would erase provenance and obscure which evidence was historical versus corrected.

## 5. Recommended decision and consequences

Record **ADOPT** for Option A and authorize the canonical RH plan in `docs/backlog.md`, including its stable IDs, `D`/`I` child convention, dependency graph, exit criteria, and Phase 4 pause boundary.

Upon acceptance:

1. create the `v0.3.1-decision-engine-hardening` GitHub milestone;
2. assign RH-00 and all subsequent RH issues to it;
3. update `docs/limitations.md` with the temporary claim freeze and RH ownership;
4. amend and relabel issues #128–#130 according to the dispositions below;
5. add the RH lane to the interactive roadmap; and
6. open only predecessor-satisfied issues, beginning with RH-01D and independently ready work.

If the decision is not accepted, record `REVISE` or `STOP`, leave the milestone uncreated, and do not begin dependent implementation.

## 6. Existing-issue overlap triage

The following dispositions are part of the RH-00 decision. They avoid duplicate stable IDs while preserving useful issue history.

| Existing issue | Field-by-field finding | RH disposition |
| --- | --- | --- |
| [#128](https://github.com/anilreddy89/Inforsight/issues/128) — documentation hardening | Its realism boundary, model-card maturity, decision-utility interpretation, and walkthrough work overlaps RH-12. Its current numeric value language must be bounded as modeled synthetic evidence, and its “limitations affected: none” statement conflicts with RH claim reconciliation. | **Amend and adopt as RH-12** when RH-12 is predecessor-ready. Replace the TBD ID, classification, priority, milestone, dependencies, claim impact, and acceptance checks with the canonical RH-12 specification. Retain the realism-boundary and walkthrough deliverables where they support reconciliation. Do not execute it early. |
| [#129](https://github.com/anilreddy89/Inforsight/issues/129) — monitoring hardening | Evidence-bearing windows, outcome joins, insufficient-data state, and drift/calibration tests overlap RH-07. Its proposed workflow transition overlaps RH-03, and its low-density detector and three-scenario report exceed the minimum RH-07 outcome unless separately justified. | **Amend and adopt as RH-07** after RH-06 closes. Replace the TBD ID and metadata; make actual scoring traffic, resolved-outcome ingestion, version-keyed bounded windows, and `insufficient_data` the release-blocking scope. Link authority-transition work to RH-03. Keep overconfidence or scenario-stress work only as non-blocking scope with predeclared evidence rules, or defer it. |
| [#130](https://github.com/anilreddy89/Inforsight/issues/130) — simulator stress variants | Scenario variants and robustness reporting support RH-12, but a mandatory “model remains calibrated” result is not a valid predeclared acceptance condition, and the work is not required to repair the core substrate. Fresh confirmation is optional under the approved plan. | **Leave independent and blocked by RH-12 triage**, rather than assign a second RH-12 identity. Amend its claim language so observed degradation is reportable rather than a failure to be designed away. RH-12 decides whether to incorporate a bounded subset, supersede it, or schedule it after the hardening release. It must not mutate historical v6 artifacts or access a final holdout. |

No issue should be closed as superseded during RH-00 unless its retained deliverables and links have first been moved to an owning issue. This preserves discussion and provenance.

## 7. Temporary claim freeze

Until RH-13 records `PROCEED`, active documentation and issue/PR text must use the following boundaries. RH-00 records the policy; the implementation PR must add corresponding scheduled entries to `docs/limitations.md`.

### Allowed descriptions

- synthetic-only, local reference implementation;
- reproducible engineering and modeling evidence within the declared synthetic mechanism;
- modeled or simulated decision value under explicit action-effect and cost assumptions;
- hash-chain integrity checks within the documented local trust boundary;
- in-process latency measured in the recorded environment; and
- P4-01 architecture-inception scaffolds with provisional affected contracts.

### Frozen claims

- production-ready, enterprise-certified, or customer-ready;
- externally validated actuarial or real-carrier performance;
- realized profit, customers saved, or empirically causal treatment uplift;
- complete factual grounding or universal hallucination prevention;
- immutable or universally tamper-proof audit storage;
- measured network, distributed, sustained-load, or cloud performance; and
- authorization to start P4-02/P4-03 implementation.

Historical artifacts are not rewritten. Where surfaced in active documentation, their statements receive present-day context and explicit supersession or limitation links.

## 8. Dependency and execution gate

```text
RH-00 decision accepted
  ├─ create v0.3.1-decision-engine-hardening milestone
  ├─ record claim freeze in docs/limitations.md
  ├─ reconcile #128, #129, and #130
  ├─ add separate RH roadmap lane
  └─ open predecessor-satisfied RH issues
       └─ ... RH-11 → RH-12 → RH-13
                              └─ PROCEED required for P4-02/P4-03
```

The complete dependency graph in `docs/backlog.md` remains authoritative.

## 9. Decision acceptance checks

- [ ] The issue records `ADOPT`, `REVISE`, or `STOP`; only `ADOPT` enables the actions below.
- [ ] The `v0.3.1-decision-engine-hardening` identity, stable `RH` IDs, `D`/`I` child convention, dependency graph, and exit criteria are approved.
- [ ] The 2026-09-07 approval and source review at commit `b15a9ba` are linked.
- [ ] The clean-room, point-in-time, holdout, authority, historical-artifact, and minimum-reference-scope boundaries are accepted.
- [ ] The temporary allowed and frozen claims are approved for entry in `docs/limitations.md`.
- [ ] Issues #128–#130 are reviewed against the table above and each receives an explicit disposition.
- [ ] P4-01 remains historical architecture-inception evidence with provisional affected contracts.
- [ ] P4-02/P4-03 implementation is explicitly blocked until RH-13 records `PROCEED`.
- [ ] No application behavior, model, generator, evaluation result, or distributed infrastructure is changed by RH-00.
- [ ] The milestone is created only after the issue records `ADOPT`, then assigned to RH-00.
- [ ] `git diff --check` and repository boundary checks pass for the documentation change.

## 10. Deliverables

### In scope for the RH-00 implementation PR

- this phase document;
- scheduled limitation entries that implement the approved claim freeze;
- backlog status/link reconciliation after the GitHub issue exists;
- roadmap representation of RH as a separate lane;
- issue #128–#130 metadata/body amendments matching the accepted dispositions; and
- tracker/project-status updates required by the repository workflow.

### Explicitly out of scope

- runtime, model, simulator, schema, API, or infrastructure changes;
- regenerated evaluation evidence;
- implementation of RH-01 through RH-13;
- creation of a release tag or GitHub release; and
- resumption of P4-02/P4-03.

## 11. Verification plan

```bash
git diff --check
./scripts/check_repository_boundaries.sh
make check
git status --short
```

Review the final diff to confirm that historical evidence is unchanged, the current backlog draft is preserved, and no unrelated file is included.

### Local verification evidence — 2026-09-07

- `node --check docs/roadmap/app.js`: passed.
- `git diff --check`: passed.
- `./scripts/check_repository_boundaries.sh`: passed.
- All `make check` targets passed through the project virtual environment; the dashboard target required the documented local headless override `MPLBACKEND=Agg`.
- Dashboard suite: 9 tests passed.
- Phase 3 qualification: Gates S1–S6 passed and 7 focused tests passed.
- Aggregate simulator suite: 465 tests passed.
- Published artifact reproducibility checks passed; no historical evidence or final-holdout artifact was changed.

The default local dashboard command aborted in the native GUI backend before the headless override was supplied. RH-11 retains ownership of making the repository-level check reliably configure and verify its headless plotting environment.

## 12. Issue-opening field content

Use `.github/ISSUE_TEMPLATE/decision.yml` and populate it from this document:

- **Work and release metadata:** metadata table and proposed-milestone timing in Sections 1 and 3.
- **Context:** Section 2.
- **Constraints and non-negotiable boundaries:** Sections 3 and 7.
- **Options considered:** Section 4.
- **Recommendation and consequences:** Sections 5 and 6.
- **Decision acceptance checks:** Section 9.
- **Dependencies and downstream work:** Sections 8 and 10.

Issue #133 recorded `ADOPT` on 2026-09-07 before Milestone #6 was created and assigned. Implementation proceeds on `docs/133-rh-00-hardening-charter`.
