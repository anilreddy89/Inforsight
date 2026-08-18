"""Point-in-time reconstruction for fictional policy-event histories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .validation import parse_utc_timestamp, prepare_and_validate_history

PolicyEvent = dict[str, Any]


@dataclass(frozen=True)
class PolicyState:
    """Immutable state derived from policy events effective by a UTC cutoff."""

    policy_id: str
    as_of: datetime
    status: str
    product_variant: str
    billing_frequency: str
    premium_amount_cents: int
    currency: str
    issued_at: datetime
    applied_event_count: int
    last_event_id: str
    last_effective_at: datetime


def reconstruct_policy_state(
    history: list[PolicyEvent],
    as_of: datetime | str,
) -> PolicyState | None:
    """Reconstruct one policy's effective state at an inclusive UTC cutoff.

    A valid cutoff before the policy's issuance returns ``None``. Invalid or
    ambiguous histories raise ``ValueError``.
    """

    cutoff = _parse_cutoff(as_of)
    prepared = prepare_and_validate_history(history)
    selected = [item for item in prepared if item.effective_at <= cutoff]

    if not selected:
        return None

    state_values: dict[str, Any] | None = None
    for item in selected:
        event = item.event
        event_type = event["event_type"]
        payload = event["payload"]

        if event_type == "policy.issued":
            if state_values is not None:
                raise ValueError("history contains more than one policy.issued event")
            state_values = _initial_state_values(event, item.effective_at)
        elif state_values is None:
            raise ValueError("an event is effective before policy issuance")
        elif event_type == "policy.status_changed":
            try:
                state_values["status"] = payload["new_status"]
            except KeyError as error:
                raise ValueError(
                    "policy.status_changed payload is missing new_status"
                ) from error

    if state_values is None:
        return None

    last = selected[-1]
    return PolicyState(
        **state_values,
        as_of=cutoff,
        applied_event_count=len(selected),
        last_event_id=last.event["event_id"],
        last_effective_at=last.effective_at,
    )


def _initial_state_values(event: PolicyEvent, issued_at: datetime) -> dict[str, Any]:
    payload = event["payload"]
    required = (
        "initial_status",
        "product_variant",
        "billing_frequency",
        "premium_amount_cents",
        "currency",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "policy.issued payload is missing " + ", ".join(sorted(missing))
        )
    return {
        "policy_id": event["policy_id"],
        "status": payload["initial_status"],
        "product_variant": payload["product_variant"],
        "billing_frequency": payload["billing_frequency"],
        "premium_amount_cents": payload["premium_amount_cents"],
        "currency": payload["currency"],
        "issued_at": issued_at,
    }


def _parse_cutoff(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware and use UTC")
        if value.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("as_of must use UTC")
        return value.astimezone(timezone.utc)
    return parse_utc_timestamp(value, "as_of")
