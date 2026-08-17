# ADR 0003: Start locally and defer distributed infrastructure

- Status: Accepted
- Date: 2026-08-16

## Context

The target architecture includes multiple languages, event streaming, cloud services, and bounded assistants. Introducing them before validating the fictional lifecycle and observation model would add cost and obscure the first falsifiable claim.

## Decision

Begin with local, standard-library Python for contracts, simulation, validation, and state reconstruction. Add databases, Java services, Kafka, cloud resources, and agent frameworks only when a passed acceptance gate creates a concrete need.

## Consequences

- The first milestone remains fast, inexpensive, and easy to inspect.
- Interfaces must be designed so later services can adopt them without changing event meaning.
- Architecture components are roadmap commitments, not claims of current implementation.
