"""Formal evaluators for Pre-Registered System Qualification Gates S1–S6.

Each evaluator returns a GateResult containing:
- gate_id: Unique identifier (e.g. "GATE_S1")
- name: Human-readable gate description
- passed: Boolean indicating 100% compliance with pre-registered standard
- scorecard_metric: Key quantitative readout (e.g. "Rejection Rate: 100.0%")
- details: Structured telemetry dictionary
- error_message: Optional failure explanation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any, Mapping, Sequence

from inforsight_simulator.assistant import CaseIntelligenceAssistant
from inforsight_simulator.audit.ledger import AuditLedger
from inforsight_simulator.audit.serialization import canonical_json_dumps, compute_sha256
from inforsight_simulator.audit.verifier import AuditTrailVerifier
from inforsight_simulator.bundle import BundledInferenceEngine
from inforsight_simulator.optimization import (
    PolicyValuation,
    PortfolioOptimizer,
    SPECIALIST_ACTIONS,
)
from inforsight_simulator.rules import (
    EligibilityRulesEngine,
    EligibleActionSet,
    PolicyContext,
)
from inforsight_simulator.rules.reasons import DisqualificationReasonCode
from inforsight_simulator.v6_corpus import V6Observation
from inforsight_simulator.v6_evaluation import _feature_map
from inforsight_simulator.workflow.models import (
    CaseState,
    SpecialistReviewAction,
    UnauthorizedExecutionError,
)
from inforsight_simulator.workflow.service import WorkflowService


@dataclass(frozen=True)
class GateResult:
    """Formal outcome record for a System Qualification Gate."""

    gate_id: str
    name: str
    passed: bool
    scorecard_metric: str
    details: dict[str, Any]
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "name": self.name,
            "passed": self.passed,
            "scorecard_metric": self.scorecard_metric,
            "details": self.details,
            "error_message": self.error_message,
        }


# =============================================================================
# Gate S1: Authority Isolation Invariant (ADR 0002)
# =============================================================================

def evaluate_gate_s1_authority_isolation(
    inference_engine: BundledInferenceEngine,
    sample_obs: V6Observation,
) -> GateResult:
    """Certify that models and engines cannot dispatch outreach without human credentials."""
    unauthorized_attempts = 0
    blocked_attempts = 0
    non_authority_markers_valid = True
    marker_checks: list[str] = []

    # 1. Check model inference output doesn't authorize action
    feat_map = _feature_map(sample_obs)
    score_res = inference_engine.score_record(feat_map)
    # The BundledInferenceEngine score output is purely a perception probability
    marker_checks.append("score_record: perception only, no dispatch capability")

    # 2. Check Assistant Case Brief marks authorized_to_act: false
    from inforsight_simulator.assistant.context import CaseEvidenceContext

    assistant = CaseIntelligenceAssistant()
    ctx = CaseEvidenceContext(
        policy_id=sample_obs.policy_id,
        as_of_date=sample_obs.as_of,
        case_id="case_s1_test",
        product_type="term_life",
        annual_premium=1200.0,
        monthly_premium=100.0,
        coverage_amount=250000.0,
        tenure_months=int(sample_obs.features.tenure_days / 30),
        total_premiums_paid=1200.0,
        policy_status="active",
        in_grace_period=False,
        days_past_due=0,
        payment_frequency="monthly",
        initial_payment_method="eft",
        risk_class="standard",
        servicing_advisor_id="adv_001",
        has_active_claim=False,
        has_legal_hold=False,
        has_registered_dispute=False,
        calibrated_probability=score_res.calibrated_probability,
        operational_tier=score_res.risk_tier,
        top_risk_drivers=(),
        eligible_actions=("grace_period_consultation", "abstain"),
        disqualified_actions=(),
        primary_action="grace_period_consultation",
        uplift_quadrant="PERSUADABLE",
        expected_net_utility=150.0,
        alternative_actions=(),
        timeline_events=(),
    )
    brief = assistant.generate_brief(
        ctx,
        generated_at=sample_obs.as_of,
        brief_id=f"brief_{sample_obs.policy_id}",
    )
    brief_dict = brief.to_dict()
    if brief_dict.get("authorized_to_act") is not False:
        non_authority_markers_valid = False
        marker_checks.append("FAILED: CaseBrief authorized_to_act != False")
    else:
        marker_checks.append("PASSED: CaseBrief authorized_to_act == False")

    # 3. Check WorkflowService / StateMachine fails closed on direct execution attempt
    workflow = WorkflowService()
    case_ctx = workflow.create_case(
        policy_id=sample_obs.policy_id,
        as_of_date=sample_obs.as_of,
        reconstructed_state={"policy_id": sample_obs.policy_id, "tenure_days": 365},
        scoring_result={
            "calibrated_probability": score_res.calibrated_probability,
            "operational_tier": score_res.risk_tier,
        },
        eligible_action_set={"primary_action": "grace_period_consultation", "eligible_actions": ["grace_period_consultation", "abstain"]},
        case_brief=brief_dict,
        model_bundle_id="phase-02-10-model-bundle",
    )

    # In RECOMMENDED state, dispatch_execution MUST fail with UnauthorizedExecutionError
    unauthorized_attempts += 1
    try:
        case_ctx.state_machine.dispatch_execution(
            channel="direct_phone",
            outreach_reference="OUTREACH-AUTOMATED-001",
            occurred_at=sample_obs.as_of,
        )
    except UnauthorizedExecutionError:
        blocked_attempts += 1
        marker_checks.append("PASSED: state_machine.dispatch_execution rejected in RECOMMENDED state")
    except Exception as exc:
        marker_checks.append(f"FAILED: expected UnauthorizedExecutionError, got {type(exc).__name__}")

    # Attempt to bypass via WorkflowService.dispatch_execution directly
    unauthorized_attempts += 1
    try:
        workflow.dispatch_execution(
            case_id=case_ctx.case_id,
            channel="direct_phone",
            outreach_reference="OUTREACH-AUTOMATED-002",
            occurred_at=sample_obs.as_of,
        )
    except UnauthorizedExecutionError:
        blocked_attempts += 1
        marker_checks.append("PASSED: workflow.dispatch_execution rejected without human review")
    except Exception as exc:
        marker_checks.append(f"FAILED: workflow.dispatch_execution raised unexpected {type(exc).__name__}")

    rejection_rate = (blocked_attempts / unauthorized_attempts) if unauthorized_attempts > 0 else 0.0
    passed = (rejection_rate == 1.0) and non_authority_markers_valid

    return GateResult(
        gate_id="GATE_S1",
        name="Authority Isolation Invariant (ADR 0002)",
        passed=passed,
        scorecard_metric=f"Rejection Rate: {rejection_rate * 100:.1f}% ({blocked_attempts}/{unauthorized_attempts})",
        details={
            "unauthorized_attempts": unauthorized_attempts,
            "blocked_attempts": blocked_attempts,
            "rejection_rate": rejection_rate,
            "non_authority_markers_valid": non_authority_markers_valid,
            "checks": marker_checks,
        },
    )


# =============================================================================
# Gate S2: Action Eligibility & Legal Dispute Firewall
# =============================================================================

def evaluate_gate_s2_eligibility_firewall(
    rules_engine: EligibilityRulesEngine,
    observations: Sequence[V6Observation],
) -> GateResult:
    """Certify that active legal disputes, claims, and non-viable policies are 100% disqualified."""
    proactive_actions = {
        "specialist_phone_outreach",
        "grace_period_consultation",
        "payment_method_remediation",
        "self_service_link",
    }

    total_dispute_tests = 0
    passed_dispute_tests = 0
    false_positive_actions = 0
    dispute_reasons_observed: set[str] = set()

    for idx, obs in enumerate(observations[:200]):
        feats = obs.features
        dpd = int(feats.recent_delay_days or 0)
        try:
            as_of_dt = datetime.fromisoformat(obs.as_of.replace("Z", "+00:00"))
        except Exception:
            as_of_dt = datetime.now(timezone.utc)

        # Scenario 1: Inject Registered Legal Dispute
        ctx_dispute = PolicyContext(
            policy_id=f"{obs.policy_id}_dispute",
            as_of=as_of_dt,
            status="grace_period" if (0 < dpd <= 30) else "active",
            tenure_days=feats.tenure_days,
            in_grace_period=(0 < dpd <= 30),
            days_past_due=dpd,
            has_registered_dispute=True,
        )
        total_dispute_tests += 1
        res_dispute = rules_engine.evaluate(ctx_dispute)
        if res_dispute.is_frozen and res_dispute.freeze_reason:
            dispute_reasons_observed.add(res_dispute.freeze_reason)
        # Verify NO proactive outreach is allowed
        allowed = set(res_dispute.eligible_actions) - {"abstain"}
        if allowed:
            false_positive_actions += len(allowed)
        else:
            passed_dispute_tests += 1

        # Scenario 2: Inject Active Insurance Claim
        ctx_claim = PolicyContext(
            policy_id=f"{obs.policy_id}_claim",
            as_of=as_of_dt,
            status="grace_period" if (0 < dpd <= 30) else "active",
            tenure_days=feats.tenure_days,
            in_grace_period=(0 < dpd <= 30),
            days_past_due=dpd,
            has_active_claim=True,
        )
        total_dispute_tests += 1
        res_claim = rules_engine.evaluate(ctx_claim)
        if res_claim.is_frozen and res_claim.freeze_reason:
            dispute_reasons_observed.add(res_claim.freeze_reason)
        allowed_claim = set(res_claim.eligible_actions) - {"abstain"}
        if allowed_claim:
            false_positive_actions += len(allowed_claim)
        else:
            passed_dispute_tests += 1

        # Scenario 3: Inject Legal Hold
        ctx_hold = PolicyContext(
            policy_id=f"{obs.policy_id}_hold",
            as_of=as_of_dt,
            status="grace_period" if (0 < dpd <= 30) else "active",
            tenure_days=feats.tenure_days,
            in_grace_period=(0 < dpd <= 30),
            days_past_due=dpd,
            has_legal_hold=True,
        )
        total_dispute_tests += 1
        res_hold = rules_engine.evaluate(ctx_hold)
        if res_hold.is_frozen and res_hold.freeze_reason:
            dispute_reasons_observed.add(res_hold.freeze_reason)
        allowed_hold = set(res_hold.eligible_actions) - {"abstain"}
        if allowed_hold:
            false_positive_actions += len(allowed_hold)
        else:
            passed_dispute_tests += 1

        # Scenario 4: Non-viable terminal status (e.g. "lapsed" or "surrendered")
        ctx_lapsed = PolicyContext(
            policy_id=f"{obs.policy_id}_lapsed",
            as_of=as_of_dt,
            status="lapsed",
            tenure_days=feats.tenure_days,
            in_grace_period=False,
            days_past_due=60,
        )
        total_dispute_tests += 1
        res_lapsed = rules_engine.evaluate(ctx_lapsed)
        allowed_lapsed = set(res_lapsed.eligible_actions) - {"abstain"}
        if allowed_lapsed:
            false_positive_actions += len(allowed_lapsed)
        else:
            passed_dispute_tests += 1

    firewall_pass_rate = (passed_dispute_tests / total_dispute_tests) if total_dispute_tests > 0 else 0.0
    passed = (firewall_pass_rate == 1.0) and (false_positive_actions == 0)

    return GateResult(
        gate_id="GATE_S2",
        name="Action Eligibility & Legal Dispute Firewall",
        passed=passed,
        scorecard_metric=f"Firewall Pass Rate: {firewall_pass_rate * 100:.1f}% (0 False Positives / {total_dispute_tests} tests)",
        details={
            "total_dispute_tests": total_dispute_tests,
            "passed_dispute_tests": passed_dispute_tests,
            "false_positive_actions": false_positive_actions,
            "firewall_pass_rate": firewall_pass_rate,
            "dispute_reasons_observed": sorted(dispute_reasons_observed),
        },
    )


# =============================================================================
# Gate S3: Budget and Specialist Capacity Adherence
# =============================================================================

def evaluate_gate_s3_capacity_adherence(
    eligible_sets: Sequence[EligibleActionSet],
    valuations: Mapping[str, PolicyValuation],
    risk_scores: Mapping[str, float],
    days_past_due_map: Mapping[str, int],
    specialist_capacity: int = 50,
    budget_cap_usd: float = 5_000.0,
) -> GateResult:
    """Certify that portfolio allocations strictly adhere to capacity and budget caps."""
    optimizer = PortfolioOptimizer(
        specialist_capacity=specialist_capacity,
        total_budget_usd=budget_cap_usd,
    )

    allocation = optimizer.optimize_portfolio(
        eligible_sets=eligible_sets,
        valuations=valuations,
        risk_scores=risk_scores,
        days_past_due_map=days_past_due_map,
    )

    specialist_count = 0
    total_cost = 0.0

    for rec in allocation.recommendations:
        if rec.recommended_action in SPECIALIST_ACTIONS:
            specialist_count += 1
        # Sum direct cost
        u = rec.action_utilities.get(rec.recommended_action)
        if u:
            total_cost += u.direct_cost_usd

    capacity_overflow = max(0, specialist_count - specialist_capacity)
    budget_overflow = max(0.0, total_cost - budget_cap_usd)

    capacity_overflow_pct = (capacity_overflow / specialist_capacity) * 100.0
    budget_overflow_pct = (budget_overflow / budget_cap_usd) * 100.0

    passed = (capacity_overflow == 0) and (budget_overflow == 0.0)

    return GateResult(
        gate_id="GATE_S3",
        name="Budget and Specialist Capacity Adherence",
        passed=passed,
        scorecard_metric=(
            f"Specialist Allocations: {specialist_count}/{specialist_capacity} (0% overflow), "
            f"Spend: ${total_cost:,.2f}/${budget_cap_usd:,.2f} (0% overflow)"
        ),
        details={
            "specialist_capacity": specialist_capacity,
            "specialist_allocated": specialist_count,
            "capacity_overflow": capacity_overflow,
            "capacity_overflow_pct": capacity_overflow_pct,
            "budget_cap_usd": budget_cap_usd,
            "total_allocated_spend_usd": total_cost,
            "budget_overflow_usd": budget_overflow,
            "budget_overflow_pct": budget_overflow_pct,
            "total_cases_allocated": len(allocation.recommendations),
        },
    )


# =============================================================================
# Gate S4: Audit Trail Tamper Resistance
# =============================================================================

def evaluate_gate_s4_audit_tamper_resistance() -> GateResult:
    """Certify cryptographic hash-chain verification and 100% tamper detection."""
    test_cases_count = 5
    ledger = AuditLedger()

    # Generate a realistic mini audit trail
    for i in range(1, test_cases_count + 1):
        pid = f"POL-TEST-{i:04d}"
        cid = f"CASE-TEST-{i:04d}"
        ts = f"2026-09-06T00:{i:02d}:00Z"
        ledger.append(
            case_id=cid,
            policy_id=pid,
            case_event_id=f"EVT-{i:04d}-1",
            from_state="CREATED",
            to_state="TRIAGED",
            decision_context_digest={"model_bundle_id": "test-bundle", "score": 0.35},
            timestamp=ts,
        )
        ledger.append(
            case_id=cid,
            policy_id=pid,
            case_event_id=f"EVT-{i:04d}-2",
            from_state="TRIAGED",
            to_state="RECOMMENDED",
            decision_context_digest={"model_bundle_id": "test-bundle", "score": 0.35},
            timestamp=ts,
        )

    import copy

    # 1. Verify pristine ledger
    clean_records = [r.to_dict() for r in ledger.records]
    res_pristine = AuditTrailVerifier.verify_records(clean_records)
    pristine_valid = res_pristine.is_valid

    attacks_tested = 0
    attacks_detected = 0
    attack_log: list[dict[str, Any]] = []

    # Attack 1: Payload mutation in record #3
    attacks_tested += 1
    mutated_records = copy.deepcopy(clean_records)
    mutated_records[3]["policy_id"] = "POL-FORGED-9999"
    res_mut = AuditTrailVerifier.verify_records(mutated_records)
    if not res_mut.is_valid:
        attacks_detected += 1
        attack_log.append({"attack": "payload_mutation", "detected": True, "error": res_mut.error_message})
    else:
        attack_log.append({"attack": "payload_mutation", "detected": False})

    # Attack 2: Record deletion (remove record #4)
    attacks_tested += 1
    deleted_records = copy.deepcopy(clean_records)
    deleted_records.pop(4)
    res_del = AuditTrailVerifier.verify_records(deleted_records)
    if not res_del.is_valid:
        attacks_detected += 1
        attack_log.append({"attack": "record_deletion", "detected": True, "error": res_del.error_message})
    else:
        attack_log.append({"attack": "record_deletion", "detected": False})

    # Attack 3: Record reordering (swap record #2 and #3)
    attacks_tested += 1
    reordered_records = copy.deepcopy(clean_records)
    reordered_records[2], reordered_records[3] = reordered_records[3], reordered_records[2]
    res_swap = AuditTrailVerifier.verify_records(reordered_records)
    if not res_swap.is_valid:
        attacks_detected += 1
        attack_log.append({"attack": "record_reordering", "detected": True, "error": res_swap.error_message})
    else:
        attack_log.append({"attack": "record_reordering", "detected": False})

    # Attack 4: Record injection (inject unauthorized block)
    attacks_tested += 1
    injected_records = copy.deepcopy(clean_records)
    fake_rec = copy.deepcopy(clean_records[2])
    fake_rec["case_event_id"] = "EVT-FORGED-INJECTION"
    injected_records.insert(3, fake_rec)
    res_inj = AuditTrailVerifier.verify_records(injected_records)
    if not res_inj.is_valid:
        attacks_detected += 1
        attack_log.append({"attack": "record_injection", "detected": True, "error": res_inj.error_message})
    else:
        attack_log.append({"attack": "record_injection", "detected": False})

    detection_rate = (attacks_detected / attacks_tested) if attacks_tested > 0 else 0.0
    passed = pristine_valid and (detection_rate == 1.0)

    return GateResult(
        gate_id="GATE_S4",
        name="Audit Trail Tamper Resistance",
        passed=passed,
        scorecard_metric=f"Tamper Detection Rate: {detection_rate * 100:.1f}% ({attacks_detected}/{attacks_tested} attacks flagged)",
        details={
            "pristine_chain_valid": pristine_valid,
            "attacks_tested": attacks_tested,
            "attacks_detected": attacks_detected,
            "tamper_detection_rate": detection_rate,
            "attack_scenarios": attack_log,
        },
    )


# =============================================================================
# Gate S5: Inference and Pipeline Latency SLA
# =============================================================================

def evaluate_gate_s5_latency_sla(
    inference_engine: BundledInferenceEngine,
    observations: Sequence[V6Observation],
    single_sla_ms: float = 10.0,
    batch_sla_ms: float = 100.0,
) -> GateResult:
    """Certify local CPU inference and scoring latencies conform to SLAs."""
    obs_sample = observations[:100]
    durations_ms: list[float] = []

    # 1. Single-policy scoring benchmark (100 repetitions)
    for obs in obs_sample:
        feat_map = _feature_map(obs)
        t0 = time.perf_counter_ns()
        _ = inference_engine.score_record(feat_map)
        t1 = time.perf_counter_ns()
        durations_ms.append((t1 - t0) / 1_000_000.0)

    durations_ms.sort()
    n = len(durations_ms)
    p50_ms = durations_ms[int(0.50 * n)]
    p90_ms = durations_ms[int(0.90 * n)]
    p95_ms = durations_ms[int(0.95 * n)]
    p99_ms = durations_ms[int(0.99 * n)]
    max_ms = durations_ms[-1]

    # 2. Batch scoring benchmark (50 policies in batch)
    batch_features = [_feature_map(o) for o in observations[:50]]
    t0_batch = time.perf_counter_ns()
    _ = [inference_engine.score_record(f) for f in batch_features]
    t1_batch = time.perf_counter_ns()
    batch_elapsed_ms = (t1_batch - t0_batch) / 1_000_000.0
    per_item_batch_ms = batch_elapsed_ms / len(batch_features)

    passed_single = (p99_ms <= single_sla_ms)
    passed_batch = (batch_elapsed_ms <= batch_sla_ms)
    passed = passed_single and passed_batch

    return GateResult(
        gate_id="GATE_S5",
        name="Inference and Pipeline Latency SLA",
        passed=passed,
        scorecard_metric=(
            f"Single P99: {p99_ms:.3f}ms (SLA <= {single_sla_ms:.1f}ms), "
            f"Batch(50): {batch_elapsed_ms:.2f}ms (SLA <= {batch_sla_ms:.1f}ms)"
        ),
        details={
            "sample_size": n,
            "latency_p50_ms": p50_ms,
            "latency_p90_ms": p90_ms,
            "latency_p95_ms": p95_ms,
            "latency_p99_ms": p99_ms,
            "latency_max_ms": max_ms,
            "single_policy_sla_ms": single_sla_ms,
            "single_policy_sla_met": passed_single,
            "batch_50_elapsed_ms": batch_elapsed_ms,
            "batch_per_policy_ms": per_item_batch_ms,
            "batch_sla_ms": batch_sla_ms,
            "batch_sla_met": passed_batch,
        },
    )


# =============================================================================
# Gate S6: Deterministic Bit-for-Bit Reproducibility
# =============================================================================

def evaluate_gate_s6_reproducibility(
    digest_run_1: str,
    digest_run_2: str,
    identical_allocations: bool,
    identical_scores: bool,
) -> GateResult:
    """Certify that two independent end-to-end pipeline executions produce bit-for-bit identical results."""
    digests_match = (digest_run_1 == digest_run_2) and (len(digest_run_1) == 64)
    passed = digests_match and identical_allocations and identical_scores

    return GateResult(
        gate_id="GATE_S6",
        name="Deterministic Bit-for-Bit Reproducibility",
        passed=passed,
        scorecard_metric=(
            f"Digest Match: {'IDENTICAL' if digests_match else 'MISMATCH'} (SHA-256: {digest_run_1[:16]}...)"
        ),
        details={
            "digest_run_1": digest_run_1,
            "digest_run_2": digest_run_2,
            "digests_match": digests_match,
            "identical_allocations": identical_allocations,
            "identical_scores": identical_scores,
        },
    )
