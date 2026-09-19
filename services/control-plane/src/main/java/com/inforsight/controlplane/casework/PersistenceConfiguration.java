package com.inforsight.controlplane.casework;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.inforsight.controlplane.audit.AuditLedgerRepository;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/** Activates only with the explicit `persistence` profile and a configured PostgreSQL datasource. */
@Configuration
@Profile("persistence")
public class PersistenceConfiguration {
    @Bean
    AuditLedgerRepository auditLedgerRepository(JdbcTemplate jdbc) {
        return new AuditLedgerRepository(jdbc);
    }

    @Bean
    CaseWorkflow persistentCaseWorkflow(JdbcTemplate jdbc, ObjectMapper mapper,
                                        PlatformTransactionManager transactionManager, AuditLedgerRepository audit) {
        return new PersistentCaseRepository(jdbc, mapper, new TransactionTemplate(transactionManager), audit);
    }
}
