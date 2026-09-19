package com.inforsight.controlplane.audit;

import java.util.List;

public final class AuditLedgerVerifier {
    public Verification verify(List<AuditLedgerEntry> entries) {
        String expectedParent = AuditHash.GENESIS_HASH;
        long expectedSequence = 1;
        for (AuditLedgerEntry entry : entries) {
            if (entry.sequence() != expectedSequence) return Verification.invalid("SEQUENCE_GAP", entry.sequence());
            if (!expectedParent.equals(entry.parentHash())) return Verification.invalid("PARENT_HASH_MISMATCH", entry.sequence());
            String expectedCurrent = AuditHash.chainHash(entry.parentHash(), entry.canonicalPayload());
            if (!expectedCurrent.equals(entry.currentHash())) return Verification.invalid("CURRENT_HASH_MISMATCH", entry.sequence());
            expectedParent = entry.currentHash();
            expectedSequence++;
        }
        return Verification.valid(entries.size());
    }

    public record Verification(boolean valid, String failureCode, long sequence, int verifiedEntries) {
        static Verification valid(int entries) { return new Verification(true, null, 0, entries); }
        static Verification invalid(String code, long sequence) { return new Verification(false, code, sequence, 0); }
    }
}
