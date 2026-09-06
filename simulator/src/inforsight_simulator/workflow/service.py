"""High-level orchestration service binding workflow state machine to audit ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
import uuid

from inforsight_simulator.audit.ledger import AuditLedger, AuditRecord
from inforsight_simulator.audit.serialization import canonical_json_dumps, compute_sha256
from inforsight_simulator.workflow.models import (
    CaseEvent,
    CaseState,
    DecisionContextDigest,
    HumanReview,
    ReviewDecision,
    SpecialistReviewAction,
    WorkflowError,
)
from inforsight_simulator.workflow.state_machine import CaseStateMachine


@dataclass
class WorkflowContext:
    """Active runtime context for a conservation case."""

    case_id: str
    policy_id: str
    state_machine: CaseStateMachine
    decision_digest: DecisionContextDigest
    recommended_action: str
    eligible_actions: list[str]
    operational_tier: str
    model_score: float
    as_of_date: str
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowService:
    """Service managing conservation case workflows and logging to the audit ledger."""

    def __init__(self, audit_ledger: Optional[AuditLedger] = None) -> None:
        self.ledger = audit_ledger or AuditLedger()
        self._cases: dict[str, WorkflowContext] = {}

    def get_case(self, case_id: str) -> Optional[WorkflowContext]:
        return self._cases.get(case_id)

    def create_case(
        self,
        *,
        policy_id: str,
        as_of_date: str,
        reconstructed_state: dict[str, Any],
        scoring_result: dict[str, Any],
        eligible_action_set: dict[str, Any],
        case_brief: dict[str, Any],
        model_bundle_id: str,
        case_id: Optional[str] = None,
        occurred_at: Optional[str] = None,
    ) -> WorkflowContext:
        """Initializes a new case and advances through TRIAGED, EVIDENCE_ASSEMBLED to RECOMMENDED."""
        cid = case_id or f"case_{uuid.uuid4().hex[:24]}"
        ts = occurred_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Compute decision context digest
        digest = DecisionContextDigest(
            reconstructed_state_sha256=compute_sha256(canonical_json_dumps(reconstructed_state)),
            model_bundle_id=model_bundle_id,
            model_score_sha256=compute_sha256(canonical_json_dumps(scoring_result)),
            eligible_action_set_sha256=compute_sha256(canonical_json_dumps(eligible_action_set)),
            case_brief_sha256=compute_sha256(canonical_json_dumps(case_brief)),
        )

        sm = CaseStateMachine(case_id=cid, policy_id=policy_id)

        # 1. NONE -> CREATED
        ev_created = sm.transition(
            to_state=CaseState.CREATED,
            payload={"as_of_date": as_of_date},
            occurred_at=ts,
        )
        self.ledger.append(
            case_id=cid,
            policy_id=policy_id,
            case_event_id=ev_created.case_event_id,
            from_state=ev_created.from_state.value,
            to_state=ev_created.to_state.value,
            decision_context_digest=digest.to_dict(),
            timestamp=ts,
        )

        # 2. CREATED -> TRIAGED
        ev_triaged = sm.transition(
            to_state=CaseState.TRIAGED,
            payload={
                "scoring_result": {
                    "calibrated_probability": scoring_result.get("calibrated_probability"),
                    "operational_tier": scoring_result.get("operational_tier"),
                    "model_bundle_id": model_bundle_id,
                }
            },
            occurred_at=ts,
        )
        self.ledger.append(
            case_id=cid,
            policy_id=policy_id,
            case_event_id=ev_triaged.case_event_id,
            from_state=ev_triaged.from_state.value,
            to_state=ev_triaged.to_state.value,
            decision_context_digest=digest.to_dict(),
            timestamp=ts,
        )

        # 3. TRIAGED -> EVIDENCE_ASSEMBLED
        ev_evidence = sm.transition(
            to_state=CaseState.EVIDENCE_ASSEMBLED,
            payload={"reconstructed_state_digest": digest.reconstructed_state_sha256},
            occurred_at=ts,
        )
        self.ledger.append(
            case_id=cid,
            policy_id=policy_id,
            case_event_id=ev_evidence.case_event_id,
            from_state=ev_evidence.from_state.value,
            to_state=ev_evidence.to_state.value,
            decision_context_digest=digest.to_dict(),
            timestamp=ts,
        )

        # 4. EVIDENCE_ASSEMBLED -> RECOMMENDED
        recommended_action = eligible_action_set.get("primary_action") or (
            case_brief.get("primary_recommendation", {}).get("action_type") or "abstain"
        )
        eligible_list = eligible_action_set.get("eligible_actions", [recommended_action])
        model_score = float(scoring_result.get("calibrated_probability", 0.0))
        operational_tier = str(scoring_result.get("operational_tier", "TIER_1_LOW"))

        ev_rec = sm.transition(
            to_state=CaseState.RECOMMENDED,
            payload={
                "recommendation": {
                    "action_type": recommended_action,
                    "model_score": model_score,
                    "operational_tier": operational_tier,
                    "authorized_to_act": False,
                },
                "eligible_actions": eligible_list,
            },
            occurred_at=ts,
        )
        self.ledger.append(
            case_id=cid,
            policy_id=policy_id,
            case_event_id=ev_rec.case_event_id,
            from_state=ev_rec.from_state.value,
            to_state=ev_rec.to_state.value,
            decision_context_digest=digest.to_dict(),
            timestamp=ts,
        )

        ctx = WorkflowContext(
            case_id=cid,
            policy_id=policy_id,
            state_machine=sm,
            decision_digest=digest,
            recommended_action=recommended_action,
            eligible_actions=list(eligible_list),
            operational_tier=operational_tier,
            model_score=model_score,
            as_of_date=as_of_date,
        )
        self._cases[cid] = ctx
        return ctx

    def submit_review(
        self,
        *,
        case_id: str,
        reviewer_id: str,
        action: SpecialistReviewAction,
        rationale_code: str,
        justification: Optional[str] = None,
        selected_action: Optional[str] = None,
        occurred_at: Optional[str] = None,
    ) -> CaseEvent:
        """Processes a specialist's review action, validating credentials and eligibility."""
        ctx = self._cases.get(case_id)
        if not ctx:
            raise WorkflowError(f"Case '{case_id}' not found in active workflow contexts")

        ts = occurred_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Map SpecialistReviewAction to ReviewDecision
        if action == SpecialistReviewAction.APPROVE_RECOMMENDATION:
            decision = ReviewDecision.APPROVED
        elif action == SpecialistReviewAction.OVERRIDE_ACTION:
            decision = ReviewDecision.OVERRIDDEN
        elif action == SpecialistReviewAction.REJECT_AND_CLOSE:
            decision = ReviewDecision.REJECTED
        elif action == SpecialistReviewAction.REQUEST_MORE_INFO:
            # Note request in metadata while remaining in RECOMMENDED
            ctx.metadata["review_status"] = "MORE_INFO_REQUESTED"
            ctx.metadata["last_reviewer_id"] = reviewer_id
            ctx.metadata["more_info_justification"] = justification
            return ctx.state_machine.events[-1]
        else:
            raise WorkflowError(f"Unsupported review action: {action}")

        review = HumanReview(
            reviewer_id=reviewer_id,
            reviewed_at=ts,
            decision=decision,
            rationale_code=rationale_code,
            justification=justification,
        )

        event = ctx.state_machine.submit_human_review(
            review=review,
            occurred_at=ts,
            recommended_action=ctx.recommended_action,
            eligible_actions=ctx.eligible_actions,
            selected_action=selected_action,
        )

        self.ledger.append(
            case_id=case_id,
            policy_id=ctx.policy_id,
            case_event_id=event.case_event_id,
            from_state=event.from_state.value,
            to_state=event.to_state.value,
            decision_context_digest=ctx.decision_digest.to_dict(),
            human_review=review.to_dict(),
            timestamp=ts,
        )

        return event

    def dispatch_execution(
        self,
        *,
        case_id: str,
        channel: str,
        outreach_reference: str,
        metadata: Optional[dict[str, Any]] = None,
        occurred_at: Optional[str] = None,
    ) -> CaseEvent:
        """Executes an approved case intervention and records it in the audit ledger."""
        ctx = self._cases.get(case_id)
        if not ctx:
            raise WorkflowError(f"Case '{case_id}' not found in active workflow contexts")

        ts = occurred_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        event = ctx.state_machine.dispatch_execution(
            channel=channel,
            outreach_reference=outreach_reference,
            occurred_at=ts,
            metadata=metadata,
        )

        hr_dict = ctx.state_machine.human_review.to_dict() if ctx.state_machine.human_review else None
        dispatched = event.payload.get("execution_details")

        self.ledger.append(
            case_id=case_id,
            policy_id=ctx.policy_id,
            case_event_id=event.case_event_id,
            from_state=event.from_state.value,
            to_state=event.to_state.value,
            decision_context_digest=ctx.decision_digest.to_dict(),
            human_review=hr_dict,
            dispatched_action=dispatched,
            timestamp=ts,
        )

        return event

    def dismiss_case(
        self,
        *,
        case_id: str,
        reason: str,
        occurred_at: Optional[str] = None,
    ) -> CaseEvent:
        """Dismisses an unselected or rejected case and logs event to audit ledger."""
        ctx = self._cases.get(case_id)
        if not ctx:
            raise WorkflowError(f"Case '{case_id}' not found in active workflow contexts")

        ts = occurred_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        event = ctx.state_machine.dismiss(
            reason=reason,
            occurred_at=ts,
        )

        hr_dict = ctx.state_machine.human_review.to_dict() if ctx.state_machine.human_review else None

        self.ledger.append(
            case_id=case_id,
            policy_id=ctx.policy_id,
            case_event_id=event.case_event_id,
            from_state=event.from_state.value,
            to_state=event.to_state.value,
            decision_context_digest=ctx.decision_digest.to_dict(),
            human_review=hr_dict,
            timestamp=ts,
        )

        return event

    def resolve_case(
        self,
        *,
        case_id: str,
        resolution_notes: str,
        occurred_at: Optional[str] = None,
    ) -> CaseEvent:
        """Resolves an executed or dismissed case and logs terminal event to audit ledger."""
        ctx = self._cases.get(case_id)
        if not ctx:
            raise WorkflowError(f"Case '{case_id}' not found in active workflow contexts")

        ts = occurred_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        event = ctx.state_machine.resolve(
            resolution_notes=resolution_notes,
            occurred_at=ts,
        )

        hr_dict = ctx.state_machine.human_review.to_dict() if ctx.state_machine.human_review else None

        self.ledger.append(
            case_id=case_id,
            policy_id=ctx.policy_id,
            case_event_id=event.case_event_id,
            from_state=event.from_state.value,
            to_state=event.to_state.value,
            decision_context_digest=ctx.decision_digest.to_dict(),
            human_review=hr_dict,
            timestamp=ts,
        )

        return event


