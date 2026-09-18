"""Broker-backed P4-02 acceptance tests.

Run with ``make streaming-integration-check`` after installing the integration
extra. The suite is opt-in because ordinary repository checks do not require a
Docker daemon.
"""

from datetime import datetime, timedelta, timezone
import json
import os
import unittest

try:
    from testcontainers.kafka import KafkaContainer
except ImportError:  # pragma: no cover - exercised only without the optional extra
    KafkaContainer = None

from inforsight_simulator.kafka_adapter import KafkaStreamingAdapter
from inforsight_simulator.streaming import PointInTimeEventBuffer


RUN_INTEGRATION = os.getenv("INFORSIGHT_RUN_KAFKA_INTEGRATION") == "1"
INTEGRATION_AVAILABLE = RUN_INTEGRATION and KafkaContainer is not None


def make_event(index: int, *, schema_version: str = "1.0.0") -> dict:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return {
        "schema_version": schema_version,
        "event_id": f"evt_{index:012x}",
        "idempotency_key": f"integration-source:{index}",
        "policy_id": f"pol_{index % 100:012x}",
        "event_type": "policy.issued",
        "occurred_at": (base + timedelta(seconds=index)).isoformat().replace("+00:00", "Z"),
        "effective_at": (base + timedelta(seconds=index)).isoformat().replace("+00:00", "Z"),
        "ingested_at": (base + timedelta(seconds=20000 + index)).isoformat().replace("+00:00", "Z"),
        "source": "p4-02-testcontainers",
        "payload": {"status": "active", "sequence": index},
    }


@unittest.skipUnless(INTEGRATION_AVAILABLE, "set INFORSIGHT_RUN_KAFKA_INTEGRATION=1 with the integration extra")
class KafkaIntegrationTest(unittest.TestCase):
    def test_dlq_and_10000_event_out_of_order_gate(self) -> None:
        from kafka import KafkaConsumer, KafkaProducer

        with KafkaContainer("confluentinc/cp-kafka:7.6.0") as container:
            bootstrap = container.get_bootstrap_server()
            producer = KafkaProducer(bootstrap_servers=bootstrap)
            topic = "policy.lifecycle.v1"
            dlq_topic = "policy.lifecycle.v1.dlq"
            invalid = make_event(10_000, schema_version="9.0.0")
            producer.send(topic, key=invalid["event_id"].encode(), value=json.dumps(invalid).encode())
            for index in reversed(range(10_000)):
                event = make_event(index)
                producer.send(topic, key=event["event_id"].encode(), value=json.dumps(event).encode())
            producer.flush()

            state = PointInTimeEventBuffer()
            accepted: list[str] = []
            adapter = KafkaStreamingAdapter(producer, state=state, downstream=lambda event: accepted.append(event["event_id"]))
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=bootstrap,
                auto_offset_reset="earliest",
                group_id=None,
                consumer_timeout_ms=60_000,
            )
            statuses: list[str] = []
            for record in consumer:
                result = adapter.process_record(record)
                statuses.append(result.status)
                if len(statuses) == 10_001:
                    break
            consumer.close()
            producer.flush()

            self.assertEqual(statuses.count("accepted"), 10_000)
            self.assertEqual(statuses.count("dead_letter"), 1)
            self.assertEqual(len(accepted), 10_000)
            visible = state.visible_events("2026-01-02T00:00:00Z")
            self.assertEqual(len(visible), 10_000)
            self.assertEqual(
                [event["event_id"] for event in visible],
                [f"evt_{index:012x}" for index in range(10_000)],
            )

            dlq = KafkaConsumer(
                dlq_topic,
                bootstrap_servers=bootstrap,
                auto_offset_reset="earliest",
                group_id=None,
                consumer_timeout_ms=30_000,
            )
            dlq_keys = [record.key.decode() for record in dlq if record.key == invalid["event_id"].encode()]
            dlq.close()
            self.assertEqual(dlq_keys, [invalid["event_id"]])


if __name__ == "__main__":
    unittest.main()
