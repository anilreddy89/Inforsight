package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.inforsight.controlplane.audit.AuditHash;
import org.junit.jupiter.api.Test;
import java.util.List;
import static org.assertj.core.api.Assertions.*;

class DemoJournalVerifierTest {
    @Test void rejectsChangedPayloadRemovedTailReorderedRecordsAndWrongCheckpoint(){
        var verifier=new DemoJournalVerifier();
        ObjectNode first=entry(1,"0".repeat(64),"{\"stage\":\"submission\"}");
        ObjectNode second=entry(2,first.path("current_hash").asText(),"{\"stage\":\"decision\"}");
        String head=second.path("current_hash").asText();
        assertThat(verifier.verify(List.of(first,second),2,head).valid()).isTrue();
        ObjectNode tampered=second.deepCopy().put("canonical_payload","{\"stage\":\"forged approval\"}");
        assertThat(verifier.verify(List.of(first,tampered),2,head).failureCode()).isEqualTo("JOURNAL_HASH_MISMATCH");
        assertThat(verifier.verify(List.of(first),2,head).failureCode()).isEqualTo("CHECKPOINT_MISMATCH");
        assertThat(verifier.verify(List.of(second,first),2,head).failureCode()).isEqualTo("JOURNAL_SEQUENCE_MISMATCH");
        assertThat(verifier.verify(List.of(first,second),2,"f".repeat(64)).valid()).isFalse();
    }
    private ObjectNode entry(int sequence,String parent,String payload){return new ObjectMapper().createObjectNode().put("sequence",sequence).put("parent_hash",parent)
            .put("canonical_payload",payload).put("current_hash",AuditHash.sha256(parent+"\n"+payload));}
}
