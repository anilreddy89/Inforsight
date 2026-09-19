package com.inforsight.controlplane.inference;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.domain.InferenceScore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;

/** Opt-in adapter for the bounded Python HTTP serving contract. */
@Component
@ConditionalOnProperty(name = "inforsight.inference.transport", havingValue = "http")
public class HttpInferenceClient implements InferenceClient {
    private final HttpClient client;
    private final ObjectMapper mapper;
    private final URI scoreUri;
    private final Duration timeout;
    private final int maxAttempts;

    public HttpInferenceClient(
            ObjectMapper mapper,
            @Value("${inforsight.inference.base-url}") String baseUrl,
            @Value("${inforsight.inference.timeout:500ms}") Duration timeout,
            @Value("${inforsight.inference.max-attempts:2}") int maxAttempts) {
        this.mapper = mapper;
        this.scoreUri = URI.create(baseUrl.replaceAll("/$", "") + "/v1/score");
        this.timeout = timeout;
        this.maxAttempts = Math.max(1, maxAttempts);
        this.client = HttpClient.newBuilder().connectTimeout(timeout).build();
    }

    @Override
    public InferenceScore score(String policyId, Instant asOf) {
        try {
            String body = mapper.writeValueAsString(java.util.Map.of("policy_id", policyId, "as_of_date", asOf.toString()));
            HttpRequest request = HttpRequest.newBuilder(scoreUri)
                    .timeout(timeout)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            Exception last = null;
            for (int attempt = 1; attempt <= maxAttempts; attempt++) {
                try {
                    HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                    if (response.statusCode() >= 200 && response.statusCode() < 300) return parse(response.body(), policyId);
                    if (response.statusCode() < 500) throw new InferenceUnavailableException("inference returned HTTP " + response.statusCode());
                    last = new InferenceUnavailableException("inference returned retryable HTTP " + response.statusCode());
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw new InferenceUnavailableException("inference request interrupted", interrupted);
                } catch (java.io.IOException | RuntimeException failure) {
                    last = failure;
                }
            }
            throw new InferenceUnavailableException("inference unavailable after " + maxAttempts + " attempts", last);
        } catch (java.io.IOException failure) {
            throw new InferenceUnavailableException("could not encode inference request", failure);
        }
    }

    private InferenceScore parse(String body, String policyId) throws java.io.IOException {
        JsonNode node = mapper.readTree(body);
        boolean authorized = node.path("authorized_to_act").asBoolean(false);
        if (authorized) throw new InferenceUnavailableException("inference response violated ADR 0002 authority boundary");
        String responsePolicy = node.path("policy_id").asText(policyId);
        if (!policyId.equals(responsePolicy)) throw new InferenceUnavailableException("inference response policy identity mismatch");
        return new InferenceScore(responsePolicy,
                node.path("calibrated_probability").asDouble(),
                node.path("operational_tier").asText("TIER_1_LOW"),
                node.path("bundle_version").asText("unknown"),
                node.path("bundle_digest").asText("unknown"), false);
    }

    public static class InferenceUnavailableException extends RuntimeException {
        public InferenceUnavailableException(String message) { super(message); }
        public InferenceUnavailableException(String message, Throwable cause) { super(message, cause); }
    }
}
