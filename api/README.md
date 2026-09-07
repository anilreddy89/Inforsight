# Inforsight External API Specifications

This directory contains versioned OpenAPI 3.1 specifications defining the REST interfaces exposed by the Java 21 / Spring Boot 3 Control Plane service for caseworker UIs, enterprise CRMs, and operational orchestration.

## Directory Structure

```text
api/
├── README.md
└── openapi/
    └── control-plane-v1.yaml    # OpenAPI 3.1 spec for Control Plane REST endpoints
```

## Key API Capabilities

1. **Case Triage Execution (`POST /api/v1/cases/triage`)**:
   - Executes batch policy intake, scoring via gRPC inference, deterministic eligibility filtering (ADR 0002 firewall), and knapsack uplift optimization under resource constraints.
2. **Case Retrieval (`GET /api/v1/cases/{case_id}`)**:
   - Returns structured case briefs with grounded evidence, policy state, risk tier, and recommended intervention.
3. **Caseworker Decision Recording (`POST /api/v1/cases/{case_id}/decision`)**:
   - Enforces human-in-the-loop authorization (ADR 0002). Only licensed caseworkers can approve, override, or dismiss interventions.
4. **Cryptographic Audit Retrieval (`GET /api/v1/cases/{case_id}/audit-trail`)**:
   - Returns immutable SHA-256 hash-chained event ledgers verifying tamper resistance.
