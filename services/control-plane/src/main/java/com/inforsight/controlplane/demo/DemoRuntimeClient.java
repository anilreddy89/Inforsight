package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;

/** Read-only HTTP calls. A failure never falls back to the bounded hash adapter. */
@Component
@Profile("persistence")
@ConditionalOnProperty(name="inforsight.journey.enabled",havingValue="true")
public class DemoRuntimeClient {
    private final String runtime;
    private final String inference;
    private final ObjectMapper mapper;
    private final HttpClient client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    public DemoRuntimeClient(ObjectMapper mapper,
                             @Value("${INFORSIGHT_DEMO_RUNTIME_BASE_URL:http://demo-runtime:8001}") String runtime,
                             @Value("${inforsight.inference.base-url:http://inference-runtime:8000}") String inference) {
        this.mapper=mapper;this.runtime=runtime.replaceAll("/$","");this.inference=inference.replaceAll("/$","");
    }
    public JsonNode runtime(String path,JsonNode body) {return post(runtime+path,body);}
    public JsonNode score(JsonNode body) {
        JsonNode score=post(inference+"/v1/score",body);
        if(!"inforsight-v6-logistic-platt-20260817".equals(score.path("bundle_id").asText())
                || !"1.0.0".equals(score.path("bundle_version").asText())
                || !"7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656".equals(score.path("bundle_digest").asText())
                || !score.has("authorized_to_act") || score.path("authorized_to_act").asBoolean(true)
                || !body.path("policy_id").asText().equals(score.path("policy_id").asText())
                || !body.path("as_of_date").asText().equals(score.path("as_of_date").asText())
                || !body.path("preprocessing_profile_id").asText().equals(score.path("preprocessing_profile_id").asText())
                || !score.path("calibrated_probability").isNumber()
                || !Double.isFinite(score.path("calibrated_probability").asDouble())
                || score.path("calibrated_probability").asDouble()<0 || score.path("calibrated_probability").asDouble()>1)
            throw new IllegalStateException("RELEASED_MODEL_IDENTITY_OR_AUTHORITY_MISMATCH");
        return score;
    }
    private JsonNode post(String url,JsonNode body) {
        try {
            HttpRequest request=HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(15))
                    .header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(mapper.writeValueAsString(body))).build();
            HttpResponse<String> response=client.send(request,HttpResponse.BodyHandlers.ofString());
            if(response.statusCode()<200||response.statusCode()>=300)throw new DependencyException("DEPENDENCY_HTTP_"+response.statusCode());
            JsonNode result=mapper.readTree(response.body());
            if(!result.isObject())throw new IllegalStateException("INVALID_DEPENDENCY_RESPONSE");
            if(result.has("authorized_to_act")&&result.path("authorized_to_act").asBoolean())throw new IllegalStateException("AUTHORITY_BOUNDARY_VIOLATION");
            return result;
        }catch(InterruptedException e){Thread.currentThread().interrupt();throw new DependencyException("DEPENDENCY_INTERRUPTED");}
        catch(java.io.IOException e){throw new DependencyException("DEPENDENCY_UNAVAILABLE");}
    }
    public static class DependencyException extends IllegalStateException {public DependencyException(String code){super(code);}}
}
