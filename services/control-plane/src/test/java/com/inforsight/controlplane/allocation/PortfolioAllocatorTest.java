package com.inforsight.controlplane.allocation;

import org.junit.jupiter.api.Test;

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
}
