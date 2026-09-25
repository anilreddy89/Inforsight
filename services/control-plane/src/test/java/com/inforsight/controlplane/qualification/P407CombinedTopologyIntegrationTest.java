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
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.AdminClientConfig;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import com.zaxxer.hikari.HikariDataSource;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Properties;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.LockSupport;

import static org.assertj.core.api.Assertions.assertThat;

/** Combined capability binding; this is a smoke run, not the scale gate. */
class P407CombinedTopologyIntegrationTest {
    private static final String WORKLOAD_NAMESPACE = "p4-07-enterprise-scale-synthetic";
    private static final String FROZEN_WORKLOAD_SHA256 =
            "c2cc1d0b524dc2b2bdd7e342adb7a63040d8429be2175403369309fb2e031a33";

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
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setJdbcUrl(jdbcUrl);
        dataSource.setUsername(username);
        dataSource.setPassword(password);
        dataSource.setMaximumPoolSize(4);
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        TransactionTemplate transactions = new TransactionTemplate(new DataSourceTransactionManager(dataSource));
        AuditLedgerRepository ledger = new AuditLedgerRepository(jdbc);
        AuditLedgerCheckpoint baseline = ledger.checkpoint();
        HttpInferenceClient inference = new HttpInferenceClient(mapper, inferenceUrl, Duration.ofSeconds(2), 1);
        CaseStore cases = new CaseStore();
        AtomicLong accepted = new AtomicLong();
        AtomicLong warmupProcessed = new AtomicLong();
        List<Long> latencies = Collections.synchronizedList(new ArrayList<>());
        List<Long> ingressToHandlerDurations = Collections.synchronizedList(new ArrayList<>());
        List<Long> inferenceDurations = Collections.synchronizedList(new ArrayList<>());
        List<Long> postInferenceDurations = Collections.synchronizedList(new ArrayList<>());
        List<Integer> batchSizes = Collections.synchronizedList(new ArrayList<>());
        record StageSample(String eventId, long ingressNanos, long total, long ingressToHandler, long requestPrep,
                           long inference, long postInference, int batchSize) {}
        List<StageSample> stageSamples = Collections.synchronizedList(new ArrayList<>());
        ConcurrentHashMap<String, Long> producerAcknowledgements = new ConcurrentHashMap<>();
        CopyOnWriteArrayList<Exception> producerFailures = new CopyOnWriteArrayList<>();
        List<Long> auditDurations = Collections.synchronizedList(new ArrayList<>());
        CopyOnWriteArrayList<Throwable> failures = new CopyOnWriteArrayList<>();
        List<AuditLedgerEntry> committedEntries = Collections.synchronizedList(new ArrayList<>());
        CopyOnWriteArrayList<Throwable> auditFailures = new CopyOnWriteArrayList<>();
        String runToken = UUID.randomUUID().toString();
        String topic = "p4_07_combined_" + runToken.replace("-", "").substring(0, 20);
        String warmupId = "evt_p407_combined_warmup_" + runToken;
        final int partitionCount = Integer.parseInt(env("INFORSIGHT_P4_07_PARTITION_COUNT", "4"));
        if (partitionCount < 1 || partitionCount > 16) {
            throw new IllegalArgumentException("partition count must be between 1 and 16");
        }
        record Prepared(String policyId, String eventId, long ingressNanos, InferenceScore score,
                        boolean warmup) {}
        AsyncAuditWriter auditWriter = new AsyncAuditWriter(transactions, ledger, committedEntries,
                auditDurations, auditFailures);
        AtomicLong lastCaseCompletedNanos = new AtomicLong();
        BatchStreamingEventHandler handler = new BatchStreamingEventHandler() {
            @Override
            public boolean handle(String topicName, String key, String value) {
                handleBatch(List.of(new StreamingRecord(topicName, key, value)));
                return true;
            }

            @Override
            public void handleBatch(List<StreamingRecord> records) {
                try {
                    long handlerStarted = System.nanoTime();
                    List<JsonNode> events = new ArrayList<>();
                    List<HttpInferenceClient.InferenceRequest> requests = new ArrayList<>();
                    int measuredCount = 0;
                    for (StreamingRecord record : records) {
                        JsonNode event = mapper.readTree(record.value());
                        events.add(event);
                        if (!event.get("event_id").asText().startsWith(warmupId)) {
                            measuredCount++;
                            ingressToHandlerDurations.add(handlerStarted - event.get("ingress_nanos").asLong());
                        }
                        requests.add(new HttpInferenceClient.InferenceRequest(event.get("policy_id").asText(),
                                Instant.parse("2026-09-18T00:00:00Z"), features()));
                    }
                    long inferenceStarted = System.nanoTime();
                    List<InferenceScore> scores = inference.scoreMinimalBatchWithFeatures(requests);
                    long inferenceCompleted = System.nanoTime();
                    List<Prepared> prepared = new ArrayList<>();
                    for (int index = 0; index < events.size(); index++) {
                        JsonNode event = events.get(index);
                        prepared.add(new Prepared(requests.get(index).policyId(), event.get("event_id").asText(),
                                event.get("ingress_nanos").asLong(), scores.get(index),
                                event.get("event_id").asText().startsWith(warmupId)));
                    }
                    List<AuditEvent> audits = new ArrayList<>();
                    for (Prepared item : prepared) {
                        var scoredCase = cases.create(item.policyId(), Instant.parse("2026-09-18T00:00:00Z"),
                                item.score(), "abstain");
                        audits.add(new AuditEvent(UUID.randomUUID(), scoredCase.caseId(), 0,
                                "P407_COMBINED_CASE_SCORED", "p407-qualification", Instant.now(),
                                Map.of("event_id", item.eventId(), "authorized_to_act", false)));
                    }
                    long caseCompleted = System.nanoTime();
                    if (measuredCount > 0) {
                        batchSizes.add(measuredCount);
                        inferenceDurations.add(inferenceCompleted - inferenceStarted);
                        postInferenceDurations.add(caseCompleted - inferenceCompleted);
                        for (Prepared item : prepared) {
                            if (item.warmup()) continue;
                            long total = caseCompleted - item.ingressNanos();
                            latencies.add(total);
                            stageSamples.add(new StageSample(item.eventId(), item.ingressNanos(), total,
                                    handlerStarted - item.ingressNanos(), inferenceStarted - handlerStarted,
                                    inferenceCompleted - inferenceStarted, caseCompleted - inferenceCompleted,
                                    measuredCount));
                        }
                    }
                    auditWriter.submit(audits);
                    accepted.addAndGet(measuredCount);
                    if (measuredCount > 0) lastCaseCompletedNanos.accumulateAndGet(caseCompleted, Math::max);
                    warmupProcessed.addAndGet(prepared.size() - measuredCount);
                } catch (Exception failure) {
                    failures.add(failure);
                    throw new IllegalStateException("combined qualification batch failed", failure);
                }
            }
        };
        String groupId = "p4-07-combined-" + UUID.randomUUID();
        createTopic(kafka, topic, partitionCount);
        List<KafkaEventConsumer> consumers = new ArrayList<>();
        int consumerCount = Integer.parseInt(env("INFORSIGHT_P4_07_CONSUMER_COUNT", "4"));
        int maxPollRecords = Integer.parseInt(env("INFORSIGHT_P4_07_MAX_POLL_RECORDS", "500"));
        int fetchMinBytes = Integer.parseInt(env("INFORSIGHT_P4_07_FETCH_MIN_BYTES", "1"));
        int fetchMaxWaitMillis = Integer.parseInt(env("INFORSIGHT_P4_07_FETCH_MAX_WAIT_MS", "5"));
        if (consumerCount < 1 || consumerCount > partitionCount) {
            throw new IllegalArgumentException("consumer count must be between 1 and " + partitionCount);
        }
        if (maxPollRecords < 1 || maxPollRecords > 500) {
            throw new IllegalArgumentException("max poll records must be between 1 and 500");
        }
        for (int index = 0; index < consumerCount; index++) {
            KafkaEventConsumer consumer = new KafkaEventConsumer(handler, kafka, groupId, topic, "earliest", maxPollRecords,
                    fetchMinBytes, fetchMaxWaitMillis);
            consumer.start();
            consumers.add(consumer);
        }
        final int eventCount = Integer.parseInt(env("INFORSIGHT_P4_07_MEASURED_EVENT_COUNT", "100"));
        if (eventCount < 1 || eventCount > 200_000) {
            throw new IllegalArgumentException("measured event count must be between 1 and 200000");
        }
        final int producerBurstSize = Integer.parseInt(env("INFORSIGHT_P4_07_PRODUCER_BURST_SIZE", "0"));
        final int producerBurstIntervalMillis = Integer.parseInt(
                env("INFORSIGHT_P4_07_PRODUCER_BURST_INTERVAL_MS", "0"));
        if ((producerBurstSize == 0) != (producerBurstIntervalMillis == 0)
                || producerBurstSize < 0 || producerBurstIntervalMillis < 0) {
            throw new IllegalArgumentException("producer burst size and interval must both be positive or both zero");
        }
        final int warmupCount = 100;
        int warmupAuditSampleCount;
        MessageDigest eventIdDigest = MessageDigest.getInstance("SHA-256");
        MessageDigest workloadDigest = MessageDigest.getInstance("SHA-256");
        String[] policyIds = new String[eventCount];
        String[] eventIds = new String[eventCount];
        for (int index = 0; index < eventCount; index++) {
            String policyId = WORKLOAD_NAMESPACE + ":policy:"
                    + String.format(Locale.ROOT, "%06d", index / 2);
            int eventNumber = index % 2;
            String eventId = HexFormat.of().formatHex(eventIdDigest.digest(
                    ("4072026:" + policyId + ":" + eventNumber).getBytes(StandardCharsets.UTF_8)));
            policyIds[index] = policyId;
            eventIds[index] = eventId;
            workloadDigest.update(("{\"event_id\":\"" + eventId + "\",\"event_number\":" + eventNumber
                    + ",\"policy_id\":\"" + policyId + "\"}").getBytes(StandardCharsets.UTF_8));
        }
        String observedWorkloadSha256 = HexFormat.of().formatHex(workloadDigest.digest());
        if (eventCount == 200_000) assertThat(observedWorkloadSha256).isEqualTo(FROZEN_WORKLOAD_SHA256);
        try (KafkaProducer<String, String> producer = producer(kafka)) {
            Thread.sleep(5_000);
            for (int index = 0; index < warmupCount; index++) {
                String eventId = warmupId + "_" + index;
                producer.send(new ProducerRecord<>(topic, index % partitionCount, eventId,
                        event(eventId, "p407-combined-warmup-policy-" + runToken + "-" + index,
                                System.nanoTime())));
            }
            producer.flush();
            long warmupDeadline = System.nanoTime() + Duration.ofSeconds(20).toNanos();
            while ((warmupProcessed.get() < warmupCount || committedEntries.size() < warmupCount)
                    && System.nanoTime() < warmupDeadline) Thread.sleep(5);
            assertThat(warmupProcessed).as("warm-up events must traverse Kafka, inference, and case creation")
                    .hasValue(warmupCount);
            assertThat(committedEntries).as("warm-up audit entries must drain before measurement")
                    .hasSize(warmupCount);
            warmupAuditSampleCount = auditDurations.size();
            long measuredStarted = System.nanoTime();
            for (int index = 0; index < eventCount; index++) {
                if (producerBurstSize > 0 && index % producerBurstSize == 0) {
                    long scheduled = measuredStarted + (long) (index / producerBurstSize)
                            * TimeUnit.MILLISECONDS.toNanos(producerBurstIntervalMillis);
                    long remaining;
                    while ((remaining = scheduled - System.nanoTime()) > 0) LockSupport.parkNanos(remaining);
                }
                String eventId = eventIds[index];
                String event = event(eventId, policyIds[index], System.nanoTime());
                producer.send(new ProducerRecord<>(topic, index % partitionCount, eventId, event),
                        (metadata, failure) -> {
                            if (failure == null) producerAcknowledgements.put(eventId, System.nanoTime());
                            else producerFailures.add(failure);
                        });
            }
            producer.flush();
            System.out.printf("P4-07 combined workload: run-id=%s, policies=%d, events=%d, sha256=%s%n",
                    runToken, (eventCount + 1) / 2, eventCount, observedWorkloadSha256);
            long deadline = System.nanoTime() + Duration.ofSeconds(Math.max(45, 30 + eventCount / 1_000)).toNanos();
            while (accepted.get() < eventCount && System.nanoTime() < deadline
                    && failures.isEmpty() && auditFailures.isEmpty()
                    && consumers.stream().noneMatch(consumer -> consumer.terminalFailure() != null)) Thread.sleep(50);
            if (accepted.get() == eventCount) {
                double scoredEventsPerSecond = eventCount * 1_000_000_000.0
                        / (lastCaseCompletedNanos.get() - measuredStarted);
                System.out.printf("P4-07 combined throughput: scored-events-per-second=%.2f; "
                                + "measured-events=%d; producer-burst=%d; burst-interval-ms=%d%n",
                        scoredEventsPerSecond, eventCount, producerBurstSize, producerBurstIntervalMillis);
            }
        }
        consumers.forEach(KafkaEventConsumer::stop);
        auditWriter.close();

        consumers.forEach(consumer -> assertThat(consumer.terminalFailure())
                .as("Kafka consumer terminal failure").isNull());
        assertThat(failures).isEmpty();
        assertThat(producerFailures).isEmpty();
        assertThat(producerAcknowledgements).hasSize(eventCount);
        assertThat(auditFailures).isEmpty();
        assertThat(accepted).hasValue(eventCount);
        assertThat(latencies).hasSize(eventCount);
        assertThat(committedEntries).hasSize(warmupCount + eventCount);
        ArrayList<Long> ordered = new ArrayList<>(latencies);
        ordered.sort(Long::compareTo);
        double p99Millis = ordered.get((int) Math.ceil(ordered.size() * 0.99) - 1) / 1_000_000.0;
        System.out.printf("P4-07 combined capability smoke: accepted=%d, p99 ingress-to-scored-case=%.3f ms%n",
                accepted.get(), p99Millis);
        System.out.printf("P4-07 combined timing: inference-batch=%.3f ms, case-audit=%.3f ms%n",
                percentileMillis(inferenceDurations, 0.99),
                percentileMillis(auditDurations.subList(warmupAuditSampleCount, auditDurations.size()), 0.99));
        System.out.printf("P4-07 combined stages: ingress-to-handler p99=%.3f ms, inference-batch p99=%.3f ms, "
                        + "post-inference-to-case p99=%.3f ms; partitions=%d, consumers=%d, fetch-min-bytes=%d, "
                        + "fetch-max-wait-ms=%d, max-poll-records=%d, batches=%d, max-batch=%d%n",
                percentileMillis(ingressToHandlerDurations, 0.99), percentileMillis(inferenceDurations, 0.99),
                percentileMillis(postInferenceDurations, 0.99), partitionCount, consumerCount, fetchMinBytes,
                fetchMaxWaitMillis, maxPollRecords, batchSizes.size(),
                batchSizes.stream().mapToInt(Integer::intValue).max().orElse(0));
        List<Long> ingressToAck = stageSamples.stream()
                .map(sample -> producerAcknowledgements.get(sample.eventId()) - sample.ingressNanos()).toList();
        List<Long> ackToHandler = stageSamples.stream()
                .map(sample -> sample.ingressNanos() + sample.ingressToHandler()
                        - producerAcknowledgements.get(sample.eventId())).toList();
        System.out.printf("P4-07 producer/consumer stages: ingress-to-ack p99=%.3f ms, "
                        + "ack-to-handler p99=%.3f ms%n",
                percentileMillis(ingressToAck, 0.99), percentileMillis(ackToHandler, 0.99));
        stageSamples.stream().sorted(Comparator.comparingLong(StageSample::total).reversed()).limit(3)
                .forEach(sample -> System.out.printf(
                        "P4-07 tail event=%s total=%.3f ms ingress-to-handler=%.3f ms prep=%.3f ms "
                                + "inference=%.3f ms post=%.3f ms batch=%d ack=%.3f ms%n",
                        sample.eventId(), sample.total() / 1_000_000.0,
                        sample.ingressToHandler() / 1_000_000.0, sample.requestPrep() / 1_000_000.0,
                        sample.inference() / 1_000_000.0, sample.postInference() / 1_000_000.0,
                        sample.batchSize(),
                        (producerAcknowledgements.get(sample.eventId()) - sample.ingressNanos()) / 1_000_000.0));
        assertThat(p99Millis).isPositive();
        ArrayList<AuditLedgerEntry> orderedEntries = new ArrayList<>(committedEntries);
        orderedEntries.sort(Comparator.comparingLong(AuditLedgerEntry::sequence));
        assertThat(verifyTail(orderedEntries, baseline)).isTrue();
        AuditLedgerCheckpoint ending = ledger.checkpoint();
        AuditLedgerEntry finalEntry = orderedEntries.get(orderedEntries.size() - 1);
        assertThat(ending.sequence()).isEqualTo(finalEntry.sequence());
        assertThat(ending.currentHash()).isEqualTo(finalEntry.currentHash());
    }

    private static void createTopic(String bootstrap, String topic, int partitions) throws Exception {
        Properties properties = new Properties();
        properties.put(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
        try (AdminClient admin = AdminClient.create(properties)) {
            admin.createTopics(List.of(new NewTopic(topic, partitions, (short) 1))).all().get();
        }
    }

    /** Single ordered writer keeps audit durability without blocking scored-case completion. */
    private static final class AsyncAuditWriter implements AutoCloseable {
        private record Pending(List<AuditEvent> events) {}

        private final TransactionTemplate transactions;
        private final AuditLedgerRepository ledger;
        private final List<AuditLedgerEntry> committedEntries;
        private final List<Long> durations;
        private final CopyOnWriteArrayList<Throwable> failures;
        private final ArrayBlockingQueue<Pending> queue = new ArrayBlockingQueue<>(1_000);
        private final ExecutorService executor = Executors.newSingleThreadExecutor();
        private volatile boolean running = true;

        private AsyncAuditWriter(TransactionTemplate transactions, AuditLedgerRepository ledger,
                                 List<AuditLedgerEntry> committedEntries,
                                 List<Long> durations,
                                 CopyOnWriteArrayList<Throwable> failures) {
            this.transactions = transactions;
            this.ledger = ledger;
            this.committedEntries = committedEntries;
            this.durations = durations;
            this.failures = failures;
            executor.submit(this::run);
        }

        private void submit(List<AuditEvent> events) throws InterruptedException {
            if (!failures.isEmpty()) throw new IllegalStateException("audit writer failed", failures.get(0));
            Pending pending = new Pending(List.copyOf(events));
            while (!queue.offer(pending, 100, TimeUnit.MILLISECONDS)) {
                if (!failures.isEmpty()) throw new IllegalStateException("audit writer failed", failures.get(0));
            }
        }

        private void run() {
            try {
                while (running || !queue.isEmpty()) {
                    Pending first = queue.poll(100, TimeUnit.MILLISECONDS);
                    if (first == null) continue;
                    List<AuditEvent> events = new ArrayList<>(first.events());
                    long deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(2);
                    while (events.size() < 500 && System.nanoTime() < deadline) {
                        Pending next = queue.poll(Math.max(1, deadline - System.nanoTime()), TimeUnit.NANOSECONDS);
                        if (next == null) break;
                        events.addAll(next.events());
                    }
                    long started = System.nanoTime();
                    List<AuditLedgerEntry> appended = transactions.execute(status -> ledger.appendBatch(events));
                    if (appended == null) throw new IllegalStateException("audit transaction returned no entries");
                    durations.add(System.nanoTime() - started);
                    committedEntries.addAll(appended);
                }
            } catch (Throwable failure) {
                failures.add(failure);
                System.err.printf("P4-07 audit writer failure: %s%n", failure);
            }
        }

        @Override
        public void close() {
            running = false;
            executor.close();
        }
    }

    private static KafkaProducer<String, String> producer(String bootstrap) {
        Properties properties = new Properties();
        properties.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap);
        properties.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        properties.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        properties.put(ProducerConfig.LINGER_MS_CONFIG, env("INFORSIGHT_P4_07_PRODUCER_LINGER_MS", "0"));
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
        long previousSequence = baseline.sequence();
        for (AuditLedgerEntry entry : entries) {
            if (entry.sequence() <= previousSequence || !parent.equals(entry.parentHash())) return false;
            if (!AuditHash.chainHash(entry.parentHash(), entry.canonicalPayload()).equals(entry.currentHash())) return false;
            parent = entry.currentHash();
            previousSequence = entry.sequence();
        }
        return !entries.isEmpty();
    }

    private static double percentileMillis(List<Long> durations, double percentile) {
        ArrayList<Long> ordered = new ArrayList<>(durations);
        ordered.sort(Long::compareTo);
        return ordered.get(Math.max(0, (int) Math.ceil(ordered.size() * percentile) - 1)) / 1_000_000.0;
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
