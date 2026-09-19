package com.inforsight.controlplane.domain;

public record ActionDefinition(
        String actionType,
        String channel,
        long directCostUsdMicros,
        int personnelSeconds,
        int regulatoryCoolingOffDays,
        int minimumTenureDays,
        Integer maximumTenureDays,
        boolean requiresGracePeriod) {
    public static java.util.List<ActionDefinition> standardCatalog() {
        return java.util.List.of(
                new ActionDefinition("courtesy_reminder", "sms", 1_500_000L, 0, 30, 30, null, false),
                new ActionDefinition("grace_period_consultation", "phone", 25_000_000L, 1_800, 30, 60, null, true),
                new ActionDefinition("specialist_phone_outreach", "phone", 65_000_000L, 3_600, 30, 90, null, false),
                new ActionDefinition("payment_method_remediation", "email", 3_000_000L, 360, 14, 30, null, false),
                new ActionDefinition("abstain", "none", 0L, 0, 0, 0, null, false));
    }
}
