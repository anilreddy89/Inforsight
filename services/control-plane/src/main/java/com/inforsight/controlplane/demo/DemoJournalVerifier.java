package com.inforsight.controlplane.demo;

import com.fasterxml.jackson.databind.JsonNode;
import com.inforsight.controlplane.audit.AuditHash;
import java.util.List;

/** Pure verifier also usable with exported records; no claims of external anchoring. */
public final class DemoJournalVerifier {
    public record Result(boolean valid,String failureCode,int verifiedEntries,String headHash) {}
    public Result verify(List<? extends JsonNode> rows,long checkpointSequence,String checkpointHash){
        String head="0".repeat(64);long sequence=0;
        for(JsonNode entry:rows){
            if(entry.path("sequence").asLong()!=++sequence)return new Result(false,"JOURNAL_SEQUENCE_MISMATCH",0,head);
            if(!head.equals(entry.path("parent_hash").asText()))return new Result(false,"JOURNAL_PARENT_MISMATCH",0,head);
            String computed=AuditHash.sha256(head+"\n"+entry.path("canonical_payload").asText());
            if(!computed.equals(entry.path("current_hash").asText()))return new Result(false,"JOURNAL_HASH_MISMATCH",0,head);
            head=computed;
        }
        if(rows.isEmpty()||checkpointSequence!=sequence||!head.equals(checkpointHash))return new Result(false,"CHECKPOINT_MISMATCH",0,head);
        return new Result(true,null,rows.size(),head);
    }
}
