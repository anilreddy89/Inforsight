package com.inforsight.controlplane.audit;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
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
            new JdbcTemplate(new DriverManagerDataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword()))
                    .update("UPDATE audit_ledger SET canonical_payload = '{\"decision\":\"TAMPERED\"}' WHERE ledger_sequence = 2");
            assertThat(new AuditLedgerVerifier().verify(ledger.entries()).failureCode()).isEqualTo("CURRENT_HASH_MISMATCH");
        }
    }

    private static AuditEvent event(String id, long version, String decision) {
        return new AuditEvent(UUID.fromString(id), "case-persistence-1", version, "HUMAN_DECISION_RECORDED",
                "reviewer-1", Instant.parse("2026-09-19T00:00:00Z"), Map.of("decision", decision));
    }
}
