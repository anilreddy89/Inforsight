# Phase 3.06 — Human-in-the-Loop Workflow and Audit Trail Engine

## Issue metadata

| Field | Value |
| --- | --- |
| Phase | Phase 3 — Policy Conservation Decision Engine & Intervention Orchestration |
| Sequence | 06 |
| Change tracker ID | `P3-06` |
| GitHub issue | [#118](https://github.com/anilreddy89/Inforsight/issues/118) |
| Issue title | `[Implementation] P3-06: Human-in-the-loop workflow and audit trail engine` |
| Branch | `feat/118-p3-06-hitl-workflow-audit-trail` |
| Pull request | `[Pending PR Creation]` |
| Status | Complete (Implementation & Test Suite Verified) |
| Milestone | [v0.3.0-decision-engine](https://github.com/anilreddy89/Inforsight/milestone/4) |
| Priority | Milestone blocking / Foundational |
| Classification | Workflow Engine / Audit Trail / Governance / Compliance |
| Strict predecessor | Phase 3.01 (`7ed7efd`), Phase 3.02 (`1177394`), Phase 3.03 (`a1e97cb`), Phase 3.04 (`87a66f9`), Phase 3.04A (`920f943`), Phase 3.05 (`39c35c0`) |
| Governing predecessor decisions | ADR 0001 (Clean Room), ADR 0002 (Separate Risk Perception from Action Eligibility), ADR 0003 (Local Deterministic Execution), ADR 0004 (Model Governance) |
| Target release tag | `v0.3.0-decision-engine` |
| Enables | P3-07 (Interactive Conservation Dashboard), P3-09 (Production Deployment & Verification) |
| Blocks | P3-07, P3-09 |
| Last reviewed | 2026-09-05 |

---

## 1. Executive Summary and Problem Statement

### 1.1 Context & Regulatory Imperative (ADR 0002)

Phase 3 establishes the policy conservation decision and orchestration capabilities for Inforsight:
- **Phase 3.01**: Defined conservation domain contracts (`conservation-action.schema.json`, `conservation-case-event.schema.json`) and the 5-action taxonomy.
- **Phase 3.02**: Built the deterministic action eligibility rules engine enforcing legal, regulatory, and business constraints (`EligibleActionSet`).
- **Phase 3.03**: Implemented economic uplift and cost-utility optimization allocating constrained specialist capacity (`OptimalRecommendation`, `PortfolioAllocation`).
- **Phase 3.04 & 3.04A**: Delivered the production model serving gateway (`/v1/score`) and real-time drift telemetry (`/v1/diagnostics`).
- **Phase 3.05**: Implemented the dual-layer bounded case intelligence assistant (`CaseBrief`, deterministic templates, and grounding guard firewalls).

While these upstream systems provide calibrated risk perceptions, legal eligibility boundaries, economic allocations, and structured case briefs, **none of them possesses the legal, ethical, or operational authority to autonomously alter an in-force policy, bill a policyholder, or dispatch customer outreach**.

Under **ADR 0002** (*Separate probabilistic risk from deterministic action eligibility*):
> "The predictive layer produces a versioned, time-bounded risk estimate. A separate deterministic rules layer evaluates allowed actions. Assistive components may assemble evidence and draft a recommendation, but a human reviewer makes the final decision."

In life insurance operations, fully autonomous policy interventions create catastrophic regulatory, legal, and operational risks:
1. **Unfair and Deceptive Acts or Practices (UDAAP) & Market Conduct Violations**: Automated outreach dispatched without licensed human review during sensitive life events (e.g., bereavement, catastrophic injury claims, ongoing legal disputes) exposes carriers to statutory penalties, state insurance commissioner audits, and private litigation.
2. **Unauthorized Policy Forfeiture or Modification**: Altering premium schedules, auto-draft details, or benefit structures without verified specialist review and recorded customer authorization breaches insurance contract law and fiduciary duties.
3. **Black-Box Decision Liability**: If an algorithmic recommendation is executed without an attributable human decision-maker and structured rationale, the carrier cannot defend its actions during a compliance examination or regulatory inquiry.

Phase 3.06 implements the **Human-in-the-Loop (HITL) Workflow and Audit Trail Engine** (`inforsight_simulator/workflow/` and `inforsight_simulator/audit/`). This subsystem enforces non-delegable human decision boundaries and records an immutable, cryptographically chained audit ledger proving complete point-in-time decision provenance.

---

## 2. Architecture & System Boundary

### 2.1 The End-to-End Decision Pipeline

The workflow and audit engine is the governing gatekeeper standing between intelligence synthesis and operational dispatch:

```text
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                                Upstream Intelligence                                  │
│  - Reconstruction: PointInTimeState (Phase 1.04)                                      │
│  - Model Serving: ScoringResult & SHAP Attributions (Phase 2.10 / Phase 3.04)         │
│  - Eligibility Rules: EligibleActionSet (Phase 3.02)                                  │
│  - Optimization: OptimalRecommendation & Utility (Phase 3.03)                         │
│  - Case Assistant: Verified CaseBrief (Phase 3.05)                                    │
└──────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                        HITL Workflow State Machine Engine                             │
│                     (inforsight_simulator/workflow/engine.py)                         │
│                                                                                       │
│   [CREATED] ──> [TRIAGED] ──> [EVIDENCE_ASSEMBLED] ──> [RECOMMENDED]                  │
│                                                              │                        │
│                           ADR 0002 Gate                      ▼                        │
│                           (Automated dispatch BLOCKED)  [HUMAN_REVIEW]                │
│                                                              │                        │
│                     ┌────────────────────────────────────────┴──────────────┐         │
│                     ▼                                                       ▼         │
│               [EXECUTED]                                               [DISMISSED]    │
│                     │                                                       │         │
│                     └────────────────────────┬──────────────────────────────┘         │
│                                              ▼                                        │
│                                         [RESOLVED]                                    │
└──────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │ Emits Case Transition Events
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                    Cryptographic Append-Only Audit Ledger                             │
│                      (inforsight_simulator/audit/ledger.py)                           │
│                                                                                       │
│   ┌───────────────────────────┐    SHA-256    ┌───────────────────────────┐           │
│   │ Entry i-1                 │ ────────────> │ Entry i                   │           │
│   │ Prev Hash: H_{i-2}        │               │ Prev Hash: H_{i-1}        │           │
│   │ Payload Digest: D_{i-1}   │               │ Payload Digest: D_i       │           │
│   │ Entry Hash: H_{i-1}       │               │ Entry Hash: H_i           │           │
│   └───────────────────────────┘               └───────────────────────────┘           │
│                                                                                       │
│   Immutable Disk File: `conservation-audit-log.jsonl`                                  │
└──────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │
                                           ▼
┌───────────────────────────────────────────────────────────────────────────────────────┐
│               Point-in-Time Audit Replay & Verification Tool                          │
│               (scripts/verify_conservation_audit_trail.py)                            │
│  - Mathematical proof of chain integrity (zero tampering / bit modification)         │
│  - Exact reconstruction of point-in-time evidence, model scores, and reviewer context │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. HITL Conservation Case State Machine

### 3.1 Lifecycle States and Transitions

The workflow engine strictly enforces the lifecycle state graph formalized in `data-contracts/conservation-case-event.schema.json`:

| State | Description | Invariants & Authority |
| --- | --- | --- |
| `NONE` | Pre-creation virtual state. | Starting state for initial event. |
| `CREATED` | Conservation case instantiated for a policy. | Generated upon triage trigger or policy anniversary/grace entry. |
| `TRIAGED` | Model scoring executed. | Contains `ScoringResult` (calibrated $\hat{p}$, operational tier, SHAP features). |
| `EVIDENCE_ASSEMBLED` | Point-in-time policy state reconstructed. | Contains immutable `PointInTimeState` as of the cutoff timestamp. |
| `RECOMMENDED` | Actions evaluated and briefed. | Contains `EligibleActionSet`, `OptimalRecommendation`, and `CaseBrief`. **`authorized_to_act: false` strictly enforced.** |
| `HUMAN_REVIEWED` | Authenticated human review recorded. | Contains verified `human_review` record (`reviewer_id`, `decision`, `rationale_code`). |
| `EXECUTED` | Approved intervention dispatched. | Only reachable from `HUMAN_REVIEWED` with `decision: APPROVED` or authorized `OVERRIDDEN`. |
| `DISMISSED` | Case closed without active intervention. | Only reachable from `HUMAN_REVIEWED` with `decision: REJECTED` or when recommendation was `abstain`. |
| `RESOLVED` | Terminal lifecycle state. | Final resting state after execution dispatch or dismissal. |

### 3.2 The Strict Non-Autonomous Invariant

The state transition table contains a hard structural constraint:
$$\text{Transition}(\text{RECOMMENDED} \to \text{EXECUTED}) \equiv \varnothing \quad (\text{Strictly Prohibited})$$

Any attempt to trigger execution directly from `RECOMMENDED` without an intervening `HUMAN_REVIEWED` transition event raises a fail-closed `UnauthorizedExecutionError`.

### 3.3 Specialist Review Actions & Validation Rules

When a conservation specialist reviews a case in state `RECOMMENDED`, the workflow engine accepts four discrete review operations:

```python
class SpecialistDecision(str, Enum):
    APPROVE_RECOMMENDATION = "APPROVE_RECOMMENDATION"
    OVERRIDE_ACTION = "OVERRIDE_ACTION"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    REJECT_AND_CLOSE = "REJECT_AND_CLOSE"
```

1. **`APPROVE_RECOMMENDATION`**:
   - The specialist accepts the system's primary recommended action (`OptimalRecommendation.recommended_action`).
   - Requires valid `reviewer_id` (`usr_[a-z0-9_]{3,32}`).
   - Sets `human_review.decision = "APPROVED"`.
   - Transitions case: `RECOMMENDED` $\to$ `HUMAN_REVIEWED`.
   - Permissible next step: `HUMAN_REVIEWED` $\to$ `EXECUTED` (or `DISMISSED` if action was `abstain`).

2. **`OVERRIDE_ACTION`**:
   - The specialist rejects the primary recommendation and selects an alternative action from the action taxonomy.
   - **Eligibility Firewall**: The overridden action **must** belong to `EligibleActionSet.eligible_actions`. Attempting to override with a disqualified action (e.g. attempting phone outreach on a legal freeze policy) is rejected fail-closed with `IneligibleOverrideError`.
   - **Mandatory Rationale Code**: Must provide a standard structured code (`OVERRIDE_RATIONALE_*`, e.g., `OVERRIDE_SPECIALIST_DISCRETION_PREMIUM_DISPUTE`, `OVERRIDE_PREFERRED_CHANNEL_EMAIL`).
   - **Mandatory Justification**: Must provide free-form text justification of at least 5 characters detailing operational context.
   - Sets `human_review.decision = "OVERRIDDEN"`.
   - Transitions case: `RECOMMENDED` $\to$ `HUMAN_REVIEWED`.

3. **`REQUEST_MORE_INFO`**:
   - The specialist determines that current evidence is insufficient (e.g. pending billing reconciliation).
   - Case transitions to a hold state or re-enters `EVIDENCE_ASSEMBLED` for refreshed point-in-time extraction.

4. **`REJECT_AND_CLOSE`**:
   - The specialist declines all proactive interventions.
   - Requires valid `reviewer_id`, structured `rationale_code` (e.g., `REJECT_CUSTOMER_REQUESTED_NO_CONTACT`, `REJECT_POLICY_REPLACED_EXTERNALLY`), and justification text.
   - Sets `human_review.decision = "REJECTED"`.
   - Transitions case: `RECOMMENDED` $\to$ `HUMAN_REVIEWED` $\to$ `DISMISSED` $\to$ `RESOLVED`.

---

## 4. Cryptographic Tamper-Evident Audit Ledger

### 4.1 Threat Model and Immutability Requirements

In insurance regulatory examinations and financial audits, operational logs stored in mutable databases or standard application loggers are vulnerable to:
- Post-hoc alteration or deletion of inconvenient decision records.
- Fabricated reviewer timestamps or synthetic approval injection.
- Re-ordering of events to simulate timely compliance with cooling-off or grace-period statutory deadlines.

To eliminate these vulnerabilities, Phase 3.06 implements an **append-only, cryptographically hash-chained audit ledger** (`inforsight_simulator/audit/`).

### 4.2 Mathematical Specification of Hash Chaining

The ledger maintains a continuous cryptographic chain across all case events:

1. **Genesis Anchor**:
   The chain originates from a deterministic, constant genesis hash:
   $$H_0 = \text{SHA-256}(\text{"INFORSIGHT_CONSERVATION_AUDIT_GENESIS_V0_3_0"})$$

2. **Canonical Serialization**:
   To ensure bit-level deterministic hashing regardless of JSON key ordering, floating-point string representations, or platform-specific whitespace, entry payloads are serialized via canonical JSON encoding (RFC 8785 conventions):
   $$C_i = \text{CanonicalJSON}(\text{EntryPayload}_i \setminus \{\text{"entry_hash"}\})$$

3. **Recursive Hash Chaining**:
   For each sequential entry $i \ge 1$:
   $$H_i = \text{SHA-256}(H_{i-1} \parallel C_i)$$
   where $\parallel$ denotes string concatenation.

4. **Tamper Evidence Property**:
   $$\forall j \ge i, \quad \frac{\partial H_j}{\partial C_i} \neq 0$$
   Any alteration, insertion, truncation, or reordering of entry $i$ breaks the hash chain for all subsequent entries $j \ge i$, causing verification to fail immediately.

### 4.3 Audit Entry Record Structure

Each line in `conservation-audit-log.jsonl` is an immutable, self-contained record:

```json
{
  "audit_entry_id": "aud_018f3a9b1c2d3e4f5a6b7c8d9e",
  "sequence_number": 142,
  "timestamp": "2026-09-05T14:30:00Z",
  "case_id": "case_982347102938471029",
  "policy_id": "pol_104928374619",
  "event_id": "cev_582910394857291039",
  "from_state": "RECOMMENDED",
  "to_state": "HUMAN_REVIEWED",
  "decision_context_digest": {
    "reconstructed_state_sha256": "4b7e...9a21",
    "model_bundle_id": "inforsight-v6-logistic-platt-20260817",
    "model_score_sha256": "7ac2...448f",
    "eligible_action_set_sha256": "8f3c...b012",
    "case_brief_sha256": "1e9a...55cd"
  },
  "human_review": {
    "reviewer_id": "usr_asmith_842",
    "reviewed_at": "2026-09-05T14:30:00Z",
    "decision": "APPROVED",
    "rationale_code": "APPROVE_OPTIMAL_RECOMMENDATION",
    "justification": "Policyholder within 10 days of grace period expiration; phone outreach selected per optimal net utility."
  },
  "dispatched_action": null,
  "prev_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "entry_hash": "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"
}
```

---

## 5. Point-in-Time Audit Replay & Verification Tool

### 5.1 CLI Verification Tool (`scripts/verify_conservation_audit_trail.py`)

A standalone CLI tool inspects and verifies any conservation audit log:

```bash
.venv/bin/python3 scripts/verify_conservation_audit_trail.py --log data/audit/conservation-audit-log.jsonl
```

### 5.2 Verification Verification Protocol

The verification script executes five sequential mathematical checks:
1. **Schema & Field Integrity**: Every line parses as valid JSON conforming to the audit record schema.
2. **Sequence Monotonicity**: `sequence_number` increases strictly by $+1$ ($0, 1, 2, \dots$) and `timestamp` is weakly monotonic non-decreasing.
3. **Cryptographic Chain Integrity**: For every record $i$, recomputes $\text{SHA-256}(H_{i-1} \parallel C_i)$ and asserts strict equality with $H_i$.
4. **ADR 0002 Compliance Invariant**: Asserts that zero entries transition to `EXECUTED` without a valid `human_review` sub-record and non-empty `reviewer_id`.
5. **Context Reproducibility Replay**: Samples historical audit entries, reloads the point-in-time state from the simulator corpus, and verifies that the reconstructed state hash matches `decision_context_digest.reconstructed_state_sha256`.

---

## 6. Implementation Scope and Module Layout

The proposed implementation introduces two new modules within `simulator/src/inforsight_simulator/`:

1. `inforsight_simulator/workflow/`:
   - `models.py`: Pydantic dataclasses for `CaseState`, `SpecialistDecision`, `HumanReviewRecord`, `WorkflowTransitionResult`.
   - `state_machine.py`: Deterministic state machine governing lifecycle transitions, validation rules, and authority checks.
   - `service.py`: High-level orchestration service binding upstream evidence (`ScoringResult`, `EligibleActionSet`, `CaseBrief`) to the state machine.

2. `inforsight_simulator/audit/`:
   - `ledger.py`: Append-only, thread-safe, cryptographically hash-chained audit logger writing to `.jsonl`.
   - `verifier.py`: Core verification engine checking sequence monotonicity, hash-chain integrity, and ADR 0002 compliance.
   - `serialization.py`: Canonical JSON serializer ensuring stable hash computation.

3. Standalone Verification Tool:
   - `scripts/verify_conservation_audit_trail.py`: CLI verification entry point.

4. Test Suite:
   - `simulator/tests/test_workflow.py`: Unit and invariant tests for the state machine, decision gates, and authority boundaries.
   - `simulator/tests/test_audit_ledger.py`: Cryptographic hash chain validation, tamper-injection detection, and concurrency tests.

---

## 7. Acceptance Criteria & Invariants

- [x] **ADR 0002 Mandatory Review Invariant**: Zero cases can transition to `EXECUTED` without a valid `human_review` record containing authenticated `reviewer_id` and timestamp.
- [x] **State Machine Integrity**: All case lifecycle transitions strictly satisfy the state graph defined in `data-contracts/conservation-case-event.schema.json`. Invalid transitions (e.g. `RECOMMENDED` $\to$ `EXECUTED`) fail closed with explicit exceptions.
- [x] **Structured Override & Justification**: Specialists can override recommendations only to actions present in `EligibleActionSet.eligible_actions`. Overrides to disqualified actions or overrides lacking structured rationale and justification ($\ge 5$ characters) are rejected.
- [x] **Cryptographic Hash Chaining**: Every audit entry includes `prev_hash` and `entry_hash = SHA256(prev_hash + canonical_payload)`. The genesis record anchors to the official genesis seed.
- [x] **Tamper-Detection Sensitivity**: Altering, deleting, inserting, or reordering any audit record in `conservation-audit-log.jsonl` is immediately detected and flagged by the verifier.
- [x] **Point-in-Time Context Digest**: Audit entries capture SHA-256 digests of upstream inputs (`PointInTimeState`, `ScoringResult`, `EligibleActionSet`, `CaseBrief`), enabling post-hoc verification.
- [x] **Zero Cloud Dependencies**: The workflow and audit logger run purely locally using standard Python libraries, adhering to ADR 0001 and ADR 0003.
- [x] **Standalone Verification Script**: `scripts/verify_conservation_audit_trail.py` executes cleanly and returns exit code `0` on valid ledgers and non-zero on tampered ledgers.
- [x] **Comprehensive Test Coverage**: Complete test suite passes with 100% assertions satisfied (`test_workflow.py`, `test_audit_ledger.py`).
- [x] **Repository Boundary Checks**: `./scripts/check_repository_boundaries.sh` passes with zero warnings.

---

## 8. Execution Command Reference

```bash
# Run workflow and audit unit test suites
.venv/bin/python3 -m unittest simulator/tests/test_workflow.py
.venv/bin/python3 -m unittest simulator/tests/test_audit_ledger.py

# Verify sample audit ledger
.venv/bin/python3 scripts/verify_conservation_audit_trail.py --log data/audit/conservation-audit-log.jsonl

# Run full repository checks
./scripts/check_repository_boundaries.sh
```

---

## 9. Verification Scorecard (Verified)

| Check | Target Standard | Status |
| :--- | :--- | :--- |
| **ADR 0002 Authority Boundary** | Direct transition `RECOMMENDED -> EXECUTED` raises `UnauthorizedExecutionError` | Verified (100%) |
| **Reviewer Credentials & Identity** | Validates `usr_[a-z0-9_]{3,32}`; rejects malformed IDs fail-closed | Verified (100%) |
| **Override Eligibility Firewall** | Specialist override restricted to `EligibleActionSet`; disqualified actions blocked | Verified (100%) |
| **Mandatory Rationale & Justification** | Rationale code regex matched; justification $\ge 5$ chars required on override/reject | Verified (100%) |
| **Canonical JSON Serialization** | RFC 8785 compliant sorted, whitespace-stripped deterministic encoding | Verified (100%) |
| **Cryptographic Hash Chaining** | Recursive $H_i = \text{SHA256}(H_{i-1} \parallel C_i)$ anchored to Genesis | Verified (100%) |
| **Tamper Detection Sensitivity** | Bit modifications, deletions, reorderings detected with sequence pointer | Verified (100%) |
| **Audit CLI Tool** | `scripts/verify_conservation_audit_trail.py` passes on valid, exits 1 on tampered | Verified (100%) |
| **Unit & Invariant Test Suite** | 15 tests in `test_workflow.py` and `test_audit_ledger.py` pass cleanly | Verified (15/15 passed) |
| **Phase 3 Regression Suite** | 51 tests across rules, optimization, assistant, workflow, audit pass | Verified (51/51 passed) |
| **Serving Regression Suite** | 52 tests in `serving/tests` pass | Verified (52/52 passed) |
| **Repository Boundaries** | `./scripts/check_repository_boundaries.sh` clean-room verified | Verified |


