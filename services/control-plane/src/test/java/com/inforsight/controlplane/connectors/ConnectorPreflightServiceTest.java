package com.inforsight.controlplane.connectors;

import com.inforsight.controlplane.audit.AuditAppender;
import com.inforsight.controlplane.audit.AuditLedgerEntry;
import org.junit.jupiter.api.Test;
import java.time.Instant;
import java.util.EnumMap;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.assertThat;

class ConnectorPreflightServiceTest {
    @Test void preparesOnlyGovernedFakeHandoffsAndFailsClosed() {
        var calls = new AtomicInteger();
        AuditAppender audit = event -> { calls.incrementAndGet(); return (AuditLedgerEntry) null; };
        var adapters = new EnumMap<ConnectorTarget, ConnectorAdapter>(ConnectorTarget.class);
        for (var target : ConnectorTarget.values()) adapters.put(target, new FakeConnectorAdapter(target));
        var service = new ConnectorPreflightService(adapters, audit);
        var valid = request(true, true, false, false, false, "idem-1");
        var ready = service.preflight(valid);
        assertThat(ready.status()).isEqualTo("PREFLIGHT_READY");
        assertThat(ready.authorizedToAct()).isFalse();
        assertThat(ready.externalExecutionDisabled()).isTrue();
        assertThat(service.preflight(valid)).isEqualTo(ready);
        assertThat(calls).hasValue(1);
        assertThat(service.preflight(request(false, true, false, false, false, "idem-human")).reasonCode()).isEqualTo("HUMAN_REVIEW_REQUIRED");
        assertThat(service.preflight(request(true, false, false, false, false, "idem-consent")).reasonCode()).isEqualTo("CONSENT_REQUIRED");
        assertThat(service.preflight(request(true, true, true, false, false, "idem-hold")).reasonCode()).isEqualTo("LEGAL_HOLD");
        assertThat(service.preflight(request(true, true, false, true, false, "idem-quiet")).reasonCode()).isEqualTo("QUIET_HOURS");
        assertThat(service.preflight(request(true, true, false, false, true, "idem-cooldown")).reasonCode()).isEqualTo("COOLDOWN_ACTIVE");
        assertThat(calls).hasValue(1);
    }
    private static ConnectorPreflightRequest request(boolean human, boolean consent, boolean hold, boolean quiet, boolean cooldown, String key) {
        return new ConnectorPreflightRequest("connector-preflight/1.0.0", ConnectorTarget.SALESFORCE_FSC, "case-1", 1, "policy-1", "snapshot-1", "a".repeat(64), key, human, consent, hold, quiet, cooldown, Instant.parse("2026-09-19T00:00:00Z"));
    }
}
