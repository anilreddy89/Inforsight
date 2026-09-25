package com.inforsight.controlplane.streaming;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Validates the shared streaming envelope and deduplicates event/idempotency
 * identities before a downstream consumer is allowed to act on an event.
 * Domain projection and durable persistence remain explicit downstream seams.
 */
@Component
public final class BoundedStreamingEventHandler implements StreamingEventHandler {
    private static final Set<String> ALLOWED_TOPICS = Set.of(
            "policy.lifecycle.v1",
            "billing.payment.v1",
            "customer.service.v1"
    );
    private final ObjectMapper mapper;
    private final Set<String> seenIdentities = ConcurrentHashMap.newKeySet();
    private final AtomicLong accepted = new AtomicLong();

    public BoundedStreamingEventHandler(ObjectMapper mapper) {
        this.mapper = mapper;
    }

    @Override
    public boolean handle(String topic, String key, String value) {
        if (topic == null || !ALLOWED_TOPICS.contains(topic) || value == null) {
            throw new IllegalArgumentException("topic and value are required");
        }
        try {
            JsonNode node = mapper.readTree(value);
            requireText(node, "schema_version");
            String eventId = requireText(node, "event_id");
            String idempotencyKey = requireText(node, "idempotency_key");
            requireText(node, "policy_id");
            requireText(node, "event_type");
            if (key != null && !key.equals(eventId)) {
                throw new IllegalArgumentException("Kafka key must equal event_id");
            }
            if (!seenIdentities.add(eventId + "\u0000" + idempotencyKey)) {
                return false;
            }
            accepted.incrementAndGet();
            return true;
        } catch (IOException failure) {
            throw new IllegalArgumentException("streaming envelope is not valid JSON", failure);
        }
    }

    public long acceptedCount() {
        return accepted.get();
    }

    private static String requireText(JsonNode node, String field) {
        JsonNode value = node == null ? null : node.get(field);
        if (value == null || !value.isTextual() || value.asText().isBlank()) {
            throw new IllegalArgumentException("streaming envelope requires text field: " + field);
        }
        return value.asText();
    }
}
