# RH-08D: Structured grounding and bounded narrative contract 1.0.0

## Status and ownership

This design specification is RH-08D for issue [#165](https://github.com/anilreddy89/Inforsight/issues/165). It defines the contract that RH-08I will implement. It introduces no runtime behavior, provider enablement, model change, artifact regeneration, or final-holdout access.

| Field | Value |
| --- | --- |
| Contract ID | `inforsight.structured-grounding` |
| Contract version | `1.0.0` |
| Design issue | [#165](https://github.com/anilreddy89/Inforsight/issues/165) |
| Implementation child | RH-08I; issue to be opened after this design merges |
| Parent outcome | RH-08 |
| Required predecessor | RH-07 issue #129 and implementation closeout |
| Canonical domain source | RH-01 `DomainSnapshot` 1.0.0 and semantic catalog |
| Default provider | Deterministic local/template path; external providers disabled |

## 1. Purpose and claim boundary

The narrative boundary accepts a typed, immutable evidence context and produces either a deterministic case-brief rendering or a constrained candidate statement set. A statement is accepted only when its kind, value, identity, and evidence references resolve against the context. The contract establishes input-to-text consistency for the declared grammar; it does not establish that source facts are true, authentic, complete, externally valid, causal, or suitable for production decisions.

The current lexical grounding guard may remain as a compatibility adapter during RH-08I migration, but its coverage must not be described as complete grounding. `GroundingAudit` fields such as `hallucination_detected` must not be interpreted as a universal hallucination guarantee.

## 2. Bound narrative context

RH-08I must introduce or adapt a context with these required identities:

| Field | Requirement |
| --- | --- |
| `policy_id` | Nonempty and equal across snapshot, case, and all statements |
| `case_id` | Nonempty case identity; not a source fact |
| `as_of` | Explicit timezone-aware UTC cutoff |
| `snapshot_id` | Exact RH-01 canonical snapshot identity |
| `snapshot_contract_version` | Supported RH-01 version, currently `1.0.0` |
| `provenance_event_ids` | Only cutoff-visible source evidence IDs |
| `field_evidence` | RH-01 field-to-event evidence mapping |
| `score_identity` | Optional; required for score statements and bound to model/bundle/preprocessing identity |
| `eligibility_identity` | Optional; required for eligibility/recommendation statements |
| `authority_state` | Presence-aware state; narrative cannot turn recommendation into authorization |
| `grounding_contract_version` | `inforsight.structured-grounding/1.0.0` |

The context is immutable after validation. Narrative code cannot traverse unrestricted history, future events, raw model feature maps as domain truth, or caller-controlled factual overrides. A context mismatch is a hard failure with a safe code and no full payload echo.

## 3. Statement grammar

The provider or renderer may emit only these statement kinds in version 1.0.0:

| Kind | Permitted value | Required evidence | Claim wording boundary |
| --- | --- | --- | --- |
| `POLICY_ID` | Canonical policy ID | Issuance/snapshot identity | Identifies the case only |
| `CASE_ID` | Canonical case ID | Case context | Identifies the workflow case only |
| `CUTOFF_DATE` | Canonical UTC date | Cutoff context | “As of” date only |
| `TIMELINE_EVENT` | Typed event summary and timestamp | Event ID in provenance | Reports visible source event only |
| `PRODUCT_TYPE` | Snapshot product value | Issuance evidence | Reports product, no inferred coverage |
| `PAYMENT_FREQUENCY` | Snapshot frequency | Issuance evidence | Reports declared frequency only |
| `PREMIUM_AMOUNT` | Typed minor-unit amount and currency | Issuance/economics evidence | Reports amount; no profit claim |
| `COVERAGE_AMOUNT` | Typed amount when known | Explicit coverage evidence | Unknown stays unavailable |
| `TENURE_DURATION` | Snapshot-derived duration | Issuance plus cutoff | Reports elapsed duration, not loyalty or causality |
| `STATUS` | Snapshot status including `unknown` | Status field evidence | No inferred active/grace/terminal status |
| `DELINQUENCY` | Typed arrears/days-past-due | Payment evidence | Reports visible arrears only |
| `RISK_SCORE` | Frozen probability and tier | Matching score identity | “Model estimates” only; no realized outcome claim |
| `RISK_DRIVER` | Frozen driver ID/text/attribution | Matching score evidence | Attribution is model explanation, not cause |
| `ELIGIBLE_ACTION` | Action ID in eligibility result | Eligibility identity | Eligible/recommended only; no authorization |
| `RECOMMENDED_ACTION` | Selected action ID | Allocation/recommendation identity | Modeled recommendation only |
| `DISQUALIFIED_ACTION` | Action ID and reason | Eligibility evidence | Reports exclusion only |
| `SAFETY_FACT` | Tri-state safety fact | RH-02 evidence identity | Unknown is rendered as unknown |
| `DISCLAIMER` | Fixed contract text | Contract constant | Required advisory/human-review boundary |

No other statement kinds are accepted. In particular, version 1.0.0 prohibits free-form claims of authorization, consent, execution, causation, guaranteed savings, realized retention, truth, authenticity, external validity, production readiness, or customer intent.

## 4. Evidence resolution rules

1. Every statement carries `statement_id`, `kind`, canonical typed `value`, and ordered `evidence_ids`.
2. Each evidence ID must occur in the bound snapshot provenance or the explicitly referenced score, eligibility, safety, economics, or recommendation evidence object.
3. The evidence object must support the statement kind and the evidence cutoff must be no later than the narrative cutoff.
4. An evidence ID from another policy, snapshot, cutoff, model identity, or contract version fails with `CONTEXT_MISMATCH`.
5. A missing or unknown field cannot be replaced by a default, inferred value, provider text, or historical fixture value.
6. Derived values such as tenure must use the canonical RH-01 derivation and cite all required source identities; they are not source facts.
7. Score claims require exact score/model/bundle/preprocessing identity. Risk is a model estimate and must not be phrased as a realized outcome or causal effect.
8. Eligibility and recommendation claims require their own identity. They never imply approval, permission, consent, execution, or authority.
9. A grounding hash may bind canonical context plus accepted statement text, but its label must say `input_text_consistency`; it is not an authenticity or truth digest.

## 5. Rendering and provider boundary

The deterministic renderer is authoritative for factual fields, timeline entries, risk metadata, action labels, safety states, and disclaimers. It must format canonical values without allowing a provider to rewrite them.

An optional provider may propose only a candidate list of grammar statements or bounded slots. RH-08I validates and renders those statements after provider return. Raw provider prose cannot be inserted into a factual field, bypass validation, or mutate operational state. On invalid provider output, stale context, unsupported kind, unknown value, or failed evidence resolution, the implementation returns a deterministic safe fallback and an audit code.

The external provider remains disabled by default. Enabling it would require a later explicit configuration decision, provider-specific adversarial fixtures, deterministic redaction/fallback behavior, and documentation that test results cover only the declared grammar—not arbitrary prose.

## 6. Stable failure vocabulary

RH-08I should expose these safe, stable categories (exact module/API naming may follow existing conventions):

| Code | Meaning |
| --- | --- |
| `GROUNDING_CONTEXT_INVALID` | Required context identity or contract version is invalid |
| `GROUNDING_CONTEXT_MISMATCH` | Policy, cutoff, snapshot, score, or evidence identity differs |
| `GROUNDING_EVIDENCE_MISSING` | Required evidence reference is absent |
| `GROUNDING_EVIDENCE_UNRESOLVED` | Evidence ID is not present or does not support the kind |
| `GROUNDING_UNKNOWN_VALUE` | Statement asserts a fact represented as unknown/unavailable |
| `GROUNDING_STATEMENT_UNSUPPORTED` | Statement kind is outside the versioned grammar |
| `GROUNDING_VALUE_INVALID` | Value has wrong type, unit, range, or canonical representation |
| `GROUNDING_AUTHORITY_CLAIM` | Text asserts approval, consent, execution, or authority |
| `GROUNDING_CAUSAL_CLAIM` | Text asserts causality, guaranteed effect, or realized outcome |
| `GROUNDING_PROVIDER_OUTPUT_INVALID` | Provider output cannot be parsed or mapped to the grammar |
| `GROUNDING_FALLBACK_REQUIRED` | Candidate cannot be safely accepted and deterministic fallback is required |

Errors must not include complete histories, feature payloads, customer data, provider secrets, or complete candidate text when that text may contain sensitive content.

## 7. Validator coverage matrix

| Claim family | RH-08D required disposition | Evidence established | Not established |
| --- | --- | --- | --- |
| Policy/case IDs | Exact typed equality and evidence resolution | Text matches bound identity | Source authenticity |
| Dates/timestamps | Canonical UTC values and visible-event evidence | Input/text consistency | Completeness of source system |
| Amounts/currency | Exact typed amount/unit and evidence | Text matches supplied value | Financial truth or realized value |
| Durations | Canonical derivation from snapshot/cutoff | Derivation consistency | Customer intent or causality |
| Percentages/scores | Frozen score identity and bounded numeric value | Model-output consistency | Accuracy, calibration, or outcome truth |
| Status/safety | Typed value plus field evidence; unknown preserved | Evidence-linked representation | Legal sufficiency or authenticity |
| Actions | Catalog/eligibility identity and allowed wording | Recommendation/eligibility consistency | Authorization, consent, execution |
| Causal claims | Reject in 1.0.0 | None | Any causal conclusion |
| External provider prose | Reject unless every slot maps to grammar | Declared slot coverage only | Arbitrary prose safety |
| Grounding hash | Label only as input/text consistency | Canonical binding | Truth, authenticity, tamper resistance |

The implementation issue must not claim more coverage than this matrix. Adversarial tests demonstrate declared grammar coverage and regression resistance, not universal hallucination prevention.

## 8. RH-08I migration and compatibility

RH-08I may preserve the existing `CaseEvidenceContext`, `GroundingGuard`, and `GroundingAudit` as compatibility surfaces only when they are fed from a validated bound context. Existing lexical checks must be labeled legacy/partial coverage until replaced or explicitly bridged. Case briefs must render canonical snapshot facts and preserve null/unknown values rather than relying on current defaults such as fabricated coverage, paid premiums, or status assumptions.

The `CaseBrief` schema should receive an additive versioned grounding identity/statement-evidence representation if required by implementation. Existing historical brief artifacts remain immutable; any changed serialized output receives an explicit compatibility or migration note and a new version. No model bundle, preprocessing identity, historical evaluation, or holdout artifact may change.

## 9. Predeclared RH-08I verification

RH-08I must add failing tests before implementation for:

- fabricated policy/case IDs, amounts, dates, durations, percentages, action IDs, authorization/consent statements, causal statements, and status assertions;
- unknown snapshot facts and missing/foreign evidence IDs;
- policy, cutoff, snapshot, score, eligibility, safety, economics, and contract-version mismatches;
- provider output that attempts to inject arbitrary prose or mutate action/authority fields;
- deterministic output for identical bound context and statement input;
- safe fallback behavior and payload-safe error codes;
- grounding-hash labeling and the distinction between consistency and truth;
- heterogeneous policies and delayed/invisible events through RH-01 snapshot fixtures.

The implementation gate is focused assistant/dashboard/context coverage, full headless `make check`, repository-boundary checks, `git diff --check`, and byte-identical protected-artifact verification. No final holdout is accessed or materialized.

## 10. Decision

RH-08D accepts bounded structured grounding as the release contract. Deterministic rendering and provider-disabled operation are sufficient for RH-08 completion. RH-08 does not require a non-deterministic provider or a general-purpose validator capable of proving arbitrary prose true.

