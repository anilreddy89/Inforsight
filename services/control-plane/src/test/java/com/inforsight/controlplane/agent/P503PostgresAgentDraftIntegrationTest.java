package com.inforsight.controlplane.agent;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.audit.AuditLedgerRepository;
import com.inforsight.controlplane.audit.AuditLedgerVerifier;
import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.casework.PersistentCaseRepository;
import com.inforsight.controlplane.domain.InferenceScore;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.containers.PostgreSQLContainer;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@EnabledIfEnvironmentVariable(named = "INFORSIGHT_RUN_P5_03_INTEGRATION", matches = "1")
class P503PostgresAgentDraftIntegrationTest {
    @Test
    void draftAuditIsAtomicCaseBoundAndSeparateFromHumanDecision() {
        try (PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")) {
            postgres.start();
            Flyway.configure().dataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())
                    .locations("classpath:db/migration").load().migrate();
            var dataSource = new DriverManagerDataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
            var jdbc = new JdbcTemplate(dataSource);
            var tx = new TransactionTemplate(new DataSourceTransactionManager(dataSource));
            var ledger = new AuditLedgerRepository(jdbc);
            var cases = new PersistentCaseRepository(jdbc, new ObjectMapper(), tx, ledger);
            var initial = new CaseStore.CaseRecord("case-p5-03", "fictional-policy", Instant.parse("2026-09-25T00:00:00Z"),
                    new InferenceScore("fictional-policy", 0.7, "TIER_3_HIGH", "bundle", "digest", false),
                    "abstain", "RECOMMENDED", 0, false);
            cases.create(initial);
            var drafts = new PersistentAgentDraftStore(jdbc, new ObjectMapper(), tx, ledger);
            var draft = new AgentDraftSubmission("1.0.0", initial.caseId(), 0, "DRAFT_FOR_REVIEW", "courtesy_reminder",
                    List.of(), List.of("fictional-event-1"), List.of("procedure@2.0"), false, true, "agent-idem-1");
            var first = drafts.submit(initial.caseId(), draft);
            assertThat(first.snapshotId()).isEqualTo(jdbc.queryForObject(
                    "SELECT snapshot_id FROM control_case WHERE case_id = ?", String.class, initial.caseId()));
            assertThat(first.auditRecordHash()).matches("[0-9a-f]{64}");
            assertThat(drafts.submit(initial.caseId(), draft)).isEqualTo(first);
            assertThat(drafts.find(initial.caseId())).contains(first);
            assertThat(cases.find(initial.caseId())).contains(initial);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(1);
            assertThat(new AuditLedgerVerifier().verify(ledger.entries()).valid()).isTrue();
            assertThatThrownBy(() -> drafts.submit(initial.caseId(), new AgentDraftSubmission("1.0.0", initial.caseId(), 0,
                    "ABSTAIN", null, List.of("LOW_CONFIDENCE"), List.of(), List.of(), false, true, "agent-idem-1")))
                    .isInstanceOf(IllegalStateException.class);
            var human = cases.decide(initial.caseId(), "REJECTED", 0, "human-idem-1", "reviewer-1");
            assertThat(human.authorizedToAct()).isFalse();
            assertThat(human.version()).isEqualTo(1);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(2);
            assertThat(new AuditLedgerVerifier().verify(ledger.entries()).valid()).isTrue();

            var failing = new PersistentAgentDraftStore(jdbc, new ObjectMapper(), tx,
                    event -> { throw new IllegalStateException("audit unavailable"); });
            var second = new CaseStore.CaseRecord("case-p5-03-rollback", "fictional-policy-2",
                    Instant.parse("2026-09-25T00:00:00Z"), initial.score(), "abstain", "RECOMMENDED", 0, false);
            cases.create(second);
            var secondDraft = new AgentDraftSubmission("1.0.0", second.caseId(), 0, "ABSTAIN", null,
                    List.of("LOW_CONFIDENCE"), List.of(), List.of(), false, true, "agent-idem-2");
            assertThatThrownBy(() -> failing.submit(second.caseId(), secondDraft))
                    .isInstanceOf(IllegalStateException.class).hasMessage("audit unavailable");
            assertThat(drafts.find(second.caseId())).isEmpty();
            assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_ledger", Integer.class)).isEqualTo(2);
        }
    }
}
