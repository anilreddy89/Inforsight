package com.inforsight.controlplane.casework;

import com.inforsight.controlplane.domain.InferenceScore;

import java.time.Instant;
import java.util.Optional;

/** Case-work boundary with equivalent in-memory and PostgreSQL implementations. */
public interface CaseWorkflow {
    CaseStore.CaseRecord create(String policyId, Instant asOf, InferenceScore score, String action);
    Optional<CaseStore.CaseRecord> find(String caseId);
    CaseStore.CaseRecord decide(String caseId, String decision, long expectedVersion, String idempotencyKey, String actorId);
    default Optional<String> auditHash(String caseId, long caseVersion) { return Optional.empty(); }
}
