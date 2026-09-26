package com.inforsight.controlplane.agent;

import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.domain.InferenceScore;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AgentDraftStoreTest {
    private static AgentDraftSubmission draft(String caseId, long version, String key) {
        return new AgentDraftSubmission("1.0.0", caseId, version, "DRAFT_FOR_REVIEW", "courtesy_reminder",
                List.of(), List.of("fictional-event-1"), List.of("procedure@2.0"), false, true, key);
    }

    @Test
    void draftIsAdvisoryAndHumanDecisionIsSeparate() {
        var cases = new CaseStore();
        var current = cases.create("fictional-policy", Instant.parse("2026-09-25T00:00:00Z"),
                new InferenceScore("fictional-policy", 0.7, "TIER_3_HIGH", "bundle", "digest", false), "abstain");
        var drafts = new InMemoryAgentDraftStore(cases);
        var submitted = drafts.submit(current.caseId(), draft(current.caseId(), 0, "idem-1"));
        assertThat(submitted.authorizedToAct()).isFalse();
        assertThat(submitted.caseVersion()).isZero();
        assertThat(drafts.find(current.caseId())).contains(submitted);
        assertThat(drafts.submit(current.caseId(), draft(current.caseId(), 0, "idem-1"))).isEqualTo(submitted);
        assertThat(cases.find(current.caseId()).orElseThrow()).isEqualTo(current);
        assertThatThrownBy(() -> drafts.submit(current.caseId(), draft(current.caseId(), 0, "different")))
                .isInstanceOf(IllegalStateException.class);
        var rejected = cases.decide(current.caseId(), "REJECTED", 0, "human-idem", "reviewer-1");
        assertThat(rejected.authorizedToAct()).isFalse();
        assertThat(rejected.state()).isEqualTo("DISMISSED");
        assertThat(drafts.find(current.caseId())).contains(submitted);
    }

    @Test
    void invalidIdentityAuthorityVersionAndShapeFailClosed() {
        var cases = new CaseStore();
        var current = cases.create("fictional-policy", Instant.parse("2026-09-25T00:00:00Z"),
                new InferenceScore("fictional-policy", 0.7, "TIER_3_HIGH", "bundle", "digest", false), "abstain");
        var drafts = new InMemoryAgentDraftStore(cases);
        assertThatThrownBy(() -> drafts.submit(current.caseId(), draft("other-case", 0, "idem")))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> drafts.submit(current.caseId(), draft(current.caseId(), 1, "idem")))
                .isInstanceOf(IllegalStateException.class);
        var baseline = draft(current.caseId(), 0, "idem");
        var escalated = new AgentDraftSubmission("1.0.0", current.caseId(), 0, baseline.status(),
                baseline.actionId(), baseline.reasonCodes(), baseline.evidenceSourceIds(),
                baseline.procedureCitations(), true, true, "idem");
        assertThatThrownBy(() -> drafts.submit(current.caseId(), escalated))
                .isInstanceOf(IllegalArgumentException.class);
        var missingCitation = new AgentDraftSubmission("1.0.0", current.caseId(), 0, baseline.status(),
                baseline.actionId(), List.of(), List.of(), List.of(), false, true, "idem");
        assertThatThrownBy(() -> drafts.submit(current.caseId(), missingCitation))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(drafts.find(current.caseId())).isEmpty();
    }
}
