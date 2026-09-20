package com.inforsight.controlplane.connectors;

import com.inforsight.controlplane.audit.AuditHash;

/** Deterministic fake adapter: it constructs no request and performs no I/O. */
public final class FakeConnectorAdapter implements ConnectorAdapter {
    private final ConnectorTarget target;
    public FakeConnectorAdapter(ConnectorTarget target) { this.target = target; }
    public ConnectorTarget target() { return target; }
    public ConnectorPreflightOutcome prepare(ConnectorPreflightRequest request) {
        String reference = "preflight_" + target.name().toLowerCase() + "_" + AuditHash.sha256(request.idempotencyKey()).substring(0, 16);
        return new ConnectorPreflightOutcome("PREFLIGHT_READY", "EXTERNAL_EXECUTION_DISABLED", reference, false, true);
    }
}
