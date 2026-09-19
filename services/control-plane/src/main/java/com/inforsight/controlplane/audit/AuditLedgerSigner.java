package com.inforsight.controlplane.audit;

/**
 * Boundary for a future KMS-backed audit signer. Implementations sign a ledger
 * head hash only and must not grant workflow execution authority.
 */
public interface AuditLedgerSigner {
    AuditSignature sign(String ledgerHeadHash);
}
