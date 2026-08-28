"""Cross-event validation for fictional policy histories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource


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

SUPPORTED_TRANSITIONS = frozenset(
    {
        ("active", "grace_period"),
        ("grace_period", "active"),
        ("grace_period", "lapsed"),
        ("active", "surrendered"),
    }
)

TERMINAL_OUTCOMES = {
    "lapsed": "outcome.lapsed",
    "surrendered": "outcome.surrendered",
}

PolicyEvent = dict[str, Any]


@dataclass(frozen=True)
class PreparedEvent:
    """Parsed event timestamps used for deterministic validation and replay."""

    event: PolicyEvent
    effective_at: datetime
    occurred_at: datetime
    ingested_at: datetime


def validate_policy_history(history: list[PolicyEvent]) -> None:
    """Validate event schemas first, then reject cross-event inconsistencies."""

    prepare_and_validate_history(history)


def prepare_and_validate_history(history: list[PolicyEvent]) -> list[PreparedEvent]:
    """Return a deterministically ordered, schema-and-semantics-valid copy."""

    _validate_event_schemas(history)
    prepared = _prepare_history(history)
    ordered = sorted(
        prepared,
        key=lambda item: (
            item.effective_at,
            item.occurred_at,
            item.event["event_id"],
        ),
    )
    _validate_timeline(ordered)
    return ordered


def _validate_event_schemas(history: object) -> None:
    if not isinstance(history, list) or not history:
        raise ValueError("history must be a non-empty list")
    validator = _policy_event_validator()
    for index, event in enumerate(history):
        errors = list(validator.iter_errors(event))
        if errors:
            direct = [error for error in errors if error.validator != "oneOf"]
            candidates = direct or [
                leaf for error in errors for leaf in _leaf_validation_errors(error)
            ]
            actionable = max(
                candidates,
                key=lambda item: (len(item.absolute_path), len(item.absolute_schema_path)),
            )
            path = ".".join(str(part) for part in actionable.absolute_path)
            location = f" at {path}" if path else ""
            raise ValueError(
                f"history event at index {index} fails JSON Schema{location}: "
                f"{actionable.message}"
            ) from errors[0]


def _leaf_validation_errors(error: ValidationError) -> list[ValidationError]:
    if not error.context:
        return [error]
    return [leaf for child in error.context for leaf in _leaf_validation_errors(child)]


@lru_cache(maxsize=1)
def _policy_event_validator() -> Draft202012Validator:
    contracts = Path(__file__).resolve().parents[3] / "data-contracts"
    schema_path = contracts / "policy-event.schema.json"
    if not schema_path.is_file():
        raise RuntimeError(
            "policy-event schemas are unavailable; install the Inforsight "
            "contract resources with the simulator"
        )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload_schemas = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((contracts / "payloads").glob("*.schema.json"))
    ]
    registry = Registry().with_resources(
        (item["$id"], Resource.from_contents(item)) for item in payload_schemas
    )
    return Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )


def parse_utc_timestamp(value: object, field: str) -> datetime:
    """Parse one contract timestamp and require an explicit UTC ``Z`` suffix."""

    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be an ISO 8601 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError(f"{field} must be a valid ISO 8601 UTC timestamp") from error
    if parsed.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError(f"{field} must use UTC")
    return parsed.astimezone(timezone.utc)


def _prepare_history(history: list[PolicyEvent]) -> list[PreparedEvent]:
    if not isinstance(history, list) or not history:
        raise ValueError("history must be a non-empty list")

    prepared: list[PreparedEvent] = []
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
            ingested_value = event["ingested_at"]
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

        effective_at = parse_utc_timestamp(
            effective_value, f"event {event_id} effective_at"
        )
        occurred_at = parse_utc_timestamp(
            occurred_value, f"event {event_id} occurred_at"
        )
        ingested_at = parse_utc_timestamp(
            ingested_value, f"event {event_id} ingested_at"
        )
        if ingested_at < occurred_at:
            raise ValueError(f"event {event_id} is ingested before it occurred")

        policy_ids.add(policy_id)
        event_ids.add(event_id)
        issuance_count += event_type == "policy.issued"
        prepared.append(
            PreparedEvent(event, effective_at, occurred_at, ingested_at)
        )

    if len(policy_ids) != 1:
        raise ValueError("history must contain events for exactly one policy_id")
    if issuance_count != 1:
        raise ValueError("history must contain exactly one policy.issued event")
    return prepared


def _validate_timeline(ordered: list[PreparedEvent]) -> None:
    issuance = next(
        item for item in ordered if item.event["event_type"] == "policy.issued"
    )
    initial_status = _payload_field(issuance, "initial_status")
    if initial_status != "active":
        raise ValueError("policy.issued initial_status must be active")

    billing_events: dict[str, PreparedEvent] = {}
    failed_payments: list[PreparedEvent] = []
    lapse_warnings: list[PreparedEvent] = []
    surrender_inquiries: list[PreparedEvent] = []
    outcomes: dict[str, list[PreparedEvent]] = {
        "outcome.lapsed": [],
        "outcome.surrendered": [],
    }

    for item in ordered:
        event = item.event
        event_id = event["event_id"]
        event_type = event["event_type"]
        payload = event["payload"]

        if item is not issuance and (
            item.effective_at < issuance.effective_at
            or item.occurred_at < issuance.occurred_at
        ):
            raise ValueError(f"event {event_id} occurs or is effective before issuance")

        if event_type == "billing.premium_due":
            billing_id = _payload_field(item, "billing_id")
            if billing_id in billing_events:
                raise ValueError(f"history contains duplicate billing_id {billing_id}")
            due_date = _parse_date(_payload_field(item, "due_date"), event_id)
            if due_date != item.effective_at.date():
                raise ValueError(
                    f"billing event {event_id} due_date does not match effective_at date"
                )
            billing_events[billing_id] = item
        elif event_type in ("payment.received", "payment.failed"):
            billing_id = _payload_field(item, "billing_id")
            billing = billing_events.get(billing_id)
            if billing is None:
                raise ValueError(
                    f"payment event {event_id} references unknown or future billing_id {billing_id}"
                )
            if (
                item.effective_at < billing.effective_at
                or item.occurred_at < billing.occurred_at
            ):
                raise ValueError(
                    f"payment event {event_id} occurs or is effective before its billing"
                )
            if event_type == "payment.failed":
                failed_payments.append(item)
        elif event_type == "notice.sent":
            notice_type = _payload_field(item, "notice_type")
            if notice_type in ("payment_reminder", "lapse_warning") and not any(
                failure.effective_at <= item.effective_at
                and failure.occurred_at <= item.occurred_at
                for failure in failed_payments
            ):
                raise ValueError(
                    f"notice event {event_id} precedes a payment failure"
                )
            if notice_type == "lapse_warning":
                lapse_warnings.append(item)
        elif event_type == "service.contact_recorded":
            if payload.get("reason") == "surrender_inquiry":
                surrender_inquiries.append(item)
        elif event_type in outcomes:
            outcomes[event_type].append(item)

    _validate_statuses_and_outcomes(ordered, initial_status, outcomes)

    for lapse in outcomes["outcome.lapsed"]:
        if not any(
            failure.effective_at <= lapse.effective_at
            and failure.occurred_at <= lapse.occurred_at
            for failure in failed_payments
        ):
            raise ValueError(
                f"lapse outcome {lapse.event['event_id']} precedes a payment failure"
            )
        if not any(
            warning.effective_at <= lapse.effective_at
            and warning.occurred_at <= lapse.occurred_at
            for warning in lapse_warnings
        ):
            raise ValueError(
                f"lapse outcome {lapse.event['event_id']} precedes a lapse warning"
            )

    for surrender in outcomes["outcome.surrendered"]:
        if not any(
            inquiry.effective_at <= surrender.effective_at
            and inquiry.occurred_at <= surrender.occurred_at
            for inquiry in surrender_inquiries
        ):
            raise ValueError(
                f"surrender outcome {surrender.event['event_id']} precedes a surrender inquiry"
            )


def _validate_statuses_and_outcomes(
    ordered: list[PreparedEvent],
    initial_status: str,
    outcomes: dict[str, list[PreparedEvent]],
) -> None:
    status = initial_status
    terminal_at: datetime | None = None
    terminal_status: str | None = None

    for item in ordered:
        event = item.event
        event_type = event["event_type"]
        if terminal_at is not None and item.effective_at > terminal_at:
            raise ValueError(
                f"event {event['event_id']} is effective after terminal status {terminal_status}"
            )
        if event_type != "policy.status_changed":
            continue

        previous = _payload_field(item, "previous_status")
        new = _payload_field(item, "new_status")
        if previous != status:
            raise ValueError(
                f"status event {event['event_id']} previous_status {previous!r} "
                f"does not match current status {status!r}"
            )
        if (previous, new) not in SUPPORTED_TRANSITIONS:
            raise ValueError(
                f"unsupported policy status transition {previous!r} -> {new!r}"
            )
        status = new
        if new in TERMINAL_OUTCOMES:
            terminal_at = item.effective_at
            terminal_status = new

    terminal_types_present = [event_type for event_type, items in outcomes.items() if items]
    if len(terminal_types_present) > 1:
        raise ValueError("history contains conflicting terminal outcomes")
    for event_type, items in outcomes.items():
        if len(items) > 1:
            raise ValueError(f"history contains more than one {event_type} event")

    for terminal, outcome_type in TERMINAL_OUTCOMES.items():
        status_events = [
            item
            for item in ordered
            if item.event["event_type"] == "policy.status_changed"
            and item.event["payload"].get("new_status") == terminal
        ]
        outcome_events = outcomes[outcome_type]
        if bool(status_events) != bool(outcome_events):
            raise ValueError(
                f"terminal status {terminal} and {outcome_type} must both be present"
            )
        if status_events and status_events[0].effective_at != outcome_events[0].effective_at:
            raise ValueError(
                f"terminal status {terminal} and {outcome_type} must share effective_at"
            )


def _payload_field(item: PreparedEvent, field: str) -> Any:
    try:
        return item.event["payload"][field]
    except KeyError as error:
        raise ValueError(
            f"{item.event['event_type']} payload is missing {field}"
        ) from error


def _parse_date(value: object, event_id: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"billing event {event_id} due_date must be an ISO 8601 date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            f"billing event {event_id} due_date must be a valid ISO 8601 date"
        ) from error
