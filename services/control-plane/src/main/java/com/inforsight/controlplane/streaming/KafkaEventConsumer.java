package com.inforsight.controlplane.streaming;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.errors.WakeupException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.SmartLifecycle;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Arrays;
import java.util.Properties;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Opt-in Kafka ingress seam for the P4-07 execution topology.
 *
 * The consumer is disabled by default. It validates/deduplicates envelopes and
 * commits offsets only after the bounded handler accepts the record. It never
 * dispatches an external action; human review and the existing control-plane
 * authority boundary remain downstream requirements.
 */
@Component
@ConditionalOnProperty(name = "inforsight.streaming.enabled", havingValue = "true")
public final class KafkaEventConsumer implements SmartLifecycle {
    private final KafkaConsumer<String, String> consumer;
    private final StreamingEventHandler handler;
    private final ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
    private volatile boolean running;

    public KafkaEventConsumer(
            StreamingEventHandler handler,
            @Value("${inforsight.streaming.bootstrap-servers:kafka:29092}") String bootstrapServers,
            @Value("${inforsight.streaming.group-id:inforsight-control-plane}") String groupId,
            @Value("${inforsight.streaming.topics:policy.lifecycle.v1,billing.payment.v1,customer.service.v1}") String topics) {
        this.handler = handler;
        Properties properties = new Properties();
        properties.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        properties.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        properties.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, "org.apache.kafka.common.serialization.StringDeserializer");
        properties.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, "org.apache.kafka.common.serialization.StringDeserializer");
        properties.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false");
        properties.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        this.consumer = new KafkaConsumer<>(properties);
        this.consumer.subscribe(Arrays.stream(topics.split(",")).map(String::trim).filter(topic -> !topic.isBlank()).toList());
    }

    @Override
    public void start() {
        running = true;
        executor.submit(this::pollLoop);
    }

    private void pollLoop() {
        try {
            while (running) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(250));
                records.forEach(record -> {
                    handler.handle(record.topic(), record.key(), record.value());
                });
                if (!records.isEmpty()) {
                    consumer.commitSync();
                }
            }
        } catch (WakeupException ignored) {
            // Normal shutdown path.
        } finally {
            consumer.close();
        }
    }

    @Override
    public void stop() {
        running = false;
        consumer.wakeup();
        executor.close();
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    @Override
    public int getPhase() {
        return Integer.MAX_VALUE;
    }
}
