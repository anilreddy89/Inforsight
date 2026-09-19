package com.inforsight.controlplane.casework;

import com.inforsight.controlplane.domain.InferenceScore;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class CaseStore {
    private final Map<String, CaseRecord> records = new ConcurrentHashMap<>();
    public CaseRecord create(String policyId, Instant asOf, InferenceScore score, String action) {
        String id = "case_" + UUID.randomUUID();
        CaseRecord record = new CaseRecord(id, policyId, asOf, score, action, "RECOMMENDED", 0, false);
        records.put(id, record);
        return record;
    }
    public Optional<CaseRecord> find(String caseId) { return Optional.ofNullable(records.get(caseId)); }
    public CaseRecord decide(String caseId, String decision, long expectedVersion, String idempotencyKey) {
        CaseRecord current = records.get(caseId);
        if (current == null) throw new IllegalArgumentException("case not found");
        if (current.version() != expectedVersion) throw new IllegalStateException("case version conflict");
        if (idempotencyKey == null || idempotencyKey.isBlank()) throw new IllegalArgumentException("idempotency_key is required");
        boolean authorized = "APPROVED".equals(decision) || "OVERRIDDEN".equals(decision);
        CaseRecord updated = new CaseRecord(current.caseId(), current.policyId(), current.asOf(), current.score(), current.recommendedAction(), "APPROVED".equals(decision) ? "HUMAN_REVIEWED" : "DISMISSED", current.version() + 1, authorized);
        records.replace(caseId, current, updated);
        return updated;
    }
    public record CaseRecord(String caseId, String policyId, Instant asOf, InferenceScore score, String recommendedAction, String state, long version, boolean authorizedToAct) {}
}
