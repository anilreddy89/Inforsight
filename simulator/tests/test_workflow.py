"""Unit and invariant tests for HITL conservation case workflow engine."""

from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor

from inforsight_simulator.audit.ledger import AuditLedger
from inforsight_simulator.workflow.models import (
    ActionResourceRequirement,
    AuthorityBoundaryError,
    CaseEvent,
    CaseState,
    HumanReview,
    IneligibleOverrideError,
    InvalidReviewerCredentialsError,
    InvalidTransitionError,
    MissingJustificationError,
    ReviewDecision,
    SpecialistReviewAction,
    TrustedActorContext,
    UnauthorizedExecutionError,
)
from inforsight_simulator.workflow.service import WorkflowService
from inforsight_simulator.workflow.state_machine import CaseStateMachine


class TestWorkflowStateMachine(unittest.TestCase):
    """Tests deterministic state transitions and hard governance invariant checks."""

    def setUp(self) -> None:
        self.case_id = "case_01918a2b3c4d5e6f7a8b9c0d"
        self.policy_id = "pol_a1b2c3d4e5f60718"
        self.sm = CaseStateMachine(case_id=self.case_id, policy_id=self.policy_id)

    def test_happy_path_lifecycle(self) -> None:
        """Verifies full standard lifecycle through approval, execution, and resolution."""
        # NONE -> CREATED
        self.sm.transition(CaseState.CREATED, {}, "2026-09-01T08:00:00Z")
        self.assertEqual(self.sm.current_state, CaseState.CREATED)

        # CREATED -> TRIAGED
        self.sm.transition(CaseState.TRIAGED, {}, "2026-09-01T08:05:00Z")
        self.assertEqual(self.sm.current_state, CaseState.TRIAGED)

        # TRIAGED -> EVIDENCE_ASSEMBLED
        self.sm.transition(CaseState.EVIDENCE_ASSEMBLED, {}, "2026-09-01T08:10:00Z")
        self.assertEqual(self.sm.current_state, CaseState.EVIDENCE_ASSEMBLED)

        # EVIDENCE_ASSEMBLED -> RECOMMENDED
        self.sm.transition(
            CaseState.RECOMMENDED,
            {
                "recommendation": {
                    "action_type": "grace_period_consultation",
                    "model_score": 0.45,
                    "operational_tier": "TIER_3_HIGH",
                    "authorized_to_act": False,
                }
            },
            "2026-09-01T08:15:00Z",
        )
        self.assertEqual(self.sm.current_state, CaseState.RECOMMENDED)

        # Specialist Review (Approve)
        review = HumanReview(
            reviewer_id="usr_specialist_01",
            reviewed_at="2026-09-01T09:00:00Z",
            decision=ReviewDecision.APPROVED,
            rationale_code="APPROVE_OPTIMAL_RECOMMENDATION",
        )
        ev_review = self.sm.submit_human_review(
            review=review,
            occurred_at="2026-09-01T09:00:00Z",
            recommended_action="grace_period_consultation",
            eligible_actions=["grace_period_consultation", "courtesy_reminder"],
        )
        self.assertEqual(self.sm.current_state, CaseState.HUMAN_REVIEWED)
        self.assertEqual(ev_review.to_state, CaseState.HUMAN_REVIEWED)
        self.assertEqual(self.sm.approved_action_type, "grace_period_consultation")

        # Dispatch Execution
        ev_exec = self.sm._commit_execution(
            channel="phone",
            outreach_reference="out_99281726",
            occurred_at="2026-09-01T09:15:00Z",
        )
        self.assertEqual(self.sm.current_state, CaseState.EXECUTED)
        self.assertEqual(ev_exec.payload["execution_details"]["action_type"], "grace_period_consultation")

        # Resolve Case
        ev_res = self.sm.resolve("Outreach completed successfully.", "2026-09-01T10:00:00Z")
        self.assertEqual(self.sm.current_state, CaseState.RESOLVED)
        self.assertEqual(len(self.sm.events), 7)

    def test_adr_0002_autonomous_execution_blocked(self) -> None:
        """Asserts that direct transition from RECOMMENDED to EXECUTED is strictly blocked."""
        # Advance to RECOMMENDED
        self.sm.transition(CaseState.CREATED, {}, "2026-09-01T08:00:00Z")
        self.sm.transition(CaseState.TRIAGED, {}, "2026-09-01T08:05:00Z")
        self.sm.transition(CaseState.EVIDENCE_ASSEMBLED, {}, "2026-09-01T08:10:00Z")
        self.sm.transition(CaseState.RECOMMENDED, {}, "2026-09-01T08:15:00Z")

        # Attempt direct autonomous execution without human review
        with self.assertRaises(UnauthorizedExecutionError) as cm:
            self.sm.transition(CaseState.EXECUTED, {}, "2026-09-01T08:20:00Z")
        self.assertIn("ADR 0002", str(cm.exception))
        self.assertIn("generic transition API", str(cm.exception))

    def test_invalid_arbitrary_transitions_rejected(self) -> None:
        """Verifies that invalid transitions violate state machine graph."""
        # Direct jump from NONE to EXECUTED
        with self.assertRaises(UnauthorizedExecutionError):
            self.sm.transition(CaseState.EXECUTED, {}, "2026-09-01T08:00:00Z")

        # Jump from CREATED to RESOLVED
        self.sm.transition(CaseState.CREATED, {}, "2026-09-01T08:00:00Z")
        with self.assertRaises(InvalidTransitionError):
            self.sm.transition(CaseState.RESOLVED, {}, "2026-09-01T08:05:00Z")

    def test_override_action_eligibility_enforcement(self) -> None:
        """Verifies that specialist overrides must be in the eligible action set."""
        # Advance to RECOMMENDED
        self.sm.transition(CaseState.CREATED, {}, "2026-09-01T08:00:00Z")
        self.sm.transition(CaseState.TRIAGED, {}, "2026-09-01T08:05:00Z")
        self.sm.transition(CaseState.EVIDENCE_ASSEMBLED, {}, "2026-09-01T08:10:00Z")
        self.sm.transition(CaseState.RECOMMENDED, {}, "2026-09-01T08:15:00Z")

        eligible = ["courtesy_reminder", "grace_period_consultation"]

        # 1. Override with disqualified action (e.g. specialist_phone_outreach)
        review_disqualified = HumanReview(
            reviewer_id="usr_specialist_02",
            reviewed_at="2026-09-01T09:00:00Z",
            decision=ReviewDecision.OVERRIDDEN,
            rationale_code="OVERRIDE_SPECIALIST_PREFERENCE",
            justification="Policyholder prefers telephone outreach directly.",
        )
        with self.assertRaises(IneligibleOverrideError) as cm:
            self.sm.submit_human_review(
                review=review_disqualified,
                occurred_at="2026-09-01T09:00:00Z",
                recommended_action="courtesy_reminder",
                eligible_actions=eligible,
                selected_action="specialist_phone_outreach",
            )
        self.assertIn("disqualified", str(cm.exception))

        # 2. Override with eligible action succeeds
        review_valid = HumanReview(
            reviewer_id="usr_specialist_02",
            reviewed_at="2026-09-01T09:00:00Z",
            decision=ReviewDecision.OVERRIDDEN,
            rationale_code="OVERRIDE_SPECIALIST_PREFERENCE",
            justification="Consultation preferred over simple reminder.",
        )
        self.sm.submit_human_review(
            review=review_valid,
            occurred_at="2026-09-01T09:00:00Z",
            recommended_action="courtesy_reminder",
            eligible_actions=eligible,
            selected_action="grace_period_consultation",
        )
        self.assertEqual(self.sm.approved_action_type, "grace_period_consultation")

    def test_reviewer_credentials_and_justification_rules(self) -> None:
        """Verifies reviewer ID regex and mandatory justification length."""
        # Invalid reviewer ID
        with self.assertRaises(InvalidReviewerCredentialsError):
            HumanReview(
                reviewer_id="invalid_user_format",
                reviewed_at="2026-09-01T09:00:00Z",
                decision=ReviewDecision.APPROVED,
                rationale_code="APPROVE_DEFAULT",
            )

        # Override missing justification
        with self.assertRaises(MissingJustificationError):
            HumanReview(
                reviewer_id="usr_valid_01",
                reviewed_at="2026-09-01T09:00:00Z",
                decision=ReviewDecision.OVERRIDDEN,
                rationale_code="OVERRIDE_RATIONALE",
                justification=None,
            )

        # Override justification too short (< 5 chars)
        with self.assertRaises(MissingJustificationError):
            HumanReview(
                reviewer_id="usr_valid_01",
                reviewed_at="2026-09-01T09:00:00Z",
                decision=ReviewDecision.OVERRIDDEN,
                rationale_code="OVERRIDE_RATIONALE",
                justification="bad",
            )

    def test_rejection_and_dismissal(self) -> None:
        """Verifies rejecting an action routes to DISMISSED and cannot be EXECUTED."""
        # Advance to RECOMMENDED
        self.sm.transition(CaseState.CREATED, {}, "2026-09-01T08:00:00Z")
        self.sm.transition(CaseState.TRIAGED, {}, "2026-09-01T08:05:00Z")
        self.sm.transition(CaseState.EVIDENCE_ASSEMBLED, {}, "2026-09-01T08:10:00Z")
        self.sm.transition(CaseState.RECOMMENDED, {}, "2026-09-01T08:15:00Z")

        reject_review = HumanReview(
            reviewer_id="usr_senior_lead",
            reviewed_at="2026-09-01T09:00:00Z",
            decision=ReviewDecision.REJECTED,
            rationale_code="REJECT_KNOWN_COMPLAINT_HOLD",
            justification="Account has pending billing adjustment query; do not disturb.",
        )
        self.sm.submit_human_review(
            review=reject_review,
            occurred_at="2026-09-01T09:00:00Z",
            recommended_action="grace_period_consultation",
            eligible_actions=["grace_period_consultation"],
        )
        self.assertEqual(self.sm.current_state, CaseState.HUMAN_REVIEWED)

        # Attempt to dispatch execution on rejected review must raise error
        with self.assertRaises(UnauthorizedExecutionError):
            self.sm.transition(CaseState.EXECUTED, {}, "2026-09-01T09:10:00Z")

        # Dismissal succeeds
        self.sm.dismiss("Rejected by specialist.", "2026-09-01T09:15:00Z")
        self.assertEqual(self.sm.current_state, CaseState.DISMISSED)

        # Final resolve
        self.sm.resolve("Case closed following dismissal.", "2026-09-01T09:30:00Z")
        self.assertEqual(self.sm.current_state, CaseState.RESOLVED)


class TestWorkflowService(unittest.TestCase):
    """Tests high-level WorkflowService binding state machine and audit ledger."""

    @staticmethod
    def actor(actor_id: str = "usr_evaluator_99") -> TrustedActorContext:
        return TrustedActorContext(
            actor_id=actor_id,
            authenticated=True,
            roles=("conservation_specialist",),
            trust_source="unit_test",
        )

    @staticmethod
    def eligible(*actions: str, primary: str) -> dict[str, object]:
        return {
            "primary_action": primary,
            "eligible_actions": list(actions),
            "snapshot_id": "snapshot_test_001",
            "safety_evidence_id": "safety_test_001",
            "requirements_version": "safety-action-requirements/1.0.0",
        }

    def approved_case(
        self,
        service: WorkflowService,
        *,
        case_id: str = "case_authority000000000001",
        reviewed_at: str = "2026-09-01T10:15:00Z",
    ):
        eligible = self.eligible("grace_period_consultation", primary="grace_period_consultation")
        ctx = service.create_case(
            case_id=case_id,
            policy_id="pol_authority000000000001",
            as_of_date="2026-09-01",
            reconstructed_state={"status": "in_force"},
            scoring_result={"calibrated_probability": 0.38, "operational_tier": "TIER_3_HIGH"},
            eligible_action_set=eligible,
            case_brief={"primary_recommendation": {"action_type": "grace_period_consultation"}},
            model_bundle_id="model_test_v1",
            action_channels={"grace_period_consultation": "phone"},
            action_resources={
                "grace_period_consultation": ActionResourceRequirement(0.5, 20.0)
            },
            occurred_at="2026-09-01T10:00:00Z",
        )
        service.submit_review(
            case_id=ctx.case_id,
            trusted_actor=self.actor(),
            action=SpecialistReviewAction.APPROVE_RECOMMENDATION,
            rationale_code="APPROVE_RECOMMENDED_ACTION",
            occurred_at=reviewed_at,
        )
        assert ctx.approval is not None
        return ctx

    def test_workflow_service_lifecycle(self) -> None:
        service = WorkflowService()

        # Create case
        ctx = service.create_case(
            policy_id="pol_839281726354",
            as_of_date="2026-09-01",
            reconstructed_state={"tenure_months": 14, "annual_premium": 1200.0},
            scoring_result={"calibrated_probability": 0.38, "operational_tier": "TIER_3_HIGH"},
            eligible_action_set=self.eligible(
                "grace_period_consultation", "courtesy_reminder",
                primary="grace_period_consultation",
            ),
            case_brief={"primary_recommendation": {"action_type": "grace_period_consultation"}},
            model_bundle_id="inforsight-v6-logistic-platt-20260817",
            action_channels={
                "grace_period_consultation": "phone",
                "courtesy_reminder": "email",
            },
            action_resources={
                "grace_period_consultation": ActionResourceRequirement(0.5, 20.0),
                "courtesy_reminder": ActionResourceRequirement(0.1, 2.0),
            },
            occurred_at="2026-09-01T10:00:00Z",
        )
        self.assertEqual(ctx.state_machine.current_state, CaseState.RECOMMENDED)
        self.assertEqual(service.ledger.total_entries, 4)

        # Submit review
        ev_rev = service.submit_review(
            case_id=ctx.case_id,
            trusted_actor=self.actor(),
            action=SpecialistReviewAction.APPROVE_RECOMMENDATION,
            rationale_code="APPROVE_RECOMMENDED_ACTION",
            justification="Standard procedure followed.",
            occurred_at="2026-09-01T10:15:00Z",
        )
        self.assertEqual(ev_rev.to_state, CaseState.HUMAN_REVIEWED)
        self.assertEqual(service.ledger.total_entries, 5)

        # Dispatch
        assert ctx.approval is not None
        ev_exec = service.dispatch_execution(
            case_id=ctx.case_id,
            trusted_actor=self.actor(),
            approval_id=ctx.approval.approval_id,
            idempotency_key=ctx.approval.idempotency_key,
            expected_case_version=ctx.approval.case_version,
            current_eligible_action_set=ctx.reviewed_eligible_action_set,
            outreach_reference="out_ref_001928",
            occurred_at="2026-09-01T10:30:00Z",
        )
        self.assertEqual(ev_exec.to_state, CaseState.EXECUTED)
        self.assertEqual(service.ledger.total_entries, 6)

        # Resolve
        ev_res = service.resolve_case(
            case_id=ctx.case_id,
            resolution_notes="Contact made; payment promised.",
            occurred_at="2026-09-01T11:00:00Z",
        )
        self.assertEqual(ev_res.to_state, CaseState.RESOLVED)
        self.assertEqual(service.ledger.total_entries, 7)

    def test_workflow_service_rejection_and_dismissal(self) -> None:
        service = WorkflowService()
        ctx = service.create_case(
            policy_id="pol_839281726355",
            as_of_date="2026-09-01",
            reconstructed_state={"tenure_months": 14, "annual_premium": 1200.0},
            scoring_result={"calibrated_probability": 0.38, "operational_tier": "TIER_3_HIGH"},
            eligible_action_set=self.eligible(
                "grace_period_consultation", primary="grace_period_consultation"
            ),
            case_brief={"primary_recommendation": {"action_type": "grace_period_consultation"}},
            model_bundle_id="inforsight-v6-logistic-platt-20260817",
            action_channels={"grace_period_consultation": "phone"},
            occurred_at="2026-09-01T10:00:00Z",
        )
        ev_rev = service.submit_review(
            case_id=ctx.case_id,
            trusted_actor=self.actor(),
            action=SpecialistReviewAction.REJECT_AND_CLOSE,
            rationale_code="REJECT_KNOWN_COMPLAINT_HOLD",
            justification="Hold per customer service escalations.",
            occurred_at="2026-09-01T10:15:00Z",
        )
        self.assertEqual(ev_rev.to_state, CaseState.HUMAN_REVIEWED)

        ev_dism = service.dismiss_case(
            case_id=ctx.case_id,
            reason="Dismissed following specialist rejection.",
            occurred_at="2026-09-01T10:20:00Z",
        )
        self.assertEqual(ev_dism.to_state, CaseState.DISMISSED)
        self.assertEqual(service.ledger.total_entries, 6)

        ev_res = service.resolve_case(
            case_id=ctx.case_id,
            resolution_notes="Case closed after dismissal.",
            occurred_at="2026-09-01T10:30:00Z",
        )
        self.assertEqual(ev_res.to_state, CaseState.RESOLVED)
        self.assertEqual(service.ledger.total_entries, 7)

    def test_generic_human_reviewed_to_executed_bypass_is_blocked(self) -> None:
        ctx = self.approved_case(WorkflowService())
        with self.assertRaises(UnauthorizedExecutionError):
            ctx.state_machine.transition(CaseState.EXECUTED, {}, "2026-09-01T10:20:00Z")

    def test_execution_requires_exact_fresh_binding_and_protected_metadata(self) -> None:
        service = WorkflowService()
        ctx = self.approved_case(service)
        approval = ctx.approval
        assert approval is not None

        cases = (
            ({"approval_id": "apr_wrong"}, "AUTH_APPROVAL_MISMATCH"),
            ({"expected_case_version": approval.case_version + 1}, "AUTH_CASE_VERSION_STALE"),
            ({"current_eligible_action_set": {**ctx.reviewed_eligible_action_set, "snapshot_id": "snapshot_new"}}, "AUTH_EVIDENCE_STALE"),
            ({"metadata": {"channel": "attacker_override"}}, "AUTH_METADATA_OVERRIDE"),
        )
        base = {
            "case_id": ctx.case_id,
            "trusted_actor": self.actor(),
            "approval_id": approval.approval_id,
            "idempotency_key": approval.idempotency_key,
            "expected_case_version": approval.case_version,
            "current_eligible_action_set": ctx.reviewed_eligible_action_set,
            "outreach_reference": "out_authority_001",
            "occurred_at": "2026-09-01T10:20:00Z",
        }
        for override, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(AuthorityBoundaryError) as cm:
                    service.dispatch_execution(**{**base, **override})
                self.assertEqual(cm.exception.code, code)
                self.assertEqual(ctx.state_machine.current_state, CaseState.HUMAN_REVIEWED)

    def test_expired_approval_fails_closed(self) -> None:
        service = WorkflowService(approval_ttl_minutes=5)
        ctx = self.approved_case(service)
        approval = ctx.approval
        assert approval is not None
        with self.assertRaises(AuthorityBoundaryError) as cm:
            service.dispatch_execution(
                case_id=ctx.case_id,
                trusted_actor=self.actor(),
                approval_id=approval.approval_id,
                idempotency_key=approval.idempotency_key,
                expected_case_version=approval.case_version,
                current_eligible_action_set=ctx.reviewed_eligible_action_set,
                outreach_reference="out_expired",
                occurred_at="2026-09-01T10:21:00Z",
            )
        self.assertEqual(cm.exception.code, "AUTH_APPROVAL_EXPIRED")

    def test_idempotent_retry_and_conflicting_replay(self) -> None:
        service = WorkflowService(capacity_hours=0.5, capacity_cost_usd=20.0)
        ctx = self.approved_case(service)
        approval = ctx.approval
        assert approval is not None
        request = {
            "case_id": ctx.case_id,
            "trusted_actor": self.actor(),
            "approval_id": approval.approval_id,
            "idempotency_key": approval.idempotency_key,
            "expected_case_version": approval.case_version,
            "current_eligible_action_set": ctx.reviewed_eligible_action_set,
            "outreach_reference": "out_idempotent",
            "occurred_at": "2026-09-01T10:20:00Z",
        }
        first = service.dispatch_execution(**request)
        second = service.dispatch_execution(**request)
        self.assertIs(first, second)
        self.assertEqual(service.ledger.total_entries, 6)
        with self.assertRaises(AuthorityBoundaryError) as cm:
            service.dispatch_execution(**{**request, "outreach_reference": "out_conflict"})
        self.assertEqual(cm.exception.code, "AUTH_IDEMPOTENCY_CONFLICT")

    def test_concurrent_attempts_commit_once(self) -> None:
        service = WorkflowService(capacity_hours=0.5, capacity_cost_usd=20.0)
        ctx = self.approved_case(service)
        approval = ctx.approval
        assert approval is not None
        request = {
            "case_id": ctx.case_id,
            "trusted_actor": self.actor(),
            "approval_id": approval.approval_id,
            "idempotency_key": approval.idempotency_key,
            "expected_case_version": approval.case_version,
            "current_eligible_action_set": ctx.reviewed_eligible_action_set,
            "outreach_reference": "out_concurrent",
            "occurred_at": "2026-09-01T10:20:00Z",
        }
        with ThreadPoolExecutor(max_workers=2) as pool:
            events = list(pool.map(lambda _: service.dispatch_execution(**request), range(2)))
        self.assertEqual(events[0].case_event_id, events[1].case_event_id)
        self.assertEqual(service.ledger.total_entries, 6)

    def test_capacity_cannot_be_consumed_twice_across_cases(self) -> None:
        service = WorkflowService(capacity_hours=0.5, capacity_cost_usd=20.0)
        first = self.approved_case(service, case_id="case_authority000000000011")
        second = self.approved_case(service, case_id="case_authority000000000012")

        for ctx in (first, second):
            assert ctx.approval is not None
        service.dispatch_execution(
            case_id=first.case_id,
            trusted_actor=self.actor(),
            approval_id=first.approval.approval_id,
            idempotency_key=first.approval.idempotency_key,
            expected_case_version=first.approval.case_version,
            current_eligible_action_set=first.reviewed_eligible_action_set,
            outreach_reference="out_capacity_first",
            occurred_at="2026-09-01T10:20:00Z",
        )
        with self.assertRaises(AuthorityBoundaryError) as cm:
            service.dispatch_execution(
                case_id=second.case_id,
                trusted_actor=self.actor(),
                approval_id=second.approval.approval_id,
                idempotency_key=second.approval.idempotency_key,
                expected_case_version=second.approval.case_version,
                current_eligible_action_set=second.reviewed_eligible_action_set,
                outreach_reference="out_capacity_second",
                occurred_at="2026-09-01T10:20:00Z",
            )
        self.assertEqual(cm.exception.code, "AUTH_CAPACITY_EXHAUSTED")
        self.assertEqual(second.state_machine.current_state, CaseState.HUMAN_REVIEWED)

    def test_audit_handoff_failure_does_not_commit_execution(self) -> None:
        class FailingExecutionLedger(AuditLedger):
            def append(self, **kwargs):
                if kwargs["to_state"] == CaseState.EXECUTED.value:
                    raise OSError("injected audit handoff failure")
                return super().append(**kwargs)

        service = WorkflowService(audit_ledger=FailingExecutionLedger())
        ctx = self.approved_case(service)
        approval = ctx.approval
        assert approval is not None
        with self.assertRaises(OSError):
            service.dispatch_execution(
                case_id=ctx.case_id,
                trusted_actor=self.actor(),
                approval_id=approval.approval_id,
                idempotency_key=approval.idempotency_key,
                expected_case_version=approval.case_version,
                current_eligible_action_set=ctx.reviewed_eligible_action_set,
                outreach_reference="out_audit_failure",
                occurred_at="2026-09-01T10:20:00Z",
            )
        self.assertEqual(ctx.state_machine.current_state, CaseState.HUMAN_REVIEWED)
        self.assertEqual(service.ledger.total_entries, 5)

    def test_untrusted_actor_context_is_rejected(self) -> None:
        with self.assertRaises(AuthorityBoundaryError) as cm:
            TrustedActorContext(
                actor_id="usr_evaluator_99",
                authenticated=False,
                roles=("conservation_specialist",),
                trust_source="request_body",
            )
        self.assertEqual(cm.exception.code, "AUTH_ACTOR_UNTRUSTED")


if __name__ == "__main__":
    unittest.main()
