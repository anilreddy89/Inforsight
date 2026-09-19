# Phase 4.03 — Java 21 / Spring Boot Control Plane Microservice

P4-03 ports the deterministic control-plane responsibilities behind the
reconciled Phase 4 service boundary. It creates a Java 21 / Spring Boot 3
service that receives case-triage requests, invokes the bounded Python
inference runtime for risk scoring, applies the deterministic eligibility and
allocation contracts, and preserves explicit human authority at the decision
boundary.

| Field | Value |
| --- | --- |
| Phase | Phase 4 — Enterprise Integration & Scale |
| Milestone | `v0.4.0-enterprise-scale` (Milestone #5) |
| Status | Implementation in progress |
| Depends on | P4-01, P4-02, RH-13 `PROCEED` |
| Blocks | P4-04, P4-05 |
| Tracking issue | [#186](https://github.com/anilreddy89/Inforsight/issues/186) |
| Pull request | TBD |

## Objective

Deliver a runnable, testable control-plane service without changing the
qualified Python model behavior, ADR 0002 authority boundary, or reconciled
P4-01 wire contracts. Java becomes the orchestration and deterministic policy
layer; Python remains the bounded inference runtime until a separately
approved replacement exists.

## Scope

- Scaffold `services/control-plane/` with Java 21, Spring Boot 3, and a
  reproducible build.
- Use virtual threads for request concurrency and document the executor
  configuration and its limits.
- Port the deterministic action-eligibility rules from
  `simulator/rules/` without introducing probabilistic behavior into the Java
  layer.
- Port the net-utility/knapsack allocation behavior from
  `simulator/optimization/` with deterministic tie-breaking and integer
  economics/resource units.
- Implement the reconciled gRPC/REST client boundary to the Python
  `BundledInferenceEngine`, including identity, version, timeout, and error
  handling.
- Expose the bounded control-plane endpoints:
  `POST /api/v1/cases/triage`, `GET /api/v1/cases/{id}`, and
  `POST /api/v1/cases/{id}/decision`.
- Add bounded resilience behavior: timeout, rate limiting, retry policy only
  for explicitly retryable failures, and circuit breaking without duplicate
  decision execution.
- Add Java unit, contract, parity, concurrency, and Testcontainers-backed
  integration tests.

## Explicit non-goals

- No change to the frozen model, feature semantics, calibration, or Python
  inference artifacts.
- No autonomous action execution: Java may calculate eligibility and present a
  recommendation, but a trusted human authorization remains required.
- No PostgreSQL durability or cryptographic audit-store implementation; that is
  P4-04.
- No CRM, telephony, cloud, Kubernetes, or production identity federation;
  those belong to later increments.
- No production-readiness, customer-readiness, or distributed-performance
  claim based only on local tests.

## Acceptance checks

- [ ] Java 21 / Spring Boot 3 project builds reproducibly from a clean checkout.
- [ ] Java eligibility decisions match the canonical Python fixtures 100%,
  including fail-closed authority and safety behavior.
- [ ] Java allocation decisions match the Python reference solver bit-for-bit,
  including integer economics, capacity constraints, and deterministic ties.
- [ ] The inference client validates the reconciled request/response identity,
  version, errors, timeout behavior, and `authorized_to_act: false` boundary.
- [ ] The three control-plane endpoints expose versioned, documented request
  and response contracts with stable error mappings.
- [ ] Virtual-thread configuration handles 1,000 concurrent bounded triage
  requests in a reproducible local test without thread-pool exhaustion.
- [ ] Retry, timeout, rate-limit, and circuit-breaker tests demonstrate no
  duplicate decision execution or authority bypass.
- [ ] Testcontainers-backed integration tests pass for the service boundary.
- [ ] Focused Java checks, relevant Python parity checks, and the repository CI
  gates pass without rewriting protected historical artifacts.
- [ ] README, backlog, change tracker, roadmap, and this phase document are
  updated with issue/PR/merge evidence at closeout.

## Evidence and issue workflow

Create one implementation issue from the repository implementation template,
copying the acceptance checklist above unchanged. The issue must identify the
P4-02 merge (`#185`, `8caae8b`) as its prerequisite and must not claim that
P4-03 is complete until the implementation PR merges and the required CI
checks pass.

The implementation branch should start from updated `main` and use a stable
name such as `implementation/p4-03-java-spring-control-plane`.

## Current implementation evidence

- Issue #186 is open on branch `implementation/p4-03-java-spring-control-plane`.
- `services/control-plane/` contains a Java 21 / Spring Boot 3 Maven module,
  virtual-thread configuration, snake-case REST mapping, and actuator health
  endpoints.
- Deterministic eligibility covers missing safety evidence, legal freezes,
  policy viability, channel consent, cooling-off, grace-period, and tenure
  gates.
- Integer-capacity allocation uses bounded exact dynamic programming with
  deterministic tie-breaking rather than a greedy approximation.
- The bounded inference adapter, triage, case retrieval, and human decision
  endpoints are covered by Spring MockMvc tests. Decision authority remains
  false until an explicit human decision is recorded.
- `make p4-03-check` and `mvn -f services/control-plane/pom.xml test` pass
  locally with 5 tests.
- The real inference transport/parity fixtures, resilience policies,
  1,000-concurrent-request gate, and Testcontainers service integration are
  still open and must be completed before this phase can be marked complete.
