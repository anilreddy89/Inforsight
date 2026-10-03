package com.inforsight.controlplane.agent;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.audit.AuditAppender;
import com.inforsight.controlplane.audit.AuditEvent;
import com.inforsight.controlplane.audit.AuditHash;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/** One untrusted draft per case; draft and audit append share a transaction. */
public final class PersistentAgentDraftStore implements AgentDraftStore {
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;
    private final TransactionTemplate transactions;
    private final AuditAppender audit;

    public PersistentAgentDraftStore(JdbcTemplate jdbc, ObjectMapper mapper,
                                     TransactionTemplate transactions, AuditAppender audit) {
        this.jdbc = jdbc;
        this.mapper = mapper;
        this.transactions = transactions;
        this.audit = audit;
    }

    public AgentDraftRecord submit(String caseId, AgentDraftSubmission draft) {
        draft.validate(caseId);
        String encoded = encode(draft);
        String digest = AuditHash.sha256(encoded);
        return transactions.execute(status -> {
            List<CaseBinding> cases = jdbc.query("SELECT case_version, state, snapshot_id, recommendation_json->>'authorized_to_act' AS authorized "
                    + "FROM control_case WHERE case_id = ? FOR UPDATE",
                    (row, index) -> new CaseBinding(row.getLong("case_version"), row.getString("state"),
                            row.getString("snapshot_id"), Boolean.parseBoolean(row.getString("authorized"))), caseId);
            if (cases.isEmpty()) throw new IllegalArgumentException("case not found");
            CaseBinding current = cases.getFirst();
            Optional<StoredDraft> previous = stored(caseId);
            if (previous.isPresent()) {
                StoredDraft prior = previous.get();
                if (prior.requestDigest().equals(digest) && prior.draft().idempotencyKey().equals(draft.idempotencyKey())) {
                    return prior.record();
                }
                throw new IllegalStateException("agent draft already exists for case");
            }
            if (current.version() != draft.expectedCaseVersion() || !"RECOMMENDED".equals(current.state())
                    || current.authorized()) throw new IllegalStateException("case version or state conflict");
            UUID eventId = UUID.randomUUID();
            jdbc.update("INSERT INTO agent_review_draft (case_id, case_version, snapshot_id, idempotency_key, "
                    + "request_digest, draft_json, audit_event_id) VALUES (?, ?, ?, ?, ?, CAST(? AS jsonb), ?)",
                    caseId, current.version(), current.snapshotId(), draft.idempotencyKey(), digest, encoded, eventId);
            var entry = audit.append(new AuditEvent(eventId, caseId, current.version(), "AGENT_DRAFT_RECORDED",
                    "agent-advisory", Instant.now(), Map.of("request_digest", digest, "snapshot_id", current.snapshotId(),
                            "authorized_to_act", false)));
            return new AgentDraftRecord(caseId, current.version(), current.snapshotId(), draft, entry.currentHash(), false);
        });
    }

    public Optional<AgentDraftRecord> find(String caseId) {
        return stored(caseId).map(StoredDraft::record);
    }

    private Optional<StoredDraft> stored(String caseId) {
        List<StoredDraft> records = jdbc.query("SELECT d.case_id, d.case_version, d.snapshot_id, d.request_digest, "
                + "d.draft_json::text, a.current_hash FROM agent_review_draft d JOIN audit_ledger a "
                + "ON a.event_id = d.audit_event_id WHERE d.case_id = ?",
                (row, index) -> {
                    AgentDraftSubmission draft = decode(row.getString(5));
                    return new StoredDraft(row.getString(4), draft,
                            new AgentDraftRecord(row.getString(1), row.getLong(2), row.getString(3),
                                    draft, row.getString(6), false));
                }, caseId);
        return records.stream().findFirst();
    }

    private String encode(AgentDraftSubmission draft) {
        try { return mapper.writeValueAsString(draft); }
        catch (Exception failure) { throw new IllegalStateException("could not encode agent draft", failure); }
    }

    private AgentDraftSubmission decode(String value) {
        try { return mapper.readValue(value, AgentDraftSubmission.class); }
        catch (Exception failure) { throw new IllegalStateException("could not decode agent draft", failure); }
    }

    private record CaseBinding(long version, String state, String snapshotId, boolean authorized) {}
    private record StoredDraft(String requestDigest, AgentDraftSubmission draft, AgentDraftRecord record) {}
}
