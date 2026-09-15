# Infrastructure

Infrastructure starts local and grows only to satisfy demonstrated needs. Cloud resources must be reproducible, observable, tagged, budget-controlled, and removable. No cloud infrastructure is provisioned by the Phase 0 scaffold.

The current `docker-compose.yml`, Java control-plane Dockerfile, and
`docker/Dockerfile.inference` are non-runnable Phase 4 topology scaffolds. They
do not represent implemented Kafka, PostgreSQL, Java, or gRPC capabilities and
must not be used as RH-06 evidence. The single canonical bounded HTTP inference
image is built from the repository root with `serving/Dockerfile` and exposes
only port 8000.
