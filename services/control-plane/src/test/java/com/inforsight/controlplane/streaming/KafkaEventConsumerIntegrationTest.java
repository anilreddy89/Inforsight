package com.inforsight.controlplane.streaming;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assumptions;
import org.testcontainers.kafka.KafkaContainer;
import org.testcontainers.utility.DockerImageName;

import java.time.Duration;
import java.util.Properties;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class KafkaEventConsumerIntegrationTest {
    private static final String TOPIC = "policy.lifecycle.v1";

    @Test
    void consumesAndDeduplicatesARealKafkaEnvelope() throws Exception {
        Assumptions.assumeTrue("1".equals(System.getenv("INFORSIGHT_RUN_P4_07_INTEGRATION")));
        String externalBootstrap = System.getenv("INFORSIGHT_P4_07_KAFKA_BOOTSTRAP_SERVERS");
        if (externalBootstrap != null && !externalBootstrap.isBlank()) {
            exercise(externalBootstrap);
            return;
        }
        DockerImageName image = DockerImageName.parse("confluentinc/cp-kafka:7.6.0")
                .asCompatibleSubstituteFor("apache/kafka");
        try (KafkaContainer kafka = new KafkaContainer(image)) {
            kafka.start();
            exercise(kafka.getBootstrapServers());
        }
    }

    @Test
    void consumesTheFrozenP407EventCardinalityAboveTheThroughputFloor() throws Exception {
        Assumptions.assumeTrue("1".equals(System.getenv("INFORSIGHT_RUN_P4_07_INTEGRATION")));
        String externalBootstrap = System.getenv("INFORSIGHT_P4_07_KAFKA_BOOTSTRAP_SERVERS");
        Assumptions.assumeTrue(externalBootstrap != null && !externalBootstrap.isBlank(),
                "The 200,000-event run requires an explicit Compose Kafka bootstrap endpoint");
        BoundedStreamingEventHandler handler = new BoundedStreamingEventHandler(new ObjectMapper());
        KafkaEventConsumer consumer = new KafkaEventConsumer(
                handler, externalBootstrap, "p4-07-throughput-" + UUID.randomUUID(), TOPIC);
        consumer.start();
        final int eventCount = 200_000;
        long baseline = handler.acceptedCount();
        long started = System.nanoTime();
        try (KafkaProducer<String, String> producer = producer(externalBootstrap)) {
            for (int index = 0; index < eventCount; index++) {
                String eventId = String.format("evt_p407_%012d", index);
                String event = "{\"schema_version\":\"1.0.0\",\"event_id\":\"" + eventId
                        + "\",\"idempotency_key\":\"idem_p407_" + index
                        + "\",\"policy_id\":\"p407-policy-" + index
                        + "\",\"event_type\":\"policy.issued\"}";
                producer.send(new ProducerRecord<>(TOPIC, eventId, event));
            }
            producer.flush();
        }
        long deadline = System.nanoTime() + Duration.ofSeconds(90).toNanos();
        while (handler.acceptedCount() < baseline + eventCount && System.nanoTime() < deadline) {
            Thread.sleep(100);
        }
        long elapsedNanos = System.nanoTime() - started;
        consumer.stop();
        assertThat(handler.acceptedCount()).isGreaterThanOrEqualTo(baseline + eventCount);
        double eventsPerSecond = eventCount / (elapsedNanos / 1_000_000_000.0);
        System.out.printf("P4-07 E1 observed throughput: %.2f events/sec; accepted=%d%n", eventsPerSecond, handler.acceptedCount() - baseline);
        assertThat(eventsPerSecond).isGreaterThanOrEqualTo(5_000.0);
    }

    @Test
    void restartsTheConsumerGroupWithoutLosingTheBoundedEventSet() throws Exception {
        Assumptions.assumeTrue("1".equals(System.getenv("INFORSIGHT_RUN_P4_07_INTEGRATION")));
        String externalBootstrap = System.getenv("INFORSIGHT_P4_07_KAFKA_BOOTSTRAP_SERVERS");
        Assumptions.assumeTrue(externalBootstrap != null && !externalBootstrap.isBlank(),
                "The restart/replay run requires an explicit Compose Kafka bootstrap endpoint");

        final int eventCount = 4_000;
        String groupId = "p4-07-restart-" + UUID.randomUUID();
        try (KafkaProducer<String, String> producer = producer(externalBootstrap)) {
            for (int index = 0; index < eventCount; index++) {
                String eventId = "evt_p407_restart_" + index;
                String event = "{\"schema_version\":\"1.0.0\",\"event_id\":\"" + eventId
                        + "\",\"idempotency_key\":\"idem_p407_restart_" + index
                        + "\",\"policy_id\":\"p407-restart-policy-" + index
                        + "\",\"event_type\":\"policy.issued\"}";
                producer.send(new ProducerRecord<>(TOPIC, eventId, event));
            }
            producer.flush();
        }

        BoundedStreamingEventHandler firstHandler = new BoundedStreamingEventHandler(new ObjectMapper());
        KafkaEventConsumer firstConsumer = new KafkaEventConsumer(firstHandler, externalBootstrap, groupId, TOPIC);
        firstConsumer.start();
        try {
            long deadline = System.nanoTime() + Duration.ofSeconds(15).toNanos();
            while (firstHandler.acceptedCount() < eventCount / 2 && System.nanoTime() < deadline) {
                Thread.sleep(50);
            }
        } finally {
            firstConsumer.stop();
        }

        BoundedStreamingEventHandler resumedHandler = new BoundedStreamingEventHandler(new ObjectMapper());
        KafkaEventConsumer resumedConsumer = new KafkaEventConsumer(resumedHandler, externalBootstrap, groupId, TOPIC);
        resumedConsumer.start();
        try {
            long deadline = System.nanoTime() + Duration.ofSeconds(30).toNanos();
            while (firstHandler.acceptedCount() + resumedHandler.acceptedCount() < eventCount
                    && System.nanoTime() < deadline) {
                Thread.sleep(50);
            }
        } finally {
            resumedConsumer.stop();
        }

        assertThat(firstHandler.acceptedCount() + resumedHandler.acceptedCount()).isEqualTo(eventCount);
    }

    private static void exercise(String bootstrapServers) throws Exception {
            BoundedStreamingEventHandler handler = new BoundedStreamingEventHandler(new ObjectMapper());
            KafkaEventConsumer consumer = new KafkaEventConsumer(handler, bootstrapServers, "p4-07-test-group", TOPIC);
            consumer.start();
            try (KafkaProducer<String, String> producer = producer(bootstrapServers)) {
                String event = "{\"schema_version\":\"1.0.0\",\"event_id\":\"evt_000000000001\",\"idempotency_key\":\"idem-1\",\"policy_id\":\"policy-1\",\"event_type\":\"policy.issued\"}";
                producer.send(new ProducerRecord<>(TOPIC, "evt_000000000001", event)).get();
                producer.send(new ProducerRecord<>(TOPIC, "evt_000000000001", event)).get();
                long deadline = System.nanoTime() + Duration.ofSeconds(15).toNanos();
                while (handler.acceptedCount() < 1 && System.nanoTime() < deadline) {
                    Thread.sleep(100);
                }
                assertThat(handler.acceptedCount()).isOne();
            } finally {
                consumer.stop();
            }
    }

    private static KafkaProducer<String, String> producer(String bootstrapServers) {
        Properties properties = new Properties();
        properties.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        properties.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        properties.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        return new KafkaProducer<>(properties);
    }
}
