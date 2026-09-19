package com.inforsight.controlplane.audit;

@FunctionalInterface
public interface AuditAppender {
    AuditLedgerEntry append(AuditEvent event);
}
