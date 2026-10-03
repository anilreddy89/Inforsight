package com.inforsight.controlplane.agent;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import java.util.Optional;

public final class PersistentTrustedAgentHandoffStore implements TrustedAgentHandoffStore {
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;
    public PersistentTrustedAgentHandoffStore(JdbcTemplate jdbc, ObjectMapper mapper) {
        this.jdbc = jdbc; this.mapper = mapper;
    }
    public void save(TrustedAgentHandoff handoff) {
        try {
            int count = jdbc.update("INSERT INTO trusted_agent_handoff (case_id, case_version, snapshot_id, event_id, handoff_json) "
                    + "SELECT case_id, case_version, snapshot_id, ?, CAST(? AS jsonb) FROM control_case "
                    + "WHERE case_id = ? AND case_version = ? AND snapshot_id = ? AND state = 'RECOMMENDED'",
                    handoff.eventId(), mapper.writeValueAsString(handoff), handoff.caseId(), handoff.caseVersion(), handoff.snapshotId());
            if (count != 1) throw new IllegalStateException("case/snapshot handoff binding failed");
        } catch (com.fasterxml.jackson.core.JsonProcessingException failure) {
            throw new IllegalStateException("handoff serialization failed", failure);
        }
    }
    public Optional<TrustedAgentHandoff> find(String caseId) {
        return jdbc.query("SELECT handoff_json::text FROM trusted_agent_handoff WHERE case_id = ?", (row, index) -> {
            try { return mapper.readValue(row.getString(1), TrustedAgentHandoff.class); }
            catch (com.fasterxml.jackson.core.JsonProcessingException failure) {
                throw new IllegalStateException("handoff decode failed", failure);
            }
        }, caseId).stream().findFirst();
    }
}
