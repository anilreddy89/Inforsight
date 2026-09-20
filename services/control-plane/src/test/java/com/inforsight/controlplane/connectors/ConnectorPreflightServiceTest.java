package com.inforsight.controlplane.connectors;

import com.inforsight.controlplane.audit.AuditAppender;
import com.inforsight.controlplane.audit.AuditLedgerEntry;
import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.casework.CaseWorkflow;
import com.inforsight.controlplane.domain.InferenceScore;
import org.junit.jupiter.api.Test;
import java.time.Instant;
import java.util.Optional;
import java.util.EnumMap;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.assertThat;

class ConnectorPreflightServiceTest {
    @Test void preparesOnlyGovernedFakeHandoffsAndFailsClosed() {
        var calls = new AtomicInteger();
        AuditAppender audit = event -> { calls.incrementAndGet(); return (AuditLedgerEntry) null; };
        var adapters = new EnumMap<ConnectorTarget, ConnectorAdapter>(ConnectorTarget.class);
        for (var target : ConnectorTarget.values()) adapters.put(target, new FakeConnectorAdapter(target));
        CaseStore.CaseRecord reviewed = new CaseStore.CaseRecord("case-1", "policy-1", Instant.parse("2026-09-19T00:00:00Z"),
                new InferenceScore("policy-1", 0.7, "TIER_3_HIGH", "bundle", "digest", false), "abstain", "HUMAN_REVIEWED", 1, true);
        CaseWorkflow cases = new CaseWorkflow() {
            public CaseStore.CaseRecord create(String p, Instant a, InferenceScore s, String action) { throw new UnsupportedOperationException(); }
            public Optional<CaseStore.CaseRecord> find(String id) { return "case-1".equals(id) ? Optional.of(reviewed) : Optional.empty(); }
            public CaseStore.CaseRecord decide(String id, String d, long v, String k, String actor) { throw new UnsupportedOperationException(); }
        };
        var service = new ConnectorPreflightService(adapters, audit, cases);
        var valid = request(true, true, false, false, false, "idem-1", ConnectorTarget.SALESFORCE_FSC);
        var ready = service.preflight(valid);
        assertThat(ready.status()).isEqualTo("PREFLIGHT_READY");
        assertThat(ready.authorizedToAct()).isFalse();
        assertThat(ready.externalExecutionDisabled()).isTrue();
        assertThat(service.preflight(valid)).isEqualTo(ready);
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> service.preflight(request(true, true, false, false, false, "idem-1", ConnectorTarget.GENESYS)))
                .isInstanceOf(IllegalStateException.class).hasMessage("idempotency key request mismatch");
        assertThat(calls).hasValue(1);
        assertThat(service.preflight(request(false, true, false, false, false, "idem-human", ConnectorTarget.SALESFORCE_FSC)).reasonCode()).isEqualTo("HUMAN_REVIEW_REQUIRED");
        assertThat(service.preflight(request(true, false, false, false, false, "idem-consent", ConnectorTarget.SALESFORCE_FSC)).reasonCode()).isEqualTo("CONSENT_REQUIRED");
        assertThat(service.preflight(request(true, true, true, false, false, "idem-hold", ConnectorTarget.SALESFORCE_FSC)).reasonCode()).isEqualTo("LEGAL_HOLD");
        assertThat(service.preflight(request(true, true, false, true, false, "idem-quiet", ConnectorTarget.SALESFORCE_FSC)).reasonCode()).isEqualTo("QUIET_HOURS");
        assertThat(service.preflight(request(true, true, false, false, true, "idem-cooldown", ConnectorTarget.SALESFORCE_FSC)).reasonCode()).isEqualTo("COOLDOWN_ACTIVE");
        assertThat(service.preflight(new ConnectorPreflightRequest("connector-preflight/1.0.0", ConnectorTarget.SALESFORCE_FSC, "case-1", 0, "policy-1", "snapshot-1", "a".repeat(64), "idem-stale", true, true, false, false, false, Instant.parse("2026-09-19T00:00:00Z"))).reasonCode()).isEqualTo("STALE_CASE_VERSION");
        assertThat(calls).hasValue(1);
    }
    private static ConnectorPreflightRequest request(boolean human, boolean consent, boolean hold, boolean quiet, boolean cooldown, String key, ConnectorTarget target) {
        return new ConnectorPreflightRequest("connector-preflight/1.0.0", target, "case-1", 1, "policy-1", "snapshot-1", "a".repeat(64), key, human, consent, hold, quiet, cooldown, Instant.parse("2026-09-19T00:00:00Z"));
    }
}
