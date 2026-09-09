"""End-to-End System Qualification Runner executing Gates S1–S6 across 1,000 synthetic test policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from inforsight_simulator.assistant import CaseIntelligenceAssistant
from inforsight_simulator.audit.ledger import AuditLedger
from inforsight_simulator.audit.serialization import canonical_json_dumps, compute_sha256
from inforsight_simulator.bundle import BundledInferenceEngine, ModelBundle
from inforsight_simulator.optimization import (
    PolicyValuation,
    PortfolioOptimizer,
    SPECIALIST_ACTIONS,
)
from inforsight_simulator.rules import (
    ActionEligibilityResult,
    EligibilityRulesEngine,
    EligibleActionSet,
    PolicyContext,
)
from inforsight_simulator.v6_corpus import (
    V6CorpusConfig,
    V6Features,
    V6Observation,
    generate_v6_corpus,
)
from inforsight_simulator.v6_evaluation import _feature_map
from inforsight_simulator.workflow.models import (
    ActionResourceRequirement,
    SpecialistReviewAction,
)
from inforsight_simulator.workflow.service import LocalTrustedActorAdapter, WorkflowService

from .gates import (
    GateResult,
    evaluate_gate_s1_authority_isolation,
    evaluate_gate_s2_eligibility_firewall,
    evaluate_gate_s3_capacity_adherence,
    evaluate_gate_s4_audit_tamper_resistance,
    evaluate_gate_s5_latency_sla,
    evaluate_gate_s6_reproducibility,
)


@dataclass(frozen=True)
class SystemQualificationResult:
    """Consolidated outcome of the pre-release system qualification suite."""

    seed: int
    cohort_size: int
    bundle_id: str
    bundle_sha256: str
    qualification_timestamp: str
    gates: dict[str, GateResult]
    overall_decision: str
    all_gates_passed: bool
    pipeline_digest: str
    allocations_summary: dict[str, Any]
    performance_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "cohort_size": self.cohort_size,
            "bundle_id": self.bundle_id,
            "bundle_sha256": self.bundle_sha256,
            "qualification_timestamp": self.qualification_timestamp,
            "gates": {k: v.to_dict() for k, v in self.gates.items()},
            "overall_decision": self.overall_decision,
            "all_gates_passed": self.all_gates_passed,
            "pipeline_digest": self.pipeline_digest,
            "allocations_summary": self.allocations_summary,
            "performance_summary": self.performance_summary,
        }


def _calculate_annual_premium_usd(features: V6Features) -> float:
    """Compute annualized premium from payment amount and billing frequency."""
    multiplier = {
        "monthly": 12,
        "quarterly": 4,
        "semiannual": 2,
        "annual": 1,
    }.get(features.billing_frequency, 12)
    return (features.premium_amount_cents / 100.0) * multiplier


class QualificationRunner:
    """Harness executing the complete end-to-end qualification pipeline."""

    def __init__(
        self,
        bundle_path: str | Path = "docs/experiments/phase-02-10-model-bundle.json",
        seed: int = 20280201,
        policy_count: int = 1000,
        specialist_capacity: int = 50,
        budget_cap_usd: float = 5_000.0,
    ) -> None:
        self.bundle_path = Path(bundle_path)
        self.seed = seed
        self.policy_count = policy_count
        self.specialist_capacity = specialist_capacity
        self.budget_cap_usd = budget_cap_usd

        # Load inference engine
        with open(self.bundle_path, "r", encoding="utf-8") as f:
            bundle_raw = f.read()
            self.bundle_sha256 = compute_sha256(bundle_raw)
            bundle_dict = json.loads(bundle_raw)

        bundle = ModelBundle.from_dict(bundle_dict)
        self.inference_engine = BundledInferenceEngine(bundle)
        self.bundle_id = bundle.bundle_id

    def _execute_pipeline_run(
        self,
        seed: int,
    ) -> tuple[dict[str, Any], Sequence[V6Observation], dict[str, float], list[EligibleActionSet], Any, AuditLedger]:
        """Execute the end-to-end pipeline and return structured outputs and ledger."""
        cohort_count = 5
        policies_per_cohort = self.policy_count // cohort_count
        actual_count = cohort_count * policies_per_cohort

        config = V6CorpusConfig(
            base_seed=seed,
            policy_count=actual_count,
            cohort_count=cohort_count,
            policies_per_cohort=policies_per_cohort,
        )
        corpus = generate_v6_corpus(config)

        # 1. Pick latest observation for each policy
        latest_obs: dict[str, V6Observation] = {}
        for obs in corpus.observations:
            pid = obs.policy_id
            if pid not in latest_obs or obs.as_of > latest_obs[pid].as_of:
                latest_obs[pid] = obs

        observations = sorted(latest_obs.values(), key=lambda o: o.policy_id)

        # 2. Score with BundledInferenceEngine
        risk_scores: dict[str, float] = {}
        operational_tiers: dict[str, str] = {}
        for obs in observations:
            feat_map = _feature_map(obs)
            res = self.inference_engine.score_record(feat_map)
            risk_scores[obs.policy_id] = res.calibrated_probability
            operational_tiers[obs.policy_id] = res.risk_tier

        # 3. Evaluate Deterministic Rules Eligibility
        rules_engine = EligibilityRulesEngine()
        eligible_sets: list[EligibleActionSet] = []
        valuations: dict[str, PolicyValuation] = {}
        dpd_map: dict[str, int] = {}

        for obs in observations:
            pid = obs.policy_id
            feats = obs.features
            dpd = int(feats.recent_delay_days or 0)
            dpd_map[pid] = dpd

            try:
                as_of_dt = datetime.fromisoformat(obs.as_of.replace("Z", "+00:00"))
            except Exception:
                as_of_dt = datetime.now(timezone.utc)

            in_grace = (0 < dpd <= 30)
            status = "grace_period" if in_grace else "active"
            ctx = PolicyContext(
                policy_id=pid,
                as_of=as_of_dt,
                status=status,
                tenure_days=feats.tenure_days,
                in_grace_period=in_grace,
                days_past_due=dpd,
                # Explicit fictional clear-state evidence for qualification fixtures.
                has_active_claim=False,
                has_legal_hold=False,
                has_registered_dispute=False,
                sms_opt_out=False,
                email_opt_out=False,
                phone_opt_out=False,
                dnc_registered=False,
            )
            es = rules_engine.evaluate(ctx)

            # Refinement 1: payment remediation requires payment failure or arrears
            if feats.recent_failed_payment_count == 0 and dpd == 0 and "payment_method_remediation" in es.eligible_actions:
                new_res = dict(es.results)
                new_res["payment_method_remediation"] = ActionEligibilityResult(
                    action_type="payment_method_remediation",
                    is_eligible=False,
                    disqualification_reasons=("DISQUALIFIED_NO_PAYMENT_FAILURE",),
                    disqualification_details=("Policy has zero payment failures and zero arrears.",),
                )
                es = EligibleActionSet(
                    policy_id=es.policy_id,
                    as_of=es.as_of,
                    is_frozen=es.is_frozen,
                    freeze_reason=es.freeze_reason,
                    results=new_res,
                    eligible_actions=tuple(a for a in es.eligible_actions if a != "payment_method_remediation"),
                )

            # Refinement 2: Low-risk self cure
            p_risk = risk_scores.get(pid, 0.10)
            if p_risk < 0.15 and not in_grace:
                new_res = dict(es.results)
                for act in es.eligible_actions:
                    if act != "abstain":
                        new_res[act] = ActionEligibilityResult(
                            action_type=act,
                            is_eligible=False,
                            disqualification_reasons=("DISQUALIFIED_LOW_RISK_SELF_CURE",),
                            disqualification_details=("Low baseline hazard (<15%) self-cures without outreach.",),
                        )
                es = EligibleActionSet(
                    policy_id=es.policy_id,
                    as_of=es.as_of,
                    is_frozen=es.is_frozen,
                    freeze_reason=es.freeze_reason,
                    results=new_res,
                    eligible_actions=("abstain",),
                )

            eligible_sets.append(es)
            ann_prem = _calculate_annual_premium_usd(feats)
            valuations[pid] = PolicyValuation(
                policy_id=pid,
                annual_premium_usd=ann_prem,
                customer_lifetime_value_usd=ann_prem * 4.5,
            )

        # 4. Uplift Knapsack Optimization
        optimizer = PortfolioOptimizer(
            specialist_capacity=self.specialist_capacity,
            total_budget_usd=self.budget_cap_usd,
        )
        allocation = optimizer.optimize_portfolio(
            eligible_sets=eligible_sets,
            valuations=valuations,
            risk_scores=risk_scores,
            days_past_due_map=dpd_map,
        )

        # 5. Assemble Case Briefs and Workflow Ledger
        from inforsight_simulator.assistant.context import CaseEvidenceContext

        audit_ledger = AuditLedger()
        workflow = WorkflowService(audit_ledger=audit_ledger)
        assistant = CaseIntelligenceAssistant()

        for rec in allocation.recommendations[:100]:  # Top 100 reviewed into workflow
            pid = rec.policy_id
            obs = latest_obs[pid]
            score_p = risk_scores[pid]
            tier = operational_tiers[pid]
            u_rec = rec.action_utilities.get(rec.recommended_action)
            cost = u_rec.direct_cost_usd if u_rec else 0.0

            brief_ctx = CaseEvidenceContext(
                policy_id=pid,
                as_of_date=obs.as_of,
                case_id=f"case_{pid}",
                product_type="term_life",
                annual_premium=valuations[pid].annual_premium_usd,
                monthly_premium=valuations[pid].annual_premium_usd / 12.0,
                coverage_amount=250000.0,
                tenure_months=int(obs.features.tenure_days / 30),
                total_premiums_paid=valuations[pid].annual_premium_usd,
                policy_status="active",
                in_grace_period=(dpd_map[pid] > 0 and dpd_map[pid] <= 30),
                days_past_due=dpd_map[pid],
                payment_frequency="monthly",
                initial_payment_method="eft",
                risk_class="standard",
                servicing_advisor_id="adv_001",
                has_active_claim=False,
                has_legal_hold=False,
                has_registered_dispute=False,
                calibrated_probability=score_p,
                operational_tier=tier,
                top_risk_drivers=(),
                eligible_actions=tuple(rec.action_utilities.keys()),
                disqualified_actions=(),
                primary_action=rec.recommended_action,
                uplift_quadrant=rec.uplift_quadrant.value if hasattr(rec.uplift_quadrant, "value") else str(rec.uplift_quadrant),
                expected_net_utility=rec.expected_net_utility_usd,
                alternative_actions=(),
                timeline_events=(),
            )
            brief = assistant.generate_brief(
                brief_ctx,
                generated_at=obs.as_of,
                brief_id=f"brief_{pid}",
            )

            case_ctx = workflow.create_case(
                case_id=f"case_{pid}",
                policy_id=pid,
                as_of_date=obs.as_of,
                occurred_at=obs.as_of,
                reconstructed_state={"policy_id": pid, "tenure": obs.features.tenure_days},
                scoring_result={"calibrated_probability": score_p, "operational_tier": tier},
                eligible_action_set={
                    "primary_action": rec.recommended_action,
                    "eligible_actions": list(rec.action_utilities.keys()),
                    "snapshot_id": f"snapshot_{pid}",
                    "safety_evidence_id": f"safety_{pid}",
                    "requirements_version": "safety-action-requirements/1.0.0",
                },
                case_brief=brief.to_dict(),
                model_bundle_id=self.bundle_id,
                action_channels={action: "specialist_crm" for action in rec.action_utilities},
                action_resources={
                    action: ActionResourceRequirement()
                    for action in rec.action_utilities
                },
            )

            # Specialist approves recommendation
            actor = LocalTrustedActorAdapter().attest("usr_qual_001")
            workflow.submit_review(
                case_id=case_ctx.case_id,
                trusted_actor=actor,
                action=SpecialistReviewAction.APPROVE_RECOMMENDATION,
                rationale_code="QUALIFICATION_BASELINE_VERIFICATION",
                occurred_at=obs.as_of,
            )

            # Dispatch approved action
            if rec.recommended_action != "abstain":
                assert case_ctx.approval is not None
                workflow.dispatch_execution(
                    case_id=case_ctx.case_id,
                    trusted_actor=actor,
                    approval_id=case_ctx.approval.approval_id,
                    idempotency_key=case_ctx.approval.idempotency_key,
                    expected_case_version=case_ctx.approval.case_version,
                    current_eligible_action_set=case_ctx.reviewed_eligible_action_set,
                    outreach_reference=f"OUT-{pid}",
                    occurred_at=obs.as_of,
                )

        # Compute deterministic pipeline digest
        ledger_operational_records = [
            {
                "sequence_number": r.sequence_number,
                "case_id": r.case_id,
                "policy_id": r.policy_id,
                "from_state": r.from_state,
                "to_state": r.to_state,
                "decision_context_digest": r.decision_context_digest,
                "human_review": r.human_review,
                "dispatched_action": r.dispatched_action,
            }
            for r in audit_ledger.records
        ]
        summary_payload = {
            "seed": seed,
            "policy_ids": [o.policy_id for o in observations],
            "risk_scores": {k: round(v, 6) for k, v in sorted(risk_scores.items())},
            "allocations": [
                {
                    "policy_id": r.policy_id,
                    "action": r.recommended_action,
                    "utility": round(r.expected_net_utility_usd, 4),
                }
                for r in sorted(allocation.recommendations, key=lambda x: x.policy_id)
            ],
            "ledger_digest": compute_sha256(canonical_json_dumps(ledger_operational_records)),
        }
        pipeline_digest = compute_sha256(canonical_json_dumps(summary_payload))

        return summary_payload, observations, risk_scores, eligible_sets, allocation, audit_ledger

    def run(self) -> SystemQualificationResult:
        """Run the full qualification suite and evaluate all 6 gates."""
        ts_now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Run 1
        summary_1, observations, risk_scores, eligible_sets, allocation, audit_ledger = self._execute_pipeline_run(self.seed)
        digest_1 = compute_sha256(canonical_json_dumps(summary_1))

        # Run 2 (to verify bit-for-bit reproducibility Gate S6)
        summary_2, _, risk_scores_2, _, allocation_2, _ = self._execute_pipeline_run(self.seed)
        digest_2 = compute_sha256(canonical_json_dumps(summary_2))

        identical_allocations = (summary_1["allocations"] == summary_2["allocations"])
        identical_scores = (summary_1["risk_scores"] == summary_2["risk_scores"])

        # Construct valuations & dpd maps for Gate S3
        valuations = {}
        dpd_map = {}
        for obs in observations:
            pid = obs.policy_id
            feats = obs.features
            dpd_map[pid] = int(feats.recent_delay_days or 0)
            ann_prem = _calculate_annual_premium_usd(feats)
            valuations[pid] = PolicyValuation(
                policy_id=pid,
                annual_premium_usd=ann_prem,
                customer_lifetime_value_usd=ann_prem * 4.5,
            )

        # Evaluate Gates S1–S6
        rules_engine = EligibilityRulesEngine()
        sample_obs = observations[0]

        g1 = evaluate_gate_s1_authority_isolation(self.inference_engine, sample_obs)
        g2 = evaluate_gate_s2_eligibility_firewall(rules_engine, observations)
        g3 = evaluate_gate_s3_capacity_adherence(
            eligible_sets=eligible_sets,
            valuations=valuations,
            risk_scores=risk_scores,
            days_past_due_map=dpd_map,
            specialist_capacity=self.specialist_capacity,
            budget_cap_usd=self.budget_cap_usd,
        )
        g4 = evaluate_gate_s4_audit_tamper_resistance()
        g5 = evaluate_gate_s5_latency_sla(self.inference_engine, observations)
        g6 = evaluate_gate_s6_reproducibility(
            digest_run_1=digest_1,
            digest_run_2=digest_2,
            identical_allocations=identical_allocations,
            identical_scores=identical_scores,
        )

        gates = {
            "GATE_S1": g1,
            "GATE_S2": g2,
            "GATE_S3": g3,
            "GATE_S4": g4,
            "GATE_S5": g5,
            "GATE_S6": g6,
        }

        all_passed = all(g.passed for g in gates.values())
        overall_decision = "RELEASE_QUALIFIED" if all_passed else "REJECTED"

        # Triage allocations summary
        action_counts: dict[str, int] = {}
        total_utility = 0.0
        for r in allocation.recommendations:
            action_counts[r.recommended_action] = action_counts.get(r.recommended_action, 0) + 1
            total_utility += r.expected_net_utility_usd

        alloc_summary = {
            "total_policies": len(allocation.recommendations),
            "action_counts": action_counts,
            "total_expected_net_utility_usd": round(total_utility, 2),
            "specialist_capacity_hours": self.specialist_capacity,
            "budget_cap_usd": self.budget_cap_usd,
        }

        perf_summary = {
            "single_p99_latency_ms": g5.details.get("latency_p99_ms"),
            "batch_50_latency_ms": g5.details.get("batch_50_elapsed_ms"),
            "firewall_pass_rate": g2.details.get("firewall_pass_rate"),
            "tamper_detection_rate": g4.details.get("tamper_detection_rate"),
        }

        return SystemQualificationResult(
            seed=self.seed,
            cohort_size=len(observations),
            bundle_id=self.bundle_id,
            bundle_sha256=self.bundle_sha256,
            qualification_timestamp=ts_now,
            gates=gates,
            overall_decision=overall_decision,
            all_gates_passed=all_passed,
            pipeline_digest=digest_1,
            allocations_summary=alloc_summary,
            performance_summary=perf_summary,
        )
