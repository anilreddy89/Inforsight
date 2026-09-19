package com.inforsight.controlplane.web;

import com.inforsight.controlplane.casework.CaseStore;
import com.inforsight.controlplane.domain.InferenceScore;
import com.inforsight.controlplane.inference.InferenceClient;
import com.inforsight.controlplane.domain.PolicyContext;
import com.inforsight.controlplane.rules.EligibilityEngine;
import org.springframework.http.HttpStatus;
import com.fasterxml.jackson.annotation.JsonProperty;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;

@RestController
@RequestMapping("/api/v1/cases")
public class ControlPlaneController {
    private final InferenceClient inference;
    private final CaseStore cases;
    private final EligibilityEngine eligibility;

    public ControlPlaneController(InferenceClient inference, CaseStore cases, EligibilityEngine eligibility) { this.inference = inference; this.cases = cases; this.eligibility = eligibility; }

    @PostMapping("/triage")
    public TriageResponse triage(@RequestBody TriageRequest request) {
        if (request.policyIds() == null || request.policyIds().isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "policy_ids is required");
        Instant asOf = request.asOfDate() == null ? Instant.now() : request.asOfDate();
        List<CaseSummary> summaries = request.policyIds().stream().map(policyId -> {
            InferenceScore score = inference.score(policyId, asOf);
            PolicyContext context = new PolicyContext(policyId, asOf, "active", 365, false, 0, false, false, false, false, false, false, false, null);
            eligibility.evaluate(context); // keep the rules firewall on the triage path; P4-03 does not bypass it
            CaseStore.CaseRecord record = cases.create(policyId, asOf, score, "abstain");
            return new CaseSummary(record.caseId(), policyId, score.operationalTier(), score.calibratedProbability(), record.recommendedAction(), record.state());
        }).toList();
        return new TriageResponse("batch_" + asOf.toEpochMilli(), summaries.size(), summaries.size(), 0.0, 0.0, summaries);
    }

    @GetMapping("/{caseId}")
    public CaseBrief brief(@PathVariable String caseId) {
        CaseStore.CaseRecord record = cases.find(caseId).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "case not found"));
        return new CaseBrief(record.caseId(), record.policyId(), record.asOf(), record.state(), record.score().calibratedProbability(), record.score().operationalTier(), "A bounded local case brief; grounding remains read-only.", record.score().bundleDigest(), record.recommendedAction(), record.authorizedToAct());
    }

    @PostMapping("/{caseId}/decision")
    public DecisionResponse decision(@PathVariable String caseId, @RequestBody DecisionRequest request) {
        CaseStore.CaseRecord record = cases.decide(caseId, request.decision(), request.expectedCaseVersion(), request.idempotencyKey());
        return new DecisionResponse(record.caseId(), record.state(), "pending-p4-04-audit", record.authorizedToAct());
    }

    public record TriageRequest(@JsonProperty("as_of_date") Instant asOfDate,
                                @JsonProperty("policy_ids") List<String> policyIds,
                                @JsonProperty("specialist_capacity_hours") Double specialistCapacityHours,
                                @JsonProperty("budget_limit_usd") Double budgetLimitUsd) {}
    public record TriageResponse(String batchId, int totalEvaluated, int allocatedCases, double totalSpendUsd, double totalSpecialistHours, List<CaseSummary> cases) {}
    public record CaseSummary(String caseId, String policyId, String operationalTier, double calibratedProbability, String recommendedAction, String state) {}
    public record CaseBrief(String caseId, String policyId, Instant asOfDate, String currentState, double calibratedProbability, String operationalTier, String factualNarrative, String groundingHash, String recommendedAction, boolean authorizedToAct) {}
    public record DecisionRequest(@JsonProperty("reviewer_id") String reviewerId,
                                  String decision,
                                  @JsonProperty("selected_action") String selectedAction,
                                  @JsonProperty("rationale_code") String rationaleCode,
                                  String notes,
                                  Instant timestamp,
                                  @JsonProperty("idempotency_key") String idempotencyKey,
                                  @JsonProperty("expected_case_version") long expectedCaseVersion) {}
    public record DecisionResponse(String caseId, String transitionStatus, String auditRecordHash, boolean authorizedToAct) {}
}
