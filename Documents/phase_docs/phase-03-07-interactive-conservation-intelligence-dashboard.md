# Phase 3.07 — Interactive Conservation Intelligence Dashboard

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 3 — Policy Conservation Decision Engine & Intervention Orchestration |
| Sequence | 07 |
| Change tracker ID | `P3-07` |
| GitHub issue | [#120](https://github.com/anilreddy89/Inforsight/issues/120) (Target) |
| Issue title | `[Implementation] P3-07: Interactive conservation intelligence dashboard` |
| Branch | `feat/120-p3-07-conservation-dashboard` |
| Pull request | [#121](https://github.com/anilreddy89/Inforsight/pull/121) (Target) |
| Status | Planned / Ready for Implementation |
| Milestone | [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4) |
| Priority | Milestone blocking / User-Facing Operational Interface |
| Classification | Interactive UI / Decision Support / Operational Dashboard / Streamlit |
| Strict predecessor | Phase 3.01 (`7ed7efd`), Phase 3.02 (`1177394`), Phase 3.03 (`a1e97cb`), Phase 3.04 (`87a66f9`), Phase 3.04A (`920f943`), Phase 3.05 (`39c35c0`), Phase 3.06 (`ec8b50a`) |
| Governing predecessor decisions | ADR 0001 (Clean Room), ADR 0002 (Separate Risk Perception from Action Eligibility), ADR 0003 (Local Deterministic Execution), ADR 0004 (Model Governance) |
| Target release tag | `v0.3.0-decision-engine` |
| Enables | P3-09 (End-to-End System Qualification & Integration Gate) |
| Blocks | P3-09 |
| Last reviewed | 2026-09-05 |

---

## 1. Executive Summary and Problem Statement

### 1.1 Context & Regulatory Imperative (ADR 0002)

Phase 3 builds the comprehensive policy conservation decision intelligence platform for Inforsight:
- **Phase 3.01**: Established formal domain contracts (`conservation-action.schema.json`, `conservation-case-event.schema.json`) and the 5-action taxonomy (phone outreach, payment arrangement, self-service link, agent follow-up, abstain).
- **Phase 3.02**: Built the pure deterministic action eligibility rules engine enforcing legal, regulatory, and business constraints (`EligibleActionSet`).
- **Phase 3.03**: Implemented economic uplift and cost-utility optimization allocating constrained specialist capacity (`OptimalRecommendation`, `PortfolioAllocation`).
- **Phase 3.04 & 3.04A**: Delivered the production model serving gateway (`/v1/score`) and real-time drift telemetry (`/v1/diagnostics`, PSI/CSI, rolling ECE/BSS).
- **Phase 3.05**: Engineered the dual-layer bounded case intelligence assistant (`CaseBrief`, deterministic templates, and grounding guard firewalls).
- **Phase 3.06**: Implemented the human-in-the-loop workflow state machine and cryptographically chained append-only audit ledger (`conservation-audit-log.jsonl`, `scripts/verify_conservation_audit_trail.py`).

While these backend systems provide calibrated risk perceptions, legal eligibility boundaries, mathematical resource allocations, grounded case summaries, and tamper-evident audit logging, **they have operated entirely as headless programmatic libraries, REST endpoints, and CLI utilities**.

In an actual life insurance carrier environment, conservation specialists, team leads, compliance officers, and operations executives cannot interact directly with Python classes or terminal commands. More critically, under **ADR 0002** (*Separate probabilistic risk from deterministic action eligibility*):
> "The predictive layer produces a versioned, time-bounded risk estimate. A separate deterministic rules layer evaluates allowed actions. Assistive components may assemble evidence and draft a recommendation, but a human reviewer makes the final decision."

Human review is not a cosmetic layer; it is the non-delegable statutory and fiduciary boundary separating algorithmic guidance from real-world policy intervention. To operationalize this principle, the platform requires an **interactive operational cockpit** that synthesizes all Phase 3 subsystems into a responsive, secure, and intuitive web interface.

### 1.2 Purpose of Phase 3.07

Phase 3.07 implements the **Interactive Conservation Intelligence Dashboard** (`dashboard/`), a lightweight, standalone Streamlit web application providing:
1. **Executive Portfolio & Operational View**: Macroscopic portfolio health, risk distribution across operational tiers (Top 1%, 5%, 20%), queue capacity meters, model drift health, and projected retention ROI.
2. **Prioritized Triage Queue Console**: Interactive, filterable queue table prioritizing in-force policies at risk based on calibrated lapse probabilities, net expected utilities, grace period urgency, and specialist capacity constraints.
3. **Deep-Dive Policy Investigation Dossier**: Granular case inspection for individual policies, featuring point-in-time event reconstruction, interactive SHAP waterfall attributions explaining risk drivers, and Grounding Guard-verified AI Case Briefs.
4. **Specialist Human-in-the-Loop Decision Console**: Operational decision workspace where conservation specialists review recommendations, approve or override interventions with mandatory structured rationales, and instantly append immutable, cryptographically chained audit records to `conservation-audit-log.jsonl`.

---

## 2. Architecture & System Boundary

### 2.1 Component Interaction Topology

The dashboard operates as a unified presentation and interaction layer directly wired to the verified Phase 1, Phase 2, and Phase 3 core libraries:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        Phase 3.07 Streamlit Interactive Dashboard                       │
│                                       (dashboard/)                                      │
├───────────────────────────┬─────────────────────────────┬───────────────────────────────┤
│    Executive Portfolio    │     Triage Queue Console    │     Case Investigation &      │
│     & Capacity View       │     (Prioritized Table)     │   Specialist Decision Console │
└─────────────┬─────────────┴──────────────┬──────────────┴───────────────┬───────────────┘
              │                            │                              │
              ▼                            ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      Dashboard Engine Bridge (dashboard/services/)                       │
└───────┬───────────────────┬──────────────────────┬──────────────────────┬───────────────┘
        │                   │                      │                      │
        ▼                   ▼                      ▼                      ▼
┌───────────────┐   ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│ Point-in-Time │   │ Bundled Model │      │ Deterministic │      │  Cost-Utility │
│ State Engine  │   │  Inference &  │      │  Eligibility  │      │  Optimization │
│  (Phase 1.04) │   │ SHAP Explain  │      │ Rules Engine  │      │ & Uplift Alloc│
│               │   │ (Phase 2.10)  │      │ (Phase 3.02)  │      │ (Phase 3.03)  │
└───────┬───────┘   └───────┬───────┘      └───────┬───────┘      └───────┬───────┘
        │                   │                      │                      │
        └───────────────────┼──────────────────────┴──────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      Case Intelligence Briefing Engine (Phase 3.05)                     │
│               (Layer 1 Templates + Layer 2 Grounded Brief + Grounding Guard)            │
└──────────────────────────────────────────┬──────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│               HITL Workflow State Machine & Cryptographic Ledger (Phase 3.06)            │
│         (Enforces ADR 0002 Authority Gate & Appends to conservation-audit-log.jsonl)    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Strict Architectural Invariants

1. **ADR 0001 (Clean Room & Public Integrity)**: The dashboard runs entirely against synthetic policy data generated by the Generation v6 simulator. Zero proprietary, client-identifying, or real policyholder information is loaded or processed.
2. **ADR 0002 (Non-Autonomous Action Boundary)**: The dashboard UI does not allow automated dispatch. Interventions can only transition from `RECOMMENDED` to `EXECUTED` when an authenticated specialist interacts with the Decision Console, validates credentials (`usr_[a-z0-9_]{3,32}`), and submits an approved decision.
3. **ADR 0003 (Local Deterministic Execution)**: The entire application executes locally via `streamlit run dashboard/app.py` without requiring external cloud databases, external microservice orchestration, or internet connectivity.
4. **Eligibility Firewall on Overrides**: When a specialist chooses to override the recommended intervention, the UI dynamically disables/restricts choice exclusively to the actions validated as legally and operationally permissible in `EligibleActionSet`. Disqualified actions cannot be selected.
5. **Cryptographic Provenance**: Every human decision executed in the dashboard is immediately written to the append-only audit ledger (`conservation-audit-log.jsonl`), updating the recursive SHA-256 hash chain and recording the point-in-time decision context digest.

---

## 3. Detailed UI Modules & Functional Specifications

### 3.1 View 1: Executive Portfolio Overview & Operational Capacity

The Executive Portfolio view provides operational leadership and retention managers with real-time visibility into portfolio vulnerability and resource constraints:

- **Executive KPI Metric Cards**:
  - **In-Force Portfolio Count**: Total active policies in the monitored cohort (e.g., 3,600 / 8,782).
  - **Grace Period Policies**: Active policies currently in statutory grace period ($0 < \text{days\_in\_grace} \le 30$).
  - **Critical Vulnerability (Tier 1)**: Policies in the Top 1% calibrated risk cohort ($\hat{p} \ge \tau_{\text{tier1}}$).
  - **Projected Value at Risk**: Sum of annualized premiums for policies in Tier 1 and Tier 2.
  - **Specialist Capacity Utilization**: Gauge showing allocated specialist hours vs. max capacity constraint (e.g., 42.5 / 50.0 hours, 85% utilized).
- **Risk Tier Distribution**:
  - Visual breakdown of the portfolio across operational tiers:
    - **Tier 1 (Top 1% - Critical)**: Immediate high-touch outreach.
    - **Tier 2 (Top 5% - Elevated)**: Proactive structured outreach.
    - **Tier 3 (Top 20% - Moderate)**: Digital / self-service nudges.
    - **Tier 4 (Bottom 80% - Normal)**: Standard administrative servicing.
- **Intervention Mix Allocation**:
  - Donut/bar chart displaying the distribution of optimized actions across the portfolio (`SPECIALIST_PHONE_OUTREACH`, `PAYMENT_RESTRUCTURING_PLAN`, `SELF_SERVICE_PORTAL_LINK`, `AGENT_CONSERVATION_ALERT`, `ABSTAIN`).
- **Telemetry & Drift Health Panel**:
  - Summary status indicator fed from Phase 3.04A monitoring (`HEALTHY`, `WARNING`, `CRITICAL`) based on Population Stability Index (PSI) and rolling calibration decay (ECE/BSS).

### 3.2 View 2: Prioritized Triage Queue Console

The Triage Queue provides conservation team supervisors and specialists with an actionable, prioritized backlog:

- **Multi-Factor Filtering & Search**:
  - Filter by **Operational Risk Tier**: Tier 1 (Top 1%), Tier 2 (Top 5%), Tier 3 (Top 20%), All.
  - Filter by **Workflow Status**: `CREATED`, `TRIAGED`, `RECOMMENDED`, `HUMAN_REVIEWED`, `EXECUTED`, `DISMISSED`.
  - Filter by **Grace Period Days**: All, Urgent ($\le 7$ days remaining), Imminent ($\le 15$ days), Standard ($\le 30$ days).
  - Filter by **Payment Channel**: Direct Debit, Credit Card, Direct Mail / Check.
  - Text search by Policy ID.
- **Interactive Triage Table**:
  - Columns:
    1. `Priority Rank`: Global rank based on Net Expected Utility.
    2. `Policy ID`: Fictional identifier with direct link to open Dossier.
    3. `Lapse Probability`: Calibrated $\hat{p}$ with color-coded risk badge.
    4. `Risk Tier`: Visual pill indicator (Tier 1: Red, Tier 2: Orange, Tier 3: Yellow, Tier 4: Gray).
    5. `Primary Risk Driver`: Dominant contributing feature from SHAP decomposition (e.g., `rolling_on_time_rate`, `premium_burden_ratio`).
    6. `Grace Days`: Days elapsed in grace period with countdown warning.
    7. `Recommended Action`: Optimal action determined by optimization matrix.
    8. `Net Utility`: Expected net dollar savings after intervention cost.
    9. `Case Status`: Current HITL state machine position.
- **Row Selection**: Clicking any policy row immediately activates View 3 and loads the full Policy Investigation Dossier.

### 3.3 View 3: Policy Case Investigation Dossier

The Dossier view provides the reviewing specialist with 360-degree point-in-time context before making a decision:

- **Policy Summary Header**:
  - Policy ID, Product Type (Term Life, Whole Life, Universal Life), Policy Age, Monthly Premium, Face Amount, Payment Frequency, Billing Channel.
  - Current Status (e.g., `IN_GRACE`, `ACTIVE`).
- **Risk Perception & Explainability (Phase 2.09 / 2.10)**:
  - Calibrated lapse probability $\hat{p}$ displayed alongside operational threshold percentiles.
  - **Interactive SHAP Waterfall Chart**: Matplotlib/Altair rendering of the exact additive log-odds decomposition showing which historical behaviors pushed risk upward (red) or downward (green).
  - **Attribution Feature Table**: Detailed table listing baseline value, policyholder value, and directional delta for top 5 risk drivers.
- **Point-in-Time Event Timeline (Phase 1.04)**:
  - Interactive vertical timeline showing chronological events up to the observation cutoff timestamp:
    - Inception $\to$ Consecutive Successful Payments $\to$ Billing Failure $\to$ Grace Period Notice $\to$ Failed Re-bill.
    - Proves point-in-time data hygiene: strict visual assurance that zero future events appear post-cutoff.
- **Grounded Case Intelligence Brief (Phase 3.05)**:
  - Rendered `CaseBrief` card displaying:
    - **Executive Summary**: High-level policy narrative.
    - **Observed Risk Signals**: Bulleted factual observations.
    - **Mitigation Opportunities**: Concrete paths to retention.
    - **Specialist Talking Points**: Empathetic, compliance-approved bullet points for customer conversation.
  - **Grounding Guard Verification Seal**: Visual badge confirming `grounding_verified: true`, `citation_count`, and explicit ADR 0002 advisory disclaimer (*"ADVISORY ONLY — Specialist judgment required"*).

### 3.4 View 4: Specialist Decision & Action Console (HITL Engine)

The Decision Console is the operational execution terminal where human authority is applied:

- **Current Case State**: Visual badge showing state (typically `RECOMMENDED`).
- **Algorithm Recommendation Summary**:
  - Action: `OptimalRecommendation.recommended_action`.
  - Expected Net Utility ($\$$).
  - Estimated Specialist Duration (minutes).
  - Permissible Alternative Actions (`EligibleActionSet.eligible_actions`).
  - Disqualified Actions & Disqualification Reasons (e.g., Phone Outreach disqualified due to missing phone consent).
- **Specialist Action Form**:
  - **Reviewer Credentials**: Text input for Specialist ID (`usr_[a-z0-9_]{3,32}`), defaulting to current session user.
  - **Decision Radio Selection**:
    1. `APPROVE_RECOMMENDATION`: Accept the algorithm's optimal intervention.
    2. `OVERRIDE_ACTION`: Select a different intervention.
    3. `REQUEST_MORE_INFO`: Place case on hold for document or billing inquiry.
    4. `REJECT_AND_CLOSE`: Decline all proactive interventions.
  - **Dynamic Conditional Inputs**:
    - When `OVERRIDE_ACTION` is selected:
      - **Override Action Dropdown**: Strictly populated with `EligibleActionSet.eligible_actions`. Any attempt to select a disqualified action is prevented at UI level.
      - **Mandatory Rationale Code**: Dropdown with predefined standard codes (`OVERRIDE_SPECIALIST_DISCRETION_PREMIUM_DISPUTE`, `OVERRIDE_PREFERRED_CHANNEL_EMAIL`, etc.).
      - **Mandatory Justification Text**: Multi-line text area validating minimum length ($\ge 5$ characters).
    - When `REJECT_AND_CLOSE` is selected:
      - **Mandatory Rationale Code**: Dropdown with predefined rejection codes (`REJECT_CUSTOMER_REQUESTED_NO_CONTACT`, `REJECT_POLICY_REPLACED_EXTERNALLY`, etc.).
      - **Mandatory Justification Text**: Multi-line text area ($\ge 5$ characters).
- **Commit Button**:
  - "Commit Decision to Cryptographic Audit Ledger".
  - On click, invokes `inforsight_simulator.workflow.engine` to transition case state:
    - $\text{RECOMMENDED} \to \text{HUMAN\_REVIEWED} \to \text{EXECUTED}$ (or $\text{DISMISSED}$).
  - Appends record to `data/audit/conservation-audit-log.jsonl`.
  - Displays instant cryptographic receipt:
    - Sequence Number
    - Entry SHA-256 Hash
    - Previous SHA-256 Hash
    - Timestamp
    - Status: Validated & Chained

---

## 4. Software Architecture & File Organization

The dashboard implementation is structured under the `dashboard/` root directory:

```text
dashboard/
├── __init__.py
├── app.py                         # Main Streamlit application entry point
├── config.py                      # Global settings, styling tokens, data paths
├── components/                    # Modular UI view components
│   ├── __init__.py
│   ├── portfolio_view.py          # View 1: Executive metrics & capacity
│   ├── queue_view.py              # View 2: Prioritized triage data table
│   ├── dossier_view.py            # View 3: Deep-dive dossier, SHAP, timeline, brief
│   ├── decision_console.py        # View 4: Specialist HITL action & audit submission
│   └── telemetry_view.py          # Model health & drift sub-panel
├── services/                      # Backend bridges & state wrappers
│   ├── __init__.py
│   ├── engine_bridge.py           # Unified bridge connecting models, rules, brief, workflow, audit
│   ├── cohort_loader.py           # Loads synthetic evaluation cohort & precomputes queue
│   └── chart_utils.py             # Altair / Plotly / Matplotlib helpers for SHAP & distributions
└── tests/                         # Automated test suite
    ├── __init__.py
    ├── test_dashboard_services.py # Unit tests for engine bridge, queue sorting, filters
    └── test_dashboard_smoke.py    # Headless Streamlit smoke tests
```

---

## 5. Acceptance Criteria & Invariants

- [ ] **Standalone Local Execution**: The dashboard launches cleanly via `.venv/bin/streamlit run dashboard/app.py` without requiring external cloud databases, credentials, or remote services.
- [ ] **Multi-Tier Dynamic Triage**: Selecting between Tier 1 (Top 1%), Tier 2 (Top 5%), Tier 3 (Top 20%), and All dynamically updates queue tables, capacity meters, and summary figures.
- [ ] **SHAP & Timeline Visualization**: The Policy Dossier correctly renders the interactive SHAP waterfall decomposition matching Phase 2.09 attributions and displays the chronological event history.
- [ ] **AI Case Brief Integration**: The Policy Dossier renders Grounding Guard-verified briefs with advisory disclaimers and talking points.
- [ ] **ADR 0002 Enforcement in UI**: The Decision Console strictly prevents autonomous execution. The Commit action requires valid specialist credentials and records human review.
- [ ] **Override Eligibility Firewall**: Overriding a recommendation restricts choices strictly to `EligibleActionSet.eligible_actions`. Disqualified actions cannot be selected. Structured rationale and text justification ($\ge 5$ characters) are enforced.
- [ ] **Live Cryptographic Audit Append**: Submitting a specialist decision appends an entry to `conservation-audit-log.jsonl` that passes `scripts/verify_conservation_audit_trail.py` verification.
- [ ] **Automated Smoke & Service Tests**: Test suite in `dashboard/tests/` passes 100% of assertions.
- [ ] **Clean-Room & Boundary Compliance**: Repository boundaries (`./scripts/check_repository_boundaries.sh`) pass cleanly with zero warnings.

---

## 6. Execution Command Reference

```bash
# Launch interactive Streamlit dashboard
.venv/bin/streamlit run dashboard/app.py

# Run dashboard service and smoke tests
.venv/bin/python3 -m unittest discover -s dashboard/tests -p 'test_*.py' -v

# Verify audit trail integrity after UI interactions
.venv/bin/python3 scripts/verify_conservation_audit_trail.py --log data/audit/conservation-audit-log.jsonl

# Run full project boundary and regression checks
./scripts/check_repository_boundaries.sh
make check
```

---

## 7. Verification Scorecard (Planned)

| Check | Target Standard | Status |
| :--- | :--- | :--- |
| **Local Zero-Cloud Launch** | `streamlit run dashboard/app.py` boots in $< 3$s locally | Planned |
| **Executive Portfolio Metrics** | Correctly aggregates portfolio risk tiers and capacity constraints | Planned |
| **Triage Queue Responsiveness** | Real-time filtering by tier, grace period, and status | Planned |
| **SHAP Attribution Fidelity** | Waterfall attributions match release model bundle logit decomposition | Planned |
| **Point-in-Time Event Timeline** | Strict chronological reconstruction with zero post-cutoff leakage | Planned |
| **Case Intelligence Grounding** | Layer 1/2 brief with Grounding Guard verification badge and advisory notice | Planned |
| **ADR 0002 Human Decision Gate** | UI blocks direct execution; enforces specialist reviewer ID format | Planned |
| **Override Eligibility Firewall** | Specialist override strictly restricted to `EligibleActionSet` | Planned |
| **Cryptographic Audit Ledger** | Live append passes `scripts/verify_conservation_audit_trail.py` | Planned |
| **Automated Test Coverage** | Headless smoke and service tests pass in `dashboard/tests/` | Planned |
| **Repository Boundaries** | `./scripts/check_repository_boundaries.sh` clean-room verified | Planned |

