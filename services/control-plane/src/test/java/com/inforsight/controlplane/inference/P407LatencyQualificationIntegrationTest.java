package com.inforsight.controlplane.inference;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.casework.CaseStore;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** Opt-in E2 measurement against an explicitly supplied inference HTTP runtime. */
class P407LatencyQualificationIntegrationTest {
    @Test
    void measuresIngressToScoredCaseP99BelowTheFrozenFloor() {
        Assumptions.assumeTrue("1".equals(System.getenv("INFORSIGHT_RUN_P4_07_LATENCY_INTEGRATION")));
        String baseUrl = System.getenv("INFORSIGHT_P4_07_INFERENCE_BASE_URL");
        Assumptions.assumeTrue(baseUrl != null && !baseUrl.isBlank(),
                "E2 requires INFORSIGHT_P4_07_INFERENCE_BASE_URL");

        HttpInferenceClient inference = new HttpInferenceClient(new ObjectMapper(), baseUrl,
                Duration.ofSeconds(2), 1);
        CaseStore cases = new CaseStore();
        Map<String, Object> features = Map.ofEntries(
                Map.entry("tenure_days", 365.0), Map.entry("premium_amount_cents", 1000.0),
                Map.entry("recent_delay_days", 0.0), Map.entry("recent_failed_payment_count", 0.0),
                Map.entry("recent_retry_count", 0.0), Map.entry("recent_recovery_count", 1.0),
                Map.entry("arrears_duration_days", 0.0), Map.entry("rolling_on_time_rate", 1.0),
                Map.entry("rolling_payment_count", 12.0), Map.entry("recent_notice_count", 0.0),
                Map.entry("recent_contact_count", 0.0), Map.entry("payment_attribute_missing", 0.0),
                Map.entry("contact_attribute_missing", 0.0), Map.entry("product_type", "fictional_term_life"),
                Map.entry("billing_frequency", "monthly"), Map.entry("notice_category", "none"),
                Map.entry("contact_category", "none"));

        for (int index = 0; index < 10; index++) {
            scoreAndCreate(inference, cases, features, index);
        }
        List<Long> durationsNanos = new ArrayList<>();
        for (int index = 0; index < 100; index++) {
            long started = System.nanoTime();
            scoreAndCreate(inference, cases, features, index + 10);
            durationsNanos.add(System.nanoTime() - started);
        }
        durationsNanos.sort(Comparator.naturalOrder());
        long p99Nanos = durationsNanos.get((int) Math.ceil(durationsNanos.size() * 0.99) - 1);
        double p99Millis = p99Nanos / 1_000_000.0;
        System.out.printf("P4-07 E2 observed ingress-to-scored-case p99: %.3f ms; samples=%d%n",
                p99Millis, durationsNanos.size());
        assertThat(p99Millis).isLessThanOrEqualTo(50.0);
    }

    private static CaseStore.CaseRecord scoreAndCreate(HttpInferenceClient inference, CaseStore cases,
                                                        Map<String, Object> features, int index) {
        Instant asOf = Instant.parse("2026-09-18T00:00:00Z");
        String policyId = "p407-latency-" + index;
        var score = inference.scoreWithFeatures(policyId, asOf, features);
        return cases.create(policyId, asOf, score, "abstain");
    }
}
