package com.inforsight.controlplane.audit;

/**
 * A ledger head captured outside the rows being verified. Keeping this value in
 * a separate trusted store is what makes tail deletion detectable.
 */
public record AuditLedgerCheckpoint(long sequence, String currentHash) {
    public AuditLedgerCheckpoint {
        if (sequence < 0 || currentHash == null || !currentHash.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("checkpoint must contain a non-negative sequence and lowercase SHA-256 hash");
        }
    }
}
