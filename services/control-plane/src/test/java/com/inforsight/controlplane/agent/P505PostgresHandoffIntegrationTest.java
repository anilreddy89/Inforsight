package com.inforsight.controlplane.agent;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.audit.AuditLedgerRepository;
import com.inforsight.controlplane.audit.AuditLedgerVerifier;
import com.inforsight.controlplane.casework.PersistentCaseRepository;
import com.inforsight.controlplane.inference.BoundedInferenceClient;
import com.inforsight.controlplane.rules.EligibilityEngine;
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

@EnabledIfEnvironmentVariable(named = "INFORSIGHT_RUN_P5_05_INTEGRATION", matches = "1")
class P505PostgresHandoffIntegrationTest {
    @Test void eventHandoffBoundsDraftAndHumanOverrideWithAuditReplay() {
        try (PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")) {
            postgres.start();
            Flyway.configure().dataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())
                    .locations("classpath:db/migration").load().migrate();
            var dataSource = new DriverManagerDataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
            var jdbc = new JdbcTemplate(dataSource);
            var mapper = new ObjectMapper().findAndRegisterModules();
            var tx = new TransactionTemplate(new DataSourceTransactionManager(dataSource));
            var ledger = new AuditLedgerRepository(jdbc);
            var handoffs = new PersistentTrustedAgentHandoffStore(jdbc, mapper);
            var cases = new PersistentCaseRepository(jdbc, mapper, tx, ledger, handoffs);
            var service = new FictionalEventReviewService(new BoundedInferenceClient(), new EligibilityEngine(), cases, handoffs);
            var event = new FictionalEventReviewService.FictionalEvent("fictional-event-1", "fictional-policy-1",
                    Instant.parse("2026-09-25T00:00:00Z"), Instant.parse("2026-09-20T00:00:00Z"),
                    "late", "active", 365, false, false, false, false, false, false, false);
            var handoff = service.ingest(event);
            assertThat(handoff.allowedActions()).contains("courtesy_reminder", "abstain");
            assertThat(handoffs.find(handoff.caseId())).contains(handoff);
            assertThat(jdbc.queryForObject("SELECT snapshot_id FROM control_case WHERE case_id = ?", String.class,
                    handoff.caseId())).isEqualTo(handoff.snapshotId());
            var drafts = new PersistentAgentDraftStore(jdbc, mapper, tx, ledger, handoffs);
            var invalid = new AgentDraftSubmission("1.0.0", handoff.caseId(), 0, "DRAFT_FOR_REVIEW", "invented_action",
                    List.of(), List.of(handoff.eventId()), List.of(handoff.procedureCitation()), false, true, "invalid");
            assertThatThrownBy(() -> drafts.submit(handoff.caseId(), invalid)).isInstanceOf(IllegalArgumentException.class);
            var valid = new AgentDraftSubmission("1.0.0", handoff.caseId(), 0, "DRAFT_FOR_REVIEW", "courtesy_reminder",
                    List.of(), List.of(handoff.eventId()), List.of(handoff.procedureCitation()), false, true, "valid");
            var recorded = drafts.submit(handoff.caseId(), valid);
            assertThat(recorded.snapshotId()).isEqualTo(handoff.snapshotId());
            assertThat(cases.find(handoff.caseId()).orElseThrow().version()).isZero();
            assertThatThrownBy(() -> cases.decide(handoff.caseId(), "OVERRIDDEN", 0, "bad-human", "reviewer",
                    "invented_action")).isInstanceOf(IllegalArgumentException.class);
            assertThat(cases.find(handoff.caseId()).orElseThrow().version()).isZero();
            var rejected = cases.decide(handoff.caseId(), "REJECTED", 0, "human-reject", "reviewer", "abstain");
            assertThat(rejected.authorizedToAct()).isFalse();
            assertThat(rejected.version()).isEqualTo(1);
            assertThat(new AuditLedgerVerifier().verify(ledger.entries(), ledger.checkpoint()).valid()).isTrue();
            assertThat(ledger.entries().stream().filter(entry -> handoff.caseId().equals(entry.caseId()))
                    .map(entry -> entry.eventType()).toList())
                    .containsExactly("AGENT_DRAFT_RECORDED", "HUMAN_DECISION_RECORDED");

            var frozenEvent = new FictionalEventReviewService.FictionalEvent("fictional-event-legal-hold",
                    "fictional-policy-legal-hold", event.asOf(), event.observedAt(), "late", "active", 365,
                    false, true, false, false, false, false, false);
            var frozen = service.ingest(frozenEvent);
            assertThat(frozen.allowedActions()).containsExactly("abstain");
            var forged = new AgentDraftSubmission("1.0.0", frozen.caseId(), 0, "DRAFT_FOR_REVIEW", "courtesy_reminder",
                    List.of(), List.of(frozen.eventId()), List.of(frozen.procedureCitation()), false, true, "forged");
            assertThatThrownBy(() -> drafts.submit(frozen.caseId(), forged)).isInstanceOf(IllegalArgumentException.class);
        }
    }
}
