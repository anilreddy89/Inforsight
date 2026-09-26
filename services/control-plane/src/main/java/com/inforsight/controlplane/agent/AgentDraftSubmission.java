package com.inforsight.controlplane.agent;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.ArrayList;
import java.util.Collections;

/** Untrusted advisory payload. Validation grants no action authority. */
public record AgentDraftSubmission(
        @JsonProperty("contract_version") String contractVersion,
        @JsonProperty("case_id") String caseId,
        @JsonProperty("expected_case_version") long expectedCaseVersion,
        String status,
        @JsonProperty("action_id") String actionId,
        @JsonProperty("reason_codes") List<String> reasonCodes,
        @JsonProperty("evidence_source_ids") List<String> evidenceSourceIds,
        @JsonProperty("procedure_citations") List<String> procedureCitations,
        @JsonProperty("authorized_to_act") boolean authorizedToAct,
        @JsonProperty("human_review_required") boolean humanReviewRequired,
        @JsonProperty("idempotency_key") String idempotencyKey) {

    public AgentDraftSubmission {
        reasonCodes = reasonCodes == null ? null : Collections.unmodifiableList(new ArrayList<>(reasonCodes));
        evidenceSourceIds = evidenceSourceIds == null ? null : Collections.unmodifiableList(new ArrayList<>(evidenceSourceIds));
        procedureCitations = procedureCitations == null ? null : Collections.unmodifiableList(new ArrayList<>(procedureCitations));
    }

    public void validate(String pathCaseId) {
        if (!"1.0.0".equals(contractVersion) || caseId == null || !caseId.equals(pathCaseId)
                || caseId.length() > 128 || expectedCaseVersion < 0
                || idempotencyKey == null || idempotencyKey.isBlank() || idempotencyKey.length() > 128
                || authorizedToAct || !humanReviewRequired
                || reasonCodes == null || evidenceSourceIds == null || procedureCitations == null
                || reasonCodes.size() > 16 || evidenceSourceIds.size() > 128 || procedureCitations.size() > 32
                || !bounded(reasonCodes) || !bounded(evidenceSourceIds) || !bounded(procedureCitations)) {
            throw new IllegalArgumentException("invalid review-only agent draft");
        }
        if ("DRAFT_FOR_REVIEW".equals(status)) {
            if (actionId == null || actionId.isBlank() || actionId.length() > 128
                    || procedureCitations.isEmpty() || !reasonCodes.isEmpty()) {
                throw new IllegalArgumentException("invalid review-only agent draft");
            }
        } else if ("ABSTAIN".equals(status)) {
            if (actionId != null || reasonCodes.isEmpty() || !evidenceSourceIds.isEmpty()
                    || !procedureCitations.isEmpty()) {
                throw new IllegalArgumentException("invalid review-only agent draft");
            }
        } else {
            throw new IllegalArgumentException("invalid review-only agent draft");
        }
    }

    private static boolean bounded(List<String> values) {
        return values.stream().allMatch(value -> value != null && !value.isBlank() && value.length() <= 128);
    }
}
