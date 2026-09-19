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

    @Test
    void checkpointMakesTailDeletionAndCallerReorderingDetectable() {
        var first = entry(1, "00000000-0000-0000-0000-000000000011", AuditHash.GENESIS_HASH);
        var second = entry(2, "00000000-0000-0000-0000-000000000012", first.currentHash());
        var checkpoint = new AuditLedgerCheckpoint(2, second.currentHash());
        var verifier = new AuditLedgerVerifier();
        assertThat(verifier.verify(List.of(first), checkpoint).failureCode()).isEqualTo("CHECKPOINT_SEQUENCE_MISMATCH");
        assertThat(verifier.verify(List.of(second, first)).failureCode()).isEqualTo("SEQUENCE_GAP");
        assertThat(verifier.verify(List.of(first, first)).failureCode()).isEqualTo("SEQUENCE_GAP");
    }

    @Test
    void localSigningSeamIsDeterministicAndRejectsChangedHead() {
        var signer = new LocalHmacAuditLedgerSigner("local-test-key-v1", "clean-room-test-key-material".getBytes());
        var signature = signer.sign(AuditHash.GENESIS_HASH);
        assertThat(signer.sign(AuditHash.GENESIS_HASH)).isEqualTo(signature);
        assertThat(signer.verifies(AuditHash.GENESIS_HASH, signature)).isTrue();
        assertThat(signer.verifies(AuditHash.sha256("changed"), signature)).isFalse();
    }

    private static AuditLedgerEntry entry(long sequence, String eventId, String parentHash) {
        var event = new AuditEvent(UUID.fromString(eventId), "case-" + sequence, sequence,
                "HUMAN_DECISION_RECORDED", "reviewer-1", Instant.parse("2026-09-19T00:00:00Z"), Map.of("decision", "APPROVED"));
        String payload = AuditHash.canonicalPayload(event);
        return new AuditLedgerEntry(sequence, event.eventId(), event.caseId(), event.caseVersion(), event.eventType(),
                event.actorId(), event.occurredAt(), payload, parentHash, AuditHash.chainHash(parentHash, payload));
    }
}
