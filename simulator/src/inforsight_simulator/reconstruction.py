"""Point-in-time reconstruction for fictional policy-event histories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


SUPPORTED_EVENT_TYPES = frozenset(
    {
        "policy.issued",
        "policy.status_changed",
        "billing.premium_due",
        "payment.received",
        "payment.failed",
        "notice.sent",
        "service.contact_recorded",
        "outcome.lapsed",
        "outcome.surrendered",
    }
)

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


@dataclass(frozen=True)
class _PreparedEvent:
    event: PolicyEvent
    effective_at: datetime
    occurred_at: datetime


def reconstruct_policy_state(
    history: list[PolicyEvent],
    as_of: datetime | str,
) -> PolicyState | None:
    """Reconstruct one policy's effective state at an inclusive UTC cutoff.

    A valid cutoff before the policy's issuance returns ``None``. Invalid or
    ambiguous histories raise ``ValueError``.
    """

    cutoff = _parse_cutoff(as_of)
    prepared = _prepare_history(history)
    selected = sorted(
        (item for item in prepared if item.effective_at <= cutoff),
        key=lambda item: (
            item.effective_at,
            item.occurred_at,
            item.event["event_id"],
        ),
    )

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


def _prepare_history(history: list[PolicyEvent]) -> list[_PreparedEvent]:
    if not isinstance(history, list) or not history:
        raise ValueError("history must be a non-empty list")

    prepared: list[_PreparedEvent] = []
    policy_ids: set[str] = set()
    event_ids: set[str] = set()
    issuance_count = 0

    for index, event in enumerate(history):
        if not isinstance(event, dict):
            raise ValueError(f"history event at index {index} must be an object")
        try:
            policy_id = event["policy_id"]
            event_id = event["event_id"]
            event_type = event["event_type"]
            effective_value = event["effective_at"]
            occurred_value = event["occurred_at"]
            payload = event["payload"]
        except KeyError as error:
            raise ValueError(
                f"history event at index {index} is missing {error.args[0]}"
            ) from error

        if not isinstance(policy_id, str) or not policy_id:
            raise ValueError(f"history event at index {index} has an invalid policy_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError(f"history event at index {index} has an invalid event_id")
        if event_id in event_ids:
            raise ValueError(f"history contains duplicate event_id {event_id}")
        if event_type not in SUPPORTED_EVENT_TYPES:
            raise ValueError(f"unsupported event_type {event_type!r}")
        if not isinstance(payload, dict):
            raise ValueError(f"history event {event_id} payload must be an object")

        policy_ids.add(policy_id)
        event_ids.add(event_id)
        issuance_count += event_type == "policy.issued"
        prepared.append(
            _PreparedEvent(
                event=event,
                effective_at=_parse_utc_timestamp(
                    effective_value, f"event {event_id} effective_at"
                ),
                occurred_at=_parse_utc_timestamp(
                    occurred_value, f"event {event_id} occurred_at"
                ),
            )
        )

    if len(policy_ids) != 1:
        raise ValueError("history must contain events for exactly one policy_id")
    if issuance_count != 1:
        raise ValueError("history must contain exactly one policy.issued event")
    return prepared


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
    return _parse_utc_timestamp(value, "as_of")


def _parse_utc_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be an ISO 8601 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError(f"{field} must be a valid ISO 8601 UTC timestamp") from error
    if parsed.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError(f"{field} must use UTC")
    return parsed.astimezone(timezone.utc)
