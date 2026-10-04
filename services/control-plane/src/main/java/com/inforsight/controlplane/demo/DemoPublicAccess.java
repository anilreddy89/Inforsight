package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.*;
import java.util.function.Supplier;

/** Anonymous signed sessions, transactional resource bounds and whole-run retention.
 * Session credentials never enter fictional case evidence or Kafka envelopes. */
@Component
@Profile("persistence")
@ConditionalOnProperty(name="inforsight.journey.enabled",havingValue="true")
@EnableScheduling
public class DemoPublicAccess {
    public static final String REQUEST_SESSION=DemoPublicAccess.class.getName()+".session";
    public static final int SESSION_SECONDS=7*24*3600;
    private static final String CAPACITY_LOCK="inforsight-public-capacity";
    private final JdbcTemplate jdbc;
    private final DemoStore store;
    private final TransactionTemplate tx;
    private final boolean enabled,secure;
    private final byte[] secret;
    private final Limits limits;

    public record Session(String id,long expires,String token) {}
    public record Limits(int submissions,int globalSubmissions,int polls,int globalPolls,int retries,int globalRetries,
                         int decisions,int globalDecisions,int concurrent,int globalConcurrent,int retained,int globalRetained,int globalSessions) {
        static Limits from(Environment env){return new Limits(value(env,"SUBMISSIONS_PER_HOUR",12),value(env,"GLOBAL_SUBMISSIONS_PER_HOUR",120),
                value(env,"POLLS_PER_MINUTE",120),value(env,"GLOBAL_POLLS_PER_MINUTE",1200),value(env,"RETRIES_PER_HOUR",3),value(env,"GLOBAL_RETRIES_PER_HOUR",30),
                value(env,"DECISIONS_PER_HOUR",30),value(env,"GLOBAL_DECISIONS_PER_HOUR",180),value(env,"CONCURRENT_RUNS",2),value(env,"GLOBAL_CONCURRENT_RUNS",8),
                value(env,"RETAINED_RUNS",12),value(env,"GLOBAL_RETAINED_RUNS",200),value(env,"GLOBAL_SESSIONS_PER_HOUR",100));}
        private static int value(Environment env,String suffix,int fallback){int value=env.getProperty("INFORSIGHT_DEMO_"+suffix,Integer.class,fallback);if(value<1||value>1000000)throw new IllegalStateException("Invalid public demo limit: "+suffix);return value;}
    }
    public static class Rejection extends RuntimeException {
        public final int status,retryAfter;public final String code;
        Rejection(int status,String code,String message,int retryAfter){super(message);this.status=status;this.code=code;this.retryAfter=retryAfter;}
    }
    @Autowired
    public DemoPublicAccess(JdbcTemplate jdbc,DemoStore store,PlatformTransactionManager manager,Environment env){
        this(jdbc,store,manager,env.getProperty("INFORSIGHT_DEMO_PUBLIC_ENABLED",Boolean.class,false),
                env.getProperty("INFORSIGHT_DEMO_COOKIE_SECURE",Boolean.class,true),readSecret(env),Limits.from(env));
    }
    DemoPublicAccess(JdbcTemplate jdbc,DemoStore store,PlatformTransactionManager manager,boolean enabled,boolean secure,byte[] secret,Limits limits){
        this.jdbc=jdbc;this.store=store;this.tx=new TransactionTemplate(manager);this.enabled=enabled;this.secure=secure;this.secret=secret.clone();this.limits=limits;
        if(enabled&&secret.length<32)throw new IllegalStateException("Public demo requires a persistent session secret of at least 32 bytes");
    }
    private static byte[] readSecret(Environment env){
        if(!env.getProperty("INFORSIGHT_DEMO_PUBLIC_ENABLED",Boolean.class,false))return new byte[0];
        String filename=env.getProperty("INFORSIGHT_DEMO_SESSION_SECRET_FILE");
        if(filename==null||filename.isBlank())throw new IllegalStateException("INFORSIGHT_DEMO_SESSION_SECRET_FILE is required in public mode");
        try{return Files.readAllBytes(Path.of(filename));}catch(Exception failure){throw new IllegalStateException("Public demo session secret could not be read");}
    }
    public boolean enabled(){return enabled;}
    public boolean secure(){return secure;}
    public String cookieName(){return secure?"__Host-inforsight_session":"inforsight_session";}
    public Session issue(){
        return tx.execute(status->{
            quota("*","sessions",0,limits.globalSessions(),3600);
            String id=DemoStore.uuid();long expires=Instant.now().getEpochSecond()+SESSION_SECONDS;
            jdbc.update("INSERT INTO demo_session(session_id,expires_at) VALUES(?,?)",id,Timestamp.from(Instant.ofEpochSecond(expires)));
            return new Session(id,expires,sign(id,expires));
        });
    }
    public Session authenticate(String token){
        if(token==null||token.length()>256)return null;
        String[] parts=token.split("\\.",-1);if(parts.length!=3||!parts[0].matches("[a-f0-9]{32}"))return null;
        try{
            long expires=Long.parseLong(parts[1]);if(expires<=Instant.now().getEpochSecond()||!constant(token,sign(parts[0],expires)))return null;
            var found=jdbc.query("SELECT expires_at FROM demo_session WHERE session_id=? AND expires_at>now()",(rs,row)->rs.getTimestamp(1).toInstant().getEpochSecond(),parts[0]);
            if(found.isEmpty()||found.getFirst()!=expires)return null;
            jdbc.update("UPDATE demo_session SET last_seen_at=now() WHERE session_id=? AND last_seen_at<now()-interval '1 minute'",parts[0]);
            return new Session(parts[0],expires,token);
        }catch(NumberFormatException invalid){return null;}
    }
    private String sign(String id,long expires){String payload=id+"."+expires;return payload+"."+hmac("cookie:"+payload);}
    private String hmac(String value){
        try{Mac mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(secret,"HmacSHA256"));return Base64.getUrlEncoder().withoutPadding().encodeToString(mac.doFinal(value.getBytes(StandardCharsets.UTF_8)));}
        catch(Exception failure){throw new IllegalStateException("Session signature unavailable");}
    }
    public String csrf(Session session){return hmac("csrf:"+session.id());}
    public String tag(Session session){return hmac("tag:"+session.id()).substring(0,24);}
    public boolean validCsrf(Session session,String value){return value!=null&&value.length()<256&&constant(csrf(session),value);}
    private static boolean constant(String a,String b){return MessageDigest.isEqual(a.getBytes(StandardCharsets.UTF_8),b.getBytes(StandardCharsets.UTF_8));}
    public Map<String,Object> description(Session session){
        Map<String,Object> result=new LinkedHashMap<>();result.put("public_mode",enabled);result.put("environment",enabled?"public-preview":"local");
        result.put("csrf_token",enabled?csrf(session):null);result.put("session_tag",enabled?tag(session):"local");result.put("expires_at",enabled?Instant.ofEpochSecond(session.expires()).toString():null);
        result.put("limits",Map.of("submissions_per_hour",limits.submissions(),"polls_per_minute",limits.polls(),"retries_per_hour",limits.retries(),
                "concurrent_processing_runs",limits.concurrent(),"retained_runs",limits.retained(),"retention_hours",24,"abandoned_review_hours",48));return result;
    }
    public void request(Session session,String method,String path){
        if(!enabled)return;
        // Coarse durable request bounds also cover rejected mutations and unknown IDs.
        consume(session.id(),"requests",240,2400,60);
        if(method.equals("GET")||method.equals("HEAD"))consume(session.id(),"polls",limits.polls(),limits.globalPolls(),60);
        if(path.endsWith("/retry"))consume(session.id(),"retries",limits.retries(),limits.globalRetries(),3600);
        if(path.endsWith("/decision"))consume(session.id(),"decisions",limits.decisions(),limits.globalDecisions(),3600);
    }
    private void consume(String owner,String operation,int perSession,int global,int seconds){tx.executeWithoutResult(status->quota(owner,operation,perSession,global,seconds));}
    private void quota(String owner,String operation,int perSession,int global,int seconds){
        jdbc.queryForObject("SELECT pg_advisory_xact_lock(hashtext(?))",Object.class,"inforsight-public-quota");
        long now=Instant.now().getEpochSecond(),window=now/seconds*seconds;
        List<String> subjects=owner.equals("*")?List.of("*"):List.of("*",owner);
        for(String subject:subjects){
            int maximum=subject.equals("*")?global:perSession;
            Integer used=jdbc.queryForObject("SELECT COALESCE((SELECT used FROM demo_quota WHERE subject=? AND operation=? AND window_start=?),0)",Integer.class,subject,operation,window);
            if(used!=null&&used>=maximum)throw new Rejection(429,"RATE_LIMITED","The fictional demo request limit has been reached. Please wait before trying again.",(int)(window+seconds-now));
        }
        for(String subject:subjects)jdbc.update("INSERT INTO demo_quota(subject,operation,window_start,used) VALUES(?,?,?,1) ON CONFLICT(subject,operation,window_start) DO UPDATE SET used=demo_quota.used+1,updated_at=now()",subject,operation,window);
    }
    public void requireOwner(Session session,String id){
        var owners=jdbc.query("SELECT owner_session_id FROM demo_run WHERE correlation_id=?",(rs,row)->rs.getString(1),id);
        if(!owners.isEmpty()&&session.id().equals(owners.getFirst())){
            jdbc.update("UPDATE demo_run SET last_accessed_at=now() WHERE correlation_id=? AND last_accessed_at<now()-interval '1 minute'",id);return;
        }
        Integer expired=jdbc.queryForObject("SELECT count(*) FROM demo_retention_receipt WHERE correlation_id=? AND owner_session_id=?",Integer.class,id,session.id());
        if(expired!=null&&expired>0)throw new Rejection(410,"RUN_EXPIRED","This fictional run has passed its retention period. Its full evidence has been removed; start a new case.",0);
        throw new Rejection(404,"NOT_FOUND","This fictional run is not available in this visitor session.",0);
    }
    public ObjectNode submit(Session session,String key,String digest,Supplier<ObjectNode> create){
        if(!enabled)return create.get();
        return tx.execute(status->{
            capacityLock();String scoped=scopedKey(session,key);var prior=store.byKey(scoped,digest);if(prior.isPresent())return prior.get();
            capacity(session,true,"");quota(session.id(),"submissions",limits.submissions(),limits.globalSubmissions(),3600);
            ObjectNode run=create.get();String id=run.path("correlation_id").asText();
            jdbc.update("UPDATE demo_run SET owner_session_id=? WHERE correlation_id=?",session.id(),id);
            return run;
        });
    }
    public String scopedKey(Session session,String key){return enabled?"public:"+hmac("submission:"+session.id()+":"+key):key;}
    public ObjectNode retry(Session session,String id){
        if(!enabled)return store.retry(id);
        return tx.execute(status->{capacityLock();requireOwner(session,id);capacity(session,false,id);return store.retry(id);});
    }
    private void capacityLock(){jdbc.queryForObject("SELECT pg_advisory_xact_lock(hashtext(?))",Object.class,CAPACITY_LOCK);}
    private void capacity(Session session,boolean retained,String retryingId){
        // A failed send may already exist in Kafka even if its acknowledgement
        // was interrupted. Keep that reservation until real delivery/retry or
        // retention resolves it; delivery must not resurrect an uncounted run.
        // Retry replaces its own reservation instead of needing a second slot.
        long[] counts=jdbc.queryForObject("""
                SELECT count(*), count(*) FILTER (WHERE r.owner_session_id=?)
                FROM demo_run r WHERE r.owner_session_id IS NOT NULL AND r.correlation_id<>?
                  AND (r.status IN ('WAITING','PROCESSING') OR
                    (r.status='FAILED'
                     AND EXISTS (SELECT 1 FROM demo_outbox o WHERE o.correlation_id=r.correlation_id AND o.attempts>0)
                     AND NOT EXISTS (SELECT 1 FROM demo_inbox i WHERE i.correlation_id=r.correlation_id)))
                """,(rs,row)->new long[]{rs.getLong(1),rs.getLong(2)},session.id(),retryingId);
        if(counts[0]>=limits.globalConcurrent()||counts[1]>=limits.concurrent())throw new Rejection(503,"DEMO_CAPACITY",
                "The fictional demo has reached its limit for processing cases and events awaiting delivery. Retry an existing failed case or try again shortly.",30);
        if(retained){
            long count=jdbc.queryForObject("SELECT count(*) FROM demo_run WHERE owner_session_id IS NOT NULL",Long.class);
            long own=jdbc.queryForObject("SELECT count(*) FROM demo_run WHERE owner_session_id=?",Long.class,session.id());
            if(count>=limits.globalRetained()||own>=limits.retained())throw new Rejection(503,"DEMO_CAPACITY","The fictional demo has reached its retained-case limit. Existing cases remain available until their retention period ends.",3600);
        }
    }
    @Scheduled(fixedDelay=60000,initialDelay=60000)
    public void cleanup(){
        if(!enabled)return;
        tx.executeWithoutResult(status->{
            capacityLock();
            var abandoned=jdbc.query("SELECT correlation_id FROM demo_run WHERE owner_session_id IS NOT NULL AND status='AWAITING_REVIEW' AND created_at<now()-interval '48 hours' AND last_accessed_at<now()-interval '24 hours' FOR UPDATE SKIP LOCKED",(rs,row)->rs.getString(1));
            for(String id:abandoned)store.expireReview(id);
            var terminal=jdbc.query("SELECT correlation_id,owner_session_id FROM demo_run WHERE owner_session_id IS NOT NULL AND status IN ('COMPLETED','FAILED','EXPIRED') AND updated_at<now()-interval '24 hours' ORDER BY updated_at LIMIT 20 FOR UPDATE SKIP LOCKED",(rs,row)->Map.entry(rs.getString(1),rs.getString(2)));
            for(var entry:terminal){
                ObjectNode receipt=store.verify(entry.getKey());
                if(!receipt.path("valid").asBoolean()){
                    System.err.println("Demo retention preserved a run whose journal did not verify: "+entry.getKey());
                    continue;
                }
                jdbc.update("INSERT INTO demo_retention_receipt(correlation_id,owner_session_id,verified_entries,last_verified_head,verification_valid) VALUES(?,?,?,?,true)",entry.getKey(),entry.getValue(),receipt.path("verified_entries").asLong(),receipt.path("head_hash").asText());
                jdbc.queryForObject("SELECT set_config('inforsight.retention_cleanup',?,true)",String.class,entry.getKey());
                for(String table:List.of("demo_decision","demo_case","demo_checkpoint","demo_journal","demo_inbox","demo_outbox","demo_run"))jdbc.update("DELETE FROM "+table+" WHERE correlation_id=?",entry.getKey());
            }
            jdbc.update("DELETE FROM demo_quota WHERE updated_at<now()-interval '48 hours'");
            jdbc.update("DELETE FROM demo_retention_receipt WHERE deleted_at<now()-interval '7 days'");
            jdbc.update("DELETE FROM demo_session s WHERE s.expires_at<now() AND NOT EXISTS(SELECT 1 FROM demo_run r WHERE r.owner_session_id=s.session_id) AND NOT EXISTS(SELECT 1 FROM demo_retention_receipt t WHERE t.owner_session_id=s.session_id)");
            jdbc.update("DELETE FROM demo_ingress_quarantine WHERE rejected_at<now()-interval '7 days'");
        });
    }
}
