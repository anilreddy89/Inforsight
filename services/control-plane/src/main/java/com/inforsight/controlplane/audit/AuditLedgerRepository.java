package com.inforsight.controlplane.audit;

import org.springframework.jdbc.core.JdbcTemplate;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import java.util.ArrayList;
import java.util.Collection;

/** PostgreSQL append-only ledger adapter. Callers must provide the surrounding transaction. */
public final class AuditLedgerRepository implements AuditAppender {
    private final JdbcTemplate jdbc;

    public AuditLedgerRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public synchronized AuditLedgerEntry append(AuditEvent event) {
        String parent = jdbc.query("SELECT current_hash FROM audit_ledger ORDER BY ledger_sequence DESC LIMIT 1 FOR UPDATE",
                result -> result.next() ? result.getString(1) : AuditHash.GENESIS_HASH);
        String payload = AuditHash.canonicalPayload(event);
        String current = AuditHash.chainHash(parent, payload);
        Long sequence = jdbc.queryForObject("""
                INSERT INTO audit_ledger (event_id, case_id, case_version, event_type, actor_id, occurred_at_utc,
                hash_algorithm, canonical_payload, parent_hash, current_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING ledger_sequence
                """, Long.class, event.eventId(), event.caseId(), event.caseVersion(), event.eventType(), event.actorId(),
                java.sql.Timestamp.from(event.occurredAt()), AuditHash.ALGORITHM, payload, parent, current);
        if (sequence == null) throw new IllegalStateException("audit ledger insert did not return a sequence");
        return new AuditLedgerEntry(sequence, event.eventId(), event.caseId(), event.caseVersion(), event.eventType(),
                event.actorId(), event.occurredAt(), payload, parent, current);
    }

    /** Appends an ordered batch in one INSERT while preserving the hash chain. */
    public synchronized java.util.List<AuditLedgerEntry> appendBatch(Collection<AuditEvent> events) {
        if (events.isEmpty()) return java.util.List.of();
        String parent = jdbc.query("SELECT current_hash FROM audit_ledger ORDER BY ledger_sequence DESC LIMIT 1 FOR UPDATE",
                result -> result.next() ? result.getString(1) : AuditHash.GENESIS_HASH);
        StringBuilder sql = new StringBuilder("INSERT INTO audit_ledger "
                + "(event_id, case_id, case_version, event_type, actor_id, occurred_at_utc, "
                + "hash_algorithm, canonical_payload, parent_hash, current_hash) VALUES ");
        ArrayList<Object> args = new ArrayList<>();
        ArrayList<AuditLedgerEntry> entries = new ArrayList<>();
        for (AuditEvent event : events) {
            String payload = AuditHash.canonicalPayload(event);
            String current = AuditHash.chainHash(parent, payload);
            if (!entries.isEmpty()) sql.append(",");
            sql.append("(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
            args.add(event.eventId()); args.add(event.caseId()); args.add(event.caseVersion());
            args.add(event.eventType()); args.add(event.actorId()); args.add(java.sql.Timestamp.from(event.occurredAt()));
            args.add(AuditHash.ALGORITHM); args.add(payload); args.add(parent); args.add(current);
            entries.add(new AuditLedgerEntry(0, event.eventId(), event.caseId(), event.caseVersion(), event.eventType(),
                    event.actorId(), event.occurredAt(), payload, parent, current));
            parent = current;
        }
        sql.append(" RETURNING ledger_sequence");
        java.util.List<Long> sequences = jdbc.query(sql.toString(), (result, row) -> result.getLong(1), args.toArray());
        if (sequences.size() != entries.size()) throw new IllegalStateException("audit batch sequence count mismatch");
        for (int index = 0; index < entries.size(); index++) {
            AuditLedgerEntry entry = entries.get(index);
            entries.set(index, new AuditLedgerEntry(sequences.get(index), entry.eventId(), entry.caseId(),
                    entry.caseVersion(), entry.eventType(), entry.actorId(), entry.occurredAt(), entry.canonicalPayload(),
                    entry.parentHash(), entry.currentHash()));
        }
        return entries;
    }

    public Optional<AuditLedgerEntry> findByEventId(java.util.UUID eventId) {
        List<AuditLedgerEntry> entries = jdbc.query("""
                SELECT ledger_sequence, event_id, case_id, case_version, event_type, actor_id, occurred_at_utc,
                canonical_payload, parent_hash, current_hash FROM audit_ledger WHERE event_id = ?
                """, (row, index) -> row(row), eventId);
        return entries.stream().findFirst();
    }

    public List<AuditLedgerEntry> entries() {
        return jdbc.query("""
                SELECT ledger_sequence, event_id, case_id, case_version, event_type, actor_id, occurred_at_utc,
                canonical_payload, parent_hash, current_hash FROM audit_ledger ORDER BY ledger_sequence
                """, (row, index) -> row(row));
    }

    public AuditLedgerCheckpoint checkpoint() {
        return jdbc.query("SELECT ledger_sequence, current_hash FROM audit_ledger ORDER BY ledger_sequence DESC LIMIT 1",
                result -> result.next() ? new AuditLedgerCheckpoint(result.getLong(1), result.getString(2))
                        : new AuditLedgerCheckpoint(0, AuditHash.GENESIS_HASH));
    }

    private static AuditLedgerEntry row(ResultSet result) throws SQLException {
        return new AuditLedgerEntry(result.getLong("ledger_sequence"),
                result.getObject("event_id", java.util.UUID.class), result.getString("case_id"),
                result.getLong("case_version"), result.getString("event_type"), result.getString("actor_id"),
                result.getTimestamp("occurred_at_utc").toInstant(), result.getString("canonical_payload"),
                result.getString("parent_hash"), result.getString("current_hash"));
    }
}
