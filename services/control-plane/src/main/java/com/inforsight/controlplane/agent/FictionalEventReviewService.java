package com.inforsight.controlplane.agent;

import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.casework.CaseWorkflow;
import com.inforsight.controlplane.casework.PersistentCaseRepository;
import com.inforsight.controlplane.domain.PolicyContext;
import com.inforsight.controlplane.inference.InferenceClient;
import com.inforsight.controlplane.rules.EligibilityEngine;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/** Opt-in fictional event projection; never a production policy-event parser. */
@Service
@Profile("persistence")
public class FictionalEventReviewService {
    private final InferenceClient inference;
    private final EligibilityEngine eligibility;
    private final CaseWorkflow cases;
    private final TrustedAgentHandoffStore handoffs;

    public FictionalEventReviewService(InferenceClient inference, EligibilityEngine eligibility,
                                       CaseWorkflow cases, TrustedAgentHandoffStore handoffs) {
        this.inference = inference; this.eligibility = eligibility; this.cases = cases; this.handoffs = handoffs;
    }

    @Transactional
    public TrustedAgentHandoff ingest(FictionalEvent event) {
        event.validate();
        Map<String, Object> features = Map.ofEntries(
                Map.entry("tenure_days", (double) event.tenureDays()),
                Map.entry("premium_amount_cents", 10000.0),
                Map.entry("recent_delay_days", "late".equals(event.paymentStatus()) ? 15.0 : 0.0),
                Map.entry("recent_failed_payment_count", "late".equals(event.paymentStatus()) ? 1.0 : 0.0),
                Map.entry("recent_retry_count", 0.0), Map.entry("recent_recovery_count", 0.0),
                Map.entry("arrears_duration_days", "late".equals(event.paymentStatus()) ? 15.0 : 0.0),
                Map.entry("rolling_on_time_rate", "late".equals(event.paymentStatus()) ? 0.5 : 1.0),
                Map.entry("rolling_payment_count", 6.0), Map.entry("recent_notice_count", 0.0),
                Map.entry("recent_contact_count", 0.0), Map.entry("payment_attribute_missing", 0.0),
                Map.entry("contact_attribute_missing", 0.0), Map.entry("product_type", "fictional_term_life"),
                Map.entry("billing_frequency", "monthly"), Map.entry("notice_category", "none"),
                Map.entry("contact_category", "none"));
        var score = inference.scoreWithFeatures(event.policyId(), event.asOf(), features);
        var context = new PolicyContext(event.policyId(), event.asOf(), event.status(), event.tenureDays(),
                "grace_period".equals(event.status()), "late".equals(event.paymentStatus()) ? 15 : 0,
                event.hasActiveClaim(), event.hasLegalHold(), event.hasRegisteredDispute(), event.smsOptOut(),
                event.emailOptOut(), event.phoneOptOut(), event.dncRegistered(), null);
        List<String> allowed = eligibility.evaluate(context).stream().filter(result -> result.eligible())
                .map(result -> result.actionType()).toList();
        CaseStore.CaseRecord record = cases.create(event.policyId(), event.asOf(), score, "abstain");
        var handoff = new TrustedAgentHandoff("1.0.0", record.caseId(), record.version(),
                PersistentCaseRepository.snapshotId(record), event.eventId(), event.policyId(), event.asOf(),
                event.observedAt(), event.paymentStatus(), allowed, "fictional-procedure@2.0",
                "Fictional specialist review procedure. Consult the case evidence before any action.",
                Instant.parse("2026-01-01T00:00:00Z"), Instant.parse("2027-01-01T00:00:00Z"), false);
        handoffs.save(handoff);
        return handoff;
    }

    public record FictionalEvent(
            @com.fasterxml.jackson.annotation.JsonProperty("event_id") String eventId,
            @com.fasterxml.jackson.annotation.JsonProperty("policy_id") String policyId,
            @com.fasterxml.jackson.annotation.JsonProperty("as_of") Instant asOf,
            @com.fasterxml.jackson.annotation.JsonProperty("observed_at") Instant observedAt,
            @com.fasterxml.jackson.annotation.JsonProperty("payment_status") String paymentStatus,
            String status,
            @com.fasterxml.jackson.annotation.JsonProperty("tenure_days") int tenureDays,
            @com.fasterxml.jackson.annotation.JsonProperty("has_active_claim") Boolean hasActiveClaim,
            @com.fasterxml.jackson.annotation.JsonProperty("has_legal_hold") Boolean hasLegalHold,
            @com.fasterxml.jackson.annotation.JsonProperty("has_registered_dispute") Boolean hasRegisteredDispute,
            @com.fasterxml.jackson.annotation.JsonProperty("sms_opt_out") Boolean smsOptOut,
            @com.fasterxml.jackson.annotation.JsonProperty("email_opt_out") Boolean emailOptOut,
            @com.fasterxml.jackson.annotation.JsonProperty("phone_opt_out") Boolean phoneOptOut,
            @com.fasterxml.jackson.annotation.JsonProperty("dnc_registered") Boolean dncRegistered) {
        public void validate() {
            if (eventId == null || eventId.isBlank() || eventId.length() > 128
                    || policyId == null || policyId.isBlank() || policyId.length() > 128
                    || asOf == null || observedAt == null || observedAt.isAfter(asOf) || asOf.isAfter(Instant.now())
                    || asOf.isBefore(Instant.parse("2026-01-01T00:00:00Z"))
                    || !asOf.isBefore(Instant.parse("2027-01-01T00:00:00Z"))
                    || !("late".equals(paymentStatus) || "current".equals(paymentStatus))
                    || !("active".equals(status) || "grace_period".equals(status))
                    || tenureDays < 0 || tenureDays > 36500
                    || hasActiveClaim == null || hasLegalHold == null || hasRegisteredDispute == null
                    || smsOptOut == null || emailOptOut == null || phoneOptOut == null || dncRegistered == null) {
                throw new IllegalArgumentException("invalid fictional event or missing safety evidence");
            }
        }
    }
}
