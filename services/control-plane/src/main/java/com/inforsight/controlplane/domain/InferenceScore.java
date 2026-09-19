package com.inforsight.controlplane.domain;

public record InferenceScore(String policyId, double calibratedProbability, String operationalTier,
                             String bundleVersion, String bundleDigest, boolean authorizedToAct) {
    public InferenceScore {
        if (authorizedToAct) throw new IllegalArgumentException("inference responses cannot authorize action");
    }
}
