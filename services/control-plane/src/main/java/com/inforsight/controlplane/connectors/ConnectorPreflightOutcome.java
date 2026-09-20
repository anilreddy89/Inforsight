package com.inforsight.controlplane.connectors;

/** A handoff preview only. This is never an external execution command. */
public record ConnectorPreflightOutcome(String status, String reasonCode, String externalReference,
                                        boolean authorizedToAct, boolean externalExecutionDisabled) {
    public ConnectorPreflightOutcome {
        if (authorizedToAct || !externalExecutionDisabled) throw new IllegalArgumentException("connector output cannot authorize execution");
    }
}
