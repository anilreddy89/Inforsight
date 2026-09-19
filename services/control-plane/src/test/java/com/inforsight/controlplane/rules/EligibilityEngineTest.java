package com.inforsight.controlplane.rules;

import com.inforsight.controlplane.domain.PolicyContext;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;

class EligibilityEngineTest {
    private final EligibilityEngine engine = new EligibilityEngine();
    private final Instant asOf = Instant.parse("2026-09-18T00:00:00Z");

    @Test
    void missingSafetyEvidenceFailsClosedExceptAbstain() {
        var results = engine.evaluate(new PolicyContext("p-1", asOf, "active", 120, false, 0, null, false, false, false, false, false, false, null));
        assertThat(results).filteredOn(r -> !r.actionType().equals("abstain")).allMatch(r -> !r.eligible() && r.reasons().contains("DISQUALIFIED_MISSING_SAFETY_EVIDENCE"));
    }

    @Test
    void legalHoldFreezesAllActiveActions() {
        var results = engine.evaluate(new PolicyContext("p-1", asOf, "active", 120, false, 0, false, true, false, false, false, false, false, null));
        assertThat(results).filteredOn(r -> !r.actionType().equals("abstain")).allMatch(r -> !r.eligible() && r.reasons().contains("DISQUALIFIED_LEGAL_HOLD"));
    }

    @Test
    void consentAndTenureAreEvaluatedDeterministically() {
        var results = engine.evaluate(new PolicyContext("p-1", asOf, "active", 30, false, 0, false, false, false, true, false, false, false, null));
        var courtesy = results.stream().filter(r -> r.actionType().equals("courtesy_reminder")).findFirst().orElseThrow();
        assertThat(courtesy.eligible()).isFalse();
        assertThat(courtesy.reasons()).contains("DISQUALIFIED_CHANNEL_OPT_OUT_SMS");
    }
}
