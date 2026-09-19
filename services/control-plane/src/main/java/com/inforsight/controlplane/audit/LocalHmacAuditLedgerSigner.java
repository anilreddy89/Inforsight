package com.inforsight.controlplane.audit;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.Arrays;

/**
 * Deterministic local test/development signer. Its caller supplies key material;
 * it is deliberately not a production KMS or key-custody implementation.
 */
public final class LocalHmacAuditLedgerSigner implements AuditLedgerSigner {
    public static final String ALGORITHM = "HMAC-SHA256-LOCAL-V1";
    private final String keyId;
    private final byte[] key;

    public LocalHmacAuditLedgerSigner(String keyId, byte[] key) {
        if (keyId == null || keyId.isBlank() || key == null || key.length < 16) {
            throw new IllegalArgumentException("local signer requires a key id and at least 16 bytes of key material");
        }
        this.keyId = keyId;
        this.key = Arrays.copyOf(key, key.length);
    }

    @Override
    public AuditSignature sign(String ledgerHeadHash) {
        if (ledgerHeadHash == null || !ledgerHeadHash.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException("ledger head must be lowercase SHA-256 hex");
        }
        return new AuditSignature(ALGORITHM, keyId, hmac(ledgerHeadHash));
    }

    public boolean verifies(String ledgerHeadHash, AuditSignature signature) {
        return signature != null && ALGORITHM.equals(signature.algorithm()) && keyId.equals(signature.keyId())
                && constantTimeEquals(hmac(ledgerHeadHash), signature.value());
    }

    private String hmac(String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            return java.util.HexFormat.of().formatHex(mac.doFinal(value.getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException failure) {
            throw new IllegalStateException("HMAC-SHA256 is unavailable", failure);
        }
    }

    private static boolean constantTimeEquals(String left, String right) {
        return java.security.MessageDigest.isEqual(left.getBytes(StandardCharsets.UTF_8), right.getBytes(StandardCharsets.UTF_8));
    }
}
