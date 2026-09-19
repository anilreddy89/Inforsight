package com.inforsight.controlplane.domain;

import java.time.Instant;

public record PolicyContext(
        String policyId,
        Instant asOf,
        String status,
        int tenureDays,
        boolean inGracePeriod,
        Integer daysPastDue,
        Boolean hasActiveClaim,
        Boolean hasLegalHold,
        Boolean hasRegisteredDispute,
        Boolean smsOptOut,
        Boolean emailOptOut,
        Boolean phoneOptOut,
        Boolean dncRegistered,
        Instant lastContactDate) {
    public PolicyContext {
        if (policyId == null || policyId.isBlank()) throw new IllegalArgumentException("policy_id cannot be empty");
        if (asOf == null) throw new IllegalArgumentException("as_of is required");
        if (tenureDays < 0 || (daysPastDue != null && daysPastDue < 0)) throw new IllegalArgumentException("negative policy age");
        if (lastContactDate != null && lastContactDate.isAfter(asOf)) throw new IllegalArgumentException("last_contact_date is after as_of");
    }
}
