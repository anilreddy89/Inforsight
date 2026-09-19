package com.inforsight.controlplane.rules;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.domain.PolicyContext;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.time.Instant;
import java.util.HashSet;

import static org.assertj.core.api.Assertions.assertThat;

class EligibilityParityFixtureTest {
    @Test
    void canonicalFixturesProduceExpectedEligibleActionSets() throws Exception {
        InputStream stream = getClass().getResourceAsStream("/parity/eligibility-fixtures.json");
        assertThat(stream).isNotNull();
        JsonNode fixtures = new ObjectMapper().readTree(stream);
        var engine = new EligibilityEngine();
        for (JsonNode fixture : fixtures) {
            var context = new PolicyContext(fixture.get("id").asText(), Instant.parse("2026-09-18T00:00:00Z"), fixture.get("status").asText(), fixture.get("tenure_days").asInt(), fixture.get("in_grace_period").asBoolean(), fixture.get("days_past_due").asInt(), nullableBoolean(fixture.get("has_active_claim")), nullableBoolean(fixture.get("has_legal_hold")), nullableBoolean(fixture.get("has_registered_dispute")), nullableBoolean(fixture.get("sms_opt_out")), nullableBoolean(fixture.get("email_opt_out")), nullableBoolean(fixture.get("phone_opt_out")), nullableBoolean(fixture.get("dnc_registered")), null);
            var actual = new HashSet<>(engine.evaluate(context).stream().filter(r -> r.eligible()).map(r -> r.actionType()).toList());
            var expected = new HashSet<String>(); fixture.get("expected_eligible").forEach(value -> expected.add(value.asText()));
            assertThat(actual).as(fixture.get("id").asText()).isEqualTo(expected);
        }
    }

    private static Boolean nullableBoolean(JsonNode node) { return node.isNull() ? null : node.asBoolean(); }
}
