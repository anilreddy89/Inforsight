package com.inforsight.controlplane.allocation;

import org.junit.jupiter.api.Test;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.InputStream;
import java.util.ArrayList;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class PortfolioAllocatorTest {
    @Test
    void choosesHighestNetUtilityWithinIntegerCapacitiesWithStableTies() {
        var allocator = new PortfolioAllocator();
        var result = allocator.allocate(List.of(
                new PortfolioAllocator.Candidate("p-2", "email", 3_000_000, 360, 9_000_000, true),
                new PortfolioAllocator.Candidate("p-1", "sms", 1_500_000, 0, 9_000_000, true),
                new PortfolioAllocator.Candidate("p-3", "phone", 65_000_000, 3600, 100_000_000, true)), 4_500_000, 360);
        assertThat(result.selected()).extracting(PortfolioAllocator.Candidate::policyId).containsExactly("p-1", "p-2");
        assertThat(result.usedMoneyMicros()).isEqualTo(4_500_000);
        assertThat(result.usedPersonnelSeconds()).isEqualTo(360);
    }

    @Test
    void matchesSharedPythonReferenceFixture() throws Exception {
        InputStream stream = getClass().getResourceAsStream("/parity/allocation-fixtures.json");
        assertThat(stream).isNotNull();
        JsonNode fixture = new ObjectMapper().readTree(stream).get(0);
        List<PortfolioAllocator.Candidate> candidates = new ArrayList<>();
        fixture.get("candidates").forEach(node -> candidates.add(new PortfolioAllocator.Candidate(
                node.get("policy_id").asText(), node.get("action_type").asText(), node.get("cost_micros").asLong(),
                node.get("personnel_seconds").asInt(), node.get("net_utility_micros").asLong(), node.get("eligible").asBoolean())));
        var result = new PortfolioAllocator().allocate(candidates, fixture.get("budget_micros").asLong(), fixture.get("personnel_seconds").asInt());
        assertThat(result.selected()).extracting(PortfolioAllocator.Candidate::policyId)
                .containsExactlyElementsOf(fixture.get("expected_selected_policy_ids").valueStream().map(JsonNode::asText).toList());
        assertThat(result.usedMoneyMicros()).isEqualTo(fixture.get("expected_budget_used_micros").asLong());
        assertThat(result.usedPersonnelSeconds()).isEqualTo(fixture.get("expected_personnel_used_seconds").asInt());
        assertThat(result.objectiveMicros()).isEqualTo(fixture.get("expected_objective_micros").asLong());
    }
}
