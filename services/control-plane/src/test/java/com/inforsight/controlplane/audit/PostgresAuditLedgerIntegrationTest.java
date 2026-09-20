package com.inforsight.controlplane.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.casework.PersistentCaseRepository;
import com.inforsight.controlplane.domain.InferenceScore;
import com.inforsight.controlplane.connectors.ConnectorAdapter;
import com.inforsight.controlplane.connectors.ConnectorPreflightRequest;
import com.inforsight.controlplane.connectors.ConnectorPreflightService;
import com.inforsight.controlplane.connectors.ConnectorTarget;
import com.inforsight.controlplane.connectors.FakeConnectorAdapter;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.containers.PostgreSQLContainer;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.EnumMap;

import static org.assertj.core.api.Assertions.assertThat;

/** Docker-backed persistence proof; opt in with INFORSIGHT_RUN_P4_04_INTEGRATION=1. */
@EnabledIfEnvironmentVariable(named = "INFORSIGHT_RUN_P4_04_INTEGRATION", matches = "1")
class PostgresAuditLedgerIntegrationTest {
    @Test
    void migrationsCreateAppendOnlyVerifiableLedger() {
        try (PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")) {
            postgres.start();
            Flyway.configure().dataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())
                    .locations("classpath:db/migration").load().migrate();
            var ledger = new AuditLedgerRepository(new JdbcTemplate(new DriverManagerDataSource(
                    postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())));
            var first = ledger.append(event("00000000-0000-0000-0000-000000000011", 1, "APPROVED"));
            var second = ledger.append(event("00000000-0000-0000-0000-000000000012", 2, "DISMISSED"));
            assertThat(second.parentHash()).isEqualTo(first.currentHash());
            assertThat(new AuditLedgerVerifier().verify(ledger.entries()).valid()).isTrue();
            var checkpoint = ledger.checkpoint();
            var adversary = new JdbcTemplate(new DriverManagerDataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()));
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> adversary
                    .update("UPDATE audit_ledger SET canonical_payload = '{\"decision\":\"TAMPERED\"}' WHERE ledger_sequence = 2"))
                    .isInstanceOf(DataAccessException.class).hasMessageContaining("append-only");
            adversary.execute("ALTER TABLE audit_ledger DISABLE TRIGGER audit_ledger_reject_update_delete");
            adversary.update("UPDATE audit_ledger SET canonical_payload = '{\"decision\":\"TAMPERED\"}' WHERE ledger_sequence = 2");
            adversary.execute("ALTER TABLE audit_ledger ENABLE TRIGGER audit_ledger_reject_update_delete");
            assertThat(new AuditLedgerVerifier().verify(ledger.entries()).failureCode()).isEqualTo("CURRENT_HASH_MISMATCH");
            adversary.execute("ALTER TABLE audit_ledger DISABLE TRIGGER audit_ledger_reject_update_delete");
            adversary.update("DELETE FROM audit_ledger WHERE ledger_sequence = 2");
            adversary.execute("ALTER TABLE audit_ledger ENABLE TRIGGER audit_ledger_reject_update_delete");
            assertThat(new AuditLedgerVerifier().verify(ledger.entries(), checkpoint).failureCode()).isEqualTo("CHECKPOINT_SEQUENCE_MISMATCH");
        }
    }

    @Test
    void decisionAndAuditAppendAreAtomicAndIdempotent() {
        try (PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")) {
            postgres.start();
            Flyway.configure().dataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())
                    .locations("classpath:db/migration").load().migrate();
            var dataSource = new DriverManagerDataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
            var jdbc = new JdbcTemplate(dataSource);
            var ledger = new AuditLedgerRepository(jdbc);
            var repository = new PersistentCaseRepository(jdbc, new ObjectMapper(),
                    new TransactionTemplate(new DataSourceTransactionManager(dataSource)), ledger);
            var initial = record("case-transaction-1");
            repository.create(initial);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM policy_snapshot WHERE policy_id = ?", Integer.class, initial.policyId())).isEqualTo(1);
            assertThat(jdbc.queryForObject("SELECT snapshot_id IS NOT NULL FROM control_case WHERE case_id = ?", Boolean.class, initial.caseId())).isTrue();
            assertThat(jdbc.queryForObject("SELECT queue_state FROM triage_queue WHERE case_id = ?", String.class, initial.caseId())).isEqualTo("PENDING_REVIEW");
            var committed = repository.decide(initial.caseId(), "APPROVED", 0, "idem-1", "reviewer-1");
            assertThat(committed.state()).isEqualTo("HUMAN_REVIEWED");
            assertThat(committed.version()).isEqualTo(1);
            var rehydratedRepository = new PersistentCaseRepository(jdbc, new ObjectMapper(),
                    new TransactionTemplate(new DataSourceTransactionManager(dataSource)), ledger);
            assertThat(rehydratedRepository.find(initial.caseId())).contains(committed);
            assertThat(rehydratedRepository.auditHash(initial.caseId(), committed.version()))
                    .hasValueSatisfying(hash -> assertThat(hash).matches("[0-9a-f]{64}"));
            var adapters = new EnumMap<ConnectorTarget, ConnectorAdapter>(ConnectorTarget.class);
            for (var target : ConnectorTarget.values()) adapters.put(target, new FakeConnectorAdapter(target));
            var connector = new ConnectorPreflightService(adapters, ledger, rehydratedRepository);
            String snapshotId = jdbc.queryForObject("SELECT snapshot_id FROM control_case WHERE case_id = ?", String.class, initial.caseId());
            var preflight = connector.preflight(new ConnectorPreflightRequest("connector-preflight/1.0.0", ConnectorTarget.SALESFORCE_FSC,
                    initial.caseId(), committed.version(), initial.policyId(), snapshotId,
                    rehydratedRepository.auditHash(initial.caseId(), committed.version()).orElseThrow(), "connector-idem-1",
                    true, true, false, false, false, Instant.parse("2026-09-19T00:00:00Z")));
            assertThat(preflight.status()).isEqualTo("PREFLIGHT_READY");
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(2);
            assertThat(repository.decide(initial.caseId(), "APPROVED", 0, "idem-1", "reviewer-1")).isEqualTo(committed);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM decision_idempotency", Integer.class)).isEqualTo(1);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(2);
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> repository.decide(initial.caseId(), "DISMISSED", 0, "idem-1", "reviewer-1"))
                    .isInstanceOf(IllegalStateException.class).hasMessage("idempotency key request mismatch");
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(2);
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> repository.decide(initial.caseId(), "DISMISSED", 0, "idem-stale", "reviewer-1"))
                    .isInstanceOf(IllegalStateException.class).hasMessage("case version conflict");
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(2);

            var rejectedRepository = new PersistentCaseRepository(jdbc, new ObjectMapper(),
                    new TransactionTemplate(new DataSourceTransactionManager(dataSource)), event -> { throw new IllegalStateException("audit unavailable"); });
            var rejected = record("case-transaction-rollback");
            rejectedRepository.create(rejected);
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> rejectedRepository.decide(rejected.caseId(), "APPROVED", 0, "idem-rollback", "reviewer-1"))
                    .isInstanceOf(IllegalStateException.class).hasMessage("audit unavailable");
            assertThat(rejectedRepository.find(rejected.caseId())).contains(rejected);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(2);
        }
    }

    private static AuditEvent event(String id, long version, String decision) {
        return new AuditEvent(UUID.fromString(id), "case-persistence-1", version, "HUMAN_DECISION_RECORDED",
                "reviewer-1", Instant.parse("2026-09-19T00:00:00Z"), Map.of("decision", decision));
    }

    private static CaseStore.CaseRecord record(String caseId) {
        return new CaseStore.CaseRecord(caseId, "policy-transaction-1", Instant.parse("2026-09-19T00:00:00Z"),
                new InferenceScore("policy-transaction-1", 0.7, "TIER_3_HIGH", "bundle-1", "digest-1", false),
                "abstain", "RECOMMENDED", 0, false);
    }
}
