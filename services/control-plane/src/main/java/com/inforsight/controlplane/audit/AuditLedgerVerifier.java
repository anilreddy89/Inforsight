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

    /** Verifies the chain against a separately retained head checkpoint. */
    public Verification verify(List<AuditLedgerEntry> entries, AuditLedgerCheckpoint checkpoint) {
        Verification chain = verify(entries);
        if (!chain.valid()) return chain;
        if (entries.isEmpty()) {
            return checkpoint.sequence() == 0 && AuditHash.GENESIS_HASH.equals(checkpoint.currentHash())
                    ? chain : Verification.invalid("CHECKPOINT_HEAD_MISMATCH", 0);
        }
        AuditLedgerEntry head = entries.get(entries.size() - 1);
        if (head.sequence() != checkpoint.sequence()) return Verification.invalid("CHECKPOINT_SEQUENCE_MISMATCH", head.sequence());
        if (!head.currentHash().equals(checkpoint.currentHash())) return Verification.invalid("CHECKPOINT_HASH_MISMATCH", head.sequence());
        return chain;
    }

    public record Verification(boolean valid, String failureCode, long sequence, int verifiedEntries) {
        static Verification valid(int entries) { return new Verification(true, null, 0, entries); }
        static Verification invalid(String code, long sequence) { return new Verification(false, code, sequence, 0); }
    }
}
