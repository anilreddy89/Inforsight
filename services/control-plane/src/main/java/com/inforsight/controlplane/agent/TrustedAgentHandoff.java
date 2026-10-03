package com.inforsight.controlplane.agent;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;

/** Server-owned fictional demo evidence; never an execution authorization. */
public record TrustedAgentHandoff(
        @JsonProperty("contract_version") String contractVersion,
        @JsonProperty("case_id") String caseId,
        @JsonProperty("case_version") long caseVersion,
        @JsonProperty("snapshot_id") String snapshotId,
        @JsonProperty("event_id") String eventId,
        @JsonProperty("policy_id") String policyId,
        @JsonProperty("as_of") Instant asOf,
        @JsonProperty("observed_at") Instant observedAt,
        @JsonProperty("payment_status") String paymentStatus,
        @JsonProperty("allowed_actions") List<String> allowedActions,
        @JsonProperty("procedure_citation") String procedureCitation,
        @JsonProperty("procedure_text") String procedureText,
        @JsonProperty("procedure_effective_from") Instant procedureEffectiveFrom,
        @JsonProperty("procedure_effective_until") Instant procedureEffectiveUntil,
        @JsonProperty("authorized_to_act") boolean authorizedToAct) {
    public TrustedAgentHandoff {
        allowedActions = List.copyOf(allowedActions);
        if (!"1.0.0".equals(contractVersion) || authorizedToAct || caseVersion != 0
                || observedAt.isAfter(asOf) || !allowedActions.contains("abstain")
                || procedureText == null || procedureText.isBlank()
                || procedureEffectiveFrom.isAfter(asOf) || !asOf.isBefore(procedureEffectiveUntil)) {
            throw new IllegalArgumentException("invalid trusted handoff");
        }
    }

    public void validateDraft(AgentDraftSubmission draft) {
        if (draft.expectedCaseVersion() != caseVersion) throw new IllegalStateException("handoff case version conflict");
        if ("DRAFT_FOR_REVIEW".equals(draft.status()) &&
                (!allowedActions.contains(draft.actionId()) || "abstain".equals(draft.actionId())
                        || !draft.procedureCitations().equals(List.of(procedureCitation))
                        || !draft.evidenceSourceIds().equals(List.of(eventId)))) {
            throw new IllegalArgumentException("draft is not supported by trusted handoff");
        }
    }
}
