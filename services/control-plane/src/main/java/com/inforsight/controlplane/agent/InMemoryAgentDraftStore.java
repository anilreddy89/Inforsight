package com.inforsight.controlplane.agent;

import com.inforsight.controlplane.audit.AuditHash;
import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.casework.CaseWorkflow;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@Service
@Profile("!persistence")
public final class InMemoryAgentDraftStore implements AgentDraftStore {
    private final CaseWorkflow cases;
    private final Map<String, AgentDraftRecord> drafts = new HashMap<>();

    public InMemoryAgentDraftStore(CaseWorkflow cases) { this.cases = cases; }

    public synchronized AgentDraftRecord submit(String caseId, AgentDraftSubmission draft) {
        draft.validate(caseId);
        AgentDraftRecord prior = drafts.get(caseId);
        if (prior != null) {
            if (prior.draft().equals(draft)) return prior;
            throw new IllegalStateException("agent draft already exists for case");
        }
        CaseStore.CaseRecord current = cases.find(caseId)
                .orElseThrow(() -> new IllegalArgumentException("case not found"));
        if (current.version() != draft.expectedCaseVersion() || !"RECOMMENDED".equals(current.state())
                || current.authorizedToAct()) throw new IllegalStateException("case version or state conflict");
        String snapshot = "snapshot_" + AuditHash.sha256(current.policyId() + "\n" + current.asOf()
                + "\n" + current.score().bundleVersion() + "\n" + current.score().bundleDigest()
                + "\n" + current.score().calibratedProbability() + "\n" + current.score().operationalTier());
        AgentDraftRecord record = new AgentDraftRecord(caseId, current.version(), snapshot, draft, null, false);
        drafts.put(caseId, record);
        return record;
    }

    public synchronized Optional<AgentDraftRecord> find(String caseId) {
        return Optional.ofNullable(drafts.get(caseId));
    }
}
