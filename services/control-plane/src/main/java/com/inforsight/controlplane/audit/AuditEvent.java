package com.inforsight.controlplane.audit;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/** Immutable, authority-neutral audit input for a committed workflow transition. */
public record AuditEvent(
        UUID eventId,
        String caseId,
        long caseVersion,
        String eventType,
        String actorId,
        Instant occurredAt,
        Map<String, Object> payload) {
    public AuditEvent {
        if (eventId == null || caseId == null || caseId.isBlank() || caseVersion < 0
                || eventType == null || eventType.isBlank() || actorId == null || actorId.isBlank()
                || occurredAt == null || payload == null) {
            throw new IllegalArgumentException("audit event fields are required");
        }
    }
}
