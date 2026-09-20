package com.inforsight.controlplane.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.casework.PersistentCaseRepository;
import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.domain.InferenceScore;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/** Opt-in Compose PostgreSQL evidence for P4-07 E4/E5. */
class P407PostgresQualificationIntegrationTest {
    private JdbcTemplate jdbc;

    @BeforeEach
    void setUp() {
        Assumptions.assumeTrue("1".equals(System.getenv("INFORSIGHT_RUN_P4_07_POSTGRES_INTEGRATION")));
        String url = env("INFORSIGHT_P4_07_POSTGRES_JDBC_URL", "jdbc:postgresql://localhost:5433/inforsight_enterprise");
        String user = env("INFORSIGHT_P4_07_POSTGRES_USERNAME", "inforsight_app");
        String password = env("INFORSIGHT_P4_07_POSTGRES_PASSWORD", "dev_insecure_local_password");
        Flyway.configure().dataSource(url, user, password)
                .locations("classpath:db/migration").load().migrate();
        jdbc = new JdbcTemplate(new DriverManagerDataSource(url, user, password));
    }

    @Test
    void detectsAuditTamperAndRestoresTheExternalLedger() {
        String suffix = UUID.randomUUID().toString();
        AuditLedgerRepository ledger = new AuditLedgerRepository(jdbc);
        AuditEvent event = event("p407-audit-" + suffix, 1, "APPROVED");
        AuditLedgerEntry entry = ledger.append(event);
        AuditLedgerCheckpoint checkpoint = ledger.checkpoint();
        String originalPayload = entry.canonicalPayload();
        try {
            jdbc.execute("ALTER TABLE audit_ledger DISABLE TRIGGER audit_ledger_reject_update_delete");
            jdbc.update("UPDATE audit_ledger SET canonical_payload = ? WHERE ledger_sequence = ?",
                    "{\"decision\":\"TAMPERED\"}", entry.sequence());
            jdbc.execute("ALTER TABLE audit_ledger ENABLE TRIGGER audit_ledger_reject_update_delete");
            assertThat(new AuditLedgerVerifier().verify(ledger.entries(), checkpoint).valid()).isFalse();
        } finally {
            jdbc.execute("ALTER TABLE audit_ledger DISABLE TRIGGER audit_ledger_reject_update_delete");
            jdbc.update("UPDATE audit_ledger SET canonical_payload = ?, current_hash = ? WHERE ledger_sequence = ?",
                    originalPayload, entry.currentHash(), entry.sequence());
            jdbc.execute("ALTER TABLE audit_ledger ENABLE TRIGGER audit_ledger_reject_update_delete");
        }
    }

    @Test
    void rehydratesCommittedCaseAndAuditAfterRepositoryRestart() {
        String suffix = UUID.randomUUID().toString();
        AuditLedgerRepository ledger = new AuditLedgerRepository(jdbc);
        var dataSource = jdbc.getDataSource();
        assertThat(dataSource).isNotNull();
        var transactions = new TransactionTemplate(new DataSourceTransactionManager(dataSource));
        var repository = new PersistentCaseRepository(jdbc, new ObjectMapper(), transactions, ledger);
        CaseStore.CaseRecord initial = new CaseStore.CaseRecord(
                "p407-restart-case-" + suffix,
                "p407-restart-policy-" + suffix,
                Instant.parse("2026-09-19T00:00:00Z"),
                new InferenceScore("p407-restart-policy-" + suffix, 0.7, "TIER_3_HIGH",
                        "bundle-p407", "digest-p407", false),
                "abstain", "RECOMMENDED", 0, false);
        repository.create(initial);
        CaseStore.CaseRecord committed = repository.decide(initial.caseId(), "APPROVED", 0,
                "p407-restart-idem-" + suffix, "reviewer-p407");

        PersistentCaseRepository restarted = new PersistentCaseRepository(jdbc, new ObjectMapper(), transactions, ledger);
        assertThat(restarted.find(initial.caseId())).contains(committed);
        assertThat(restarted.auditHash(initial.caseId(), committed.version())).isPresent();
        assertThat(new AuditLedgerVerifier().verify(ledger.entries()).valid()).isTrue();
    }

    private static AuditEvent event(String caseId, long version, String decision) {
        return new AuditEvent(UUID.randomUUID(), caseId, version, "P407_TAMPER_PROBE",
                "p407-qualification", Instant.parse("2026-09-19T00:00:00Z"), Map.of("decision", decision));
    }

    private static String env(String name, String fallback) {
        String value = System.getenv(name);
        return value == null || value.isBlank() ? fallback : value;
    }
}
