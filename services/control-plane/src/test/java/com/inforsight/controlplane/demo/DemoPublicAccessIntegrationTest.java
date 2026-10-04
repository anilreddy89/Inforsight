package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import jakarta.servlet.http.Cookie;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.testcontainers.containers.PostgreSQLContainer;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.*;

import static org.assertj.core.api.Assertions.*;

/** Real PostgreSQL for anonymous ownership, durable limits and retention.
 * The existing full acceptance suite proves the workflow; these fixtures test
 * access control without substituting fictional outputs into that acceptance. */
@EnabledIfEnvironmentVariable(named="INFORSIGHT_RUN_DEMO_INTEGRATION",matches="1")
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class DemoPublicAccessIntegrationTest {
    private final ObjectMapper mapper=new ObjectMapper();
    private final byte[] secret="a-test-only-secret-of-at-least-32-bytes".getBytes(StandardCharsets.UTF_8);
    private PostgreSQLContainer<?> postgres;private JdbcTemplate jdbc;private DataSourceTransactionManager manager;private DemoStore store;
    private static final DemoPublicAccess.Limits DEFAULT=new DemoPublicAccess.Limits(12,120,120,1200,3,30,30,180,2,8,12,200,100);
    @BeforeAll void start(){
        postgres=new PostgreSQLContainer<>("postgres:16-alpine");postgres.start();
        var ds=new DriverManagerDataSource(postgres.getJdbcUrl(),postgres.getUsername(),postgres.getPassword());
        Flyway.configure().dataSource(ds).locations("classpath:db/migration").load().migrate();
        jdbc=new JdbcTemplate(ds);manager=new DataSourceTransactionManager(ds);store=new DemoStore(jdbc,mapper,manager);
    }
    @AfterAll void stop(){if(postgres!=null)postgres.stop();}
    @BeforeEach void clear(){jdbc.execute("TRUNCATE demo_session,demo_run,demo_quota,demo_retention_receipt CASCADE");}
    private DemoPublicAccess access(){return access(DEFAULT);}
    private DemoPublicAccess access(DemoPublicAccess.Limits limits){return new DemoPublicAccess(jdbc,store,manager,true,true,secret,limits);}

    @Test void signedSessionsSurviveRestartButRejectTamperingAndExpiredDatabaseRows(){
        var access=access();var session=access.issue();
        assertThat(access.authenticate(session.token())).isEqualTo(session);
        assertThat(access().authenticate(session.token())).isEqualTo(session);
        assertThat(access.authenticate(session.token()+"x")).isNull();
        assertThat(access.authenticate(session.id()+".9999999999.invalid")).isNull();
        assertThat(access.validCsrf(session,access.csrf(session))).isTrue();
        assertThat(access.validCsrf(session,access.csrf(access.issue()))).isFalse();
        assertThat(access.tag(session)).isNotEqualTo(session.id());
        assertThat(access.scopedKey(session,"request-one")).doesNotContain(session.id());
        jdbc.update("UPDATE demo_session SET expires_at=now()-interval '1 second' WHERE session_id=?",session.id());
        assertThat(access.authenticate(session.token())).isNull();
        assertThatThrownBy(()->new DemoPublicAccess(jdbc,store,manager,true,true,new byte[0],DEFAULT)).isInstanceOf(IllegalStateException.class);
    }

    @Test void ownershipAndIdempotencyAreScopedToTheSignedVisitor(){
        var access=access();var first=access.issue();var second=access.issue();
        ObjectNode a=create(access,first,"same-browser-key"),replay=create(access,first,"same-browser-key");
        assertThat(replay.path("correlation_id")).isEqualTo(a.path("correlation_id"));
        ObjectNode b=create(access,second,"same-browser-key");
        assertThat(b.path("correlation_id")).isNotEqualTo(a.path("correlation_id"));
        access.requireOwner(first,a.path("correlation_id").asText());
        assertRejected(()->access.requireOwner(second,a.path("correlation_id").asText()),404,"NOT_FOUND");
        ObjectNode local=store.create("run_local","evt_local","pol_local","late-payment","local-key","local-digest",mapper.createObjectNode());
        assertRejected(()->access.requireOwner(first,local.path("correlation_id").asText()),404,"NOT_FOUND");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM demo_run WHERE owner_session_id IS NOT NULL",Integer.class)).isEqualTo(2);
        assertThatThrownBy(()->access.submit(first,"same-browser-key","different",()->{throw new AssertionError("must not create");})).isInstanceOf(IllegalStateException.class);
    }

    @Test void durablePerSessionGlobalAndMintQuotasSurviveNewServiceInstances(){
        var limits=new DemoPublicAccess.Limits(1,2,2,3,1,1,1,1,10,10,10,10,3);
        var access=access(limits);var first=access.issue();var second=access.issue();
        access.request(first,"HEAD","/api/v1/demo/runs/unknown");
        access(limits).request(first,"GET","/api/v1/demo/runs/unknown");
        assertRejected(()->access(limits).request(first,"GET","/api/v1/demo/runs/unknown"),429,"RATE_LIMITED");
        access.request(second,"GET","/api/v1/demo/scenarios");
        assertRejected(()->access.request(second,"GET","/api/v1/demo/scenarios"),429,"RATE_LIMITED");
        create(access,first,"one");create(access,first,"one"); // idempotent replay does not spend a submission
        assertRejected(()->create(access,first,"two"),429,"RATE_LIMITED");
        create(access,second,"two");var third=access.issue();
        assertRejected(()->create(access,third,"three"),429,"RATE_LIMITED");
        assertRejected(access::issue,429,"RATE_LIMITED");
        access.request(first,"POST","/api/v1/demo/runs/unknown/retry");
        assertRejected(()->access(limits).request(first,"POST","/api/v1/demo/runs/unknown/retry"),429,"RATE_LIMITED");
    }

    @Test void concurrentSubmissionsCannotRaceTheGlobalCapacityCheck()throws Exception {
        var limits=new DemoPublicAccess.Limits(12,120,120,1200,3,30,30,180,1,1,12,200,100);
        var access=access(limits);var a=access.issue();var b=access.issue();CountDownLatch ready=new CountDownLatch(2),go=new CountDownLatch(1);
        try(var executor=Executors.newFixedThreadPool(2)){
            var futures=List.of(executor.submit(()->competingCreate(access,a,ready,go)),executor.submit(()->competingCreate(access,b,ready,go)));
            assertThat(ready.await(5,TimeUnit.SECONDS)).isTrue();go.countDown();
            assertThat(List.of(futures.get(0).get(10,TimeUnit.SECONDS),futures.get(1).get(10,TimeUnit.SECONDS))).containsExactlyInAnyOrder(202,503);
            assertThat(jdbc.queryForObject("SELECT count(*) FROM demo_run",Integer.class)).isEqualTo(1);
        }
    }
    private int competingCreate(DemoPublicAccess access,DemoPublicAccess.Session owner,CountDownLatch ready,CountDownLatch go)throws Exception {
        ready.countDown();go.await();try{create(access,owner,"race");return 202;}catch(DemoPublicAccess.Rejection rejected){return rejected.status;}
    }

    @Test void retainedRunCapsAndRetryCapacityCannotBeBypassedByCompletedOrFailedCases(){
        var limits=new DemoPublicAccess.Limits(12,120,120,1200,3,30,30,180,1,2,2,3,100);
        var access=access(limits);var owner=access.issue();var other=access.issue();var third=access.issue();
        String first=create(access,owner,"first").path("correlation_id").asText();store.fail(first,"publication","TEST_FAILURE");
        String second=create(access,owner,"second").path("correlation_id").asText();store.fail(second,"publication","TEST_FAILURE");
        assertRejected(()->create(access,owner,"third"),503,"DEMO_CAPACITY");
        assertThat(create(access,owner,"first").path("correlation_id").asText()).isEqualTo(first);
        access.retry(owner,first);assertRejected(()->access.retry(owner,second),503,"DEMO_CAPACITY");
        store.fail(first,"publication","TEST_FAILURE");
        String finalSlot=create(access,other,"last-slot").path("correlation_id").asText();store.fail(finalSlot,"publication","TEST_FAILURE");
        assertRejected(()->create(access,third,"global-overflow"),503,"DEMO_CAPACITY");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM demo_run",Long.class)).isEqualTo(3);
    }

    @Test void interruptedPublicationKeepsItsCapacityReservationThroughRetryAndLateDelivery(){
        var limits=new DemoPublicAccess.Limits(12,120,120,1200,3,30,30,180,1,1,12,200,100);
        var access=access(limits);var owner=access.issue();var other=access.issue();
        String id=create(access,owner,"uncertain-publish").path("correlation_id").asText();
        ObjectNode envelope=store.pending().getFirst();
        assertRejected(()->create(access,owner,"while-waiting"),503,"DEMO_CAPACITY");
        store.publishing(id);store.fail(id,"publication","ACK_INTERRUPTED");
        assertRejected(()->create(access,owner,"owner-overflow"),503,"DEMO_CAPACITY");
        assertRejected(()->create(access,other,"global-overflow"),503,"DEMO_CAPACITY");
        assertThat(access.retry(owner,id).path("status").asText()).isEqualTo("WAITING");
        store.publishing(id);
        store.published(id,mapper.createObjectNode().put("offset",3));
        // A publication commit can succeed while its acknowledgement to the
        // caller is interrupted. That FAILED state still awaits durable ingest.
        store.fail(id,"publication","PUBLICATION_COMMIT_ACK_INTERRUPTED");
        assertRejected(()->create(access,other,"before-late-delivery"),503,"DEMO_CAPACITY");
        store.ingest(envelope,"inforsight.demo.events.v1",0,3,1000);
        assertThat(store.get(id).path("status").asText()).isEqualTo("PROCESSING");
        assertRejected(()->create(access,other,"after-late-delivery"),503,"DEMO_CAPACITY");
        assertThat(store.verify(id).path("valid").asBoolean()).isTrue();
        // Once publication is durably committed, a later score failure releases
        // its slot as before. Retrying that run must acquire a new available slot.
        store.fail(id,"score","INFERENCE_UNAVAILABLE");
        assertThat(create(access,other,"after-score-failure").path("status").asText()).isEqualTo("WAITING");
        assertRejected(()->access.retry(owner,id),503,"DEMO_CAPACITY");
    }

    @Test void filterEnforcesCookieCsrfOriginAndOwnershipForEveryRunRoute()throws Exception {
        var access=access();var owner=access.issue();var stranger=access.issue();String id=create(access,owner,"one").path("correlation_id").asText();
        var filter=new DemoSessionFilter(access,mapper);
        for(String suffix:List.of("","/audit","/retry","/decision")){
            String method=suffix.equals("/retry")||suffix.equals("/decision")?"POST":"GET";
            var request=request(method,"/api/v1/demo/runs/"+id+suffix,access,stranger,true);var response=new MockHttpServletResponse();var chain=new MockFilterChain();
            filter.doFilter(request,response,chain);assertThat(response.getStatus()).as(suffix).isEqualTo(404);assertThat(chain.getRequest()).isNull();
        }
        var allowed=request("HEAD","/api/v1/demo/runs/"+id,access,owner,true);var passed=new MockFilterChain();filter.doFilter(allowed,new MockHttpServletResponse(),passed);assertThat(passed.getRequest()).isNotNull();
        for(String origin:List.of("https://attacker.example","https://demo.example:444","null","")){
            var request=request("POST","/api/v1/demo/runs",access,owner,true);request.removeHeader("Origin");if(!origin.isEmpty())request.addHeader("Origin",origin);
            var response=new MockHttpServletResponse();filter.doFilter(request,response,new MockFilterChain());assertThat(response.getStatus()).isEqualTo(403);
        }
        var csrf=request("POST","/api/v1/demo/runs",access,owner,false);var denied=new MockHttpServletResponse();filter.doFilter(csrf,denied,new MockFilterChain());assertThat(denied.getStatus()).isEqualTo(403);
        var absent=request("GET","/api/v1/demo/runs/"+id,access,null,false);var unauthorized=new MockHttpServletResponse();filter.doFilter(absent,unauthorized,new MockFilterChain());assertThat(unauthorized.getStatus()).isEqualTo(401);
        for(String path:List.of("/api/v1/%64emo/runs/"+id,"/api/v1/demo/runs/%72un-other","/api/v1/demo/runs/x/../"+id,"/api/v1/demo/runs/"+id+";x=y","/api/v1/cases/old")){
            var response=new MockHttpServletResponse();filter.doFilter(request("GET",path,access,owner,false),response,new MockFilterChain());assertThat(response.getStatus()).as(path).isEqualTo(404);
        }
        var bootstrap=new MockHttpServletResponse();filter.doFilter(request("GET","/api/v1/demo/session",access,null,false),bootstrap,new MockFilterChain());
        assertThat(bootstrap.getHeader("Set-Cookie")).contains("__Host-inforsight_session=","Path=/","Secure","HttpOnly","SameSite=Strict").doesNotContain("Domain=");
        long count=jdbc.queryForObject("SELECT count(*) FROM demo_session",Long.class);
        filter.doFilter(request("GET","/api/v1/demo/session",access,owner,false),new MockHttpServletResponse(),new MockFilterChain());
        assertThat(jdbc.queryForObject("SELECT count(*) FROM demo_session",Long.class)).isEqualTo(count);
    }

    @Test void retentionVerifiesBeforeWholeChainDeletionAndNeverDeletesActiveOrDamagedRuns(){
        var access=access();var owner=access.issue();var other=access.issue();
        String retired=create(access,owner,"retired").path("correlation_id").asText();store.fail(retired,"publication","TEST_FAILURE");
        String active=create(access,owner,"active").path("correlation_id").asText();
        String damaged=create(access,other,"damaged").path("correlation_id").asText();store.fail(damaged,"publication","TEST_FAILURE");
        jdbc.update("UPDATE demo_run SET updated_at=now()-interval '25 hours',created_at=now()-interval '72 hours',last_accessed_at=now()-interval '72 hours'");
        jdbc.update("UPDATE demo_run SET document=jsonb_set(document,'{stages,0,status}','\"waiting\"') WHERE correlation_id=?",damaged);
        assertThatThrownBy(()->jdbc.update("DELETE FROM demo_journal WHERE correlation_id=?",retired)).isInstanceOf(DataAccessException.class).hasMessageContaining("append-only");
        ObjectNode before=store.verify(retired);assertThat(before.path("valid").asBoolean()).isTrue();access.cleanup();
        assertRejected(()->access.requireOwner(owner,retired),410,"RUN_EXPIRED");assertRejected(()->access.requireOwner(other,retired),404,"NOT_FOUND");
        assertThat(jdbc.queryForObject("SELECT last_verified_head FROM demo_retention_receipt WHERE correlation_id=?",String.class,retired)).isEqualTo(before.path("head_hash").asText());
        assertThat(jdbc.queryForObject("SELECT count(*) FROM demo_journal WHERE correlation_id=?",Long.class,retired)).isZero();
        assertThat(store.get(active).path("status").asText()).isEqualTo("WAITING");assertThat(store.get(damaged).path("status").asText()).isEqualTo("FAILED");
    }

    @Test void onlyIdleAbandonedReviewsExpireAndTheRemainingEvidenceStillVerifies(){
        var access=access();var owner=access.issue();String idle=create(access,owner,"idle").path("correlation_id").asText();reviewReady(idle);
        String reading=create(access,owner,"reading").path("correlation_id").asText();reviewReady(reading);
        jdbc.update("UPDATE demo_run SET created_at=now()-interval '72 hours',last_accessed_at=now()-interval '25 hours'");
        access.requireOwner(owner,reading);access.cleanup();
        assertThat(store.get(idle).path("status").asText()).isEqualTo("EXPIRED");
        assertThat(store.get(idle).path("artifacts").has("decision")).isFalse();
        assertThat(DemoStore.stage(store.get(idle),"decision").path("status").asText()).isEqualTo("blocked");
        assertThat(store.verify(idle).path("valid").asBoolean()).isTrue();
        assertThat(store.verify(idle).path("entries").get(store.verify(idle).path("entries").size()-1).path("producer").asText()).isEqualTo("Java demo retention worker");
        assertThat(store.get(reading).path("status").asText()).isEqualTo("AWAITING_REVIEW");
        assertThatThrownBy(()->store.retry(idle)).isInstanceOf(IllegalStateException.class);
        jdbc.update("UPDATE demo_quota SET updated_at=now()-interval '49 hours'");access.cleanup();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM demo_quota",Integer.class)).isZero();
    }

    private MockHttpServletRequest request(String method,String path,DemoPublicAccess access,DemoPublicAccess.Session owner,boolean csrf){
        var request=new MockHttpServletRequest(method,path);request.setServerName("demo.example");request.addHeader("Host","demo.example");request.addHeader("Origin","https://demo.example");
        if(owner!=null){request.setCookies(new Cookie(access.cookieName(),owner.token()));if(csrf)request.addHeader("X-Demo-CSRF",access.csrf(owner));}return request;
    }
    private ObjectNode create(DemoPublicAccess access,DemoPublicAccess.Session owner,String key){
        return access.submit(owner,key,"request-"+key,()->{String id="run_"+DemoStore.uuid();return store.create(id,"evt_"+DemoStore.uuid(),"pol_"+DemoStore.uuid(),"late-payment",access.scopedKey(owner,key),"request-"+key,mapper.createObjectNode().put("fictional",true));});
    }
    private void reviewReady(String id){
        ObjectNode run=store.get(id);store.finish(id,"allocation",mapper.createObjectNode().put("selected_action","abstain"),"allocation","completed");
        store.finish(id,"case",mapper.createObjectNode().put("case_id",run.path("case_id").asText()).put("case_version",0).put("state","AWAITING_REVIEW"),"case","completed");
        store.finish(id,"agent",mapper.createObjectNode().put("status","ABSTAIN").put("authorized_to_act",false),"agent","abstained");
    }
    private void assertRejected(Runnable call,int status,String code){assertThatThrownBy(call::run).isInstanceOfSatisfying(DemoPublicAccess.Rejection.class,e->{assertThat(e.status).isEqualTo(status);assertThat(e.code).isEqualTo(code);});}
}
