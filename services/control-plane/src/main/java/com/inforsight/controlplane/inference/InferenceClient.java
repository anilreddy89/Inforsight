package com.inforsight.controlplane.inference;

import com.inforsight.controlplane.domain.InferenceScore;

import java.time.Instant;
import java.util.Map;

public interface InferenceClient {
    InferenceScore score(String policyId, Instant asOf);
    default InferenceScore scoreWithFeatures(String policyId, Instant asOf, Map<String, Object> features) {
        return score(policyId, asOf);
    }
}
