package com.inforsight.controlplane.web;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.springframework.http.MediaType.APPLICATION_JSON;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Exercises the persistence profile through the public REST contract. */
@EnabledIfEnvironmentVariable(named = "INFORSIGHT_RUN_P4_04_INTEGRATION", matches = "1")
@Testcontainers
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("persistence")
class PersistentControlPlaneControllerIntegrationTest {
    @Container
    private static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void databaseProperties(DynamicPropertyRegistry properties) {
        properties.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        properties.add("spring.datasource.username", POSTGRES::getUsername);
        properties.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Autowired
    MockMvc mockMvc;

    @Test
    void persistentProfileWritesDecisionAndReturnsCommittedAuditHash() throws Exception {
        String triage = mockMvc.perform(post("/api/v1/cases/triage")
                        .contentType(APPLICATION_JSON)
                        .content("{\"as_of_date\":\"2026-09-18T00:00:00Z\",\"policy_ids\":[\"p-persistence\"]}"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        String caseId = JsonPath.read(triage, "$.cases[0].case_id");

        mockMvc.perform(post("/api/v1/cases/{caseId}/decision", caseId)
                        .contentType(APPLICATION_JSON)
                        .content("{\"reviewer_id\":\"reviewer-persistence\",\"decision\":\"APPROVED\",\"idempotency_key\":\"idem-persistence-1\",\"expected_case_version\":0}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.transition_status").value("HUMAN_REVIEWED"))
                .andExpect(jsonPath("$.audit_record_hash").value(org.hamcrest.Matchers.matchesPattern("[0-9a-f]{64}")));
    }
}
