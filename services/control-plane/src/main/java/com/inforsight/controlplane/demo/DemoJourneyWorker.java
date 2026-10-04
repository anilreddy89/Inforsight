package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.inforsight.controlplane.allocation.PortfolioAllocator;
import com.inforsight.controlplane.domain.PolicyContext;
import com.inforsight.controlplane.rules.EligibilityEngine;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.errors.WakeupException;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.SmartLifecycle;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Supplier;

/** One bounded local worker: transactional outbox -> Kafka -> durable inbox -> real services. */
@Component
@Profile("persistence")
@ConditionalOnProperty(name="inforsight.journey.enabled",havingValue="true")
public class DemoJourneyWorker implements SmartLifecycle {
    public static final String TOPIC="inforsight.demo.events.v1";
    private final DemoStore store;private final DemoRuntimeClient runtime;private final ObjectMapper mapper;
    private final EligibilityEngine rules;private final PortfolioAllocator allocator;private final String bootstrap;
    private final ExecutorService executor=Executors.newVirtualThreadPerTaskExecutor();
    private volatile boolean running;private volatile KafkaConsumer<String,String> consumer;
    public DemoJourneyWorker(DemoStore store,DemoRuntimeClient runtime,ObjectMapper mapper,EligibilityEngine rules,
                             PortfolioAllocator allocator,@Value("${INFORSIGHT_KAFKA_BOOTSTRAP_SERVERS:kafka:29092}")String bootstrap){
        this.store=store;this.runtime=runtime;this.mapper=mapper;this.rules=rules;this.allocator=allocator;this.bootstrap=bootstrap;
    }
    @Override public void start(){running=true;executor.submit(this::loop);}
    @Override public void stop(){running=false;if(consumer!=null)consumer.wakeup();executor.shutdown();}
    @Override public boolean isRunning(){return running;}
    @Override public int getPhase(){return Integer.MAX_VALUE-1;}
    private void loop(){
        while(running){
            try{
                try(AdminClient admin=AdminClient.create(Map.of(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG,bootstrap))){
                    try{admin.createTopics(List.of(new NewTopic(TOPIC,1,(short)1))).all().get(15,TimeUnit.SECONDS);}
                    catch(ExecutionException e){if(!(e.getCause() instanceof org.apache.kafka.common.errors.TopicExistsException))throw e;}
                }
                Properties producerConfig=new Properties();producerConfig.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG,bootstrap);
                producerConfig.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,StringSerializer.class.getName());producerConfig.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG,StringSerializer.class.getName());
                producerConfig.put(ProducerConfig.ACKS_CONFIG,"all");producerConfig.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG,true);
                producerConfig.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG,15000);producerConfig.put(ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG,5000);producerConfig.put(ProducerConfig.MAX_BLOCK_MS_CONFIG,10000);
                Properties consumerConfig=new Properties();consumerConfig.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG,bootstrap);
                consumerConfig.put(ConsumerConfig.GROUP_ID_CONFIG,"inforsight-demo-journey-v1");consumerConfig.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,StringDeserializer.class.getName());consumerConfig.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,StringDeserializer.class.getName());
                consumerConfig.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG,false);consumerConfig.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG,"earliest");consumerConfig.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG,10);
                try(KafkaProducer<String,String> producer=new KafkaProducer<>(producerConfig);KafkaConsumer<String,String> active=new KafkaConsumer<>(consumerConfig)){
                    consumer=active;active.subscribe(List.of(TOPIC));
                    while(running){
                        for(ObjectNode event:store.pending())publish(producer,event);
                        ConsumerRecords<String,String> records=active.poll(Duration.ofMillis(250));
                        for(ConsumerRecord<String,String> record:records){
                            try {
                                JsonNode envelope=store.parse(record.value());
                                if(record.key()==null||!record.key().equals(envelope.path("event_id").asText()))throw new IllegalArgumentException("Kafka identity mismatch");
                                store.ingest(envelope,record.topic(),record.partition(),record.offset(),record.timestamp());
                            } catch(org.springframework.dao.DataAccessException unavailable) {
                                throw unavailable; // no offset commits if durable acceptance is unavailable
                            } catch(Exception rejected) {
                                store.quarantine(record.topic(),record.partition(),record.offset(),record.value(),"INVALID_OR_UNBOUND_DEMO_ENVELOPE");
                            }
                        }
                        if(!records.isEmpty())active.commitSync();
                        for(String id:store.resumable())process(id);
                    }
                }finally{consumer=null;}
            }catch(WakeupException ignored){if(!running)return;}
            catch(Exception e){
                System.err.println("Demo journey worker reconnecting: "+e.getClass().getSimpleName());
                try{Thread.sleep(1000);}catch(InterruptedException interrupted){Thread.currentThread().interrupt();return;}
            }
        }
    }
    private void publish(KafkaProducer<String,String> producer,ObjectNode envelope){
        String id=envelope.path("correlation_id").asText();
        try{
            store.publishing(id);
            RecordMetadata receipt=producer.send(new ProducerRecord<>(TOPIC,envelope.path("event_id").asText(),store.encode(envelope))).get(20,TimeUnit.SECONDS);
            ObjectNode evidence=mapper.createObjectNode().put("topic",receipt.topic()).put("partition",receipt.partition()).put("offset",receipt.offset())
                    .put("event_id",envelope.path("event_id").asText()).put("broker_timestamp",Instant.ofEpochMilli(receipt.timestamp()).toString())
                    .put("acknowledged_at",Instant.now().toString()).put("envelope_sha256",store.hash(envelope)).put("acks","all");
            store.published(id,evidence);
        }catch(Exception e){store.fail(id,"publication",code(e));}
    }

    void process(String id){
        String current="snapshot";
        try{
            if(!store.done(id,"snapshot")){
                ObjectNode run=store.get(id);ObjectNode body=mapper.createObjectNode().put("policy_id",run.path("policy_id").asText())
                        .put("event_id",run.path("event_id").asText()).put("correlation_id",id).put("as_of",run.path("source").path("as_of").asText());
                body.set("history",run.path("source").path("history"));
                stage(id,"snapshot",()->{
                    JsonNode result=runtime.runtime("/v1/demo/project",body);
                    if(!result.path("snapshot").path("policy_id").asText().equals(body.path("policy_id").asText())||result.path("snapshot").path("snapshot_id").asText().isBlank())throw new IllegalStateException("SNAPSHOT_IDENTITY_MISMATCH");
                    return result;
                },"projection");
            }
            current="score";
            if(!store.done(id,"score"))stage(id,"score",()->{
                ObjectNode run=store.get(id);JsonNode projection=run.path("artifacts").path("projection");
                ObjectNode body=mapper.createObjectNode().put("policy_id",run.path("policy_id").asText()).put("observation_id",id)
                        .put("as_of_date",projection.path("snapshot").path("as_of").asText()).put("feature_stage","raw-v6-features")
                        .put("preprocessing_profile_id","v6-coefficient-transform-then-bundle-zscore/1.0.0");
                body.set("features",projection.path("features"));JsonNode result=runtime.score(body);
                if(!result.path("catalog_sha256").asText().equals(projection.path("snapshot").path("catalog_file_sha256").asText()))throw new IllegalStateException("MODEL_SNAPSHOT_CATALOG_MISMATCH");
                return result;
            },"score");
            current="rules";
            if(!store.done(id,"rules"))stage(id,"rules",()->{
                ObjectNode run=store.get(id);JsonNode context=run.path("artifacts").path("projection").path("context");
                PolicyContext policy=new PolicyContext(run.path("policy_id").asText(),Instant.parse(run.path("source").path("as_of").asText()),
                        context.path("status").asText("unknown"),context.path("tenure_days").asInt(),context.path("in_grace_period").asBoolean(false),nullableInt(context,"days_past_due"),
                        nullableBool(context,"has_active_claim"),nullableBool(context,"has_legal_hold"),nullableBool(context,"has_registered_dispute"),nullableBool(context,"sms_opt_out"),nullableBool(context,"email_opt_out"),nullableBool(context,"phone_opt_out"),nullableBool(context,"dnc_registered"),
                        context.path("last_contact_date").isTextual()?Instant.parse(context.path("last_contact_date").asText()):null);
                ObjectNode result=mapper.createObjectNode().put("rules_version","java-eligibility/1.0.0").put("authorized_to_act",false)
                        .put("snapshot_id",run.path("artifacts").path("snapshot").path("snapshot_id").asText());
                result.set("results",mapper.valueToTree(rules.evaluate(policy)));result.set("context",context);return result;
            },"rules");
            current="allocation";
            if(!store.done(id,"allocation"))stage(id,"allocation",()->allocate(store.get(id)),"allocation");
            current="case";
            if(!store.done(id,"case"))stage(id,"case",()->{
                ObjectNode run=store.get(id);JsonNode artifacts=run.path("artifacts");
                ObjectNode record=mapper.createObjectNode().put("case_id",run.path("case_id").asText()).put("case_version",0).put("state","AWAITING_REVIEW")
                        .put("correlation_id",id).put("policy_id",run.path("policy_id").asText()).put("event_id",run.path("event_id").asText())
                        .put("snapshot_id",artifacts.path("snapshot").path("snapshot_id").asText()).put("bundle_digest",artifacts.path("score").path("bundle_digest").asText())
                        .put("recommended_action",artifacts.path("allocation").path("selected_action").asText()).put("authorized_to_act",false)
                        .put("external_execution_enabled",false).put("persisted_at",Instant.now().toString());
                record.put("snapshot_digest",store.hash(artifacts.path("snapshot"))).put("score_digest",store.hash(artifacts.path("score")))
                        .put("rules_digest",store.hash(artifacts.path("rules"))).put("allocation_digest",store.hash(artifacts.path("allocation")));return record;
            },"case");
            current="agent";
            if(!store.done(id,"agent"))stage(id,"agent",()->{
                ObjectNode run=store.get(id);JsonNode artifacts=run.path("artifacts");ObjectNode body=mapper.createObjectNode()
                        .put("case_id",run.path("case_id").asText()).put("case_version",run.path("case_version").asLong()).put("event_id",run.path("event_id").asText());
                body.set("snapshot",artifacts.path("snapshot"));body.set("score",artifacts.path("score"));body.set("rules",artifacts.path("rules").path("results"));body.set("allocation",artifacts.path("allocation"));
                JsonNode draft=runtime.runtime("/v1/demo/draft",body);
                if(!draft.path("case_id").asText().equals(body.path("case_id").asText()) || !draft.path("snapshot_id").asText().equals(artifacts.path("snapshot").path("snapshot_id").asText())
                        || !draft.has("authorized_to_act") || draft.path("authorized_to_act").asBoolean(true)
                        || !draft.path("human_review_required").asBoolean(false)
                        || draft.path("case_version").asLong(-1)!=body.path("case_version").asLong()
                        || !"inforsight-bounded-agent/1.0.0".equals(draft.path("workflow_id").asText())
                        || !Set.of("DRAFT_FOR_REVIEW","ABSTAIN").contains(draft.path("status").asText())) throw new IllegalStateException("AGENT_BINDING_OR_AUTHORITY_MISMATCH");
                String action=draft.path("action_id").asText();if(draft.path("status").asText().equals("DRAFT_FOR_REVIEW")&&!action.equals(artifacts.path("allocation").path("selected_action").asText()))throw new IllegalStateException("AGENT_ACTION_NOT_ALLOCATED");
                if(draft.path("status").asText().equals("DRAFT_FOR_REVIEW") &&
                        (draft.path("procedure_citations").size()!=1 || !"fictional-local-review@1.0.0".equals(draft.path("procedure_citations").get(0).asText())))throw new IllegalStateException("UNTRUSTED_AGENT_PROCEDURE_CITATION");
                Set<String> visible=new HashSet<>();artifacts.path("projection").path("source_event_ids").forEach(v->visible.add(v.asText()));
                for(JsonNode source:draft.path("evidence_source_ids"))if(!visible.contains(source.asText()))throw new IllegalStateException("AGENT_EVIDENCE_OUTSIDE_SNAPSHOT");
                return draft;
            },"agent");
        }catch(Exception failure){store.fail(id,current,code(failure));}
    }
    private JsonNode allocate(ObjectNode run){
        JsonNode artifacts=run.path("artifacts");ObjectNode body=mapper.createObjectNode();body.set("snapshot",artifacts.path("snapshot"));body.set("score",artifacts.path("score"));body.set("rules",artifacts.path("rules").path("results"));
        JsonNode valuation=runtime.runtime("/v1/demo/value",body);List<PortfolioAllocator.Candidate> candidates=new ArrayList<>();
        Set<String> eligible=new HashSet<>();for(JsonNode rule:artifacts.path("rules").path("results"))if(rule.path("eligible").asBoolean())eligible.add(rule.path("action_type").asText());
        for(JsonNode c:valuation.path("candidates")){
            if(!c.path("policy_id").asText().equals(run.path("policy_id").asText()))throw new IllegalStateException("VALUATION_POLICY_MISMATCH");
            candidates.add(new PortfolioAllocator.Candidate(c.path("policy_id").asText(),c.path("action_type").asText(),c.path("cost_micros").asLong(),c.path("personnel_seconds").asInt(),c.path("net_utility_micros").asLong(),eligible.contains(c.path("action_type").asText())&&c.path("eligible").asBoolean()));
        }
        long budget=30_000_000L;int seconds=1800;var allocated=allocator.allocate(candidates,budget,seconds);
        ObjectNode result=mapper.valueToTree(allocated);result.put("budget_micros",budget).put("personnel_seconds",seconds)
                .put("selected_action",allocated.selected().isEmpty()?"abstain":allocated.selected().getFirst().actionType())
                .put("allocator_version","java-multiple-choice-knapsack/1.1.0").put("authorized_to_act",false)
                .put("scope","One fictional policy; at most one action; fixed demo resource budget");
        result.set("valuation",valuation);return result;
    }
    private void stage(String id,String name,Supplier<JsonNode> operation,String artifact){
        store.start(id,name);JsonNode evidence=operation.get();String status=name.equals("agent")&&evidence.path("status").asText().equals("ABSTAIN")?"abstained":"completed";
        store.finish(id,name,evidence,artifact,status);
    }
    private static Boolean nullableBool(JsonNode context,String name){return context.path(name).isBoolean()?context.path(name).asBoolean():null;}
    private static Integer nullableInt(JsonNode context,String name){return context.path(name).isInt()?context.path(name).asInt():null;}
    private static String code(Exception failure){String code=failure.getMessage();return code!=null&&code.matches("[A-Z0-9_]{3,100}")?code:"COMPONENT_UNAVAILABLE";}
}
