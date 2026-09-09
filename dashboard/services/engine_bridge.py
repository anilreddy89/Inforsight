"""Unified bridge connecting models, rules, optimization, assistant, workflow, and audit ledger."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from inforsight_simulator.assistant import (
    BriefRecommendation,
    CaseBrief,
    CaseEvidenceContext,
    CaseIntelligenceAssistant,
    DisqualifiedActionSummary,
    FactualTimelineEvent,
    OperationalUrgency,
    RiskAssessment,
    RiskDriver,
)
from inforsight_simulator.audit.ledger import AuditLedger
from inforsight_simulator.bundle import BundledInferenceEngine, ModelBundle, ScoringResult
from inforsight_simulator.domain_snapshot import DomainSnapshot
from inforsight_simulator.economics import load_economics_resource_contract
from inforsight_simulator.optimization import (
    OptimalRecommendation,
    PolicyValuation,
    UpliftQuadrant,
    classify_uplift_quadrant,
    evaluate_action_utilities,
    select_best_unconstrained_action,
)
from inforsight_simulator.rules import (
    ConservationActionDefinition,
    EligibilityRulesEngine,
    EligibleActionSet,
    PolicyContext,
)
from inforsight_simulator.semantic_catalog import (
    PREPROCESSING_PROFILE_ID,
    SemanticCatalog,
    load_semantic_catalog,
)
from inforsight_simulator.safety_evidence import SafetyEvidence
from inforsight_simulator.workflow.models import (
    ActionResourceRequirement,
    CaseEvent,
    CaseState,
    SpecialistReviewAction,
)
from inforsight_simulator.workflow.service import (
    LocalTrustedActorAdapter,
    WorkflowContext,
    WorkflowService,
)

from dashboard.config import (
    DEFAULT_BUDGET,
    DEFAULT_AUDIT_LOG_PATH,
    DEFAULT_BUNDLE_PATH,
    DEFAULT_MAX_SPECIALIST_HOURS,
)


class EngineBridge:
    """Central engine bridge coordinating all Phase 1-3 modules for the dashboard."""

    def __init__(
        self,
        bundle_path: Path | str = DEFAULT_BUNDLE_PATH,
        audit_log_path: Path | str = DEFAULT_AUDIT_LOG_PATH,
    ) -> None:
        self.bundle_path = Path(bundle_path)
        self.audit_log_path = Path(audit_log_path)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Load Model Bundle and BundledInferenceEngine
        if not self.bundle_path.exists():
            raise FileNotFoundError(f"Model bundle not found at: {self.bundle_path}")
        self.bundle_sha256 = hashlib.sha256(self.bundle_path.read_bytes()).hexdigest()
        self.bundle = ModelBundle.load(self.bundle_path)
        self.inference_engine = BundledInferenceEngine(self.bundle)
        self.semantic_catalog = load_semantic_catalog()
        self.economics_contract = load_economics_resource_contract(catalog=self.semantic_catalog)

        # 2. Initialize Audit Ledger and Workflow Service
        self.audit_ledger = AuditLedger(log_path=self.audit_log_path)
        self.workflow_service = WorkflowService(
            audit_ledger=self.audit_ledger,
            capacity_hours=DEFAULT_MAX_SPECIALIST_HOURS,
            capacity_cost_usd=DEFAULT_BUDGET,
        )
        self.trusted_actor_adapter = LocalTrustedActorAdapter()

        # 3. Initialize Rules Engine and Assistant
        self.rules_engine = EligibilityRulesEngine()
        self.assistant = CaseIntelligenceAssistant()

    def score_observation(
        self,
        observation_map: Mapping[str, Any],
        *,
        preprocessing_profile: str = PREPROCESSING_PROFILE_ID,
        snapshot: DomainSnapshot | None = None,
        policy_id: str | None = None,
        as_of: datetime | str | None = None,
    ) -> ScoringResult:
        """Scores a single raw observation map with calibrated probability and SHAP decomposition."""
        self.semantic_catalog.require_preprocessing_profile(preprocessing_profile)
        if snapshot is not None:
            if policy_id is None or as_of is None:
                raise ValueError("snapshot scoring requires policy_id and as_of")
            snapshot.validate_context(
                policy_id=policy_id, as_of=as_of, catalog=self.semantic_catalog
            )
        return self.inference_engine.score_record(dict(observation_map))

    def evaluate_eligibility(self, policy_context: PolicyContext) -> EligibleActionSet:
        """Determines legal and regulatory action eligibility under ADR 0002."""
        return self.rules_engine.evaluate(policy_context)

    def evaluate_snapshot(
        self, snapshot: DomainSnapshot, safety_evidence: SafetyEvidence | None = None
    ) -> EligibleActionSet:
        """Evaluate a validated snapshot without coercing unknown facts to permission."""

        return self.rules_engine.evaluate_snapshot(
            snapshot, self.semantic_catalog, safety_evidence
        )

    def optimize_action(
        self,
        eligible_action_set: EligibleActionSet,
        policy_valuation: PolicyValuation,
        calibrated_probability: float,
        days_past_due: int = 0,
    ) -> OptimalRecommendation:
        """Computes cost-utility uplift matrix and selects optimal unconstrained intervention."""
        utilities = evaluate_action_utilities(
            eligible_set=eligible_action_set,
            valuation=policy_valuation,
            lapse_risk_p=calibrated_probability,
            days_past_due=days_past_due,
        )
        return select_best_unconstrained_action(policy_valuation.policy_id, utilities)

    def synthesize_case_brief(
        self,
        policy_id: str,
        as_of_date: str,
        scoring_result: ScoringResult,
        eligible_action_set: EligibleActionSet,
        optimal_rec: OptimalRecommendation,
        policy_context: PolicyContext | None,
        timeline_events: Sequence[Mapping[str, Any]],
        annual_premium: float = 1800.0,
        monthly_premium: float = 150.0,
        coverage_amount: float | None = 250000.0,
        total_premiums_paid: float | None = 2700.0,
        case_id: str = "case_brief_gen",
        snapshot: DomainSnapshot | None = None,
    ) -> CaseBrief:
        """Generates a Grounding Guard-verified CaseBrief for specialist review."""
        # Convert timeline events
        factual_events = [
            FactualTimelineEvent(
                occurred_at=e.get("effective_time") or e.get("occurred_at") or as_of_date,
                event_type=e.get("event_type", "UNKNOWN"),
                summary=e.get("summary", f"Event: {e.get('event_type')}"),
            )
            for e in timeline_events
        ]

        # Convert top risk drivers
        top_drivers = [
            RiskDriver(
                feature_name=driver[0],
                attribution=float(driver[1]),
                display_text=f"{driver[0].replace('_', ' ').title()} ({driver[1]:+.3f})",
            )
            for driver in scoring_result.top_risk_drivers[:4]
        ]

        disqualified_summaries = [
            DisqualifiedActionSummary(
                action_id=action,
                reason_code=res.disqualification_reasons[0] if res.disqualification_reasons else "INELIGIBLE",
                description=res.disqualification_details[0] if res.disqualification_details else "Disqualified by eligibility rules",
            )
            for action, res in eligible_action_set.results.items()
            if not res.is_eligible
        ]

        if snapshot is not None:
            snapshot.validate_context(
                policy_id=policy_id, as_of=as_of_date, catalog=self.semantic_catalog
            )
        if snapshot is None and policy_context is None:
            raise ValueError("snapshot or policy_context is required")
        tenure_days = snapshot.tenure_days if snapshot else policy_context.tenure_days
        tenure_months = max(1, tenure_days // 30)

        evidence = CaseEvidenceContext(
            policy_id=policy_id,
            as_of_date=as_of_date,
            case_id=case_id,
            product_type=snapshot.product_type if snapshot else "term_life",
            annual_premium=annual_premium,
            monthly_premium=monthly_premium,
            coverage_amount=coverage_amount,
            tenure_months=tenure_months,
            total_premiums_paid=total_premiums_paid,
            policy_status=snapshot.status if snapshot else policy_context.status,
            in_grace_period=(
                snapshot.in_grace_period if snapshot else policy_context.in_grace_period
            ),
            days_past_due=snapshot.days_past_due if snapshot else policy_context.days_past_due,
            payment_frequency=snapshot.billing_frequency if snapshot else "monthly",
            initial_payment_method="unknown" if snapshot else "direct_debit",
            risk_class="STANDARD",
            servicing_advisor_id="adv_conservation_pool",
            calibrated_probability=scoring_result.calibrated_probability,
            operational_tier=scoring_result.risk_tier,
            primary_action=optimal_rec.recommended_action,
            uplift_quadrant=optimal_rec.uplift_quadrant.value,
            expected_net_utility=optimal_rec.expected_net_utility_usd,
            timeline_events=tuple(factual_events),
            top_risk_drivers=tuple(top_drivers),
            disqualified_actions=tuple(disqualified_summaries),
            eligible_actions=tuple(eligible_action_set.eligible_actions),
            has_active_claim=(snapshot.safety.has_active_claim if snapshot else policy_context.has_active_claim),
            has_legal_hold=(snapshot.safety.has_legal_hold if snapshot else policy_context.has_legal_hold),
            has_registered_dispute=(snapshot.safety.has_registered_dispute if snapshot else policy_context.has_registered_dispute),
        )

        return self.assistant.generate_brief(evidence)

    def get_or_create_workflow(
        self,
        *,
        policy_id: str,
        as_of_date: str,
        reconstructed_state: Mapping[str, Any],
        scoring_result: ScoringResult,
        eligible_action_set: EligibleActionSet,
        case_brief: CaseBrief,
        case_id: Optional[str] = None,
    ) -> WorkflowContext:
        """Initializes or retrieves the active WorkflowContext advancing to RECOMMENDED."""
        cid = case_id or f"case_{hashlib.md5(f'{policy_id}_{as_of_date}'.encode()).hexdigest()[:24]}"
        existing = self.workflow_service.get_case(cid)
        if existing:
            return existing

        return self.workflow_service.create_case(
            policy_id=policy_id,
            as_of_date=as_of_date,
            reconstructed_state=dict(reconstructed_state),
            scoring_result=scoring_result.to_dict(),
            eligible_action_set={
                "eligible_actions": list(eligible_action_set.eligible_actions),
                "primary_action": case_brief.intervention_recommendations.primary_action,
                "snapshot_id": eligible_action_set.snapshot_id,
                "safety_evidence_id": eligible_action_set.safety_evidence_id,
                "requirements_version": eligible_action_set.requirements_version,
            },
            case_brief=case_brief.to_dict(),
            model_bundle_id=self.bundle.bundle_id,
            action_channels={
                action.action_type: action.channel
                for action in self.rules_engine.action_catalog
                if action.action_type in eligible_action_set.eligible_actions
            },
            action_resources={
                action: ActionResourceRequirement(
                    personnel_hours=self.economics_contract.action(action).personnel_hours,
                    direct_cost_usd=self.economics_contract.action(action).direct_cost_usd,
                )
                for action in eligible_action_set.eligible_actions
            },
            case_id=cid,
        )

    def submit_specialist_decision(
        self,
        case_id: str,
        reviewer_id: str,
        action: SpecialistReviewAction,
        rationale_code: str,
        justification: Optional[str] = None,
        selected_action: Optional[str] = None,
    ) -> tuple[CaseEvent, Optional[CaseEvent]]:
        """Processes human specialist review, records audit entry, and dispatches intervention if approved/overridden."""
        review_event = self.workflow_service.submit_review(
            case_id=case_id,
            trusted_actor=self.trusted_actor_adapter.attest(reviewer_id),
            action=action,
            rationale_code=rationale_code,
            justification=justification,
            selected_action=selected_action,
        )

        exec_event = None
        ctx = self.workflow_service.get_case(case_id)
        if ctx and ctx.state_machine.current_state == CaseState.HUMAN_REVIEWED:
            if action in (
                SpecialistReviewAction.APPROVE_RECOMMENDATION,
                SpecialistReviewAction.OVERRIDE_ACTION,
            ):
                final_action = (
                    selected_action
                    if action == SpecialistReviewAction.OVERRIDE_ACTION
                    else ctx.recommended_action
                )
                approval = ctx.approval
                if approval is None:
                    raise RuntimeError("approved workflow is missing its authority binding")
                exec_event = self.workflow_service.dispatch_execution(
                    case_id=case_id,
                    trusted_actor=self.trusted_actor_adapter.attest(reviewer_id),
                    approval_id=approval.approval_id,
                    idempotency_key=approval.idempotency_key,
                    expected_case_version=approval.case_version,
                    current_eligible_action_set=ctx.reviewed_eligible_action_set,
                    outreach_reference=f"outreach_{case_id}_{final_action}",
                )
            elif action == SpecialistReviewAction.REJECT_AND_CLOSE:
                self.workflow_service.dismiss_case(
                    case_id=case_id,
                    reason=f"Rejected by specialist: {rationale_code}",
                )
                exec_event = self.workflow_service.resolve_case(
                    case_id=case_id,
                    resolution_notes=f"Closed following rejection: {justification or rationale_code}",
                )

        return review_event, exec_event
