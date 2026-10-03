package com.inforsight.controlplane.agent;

import java.util.Optional;

public interface AgentDraftStore {
    AgentDraftRecord submit(String caseId, AgentDraftSubmission draft);
    Optional<AgentDraftRecord> find(String caseId);
}
