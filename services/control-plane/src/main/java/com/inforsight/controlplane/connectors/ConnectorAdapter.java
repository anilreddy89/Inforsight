package com.inforsight.controlplane.connectors;

public interface ConnectorAdapter {
    ConnectorTarget target();
    ConnectorPreflightOutcome prepare(ConnectorPreflightRequest request);
}
