package com.inforsight.controlplane.inference;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.utility.MountableFile;

import java.time.Duration;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;

/** Docker-backed contract test; opt in with INFORSIGHT_RUN_JAVA_INTEGRATION=1. */
@EnabledIfEnvironmentVariable(named = "INFORSIGHT_RUN_JAVA_INTEGRATION", matches = "1")
class InferenceContainerIntegrationTest {
    @Test
    void httpInferenceAdapterReachesContainerizedServingBoundary() {
        try (GenericContainer<?> container = new GenericContainer<>("python:3.12-alpine")
                .withCopyFileToContainer(MountableFile.forClasspathResource("testcontainers/inference_stub.py"), "/tmp/inference_stub.py")
                .withExposedPorts(8000)
                .withCommand("python3", "/tmp/inference_stub.py")) {
            container.start();
            var client = new HttpInferenceClient(new ObjectMapper(), "http://" + container.getHost() + ":" + container.getMappedPort(8000), Duration.ofSeconds(5), 2);
            var score = client.score("container-policy", Instant.parse("2026-09-18T00:00:00Z"));
            assertThat(score.policyId()).isEqualTo("container-policy");
            assertThat(score.bundleVersion()).isEqualTo("fixture-1.0.0");
            assertThat(score.authorizedToAct()).isFalse();
        }
    }
}
