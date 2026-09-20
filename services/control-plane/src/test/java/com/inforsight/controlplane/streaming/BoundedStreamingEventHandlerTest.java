package com.inforsight.controlplane.streaming;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BoundedStreamingEventHandlerTest {
    private final BoundedStreamingEventHandler handler = new BoundedStreamingEventHandler(new ObjectMapper());

    @Test
    void acceptsEnvelopeAndRejectsReplay() {
        String event = "{\"schema_version\":\"1.0.0\",\"event_id\":\"evt_000000000001\",\"idempotency_key\":\"idem-1\",\"policy_id\":\"policy-1\",\"event_type\":\"policy.issued\"}";
        assertThat(handler.handle("policy.lifecycle.v1", "evt_000000000001", event)).isTrue();
        assertThat(handler.handle("policy.lifecycle.v1", "evt_000000000001", event)).isFalse();
        assertThat(handler.acceptedCount()).isOne();
    }

    @Test
    void rejectsKeyMismatchAndMissingEnvelopeFields() {
        String event = "{\"schema_version\":\"1.0.0\",\"event_id\":\"evt_000000000001\",\"idempotency_key\":\"idem-1\",\"policy_id\":\"policy-1\",\"event_type\":\"policy.issued\"}";
        assertThatThrownBy(() -> handler.handle("policy.lifecycle.v1", "wrong", event))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Kafka key");
        assertThatThrownBy(() -> handler.handle("policy.lifecycle.v1", "evt_000000000001", "{}"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("schema_version");
        assertThatThrownBy(() -> handler.handle("unknown.v1", "evt_000000000001", event))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
