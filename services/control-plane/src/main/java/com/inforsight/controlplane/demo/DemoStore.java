package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.inforsight.controlplane.audit.AuditHash;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Duration;
import java.time.Instant;
import java.sql.Timestamp;
import java.util.*;
import java.util.function.Consumer;

/** Durable, isolated demo artifacts and an append-only per-run evidence journal. */
@Repository
@Profile("persistence")
@ConditionalOnProperty(name = "inforsight.journey.enabled", havingValue = "true")
public class DemoStore {
    public static final List<String> STAGES = List.of("submission", "publication", "ingestion", "snapshot", "score", "rules", "allocation", "case", "agent", "decision", "audit");
    private static final String GENESIS = "0".repeat(64);
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;
    private final TransactionTemplate tx;

    public DemoStore(JdbcTemplate jdbc, ObjectMapper mapper, PlatformTransactionManager manager) {
        this.jdbc = jdbc; this.mapper = mapper; this.tx = new TransactionTemplate(manager);
    }

    public Optional<ObjectNode> byKey(String key, String digest) {
        var rows = jdbc.query("SELECT request_digest,document::text FROM demo_run WHERE idempotency_key=?",
                (rs, row) -> Map.entry(rs.getString(1), object(rs.getString(2))), key);
        if (rows.isEmpty()) return Optional.empty();
        if (!rows.getFirst().getKey().equals(digest)) throw new IllegalStateException("idempotency key request mismatch");
        return Optional.of(rows.getFirst().getValue());
    }

    public ObjectNode create(String correlation, String event, String policy, String scenario, String key,
                             String digest, JsonNode source) {
        return tx.execute(status -> {
            // Serialize create/replay on the idempotency identity, including concurrent HTTP retries.
            jdbc.queryForObject("SELECT pg_advisory_xact_lock(hashtext(?))", Object.class, "demo-submit:" + key);
            var replay = byKey(key, digest);
            if (replay.isPresent()) return replay.get();
            Instant now = Instant.now();
            ObjectNode run = mapper.createObjectNode();
            run.put("correlation_id", correlation).put("event_id", event).put("policy_id", policy)
                    .put("scenario_id", scenario).put("status", "WAITING").put("case_id", "case_" + uuid())
                    .put("case_version", 0).put("created_at", now.toString()).put("updated_at", now.toString())
                    .put("fictional", true).put("environment", "local").put("external_execution_enabled", false);
            run.set("source", source); run.set("artifacts", mapper.createObjectNode());
            var stages = run.putArray("stages");
            for (String name : STAGES) stages.addObject().put("stage", name).put("status", "waiting")
                    .put("producer", producer(name)).put("attempt", 0).putNull("started_at").putNull("completed_at")
                    .putNull("duration_ms").set("input_refs", mapper.createArrayNode());
            for (JsonNode item : stages) { ((ObjectNode)item).set("output_refs", mapper.createArrayNode()); ((ObjectNode)item).set("evidence", mapper.createObjectNode()); }
            jdbc.update("INSERT INTO demo_run(correlation_id,event_id,idempotency_key,request_digest,status,document) VALUES(?,?,?,?,?,CAST(? AS jsonb))",
                    correlation,event,key,digest,"WAITING",encode(run));
            ObjectNode envelope = mapper.createObjectNode();
            envelope.put("schema_version","inforsight.demo.event/1.0.0").put("event_id",event).put("policy_id",policy)
                    .put("correlation_id",correlation).put("event_type","fictional.policy_event_submitted")
                    .put("idempotency_key",key).put("submitted_at",now.toString()).put("fictional",true);
            envelope.set("payload",source);
            jdbc.update("INSERT INTO demo_outbox(event_id,correlation_id,envelope) VALUES(?,?,CAST(? AS jsonb))", event,correlation,encode(envelope));
            finishInRun(run,"submission",source,null,"completed",now);
            write(run);
            return run;
        });
    }

    public ObjectNode get(String id) {
        return jdbc.query("SELECT document::text FROM demo_run WHERE correlation_id=?", (rs,row)->object(rs.getString(1)),id)
                .stream().findFirst().orElseThrow(()->new NoSuchElementException("fictional run not found"));
    }

    public List<ObjectNode> pending() {
        return jdbc.query("SELECT o.envelope::text FROM demo_outbox o JOIN demo_run r USING(correlation_id) WHERE o.published_at IS NULL AND o.attempts<3 AND r.status<>'FAILED' ORDER BY r.created_at LIMIT 10",
                (rs,row)->object(rs.getString(1)));
    }

    public void publishing(String id) {
        mutate(id, run -> {
            jdbc.update("UPDATE demo_outbox SET attempts=attempts+1 WHERE correlation_id=?",id);
            startInRun(run,"publication");
        });
    }

    public void published(String id, JsonNode evidence) {
        mutate(id,run->{
            jdbc.update("UPDATE demo_outbox SET published_at=now(),last_error=NULL WHERE correlation_id=?",id);
            finishInRun(run,"publication",evidence,null,"completed",Instant.now());
        });
    }

    public void ingest(JsonNode envelope, String topic, int partition, long offset) {
        ingest(envelope,topic,partition,offset,-1);
    }
    public void ingest(JsonNode envelope, String topic, int partition, long offset,long brokerTimestamp) {
        String id=envelope.path("correlation_id").asText();
        mutate(id,run->{
            String stored=jdbc.queryForObject("SELECT envelope::text FROM demo_outbox WHERE correlation_id=?",String.class,id);
            if (!object(stored).equals(envelope) || !run.path("event_id").asText().equals(envelope.path("event_id").asText()))
                throw new IllegalArgumentException("Kafka envelope does not match persisted fictional submission");
            if(!stage(run,"publication").path("status").asText().equals("completed")) {
                // The broker may accept a publish immediately before its producer
                // acknowledgement transaction fails. Delivery is real evidence;
                // label the recovery accurately instead of inventing that ack.
                startInRun(run,"publication");
                ObjectNode delivered=mapper.createObjectNode().put("event_id",run.path("event_id").asText())
                        .put("topic",topic).put("partition",partition).put("offset",offset)
                        .put("envelope_sha256",hash(envelope)).put("confirmed_by_delivery_at",Instant.now().toString())
                        .put("recovery","BROKER_DELIVERY_CONFIRMED_AFTER_ACK_RECORD_INTERRUPTION")
                        .put("publisher_ack_record_available",false);
                if(brokerTimestamp>=0)delivered.put("broker_timestamp",Instant.ofEpochMilli(brokerTimestamp).toString());
                jdbc.update("UPDATE demo_outbox SET published_at=now(),last_error=NULL WHERE correlation_id=?",id);
                finishInRun(run,"publication",delivered,null,"completed",Instant.now());
                for(JsonNode item:run.path("stages"))if(item.path("status").asText().equals("blocked"))((ObjectNode)item).put("status","waiting");
            }
            int inserted=jdbc.update("INSERT INTO demo_inbox(event_id,correlation_id,topic,partition_id,record_offset) VALUES(?,?,?,?,?) ON CONFLICT(event_id) DO NOTHING",
                    run.path("event_id").asText(),id,topic,partition,offset);
            if (inserted==0) return;
            startInRun(run,"ingestion");
            ObjectNode evidence=mapper.createObjectNode().put("event_id",run.path("event_id").asText()).put("topic",topic)
                    .put("partition",partition).put("offset",offset).put("consumer_group","inforsight-demo-journey-v1")
                    .put("envelope_sha256",hash(envelope)).put("received_at",Instant.now().toString());
            finishInRun(run,"ingestion",evidence,null,"completed",Instant.now());
            run.put("status","PROCESSING");
        });
    }
    public void quarantine(String topic,int partition,long offset,String raw,String code){
        jdbc.update("INSERT INTO demo_ingress_quarantine(topic,partition_id,record_offset,payload_sha256,error_code) VALUES(?,?,?,?,?) ON CONFLICT DO NOTHING",
                topic,partition,offset,AuditHash.sha256(raw==null?"":raw),code);
    }

    public List<String> resumable() {
        return jdbc.query("SELECT r.correlation_id FROM demo_run r JOIN demo_inbox i USING(correlation_id) WHERE r.status='PROCESSING' ORDER BY r.created_at LIMIT 10",
                (rs,row)->rs.getString(1));
    }

    public boolean done(String id,String name) {
        String state=stage(get(id),name).path("status").asText();
        return state.equals("completed")||state.equals("abstained");
    }
    public void start(String id,String name) { mutate(id,run->startInRun(run,name)); }
    public void finish(String id,String name,JsonNode evidence,String artifact,String status) {
        mutate(id,run->{
            if (name.equals("case")) jdbc.update("INSERT INTO demo_case(case_id,correlation_id,state,evidence) VALUES(?,?,?,CAST(? AS jsonb)) ON CONFLICT(correlation_id) DO NOTHING",
                    run.path("case_id").asText(),id,"AWAITING_REVIEW",encode(evidence));
            finishInRun(run,name,evidence,artifact,status,Instant.now());
            if(name.equals("snapshot")) ((ObjectNode)run.path("artifacts")).set("snapshot",evidence.path("snapshot").deepCopy());
            if (name.equals("agent")) run.put("status","AWAITING_REVIEW");
        });
    }

    public void fail(String id,String name,String code) {
        mutate(id,run->{
            ObjectNode step=stage(run,name); step.put("status","failed").put("completed_at",Instant.now().toString());
            step.set("error",mapper.createObjectNode().put("code",code).put("retryable",true)
                    .put("message","This component did not produce a verified output. Retry preserves the submitted evidence."));
            duration(step); run.put("status","FAILED");
            journal(run,name,"failed",step);
            for (int index=STAGES.indexOf(name)+1;index<STAGES.size();index++) {
                ObjectNode later=stage(run,STAGES.get(index));
                if (later.path("status").asText().equals("waiting")) later.put("status","blocked");
            }
        });
    }

    public ObjectNode retry(String id) {
        return mutate(id,run->{
            if (!run.path("status").asText().equals("FAILED")) throw new IllegalStateException("only a failed run can be retried");
            for (JsonNode s:run.path("stages")) if (Set.of("failed","blocked").contains(s.path("status").asText())) {
                ((ObjectNode)s).put("status","waiting"); ((ObjectNode)s).remove("error");
            }
            jdbc.update("UPDATE demo_outbox SET attempts=0,last_error=NULL WHERE correlation_id=? AND published_at IS NULL",id);
            Integer accepted=jdbc.queryForObject("SELECT count(*) FROM demo_inbox WHERE correlation_id=?",Integer.class,id);
            run.put("status",accepted!=null&&accepted>0?"PROCESSING":"WAITING");
            journal(run,"submission","retry_requested",mapper.createObjectNode().put("requested_at",Instant.now().toString()));
        });
    }

    /** Abandoned review expiry is an actual persisted transition, never a human decision. */
    public void expireReview(String id) {
        mutate(id,run->{
            if(!run.path("status").asText().equals("AWAITING_REVIEW"))throw new IllegalStateException("only abandoned review may expire");
            run.put("status","EXPIRED").put("expired_at",Instant.now().toString());
            for(String name:List.of("decision","audit")){
                ObjectNode step=stage(run,name);step.put("status","blocked").put("producer","Java demo retention worker");
                step.set("error",mapper.createObjectNode().put("code","RUN_EXPIRED").put("retryable",false)
                        .put("message","The abandoned fictional review expired without a human decision. Completed evidence remains intact until retention cleanup."));
                journal(run,name,"blocked",step,"Java demo retention worker");
            }
        });
    }

    public ObjectNode decide(String id,JsonNode request) {
        String key=required(request,"idempotency_key",128); String digest=hash(request);
        return tx.execute(status->{
            ObjectNode run=locked(id);
            var prior=jdbc.query("SELECT request_digest,response::text FROM demo_decision WHERE correlation_id=? AND idempotency_key=?",
                    (rs,row)->Map.entry(rs.getString(1),object(rs.getString(2))),id,key);
            if(!prior.isEmpty()) { if(!prior.getFirst().getKey().equals(digest)) throw new IllegalStateException("idempotency key request mismatch"); return prior.getFirst().getValue(); }
            if(!run.path("status").asText().equals("AWAITING_REVIEW")) throw new IllegalStateException("case is not ready for human review");
            if(!request.has("expected_case_version") || request.path("expected_case_version").asLong(-1)!=run.path("case_version").asLong()) throw new IllegalStateException("case version conflict");
            if(!verify(id).path("valid").asBoolean())throw new IllegalStateException("audit integrity verification failed before review");
            String decision=required(request,"decision",40); required(request,"reviewer_id",128);
            required(request,"rationale",500); if(request.path("notes").asText().length()>2000) throw new IllegalArgumentException("notes exceeds 2000 characters");
            if(!Set.of("APPROVED","REJECTED","REQUEST_MORE_INFORMATION").contains(decision)) throw new IllegalArgumentException("unsupported fictional decision");
            var artifacts=(ObjectNode)run.path("artifacts"); String action=artifacts.path("allocation").path("selected_action").asText("abstain");
            JsonNode draft=artifacts.path("agent");
            if(decision.equals("APPROVED") && (action.equals("abstain") || !draft.path("status").asText().equals("DRAFT_FOR_REVIEW") || !action.equals(draft.path("action_id").asText())))
                throw new IllegalArgumentException("approval requires an eligible allocated agent draft; abstention cannot authorize action");
            startInRun(run,"decision");
            long version=run.path("case_version").asLong()+1; String state=decisionState(decision);
            ObjectNode evidence=request.deepCopy(); evidence.put("committed_at",Instant.now().toString()).put("case_version",version)
                    .put("case_id",run.path("case_id").asText()).put("selected_action",action).put("human_authority",true)
                    .put("authorized_to_act",false).put("external_execution_enabled",false);
            run.put("case_version",version);
            ObjectNode caseRecord=(ObjectNode)artifacts.path("case"); caseRecord.put("case_version",version).put("state",state);caseRecord.set("human_decision",evidence);
            jdbc.update("UPDATE demo_case SET version=?,state=?,evidence=CAST(? AS jsonb),updated_at=now() WHERE correlation_id=?",version,state,encode(caseRecord),id);
            finishInRun(run,"decision",evidence,"decision","completed",Instant.now());
            startInRun(run,"audit");
            write(run); // same transaction: bind the verifier to this pending persisted decision.
            ObjectNode check=verify(id);
            if(!check.path("valid").asBoolean()) throw new IllegalStateException("audit integrity verification failed");
            check.remove("entries");
            finishInRun(run,"audit",check,null,"completed",Instant.now());
            run.put("status","COMPLETED"); write(run);
            jdbc.update("INSERT INTO demo_decision(correlation_id,idempotency_key,request_digest,response) VALUES(?,?,?,CAST(? AS jsonb))",id,key,digest,encode(run));
            return run;
        });
    }

    public ObjectNode verify(String id) {
        // All journey writers acquire this same row lock. Keep it until the
        // document, journal, checkpoint and case have been read so a legitimate
        // stage commit cannot be mistaken for a corrupted audit projection.
        return tx.execute(status -> verifyLocked(id));
    }

    private ObjectNode verifyLocked(String id) {
        ObjectNode run=locked(id);
        var rows=jdbc.query("SELECT sequence,event_id,stage,event_type,occurred_at,producer,canonical_payload,parent_hash,current_hash FROM demo_journal WHERE correlation_id=? ORDER BY sequence",
                (rs,row)->{
                    ObjectNode entry=mapper.createObjectNode().put("sequence",rs.getLong(1)).put("event_id",rs.getString(2))
                            .put("stage",rs.getString(3)).put("event_type",rs.getString(4)).put("occurred_at",rs.getTimestamp(5).toInstant().toString())
                            .put("producer",rs.getString(6)).put("canonical_payload",rs.getString(7)).put("parent_hash",rs.getString(8)).put("current_hash",rs.getString(9));
                    entry.set("payload",object(rs.getString(7)));return entry;
                },id);
        var checkpoint=jdbc.query("SELECT sequence,head_hash FROM demo_checkpoint WHERE correlation_id=?",(rs,row)->Map.entry(rs.getLong(1),rs.getString(2)),id);
        var verification=new DemoJournalVerifier().verify(rows,checkpoint.isEmpty()?0:checkpoint.getFirst().getKey(),checkpoint.isEmpty()?GENESIS:checkpoint.getFirst().getValue());
        String error=verification.failureCode();String head=verification.headHash();
        for(ObjectNode entry:rows){
            JsonNode payload=entry.path("payload");
            if(!entry.path("event_id").asText().equals(payload.path("journal_event_id").asText())
                    ||!entry.path("stage").asText().equals(payload.path("stage").asText())
                    ||!entry.path("event_type").asText().equals(payload.path("stage").asText()+"."+payload.path("status").asText())
                    ||!entry.path("producer").asText().equals(payload.path("producer").asText())
                    ||!id.equals(payload.path("correlation_id").asText())
                    ||!run.path("event_id").asText().equals(payload.path("source_event_id").asText()))error="JOURNAL_METADATA_MISMATCH";
            try{
                // PostgreSQL timestamps preserve microseconds, while Java may record nanoseconds.
                if(Math.abs(Duration.between(Instant.parse(entry.path("occurred_at").asText()),Instant.parse(payload.path("occurred_at").asText())).toNanos())>500)error="JOURNAL_TIMESTAMP_MISMATCH";
            }catch(RuntimeException invalid){error="JOURNAL_TIMESTAMP_MISMATCH";}
        }
        // A valid chain alone is insufficient if the screen's artifact has been
        // changed separately. Bind each completed displayed stage to its journal.
        Map<String,JsonNode> committed=new HashMap<>();
        Map<String,JsonNode> latest=new HashMap<>();
        for(ObjectNode entry:rows){
            JsonNode payload=entry.path("payload");String name=payload.path("stage").asText();
            // retry_requested is a run command rather than a stage transition.
            if(!payload.path("status").asText().equals("retry_requested"))latest.put(name,payload);
            if(Set.of("completed","abstained").contains(payload.path("status").asText()))committed.put(name,payload.path("evidence"));
        }
        Map<String,JsonNode> displayed=new HashMap<>();
        for(JsonNode step:run.path("stages")){
            String name=step.path("stage").asText();
            if(!step.isObject()||!STAGES.contains(name)||displayed.put(name,step)!=null)error="DISPLAYED_STAGE_SCHEMA_MISMATCH";
            if(Set.of("completed","abstained").contains(step.path("status").asText()) && !step.equals(committed.get(name)))error="DISPLAYED_STAGE_EVIDENCE_MISMATCH";
        }
        if(!run.path("stages").isArray()||displayed.size()!=STAGES.size())error="DISPLAYED_STAGE_SCHEMA_MISMATCH";
        // Check from the immutable journal back to the mutable projection too:
        // deleting or downgrading a completed stage must never pass verification.
        for(var entry:latest.entrySet())if(Set.of("completed","abstained").contains(entry.getValue().path("status").asText())
                && !entry.getValue().path("evidence").equals(displayed.get(entry.getKey())))error="DISPLAYED_STAGE_EVIDENCE_MISMATCH";
        JsonNode artifacts=run.path("artifacts");
        for(String name:List.of("score","rules","allocation","agent","decision"))
            if((committed.containsKey(name)||artifacts.has(name)) && (!artifacts.has(name)||!committed.containsKey(name)
                    ||!artifacts.path(name).equals(committed.get(name).path("evidence"))))error="ARTIFACT_EVIDENCE_MISMATCH";
        if((committed.containsKey("snapshot")||artifacts.has("snapshot")) && (!artifacts.has("snapshot")||!committed.containsKey("snapshot")
                ||!artifacts.path("snapshot").equals(committed.get("snapshot").path("evidence").path("snapshot"))))error="SNAPSHOT_EVIDENCE_MISMATCH";
        if((committed.containsKey("snapshot")||artifacts.has("projection")) && (!artifacts.has("projection")||!committed.containsKey("snapshot")
                ||!artifacts.path("projection").equals(committed.get("snapshot").path("evidence"))))error="PROJECTION_EVIDENCE_MISMATCH";
        if(committed.containsKey("case")&&!artifacts.path("case").isObject())error="PERSISTED_CASE_EVIDENCE_MISMATCH";
        if(artifacts.has("case")&&!committed.containsKey("case"))error="CASE_VERSION_PROVENANCE_MISMATCH";
        if(artifacts.path("case").isObject()&&committed.containsKey("case")){
            var stored=jdbc.query("SELECT evidence::text FROM demo_case WHERE correlation_id=?",(rs,row)->object(rs.getString(1)),id);
            if(stored.isEmpty()||!stored.getFirst().equals(artifacts.path("case")))error="PERSISTED_CASE_EVIDENCE_MISMATCH";
            ObjectNode expected=committed.get("case").path("evidence").deepCopy();
            if(artifacts.has("decision")){
                JsonNode decision=artifacts.path("decision");expected.put("case_version",decision.path("case_version").asLong()).put("state",decisionState(decision.path("decision").asText()));
                expected.set("human_decision",decision);
            }
            if(!hash(expected).equals(hash(artifacts.path("case"))) || run.path("case_version").asLong()!=expected.path("case_version").asLong()
                    ||!run.path("case_id").asText().equals(expected.path("case_id").asText()))error="CASE_VERSION_PROVENANCE_MISMATCH";
        }
        ObjectNode result=mapper.createObjectNode().put("valid",error==null&&!rows.isEmpty()).put("verified_entries",error==null?rows.size():0)
                .put("head_hash",head).put("scope","local demo run SHA-256 chain and persisted checkpoint")
                .put("externally_anchored",false).put("verified_at",Instant.now().toString());
        if(error!=null)result.put("failure_code",error);
        result.set("entries",mapper.valueToTree(rows)); return result;
    }

    private ObjectNode mutate(String id,Consumer<ObjectNode> action) { return tx.execute(s->{ObjectNode run=locked(id);action.accept(run);write(run);return run;}); }
    private ObjectNode locked(String id) {return jdbc.query("SELECT document::text FROM demo_run WHERE correlation_id=? FOR UPDATE",(rs,row)->object(rs.getString(1)),id).stream().findFirst().orElseThrow(()->new NoSuchElementException("fictional run not found"));}
    private void write(ObjectNode run) {run.put("updated_at",Instant.now().toString());jdbc.update("UPDATE demo_run SET status=?,document=CAST(? AS jsonb),updated_at=now() WHERE correlation_id=?",run.path("status").asText(),encode(run),run.path("correlation_id").asText());}
    private void startInRun(ObjectNode run,String name) {ObjectNode step=stage(run,name);step.put("status","processing").put("attempt",step.path("attempt").asInt()+1).put("started_at",Instant.now().toString()).putNull("completed_at").putNull("duration_ms");step.remove("error");journal(run,name,"processing",step);}
    private void finishInRun(ObjectNode run,String name,JsonNode evidence,String artifact,String status,Instant now) {
        ObjectNode step=stage(run,name); if(step.path("started_at").isNull()) {step.put("started_at",now.toString()).put("attempt",1);}
        step.remove("error");
        step.put("status",status).put("completed_at",now.toString());duration(step);step.set("evidence",evidence.deepCopy());
        String id=run.path("correlation_id").asText();
        var inputs=step.putArray("input_refs");int index=STAGES.indexOf(name);if(index>0)inputs.add("run:"+id+"/"+STAGES.get(index-1));
        step.putArray("output_refs").add("sha256:"+hash(evidence));
        if(artifact!=null)((ObjectNode)run.path("artifacts")).set(artifact,evidence.deepCopy());
        journal(run,name,status,step);
    }
    private void journal(ObjectNode run,String stage,String status,JsonNode evidence) {
        journal(run,stage,status,evidence,producer(stage));
    }
    private void journal(ObjectNode run,String stage,String status,JsonNode evidence,String producer) {
        String id=run.path("correlation_id").asText();
        var prior=jdbc.query("SELECT sequence,head_hash FROM demo_checkpoint WHERE correlation_id=?",(rs,row)->Map.entry(rs.getLong(1),rs.getString(2)),id);
        long sequence=prior.isEmpty()?1:prior.getFirst().getKey()+1;String parent=prior.isEmpty()?GENESIS:prior.getFirst().getValue();
        Instant now=Instant.now();String event="evt_"+uuid();
        ObjectNode payload=mapper.createObjectNode().put("correlation_id",id).put("source_event_id",run.path("event_id").asText())
                .put("journal_event_id",event).put("stage",stage).put("status",status).put("case_version",run.path("case_version").asLong())
                .put("occurred_at",now.toString()).put("producer",producer);payload.set("evidence",evidence.deepCopy());
        String canonical=encode(payload);String hash=AuditHash.sha256(parent+"\n"+canonical);
        jdbc.update("INSERT INTO demo_journal(correlation_id,sequence,event_id,stage,event_type,occurred_at,producer,canonical_payload,parent_hash,current_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
                id,sequence,event,stage,stage+"."+status,Timestamp.from(now),producer,canonical,parent,hash);
        jdbc.update("INSERT INTO demo_checkpoint(correlation_id,sequence,head_hash) VALUES(?,?,?) ON CONFLICT(correlation_id) DO UPDATE SET sequence=excluded.sequence,head_hash=excluded.head_hash",id,sequence,hash);
    }
    private static void duration(ObjectNode step) {if(step.path("started_at").isTextual()&&step.path("completed_at").isTextual())step.put("duration_ms",Math.max(0,Duration.between(Instant.parse(step.path("started_at").asText()),Instant.parse(step.path("completed_at").asText())).toMillis()));}
    public static ObjectNode stage(ObjectNode run,String name) {for(JsonNode step:run.path("stages"))if(name.equals(step.path("stage").asText()))return (ObjectNode)step;throw new IllegalArgumentException("unknown stage");}
    public static String producer(String stage) {return switch(stage) {case "publication"->"Kafka producer / Java control plane";case "ingestion"->"Kafka consumer / Java control plane";case "snapshot"->"Python evidence projection";case "score"->"Python released-model inference";case "agent"->"Python bounded agent workflow";case "decision"->"Human reviewer / Java control plane";case "audit"->"PostgreSQL / Java SHA-256 verifier";default->"Java control plane";};}
    public String hash(JsonNode value){return AuditHash.sha256(canonical(value));}
    private String canonical(JsonNode value){ if(value.isObject()){var sorted=mapper.createObjectNode();var names=new TreeSet<String>();value.fieldNames().forEachRemaining(names::add);for(String key:names)sorted.set(key,parse(canonical(value.get(key))));return encode(sorted);}if(value.isArray()){var array=mapper.createArrayNode();for(JsonNode item:value)array.add(parse(canonical(item)));return encode(array);}return encode(value);}
    public String encode(JsonNode value){try{return mapper.writeValueAsString(value);}catch(Exception e){throw new IllegalStateException("could not encode demo evidence",e);}}
    public JsonNode parse(String value){try{return mapper.readTree(value);}catch(Exception e){throw new IllegalStateException("could not decode demo evidence",e);}}
    private ObjectNode object(String value){return (ObjectNode)parse(value);}
    public static String uuid(){return UUID.randomUUID().toString().replace("-","");}
    private static String decisionState(String decision){return switch(decision){case "APPROVED"->"HUMAN_APPROVED";case "REJECTED"->"REJECTED";default->"MORE_INFORMATION_REQUESTED";};}
    public static String required(JsonNode request,String name,int max){JsonNode v=request.get(name);if(v==null||!v.isTextual()||v.asText().isBlank()||v.asText().length()>max)throw new IllegalArgumentException(name+" is required and must contain at most "+max+" characters");return v.asText();}
}
