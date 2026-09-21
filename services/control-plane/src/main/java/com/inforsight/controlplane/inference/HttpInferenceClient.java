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
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Opt-in adapter for the bounded Python HTTP serving contract. */
@Component
@ConditionalOnProperty(name = "inforsight.inference.transport", havingValue = "http")
public class HttpInferenceClient implements InferenceClient {
    private final HttpClient client;
    private final ObjectMapper mapper;
    private final URI scoreUri;
    private final URI minimalScoreUri;
    private final URI minimalBatchScoreUri;
    private final Duration timeout;
    private final int maxAttempts;

    public HttpInferenceClient(
            ObjectMapper mapper,
            @Value("${inforsight.inference.base-url}") String baseUrl,
            @Value("${inforsight.inference.timeout:500ms}") Duration timeout,
            @Value("${inforsight.inference.max-attempts:2}") int maxAttempts) {
        this.mapper = mapper;
        this.scoreUri = URI.create(baseUrl.replaceAll("/$", "") + "/v1/score");
        this.minimalScoreUri = URI.create(baseUrl.replaceAll("/$", "") + "/v1/score/minimal");
        this.minimalBatchScoreUri = URI.create(baseUrl.replaceAll("/$", "") + "/v1/score/minimal/batch");
        this.timeout = timeout;
        this.maxAttempts = Math.max(1, maxAttempts);
        this.client = HttpClient.newBuilder().connectTimeout(timeout).build();
    }

    @Override
    public InferenceScore score(String policyId, Instant asOf) {
        return scoreWithFeatures(policyId, asOf, Map.of());
    }

    /** Scores a raw-v6 record when the caller has the feature snapshot available. */
    public InferenceScore scoreWithFeatures(String policyId, Instant asOf, Map<String, Object> features) {
        try {
            Map<String, Object> request = new java.util.LinkedHashMap<>();
            request.put("policy_id", policyId);
            request.put("observation_id", asOf.toString());
            request.put("as_of_date", asOf.toString());
            request.put("feature_stage", "raw-v6-features");
            request.put("preprocessing_profile_id", "v6-coefficient-transform-then-bundle-zscore/1.0.0");
            request.put("features", features);
            String body = mapper.writeValueAsString(request);
            HttpRequest httpRequest = HttpRequest.newBuilder(scoreUri)
                    .timeout(timeout)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            Exception last = null;
            for (int attempt = 1; attempt <= maxAttempts; attempt++) {
                try {
                    HttpResponse<String> response = client.send(httpRequest, HttpResponse.BodyHandlers.ofString());
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

    /** Control-plane response profile without explanation payloads. */
    public InferenceScore scoreMinimalWithFeatures(String policyId, Instant asOf, Map<String, Object> features) {
        try {
            Map<String, Object> request = new java.util.LinkedHashMap<>();
            request.put("policy_id", policyId);
            request.put("observation_id", asOf.toString());
            request.put("as_of_date", asOf.toString());
            request.put("feature_stage", "raw-v6-features");
            request.put("preprocessing_profile_id", "v6-coefficient-transform-then-bundle-zscore/1.0.0");
            request.put("features", features);
            HttpRequest httpRequest = HttpRequest.newBuilder(minimalScoreUri).timeout(timeout)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(request))).build();
            HttpResponse<String> response = client.send(httpRequest, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new InferenceUnavailableException("minimal inference returned HTTP " + response.statusCode());
            }
            return parse(response.body(), policyId);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new InferenceUnavailableException("minimal inference request interrupted", interrupted);
        } catch (java.io.IOException | RuntimeException failure) {
            if (failure instanceof InferenceUnavailableException unavailable) throw unavailable;
            throw new InferenceUnavailableException("minimal inference unavailable", failure);
        }
    }

    /** Scores a bounded Kafka poll in one HTTP request using the minimal response profile. */
    public List<InferenceScore> scoreMinimalBatchWithFeatures(List<InferenceRequest> requests) {
        if (requests.isEmpty()) return List.of();
        try {
            Map<String, Object> body = Map.of("requests", requests.stream().map(request -> {
                Map<String, Object> payload = new java.util.LinkedHashMap<>();
                payload.put("policy_id", request.policyId());
                payload.put("observation_id", request.asOf().toString());
                payload.put("as_of_date", request.asOf().toString());
                payload.put("feature_stage", "raw-v6-features");
                payload.put("preprocessing_profile_id", "v6-coefficient-transform-then-bundle-zscore/1.0.0");
                payload.put("features", request.features());
                return payload;
            }).toList());
            HttpRequest httpRequest = HttpRequest.newBuilder(minimalBatchScoreUri).timeout(timeout)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body))).build();
            HttpResponse<String> response = client.send(httpRequest, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new InferenceUnavailableException("minimal batch inference returned HTTP " + response.statusCode());
            }
            JsonNode scores = mapper.readTree(response.body());
            if (!scores.isArray() || scores.size() != requests.size()) {
                throw new InferenceUnavailableException("minimal batch inference response count mismatch");
            }
            List<InferenceScore> parsed = new ArrayList<>();
            for (int index = 0; index < requests.size(); index++) {
                parsed.add(parseNode(scores.get(index), requests.get(index).policyId()));
            }
            return parsed;
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new InferenceUnavailableException("minimal batch inference request interrupted", interrupted);
        } catch (java.io.IOException | RuntimeException failure) {
            if (failure instanceof InferenceUnavailableException unavailable) throw unavailable;
            throw new InferenceUnavailableException("minimal batch inference unavailable", failure);
        }
    }

    private InferenceScore parse(String body, String policyId) throws java.io.IOException {
        return parseNode(mapper.readTree(body), policyId);
    }

    private InferenceScore parseNode(JsonNode node, String policyId) {
        boolean authorized = node.path("authorized_to_act").asBoolean(false);
        if (authorized) throw new InferenceUnavailableException("inference response violated ADR 0002 authority boundary");
        String responsePolicy = node.path("policy_id").asText(policyId);
        if (!policyId.equals(responsePolicy)) throw new InferenceUnavailableException("inference response policy identity mismatch");
        return new InferenceScore(responsePolicy,
                node.path("calibrated_probability").asDouble(),
                node.path("operational_tier").asText(node.path("risk_tier_id").asText("TIER_1_LOW")),
                node.path("bundle_version").asText("unknown"),
                node.path("bundle_digest").asText("unknown"), false);
    }

    public record InferenceRequest(String policyId, Instant asOf, Map<String, Object> features) {}

    public static class InferenceUnavailableException extends RuntimeException {
        public InferenceUnavailableException(String message) { super(message); }
        public InferenceUnavailableException(String message, Throwable cause) { super(message, cause); }
    }
}
