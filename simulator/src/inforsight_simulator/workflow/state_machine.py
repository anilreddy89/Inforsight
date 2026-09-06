"""Deterministic finite state machine governing conservation case lifecycles.

Enforces legal boundaries, regulatory invariants, and the ADR 0002 mandatory
human review gate.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence
import uuid

from inforsight_simulator.workflow.models import (
    CaseEvent,
    CaseState,
    HumanReview,
    IneligibleOverrideError,
    InvalidTransitionError,
    ReviewDecision,
    SpecialistReviewAction,
    UnauthorizedExecutionError,
)

# Formal transition graph defined in data-contracts/conservation-case-event.schema.json
VALID_TRANSITIONS: frozenset[tuple[CaseState, CaseState]] = frozenset(
    [
        (CaseState.NONE, CaseState.CREATED),
        (CaseState.CREATED, CaseState.TRIAGED),
        (CaseState.TRIAGED, CaseState.EVIDENCE_ASSEMBLED),
        (CaseState.EVIDENCE_ASSEMBLED, CaseState.RECOMMENDED),
        (CaseState.RECOMMENDED, CaseState.HUMAN_REVIEWED),
        (CaseState.HUMAN_REVIEWED, CaseState.EXECUTED),
        (CaseState.HUMAN_REVIEWED, CaseState.DISMISSED),
        (CaseState.EXECUTED, CaseState.RESOLVED),
        (CaseState.DISMISSED, CaseState.RESOLVED),
    ]
)


class CaseStateMachine:
    """Manages lifecycle transitions for a single conservation case."""

    def __init__(
        self,
        case_id: str,
        policy_id: str,
        initial_state: CaseState = CaseState.NONE,
    ) -> None:
        self.case_id = case_id
        self.policy_id = policy_id
        self._current_state = initial_state
        self._events: list[CaseEvent] = []
        self._human_review: Optional[HumanReview] = None
        self._approved_action_type: Optional[str] = None

    @property
    def current_state(self) -> CaseState:
        return self._current_state

    @property
    def human_review(self) -> Optional[HumanReview]:
        return self._human_review

    @property
    def approved_action_type(self) -> Optional[str]:
        return self._approved_action_type

    @property
    def events(self) -> tuple[CaseEvent, ...]:
        return tuple(self._events)

    def transition(
        self,
        to_state: CaseState,
        payload: dict[str, Any],
        occurred_at: str,
        case_event_id: Optional[str] = None,
    ) -> CaseEvent:
        """Executes a validated state transition and records a CaseEvent."""
        from_state = self._current_state

        # Hard ADR 0002 boundary check: autonomous execution is strictly prohibited
        if from_state == CaseState.RECOMMENDED and to_state == CaseState.EXECUTED:
            raise UnauthorizedExecutionError(
                f"Autonomous execution violation (ADR 0002): Case '{self.case_id}' cannot transition "
                f"directly from {from_state.value} to {to_state.value} without human review."
            )

        edge = (from_state, to_state)
        if edge not in VALID_TRANSITIONS:
            raise InvalidTransitionError(
                f"Invalid transition for case '{self.case_id}': from {from_state.value} "
                f"to {to_state.value} is not permitted by conservation case contract."
            )

        event_id = case_event_id or f"cev_{uuid.uuid4().hex[:24]}"
        event = CaseEvent(
            case_event_id=event_id,
            case_id=self.case_id,
            policy_id=self.policy_id,
            from_state=from_state,
            to_state=to_state,
            occurred_at=occurred_at,
            payload=payload,
        )

        self._current_state = to_state
        self._events.append(event)
        return event

    def submit_human_review(
        self,
        review: HumanReview,
        occurred_at: str,
        recommended_action: str,
        eligible_actions: Sequence[str],
        selected_action: Optional[str] = None,
        case_event_id: Optional[str] = None,
    ) -> CaseEvent:
        """Processes a human review decision from RECOMMENDED to HUMAN_REVIEWED."""
        if self._current_state != CaseState.RECOMMENDED:
            raise InvalidTransitionError(
                f"Cannot submit human review for case '{self.case_id}' in state {self._current_state.value}; "
                f"expected {CaseState.RECOMMENDED.value}"
            )

        chosen_action: str
        if review.decision == ReviewDecision.APPROVED:
            chosen_action = recommended_action
        elif review.decision == ReviewDecision.OVERRIDDEN:
            if not selected_action:
                raise IneligibleOverrideError(
                    "Selected action must be specified when decision is OVERRIDDEN"
                )
            if selected_action not in eligible_actions:
                raise IneligibleOverrideError(
                    f"Specialist override action '{selected_action}' is disqualified. "
                    f"Allowed eligible actions: {list(eligible_actions)}"
                )
            chosen_action = selected_action
        elif review.decision == ReviewDecision.REJECTED:
            chosen_action = "abstain"
        else:
            chosen_action = "abstain"

        self._human_review = review
        self._approved_action_type = chosen_action

        payload = {"human_review": review.to_dict()}
        return self.transition(
            to_state=CaseState.HUMAN_REVIEWED,
            payload=payload,
            occurred_at=occurred_at,
            case_event_id=case_event_id,
        )

    def dispatch_execution(
        self,
        channel: str,
        outreach_reference: str,
        occurred_at: str,
        metadata: Optional[dict[str, Any]] = None,
        case_event_id: Optional[str] = None,
    ) -> CaseEvent:
        """Dispatches an approved action from HUMAN_REVIEWED to EXECUTED."""
        if self._current_state != CaseState.HUMAN_REVIEWED:
            raise UnauthorizedExecutionError(
                f"Cannot execute case '{self.case_id}' in state {self._current_state.value}; "
                f"must be {CaseState.HUMAN_REVIEWED.value} with recorded human authorization."
            )

        if not self._human_review:
            raise UnauthorizedExecutionError(
                f"Cannot execute case '{self.case_id}': missing human review record."
            )

        if self._human_review.decision == ReviewDecision.REJECTED:
            raise InvalidTransitionError(
                f"Cannot execute case '{self.case_id}': human review decision was REJECTED."
            )

        action_type = self._approved_action_type or "abstain"
        if action_type == "abstain":
            # An abstain decision is dismissed rather than dispatched as an active execution
            return self.transition(
                to_state=CaseState.DISMISSED,
                payload={
                    "human_review": self._human_review.to_dict(),
                    "reason": "ABSTAIN_SELECTED",
                },
                occurred_at=occurred_at,
                case_event_id=case_event_id,
            )

        payload = {
            "human_review": self._human_review.to_dict(),
            "execution_details": {
                "action_type": action_type,
                "channel": channel,
                "outreach_reference": outreach_reference,
                **(metadata or {}),
            },
        }

        return self.transition(
            to_state=CaseState.EXECUTED,
            payload=payload,
            occurred_at=occurred_at,
            case_event_id=case_event_id,
        )

    def dismiss(
        self,
        reason: str,
        occurred_at: str,
        case_event_id: Optional[str] = None,
    ) -> CaseEvent:
        """Dismisses a case from HUMAN_REVIEWED to DISMISSED."""
        if self._current_state != CaseState.HUMAN_REVIEWED:
            raise InvalidTransitionError(
                f"Cannot dismiss case '{self.case_id}' in state {self._current_state.value}; "
                f"expected {CaseState.HUMAN_REVIEWED.value}"
            )

        payload: dict[str, Any] = {"reason": reason}
        if self._human_review:
            payload["human_review"] = self._human_review.to_dict()

        return self.transition(
            to_state=CaseState.DISMISSED,
            payload=payload,
            occurred_at=occurred_at,
            case_event_id=case_event_id,
        )

    def resolve(
        self,
        resolution_notes: str,
        occurred_at: str,
        case_event_id: Optional[str] = None,
    ) -> CaseEvent:
        """Transitions a case from EXECUTED or DISMISSED to terminal state RESOLVED."""
        if self._current_state not in (CaseState.EXECUTED, CaseState.DISMISSED):
            raise InvalidTransitionError(
                f"Cannot resolve case '{self.case_id}' in state {self._current_state.value}; "
                f"must be {CaseState.EXECUTED.value} or {CaseState.DISMISSED.value}"
            )

        payload = {"resolution_notes": resolution_notes}
        return self.transition(
            to_state=CaseState.RESOLVED,
            payload=payload,
            occurred_at=occurred_at,
            case_event_id=case_event_id,
        )

