package com.inforsight.controlplane.inference;

import com.inforsight.controlplane.domain.InferenceScore;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.Objects;

/** Bounded local adapter; the production gRPC transport is a separately versioned integration. */
@Component
public class BoundedInferenceClient implements InferenceClient {
    @Override
    public InferenceScore score(String policyId, Instant asOf) {
        Objects.requireNonNull(policyId);
        int hash = Math.floorMod(Objects.hash(policyId, asOf), 1000);
        double probability = hash / 1000.0;
        String tier = probability >= .75 ? "TIER_4_CRITICAL" : probability >= .50 ? "TIER_3_HIGH" : probability >= .25 ? "TIER_2_ELEVATED" : "TIER_1_LOW";
        return new InferenceScore(policyId, probability, tier, "bounded-local-adapter", "not-a-production-digest", false);
    }
}
