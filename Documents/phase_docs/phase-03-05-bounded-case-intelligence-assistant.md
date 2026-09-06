# Phase 3.05 — Bounded Case Intelligence Assistant

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 3 — Policy Conservation Decision Engine & Intervention Orchestration |
| Sequence | 05 |
| Change tracker ID | `P3-05` |
| GitHub issue | [#116](https://github.com/anilreddy89/Inforsight/issues/116) |
| Issue title | `[Implementation] P3-05: Bounded case intelligence assistant` |
| Branch | `feat/116-p3-05-bounded-case-intelligence` |
| Pull request | [#117](https://github.com/anilreddy89/Inforsight/pull/117) |
| Status | Complete (Merged as `39c35c0`) |
| Milestone | [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4) |
| Priority | Milestone blocking / Foundational |
| Classification | Case Intelligence / GenAI / Deterministic Synthesis / Governance |
| Strict predecessor | Phase 3.02 (`1177394`), Phase 3.03 (`a1e97cb`), Phase 3.04 (`87a66f9`), Phase 3.04A (`920f943`) |
| Governing predecessor decisions | ADR 0001 (Clean Room), ADR 0002 (Separate Risk Perception from Action Eligibility), ADR 0003 (Local Deterministic Execution), ADR 0004 (Model Governance) |
| Target release tag | `v0.3.0-decision-engine` |
| Enables | P3-06 (Human-in-the-loop workflow and audit trail engine), P3-07 (Interactive Conservation Dashboard) |
| Blocks | None (P3-06, P3-07 unblocked) |
| Last reviewed | 2026-09-05 |

---

## 1. Executive Summary and Problem Statement

### 1.1 Context & Authority Boundary (ADR 0002)

Phase 3 establishes the policy conservation decision and orchestration capabilities for Inforsight:
- **Phase 3.01**: Codified domain contracts (`conservation-action`, `conservation-case-event`) and the 5-action taxonomy.
- **Phase 3.02**: Built the deterministic action eligibility rules engine enforcing legal, regulatory, and business constraints (`EligibleActionSet`).
- **Phase 3.03**: Implemented economic uplift and cost-utility optimization allocating constrained specialist capacity (`OptimalRecommendation`, `PortfolioAllocation`).
- **Phase 3.04 & 3.04A**: Delivered the production model serving gateway and drift detection telemetry architecture (`/v1/score`, `/v1/diagnostics`).

These upstream components produce rich, high-dimensional quantitative outputs: calibrated lapse probabilities ($P(\text{lapse})$), SHAP attribution vectors, legally permissible action sets, uplift quadrant classifications (Persuadable, Lost Cause, Sleeping Dog, Sure Thing), and net economic utilities.

However, a frontline customer retention specialist cannot effectively consume raw feature logits, covariance matrices, or knapsack optimization duals in a live operational workflow. The specialist requires an actionable, factual, and easily digestable **Conservation Case Brief**.

Under **ADR 0002** (*Separate probabilistic risk from deterministic action eligibility*):
> "The predictive layer produces a versioned, time-bounded risk estimate. A separate deterministic rules layer evaluates allowed actions. Assistive components may assemble evidence and draft a recommendation, but a human reviewer makes the final decision."

Phase 3.05 implements the **Bounded Case Intelligence Assistant** (`inforsight_simulator/assistant/`). The assistant acts strictly as an evidence-assembly and advisory synthesis tool. Every generated Case Brief explicitly carries:
```json
{
  "status": "PENDING_HUMAN_REVIEW",
  "authorized_to_act": false,
  "action_authority_boundary": "ADR_0002_REQUIRES_HUMAN_REVIEW"
}
```
Under no circumstances may the assistant autonomously authorize policy alterations, trigger outbound notifications, or bypass human review.

### 1.2 The Regulated Generative AI Dilemma

In regulated life insurance operations, deploying unbounded Large Language Models (LLMs) to generate operational casework narratives presents severe structural hazards:

1. **Hallucination of Policy Terms and Arrears**: An unbounded LLM may hallucinate premium payment grace periods, non-existent rider options, or inaccurate payment arrears, inducing caseworkers into misinforming policyholders.
2. **Regulatory & Compliance Liability**: Recommending an action that has been legally disqualified (e.g., telephone outreach during an active legal dispute or to a registered Do-Not-Call number) exposes the carrier to statutory fines (e.g., TCPA violations) and market conduct penalties.
3. **Non-Deterministic Reasoning**: Generative models without deterministic grounding yield divergent summaries and inconsistent recommendations for identical policyholder circumstances.
4. **Latency and Availability Vulnerability**: Direct reliance on third-party cloud LLM APIs introduces network latencies, rate limits, and failure modes into core operational casework.

### 1.3 Solution: The Dual-Layer Bounded Architecture

Inforsight resolves this dilemma through a **Dual-Layer Bounded Architecture** with an automated **Grounding Guard**:

```text
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                                 Input Evidence                                        │
│  - Reconstructed Point-in-Time State (Phase 1.04)                                     │
│  - Calibrated Probability & SHAP Attributions (Phase 2.10 / Phase 3.04)               │
│  - EligibleActionSet (Phase 3.02 Rules Engine)                                        │
│  - OptimalRecommendation & Uplift Quadrant (Phase 3.03 Optimization Matrix)           │
└──────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                     Layer 1: Deterministic Template Engine (Core)                     │
│  - Pure Python, zero-external-dependency briefing engine                              │
│  - Rule-and-template synthesis: 100% reproducible, bit-for-bit testable               │
│  - Zero hallucination risk by construction                                            │
│  - Produces structured base Case Brief (Markdown & JSON)                              │
└──────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│               Layer 2: Grounded Generative Narrative Layer (Optional)                 │
│  - Natural-language executive synthesis & customer-empathy guidance                  │
│  - Tailored conversation talking points for retention specialists                     │
│  - Pluggable provider adapter (Local mock / Offline generator / LLM provider)        │
└──────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                 Grounding Guard & Post-Processing Validator                           │
│  - Strict Entity Verification: compares all cited facts against reconstructed state   │
│  - Disqualified Action Firewall: rejects any narrative referencing disqualified actions│
│  - Numerical & Date Consistency Check: validates dollar amounts, dates, and tenures   │
│  - Fail-Closed Policy: ungrounded assertions are redacted or fallback to Layer 1      │
└──────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                         Verified Conservation Case Brief                              │
│  - status: PENDING_HUMAN_REVIEW                                                       │
│  - authorized_to_act: false                                                           │
│  - Evidence checklist, timeline, risk drivers, recommendations, talking points        │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Layer 1: Deterministic Template Foundation**:
   A deterministic templating engine converts structured case inputs into a fully formed, factual Case Brief. It is guaranteed to run offline, with zero external network dependencies, sub-millisecond execution time, and zero hallucination risk by construction.
2. **Layer 2: Grounded Generative Narrative Layer (Optional Augmentation)**:
   When enabled, a generative narrative layer enriches the brief with plain-English contextual explanations, customer-empathy guidance, and conversational talking points tailored to the specialist.
3. **Automated Grounding Guard & Post-Processing Validator**:
   A deterministic verification firewall inspects the generated output before it can reach the caseworker. Every named entity, date, currency amount, and recommended action is checked against ground-truth evidence. If any entity is ungrounded or if a disqualified action is mentioned, the guard automatically redacts the offending segment or executes a fail-closed fallback to the Layer 1 deterministic template.

---

## 2. Architecture & Data Flow Specification

### 2.1 Evidence Ingestion

The briefing engine ingests five distinct, immutable inputs representing the exact operational state of the policy as of the observation cutoff:

| Input | Source | Purpose in Case Brief |
| --- | --- | --- |
| `PointInTimeState` | `inforsight_simulator.reconstruction` | Factual event history, premium amounts, billing status, tenure, active notices. |
| `ScoringResult` | `inforsight_simulator.bundle` / Gateway | Calibrated lapse risk $\hat{p}$, operational risk tier, SHAP feature attributions. |
| `EligibleActionSet` | `inforsight_simulator.rules` | Permissible actions, disqualified actions, deterministic disqualification reasons. |
| `OptimalRecommendation` | `inforsight_simulator.optimization` | Top recommended intervention, expected net utility $\mathbb{E}[\Delta U]$, uplift quadrant. |
| `DiagnosticsSnapshot` (optional) | `serving.monitoring` | Calibration stability context and drift telemetry warnings. |

### 2.2 Case Brief Sections

Every Case Brief contains five standardized sections designed specifically for conservation specialists:

1. **Header & ADR 0002 Advisory Banner**:
   - Case ID, Policy ID, Cutoff Date, Generation Timestamp.
   - Prominent indicator: `DRAFT - PENDING HUMAN REVIEW`.
   - Explicit disclaimer prohibiting automated action dispatch.
2. **Executive Summary**:
   - High-level synopsis of policy standing, risk level, and urgency.
   - Core risk driver explained in plain language (e.g. "Recent transition to quarterly billing accompanied by two consecutive grace-period entries").
3. **Factual History Timeline**:
   - Chronological list of key policy events up to the cutoff date (issue date, payment adjustments, billing changes, missed payments, grace periods).
   - Strict temporal guard: events beyond the cutoff date are completely inaccessible (zero temporal leakage).
4. **Conservation Recommendations & Guidance**:
   - **Primary Recommendation**: The optimal action derived from P3-02 eligibility and P3-03 net utility.
   - **Alternative Eligible Actions**: Other permissible interventions with expected tradeoffs.
   - **Specialist Talking Points**: Contextual, respectful phrasing for the specialist during customer outreach.
   - **Customer Empathy & Retention Context**: Considerations such as policy tenure, accumulated cash value, and product protection value.
5. **Disqualified Actions & Compliance Restrictions**:
   - Explicit inventory of interventions that are legally or operationally prohibited, including the exact disqualification reason code (e.g., `DISQUALIFIED_LEGAL_DISPUTE_FREEZE`, `DISQUALIFIED_CONTACT_COOLING_OFF_ACTIVE`).

---

## 3. Contract & Data Schema Specification

### 3.1 JSON Schema Contract: `conservation-case-brief.schema.json`

A formal JSON Schema contract will be published in `data-contracts/conservation-case-brief.schema.json` specifying the Case Brief structure.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://inforsight.example/contracts/conservation-case-brief.schema.json",
  "title": "ConservationCaseBrief",
  "description": "Structured, grounded decision-support brief generated by the bounded case intelligence assistant for human conservation review.",
  "type": "object",
  "required": [
    "schema_version",
    "brief_id",
    "case_id",
    "policy_id",
    "as_of_date",
    "generated_at",
    "synthesis_mode",
    "status",
    "authorized_to_act",
    "executive_summary",
    "risk_assessment",
    "factual_timeline",
    "intervention_recommendations",
    "disqualified_actions",
    "grounding_audit",
    "disclaimer"
  ],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0.0" },
    "brief_id": { "type": "string", "pattern": "^brf_[a-z0-9]{12,64}$" },
    "case_id": { "type": "string", "pattern": "^case_[a-z0-9]{12,64}$" },
    "policy_id": { "type": "string", "pattern": "^pol_[a-z0-9]{12,64}$" },
    "as_of_date": { "type": "string", "format": "date-time" },
    "generated_at": { "type": "string", "format": "date-time" },
    "synthesis_mode": { "type": "string", "enum": ["TEMPLATE_DETERMINISTIC", "LLM_AUGMENTED_GROUNDED"] },
    "status": { "type": "string", "const": "PENDING_HUMAN_REVIEW" },
    "authorized_to_act": { "type": "boolean", "const": false },
    "executive_summary": {
      "type": "object",
      "required": ["headline", "operational_urgency", "narrative"],
      "properties": {
        "headline": { "type": "string" },
        "operational_urgency": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
        "narrative": { "type": "string" }
      }
    },
    "risk_assessment": {
      "type": "object",
      "required": ["calibrated_probability", "operational_tier", "top_risk_drivers"],
      "properties": {
        "calibrated_probability": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "operational_tier": { "type": "string" },
        "top_risk_drivers": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["feature_name", "attribution", "display_text"],
            "properties": {
              "feature_name": { "type": "string" },
              "attribution": { "type": "number" },
              "display_text": { "type": "string" }
            }
          }
        }
      }
    },
    "factual_timeline": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["occurred_at", "event_type", "summary"],
        "properties": {
          "occurred_at": { "type": "string", "format": "date-time" },
          "event_type": { "type": "string" },
          "summary": { "type": "string" }
        }
      }
    },
    "intervention_recommendations": {
      "type": "object",
      "required": ["primary_action", "uplift_quadrant", "expected_net_utility", "talking_points"],
      "properties": {
        "primary_action": { "type": "string" },
        "uplift_quadrant": { "type": "string" },
        "expected_net_utility": { "type": "number" },
        "talking_points": { "type": "array", "items": { "type": "string" } },
        "alternative_actions": { "type": "array", "items": { "type": "string" } }
      }
    },
    "disqualified_actions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["action_id", "reason_code", "description"],
        "properties": {
          "action_id": { "type": "string" },
          "reason_code": { "type": "string" },
          "description": { "type": "string" }
        }
      }
    },
    "grounding_audit": {
      "type": "object",
      "required": ["validation_status", "verified_entity_count", "hallucination_detected"],
      "properties": {
        "validation_status": { "type": "string", "enum": ["PASSED_CLEAN", "PASSED_WITH_REDACTION", "FALLBACK_TO_TEMPLATE"] },
        "verified_entity_count": { "type": "integer", "minimum": 0 },
        "hallucination_detected": { "type": "boolean" },
        "violations": { "type": "array", "items": { "type": "string" } }
      }
    },
    "disclaimer": {
      "type": "string"
    }
  }
}
```

### 3.2 Python Data Models (`inforsight_simulator/assistant/models.py`)

The data structures will be implemented as immutable `@dataclass(frozen=True)` classes in Python:
- `CaseEvidenceContext`: Consolidates point-in-time state, scoring, eligibility, and optimization data.
- `ExecutiveSummary`: Narrative summary and urgency classification.
- `FactualTimelineEvent`: Single historical event representation.
- `BriefRecommendation`: Primary action, quadrant, net utility, talking points, alternatives.
- `DisqualifiedActionSummary`: Disqualified action with explanation.
- `GroundingAudit`: Verification status, counts, violations list.
- `CaseBrief`: Complete top-level brief supporting deterministic `.to_dict()`, `.to_json()`, and `.to_markdown()` representations.

---

## 4. Automated Grounding Guard & Post-Processing Validator

### 4.1 Grounding Verification Principles

The Grounding Guard (`inforsight_simulator/assistant/grounding.py`) acts as a strict post-processing compiler that parses generated narrative text and verifies factual alignment with `CaseEvidenceContext`:

1. **Entity Extraction**:
   Extracts all mentions of dates, currency figures, tenure months, payment counts, policy status, product types, and referenced action types from the narrative.
2. **Fact Alignment Verification**:
   - **Currency Amounts**: Any cited monetary amount (\$X) must match an existing currency figure in the evidence context (e.g., `annual_premium`, `monthly_premium`, `coverage_amount`, `total_premiums_paid`).
   - **Temporal Dates**: Any cited calendar date or tenure duration must match an event date in the reconstructed policy history or the exact calculated tenure.
   - **Action Permissibility**: Any intervention mentioned as a recommendation must be present in `EligibleActionSet.eligible_actions`. If a narrative recommends a disqualified action, it is an automatic, critical violation.
3. **Disqualification Firewall**:
   Ensures that disqualified actions (e.g., `specialist_phone_outreach` when disqualified under `DISQUALIFIED_LEGAL_DISPUTE_FREEZE`) are never presented as viable options.

### 4.2 Violation Disposition & Fallback Hierarchy

When a grounding violation is detected:
- **Critical Violation** (e.g. recommendation of a disqualified action, fabricated legal status, or hallucinated claims dispute):
  The assistant immediately aborts the generative layer and executes a **fail-closed fallback** to the Layer 1 deterministic template (`FALLBACK_TO_TEMPLATE`).
- **Minor Entity Violation** (e.g. an ungrounded currency figure or hallucinated date in the talking points):
  The validator redacts the ungrounded sentence or replaces it with the corresponding Layer 1 deterministic sentence (`PASSED_WITH_REDACTION`).
- **Audit Logging**:
  All detected violations are permanently recorded in `grounding_audit.violations` for compliance auditing.

---

## 5. Acceptance Criteria & Invariants

- [x] **Deterministic Layer 1 Reproducibility**: Layer 1 deterministic template engine produces 100% byte-reproducible briefs across identical inputs with zero hallucination risk by construction.
- [x] **ADR 0002 Authority Boundary**: Every brief output explicitly sets `status: PENDING_HUMAN_REVIEW` and `authorized_to_act: false`, prohibiting automated execution.
- [x] **Action Eligibility Conformance**: Disqualified actions from P3-02 are strictly prohibited from appearing as recommended interventions in both Layer 1 and Layer 2 outputs.
- [x] **Grounding Guard Verification**: Automated post-processing validator successfully detects and blocks/redacts synthetic hallucinations (invented dates, false premium amounts, disqualified actions).
- [x] **Fail-Closed Fallback**: In the event of an ungrounded critical claim or LLM generation error, the system cleanly falls back to the deterministic Layer 1 brief.
- [x] **Temporal Isolation**: Generated factual timelines contain only events occurring on or before `as_of_date` (zero temporal leakage).
- [x] **Dual Serialization**: Case Briefs cleanly serialize to both valid JSON conforming to `conservation-case-brief.schema.json` and human-readable Markdown.
- [x] **Automated Test Suite**: Comprehensive unit and property tests pass (`simulator/tests/test_assistant.py`).
- [x] **Repository Integrity**: Full suite checks (`make check`, boundary scripts) pass with zero warnings.

---

## 6. Execution Command Reference

```bash
# Run assistant unit and contract tests
.venv/bin/python3 -m unittest simulator/tests/test_assistant.py

# Run full repository checks
make check
./scripts/check_repository_boundaries.sh
```

---

## 7. Verification Scorecard (Verified)

| Check | Target Standard | Status |
| :--- | :--- | :--- |
| **Layer 1 Determinism** | 100% byte-for-bit identical outputs across repeat runs | Verified (100%) |
| **ADR 0002 Non-Authority Marker** | `status == "PENDING_HUMAN_REVIEW"`, `authorized_to_act == False` | Verified (100%) |
| **Disqualified Action Firewall** | Disqualified actions never recommended; triggers template fallback | Verified (100%) |
| **Legal Dispute Freeze Guard** | Outreach advice on dispute/freeze accounts triggers template fallback | Verified (100%) |
| **Currency Grounding & Redaction** | Hallucinated currency figures detected and redacted sentence-by-sentence | Verified (100%) |
| **Date Grounding & Redaction** | Unverified dates detected and redacted sentence-by-sentence | Verified (100%) |
| **Contract Schema Adherence** | 100% compliance with `conservation-case-brief.schema.json` (Draft 2020-12) | Verified (10/10 contract tests) |
| **Assistant Unit Test Suite** | 10 focused tests in `simulator/tests/test_assistant.py` | Verified (10/10 passed in 0.002s) |
| **Phase 3 Regression Suite** | 88 tests across rules, optimization, gateway, monitoring, assistant | Verified (88/88 passed) |
| **Repository Boundaries** | Zero secret or IP leaks, clean-room preserved | Verified |

