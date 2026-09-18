import unittest

from inforsight_simulator.streaming import PointInTimeEventBuffer, StreamingIngress


def event(event_type: str = "policy.issued") -> dict:
    return {
        "schema_version": "1.0.0",
        "event_id": "evt_123456789abc",
        "idempotency_key": "source-a:123",
        "policy_id": "pol_123456789abc",
        "event_type": event_type,
        "occurred_at": "2026-01-01T00:00:00Z",
        "effective_at": "2026-01-01T00:00:00Z",
        "ingested_at": "2026-01-01T00:01:00Z",
        "source": "test-fixture",
        "payload": {"status": "active"},
    }


class StreamingIngressTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ingress = StreamingIngress()

    def test_accepts_valid_event(self) -> None:
        result = self.ingress.ingest("policy.lifecycle.v1", event())
        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.topic, "policy.lifecycle.v1")

    def test_deduplicates_event_id_and_idempotency_key(self) -> None:
        first = self.ingress.ingest("policy.lifecycle.v1", event())
        second = self.ingress.ingest("policy.lifecycle.v1", event())
        self.assertEqual(first.status, "accepted")
        self.assertEqual(second.status, "duplicate")

    def test_routes_invalid_event_to_dead_letter_topic(self) -> None:
        invalid = event()
        invalid["schema_version"] = "9.0.0"
        result = self.ingress.ingest("policy.lifecycle.v1", invalid)
        self.assertEqual(result.status, "dead_letter")
        self.assertEqual(result.topic, "policy.lifecycle.v1.dlq")

    def test_rejects_wrong_domain_topic(self) -> None:
        result = self.ingress.ingest("billing.payment.v1", event())
        self.assertEqual(result.status, "dead_letter")
        self.assertEqual(result.topic, "billing.payment.v1.dlq")

    def test_unknown_topic_is_dead_lettered(self) -> None:
        result = self.ingress.ingest("unknown.v1", event())
        self.assertEqual(result.status, "dead_letter")
        self.assertEqual(result.topic, "unknown.v1.dlq")


class PointInTimeEventBufferTest(unittest.TestCase):
    def test_visibility_is_independent_of_arrival_order(self) -> None:
        first = event()
        first["event_id"] = "evt_123456789abd"
        first["effective_at"] = "2026-01-02T00:00:00Z"
        second = event()
        second["event_id"] = "evt_123456789abe"
        second["effective_at"] = "2026-01-01T00:00:00Z"

        buffer = PointInTimeEventBuffer()
        buffer.append(first)
        buffer.append(second)
        self.assertEqual(
            [item["event_id"] for item in buffer.visible_events("2026-01-03T00:00:00Z")],
            ["evt_123456789abe", "evt_123456789abd"],
        )

    def test_late_ingestion_remains_invisible_at_cutoff(self) -> None:
        late = event()
        late["ingested_at"] = "2026-01-03T00:00:00Z"
        buffer = PointInTimeEventBuffer()
        buffer.append(late)
        self.assertEqual(buffer.visible_events("2026-01-02T00:00:00Z"), ())

    def test_conflicting_event_id_is_rejected(self) -> None:
        original = event()
        changed = event()
        changed["payload"] = {"status": "terminated"}
        buffer = PointInTimeEventBuffer()
        buffer.append(original)
        with self.assertRaises(ValueError):
            buffer.append(changed)


if __name__ == "__main__":
    unittest.main()
