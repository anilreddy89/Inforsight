package com.inforsight.controlplane.agent;

import java.util.Optional;

public interface TrustedAgentHandoffStore {
    void save(TrustedAgentHandoff handoff);
    Optional<TrustedAgentHandoff> find(String caseId);
}
