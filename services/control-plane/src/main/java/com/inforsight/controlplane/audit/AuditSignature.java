package com.inforsight.controlplane.audit;

/** Versioned signing result. This is a local seam, not a claim of KMS custody. */
public record AuditSignature(String algorithm, String keyId, String value) {
    public AuditSignature {
        if (algorithm == null || algorithm.isBlank() || keyId == null || keyId.isBlank()
                || value == null || !value.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("signature fields must be present and lowercase SHA-256 hex");
        }
    }
}
