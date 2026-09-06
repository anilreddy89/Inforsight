"""Unit and invariant tests for HITL conservation case workflow engine."""

from __future__ import annotations

import unittest

from inforsight_simulator.workflow.models import (
    CaseEvent,
    CaseState,
    HumanReview,
    IneligibleOverrideError,
    InvalidReviewerCredentialsError,
    InvalidTransitionError,
    MissingJustificationError,
    ReviewDecision,
    SpecialistReviewAction,
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
        ev_exec = self.sm.dispatch_execution(
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
        self.assertIn("without human review", str(cm.exception))

    def test_invalid_arbitrary_transitions_rejected(self) -> None:
        """Verifies that invalid transitions violate state machine graph."""
        # Direct jump from NONE to EXECUTED
        with self.assertRaises(InvalidTransitionError):
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
        with self.assertRaises(InvalidTransitionError):
            self.sm.dispatch_execution("phone", "out_123", "2026-09-01T09:10:00Z")

        # Dismissal succeeds
        self.sm.dismiss("Rejected by specialist.", "2026-09-01T09:15:00Z")
        self.assertEqual(self.sm.current_state, CaseState.DISMISSED)

        # Final resolve
        self.sm.resolve("Case closed following dismissal.", "2026-09-01T09:30:00Z")
        self.assertEqual(self.sm.current_state, CaseState.RESOLVED)


class TestWorkflowService(unittest.TestCase):
    """Tests high-level WorkflowService binding state machine and audit ledger."""

    def test_workflow_service_lifecycle(self) -> None:
        service = WorkflowService()

        # Create case
        ctx = service.create_case(
            policy_id="pol_839281726354",
            as_of_date="2026-09-01",
            reconstructed_state={"tenure_months": 14, "annual_premium": 1200.0},
            scoring_result={"calibrated_probability": 0.38, "operational_tier": "TIER_3_HIGH"},
            eligible_action_set={
                "primary_action": "grace_period_consultation",
                "eligible_actions": ["grace_period_consultation", "courtesy_reminder"],
            },
            case_brief={"primary_recommendation": {"action_type": "grace_period_consultation"}},
            model_bundle_id="inforsight-v6-logistic-platt-20260817",
            occurred_at="2026-09-01T10:00:00Z",
        )
        self.assertEqual(ctx.state_machine.current_state, CaseState.RECOMMENDED)
        self.assertEqual(service.ledger.total_entries, 4)

        # Submit review
        ev_rev = service.submit_review(
            case_id=ctx.case_id,
            reviewer_id="usr_evaluator_99",
            action=SpecialistReviewAction.APPROVE_RECOMMENDATION,
            rationale_code="APPROVE_RECOMMENDED_ACTION",
            justification="Standard procedure followed.",
            occurred_at="2026-09-01T10:15:00Z",
        )
        self.assertEqual(ev_rev.to_state, CaseState.HUMAN_REVIEWED)
        self.assertEqual(service.ledger.total_entries, 5)

        # Dispatch
        ev_exec = service.dispatch_execution(
            case_id=ctx.case_id,
            channel="phone",
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


if __name__ == "__main__":
    unittest.main()

