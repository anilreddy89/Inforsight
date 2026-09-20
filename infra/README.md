# Infrastructure

Infrastructure starts local and grows only to satisfy demonstrated needs. Cloud resources must be reproducible, observable, tagged, budget-controlled, and removable. No cloud infrastructure is provisioned by the Phase 0 scaffold.

P4-06 provides runnable local evidence artifacts:

- `docker-compose.yml` starts the bounded Kafka, PostgreSQL, inference, and
  Java control-plane topology with health checks. Its credentials are local
  development values only.
- `docker/Dockerfile.control-plane` builds the Spring Boot service through a
  Maven builder stage and runs the JRE image as a non-root user.
- `docker/Dockerfile.inference` builds the bounded HTTP inference runtime
  through a Python builder stage and runs it as a non-root user.
- `helm/inforsight` renders the control-plane, inference, PostgreSQL, service,
  probe, resource, and HPA configuration. It is a deployment configuration
  baseline, not proof of a live cluster, cloud readiness, or production SLO.

Run the static gate with `make p4-06-check`. If Docker is available, validate
the Compose file with `docker compose -f infra/docker-compose.yml config` and
build the images from the repository root.
