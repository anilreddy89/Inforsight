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
