package com.inforsight.controlplane.casework;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.audit.AuditAppender;
import com.inforsight.controlplane.audit.AuditEvent;
import com.inforsight.controlplane.audit.AuditHash;
import com.inforsight.controlplane.domain.InferenceScore;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** PostgreSQL case adapter. Decision state, idempotency, and audit append share one transaction. */
public final class PersistentCaseRepository implements CaseWorkflow {
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;
    private final TransactionTemplate transactions;
    private final AuditAppender audit;

    public PersistentCaseRepository(JdbcTemplate jdbc, ObjectMapper mapper, TransactionTemplate transactions, AuditAppender audit) {
        this.jdbc = jdbc;
        this.mapper = mapper;
        this.transactions = transactions;
        this.audit = audit;
    }

    public CaseStore.CaseRecord create(CaseStore.CaseRecord record) {
        String snapshotId = snapshotId(record);
        jdbc.update("""
                INSERT INTO policy_snapshot (snapshot_id, policy_id, as_of_utc, evidence_digest, payload_json)
                VALUES (?, ?, ?, ?, CAST(? AS jsonb))
                ON CONFLICT (snapshot_id) DO NOTHING
                """, snapshotId, record.policyId(), Timestamp.from(record.asOf()), snapshotEvidenceDigest(record), encodeSnapshot(record));
        jdbc.update("""
                INSERT INTO control_case (case_id, policy_id, snapshot_id, state, case_version, recommendation_json, created_at_utc, updated_at_utc)
                VALUES (?, ?, ?, ?, ?, CAST(? AS jsonb), ?, ?)
                """, record.caseId(), record.policyId(), snapshotId, record.state(), record.version(), encode(record),
                Timestamp.from(record.asOf()), Timestamp.from(record.asOf()));
        return record;
    }

    @Override
    public CaseStore.CaseRecord create(String policyId, Instant asOf, InferenceScore score, String action) {
        return create(new CaseStore.CaseRecord("case_" + UUID.randomUUID(), policyId, asOf, score, action,
                "RECOMMENDED", 0, false));
    }

    public Optional<CaseStore.CaseRecord> find(String caseId) {
        List<CaseStore.CaseRecord> records = jdbc.query("""
                SELECT recommendation_json::text FROM control_case WHERE case_id = ?
                """, (row, index) -> decode(row.getString(1)), caseId);
        return records.stream().findFirst();
    }

    public CaseStore.CaseRecord decide(String caseId, String decision, long expectedVersion, String idempotencyKey, String actorId) {
        if (idempotencyKey == null || idempotencyKey.isBlank()) throw new IllegalArgumentException("idempotency_key is required");
        if (actorId == null || actorId.isBlank()) throw new IllegalArgumentException("reviewer_id is required");
        String requestDigest = requestDigest(caseId, decision, expectedVersion, actorId);
        return transactions.execute(status -> {
            Optional<IdempotentDecision> replay = idempotent(caseId, idempotencyKey);
            if (replay.isPresent()) {
                if (!requestDigest.equals(replay.get().requestDigest())) {
                    throw new IllegalStateException("idempotency key request mismatch");
                }
                return replay.get().record();
            }
            CaseStore.CaseRecord current = lockedCase(caseId);
            if (current.version() != expectedVersion) throw new IllegalStateException("case version conflict");
            boolean authorized = "APPROVED".equals(decision) || "OVERRIDDEN".equals(decision);
            CaseStore.CaseRecord updated = new CaseStore.CaseRecord(current.caseId(), current.policyId(), current.asOf(), current.score(),
                    current.recommendedAction(), "APPROVED".equals(decision) ? "HUMAN_REVIEWED" : "DISMISSED", current.version() + 1, authorized);
            int changed = jdbc.update("""
                    UPDATE control_case SET state = ?, case_version = ?, recommendation_json = CAST(? AS jsonb), updated_at_utc = ?
                    WHERE case_id = ? AND case_version = ?
                    """, updated.state(), updated.version(), encode(updated), Timestamp.from(Instant.now()), caseId, current.version());
            if (changed != 1) throw new IllegalStateException("case version conflict");
            audit.append(new AuditEvent(UUID.randomUUID(), caseId, updated.version(), "HUMAN_DECISION_RECORDED", actorId,
                    Instant.now(), Map.of("decision", decision, "idempotency_key", idempotencyKey, "authorized_to_act", authorized)));
            jdbc.update("""
                    INSERT INTO decision_idempotency (case_id, idempotency_key, request_digest, response_json, committed_case_version)
                    VALUES (?, ?, ?, CAST(? AS jsonb), ?)
                    """, caseId, idempotencyKey, requestDigest, encode(updated), updated.version());
            return updated;
        });
    }

    @Override
    public Optional<String> auditHash(String caseId, long caseVersion) {
        List<String> hashes = jdbc.query("SELECT current_hash FROM audit_ledger WHERE case_id = ? AND case_version = ? "
                        + "AND event_type = 'HUMAN_DECISION_RECORDED'", (row, index) -> row.getString(1), caseId, caseVersion);
        return hashes.stream().findFirst();
    }

    private Optional<IdempotentDecision> idempotent(String caseId, String idempotencyKey) {
        List<IdempotentDecision> records = jdbc.query("SELECT request_digest, response_json::text FROM decision_idempotency WHERE case_id = ? AND idempotency_key = ?",
                (row, index) -> new IdempotentDecision(row.getString(1), decode(row.getString(2))), caseId, idempotencyKey);
        return records.stream().findFirst();
    }

    private static String requestDigest(String caseId, String decision, long expectedVersion, String actorId) {
        return AuditHash.sha256(caseId + "\n" + expectedVersion + "\n" + decision + "\n" + actorId);
    }

    private CaseStore.CaseRecord lockedCase(String caseId) {
        List<CaseStore.CaseRecord> records = jdbc.query("SELECT recommendation_json::text FROM control_case WHERE case_id = ? FOR UPDATE",
                (row, index) -> decode(row.getString(1)), caseId);
        if (records.isEmpty()) throw new IllegalArgumentException("case not found");
        return records.getFirst();
    }

    private String encode(CaseStore.CaseRecord record) {
        try {
            return mapper.writeValueAsString(Map.ofEntries(Map.entry("case_id", record.caseId()), Map.entry("policy_id", record.policyId()),
                    Map.entry("as_of", record.asOf().toString()), Map.entry("calibrated_probability", record.score().calibratedProbability()),
                    Map.entry("operational_tier", record.score().operationalTier()), Map.entry("bundle_version", record.score().bundleVersion()),
                    Map.entry("bundle_digest", record.score().bundleDigest()), Map.entry("recommended_action", record.recommendedAction()),
                    Map.entry("state", record.state()), Map.entry("version", record.version()), Map.entry("authorized_to_act", record.authorizedToAct())));
        } catch (Exception failure) { throw new IllegalStateException("could not encode case record", failure); }
    }

    private String encodeSnapshot(CaseStore.CaseRecord record) {
        try {
            return mapper.writeValueAsString(Map.ofEntries(Map.entry("policy_id", record.policyId()),
                    Map.entry("as_of_utc", record.asOf().toString()), Map.entry("bundle_version", record.score().bundleVersion()),
                    Map.entry("bundle_digest", record.score().bundleDigest()),
                    Map.entry("calibrated_probability", record.score().calibratedProbability()),
                    Map.entry("operational_tier", record.score().operationalTier())));
        } catch (Exception failure) { throw new IllegalStateException("could not encode policy snapshot", failure); }
    }

    private static String snapshotEvidenceDigest(CaseStore.CaseRecord record) {
        return AuditHash.sha256(record.policyId() + "\n" + record.asOf() + "\n" + record.score().bundleVersion() + "\n"
                + record.score().bundleDigest() + "\n" + record.score().calibratedProbability() + "\n" + record.score().operationalTier());
    }

    private static String snapshotId(CaseStore.CaseRecord record) {
        return "snapshot_" + snapshotEvidenceDigest(record);
    }

    private CaseStore.CaseRecord decode(String encoded) {
        try {
            JsonNode node = mapper.readTree(encoded);
            return new CaseStore.CaseRecord(node.get("case_id").asText(), node.get("policy_id").asText(), Instant.parse(node.get("as_of").asText()),
                    new InferenceScore(node.get("policy_id").asText(), node.get("calibrated_probability").asDouble(), node.get("operational_tier").asText(),
                            node.get("bundle_version").asText(), node.get("bundle_digest").asText(), false),
                    node.get("recommended_action").asText(), node.get("state").asText(), node.get("version").asLong(), node.get("authorized_to_act").asBoolean());
        } catch (Exception failure) { throw new IllegalStateException("could not decode persisted case record", failure); }
    }

    private record IdempotentDecision(String requestDigest, CaseStore.CaseRecord record) {}
}
