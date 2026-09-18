"""Dependency-light streaming ingress semantics for the P4-02 boundary.

The Kafka adapter will call this boundary. Keeping validation and deduplication
independent of the broker makes the safety behavior testable without Docker.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


STREAMING_CONTRACT_VERSION = "1.0.0"
TOPIC_SCHEMAS = {
    "policy.lifecycle.v1": "policy-lifecycle-events.schema.json",
    "billing.payment.v1": "billing-payment-events.schema.json",
    "customer.service.v1": "customer-service-events.schema.json",
}
DEAD_LETTER_SUFFIX = ".dlq"


@dataclass(frozen=True)
class IngressResult:
    status: str
    topic: str
    event_id: str | None = None
    reason: str | None = None


class PointInTimeEventBuffer:
    """Retain accepted events and replay visibility independently of arrival order."""

    def __init__(self) -> None:
        self._events: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _time(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("streaming timestamps must be UTC")
        return parsed

    def append(self, event: Mapping[str, Any]) -> None:
        event_id = event.get("event_id")
        if not isinstance(event_id, str):
            raise ValueError("event must contain a string event_id")
        occurred_at = self._time(event["occurred_at"])
        ingested_at = self._time(event["ingested_at"])
        self._time(event["effective_at"])
        if occurred_at > ingested_at:
            raise ValueError("occurred_at cannot be after ingested_at")

        candidate = dict(event)
        prior = self._events.get(event_id)
        if prior is not None and json.dumps(prior, sort_keys=True) != json.dumps(candidate, sort_keys=True):
            raise ValueError(f"event_id {event_id!r} was reused with different content")
        self._events[event_id] = candidate

    def visible_events(self, as_of: str | datetime) -> tuple[Mapping[str, Any], ...]:
        cutoff = self._time(as_of) if isinstance(as_of, str) else as_of
        if cutoff.tzinfo is None or cutoff.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError("as_of must be UTC")
        visible = [
            event
            for event in self._events.values()
            if self._time(event["effective_at"]) <= cutoff
            and self._time(event["ingested_at"]) <= cutoff
        ]
        visible.sort(
            key=lambda event: (
                event["effective_at"],
                event["occurred_at"],
                event["ingested_at"],
                event["event_id"],
            )
        )
        return tuple(visible)


class StreamingIngress:
    """Validate and deduplicate events before handing them to a Kafka sink."""

    def __init__(self, contracts_dir: Path | None = None) -> None:
        root = contracts_dir or Path(__file__).resolve().parents[3] / "data-contracts" / "streaming"
        self._validators = {
            topic: Draft202012Validator(
                json.loads((root / filename).read_text(encoding="utf-8")),
                format_checker=FormatChecker(),
            )
            for topic, filename in TOPIC_SCHEMAS.items()
        }
        self._seen: set[tuple[str, str]] = set()

    def ingest(self, topic: str, event: Mapping[str, Any]) -> IngressResult:
        validator = self._validators.get(topic)
        if validator is None:
            return IngressResult("dead_letter", f"{topic}{DEAD_LETTER_SUFFIX}", reason="unknown_topic")

        errors = sorted(validator.iter_errors(event), key=lambda error: list(error.path))
        if errors:
            return IngressResult(
                "dead_letter",
                f"{topic}{DEAD_LETTER_SUFFIX}",
                event_id=event.get("event_id") if isinstance(event.get("event_id"), str) else None,
                reason=errors[0].message,
            )

        key = (event["event_id"], event["idempotency_key"])
        if key in self._seen:
            return IngressResult("duplicate", topic, event_id=event["event_id"], reason="duplicate_idempotency_key")

        self._seen.add(key)
        return IngressResult("accepted", topic, event_id=event["event_id"])


__all__ = [
    "DEAD_LETTER_SUFFIX",
    "IngressResult",
    "PointInTimeEventBuffer",
    "STREAMING_CONTRACT_VERSION",
    "StreamingIngress",
    "TOPIC_SCHEMAS",
]
