package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.containers.PostgreSQLContainer;

import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.assertj.core.api.Assertions.*;

/** Real PostgreSQL transactions; fixture outputs exercise storage, never a UI simulation. */
@EnabledIfEnvironmentVariable(named="INFORSIGHT_RUN_DEMO_INTEGRATION",matches="1")
class DemoStoreIntegrationTest {
    private final ObjectMapper mapper=new ObjectMapper();

    @Test void outboxInboxRetryAndHumanDecisionRemainDurableAndIdempotent() {
        try(var postgres=new PostgreSQLContainer<>("postgres:16-alpine")){
            postgres.start();var ds=new DriverManagerDataSource(postgres.getJdbcUrl(),postgres.getUsername(),postgres.getPassword());
            Flyway.configure().dataSource(ds).locations("classpath:db/migration").load().migrate();
            var jdbc=new JdbcTemplate(ds);var store=new DemoStore(jdbc,mapper,new DataSourceTransactionManager(ds));
            ObjectNode run=store.create("run-one","evt-one","pol-one","late-payment","submit-one","request-one",mapper.createObjectNode().put("fictional",true));
            assertThat(store.hash(store.create("ignored","ignored","ignored","late-payment","submit-one","request-one",mapper.createObjectNode()))).isEqualTo(store.hash(run));
            assertThatThrownBy(()->store.byKey("submit-one","different")).isInstanceOf(IllegalStateException.class);
            var envelope=store.pending().getFirst();
            store.publishing("run-one");store.published("run-one",mapper.createObjectNode().put("offset",3));
            store.ingest(envelope,"topic",0,3);int count=store.verify("run-one").path("verified_entries").asInt();
            store.ingest(envelope,"topic",0,3);assertThat(store.verify("run-one").path("verified_entries").asInt()).isEqualTo(count);
            store.start("run-one","snapshot");store.fail("run-one","snapshot","TEST_DEPENDENCY_DOWN");
            assertThat(store.get("run-one").path("status").asText()).isEqualTo("FAILED");
            var reloaded=new DemoStore(jdbc,mapper,new DataSourceTransactionManager(ds));
            assertThat(reloaded.retry("run-one").path("status").asText()).isEqualTo("PROCESSING");
            assertThat(reloaded.resumable()).contains("run-one");
            reloaded.start("run-one","snapshot");
            ObjectNode projected=mapper.createObjectNode();projected.set("snapshot",mapper.createObjectNode().put("snapshot_id","snap-one"));
            reloaded.finish("run-one","snapshot",projected,"projection","completed");
            assertThat(DemoStore.stage(reloaded.get("run-one"),"snapshot").path("attempt").asInt()).isEqualTo(2);
            reloaded.finish("run-one","allocation",mapper.createObjectNode().put("selected_action","abstain"),"allocation","completed");
            reloaded.finish("run-one","case",mapper.createObjectNode().put("case_id",run.path("case_id").asText()).put("case_version",0).put("state","AWAITING_REVIEW"),"case","completed");
            reloaded.finish("run-one","agent",mapper.createObjectNode().put("status","ABSTAIN").put("authorized_to_act",false),"agent","abstained");
            ObjectNode approval=decision("APPROVED","approve-one");
            assertThatThrownBy(()->reloaded.decide("run-one",approval)).isInstanceOf(IllegalArgumentException.class).hasMessageContaining("abstention");
            ObjectNode request=decision("REQUEST_MORE_INFORMATION","rfi-one");
            ObjectNode completed=reloaded.decide("run-one",request);
            assertThat(completed.path("status").asText()).isEqualTo("COMPLETED");
            assertThat(completed.path("artifacts").path("decision").path("authorized_to_act").asBoolean()).isFalse();
            assertThat(completed.path("artifacts").path("case").path("case_version").asInt()).isEqualTo(1);
            assertThat(DemoStore.stage(completed,"case").path("evidence").path("case_version").asInt()).isZero();
            assertThat(reloaded.hash(reloaded.decide("run-one",request))).isEqualTo(reloaded.hash(completed));
            assertThat(jdbc.queryForObject("SELECT count(*) FROM demo_decision",Integer.class)).isEqualTo(1);
            assertThat(reloaded.verify("run-one").path("valid").asBoolean()).isTrue();
            store.create("run-recovery","evt-recovery","pol-recovery","late-payment","submit-recovery","request-recovery",mapper.createObjectNode().put("fictional",true));
            var recoveryEnvelope=store.pending().getFirst();
            store.publishing("run-recovery");store.fail("run-recovery","publication","ACK_DATABASE_INTERRUPTION");
            store.ingest(recoveryEnvelope,"topic",0,4,1000);
            ObjectNode recovered=store.get("run-recovery");
            assertThat(recovered.path("status").asText()).isEqualTo("PROCESSING");
            assertThat(DemoStore.stage(recovered,"publication").path("evidence").path("publisher_ack_record_available").asBoolean(true)).isFalse();
            assertThat(store.verify("run-recovery").path("valid").asBoolean()).isTrue();
            store.quarantine("topic",0,5,"untrusted","INVALID_OR_UNBOUND_DEMO_ENVELOPE");
            store.quarantine("topic",0,5,"untrusted","INVALID_OR_UNBOUND_DEMO_ENVELOPE");
            assertThat(jdbc.queryForObject("SELECT count(*) FROM demo_ingress_quarantine",Integer.class)).isEqualTo(1);
            assertThatThrownBy(()->jdbc.update("UPDATE demo_journal SET canonical_payload='{}' WHERE sequence=1")).isInstanceOf(DataAccessException.class).hasMessageContaining("append-only");
            jdbc.execute("ALTER TABLE demo_journal DISABLE TRIGGER demo_journal_append_only");
            jdbc.update("UPDATE demo_journal SET producer='forged component' WHERE correlation_id='run-one' AND sequence=1");
            jdbc.execute("ALTER TABLE demo_journal ENABLE TRIGGER demo_journal_append_only");
            assertThat(reloaded.verify("run-one").path("failure_code").asText()).isEqualTo("JOURNAL_METADATA_MISMATCH");
            jdbc.execute("ALTER TABLE demo_journal DISABLE TRIGGER demo_journal_append_only");
            jdbc.update("UPDATE demo_journal SET canonical_payload='{}' WHERE sequence=1");
            jdbc.execute("ALTER TABLE demo_journal ENABLE TRIGGER demo_journal_append_only");
            assertThat(reloaded.verify("run-one").path("valid").asBoolean()).isFalse();
        }
    }

    @Test void rejectsMissingArtifactsRemovedOrDowngradedStages() {
        try(var postgres=new PostgreSQLContainer<>("postgres:16-alpine")){
            postgres.start();var ds=new DriverManagerDataSource(postgres.getJdbcUrl(),postgres.getUsername(),postgres.getPassword());
            Flyway.configure().dataSource(ds).locations("classpath:db/migration").load().migrate();
            var jdbc=new JdbcTemplate(ds);var store=new DemoStore(jdbc,mapper,new DataSourceTransactionManager(ds));
            ObjectNode original=completeFixture(store,"run-projection");
            assertThat(store.verify("run-projection").path("valid").asBoolean()).isTrue();

            for(String artifact:List.of("projection","snapshot","score","rules","allocation","case","agent","decision")){
                ObjectNode damaged=original.deepCopy();((ObjectNode)damaged.path("artifacts")).remove(artifact);
                assertProjectionRejected(store,jdbc,damaged,"removed artifact: "+artifact);
            }
            for(String name:DemoStore.STAGES){
                ObjectNode removed=original.deepCopy();ArrayNode stages=(ArrayNode)removed.path("stages");
                for(int index=0;index<stages.size();index++)if(stages.get(index).path("stage").asText().equals(name)){stages.remove(index);break;}
                assertProjectionRejected(store,jdbc,removed,"removed stage: "+name);
                ObjectNode downgraded=original.deepCopy();DemoStore.stage(downgraded,name).put("status","waiting");
                assertProjectionRejected(store,jdbc,downgraded,"downgraded stage: "+name);
            }
            ObjectNode duplicated=original.deepCopy();((ArrayNode)duplicated.path("stages")).add(DemoStore.stage(duplicated,"score").deepCopy());
            assertProjectionRejected(store,jdbc,duplicated,"duplicate stage identity");
            jdbc.update("UPDATE demo_run SET document=CAST(? AS jsonb) WHERE correlation_id=?",store.encode(original),"run-projection");
            assertThat(store.verify("run-projection").path("valid").asBoolean()).isTrue();
        }
    }

    @Test void verificationHoldsTheRunLockUntilAllEvidenceReadsFinish() throws Exception {
        try(var postgres=new PostgreSQLContainer<>("postgres:16-alpine")){
            postgres.start();var ds=new DriverManagerDataSource(postgres.getJdbcUrl(),postgres.getUsername(),postgres.getPassword());
            Flyway.configure().dataSource(ds).locations("classpath:db/migration").load().migrate();
            var jdbc=new JdbcTemplate(ds);var manager=new DataSourceTransactionManager(ds);
            var store=new DemoStore(jdbc,mapper,manager);
            store.create("run-consistent","evt-consistent","pol-consistent","late-payment","submit-consistent","request-consistent",mapper.createObjectNode().put("fictional",true));
            CountDownLatch documentRead=new CountDownLatch(1),continueVerification=new CountDownLatch(1);
            AtomicBoolean intercept=new AtomicBoolean(true);
            // Pause after the real PostgreSQL document read, before journal and
            // checkpoint reads. A concurrent writer must remain blocked here.
            var inspectingJdbc=new JdbcTemplate(ds){
                @Override public <T> List<T> query(String sql,RowMapper<T> rowMapper,Object... args){
                    List<T> result=super.query(sql,rowMapper,args);
                    if(sql.startsWith("SELECT document::text FROM demo_run")&&intercept.compareAndSet(true,false)){
                        documentRead.countDown();
                        try{if(!continueVerification.await(10,TimeUnit.SECONDS))throw new IllegalStateException("test verifier was not released");}
                        catch(InterruptedException e){Thread.currentThread().interrupt();throw new IllegalStateException(e);}
                    }
                    return result;
                }
            };
            var verifier=new DemoStore(inspectingJdbc,mapper,manager);
            try(ExecutorService executor=Executors.newFixedThreadPool(2)){
                Future<ObjectNode> receipt=executor.submit(()->verifier.verify("run-consistent"));
                try{
                    assertThat(documentRead.await(5,TimeUnit.SECONDS)).isTrue();
                    Future<?> writer=executor.submit(()->store.start("run-consistent","publication"));
                    long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(5);int blocked=0;
                    while(blocked==0&&System.nanoTime()<deadline){
                        blocked=jdbc.queryForObject("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock'",Integer.class);
                        if(blocked==0)Thread.sleep(20);
                    }
                    assertThat(blocked).as("stage writer waits for the verifier's transaction lock").isGreaterThan(0);
                    assertThat(writer.isDone()).isFalse();
                    continueVerification.countDown();
                    ObjectNode verified=receipt.get(5,TimeUnit.SECONDS);
                    assertThat(verified.path("valid").asBoolean()).isTrue();
                    assertThat(verified.path("verified_entries").asInt()).isEqualTo(1);
                    writer.get(5,TimeUnit.SECONDS);
                    assertThat(store.verify("run-consistent").path("valid").asBoolean()).isTrue();
                    assertThat(store.verify("run-consistent").path("verified_entries").asInt()).isEqualTo(2);
                }finally{continueVerification.countDown();}
            }
        }
    }

    private ObjectNode completeFixture(DemoStore store,String id){
        ObjectNode run=store.create(id,"evt-"+id,"pol-"+id,"late-payment","submit-"+id,"request-"+id,mapper.createObjectNode().put("fictional",true));
        ObjectNode envelope=store.pending().getFirst();store.publishing(id);store.published(id,mapper.createObjectNode().put("offset",3));store.ingest(envelope,"topic",0,3);
        ObjectNode projected=mapper.createObjectNode();projected.set("snapshot",mapper.createObjectNode().put("snapshot_id","snap-"+id));
        store.finish(id,"snapshot",projected,"projection","completed");
        store.finish(id,"score",mapper.createObjectNode().put("calibrated_probability",0.5),"score","completed");
        store.finish(id,"rules",mapper.createObjectNode().put("rules_version","fixture"),"rules","completed");
        store.finish(id,"allocation",mapper.createObjectNode().put("selected_action","abstain"),"allocation","completed");
        store.finish(id,"case",mapper.createObjectNode().put("case_id",run.path("case_id").asText()).put("case_version",0).put("state","AWAITING_REVIEW"),"case","completed");
        store.finish(id,"agent",mapper.createObjectNode().put("status","ABSTAIN").put("authorized_to_act",false),"agent","abstained");
        return store.decide(id,decision("REJECTED","reject-"+id));
    }

    private void assertProjectionRejected(DemoStore store,JdbcTemplate jdbc,ObjectNode damaged,String description){
        jdbc.update("UPDATE demo_run SET document=CAST(? AS jsonb) WHERE correlation_id=?",store.encode(damaged),damaged.path("correlation_id").asText());
        ObjectNode receipt=store.verify(damaged.path("correlation_id").asText());
        assertThat(receipt.path("valid").asBoolean()).as(description).isFalse();
        assertThat(receipt.path("verified_entries").asInt()).as(description).isZero();
    }
    private ObjectNode decision(String type,String key){return mapper.createObjectNode().put("decision",type).put("expected_case_version",0)
            .put("idempotency_key",key).put("reviewer_id","fictional-reviewer").put("rationale","Test fixture evidence review").put("notes","");}
}
