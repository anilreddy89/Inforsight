package com.inforsight.controlplane.connectors;

import com.inforsight.controlplane.audit.AuditAppender;
import com.inforsight.controlplane.audit.AuditEvent;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Fail-closed connector handoff preparation; it has no external transport path. */
public final class ConnectorPreflightService {
    private final Map<ConnectorTarget, ConnectorAdapter> adapters;
    private final AuditAppender audit;
    private final Map<String, ConnectorPreflightOutcome> idempotent = new ConcurrentHashMap<>();
    public ConnectorPreflightService(Map<ConnectorTarget, ConnectorAdapter> adapters, AuditAppender audit) { this.adapters = Map.copyOf(adapters); this.audit = audit; }
    public ConnectorPreflightOutcome preflight(ConnectorPreflightRequest request) {
        String key = request.caseId() + "\u0000" + request.idempotencyKey();
        ConnectorPreflightOutcome replay = idempotent.get(key);
        if (replay != null) return replay;
        String denial = denial(request);
        if (denial != null) return new ConnectorPreflightOutcome("PREFLIGHT_DENIED", denial, null, false, true);
        ConnectorAdapter adapter = adapters.get(request.target());
        if (adapter == null) return new ConnectorPreflightOutcome("PREFLIGHT_DENIED", "UNSUPPORTED_TARGET", null, false, true);
        ConnectorPreflightOutcome outcome = adapter.prepare(request);
        audit.append(new AuditEvent(UUID.randomUUID(), request.caseId(), request.caseVersion(), "CONNECTOR_PREFLIGHT_RECORDED",
                "connector-preflight", Instant.now(), Map.of("target", request.target().name(), "status", outcome.status(), "idempotency_key", request.idempotencyKey(), "authorized_to_act", false)));
        idempotent.put(key, outcome);
        return outcome;
    }
    private static String denial(ConnectorPreflightRequest r) {
        if (!r.humanReviewed()) return "HUMAN_REVIEW_REQUIRED";
        if (!r.consentPresent()) return "CONSENT_REQUIRED";
        if (r.legalHold()) return "LEGAL_HOLD";
        if (r.quietHours()) return "QUIET_HOURS";
        if (r.cooldownActive()) return "COOLDOWN_ACTIVE";
        return null;
    }
}
