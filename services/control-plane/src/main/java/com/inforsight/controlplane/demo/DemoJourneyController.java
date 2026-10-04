package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import jakarta.servlet.http.HttpServletRequest;
import java.util.*;

@RestController
@RequestMapping("/api/v1/demo")
@Profile("persistence")
@ConditionalOnProperty(name="inforsight.journey.enabled",havingValue="true")
public class DemoJourneyController {
    private final DemoStore store;private final DemoRuntimeClient runtime;private final ObjectMapper mapper;private final DemoPublicAccess access;
    private static final Map<String,String> SCENARIOS=Map.of("late-payment","late_payment","missing-safety-evidence","missing_evidence","agent-abstention","legal_hold");
    public DemoJourneyController(DemoStore store,DemoRuntimeClient runtime,ObjectMapper mapper,DemoPublicAccess access){this.store=store;this.runtime=runtime;this.mapper=mapper;this.access=access;}

    @GetMapping("/session") public Map<String,Object> session(HttpServletRequest request){return access.description(visitor(request));}

    @GetMapping("/scenarios")
    public Map<String,Object> scenarios(){return Map.of("environment",access.enabled()?"public-preview":"local","external_execution_enabled",false,"scenarios",List.of(
            Map.of("scenario_id","late-payment","title","A late payment","description","A fictional late payment passes through modeled risk, eligibility and resource allocation before human review.","enabled",true),
            Map.of("scenario_id","missing-safety-evidence","title","Missing safety evidence","description","An unknown legal-hold fact stops action eligibility and makes the bounded agent abstain.","enabled",true),
            Map.of("scenario_id","agent-abstention","title","A known legal hold","description","Known legal-hold evidence blocks action. Follow a real abstention to a recorded human decision.","enabled",true)),
            "safe_inputs",Map.of("premium_amount_cents",Map.of("minimum",1000,"maximum",100000),"delay_days",Map.of("minimum",1,"maximum",45)));}

    @PostMapping("/runs")
    public ResponseEntity<ObjectNode> create(@RequestHeader(value="Idempotency-Key",required=false)String key,@RequestBody JsonNode request,HttpServletRequest servlet){
        if(key==null||key.isBlank()||key.length()>128)throw new IllegalArgumentException("Idempotency-Key is required, at most 128 characters");
        exact(request,Set.of("scenario_id","overrides"));
        String scenario=DemoStore.required(request,"scenario_id",64);if(!SCENARIOS.containsKey(scenario))throw new IllegalArgumentException("unknown fictional scenario");
        JsonNode overrides=request.path("overrides");
        if(!overrides.isMissingNode()){
            exact(overrides,Set.of("premium_amount_cents","delay_days"));
            bounds(overrides,"premium_amount_cents",1000,100000);bounds(overrides,"delay_days",1,45);
        }
        var session=visitor(servlet);String scoped=access.scopedKey(session,key),digest=store.hash(request);
        var replay=store.byKey(scoped,digest);if(replay.isPresent())return ResponseEntity.ok(replay.get());
        ObjectNode accepted=access.submit(session,key,digest,()->{
            String correlation="run_"+DemoStore.uuid(),event="evt_"+DemoStore.uuid(),policy="pol_"+DemoStore.uuid();
            ObjectNode body=mapper.createObjectNode().put("scenario_id",SCENARIOS.get(scenario)).put("policy_id",policy).put("event_id",event);
            if(overrides.isObject())body.set("overrides",overrides);
            JsonNode source=runtime.runtime("/v1/demo/scenario",body);
            if(!source.path("fictional").asBoolean()||!source.path("event_id").asText().equals(event))throw new IllegalStateException("scenario source identity mismatch");
            return store.create(correlation,event,policy,scenario,scoped,digest,source);
        });return ResponseEntity.accepted().body(accepted);
    }
    @GetMapping("/runs/{id}") public ObjectNode get(@PathVariable String id){return store.get(id);}
    @PostMapping("/runs/{id}/retry") public ObjectNode retry(@PathVariable String id,HttpServletRequest request){return access.retry(visitor(request),id);}
    @PostMapping("/runs/{id}/decision") public ObjectNode decision(@PathVariable String id,@RequestBody JsonNode body,HttpServletRequest request){
        exact(body,Set.of("decision","expected_case_version","idempotency_key","rationale","notes","reviewer_id"));
        if(access.enabled())((ObjectNode)body).put("reviewer_id","visitor_"+access.tag(visitor(request)));
        return store.decide(id,body);
    }
    @GetMapping("/runs/{id}/audit") public ObjectNode audit(@PathVariable String id){return store.verify(id);}
    @ExceptionHandler(IllegalArgumentException.class) public ResponseEntity<?> bad(IllegalArgumentException e){return ResponseEntity.badRequest().body(Map.of("code","BAD_REQUEST","message",e.getMessage()));}
    @ExceptionHandler(IllegalStateException.class) public ResponseEntity<?> conflict(IllegalStateException e){return ResponseEntity.status(409).body(Map.of("code","CONFLICT","message",e.getMessage()));}
    @ExceptionHandler(DemoRuntimeClient.DependencyException.class) public ResponseEntity<?> unavailable(DemoRuntimeClient.DependencyException e){return ResponseEntity.status(503).body(Map.of("code",e.getMessage(),"message","A required local service is unavailable; no event was accepted."));}
    @ExceptionHandler(NoSuchElementException.class) public ResponseEntity<?> missing(NoSuchElementException e){return ResponseEntity.status(404).body(Map.of("code","NOT_FOUND","message",e.getMessage()));}
    @ExceptionHandler(DemoPublicAccess.Rejection.class) public ResponseEntity<?> limited(DemoPublicAccess.Rejection e){
        Map<String,Object> body=new LinkedHashMap<>();body.put("code",e.code);body.put("message",e.getMessage());
        var response=ResponseEntity.status(e.status);if(e.retryAfter>0){body.put("retry_after_seconds",e.retryAfter);response.header("Retry-After",Integer.toString(e.retryAfter));}return response.body(body);
    }
    private static DemoPublicAccess.Session visitor(HttpServletRequest request){return (DemoPublicAccess.Session)request.getAttribute(DemoPublicAccess.REQUEST_SESSION);}
    static void exact(JsonNode body,Set<String> allowed){if(!body.isObject())throw new IllegalArgumentException("JSON object required");body.fieldNames().forEachRemaining(key->{if(!allowed.contains(key))throw new IllegalArgumentException("unsupported field: "+key);});}
    private static void bounds(JsonNode body,String key,int min,int max){if(body.has(key)&&(!body.get(key).isIntegralNumber()||body.get(key).asLong()<min||body.get(key).asLong()>max))throw new IllegalArgumentException(key+" is outside the fictional demo bounds");}
}
