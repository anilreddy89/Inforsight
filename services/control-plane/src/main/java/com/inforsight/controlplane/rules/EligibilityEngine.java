package com.inforsight.controlplane.rules;

import com.inforsight.controlplane.domain.ActionDefinition;
import com.inforsight.controlplane.domain.EligibilityResult;
import com.inforsight.controlplane.domain.PolicyContext;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Service
public class EligibilityEngine {
    private final List<ActionDefinition> catalog = ActionDefinition.standardCatalog();

    public List<EligibilityResult> evaluate(PolicyContext context) {
        List<EligibilityResult> results = new ArrayList<>();
        boolean missingSafety = context.hasActiveClaim() == null || context.hasLegalHold() == null || context.hasRegisteredDispute() == null;
        if (missingSafety) return unavailable(results);
        String freeze = context.hasLegalHold() ? "DISQUALIFIED_LEGAL_HOLD" :
                context.hasActiveClaim() ? "DISQUALIFIED_ACTIVE_CLAIM" :
                        context.hasRegisteredDispute() ? "DISQUALIFIED_LEGAL_DISPUTE_FREEZE" : null;
        if (freeze != null) return frozen(results, freeze);
        String status = context.status().toLowerCase();
        if (!(status.equals("active") || status.equals("grace_period"))) {
            String reason = switch (status) {
                case "lapsed" -> "DISQUALIFIED_POLICY_LAPSED";
                case "surrendered" -> "DISQUALIFIED_POLICY_SURRENDERED";
                case "terminated" -> "DISQUALIFIED_POLICY_TERMINATED";
                case "matured" -> "DISQUALIFIED_POLICY_MATURED";
                default -> "DISQUALIFIED_POLICY_NOT_IN_FORCE";
            };
            return frozen(results, reason);
        }
        for (ActionDefinition action : catalog) {
            if (action.actionType().equals("abstain")) {
                results.add(new EligibilityResult("abstain", true, List.of()));
                continue;
            }
            List<String> reasons = new ArrayList<>();
            if (action.channel().equals("sms") && Boolean.TRUE.equals(context.smsOptOut())) reasons.add("DISQUALIFIED_CHANNEL_OPT_OUT_SMS");
            if (action.channel().equals("email") && Boolean.TRUE.equals(context.emailOptOut())) reasons.add("DISQUALIFIED_CHANNEL_OPT_OUT_EMAIL");
            if (action.channel().equals("phone") && Boolean.TRUE.equals(context.phoneOptOut())) reasons.add("DISQUALIFIED_CHANNEL_OPT_OUT_PHONE");
            if (action.channel().equals("phone") && Boolean.TRUE.equals(context.dncRegistered())) reasons.add("DISQUALIFIED_DNC_REGISTRY");
            if (context.lastContactDate() != null && Duration.between(context.lastContactDate(), context.asOf()).toDays() < action.regulatoryCoolingOffDays()) reasons.add("DISQUALIFIED_CONTACT_COOLING_OFF_ACTIVE");
            if (action.requiresGracePeriod() && !context.inGracePeriod()) reasons.add("DISQUALIFIED_GRACE_PERIOD_REQUIRED");
            if (context.tenureDays() < action.minimumTenureDays()) reasons.add("DISQUALIFIED_MINIMUM_TENURE_NOT_MET");
            if (action.maximumTenureDays() != null && context.tenureDays() > action.maximumTenureDays()) reasons.add("DISQUALIFIED_MAXIMUM_TENURE_EXCEEDED");
            results.add(new EligibilityResult(action.actionType(), reasons.isEmpty(), reasons));
        }
        return List.copyOf(results);
    }

    private List<EligibilityResult> unavailable(List<EligibilityResult> ignored) { return catalog.stream().map(a -> new EligibilityResult(a.actionType(), a.actionType().equals("abstain"), a.actionType().equals("abstain") ? List.of() : List.of("DISQUALIFIED_MISSING_SAFETY_EVIDENCE"))).toList(); }
    private List<EligibilityResult> frozen(List<EligibilityResult> ignored, String reason) { return catalog.stream().map(a -> new EligibilityResult(a.actionType(), a.actionType().equals("abstain"), a.actionType().equals("abstain") ? List.of() : List.of(reason))).toList(); }
}
