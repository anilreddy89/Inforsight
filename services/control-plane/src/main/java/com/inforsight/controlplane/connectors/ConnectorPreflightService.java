package com.inforsight.controlplane.connectors;

import com.inforsight.controlplane.audit.AuditAppender;
import com.inforsight.controlplane.audit.AuditEvent;
import com.inforsight.controlplane.audit.AuditHash;
import com.inforsight.controlplane.casework.CaseWorkflow;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Fail-closed connector handoff preparation; it has no external transport path. */
public final class ConnectorPreflightService {
    private final Map<ConnectorTarget, ConnectorAdapter> adapters;
    private final AuditAppender audit;
    private final CaseWorkflow cases;
    private final Map<String, Replay> idempotent = new ConcurrentHashMap<>();
    public ConnectorPreflightService(Map<ConnectorTarget, ConnectorAdapter> adapters, AuditAppender audit, CaseWorkflow cases) { this.adapters = Map.copyOf(adapters); this.audit = audit; this.cases = cases; }
    public ConnectorPreflightOutcome preflight(ConnectorPreflightRequest request) {
        String key = request.caseId() + "\u0000" + request.idempotencyKey();
        String digest = AuditHash.sha256(request.target() + "\n" + request.caseVersion() + "\n" + request.snapshotId());
        Replay replay = idempotent.get(key);
        if (replay != null) {
            if (!digest.equals(replay.digest())) throw new IllegalStateException("idempotency key request mismatch");
            return replay.outcome();
        }
        String denial = denial(request);
        if (denial != null) return new ConnectorPreflightOutcome("PREFLIGHT_DENIED", denial, null, false, true);
        ConnectorAdapter adapter = adapters.get(request.target());
        if (adapter == null) return new ConnectorPreflightOutcome("PREFLIGHT_DENIED", "UNSUPPORTED_TARGET", null, false, true);
        ConnectorPreflightOutcome outcome = adapter.prepare(request);
        audit.append(new AuditEvent(UUID.randomUUID(), request.caseId(), request.caseVersion(), "CONNECTOR_PREFLIGHT_RECORDED",
                "connector-preflight", Instant.now(), Map.of("target", request.target().name(), "status", outcome.status(), "idempotency_key", request.idempotencyKey(), "authorized_to_act", false)));
        idempotent.put(key, new Replay(digest, outcome));
        return outcome;
    }
    private String denial(ConnectorPreflightRequest r) {
        var record = cases.find(r.caseId());
        if (record.isEmpty()) return "CASE_NOT_FOUND";
        if (record.get().version() != r.caseVersion()) return "STALE_CASE_VERSION";
        if (!"HUMAN_REVIEWED".equals(record.get().state())) return "HUMAN_REVIEW_REQUIRED";
        if (!r.humanReviewed()) return "HUMAN_REVIEW_REQUIRED";
        if (!r.consentPresent()) return "CONSENT_REQUIRED";
        if (r.legalHold()) return "LEGAL_HOLD";
        if (r.quietHours()) return "QUIET_HOURS";
        if (r.cooldownActive()) return "COOLDOWN_ACTIVE";
        return null;
    }
    private record Replay(String digest, ConnectorPreflightOutcome outcome) {}
}
