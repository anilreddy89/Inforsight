"""Kafka adapter for the P4-02 streaming ingress boundary.

The adapter deliberately depends on a small producer/consumer protocol. A
real ``kafka-python`` client can be supplied in deployment, while unit tests
use in-memory fakes and exercise the same validation and DLQ behavior.
"""

from dataclasses import dataclass
import json
from typing import Any, Callable, Iterable, Mapping, Protocol

from .streaming import IngressResult, PointInTimeEventBuffer, StreamingIngress


class Producer(Protocol):
    def send(self, topic: str, *, key: bytes | None, value: bytes) -> Any: ...


class ConsumerRecord(Protocol):
    topic: str
    value: bytes | str | Mapping[str, Any]


class Consumer(Protocol):
    def __iter__(self) -> Iterable[ConsumerRecord]: ...


class KafkaClientUnavailable(RuntimeError):
    """Raised when the optional Kafka client dependency is not installed."""


@dataclass(frozen=True)
class PublishedEvent:
    topic: str
    event_id: str
    key: bytes


class KafkaStreamingAdapter:
    """Bridge Kafka records to :class:`StreamingIngress` and a downstream sink."""

    def __init__(
        self,
        producer: Producer,
        ingress: StreamingIngress | None = None,
        state: PointInTimeEventBuffer | None = None,
        downstream: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        self.producer = producer
        self.ingress = ingress or StreamingIngress()
        self.state = state
        self.downstream = downstream or (lambda event: None)

    @classmethod
    def from_bootstrap_servers(
        cls,
        bootstrap_servers: str,
        *,
        group_id: str | None = None,
        ingress: StreamingIngress | None = None,
        state: PointInTimeEventBuffer | None = None,
        downstream: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> "KafkaStreamingAdapter":
        try:
            from kafka import KafkaConsumer, KafkaProducer
        except ImportError as exc:
            raise KafkaClientUnavailable(
                "Install the optional 'streaming' extra to use the Kafka adapter"
            ) from exc

        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            key_serializer=lambda value: value,
            value_serializer=lambda value: value,
        )
        # The consumer is retained for the caller's processing loop. This
        # factory is intentionally only a client wiring point; subscription and
        # offset policy belong to the deployment entrypoint.
        consumer = KafkaConsumer(bootstrap_servers=bootstrap_servers, group_id=group_id)
        adapter = cls(producer, ingress=ingress, state=state, downstream=downstream)
        adapter.consumer = consumer  # type: ignore[attr-defined]
        return adapter

    @staticmethod
    def _encode(event: Mapping[str, Any]) -> bytes:
        return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    def publish(self, topic: str, event: Mapping[str, Any]) -> PublishedEvent:
        event_id = event.get("event_id")
        if not isinstance(event_id, str):
            raise ValueError("event must contain a string event_id")
        key = event_id.encode("utf-8")
        self.producer.send(topic, key=key, value=self._encode(event))
        return PublishedEvent(topic, event_id, key)

    def process_record(self, record: ConsumerRecord) -> IngressResult:
        event = record.value
        if isinstance(event, bytes):
            try:
                event = json.loads(event.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                event = {}
        elif isinstance(event, str):
            try:
                event = json.loads(event)
            except json.JSONDecodeError:
                event = {}

        if not isinstance(event, Mapping):
            event = {}
        result = self.ingress.ingest(record.topic, event)
        if result.status == "accepted":
            try:
                if self.state is not None:
                    self.state.append(event)
            except (KeyError, TypeError, ValueError) as exc:
                result = IngressResult(
                    "dead_letter",
                    f"{record.topic}.dlq",
                    event_id=event.get("event_id") if isinstance(event.get("event_id"), str) else None,
                    reason=str(exc),
                )
            else:
                self.downstream(event)
        elif result.status == "dead_letter":
            self.producer.send(
                result.topic,
                key=(result.event_id or "invalid").encode("utf-8"),
                value=self._encode(event),
            )
        return result


__all__ = [
    "ConsumerRecord",
    "KafkaClientUnavailable",
    "KafkaStreamingAdapter",
    "PublishedEvent",
]
