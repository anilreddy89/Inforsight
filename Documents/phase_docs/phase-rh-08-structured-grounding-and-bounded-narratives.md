# RH-08 — Bind Narratives to Structured Evidence

## Issue metadata

| Field | Value |
| --- | --- |
| Initiative | Review hardening — post-Phase 3 maintenance and correctness |
| Stable work ID | `RH-08` |
| Delivery type | Design specification followed by bounded implementation |
| Status | RH-08I completed through [PR #168](https://github.com/anilreddy89/Inforsight/pull/168), merge `c283f184` |
| Milestone | `v0.3.1-decision-engine-hardening` (Milestone #6) |
| Classification | Current defect / safety boundary |
| Priority | High; mandatory for the hardening release |
| Strict predecessor | RH-08D issue #165 / PR #166, merge `8035001` |
| Governing backlog | [RH-08](../../docs/backlog.md#rh-08---bind-narratives-to-structured-evidence) |
| Source finding | [Project review finding 12](../Project_Review_Through_P4-01.md#12-grounding-is-lexical-and-incomplete) |
| Related contract | [RH-01 domain snapshot and semantic catalog](../../docs/hardening/rh-01-domain-snapshot-contract.md) |

## 1. Outcome

Case briefs and narrative outputs must be grounded in the canonical RH-01 snapshot and explicitly bound typed evidence. Factual fields are rendered deterministically; provider-generated text, if retained, is restricted to a versioned statement grammar. Every permitted claim resolves to typed evidence identifiers and matching policy, cutoff, snapshot, score, and model identity. Unsupported identifiers, amounts, dates, durations, percentages, actions, authorizations, causal claims, and status assertions fail validation or fall back to a deterministic template.

RH-08 establishes bounded local grounding. It does not prove arbitrary prose true, certify an external language model, or enable an external provider by default.

## 2. Starting state and defect

The current grounding guard performs lexical checks for selected currency/date values and action phrases. It does not establish factual accuracy for every statement, policy identifier, duration, percentage, causal assertion, paraphrased action, headline amount, or status claim. A grounding hash proves consistency between supplied input and text; it does not prove that the input is true. The default provider is deterministic/mock and is not evidence about an external provider under adversarial input.

RH-01 supplies the canonical dual-time snapshot, provenance, field evidence, and shared identity boundary. RH-08 must consume that evidence rather than reconstructing facts from unrestricted history, guessed dashboard fields, model features, or provider output.

## 3. Governing invariants

1. Narrative context contains one validated policy, cutoff, snapshot ID, visible evidence/provenance, and matching score/model identity when present.
2. Narrative code cannot read future events, unrestricted history, raw feature maps as domain truth, or caller-supplied factual overrides.
3. Every factual statement has a typed statement kind, canonical value, and evidence identifiers present in the bound context.
4. Dates and durations derive from cutoff-visible snapshot facts; amounts derive from typed facts or explicitly named versioned economics values. Unknown values remain unknown.
5. Recommendation, eligibility, authorization, consent, and execution are distinct claim types.
6. Causal, realized-outcome, external-validity, and production-performance claims are prohibited without separately governed evidence.
7. Unsupported kinds, mismatched identities, stale contexts, invalid evidence references, and unresolvable values fail closed or use the documented deterministic fallback.
8. A grounding hash is labeled input/text consistency evidence only, not truth, authenticity, or a universal hallucination guarantee.
9. External providers remain disabled by default and require adversarial fixtures plus an explicit configuration boundary before enablement.
10. Narrative generation has no action authority and cannot alter scores, tiers, eligibility, reservations, approvals, workflow transitions, model bytes, or historical artifacts.

## 4. Delivery split

**RH-08D — Design specification:** Define the versioned statement grammar, typed evidence model, context identity, deterministic rendering rules, rejection/fallback behavior, provider boundary, validator coverage matrix, and migration plan. RH-08D merges before RH-08I starts.

**RH-08I — Bounded implementation:** Implement the RH-08D contract, migrate case briefs and narrative consumers to bound context, preserve unknowns, and add adversarial regression coverage. Do not expand event, safety, economics, or authority taxonomies.

## 5. In scope

- Versioned typed statement grammar and typed evidence vocabulary.
- Context bound to RH-01 snapshot identity, cutoff, provenance, field evidence, and matching score identity where applicable.
- Deterministic rendering, safe fallback templates, stable validation failures, and provider-interface hardening.
- Explicit separation of facts, model outputs, eligibility, recommendation, authorization, and execution.
- Focused tests, documentation, and compatibility notes for local consumers.

## 6. Out of scope

- Proving arbitrary generated prose true or universal hallucination detection.
- Enabling an external LLM/provider as a release requirement.
- New event types, snapshot facts, safety evidence, economics/action rules, or model changes.
- Authority, approval, transition, reservation, audit durability, wire-contract, or production-infrastructure work owned elsewhere.
- Historical artifact rewriting, corrected evidence regeneration, final-holdout access, or Phase 4 implementation.

## 7. Predeclared acceptance gates

### RH-08D

- [ ] Versioned statement grammar and complete typed evidence vocabulary are specified.
- [ ] Each statement kind has source fields, evidence-ID resolution, renderer, and rejection/fallback behavior.
- [ ] Context identity binds policy, cutoff, snapshot, provenance/evidence, and matching score/model identity where relevant.
- [ ] Unsupported identifiers, amounts, dates, durations, percentages, actions, authorizations, causal claims, and status assertions are explicitly rejected.
- [ ] Validator coverage distinguishes input/text consistency from truth, authenticity, and provider behavior.
- [ ] Provider default-disabled disposition, adversarial fixture protocol, and migration plan are documented.
- [ ] Design validation, boundary checks, and `git diff --check` pass.

### RH-08I

- [ ] Case-brief facts render deterministically from the canonical snapshot and matching evidence.
- [ ] Invalid identity, evidence references, unsupported kinds, and unresolvable values fail closed or use the documented fallback.
- [ ] Adversarial fixtures cover fabricated IDs, amounts, dates, durations, percentages, actions, authorizations, causal claims, and status assertions.
- [ ] Unknown facts remain unknown and are not replaced with defaults or provider prose.
- [ ] Provider text cannot bypass the statement grammar or mutate operational state.
- [ ] Existing supported local outputs remain compatible or receive a versioned migration note.
- [ ] Focused tests, full headless `make check`, boundary checks, and `git diff --check` pass.
- [ ] Protected historical artifacts remain byte-identical; no final holdout is accessed or materialized.

## 8. Dependencies and downstream gates

RH-01 is complete and supplies the domain snapshot/semantic catalog boundary. RH-07/#129 must close before RH-08 starts operationally. RH-08 blocks the grounding component of RH-11 qualification and participates in the RH-09/RH-10-to-RH-11 gate. RH-12 owns evidence regeneration and documentation reconciliation. P4-02/P4-03 remain paused until RH-13 records `PROCEED`.

## 9. Execution sequence

1. Confirm RH-07 issue/PR closeout and start RH-08D from updated `main`.
2. Inventory grounding, case-brief, assistant-context, and dashboard seams; preserve existing behavior as compatibility evidence.
3. Review grammar, typed evidence, identity rules, coverage matrix, and migration plan before implementation.
4. Open RH-08I only after RH-08D merges; start with adversarial and unknown-fact regressions.
5. Implement deterministic rendering and bounded provider validation, migrate consumers, and run the full hardening gate.
6. Record merged issue/PR evidence in this document and the repository trackers.

## 10. Issue tracking and implementation instructions

RH-08D is tracked by issue [#165](https://github.com/anilreddy89/Inforsight/issues/165) and merged through [PR #166](https://github.com/anilreddy89/Inforsight/pull/166), merge `8035001`. RH-08I issue [#167](https://github.com/anilreddy89/Inforsight/issues/167) closed through [PR #168](https://github.com/anilreddy89/Inforsight/pull/168), merge `c283f184`.

### RH-08D design issue — merged

- Template: `.github/ISSUE_TEMPLATE/design.yml`
- Issue: [#165](https://github.com/anilreddy89/Inforsight/issues/165)
- PR: [#166](https://github.com/anilreddy89/Inforsight/pull/166), merge `8035001`
- Title: `[Design] RH-08D: Define structured grounding and bounded narrative contract`
- Label: `design`
- Milestone: `v0.3.1-decision-engine-hardening`
- Work metadata: `Backlog work ID: RH-08D; Classification: Current defect / safety boundary; Priority: High; Milestone: v0.3.1-decision-engine-hardening`
- Outcome: paste Section 1.
- Context: cite RH-01, RH-07/#129, the source review finding, and this phase document.
- Scope: paste Sections 5–6; state that RH-08I is the linked implementation child.
- Impact: no runtime or historical-artifact changes while design is open; introduces a versioned narrative contract; RH-08I must provide migration handling.
- Acceptance: paste the RH-08D checklist in Section 7.
- Evidence: design document, grammar/coverage matrix, accepted/rejected examples, design validation, boundary checks, and `git diff --check`.
- Dependencies: `Must merge first: RH-07/#129 implementation PR. Blocks: RH-08I and RH-11 grounding qualification. Related: RH-01, RH-03, RH-07, RH-12.`

The normative design is [the RH-08D contract](../../docs/hardening/rh-08-structured-grounding-contract.md). RH-08I is governed by the separate [implementation phase document](phase-rh-08i-structured-grounding-implementation.md).

### RH-08I implementation issue — implementation complete locally

Issue [#167](https://github.com/anilreddy89/Inforsight/issues/167) is open. The implementation is complete locally on `fix/167-rh-08i-structured-grounding`; open the PR and record its number here after creation.

- Title: `[Implementation] RH-08I: Bind narratives to structured evidence`
- Label: `implementation`
- Milestone: `v0.3.1-decision-engine-hardening`
- Work metadata: `Backlog work ID: RH-08I; Classification: Current defect / safety boundary; Priority: High; Milestone: v0.3.1-decision-engine-hardening`
- Outcome: paste Section 1 and state that the merged RH-08D contract governs implementation.
- Context: link the merged RH-08D issue/PR, RH-01, RH-07, and the source review finding.
- Scope and impact: paste Sections 5–6; state that no model, holdout, or historical artifact changes are permitted.
- Acceptance: paste the RH-08I checklist in Section 7.
- Evidence: include accepted/rejected fixture output, focused tests, full headless `make check`, boundary checks, and `git diff --check`.
- Dependencies: `Must merge first: RH-08D. Blocks: RH-11 grounding qualification. Related: RH-01, RH-03, RH-07, RH-09, RH-10, RH-12.`

Use the resulting issue number in the branch and PR: `fix/<issue-number>-rh-08i-structured-grounding`; PR title `RH-08I: Bind narratives to structured evidence`; body must include `Closes #<issue-number>`.

## 11. Verification commands

```bash
source .venv/bin/activate
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/inforsight-mpl make check
./scripts/check_repository_boundaries.sh
git diff --check
git status --short
```

Do not access or materialize the final holdout, enable an external provider without the RH-08D gate, regenerate historical evidence, or accept generated changes without exact diff inspection.
