package com.inforsight.controlplane.web;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.assertj.core.api.Assertions.assertThat;
import org.springframework.test.web.servlet.MvcResult;
import com.jayway.jsonpath.JsonPath;

@SpringBootTest
@AutoConfigureMockMvc
class ControlPlaneControllerTest {
    @Autowired MockMvc mockMvc;

    @Test
    void triageCreatesNonAuthoritativeCases() throws Exception {
        mockMvc.perform(post("/api/v1/cases/triage")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"as_of_date\":\"2026-09-18T00:00:00Z\",\"policy_ids\":[\"p-1\"]}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.total_evaluated").value(1))
                .andExpect(jsonPath("$.cases[0].state").value("RECOMMENDED"));
    }

    @Test
    void caseBriefAndDecisionAreVersionedAndIdempotent() throws Exception {
        MvcResult triage = mockMvc.perform(post("/api/v1/cases/triage")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"as_of_date\":\"2026-09-18T00:00:00Z\",\"policy_ids\":[\"p-contract\"]}"))
                .andExpect(status().isOk())
                .andReturn();
        String caseId = JsonPath.read(triage.getResponse().getContentAsString(), "$.cases[0].case_id");

        mockMvc.perform(get("/api/v1/cases/{caseId}", caseId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.case_id").value(caseId))
                .andExpect(jsonPath("$.current_state").value("RECOMMENDED"))
                .andExpect(jsonPath("$.authorized_to_act").value(false));

        String decision = "{\"reviewer_id\":\"reviewer-1\",\"decision\":\"APPROVED\",\"selected_action\":\"abstain\",\"idempotency_key\":\"idem-contract-1\",\"expected_case_version\":0}";
        String first = mockMvc.perform(post("/api/v1/cases/{caseId}/decision", caseId)
                        .contentType(MediaType.APPLICATION_JSON).content(decision))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.transition_status").value("HUMAN_REVIEWED"))
                .andExpect(jsonPath("$.authorized_to_act").value(true))
                .andReturn().getResponse().getContentAsString();
        String replay = mockMvc.perform(post("/api/v1/cases/{caseId}/decision", caseId)
                        .contentType(MediaType.APPLICATION_JSON).content(decision))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        assertThat(replay).isEqualTo(first);
    }

    @Test
    void invalidCaseAndMissingIdempotencyHaveStableErrors() throws Exception {
        mockMvc.perform(get("/api/v1/cases/case-does-not-exist"))
                .andExpect(status().isNotFound());
        mockMvc.perform(post("/api/v1/cases/triage")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"as_of_date\":\"2026-09-18T00:00:00Z\",\"policy_ids\":[]}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("BAD_REQUEST"));
    }
}
