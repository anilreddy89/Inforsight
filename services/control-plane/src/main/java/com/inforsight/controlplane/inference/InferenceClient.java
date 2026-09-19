package com.inforsight.controlplane.inference;

import com.inforsight.controlplane.domain.InferenceScore;

import java.time.Instant;

public interface InferenceClient {
    InferenceScore score(String policyId, Instant asOf);
}
