package com.inforsight.controlplane.audit;

import java.time.Instant;
import java.util.UUID;

public record AuditLedgerEntry(
        long sequence,
        UUID eventId,
        String caseId,
        long caseVersion,
        String eventType,
        String actorId,
        Instant occurredAt,
        String canonicalPayload,
        String parentHash,
        String currentHash) {}
