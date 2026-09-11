"""Domain models and exceptions for HITL conservation case workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Optional


class CaseState(str, Enum):
    """Lifecycle states defined in data-contracts/conservation-case-event.schema.json."""

    NONE = "NONE"
    CREATED = "CREATED"
    TRIAGED = "TRIAGED"
    EVIDENCE_ASSEMBLED = "EVIDENCE_ASSEMBLED"
    RECOMMENDED = "RECOMMENDED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    EXECUTED = "EXECUTED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class SpecialistReviewAction(str, Enum):
    """Actions selectable by a conservation specialist during case review."""

    APPROVE_RECOMMENDATION = "APPROVE_RECOMMENDATION"
    OVERRIDE_ACTION = "OVERRIDE_ACTION"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    REJECT_AND_CLOSE = "REJECT_AND_CLOSE"


class ReviewDecision(str, Enum):
    """Formal review decision recorded in the event payload."""

    APPROVED = "APPROVED"
    OVERRIDDEN = "OVERRIDDEN"
    REJECTED = "REJECTED"


REVIEWER_ID_REGEX = re.compile(r"^usr_[a-z0-9_]{3,32}$")
RATIONALE_CODE_REGEX = re.compile(r"^[A-Z0-9_]{3,64}$")
CASE_EVENT_ID_REGEX = re.compile(r"^cev_[a-z0-9]{12,64}$")
CASE_ID_REGEX = re.compile(r"^case_[a-z0-9]{12,64}$")
POLICY_ID_REGEX = re.compile(r"^pol_[a-z0-9]{12,64}$")


class WorkflowError(Exception):
    """Base exception for workflow state machine violations."""


class InvalidTransitionError(WorkflowError):
    """Raised when an illegal state transition is attempted."""


class UnauthorizedExecutionError(WorkflowError):
    """Raised when action execution is attempted without human review authorization (ADR 0002)."""


class IneligibleOverrideError(WorkflowError):
    """Raised when a specialist attempts to override with a disqualified action."""


class InvalidReviewerCredentialsError(WorkflowError):
    """Raised when reviewer ID or credentials fail validation."""


class MissingJustificationError(WorkflowError):
    """Raised when required rationale code or justification is missing or inadequate."""


class AuthorityBoundaryError(UnauthorizedExecutionError):
    """Stable fail-closed authority-boundary error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class TrustedActorContext:
    """Identity asserted by a trusted local server-side adapter, never a request body."""

    actor_id: str
    authenticated: bool
    roles: tuple[str, ...]
    trust_source: str

    def __post_init__(self) -> None:
        if not self.authenticated:
            raise AuthorityBoundaryError("AUTH_ACTOR_UNTRUSTED", "actor is not authenticated")
        if not REVIEWER_ID_REGEX.match(self.actor_id):
            raise InvalidReviewerCredentialsError(
                f"Actor ID '{self.actor_id}' does not match the trusted reviewer pattern"
            )
        if "conservation_specialist" not in self.roles:
            raise AuthorityBoundaryError(
                "AUTH_ACTOR_UNAUTHORIZED", "actor lacks conservation_specialist authority"
            )
        if not self.trust_source:
            raise AuthorityBoundaryError("AUTH_ACTOR_UNTRUSTED", "trust source is required")


@dataclass(frozen=True)
class ApprovalBinding:
    """Single-use approval bound to the exact evidence and recommendation reviewed."""

    approval_id: str
    case_id: str
    case_version: int
    snapshot_id: str
    safety_evidence_id: str
    eligibility_digest: str
    requirements_version: str
    action_type: str
    channel: str
    recommendation_version: str
    model_bundle_id: str
    actor_id: str
    reviewed_at: str
    expires_at: str
    idempotency_key: str
    schema_version: str = "authority-approval/1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)

    def is_expired_at(self, occurred_at: str) -> bool:
        def parse(value: str) -> datetime:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if result.tzinfo is None:
                raise AuthorityBoundaryError("AUTH_TIME_INVALID", "authority times must be timezone-aware")
            return result.astimezone(timezone.utc)

        return parse(occurred_at) > parse(self.expires_at)


@dataclass(frozen=True)
class ActionResourceRequirement:
    """Bounded local resource units reserved atomically at execution."""

    personnel_hours: float = 0.0
    direct_cost_usd: float = 0.0
    personnel_seconds: int | None = None
    direct_cost_usd_micros: int | None = None

    def __post_init__(self) -> None:
        if self.personnel_hours < 0 or self.direct_cost_usd < 0:
            raise ValueError("action resources cannot be negative")
        seconds = self.personnel_seconds
        micros = self.direct_cost_usd_micros
        if seconds is None:
            converted_seconds = self.personnel_hours * 3_600
            if not converted_seconds.is_integer():
                raise ValueError("personnel_hours must convert exactly to integer seconds")
            seconds = int(converted_seconds)
        if micros is None:
            converted_micros = self.direct_cost_usd * 1_000_000
            if not converted_micros.is_integer():
                raise ValueError("direct_cost_usd must convert exactly to integer USD micros")
            micros = int(converted_micros)
        if not isinstance(seconds, int) or seconds < 0:
            raise ValueError("personnel_seconds must be a nonnegative integer")
        if not isinstance(micros, int) or micros < 0:
            raise ValueError("direct_cost_usd_micros must be a nonnegative integer")
        object.__setattr__(self, "personnel_seconds", seconds)
        object.__setattr__(self, "direct_cost_usd_micros", micros)


@dataclass(frozen=True)
class HumanReview:
    """Immutable human review record conforming to conservation-case-event contract."""

    reviewer_id: str
    reviewed_at: str
    decision: ReviewDecision
    rationale_code: str
    justification: Optional[str] = None

    def __post_init__(self) -> None:
        if not REVIEWER_ID_REGEX.match(self.reviewer_id):
            raise InvalidReviewerCredentialsError(
                f"Reviewer ID '{self.reviewer_id}' does not match pattern '^usr_[a-z0-9_]{{3,32}}$'"
            )
        if not RATIONALE_CODE_REGEX.match(self.rationale_code):
            raise MissingJustificationError(
                f"Rationale code '{self.rationale_code}' does not match pattern '^[A-Z0-9_]{{3,64}}$'"
            )
        if self.decision in (ReviewDecision.OVERRIDDEN, ReviewDecision.REJECTED):
            if not self.justification or len(self.justification.strip()) < 5:
                raise MissingJustificationError(
                    f"Decision '{self.decision.value}' requires non-empty justification of at least 5 characters"
                )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at,
            "decision": self.decision.value,
            "rationale_code": self.rationale_code,
        }
        if self.justification is not None:
            d["justification"] = self.justification
        return d


@dataclass(frozen=True)
class DecisionContextDigest:
    """Cryptographic fingerprints of point-in-time inputs for tamper-evident provenance."""

    reconstructed_state_sha256: str
    model_bundle_id: str
    model_score_sha256: str
    eligible_action_set_sha256: str
    case_brief_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconstructed_state_sha256": self.reconstructed_state_sha256,
            "model_bundle_id": self.model_bundle_id,
            "model_score_sha256": self.model_score_sha256,
            "eligible_action_set_sha256": self.eligible_action_set_sha256,
            "case_brief_sha256": self.case_brief_sha256,
        }


@dataclass(frozen=True)
class ExecutionDetails:
    """Details of dispatched intervention following human review approval."""

    action_type: str
    channel: str
    outreach_reference: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "action_type": self.action_type,
            "channel": self.channel,
            "outreach_reference": self.outreach_reference,
        }
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@dataclass(frozen=True)
class CaseEvent:
    """Immutable case lifecycle event strictly conforming to conservation-case-event.schema.json."""

    case_event_id: str
    case_id: str
    policy_id: str
    from_state: CaseState
    to_state: CaseState
    occurred_at: str
    payload: dict[str, Any]
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_event_id": self.case_event_id,
            "case_id": self.case_id,
            "policy_id": self.policy_id,
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "occurred_at": self.occurred_at,
            "payload": self.payload,
        }
