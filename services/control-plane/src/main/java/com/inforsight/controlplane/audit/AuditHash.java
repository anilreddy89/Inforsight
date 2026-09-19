package com.inforsight.controlplane.audit;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Map;

/** Canonical SHA-256 chain calculation. Any serialized-field drift changes the hash. */
public final class AuditHash {
    public static final String ALGORITHM = "SHA-256";
    public static final String GENESIS_HASH = "0".repeat(64);
    private static final ObjectMapper CANONICAL_MAPPER = new ObjectMapper()
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    private AuditHash() {}

    public static String canonicalPayload(AuditEvent event) {
        try {
            return CANONICAL_MAPPER.writeValueAsString(Map.of(
                    "actor_id", event.actorId(),
                    "case_id", event.caseId(),
                    "case_version", event.caseVersion(),
                    "event_id", event.eventId().toString(),
                    "event_type", event.eventType(),
                    "occurred_at_utc", event.occurredAt().toString(),
                    "payload", event.payload()));
        } catch (JsonProcessingException failure) {
            throw new IllegalArgumentException("audit payload cannot be canonicalized", failure);
        }
    }

    public static String chainHash(String parentHash, String canonicalPayload) {
        if (parentHash == null || !parentHash.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("parent hash must be lowercase SHA-256 hex");
        }
        return sha256(parentHash + "\n" + canonicalPayload);
    }

    public static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance(ALGORITHM).digest(value.getBytes(StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException failure) {
            throw new IllegalStateException("SHA-256 is unavailable", failure);
        }
    }
}
