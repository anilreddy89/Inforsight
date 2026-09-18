import json
import unittest
from dataclasses import dataclass

from inforsight_simulator.kafka_adapter import KafkaStreamingAdapter
from inforsight_simulator.streaming import PointInTimeEventBuffer


@dataclass
class Record:
    topic: str
    value: bytes


class FakeProducer:
    def __init__(self) -> None:
        self.sent = []

    def send(self, topic: str, *, key: bytes | None, value: bytes) -> None:
        self.sent.append((topic, key, value))


def valid_event() -> dict:
    return {
        "schema_version": "1.0.0",
        "event_id": "evt_123456789abc",
        "idempotency_key": "source-a:123",
        "policy_id": "pol_123456789abc",
        "event_type": "policy.issued",
        "occurred_at": "2026-01-01T00:00:00Z",
        "effective_at": "2026-01-01T00:00:00Z",
        "ingested_at": "2026-01-01T00:01:00Z",
        "source": "test-fixture",
        "payload": {"status": "active"},
    }


class KafkaStreamingAdapterTest(unittest.TestCase):
    def test_publish_uses_event_id_as_kafka_key(self) -> None:
        producer = FakeProducer()
        adapter = KafkaStreamingAdapter(producer)
        published = adapter.publish("policy.lifecycle.v1", valid_event())
        self.assertEqual(published.key, b"evt_123456789abc")
        self.assertEqual(producer.sent[0][0], "policy.lifecycle.v1")
        self.assertEqual(json.loads(producer.sent[0][2]), valid_event())

    def test_valid_record_reaches_downstream(self) -> None:
        producer = FakeProducer()
        downstream = []
        adapter = KafkaStreamingAdapter(producer, downstream=downstream.append)
        result = adapter.process_record(Record("policy.lifecycle.v1", json.dumps(valid_event()).encode()))
        self.assertEqual(result.status, "accepted")
        self.assertEqual(downstream, [valid_event()])
        self.assertEqual(producer.sent, [])

    def test_accepted_record_updates_point_in_time_state(self) -> None:
        producer = FakeProducer()
        state = PointInTimeEventBuffer()
        adapter = KafkaStreamingAdapter(producer, state=state)
        result = adapter.process_record(Record("policy.lifecycle.v1", json.dumps(valid_event()).encode()))
        self.assertEqual(result.status, "accepted")
        self.assertEqual(len(state.visible_events("2026-01-02T00:00:00Z")), 1)

    def test_invalid_record_is_published_to_dlq_without_crashing(self) -> None:
        producer = FakeProducer()
        adapter = KafkaStreamingAdapter(producer)
        invalid = valid_event()
        invalid["schema_version"] = "9.0.0"
        result = adapter.process_record(Record("policy.lifecycle.v1", json.dumps(invalid).encode()))
        self.assertEqual(result.status, "dead_letter")
        self.assertEqual(producer.sent[0][0], "policy.lifecycle.v1.dlq")

    def test_malformed_json_is_published_to_dlq(self) -> None:
        producer = FakeProducer()
        adapter = KafkaStreamingAdapter(producer)
        result = adapter.process_record(Record("billing.payment.v1", b"not-json"))
        self.assertEqual(result.status, "dead_letter")
        self.assertEqual(producer.sent[0][0], "billing.payment.v1.dlq")


if __name__ == "__main__":
    unittest.main()
