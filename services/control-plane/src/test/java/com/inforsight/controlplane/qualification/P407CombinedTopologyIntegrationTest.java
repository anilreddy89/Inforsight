package com.inforsight.controlplane.qualification;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.audit.AuditEvent;
import com.inforsight.controlplane.audit.AuditHash;
import com.inforsight.controlplane.audit.AuditLedgerCheckpoint;
import com.inforsight.controlplane.audit.AuditLedgerEntry;
import com.inforsight.controlplane.audit.AuditLedgerRepository;
import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.domain.InferenceScore;
import com.inforsight.controlplane.inference.HttpInferenceClient;
import com.inforsight.controlplane.streaming.KafkaEventConsumer;
import com.inforsight.controlplane.streaming.BatchStreamingEventHandler;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/** Combined capability binding; this is a smoke run, not the scale gate. */
class P407CombinedTopologyIntegrationTest {

    @Test
    void bindsKafkaInferenceCaseAndPostgresAuditInOneRun() throws Exception {
        Assumptions.assumeTrue("1".equals(System.getenv("INFORSIGHT_RUN_P4_07_COMBINED_INTEGRATION")));
        String kafka = required("INFORSIGHT_P4_07_KAFKA_BOOTSTRAP_SERVERS");
        String inferenceUrl = required("INFORSIGHT_P4_07_INFERENCE_BASE_URL");
        String jdbcUrl = env("INFORSIGHT_P4_07_POSTGRES_JDBC_URL", "jdbc:postgresql://localhost:5433/inforsight_enterprise");
        String username = env("INFORSIGHT_P4_07_POSTGRES_USERNAME", "inforsight_app");
        String password = env("INFORSIGHT_P4_07_POSTGRES_PASSWORD", "dev_insecure_local_password");
        Flyway.configure().dataSource(jdbcUrl, username, password).locations("classpath:db/migration").load().migrate();

        ObjectMapper mapper = new ObjectMapper();
        JdbcTemplate jdbc = new JdbcTemplate(new DriverManagerDataSource(jdbcUrl, username, password));
        AuditLedgerRepository ledger = new AuditLedgerRepository(jdbc);
        AuditLedgerCheckpoint baseline = ledger.checkpoint();
        HttpInferenceClient inference = new HttpInferenceClient(mapper, inferenceUrl, Duration.ofSeconds(2), 1);
        CaseStore cases = new CaseStore();
        AtomicLong accepted = new AtomicLong();
        CopyOnWriteArrayList<Long> latencies = new CopyOnWriteArrayList<>();
        CopyOnWriteArrayList<Throwable> failures = new CopyOnWriteArrayList<>();
        CopyOnWriteArrayList<AuditLedgerEntry> committedEntries = new CopyOnWriteArrayList<>();
        String runToken = UUID.randomUUID().toString();
        String topic = "p4_07_combined_" + runToken.replace("-", "").substring(0, 20);
        ExecutorService inferenceExecutor = Executors.newVirtualThreadPerTaskExecutor();
        record Prepared(String policyId, String eventId, long ingressNanos, InferenceScore score) {}
        BatchStreamingEventHandler handler = new BatchStreamingEventHandler() {
            @Override
            public boolean handle(String topicName, String key, String value) {
                handleBatch(List.of(new StreamingRecord(topicName, key, value)));
                return true;
            }

            @Override
            public void handleBatch(List<StreamingRecord> records) {
                try {
                    List<Future<Prepared>> futures = records.stream().map(record -> inferenceExecutor.submit(() -> {
                        JsonNode event = mapper.readTree(record.value());
                        String policyId = event.get("policy_id").asText();
                        InferenceScore score = inference.scoreWithFeatures(policyId,
                                Instant.parse("2026-09-18T00:00:00Z"), features());
                        return new Prepared(policyId, event.get("event_id").asText(),
                                event.get("ingress_nanos").asLong(), score);
                    })).toList();
                    List<Prepared> prepared = new ArrayList<>();
                    for (Future<Prepared> future : futures) prepared.add(future.get());
                    List<AuditEvent> audits = new ArrayList<>();
                    for (Prepared item : prepared) {
                        cases.create(item.policyId(), Instant.parse("2026-09-18T00:00:00Z"), item.score(), "abstain");
                        audits.add(new AuditEvent(UUID.randomUUID(), item.policyId(), 0, "P407_COMBINED_CASE_SCORED",
                                "p407-qualification", Instant.now(), Map.of("event_id", item.eventId(), "authorized_to_act", false)));
                    }
                    committedEntries.addAll(ledger.appendBatch(audits));
                    for (Prepared item : prepared) latencies.add(System.nanoTime() - item.ingressNanos());
                    accepted.addAndGet(prepared.size());
                } catch (Exception failure) {
                    failures.add(failure);
                    throw new IllegalStateException("combined qualification batch failed", failure);
                }
            }
        };
        String groupId = "p4-07-combined-" + UUID.randomUUID();
        String warmupId = "evt_p407_combined_warmup_" + runToken;
        try (KafkaProducer<String, String> producer = producer(kafka)) {
            producer.send(new ProducerRecord<>(topic, warmupId,
                    event(warmupId, "p407-combined-warmup-" + runToken, System.nanoTime()))).get();
            producer.flush();
        }
        KafkaEventConsumer consumer = new KafkaEventConsumer(handler, kafka, groupId, topic, "latest", 500);
        consumer.start();
        final int eventCount = 100;
        try (KafkaProducer<String, String> producer = producer(kafka)) {
            Thread.sleep(2_000);
            for (int index = 0; index < eventCount; index++) {
                String eventId = "evt_p407_combined_" + runToken + "_" + index;
                String event = event(eventId, "p407-combined-policy-" + runToken + "-" + index, System.nanoTime());
                producer.send(new ProducerRecord<>(topic, eventId, event));
            }
            producer.flush();
        }
        long deadline = System.nanoTime() + Duration.ofSeconds(45).toNanos();
        while (accepted.get() < eventCount && System.nanoTime() < deadline) Thread.sleep(50);
        consumer.stop();
        inferenceExecutor.close();

        assertThat(failures).isEmpty();
        assertThat(accepted).hasValue(eventCount);
        assertThat(latencies).hasSize(eventCount);
        ArrayList<Long> ordered = new ArrayList<>(latencies);
        ordered.sort(Long::compareTo);
        double p99Millis = ordered.get((int) Math.ceil(ordered.size() * 0.99) - 1) / 1_000_000.0;
        System.out.printf("P4-07 combined capability smoke: accepted=%d, p99 ingress-to-audit=%.3f ms%n",
                accepted.get(), p99Millis);
        assertThat(p99Millis).isPositive();
        assertThat(verifyTail(committedEntries, baseline)).isTrue();
    }

    private static KafkaProducer<String, String> producer(String bootstrap) {
        Properties properties = new Properties();
        properties.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
        properties.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        properties.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        return new KafkaProducer<>(properties);
    }

    private static Map<String, Object> features() {
        return Map.ofEntries(Map.entry("tenure_days", 365.0), Map.entry("premium_amount_cents", 1000.0),
                Map.entry("recent_delay_days", 0.0), Map.entry("recent_failed_payment_count", 0.0),
                Map.entry("recent_retry_count", 0.0), Map.entry("recent_recovery_count", 1.0),
                Map.entry("arrears_duration_days", 0.0), Map.entry("rolling_on_time_rate", 1.0),
                Map.entry("rolling_payment_count", 12.0), Map.entry("recent_notice_count", 0.0),
                Map.entry("recent_contact_count", 0.0), Map.entry("payment_attribute_missing", 0.0),
                Map.entry("contact_attribute_missing", 0.0), Map.entry("product_type", "fictional_term_life"),
                Map.entry("billing_frequency", "monthly"), Map.entry("notice_category", "none"),
                Map.entry("contact_category", "none"));
    }

    private static String event(String eventId, String policyId, long ingressNanos) {
        return "{\"schema_version\":\"1.0.0\",\"event_id\":\"" + eventId
                + "\",\"idempotency_key\":\"idem_" + eventId
                + "\",\"policy_id\":\"" + policyId
                + "\",\"event_type\":\"policy.issued\",\"ingress_nanos\":" + ingressNanos + "}";
    }

    private static boolean verifyTail(List<AuditLedgerEntry> entries, AuditLedgerCheckpoint baseline) {
        String parent = baseline.currentHash();
        long sequence = baseline.sequence() + 1;
        for (AuditLedgerEntry entry : entries) {
            if (entry.sequence() != sequence || !parent.equals(entry.parentHash())) return false;
            if (!AuditHash.chainHash(entry.parentHash(), entry.canonicalPayload()).equals(entry.currentHash())) return false;
            parent = entry.currentHash();
            sequence++;
        }
        return !entries.isEmpty();
    }

    private static String required(String name) {
        String value = System.getenv(name);
        Assumptions.assumeTrue(value != null && !value.isBlank(), name + " is required");
        return value;
    }

    private static String env(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : value;
    }
}
