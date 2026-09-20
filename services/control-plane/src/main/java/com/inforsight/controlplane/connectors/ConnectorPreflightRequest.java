package com.inforsight.controlplane.connectors;

import java.time.Instant;

public record ConnectorPreflightRequest(String contractVersion, ConnectorTarget target, String caseId, long caseVersion,
                                        String policyId, String snapshotId, String auditHash, String idempotencyKey,
                                        boolean humanReviewed, boolean consentPresent, boolean legalHold,
                                        boolean quietHours, boolean cooldownActive, Instant asOf) {
    public ConnectorPreflightRequest {
        if (!"connector-preflight/1.0.0".equals(contractVersion) || target == null || caseId == null || caseId.isBlank()
                || caseVersion < 0 || policyId == null || policyId.isBlank() || snapshotId == null || snapshotId.isBlank()
                || auditHash == null || !auditHash.matches("[0-9a-f]{64}") || idempotencyKey == null || idempotencyKey.isBlank()
                || asOf == null) throw new IllegalArgumentException("connector preflight identity fields are required");
    }
}
