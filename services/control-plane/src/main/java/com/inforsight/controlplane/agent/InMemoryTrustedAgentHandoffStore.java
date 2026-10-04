package com.inforsight.controlplane.agent;

import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Service
@Profile("!persistence")
public final class InMemoryTrustedAgentHandoffStore implements TrustedAgentHandoffStore {
    private final Map<String, TrustedAgentHandoff> handoffs = new ConcurrentHashMap<>();
    public void save(TrustedAgentHandoff handoff) {
        if (handoffs.putIfAbsent(handoff.caseId(), handoff) != null) throw new IllegalStateException("handoff already exists");
    }
    public Optional<TrustedAgentHandoff> find(String caseId) { return Optional.ofNullable(handoffs.get(caseId)); }
}
