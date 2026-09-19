package com.inforsight.controlplane.audit;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class AuditHashTest {
    @Test
    void canonicalPayloadAndHashAreDeterministicAndDetectMutation() {
        var event = new AuditEvent(UUID.fromString("00000000-0000-0000-0000-000000000001"), "case-1", 1,
                "HUMAN_DECISION_RECORDED", "reviewer-1", Instant.parse("2026-09-19T00:00:00Z"), Map.of("decision", "APPROVED"));
        String payload = AuditHash.canonicalPayload(event);
        String hash = AuditHash.chainHash(AuditHash.GENESIS_HASH, payload);
        assertThat(AuditHash.chainHash(AuditHash.GENESIS_HASH, payload)).isEqualTo(hash);
        var entry = new AuditLedgerEntry(1, event.eventId(), event.caseId(), event.caseVersion(), event.eventType(),
                event.actorId(), event.occurredAt(), payload, AuditHash.GENESIS_HASH, hash);
        assertThat(new AuditLedgerVerifier().verify(List.of(entry)).valid()).isTrue();
        var tampered = new AuditLedgerEntry(1, event.eventId(), event.caseId(), event.caseVersion(), event.eventType(),
                event.actorId(), event.occurredAt(), payload.replace("APPROVED", "DISMISSED"), AuditHash.GENESIS_HASH, hash);
        assertThat(new AuditLedgerVerifier().verify(List.of(tampered)).failureCode()).isEqualTo("CURRENT_HASH_MISMATCH");
    }
}
