package com.inforsight.controlplane.casework;

import com.inforsight.controlplane.domain.InferenceScore;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;

class CaseStoreTest {
    @Test
    void sameIdempotencyKeyReplaysCommittedDecisionWithoutIncrementingVersion() {
        var store = new CaseStore();
        var created = store.create("p-1", Instant.parse("2026-09-18T00:00:00Z"), new InferenceScore("p-1", .5, "TIER_3_HIGH", "fixture", "digest", false), "abstain");
        var first = store.decide(created.caseId(), "APPROVED", 0, "decision-1");
        var replay = store.decide(created.caseId(), "APPROVED", 0, "decision-1");
        assertThat(replay).isEqualTo(first);
        assertThat(replay.version()).isEqualTo(1);
        assertThat(replay.authorizedToAct()).isTrue();
    }
}
