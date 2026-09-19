package com.inforsight.controlplane.inference;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.utility.MountableFile;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** Docker-backed contract test; opt in with INFORSIGHT_RUN_JAVA_INTEGRATION=1. */
@EnabledIfEnvironmentVariable(named = "INFORSIGHT_RUN_JAVA_INTEGRATION", matches = "1")
class InferenceContainerIntegrationTest {
    @Test
    void httpInferenceAdapterReachesContainerizedServingBoundary() {
        String image = System.getProperty("inforsight.serving.image", "python:3.12-alpine");
        GenericContainer<?> configured = new GenericContainer<>(image);
        if (image.equals("python:3.12-alpine")) {
            configured.withCopyFileToContainer(MountableFile.forClasspathResource("testcontainers/inference_stub.py"), "/tmp/inference_stub.py")
                    .withCommand("python3", "/tmp/inference_stub.py");
        }
        try (GenericContainer<?> container = configured.withExposedPorts(8000)
                .withStartupTimeout(Duration.ofMinutes(3))) {
            container.start();
            var client = new HttpInferenceClient(new ObjectMapper(), "http://" + container.getHost() + ":" + container.getMappedPort(8000), Duration.ofSeconds(5), 2);
            var score = client.scoreWithFeatures("container-policy", Instant.parse("2026-09-18T00:00:00Z"), Map.ofEntries(
                    Map.entry("tenure_days", 1.5), Map.entry("premium_amount_cents", 1.2), Map.entry("recent_delay_days", 0.8),
                    Map.entry("recent_failed_payment_count", 1.0), Map.entry("recent_retry_count", 0.5), Map.entry("recent_recovery_count", 0.0),
                    Map.entry("arrears_duration_days", 0.6), Map.entry("rolling_on_time_rate", 0.65), Map.entry("rolling_payment_count", 0.8),
                    Map.entry("recent_notice_count", 0.5), Map.entry("recent_contact_count", 0.3), Map.entry("payment_attribute_missing", 0.0),
                    Map.entry("contact_attribute_missing", 0.0), Map.entry("product_type", "fictional_term_life"),
                    Map.entry("billing_frequency", "monthly"), Map.entry("notice_category", "grace_warning"), Map.entry("contact_category", "none")));
            assertThat(score.policyId()).isEqualTo("container-policy");
            if (image.equals("python:3.12-alpine")) assertThat(score.bundleVersion()).isEqualTo("fixture-1.0.0");
            assertThat(score.authorizedToAct()).isFalse();
        }
    }
}
