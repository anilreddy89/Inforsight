package com.inforsight.controlplane.web;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

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
}
