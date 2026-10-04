package com.inforsight.controlplane.agent;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import com.inforsight.controlplane.audit.AuditLedgerRepository;
import com.inforsight.controlplane.audit.AuditLedgerVerifier;
import java.util.Map;
import java.util.Set;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.dao.DataIntegrityViolationException;

/** Explicitly enabled only for the local fictional demo topology. */
@RestController
@RequestMapping("/api/v1/demo")
@Profile("persistence")
@ConditionalOnProperty(name = "inforsight.demo.enabled", havingValue = "true")
public class FictionalEventReviewController {
    private final FictionalEventReviewService service;
    private final TrustedAgentHandoffStore handoffs;
    private final AuditLedgerRepository ledger;
    private final ObjectMapper mapper;
    private static final Set<String> EVENT_FIELDS = Set.of("event_id", "policy_id", "as_of", "observed_at",
            "payment_status", "status", "tenure_days", "has_active_claim", "has_legal_hold",
            "has_registered_dispute", "sms_opt_out", "email_opt_out", "phone_opt_out", "dnc_registered");
    public FictionalEventReviewController(FictionalEventReviewService service, TrustedAgentHandoffStore handoffs,
                                          AuditLedgerRepository ledger, ObjectMapper mapper) {
        this.service = service; this.handoffs = handoffs; this.ledger = ledger; this.mapper = mapper;
    }
    @PostMapping("/events")
    public TrustedAgentHandoff ingest(@RequestBody JsonNode event) {
        if (!event.isObject() || event.size() != EVENT_FIELDS.size()
                || !event.properties().stream().map(Map.Entry::getKey).allMatch(EVENT_FIELDS::contains)) {
            throw new IllegalArgumentException("invalid fictional event fields");
        }
        try {
            return service.ingest(mapper.treeToValue(event, FictionalEventReviewService.FictionalEvent.class));
        } catch (com.fasterxml.jackson.core.JsonProcessingException failure) {
            throw new IllegalArgumentException("invalid fictional event JSON", failure);
        }
    }
    @GetMapping("/cases/{caseId}/handoff")
    public TrustedAgentHandoff handoff(@PathVariable String caseId) {
        return handoffs.find(caseId).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    }
    @GetMapping("/cases/{caseId}/audit")
    public Map<String, Object> audit(@PathVariable String caseId) {
        handoff(caseId);
        var entries = ledger.entries();
        var verified = new AuditLedgerVerifier().verify(entries, ledger.checkpoint());
        var caseEvents = entries.stream().filter(entry -> caseId.equals(entry.caseId()))
                .map(entry -> entry.eventType()).toList();
        var caseEntries = entries.stream().filter(entry -> caseId.equals(entry.caseId()))
                .map(entry -> Map.of("event_type", entry.eventType(), "case_version", entry.caseVersion(),
                        "current_hash", entry.currentHash(), "canonical_payload", entry.canonicalPayload())).toList();
        return Map.of("valid", verified.valid(), "events", caseEvents, "entries", caseEntries,
                "verified_entries", verified.verifiedEntries());
    }

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Map<String, String> badRequest(IllegalArgumentException failure) {
        return Map.of("code", "BAD_REQUEST", "message", failure.getMessage());
    }
    @ExceptionHandler(DataIntegrityViolationException.class)
    @ResponseStatus(HttpStatus.CONFLICT)
    public Map<String, String> duplicateEvent(DataIntegrityViolationException failure) {
        return Map.of("code", "CONFLICT", "message", "fictional event identity already recorded");
    }
}
