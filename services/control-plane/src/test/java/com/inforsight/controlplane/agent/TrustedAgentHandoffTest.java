package com.inforsight.controlplane.agent;

import org.junit.jupiter.api.Test;
import java.time.Instant;
import java.util.List;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class TrustedAgentHandoffTest {
    private static final TrustedAgentHandoff HANDOFF = new TrustedAgentHandoff("1.0.0", "case-demo", 0,
            "snapshot-demo", "fictional-event", "fictional-policy", Instant.parse("2026-09-25T00:00:00Z"),
            Instant.parse("2026-09-20T00:00:00Z"), "late", List.of("courtesy_reminder", "abstain"),
            "fictional-procedure@2.0", "Fictional review procedure.",
            Instant.parse("2026-01-01T00:00:00Z"), Instant.parse("2027-01-01T00:00:00Z"), false);

    @Test void draftCannotExpandServerOwnedActionOrCitation() {
        HANDOFF.validateDraft(new AgentDraftSubmission("1.0.0", "case-demo", 0, "DRAFT_FOR_REVIEW",
                "courtesy_reminder", List.of(), List.of("fictional-event"), List.of("fictional-procedure@2.0"),
                false, true, "valid"));
        assertThatThrownBy(() -> HANDOFF.validateDraft(new AgentDraftSubmission("1.0.0", "case-demo", 0,
                "DRAFT_FOR_REVIEW", "invented_action", List.of(), List.of("fictional-event"),
                List.of("fictional-procedure@2.0"), false, true, "bad")))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HANDOFF.validateDraft(new AgentDraftSubmission("1.0.0", "case-demo", 0,
                "DRAFT_FOR_REVIEW", "courtesy_reminder", List.of(), List.of("fictional-event"),
                List.of("wrong-procedure@2.0"), false, true, "bad")))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test void futureEventAndStaleCaseFailClosed() {
        assertThatThrownBy(() -> new TrustedAgentHandoff("1.0.0", "case-demo", 0, "snapshot-demo",
                "event", "policy", Instant.parse("2026-09-20T00:00:00Z"), Instant.parse("2026-09-21T00:00:00Z"),
                "late", List.of("abstain"), "fictional-procedure@2.0", "Fictional review procedure.",
                Instant.parse("2026-01-01T00:00:00Z"), Instant.parse("2027-01-01T00:00:00Z"), false))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HANDOFF.validateDraft(new AgentDraftSubmission("1.0.0", "case-demo", 1,
                "ABSTAIN", null, List.of("LOW_CONFIDENCE"), List.of(), List.of(), false, true, "stale")))
                .isInstanceOf(IllegalStateException.class);
    }
}
