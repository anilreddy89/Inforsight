package com.inforsight.controlplane.streaming;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Timeout;
import org.testcontainers.kafka.KafkaContainer;
import org.testcontainers.utility.DockerImageName;

import java.time.Duration;
import java.util.Properties;
import java.util.UUID;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

class KafkaEventConsumerIntegrationTest {
    @Test
    void consumesAndDeduplicatesARealKafkaEnvelope() throws Exception {
        Assumptions.assumeTrue("1".equals(System.getenv("INFORSIGHT_RUN_P4_07_INTEGRATION")));
        String externalBootstrap = System.getenv("INFORSIGHT_P4_07_KAFKA_BOOTSTRAP_SERVERS");
        if (externalBootstrap != null && !externalBootstrap.isBlank()) {
            exercise(externalBootstrap, topic("envelope"));
            return;
        }
        DockerImageName image = DockerImageName.parse("confluentinc/cp-kafka:7.6.0")
                .asCompatibleSubstituteFor("apache/kafka");
        try (KafkaContainer kafka = new KafkaContainer(image)) {
            kafka.start();
            exercise(kafka.getBootstrapServers(), topic("envelope"));
        }
    }

    @Test
    @Timeout(value = 120, unit = TimeUnit.SECONDS)
    void consumesTheFrozenP407EventCardinalityAboveTheThroughputFloor() throws Exception {
        Assumptions.assumeTrue("1".equals(System.getenv("INFORSIGHT_RUN_P4_07_INTEGRATION")));
        String externalBootstrap = System.getenv("INFORSIGHT_P4_07_KAFKA_BOOTSTRAP_SERVERS");
        Assumptions.assumeTrue(externalBootstrap != null && !externalBootstrap.isBlank(),
                "The 200,000-event run requires an explicit Compose Kafka bootstrap endpoint");
        String topic = topic("throughput");
        createTopic(externalBootstrap, topic);
        BoundedStreamingEventHandler handler = new BoundedStreamingEventHandler(new ObjectMapper());
        KafkaEventConsumer consumer = new KafkaEventConsumer(
                isolatedHandler(handler, topic), externalBootstrap, "p4-07-throughput-" + UUID.randomUUID(), topic);
        consumer.start();
        final int eventCount = 200_000;
        long baseline = handler.acceptedCount();
        long started = System.nanoTime();
        AtomicInteger acknowledged = new AtomicInteger();
        ConcurrentLinkedQueue<Exception> producerFailures = new ConcurrentLinkedQueue<>();
        try (KafkaProducer<String, String> producer = producer(externalBootstrap)) {
            for (int index = 0; index < eventCount; index++) {
                String eventId = String.format("evt_p407_%012d", index);
                String event = "{\"schema_version\":\"1.0.0\",\"event_id\":\"" + eventId
                        + "\",\"idempotency_key\":\"idem_p407_" + index
                        + "\",\"policy_id\":\"p407-policy-" + index
                        + "\",\"event_type\":\"policy.issued\"}";
                producer.send(new ProducerRecord<>(topic, eventId, event), (metadata, failure) -> {
                    if (failure == null) acknowledged.incrementAndGet();
                    else producerFailures.add(failure);
                });
            }
            producer.flush();
        }
        assertThat(producerFailures).as("producer errors").isEmpty();
        assertThat(acknowledged).as("broker-acknowledged events").hasValue(eventCount);
        long deadline = System.nanoTime() + Duration.ofSeconds(90).toNanos();
        while (handler.acceptedCount() < baseline + eventCount && System.nanoTime() < deadline) {
            Thread.sleep(100);
        }
        long elapsedNanos = System.nanoTime() - started;
        consumer.stop();
        assertThat(consumer.terminalFailure()).isNull();
        assertThat(handler.acceptedCount()).isEqualTo(baseline + eventCount);
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

        String topic = topic("restart");
        createTopic(externalBootstrap, topic);
        final int eventCount = 4_000;
        String groupId = "p4-07-restart-" + UUID.randomUUID();
        AtomicInteger acknowledged = new AtomicInteger();
        ConcurrentLinkedQueue<Exception> producerFailures = new ConcurrentLinkedQueue<>();
        try (KafkaProducer<String, String> producer = producer(externalBootstrap)) {
            for (int index = 0; index < eventCount; index++) {
                String eventId = "evt_p407_restart_" + index;
                String event = "{\"schema_version\":\"1.0.0\",\"event_id\":\"" + eventId
                        + "\",\"idempotency_key\":\"idem_p407_restart_" + index
                        + "\",\"policy_id\":\"p407-restart-policy-" + index
                        + "\",\"event_type\":\"policy.issued\"}";
                producer.send(new ProducerRecord<>(topic, eventId, event), (metadata, failure) -> {
                    if (failure == null) acknowledged.incrementAndGet();
                    else producerFailures.add(failure);
                });
            }
            producer.flush();
        }
        assertThat(producerFailures).as("restart-probe producer errors").isEmpty();
        assertThat(acknowledged).as("restart-probe broker-acknowledged events").hasValue(eventCount);

        BoundedStreamingEventHandler firstHandler = new BoundedStreamingEventHandler(new ObjectMapper());
        KafkaEventConsumer firstConsumer = new KafkaEventConsumer(
                isolatedHandler(firstHandler, topic), externalBootstrap, groupId, topic);
        firstConsumer.start();
        try {
            long deadline = System.nanoTime() + Duration.ofSeconds(15).toNanos();
            while (firstHandler.acceptedCount() < eventCount / 2 && System.nanoTime() < deadline) {
                Thread.sleep(50);
            }
        } finally {
            firstConsumer.stop();
        }
        assertThat(firstConsumer.terminalFailure()).as("first consumer failure").isNull();

        BoundedStreamingEventHandler resumedHandler = new BoundedStreamingEventHandler(new ObjectMapper());
        KafkaEventConsumer resumedConsumer = new KafkaEventConsumer(
                isolatedHandler(resumedHandler, topic), externalBootstrap, groupId, topic);
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

        assertThat(resumedConsumer.terminalFailure()).as("resumed consumer failure").isNull();
        assertThat(firstHandler.acceptedCount() + resumedHandler.acceptedCount()).isEqualTo(eventCount);
    }

    private static void exercise(String bootstrapServers, String topic) throws Exception {
        createTopic(bootstrapServers, topic);
        BoundedStreamingEventHandler handler = new BoundedStreamingEventHandler(new ObjectMapper());
        KafkaEventConsumer consumer = new KafkaEventConsumer(isolatedHandler(handler, topic), bootstrapServers,
                "p4-07-test-group-" + UUID.randomUUID(), topic);
        consumer.start();
        try (KafkaProducer<String, String> producer = producer(bootstrapServers)) {
            String event = "{\"schema_version\":\"1.0.0\",\"event_id\":\"evt_000000000001\",\"idempotency_key\":\"idem-1\",\"policy_id\":\"policy-1\",\"event_type\":\"policy.issued\"}";
            producer.send(new ProducerRecord<>(topic, "evt_000000000001", event)).get();
            producer.send(new ProducerRecord<>(topic, "evt_000000000001", event)).get();
            long deadline = System.nanoTime() + Duration.ofSeconds(15).toNanos();
            while (handler.acceptedCount() < 1 && System.nanoTime() < deadline) {
                Thread.sleep(100);
            }
            assertThat(consumer.terminalFailure()).isNull();
            assertThat(handler.acceptedCount()).isOne();
        } finally {
            consumer.stop();
        }
    }

    private static StreamingEventHandler isolatedHandler(BoundedStreamingEventHandler delegate, String topic) {
        // Production allows only versioned domain topics. This test maps its
        // per-run isolation topic to that domain topic after Kafka delivery.
        return (actualTopic, key, value) -> {
            if (!topic.equals(actualTopic)) throw new IllegalArgumentException("unexpected test topic");
            return delegate.handle("policy.lifecycle.v1", key, value);
        };
    }

    private static String topic(String scenario) {
        return "p4_07_" + scenario + "_" + UUID.randomUUID().toString().replace("-", "");
    }

    private static void createTopic(String bootstrapServers, String topic) throws Exception {
        Properties properties = new Properties();
        properties.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        try (AdminClient admin = AdminClient.create(properties)) {
            admin.createTopics(List.of(new NewTopic(topic, 4, (short) 1))).all().get();
            long deadline = System.nanoTime() + Duration.ofSeconds(10).toNanos();
            while (System.nanoTime() < deadline) {
                var description = admin.describeTopics(List.of(topic)).allTopicNames().get().get(topic);
                if (description != null && description.partitions().size() == 4
                        && description.partitions().stream().allMatch(partition -> partition.leader() != null)) return;
                Thread.sleep(50);
            }
            throw new IllegalStateException("test topic did not acquire four partition leaders: " + topic);
        }
    }

    private static KafkaProducer<String, String> producer(String bootstrapServers) {
        Properties properties = new Properties();
        properties.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        properties.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        properties.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        // This is a synthetic consumer probe, not the production publisher.
        // Avoid local broker idempotent-sequence errors. Allow a bounded retry
        // for leader establishment, but require every send to be acknowledged.
        properties.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "false");
        properties.put(ProducerConfig.RETRIES_CONFIG, "3");
        properties.put(ProducerConfig.ACKS_CONFIG, "all");
        properties.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, "30000");
        properties.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG, "10000");
        properties.put(ProducerConfig.MAX_BLOCK_MS_CONFIG, "30000");
        return new KafkaProducer<>(properties);
    }
}
