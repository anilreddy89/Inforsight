# Inforsight Protocol Buffer Specifications

This directory contains versioned Protocol Buffers (v3) schemas defining strongly typed, low-latency inter-service RPC interfaces between Inforsight distributed microservices.

## Directory Structure

```text
proto/
├── README.md
└── v1/
    └── inference_service.proto    # Low-latency gRPC interface to BundledInferenceEngine
```

## Conventions & Standards

1. **Syntax**: All contracts use `proto3`.
2. **Versioning**: Services are version-namespaced (e.g. `package inforsight.inference.v1;` in `proto/v1/`).
3. **Naming**:
   - Messages: `CamelCase` (e.g. `PolicyScoreResponse`).
   - Fields: `snake_case` (e.g. `calibrated_probability`).
   - Services & RPCs: `CamelCase` (e.g. `ScorePolicy`).
4. **Authority Boundary Invariant (ADR 0002)**:
   - Inference service responses must explicitly include:
     ```protobuf
     bool authorized_to_act = 4;
     ```
   - In application code, this must be explicitly set to `false` to guarantee perception-only authority across network boundaries.

## Compilation

Stubs can be generated for Python and Java:

```bash
# Python stubs
python -m grpc_tools.protoc -I. --python_out=services/inference --grpc_python_out=services/inference proto/v1/inference_service.proto

# Java stubs (via protobuf-maven-plugin in services/control-plane/pom.xml)
mvn compile
```
