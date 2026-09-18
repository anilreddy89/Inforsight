# RH-11: Expanded qualification, CI, and read-only artifact verification

Status: implementation complete locally; issue #179 open and PR pending  
Release: `v0.3.1-decision-engine-hardening`  
Classification: test gap / tooling defect  
Priority: release blocking  
Dependencies: RH-01 through RH-10; RH-07 issue #129 / PR #164 is merged  
Downstream: RH-12 evidence reconciliation, RH-13 release decision

## Purpose

RH-11 is the qualification gate for the hardening release. It must prove that
the repaired contracts and safety boundaries are exercised together across the
simulator, serving layer, dashboard, inference runtime, CI packaging, and
adversarial checks. The gate must also prove that verification is read-only and
does not rewrite published evidence while running in check mode.

RH-11 does not make the system production-ready, establish network or sustained
load performance, or authorize Phase 4 implementation. Those claims remain
blocked until direct evidence exists and RH-13 records the release decision.

## Required outcome

The completed increment must provide a reproducible qualification path that:

- installs and runs the release-relevant suites in CI;
- exercises meaningful Streamlit interactions and refresh behavior;
- runs clean-image runtime, API/interface, contract, authority, audit,
  monitoring, harmful-treatment, and grounding adversarial checks;
- verifies `--check` and artifact checks are read-only against published
  evidence;
- states exactly what each qualification gate proves and does not prove;
- replaces the static README workflow badge with truthful workflow status; and
- verifies clean working-tree operation and a documented headless plotting
  backend.

## Scope

### RH-11 owns

- CI matrix coverage and parallel qualification jobs for dashboard, serving,
  simulator, inference runtime, contracts, and repository boundaries;
- Streamlit AppTest coverage for meaningful interactions, capacity,
  point-in-time behavior, and post-decision refresh;
- clean-image or isolated-environment runtime smoke and API/interface tests;
- contract compilation/lint and authority-bypass regression coverage;
- audit truncation, monitoring-evidence, harmful-treatment, and structured
  grounding adversarial checks;
- read-only verification of `--check` paths and published artifacts;
- explicit claim-boundary text for timing, qualification, and clean-environment
  evidence; and
- README workflow-badge and qualification documentation reconciliation.

### Out of scope

- regenerating corrected scientific or economic evidence owned by RH-12;
- changing model training, decision policy, or workflow semantics except where
  required to expose an existing qualification seam;
- making in-process timing claims into network or sustained-load claims;
- PostgreSQL, KMS, Kafka, Java, cloud deployment, or production readiness;
- inspecting, transforming, predicting, or evaluating a final holdout; and
- the formal `PROCEED`, `REMEDIATE`, or `STOP` decision owned by RH-13.

## Dependency and merge order

```text
RH-07 issue #129 / PR #164 (merged `793217f`)
  -> RH-10 issue #174 / PR #176 (merged 30e1155)
  -> RH-11 issue #179 / branch `test/179-rh-11-qualification-ci`
  -> RH-12 evidence reconciliation
  -> RH-13 release decision
```

RH-11 starts from updated `main` after the RH-10 merge and the completed RH-07
implementation. RH-12 and RH-13 remain blocked until the RH-11 evidence is
complete.

## Acceptance gate

- [ ] CI installs and runs dashboard and serving suites plus all release-relevant `make check` targets.
- [ ] Streamlit AppTest covers meaningful interactions, capacity, point-in-time, and post-decision refresh behavior.
- [ ] Clean-image runtime smoke, API/interface tests, contract compile/lint, authority bypass, audit truncation, monitoring evidence, harmful-treatment, and grounding adversarial tests run in CI.
- [ ] `--check` and artifact verification are read-only and compare against published evidence.
- [ ] Each qualification gate states precisely what it proves; in-process timing is not described as network or sustained-load evidence.
- [ ] The README badge reflects the actual workflow rather than a static passing image.
- [ ] Verification checks working-tree cleanliness, runs in a clean environment, and uses a documented headless plotting backend.
- [ ] No final holdout is accessed, transformed, predicted, or evaluated.
- [ ] Historical artifacts remain unchanged unless a separately versioned RH-12 evidence update authorizes replacement.

## Issue creation map

Create one implementation issue from `.github/ISSUE_TEMPLATE/implementation.yml`:

| Work | Template | Title | Label | Milestone |
| --- | --- | --- | --- | --- |
| RH-11 | Implementation task | `[Implementation] Expand qualification, CI, and read-only artifact verification` | `implementation` | `v0.3.1-decision-engine-hardening` |

Use the exact field guidance in `docs/engineering-improvement-workflow.md`.
Implementation issue: [#179](https://github.com/anilreddy89/Inforsight/issues/179)
on branch `test/179-rh-11-qualification-ci`. The primary deliverable is a
qualification and evidence gate.

## Claim and artifact impact

RH-11 may add test fixtures, CI configuration, qualification logs, and
documentation. It must not add production-readiness, network-performance,
distributed-durability, authenticity, tamper-resistance, or exactly-once
claims. Verification must be read-only in check mode and must not overwrite
historical artifacts. Any deterministic output or serialized contract change
requires explicit versioning, migration notes, and review before acceptance.

## Completion evidence

The RH-11 closeout should link:

- the issue and PR numbers and merge commit;
- CI job names and final required status;
- Streamlit AppTest and clean-image smoke output;
- contract, interface, authority, audit, monitoring, harmful-treatment, and
  grounding adversarial test output;
- proof that check-mode verification leaves the working tree and published
  artifacts unchanged;
- the documented headless plotting configuration; and
- the exact claims passed to RH-12 and RH-13 without broadening them.

Local implementation evidence: the full guarded `make check` path passes 528
tests and leaves the working tree unchanged. Final RH-11 closure remains
pending issue #179 closure and PR merge.
