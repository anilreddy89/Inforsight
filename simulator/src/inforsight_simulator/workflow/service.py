"""High-level orchestration service binding workflow state machine to audit ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import copy
from pathlib import Path
import threading
from typing import Any, Optional
import uuid

from inforsight_simulator.audit.ledger import AuditLedger
from inforsight_simulator.audit.serialization import canonical_json_dumps, compute_sha256
from inforsight_simulator.workflow.models import (
    ActionResourceRequirement,
    ApprovalBinding,
    AuthorityBoundaryError,
    CaseEvent,
    CaseState,
    DecisionContextDigest,
    HumanReview,
    IneligibleOverrideError,
    ReviewDecision,
    SpecialistReviewAction,
    TrustedActorContext,
    WorkflowError,
)
from inforsight_simulator.workflow.state_machine import CaseStateMachine
from inforsight_simulator.workflow.persistence import (
    WorkflowStateRecoveryError,
    WorkflowStateStore,
)


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
    snapshot_id: str | None
    safety_evidence_id: str | None
    eligibility_digest: str
    requirements_version: str
    recommendation_version: str
    model_bundle_id: str
    action_channels: dict[str, str]
    action_resources: dict[str, ActionResourceRequirement]
    reviewed_eligible_action_set: dict[str, Any]
    case_version: int = 4
    approval: ApprovalBinding | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LocalTrustedActorAdapter:
    """Bounded demo adapter representing identity already authenticated by app context.

    The adapter is trusted local process configuration, not a production identity
    provider. Callers must not construct TrustedActorContext from request JSON.
    """

    def attest(self, actor_id: str) -> TrustedActorContext:
        return TrustedActorContext(
            actor_id=actor_id,
            authenticated=True,
            roles=("conservation_specialist",),
            trust_source="local_streamlit_session",
        )


class WorkflowService:
    """Service managing conservation case workflows and logging to the audit ledger."""

    def __init__(
        self,
        audit_ledger: Optional[AuditLedger] = None,
        *,
        capacity_hours: float = float("inf"),
        capacity_cost_usd: float = float("inf"),
        capacity_seconds: int | None = None,
        capacity_cost_usd_micros: int | None = None,
        approval_ttl_minutes: int = 30,
        state_path: str | Path | None = None,
    ) -> None:
        self.ledger = audit_ledger or AuditLedger()
        self._cases: dict[str, WorkflowContext] = {}
        self._lock = threading.RLock()
        self._remaining_seconds = (
            capacity_seconds
            if capacity_seconds is not None
            else (2**63 - 1 if capacity_hours == float("inf") else int(capacity_hours * 3_600))
        )
        self._remaining_cost_usd_micros = (
            capacity_cost_usd_micros
            if capacity_cost_usd_micros is not None
            else (
                2**63 - 1
                if capacity_cost_usd == float("inf")
                else int(capacity_cost_usd * 1_000_000)
            )
        )
        if self._remaining_seconds < 0 or self._remaining_cost_usd_micros < 0:
            raise ValueError("workflow capacities must be nonnegative")
        self._approval_ttl = timedelta(minutes=approval_ttl_minutes)
        self._execution_results: dict[str, tuple[str, CaseEvent]] = {}
        self._capacity_seconds = self._remaining_seconds
        self._capacity_cost_usd_micros = self._remaining_cost_usd_micros
        self._capacity_version = 1
        self._reservation_version = 0
        self._reservations: dict[str, tuple[str, ActionResourceRequirement]] = {}
        self._state_store = WorkflowStateStore(state_path) if state_path else None
        if self._state_store:
            self._restore_persisted_state()

    def _serialize_state(self) -> dict[str, Any]:
        def event_dict(event: CaseEvent) -> dict[str, Any]:
            return event.to_dict()

        cases = []
        for ctx in self._cases.values():
            cases.append(
                {
                    "case_id": ctx.case_id,
                    "policy_id": ctx.policy_id,
                    "state": ctx.state_machine.current_state.value,
                    "events": [event_dict(event) for event in ctx.state_machine.events],
                    "human_review": (
                        ctx.state_machine.human_review.to_dict()
                        if ctx.state_machine.human_review
                        else None
                    ),
                    "approved_action_type": ctx.state_machine.approved_action_type,
                    "decision_digest": ctx.decision_digest.to_dict(),
                    "recommended_action": ctx.recommended_action,
                    "eligible_actions": ctx.eligible_actions,
                    "operational_tier": ctx.operational_tier,
                    "model_score": ctx.model_score,
                    "as_of_date": ctx.as_of_date,
                    "snapshot_id": ctx.snapshot_id,
                    "safety_evidence_id": ctx.safety_evidence_id,
                    "eligibility_digest": ctx.eligibility_digest,
                    "requirements_version": ctx.requirements_version,
                    "recommendation_version": ctx.recommendation_version,
                    "model_bundle_id": ctx.model_bundle_id,
                    "action_channels": ctx.action_channels,
                    "action_resources": {
                        name: requirement.__dict__
                        for name, requirement in ctx.action_resources.items()
                    },
                    "reviewed_eligible_action_set": ctx.reviewed_eligible_action_set,
                    "case_version": ctx.case_version,
                    "approval": ctx.approval.to_dict() if ctx.approval else None,
                    "metadata": ctx.metadata,
                }
            )
        return {
            "cases": cases,
            "remaining_seconds": self._remaining_seconds,
            "remaining_cost_usd_micros": self._remaining_cost_usd_micros,
            "capacity_version": self._capacity_version,
            "reservation_version": self._reservation_version,
            "capacity_seconds": self._capacity_seconds,
            "capacity_cost_usd_micros": self._capacity_cost_usd_micros,
            "reservations": {
                case_id: {"action_type": action, "requirement": requirement.__dict__}
                for case_id, (action, requirement) in self._reservations.items()
            },
            "execution_results": {
                key: {"digest": digest, "event": event.to_dict()}
                for key, (digest, event) in self._execution_results.items()
            },
        }

    def _restore_state(self, payload: dict[str, Any]) -> None:
        self._cases.clear()
        for raw in payload.get("cases", []):
            sm = CaseStateMachine(
                case_id=raw["case_id"],
                policy_id=raw["policy_id"],
                initial_state=CaseState(raw["state"]),
            )
            sm._events = [
                CaseEvent(
                    case_event_id=event["case_event_id"],
                    case_id=event["case_id"],
                    policy_id=event["policy_id"],
                    from_state=CaseState(event["from_state"]),
                    to_state=CaseState(event["to_state"]),
                    occurred_at=event["occurred_at"],
                    payload=event["payload"],
                    schema_version=event.get("schema_version", "1.0.0"),
                )
                for event in raw["events"]
            ]
            review = raw.get("human_review")
            sm._human_review = (
                HumanReview(
                    reviewer_id=review["reviewer_id"],
                    reviewed_at=review["reviewed_at"],
                    decision=ReviewDecision(review["decision"]),
                    rationale_code=review["rationale_code"],
                    justification=review.get("justification"),
                )
                if review
                else None
            )
            sm._approved_action_type = raw.get("approved_action_type")
            approval = raw.get("approval")
            ctx = WorkflowContext(
                case_id=raw["case_id"],
                policy_id=raw["policy_id"],
                state_machine=sm,
                decision_digest=DecisionContextDigest(**raw["decision_digest"]),
                recommended_action=raw["recommended_action"],
                eligible_actions=list(raw["eligible_actions"]),
                operational_tier=raw["operational_tier"],
                model_score=raw["model_score"],
                as_of_date=raw["as_of_date"],
                snapshot_id=raw.get("snapshot_id"),
                safety_evidence_id=raw.get("safety_evidence_id"),
                eligibility_digest=raw["eligibility_digest"],
                requirements_version=raw["requirements_version"],
                recommendation_version=raw["recommendation_version"],
                model_bundle_id=raw["model_bundle_id"],
                action_channels=dict(raw["action_channels"]),
                action_resources={
                    name: ActionResourceRequirement(**requirement)
                    for name, requirement in raw["action_resources"].items()
                },
                reviewed_eligible_action_set=dict(raw["reviewed_eligible_action_set"]),
                case_version=raw["case_version"],
                approval=ApprovalBinding(**approval) if approval else None,
                metadata=dict(raw.get("metadata", {})),
            )
            self._cases[ctx.case_id] = ctx
        for name in (
            "remaining_seconds", "remaining_cost_usd_micros", "capacity_version",
            "reservation_version", "capacity_seconds", "capacity_cost_usd_micros",
        ):
            setattr(self, f"_{name}", payload[name])
        self._reservations = {
            case_id: (
                item["action_type"],
                ActionResourceRequirement(**item["requirement"]),
            )
            for case_id, item in payload.get("reservations", {}).items()
        }
        self._execution_results = {
            key: (item["digest"], self._event_from_dict(item["event"]))
            for key, item in payload.get("execution_results", {}).items()
        }

    @staticmethod
    def _event_from_dict(event: dict[str, Any]) -> CaseEvent:
        return CaseEvent(
            case_event_id=event["case_event_id"],
            case_id=event["case_id"],
            policy_id=event["policy_id"],
            from_state=CaseState(event["from_state"]),
            to_state=CaseState(event["to_state"]),
            occurred_at=event["occurred_at"],
            payload=event["payload"],
            schema_version=event.get("schema_version", "1.0.0"),
        )

    def _restore_persisted_state(self) -> None:
        assert self._state_store is not None
        stored = self._state_store.load()
        if not stored:
            return
        pending = stored.get("pending")
        selected = stored["committed"]
        if pending:
            committed_event_ids = {record.case_event_id for record in self.ledger.records}
            if pending["audit_entry_id"] in committed_event_ids:
                selected = pending["target"]
        self._restore_state(selected)
        if self.ledger.log_path:
            audit_event_ids = {record.case_event_id for record in self.ledger.records}
            missing = {
                event.case_event_id
                for ctx in self._cases.values()
                for event in ctx.state_machine.events
                if event.case_event_id not in audit_event_ids
            }
            if missing:
                raise WorkflowStateRecoveryError(
                    "workflow state references audit events absent from the durable ledger"
                )

    def _persist_committed(self) -> None:
        if self._state_store:
            self._state_store.commit(self._serialize_state())

    def _begin_pending(self, committed: dict[str, Any], target: dict[str, Any], event: CaseEvent) -> None:
        if self._state_store:
            self._state_store.begin(
                committed=committed,
                target=target,
                audit_entry_id=event.case_event_id,
            )

    def capacity_snapshot(self) -> dict[str, int]:
        """Return one lock-consistent exact-capacity and reservation snapshot."""
        with self._lock:
            return {
                "capacity_version": self._capacity_version,
                "reservation_version": self._reservation_version,
                "capacity_seconds": self._capacity_seconds,
                "remaining_seconds": self._remaining_seconds,
                "capacity_cost_usd_micros": self._capacity_cost_usd_micros,
                "remaining_cost_usd_micros": self._remaining_cost_usd_micros,
            }

    def _replacement_resources(
        self,
        *,
        case_id: str,
        action_type: str | None,
        requirement: ActionResourceRequirement | None,
        expected_capacity_version: int,
    ) -> tuple[int, int]:
        if expected_capacity_version != self._capacity_version:
            raise AuthorityBoundaryError(
                "CAPACITY_VERSION_CONFLICT", "capacity version changed before reservation"
            )
        old = self._reservations.get(case_id)
        old_requirement = old[1] if old else ActionResourceRequirement()
        new_requirement = requirement or ActionResourceRequirement()
        available_seconds = self._remaining_seconds + old_requirement.personnel_seconds
        available_micros = (
            self._remaining_cost_usd_micros + old_requirement.direct_cost_usd_micros
        )
        if (
            new_requirement.personnel_seconds > available_seconds
            or new_requirement.direct_cost_usd_micros > available_micros
        ):
            raise AuthorityBoundaryError(
                "CAPACITY_EXCEEDED", "replacement exceeds current exact resource capacity"
            )
        return (
            available_seconds - new_requirement.personnel_seconds,
            available_micros - new_requirement.direct_cost_usd_micros,
        )

    def replace_reservation(
        self,
        *,
        case_id: str,
        action_type: str | None,
        requirement: ActionResourceRequirement | None,
        expected_capacity_version: int,
    ) -> dict[str, int]:
        """Atomically release an old reservation and reserve its replacement."""
        with self._lock:
            remaining_seconds, remaining_micros = self._replacement_resources(
                case_id=case_id,
                action_type=action_type,
                requirement=requirement,
                expected_capacity_version=expected_capacity_version,
            )
            self._remaining_seconds = remaining_seconds
            self._remaining_cost_usd_micros = remaining_micros
            if action_type is None or requirement is None:
                self._reservations.pop(case_id, None)
            else:
                self._reservations[case_id] = (action_type, requirement)
            self._capacity_version += 1
            self._reservation_version += 1
            return self.capacity_snapshot()

    def get_case(self, case_id: str) -> Optional[WorkflowContext]:
        return self._cases.get(case_id)

    def _snapshot_mutation_state(self, ctx: WorkflowContext) -> dict[str, Any]:
        """Capture local state before an audit handoff can commit or fail."""
        return {
            "state": ctx.state_machine._current_state,
            "events": list(ctx.state_machine._events),
            "human_review": ctx.state_machine._human_review,
            "approved_action_type": ctx.state_machine._approved_action_type,
            "case_version": ctx.case_version,
            "approval": ctx.approval,
            "metadata": copy.deepcopy(ctx.metadata),
            "remaining_seconds": self._remaining_seconds,
            "remaining_cost_usd_micros": self._remaining_cost_usd_micros,
            "capacity_version": self._capacity_version,
            "reservation_version": self._reservation_version,
            "reservations": copy.deepcopy(self._reservations),
        }

    def _restore_mutation_state(self, ctx: WorkflowContext, snapshot: dict[str, Any]) -> None:
        """Restore uncommitted local state after a failed audit handoff."""
        ctx.state_machine._current_state = snapshot["state"]
        ctx.state_machine._events = snapshot["events"]
        ctx.state_machine._human_review = snapshot["human_review"]
        ctx.state_machine._approved_action_type = snapshot["approved_action_type"]
        ctx.case_version = snapshot["case_version"]
        ctx.approval = snapshot["approval"]
        ctx.metadata = snapshot["metadata"]
        self._remaining_seconds = snapshot["remaining_seconds"]
        self._remaining_cost_usd_micros = snapshot["remaining_cost_usd_micros"]
        self._capacity_version = snapshot["capacity_version"]
        self._reservation_version = snapshot["reservation_version"]
        self._reservations = snapshot["reservations"]

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
        action_channels: Optional[dict[str, str]] = None,
        action_resources: Optional[dict[str, ActionResourceRequirement]] = None,
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
            snapshot_id=eligible_action_set.get("snapshot_id"),
            safety_evidence_id=eligible_action_set.get("safety_evidence_id"),
            eligibility_digest=digest.eligible_action_set_sha256,
            requirements_version=str(eligible_action_set["requirements_version"]),
            recommendation_version=compute_sha256(canonical_json_dumps(case_brief)),
            model_bundle_id=model_bundle_id,
            action_channels=dict(action_channels or {}),
            action_resources=dict(action_resources or {}),
            reviewed_eligible_action_set=dict(eligible_action_set),
        )
        self._cases[cid] = ctx
        self._persist_committed()
        return ctx

    def submit_review(
        self,
        **kwargs: Any,
    ) -> CaseEvent:
        """Serialize review, eligibility revalidation, and reservation replacement."""
        with self._lock:
            return self._submit_review_locked(**kwargs)

    def _submit_review_locked(
        self,
        *,
        case_id: str,
        trusted_actor: TrustedActorContext,
        action: SpecialistReviewAction,
        rationale_code: str,
        justification: Optional[str] = None,
        selected_action: Optional[str] = None,
        expected_capacity_version: int | None = None,
        occurred_at: Optional[str] = None,
    ) -> CaseEvent:
        """Processes a specialist review using identity supplied by trusted server context."""
        ctx = self._cases.get(case_id)
        if not ctx:
            raise WorkflowError(f"Case '{case_id}' not found in active workflow contexts")

        if (
            action == SpecialistReviewAction.APPROVE_RECOMMENDATION
            and ctx.recommended_action not in ctx.eligible_actions
        ):
            raise IneligibleOverrideError(
                f"Recommended action '{ctx.recommended_action}' is unavailable for approval"
            )

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
            ctx.metadata["last_reviewer_id"] = trusted_actor.actor_id
            ctx.metadata["more_info_justification"] = justification
            return ctx.state_machine.events[-1]
        else:
            raise WorkflowError(f"Unsupported review action: {action}")

        if decision == ReviewDecision.APPROVED:
            chosen_action = ctx.recommended_action
        elif decision == ReviewDecision.OVERRIDDEN:
            if selected_action is None or selected_action not in ctx.eligible_actions:
                raise IneligibleOverrideError(
                    f"Specialist override action '{selected_action}' is disqualified"
                )
            chosen_action = selected_action
        else:
            chosen_action = "abstain"
        if decision in (ReviewDecision.APPROVED, ReviewDecision.OVERRIDDEN):
            for name in ("snapshot_id", "safety_evidence_id", "requirements_version"):
                if not getattr(ctx, name):
                    raise AuthorityBoundaryError(
                        "AUTH_EVIDENCE_UNBOUND", f"approval requires {name}"
                    )
            if chosen_action not in ctx.action_resources:
                raise AuthorityBoundaryError(
                    "AUTH_RESOURCE_UNBOUND",
                    f"action '{chosen_action}' has no authoritative resource requirement",
                )
        channel = ctx.action_channels.get(
            chosen_action, "none" if chosen_action == "abstain" else "unknown"
        )
        if decision in (ReviewDecision.APPROVED, ReviewDecision.OVERRIDDEN) and channel == "unknown":
                raise AuthorityBoundaryError(
                    "AUTH_CHANNEL_UNBOUND", f"action '{chosen_action}' has no authoritative channel"
                )

        reservation_requirement = (
            ctx.action_resources[chosen_action]
            if decision in (ReviewDecision.APPROVED, ReviewDecision.OVERRIDDEN)
            else None
        )
        reservation_version = expected_capacity_version
        # Preflight while holding the same lock used by commit. No resource is
        # released when the expected version is stale or the replacement fails.
        if reservation_version is not None:
            self._replacement_resources(
                case_id=case_id,
                action_type=(chosen_action if reservation_requirement else None),
                requirement=reservation_requirement,
                expected_capacity_version=reservation_version,
            )

        review = HumanReview(
            reviewer_id=trusted_actor.actor_id,
            reviewed_at=ts,
            decision=decision,
            rationale_code=rationale_code,
            justification=justification,
        )

        snapshot = self._snapshot_mutation_state(ctx)
        committed_state = self._serialize_state()
        audit_committed = False
        try:
            event = ctx.state_machine.submit_human_review(
                review=review,
                occurred_at=ts,
                recommended_action=ctx.recommended_action,
                eligible_actions=ctx.eligible_actions,
                selected_action=selected_action,
            )

            ctx.case_version += 1
            expiry = (
                datetime.fromisoformat(ts.replace("Z", "+00:00")) + self._approval_ttl
            ).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            approval_seed = compute_sha256(
                canonical_json_dumps(
                    {
                        "case_id": case_id,
                        "case_version": ctx.case_version,
                        "eligibility_digest": ctx.eligibility_digest,
                        "action_type": chosen_action,
                        "channel": channel,
                        "actor_id": trusted_actor.actor_id,
                        "reviewed_at": ts,
                    }
                )
            )
            ctx.approval = ApprovalBinding(
                approval_id=f"apr_{approval_seed[:24]}",
                case_id=case_id,
                case_version=ctx.case_version,
                snapshot_id=ctx.snapshot_id or "unavailable",
                safety_evidence_id=ctx.safety_evidence_id or "unavailable",
                eligibility_digest=ctx.eligibility_digest,
                requirements_version=ctx.requirements_version,
                action_type=chosen_action,
                channel=channel,
                recommendation_version=ctx.recommendation_version,
                model_bundle_id=ctx.model_bundle_id,
                actor_id=trusted_actor.actor_id,
                reviewed_at=ts,
                expires_at=expiry,
                idempotency_key=f"exec_{approval_seed[24:48]}",
            )

            if reservation_version is not None:
                self.replace_reservation(
                    case_id=case_id,
                    action_type=(chosen_action if reservation_requirement else None),
                    requirement=reservation_requirement,
                    expected_capacity_version=reservation_version,
                )
            self._begin_pending(committed_state, self._serialize_state(), event)
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
            audit_committed = True
            self._persist_committed()
            return event
        except Exception:
            self._restore_mutation_state(ctx, snapshot)
            if self._state_store and not audit_committed:
                self._state_store.rollback(committed_state)
            raise

    def dispatch_execution(
        self,
        *,
        case_id: str,
        trusted_actor: TrustedActorContext,
        approval_id: str,
        idempotency_key: str,
        expected_case_version: int,
        current_eligible_action_set: dict[str, Any],
        outreach_reference: str,
        metadata: Optional[dict[str, Any]] = None,
        occurred_at: Optional[str] = None,
    ) -> CaseEvent:
        """Common atomic boundary for every intervention execution path."""
        ts = occurred_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        request_digest = compute_sha256(
            canonical_json_dumps(
                {
                    "case_id": case_id,
                    "approval_id": approval_id,
                    "expected_case_version": expected_case_version,
                    "current_eligible_action_set": current_eligible_action_set,
                    "outreach_reference": outreach_reference,
                    "metadata": metadata or {},
                }
            )
        )

        with self._lock:
            prior = self._execution_results.get(idempotency_key)
            if prior:
                if prior[0] != request_digest:
                    raise AuthorityBoundaryError(
                        "AUTH_IDEMPOTENCY_CONFLICT",
                        "idempotency key was reused with different input",
                    )
                return prior[1]

            ctx = self._cases.get(case_id)
            if not ctx:
                raise WorkflowError(f"Case '{case_id}' not found in active workflow contexts")
            approval = ctx.approval
            if approval is None:
                raise AuthorityBoundaryError("AUTH_APPROVAL_MISSING", "case has no bound approval")
            if approval.approval_id != approval_id or approval.idempotency_key != idempotency_key:
                raise AuthorityBoundaryError(
                    "AUTH_APPROVAL_MISMATCH",
                    "approval or idempotency identity does not match",
                )
            if approval.actor_id != trusted_actor.actor_id:
                raise AuthorityBoundaryError("AUTH_ACTOR_MISMATCH", "executing actor differs from approving actor")
            if approval.is_expired_at(ts):
                raise AuthorityBoundaryError("AUTH_APPROVAL_EXPIRED", "approval has expired")
            if ctx.case_version != expected_case_version or approval.case_version != expected_case_version:
                raise AuthorityBoundaryError(
                    "AUTH_CASE_VERSION_STALE",
                    "case version differs from approved version",
                )

            current_digest = compute_sha256(canonical_json_dumps(current_eligible_action_set))
            current_actions = current_eligible_action_set.get("eligible_actions", [])
            identity_fields = {
                "snapshot_id": approval.snapshot_id,
                "safety_evidence_id": approval.safety_evidence_id,
                "requirements_version": approval.requirements_version,
            }
            if any(current_eligible_action_set.get(k) != v for k, v in identity_fields.items()):
                raise AuthorityBoundaryError(
                    "AUTH_EVIDENCE_STALE",
                    "current evidence identity differs from reviewed evidence",
                )
            if current_digest != approval.eligibility_digest or approval.action_type not in current_actions:
                raise AuthorityBoundaryError(
                    "AUTH_ELIGIBILITY_STALE",
                    "current eligibility differs from reviewed eligibility",
                )

            requirement = ctx.action_resources.get(approval.action_type, ActionResourceRequirement())
            reserved = self._reservations.get(case_id)
            if reserved is None:
                try:
                    self._replacement_resources(
                        case_id=case_id,
                        action_type=approval.action_type,
                        requirement=requirement,
                        expected_capacity_version=self._capacity_version,
                    )
                except AuthorityBoundaryError as exc:
                    if exc.code == "CAPACITY_EXCEEDED":
                        raise AuthorityBoundaryError(
                            "AUTH_CAPACITY_EXHAUSTED",
                            "insufficient hours or money for approved action",
                        ) from exc
                    raise
            if reserved is not None and reserved[0] != approval.action_type:
                raise AuthorityBoundaryError(
                    "STALE_ALLOCATION", "approved action lacks its exact current reservation"
                )

            protected = {"action_type", "channel", "reviewer_id", "approval_id", "case_version"}
            if protected.intersection(metadata or {}):
                raise AuthorityBoundaryError(
                    "AUTH_METADATA_OVERRIDE",
                    "caller metadata contains protected authority fields",
                )

            snapshot = self._snapshot_mutation_state(ctx)
            committed_state = self._serialize_state()
            audit_committed = False
            try:
                event = ctx.state_machine._prepare_execution(
                    channel=approval.channel,
                    outreach_reference=outreach_reference,
                    occurred_at=ts,
                    metadata=metadata,
                )
                hr_dict = (
                    ctx.state_machine.human_review.to_dict()
                    if ctx.state_machine.human_review
                    else None
                )
                dispatched = event.payload.get("execution_details")
                if reserved is None:
                    self.replace_reservation(
                        case_id=case_id,
                        action_type=approval.action_type,
                        requirement=requirement,
                        expected_capacity_version=self._capacity_version,
                    )
                ctx.state_machine._record_prepared_execution(event)
                ctx.case_version += 1
                self._execution_results[idempotency_key] = (request_digest, event)
                self._begin_pending(committed_state, self._serialize_state(), event)
                self.ledger.append(
                    case_id=case_id,
                    policy_id=ctx.policy_id,
                    case_event_id=event.case_event_id,
                    from_state=event.from_state.value,
                    to_state=event.to_state.value,
                    decision_context_digest=ctx.decision_digest.to_dict(),
                    human_review=hr_dict,
                    dispatched_action=dispatched,
                    metadata={"approval_binding": approval.to_dict()},
                    timestamp=ts,
                )
                audit_committed = True
                self._persist_committed()
                return event
            except Exception:
                self._restore_mutation_state(ctx, snapshot)
                if self._state_store and not audit_committed:
                    self._state_store.rollback(committed_state)
                raise

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

        snapshot = self._snapshot_mutation_state(ctx)
        committed_state = self._serialize_state()
        audit_committed = False
        try:
            event = ctx.state_machine.dismiss(reason=reason, occurred_at=ts)
            hr_dict = ctx.state_machine.human_review.to_dict() if ctx.state_machine.human_review else None
            self._begin_pending(committed_state, self._serialize_state(), event)
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
            audit_committed = True
            self._persist_committed()
            return event
        except Exception:
            self._restore_mutation_state(ctx, snapshot)
            if self._state_store and not audit_committed:
                self._state_store.rollback(committed_state)
            raise

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

        snapshot = self._snapshot_mutation_state(ctx)
        committed_state = self._serialize_state()
        audit_committed = False
        try:
            event = ctx.state_machine.resolve(
                resolution_notes=resolution_notes,
                occurred_at=ts,
            )
            hr_dict = ctx.state_machine.human_review.to_dict() if ctx.state_machine.human_review else None
            self._begin_pending(committed_state, self._serialize_state(), event)
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
            audit_committed = True
            self._persist_committed()
            return event
        except Exception:
            self._restore_mutation_state(ctx, snapshot)
            if self._state_store and not audit_committed:
                self._state_store.rollback(committed_state)
            raise
