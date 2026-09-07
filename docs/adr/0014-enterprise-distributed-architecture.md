# ADR 0014: Enterprise Distributed Architecture & Microservice Decomposition

- Status: Proposed / In Review
- Date: 2026-09-06
- Decision owner: Anil Jonnala
- Trigger: Inception of Phase 4 (Enterprise Integration & Scale) following Phase 3 system qualification
- Preserves: ADR 0001 (Clean Room & Synthetic Invariants), ADR 0002 (Perception vs Action Authority Boundary), ADR 0003 (Local Deterministic Execution & Cloud Deferral), ADR 0012 (Bounded Hazard Substrate), ADR 0013 (Acceptance Protocol 3.1.0)
- Enables: P4-02 (Apache Kafka Streaming Ingress), P4-03 (Java 21 / Spring Boot Control Plane), P4-04 (Persistence Layer & Cryptographic Audit Store), P4-05 (Enterprise Connectors), P4-06 (Cloud Infrastructure & Orchestration), P4-07 (Enterprise Scale Qualification)
- Blocks: Uncoordinated microservice implementation, non-contractual network boundaries, unauthorized autonomous actions

---

## 1. Context and Problem Framing

In Phase 3, Inforsight delivered an end-to-end, single-process reference implementation of the Policy Conservation Decision Engine (Milestone `v0.3.0-decision-engine`, commit `dabc95b`). The system achieved formal `RELEASE_QUALIFIED` status by passing 100% of the System Qualification Gates (S1–S6) across 1,000 synthetic test policies and demonstrating a 2.92x Return on Conservation Spend (ROCS) in offline policy evaluation.

However, operating under ADR 0003 (*Start Local and Defer Distributed Infrastructure*), distributed microservices, multi-language runtimes, and external message brokers were intentionally deferred until the mathematical formulation, uplift optimization, and human-in-the-loop workflows were qualified.

With Phase 3 complete, Inforsight transitions to Phase 4 (**Enterprise Integration & Scale**). In an enterprise life insurance carrier environment, a monolithic single-process Python application presents critical scaling and integration bottlenecks:

1. **Compute vs. I/O Scaling Imbalance**: Model scoring (feature reconstruction, matrix operations, Platt probability calibration) is CPU-bound and requires horizontal worker scaling. Conversely, intake queue management, policyholder state tracking, and casework triage workflows are high-concurrency, I/O-bound operations.
2. **Enterprise Concurrency & JVM Ecosystem**: Enterprise Policy Administration Systems (PAS) and event streaming backbones predominantly integrate with the JVM ecosystem. High-throughput queuing, connection pooling, and low-latency concurrency benefit substantially from Java 21 Virtual Threads (Project Loom) and Spring Boot 3.
3. **Hard Authority Isolation (ADR 0002)**: ADR 0002 mandates that predictive models have *Perception Authority only* (`authorized_to_act: false`). In a distributed architecture, this boundary cannot rely on internal function convention; it must be enforced across network boundaries via strongly typed, immutable inter-service schemas.
4. **Local Deterministic Reproducibility (ADR 0003)**: Despite moving to distributed microservices, the system must remain 100% reproducible and verifiable locally without mandatory public cloud vendor lock-in.

---

## 2. Options Considered

### Option 1: Monolithic Python Service
Keep all components (streaming ingress, scoring, eligibility rules, knapsack solver, database access, and API gateway) inside a single Python/FastAPI codebase.
- *Pros*: Simple codebase; no inter-process serialization overhead; zero multi-language build complexity.
- *Cons*: Python Global Interpreter Lock (GIL) limits multi-threaded CPU concurrency; poor alignment with enterprise JVM integration standards; high blast radius where a memory spike during batch scoring could stall real-time intake queues.

### Option 2: Polyglot Distributed Microservices (Selected)
Decompose the system into specialized, loosely coupled services:
- **Inference Runtime**: Python 3.12 / FastAPI / gRPC microservice dedicated solely to model evaluation and local attribution.
- **Control Plane**: Java 21 / Spring Boot 3 microservice utilizing Virtual Threads (Project Loom) for business rule execution, knapsack uplift optimization, case management, and database persistence.
- **Streaming Gateway**: Apache Kafka event streaming backbone for bitemporal policy event ingress.
- **Persistence Store**: PostgreSQL 16 relational database with Flyway migrations and append-only SHA-256 hash-chained audit storage.
- *Pros*: Optimal runtime selection for each workload (Python for ML, Java for high-concurrency transactional orchestration); clear network boundaries; independent horizontal autoscaling (HPA); strict structural isolation of authority.
- *Cons*: Introduces network RPC latency and serialization overhead; requires multi-language build and container orchestration tooling.

### Option 3: Distributed All-Java Architecture
Retrain or export models to Java via ONNX Runtime / PMML, running the entire stack in Java.
- *Pros*: Single runtime environment; high concurrency across all components.
- *Cons*: Increases coupling between ML engineering and backend engineering; complicates feature preprocessing parity and diagnostic explainability workflows (SHAP/attribution); higher migration friction for ML researchers.

---

## 3. Decision

We adopt **Option 2: Polyglot Distributed Microservices** with strict contractual boundaries:

```text
                                 ┌─────────────────────────────────┐
                                 │     Enterprise Event Bus        │
                                 │         (Apache Kafka)          │
                                 └──────────────┬──────────────────┘
                                                │ Bitemporal events
                                                ▼
 ┌──────────────────────┐         ┌─────────────────────────────────┐
 │   Caseworker UI /    │  REST   │      Java 21 / Spring Boot 3    │
 │   Enterprise CRM     │◄───────►│          Control Plane          │
 └──────────────────────┘         │ (Rules, Knapsack, HITL, Triage) │
                                  └───────┬─────────────────┬───────┘
                                          │                 │
                                gRPC RPC  │                 │ JDBC / Flyway
                                (≤ 5ms)   ▼                 ▼
                       ┌──────────────────────┐  ┌──────────────────┐
                       │   Python / FastAPI   │  │    PostgreSQL    │
                       │   Inference Engine   │  │   & Cryptographic│
                       │ (Model Bundle Scoring│  │    Audit Store   │
                       └──────────────────────┘  └──────────────────┘
```

### 3.1 Service Boundaries & Responsibilities

1. **Inference Runtime (`services/inference/`)**:
   - **Stack**: Python 3.12, FastAPI, gRPC (`grpcio`), NumPy, frozen release bundle (`inforsight-v6-logistic-platt-20260817`).
   - **Responsibility**: Point-in-time feature transformation, logistic scoring, Platt probability calibration, and additive log-odds feature attribution.
   - **ADR 0002 Governance**: **Perception Only**. All inference responses strictly set `authorized_to_act = false` as an immutable application guarantee. The service has zero database access, zero network egress to customer channels, and zero authority to trigger outreach.

2. **Control Plane (`services/control-plane/`)**:
   - **Stack**: Java 21, Spring Boot 3, Virtual Threads (Project Loom), Spring Data JPA / JDBC.
   - **Responsibility**: Ingestion queue orchestration, point-in-time policy state reconstruction, deterministic business eligibility rules (ADR 0002 firewall), knapsack net expected utility uplift optimization, caseworker triage queue management, and HITL authorization workflows.
   - **ADR 0002 Governance**: **Sole Action Authority**. The Control Plane is the only service permitted to record caseworker decisions, transition case states to `HUMAN_REVIEWED` or `EXECUTED`, and interact with outbound CRM/telephony connectors.

3. **Streaming Gateway (`infra/kafka/`)**:
   - **Stack**: Apache Kafka (KRaft mode).
   - **Responsibility**: Decoupled bitemporal policy event streams (`policy-lifecycle-events`, `billing-payment-events`, `customer-service-events`).
   - **Governance**: Dead Letter Queue (DLQ) routing for unversioned or malformed payloads; event deduplication via `(event_id, idempotency_key)`.

4. **Persistence & Cryptographic Audit Store**:
   - **Stack**: PostgreSQL 16, Flyway schema migrations.
   - **Responsibility**: Durable case state, policy snapshots, active triage queues, and an append-only SHA-256 hash-chained cryptographic ledger (`conservation_audit_ledger`) recording all caseworker sign-offs and state transitions.

### 3.2 Inter-Service Communication Protocols

1. **Internal RPC (Control Plane $\to$ Inference Runtime)**:
   - **Protocol**: Protocol Buffers v3 over gRPC (HTTP/2 multiplexing, binary serialization).
   - **SLA**: $P_{99} \le 5.0\text{ms}$ network RPC roundtrip for single policy scoring; $P_{99} \le 50.0\text{ms}$ for batch scoring (up to 100 policies).
   - **Contract**: `proto/v1/inference_service.proto`.

2. **External Integration (Caseworker UI / CRM $\to$ Control Plane)**:
   - **Protocol**: RESTful HTTP/JSON over OpenAPI 3.1.
   - **Contract**: `api/openapi/control-plane-v1.yaml`.

### 3.3 Semantic Hardening of Authority Isolation (ADR 0002)

In Protobuf v3, default boolean fields evaluate to `false`. To prevent semantic ambiguity:
- Application code within the Inference Runtime must explicitly set `authorized_to_act = false` on every response payload.
- Deserialization in the Control Plane must verify the presence of this non-authority marker.
- Outbound enterprise connectors must fail-closed if an outreach dispatch payload lacks explicit human authorization sign-off credentials (`reviewer_id`, `review_timestamp`, `decision = APPROVED`).

---

## 4. Consequences and Tradeoffs

### Positive Consequences
- **Decoupled Autoscaling**: Inference pods scale independently based on CPU load and scoring request rate; Control Plane pods scale based on queue depth and HTTP connections.
- **High Concurrency**: Java 21 Virtual Threads permit handling $> 1,000$ concurrent casework triage workflows without thread pool exhaustion.
- **Strict Compliance**: The network boundary physically enforces ADR 0002—the inference engine cannot mutate records or dispatch communications even in the event of a bug.
- **Preserved Clean-Room Invariants**: Complete zero-dependency local development via Docker Compose preserves ADR 0003.

### Negative Consequences & Mitigations
- **Network Overhead**: Introducing gRPC adds network latency compared to in-memory function calls. *Mitigation*: Binary Protobuf serialization and persistent HTTP/2 connection pooling satisfy the sub-5ms SLA.
- **Dual-Language Parity Maintenance**: Business rules and knapsack optimization are ported to Java. *Mitigation*: Strict parity test suites using identical canonical fixtures (`fixtures/canonical_qualification_cohort.json`) guarantee 100% bit-for-bit decision and allocation concordance.
- **Operational Complexity**: Managing Kafka, PostgreSQL, and multiple container runtimes. *Mitigation*: Unified local orchestration via `infra/docker-compose.yml` ensures one-command startup and automated healthchecks.
