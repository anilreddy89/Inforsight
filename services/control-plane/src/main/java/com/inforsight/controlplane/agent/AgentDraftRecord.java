package com.inforsight.controlplane.agent;

import com.fasterxml.jackson.annotation.JsonProperty;

/** Case-bound review material, not a human decision or action authorization. */
public record AgentDraftRecord(
        @JsonProperty("case_id") String caseId,
        @JsonProperty("case_version") long caseVersion,
        @JsonProperty("snapshot_id") String snapshotId,
        AgentDraftSubmission draft,
        @JsonProperty("audit_record_hash") String auditRecordHash,
        @JsonProperty("authorized_to_act") boolean authorizedToAct) {}
