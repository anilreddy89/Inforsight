"""Immutable domain models for policy conservation action eligibility rules.

These structures represent point-in-time policy context, action specifications,
and auditable evaluation outputs strictly decoupled from predictive ML models
(ADR 0002).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .reasons import DisqualificationReasonCode


@dataclass(frozen=True)
class PolicyContext:
    """Immutable point-in-time policy state, preferences, and governance flags."""

    policy_id: str
    as_of: datetime
    status: str
    tenure_days: int
    in_grace_period: bool
    days_past_due: int
    has_active_claim: bool = False
    has_legal_hold: bool = False
    has_registered_dispute: bool = False
    sms_opt_out: bool = False
    email_opt_out: bool = False
    phone_opt_out: bool = False
    dnc_registered: bool = False
    last_contact_date: datetime | None = None

    def __post_init__(self) -> None:
        """Validate core invariants on initialization."""
        if not self.policy_id:
            raise ValueError("policy_id cannot be empty")
        if not isinstance(self.as_of, datetime):
            raise TypeError("as_of must be a datetime instance")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("as_of must be timezone-aware and use UTC")
        if self.tenure_days < 0:
            raise ValueError("tenure_days cannot be negative")
        if self.days_past_due < 0:
            raise ValueError("days_past_due cannot be negative")
        if self.last_contact_date is not None:
            if not isinstance(self.last_contact_date, datetime):
                raise TypeError("last_contact_date must be a datetime instance or None")
            if (
                self.last_contact_date.tzinfo is None
                or self.last_contact_date.utcoffset() != timezone.utc.utcoffset(None)
            ):
                raise ValueError("last_contact_date must be timezone-aware and use UTC")
            if self.last_contact_date > self.as_of:
                raise ValueError("last_contact_date cannot be in the future relative to as_of")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PolicyContext:
        """Construct PolicyContext from a dictionary, parsing ISO 8601 UTC dates."""
        as_of = data["as_of"]
        if isinstance(as_of, str):
            as_of = datetime.fromisoformat(as_of.replace("Z", "+00:00")).astimezone(timezone.utc)

        last_contact = data.get("last_contact_date")
        if isinstance(last_contact, str):
            last_contact = datetime.fromisoformat(
                last_contact.replace("Z", "+00:00")
            ).astimezone(timezone.utc)

        return cls(
            policy_id=data["policy_id"],
            as_of=as_of,
            status=data["status"],
            tenure_days=int(data["tenure_days"]),
            in_grace_period=bool(data["in_grace_period"]),
            days_past_due=int(data["days_past_due"]),
            has_active_claim=bool(data.get("has_active_claim", False)),
            has_legal_hold=bool(data.get("has_legal_hold", False)),
            has_registered_dispute=bool(data.get("has_registered_dispute", False)),
            sms_opt_out=bool(data.get("sms_opt_out", False)),
            email_opt_out=bool(data.get("email_opt_out", False)),
            phone_opt_out=bool(data.get("phone_opt_out", False)),
            dnc_registered=bool(data.get("dnc_registered", False)),
            last_contact_date=last_contact,
        )


@dataclass(frozen=True)
class ConservationActionDefinition:
    """In-memory representation of an action conforming to conservation-action schema."""

    action_id: str
    action_type: str
    channel: str
    direct_cost_usd: float
    personnel_hours: float
    regulatory_cooling_off_days: int
    minimum_policy_tenure_days: int
    maximum_policy_tenure_days: int | None = None
    requires_grace_period: bool = False

    def __post_init__(self) -> None:
        if self.action_type == "abstain":
            if self.direct_cost_usd != 0.0:
                raise ValueError("abstain action must have direct_cost_usd == 0.0")
            if self.personnel_hours != 0.0:
                raise ValueError("abstain action must have personnel_hours == 0.0")
            if self.channel != "none":
                raise ValueError("abstain action must have channel == 'none'")
        else:
            if self.direct_cost_usd <= 0.0:
                raise ValueError("active intervention must have direct_cost_usd > 0.0")
            if self.channel == "none":
                raise ValueError("active intervention cannot have channel == 'none'")


@dataclass(frozen=True)
class ActionEligibilityResult:
    """Evaluation output for one candidate action."""

    action_type: str
    is_eligible: bool
    disqualification_reasons: tuple[str, ...]
    disqualification_details: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            "action_type": self.action_type,
            "is_eligible": self.is_eligible,
            "disqualification_reasons": list(self.disqualification_reasons),
            "disqualification_details": list(self.disqualification_details),
        }


@dataclass(frozen=True)
class EligibleActionSet:
    """Complete, immutable evaluation result set for a policy triage episode."""

    policy_id: str
    as_of: datetime
    is_frozen: bool
    freeze_reason: str | None
    results: dict[str, ActionEligibilityResult]
    eligible_actions: tuple[str, ...]

    def is_eligible(self, action_type: str) -> bool:
        """Check if a specific action type is eligible."""
        result = self.results.get(action_type)
        return result.is_eligible if result else False

    def get_reasons(self, action_type: str) -> tuple[str, ...]:
        """Get disqualification reason codes for a specific action type."""
        result = self.results.get(action_type)
        return result.disqualification_reasons if result else ()

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            "policy_id": self.policy_id,
            "as_of": self.as_of.isoformat().replace("+00:00", "Z"),
            "is_frozen": self.is_frozen,
            "freeze_reason": self.freeze_reason,
            "results": {k: v.to_dict() for k, v in sorted(self.results.items())},
            "eligible_actions": list(self.eligible_actions),
        }

