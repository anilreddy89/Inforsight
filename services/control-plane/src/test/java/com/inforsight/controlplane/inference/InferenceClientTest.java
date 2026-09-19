package com.inforsight.controlplane.inference;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.Executors;

import static org.assertj.core.api.Assertions.assertThat;

class InferenceClientTest {
    @Test
    void httpTransportValidatesIdentityAndKeepsAuthorityFalse() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(0), 0);
        server.createContext("/v1/score", exchange -> {
            byte[] response = "{\"policy_id\":\"p-1\",\"calibrated_probability\":0.75,\"operational_tier\":\"TIER_4_CRITICAL\",\"bundle_version\":\"1.0.0\",\"bundle_digest\":\"abc\",\"authorized_to_act\":false}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.start();
        try {
            var client = new HttpInferenceClient(new ObjectMapper(), "http://localhost:" + server.getAddress().getPort(), Duration.ofSeconds(2), 1);
            var score = client.score("p-1", Instant.parse("2026-09-18T00:00:00Z"));
            assertThat(score.calibratedProbability()).isEqualTo(0.75);
            assertThat(score.authorizedToAct()).isFalse();
        } finally { server.stop(0); }
    }

    @Test
    void boundedAdapterHandlesOneThousandVirtualThreadRequests() throws Exception {
        var client = new BoundedInferenceClient();
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            var futures = java.util.stream.IntStream.range(0, 1000)
                    .mapToObj(i -> executor.submit(() -> client.score("p-" + i, Instant.parse("2026-09-18T00:00:00Z"))))
                    .toList();
            for (var future : futures) assertThat(future.get().authorizedToAct()).isFalse();
        }
    }
}
