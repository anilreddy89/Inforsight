package com.inforsight.controlplane.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.casework.PersistentCaseRepository;
import com.inforsight.controlplane.domain.InferenceScore;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.containers.PostgreSQLContainer;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

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
            new JdbcTemplate(new DriverManagerDataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()))
                    .update("UPDATE audit_ledger SET canonical_payload = '{\"decision\":\"TAMPERED\"}' WHERE ledger_sequence = 2");
            assertThat(new AuditLedgerVerifier().verify(ledger.entries()).failureCode()).isEqualTo("CURRENT_HASH_MISMATCH");
            new JdbcTemplate(new DriverManagerDataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()))
                    .update("DELETE FROM audit_ledger WHERE ledger_sequence = 2");
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
            var committed = repository.decide(initial.caseId(), "APPROVED", 0, "idem-1", "reviewer-1");
            assertThat(committed.state()).isEqualTo("HUMAN_REVIEWED");
            assertThat(committed.version()).isEqualTo(1);
            assertThat(repository.decide(initial.caseId(), "APPROVED", 0, "idem-1", "reviewer-1")).isEqualTo(committed);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM decision_idempotency", Integer.class)).isEqualTo(1);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(1);
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> repository.decide(initial.caseId(), "DISMISSED", 0, "idem-stale", "reviewer-1"))
                    .isInstanceOf(IllegalStateException.class).hasMessage("case version conflict");
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(1);

            var rejectedRepository = new PersistentCaseRepository(jdbc, new ObjectMapper(),
                    new TransactionTemplate(new DataSourceTransactionManager(dataSource)), event -> { throw new IllegalStateException("audit unavailable"); });
            var rejected = record("case-transaction-rollback");
            rejectedRepository.create(rejected);
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> rejectedRepository.decide(rejected.caseId(), "APPROVED", 0, "idem-rollback", "reviewer-1"))
                    .isInstanceOf(IllegalStateException.class).hasMessage("audit unavailable");
            assertThat(rejectedRepository.find(rejected.caseId())).contains(rejected);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(1);
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
