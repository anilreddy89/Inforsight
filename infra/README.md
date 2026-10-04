# Local demo infrastructure

`make demo-up` builds and starts the **inforsight-demo** Docker Compose project.
Open **http://localhost:3000** for the visitor UI. GCP remains **Planned**; these
files do not establish a live cloud deployment or P4-07 enterprise-scale pass.

| Service | Runtime | Host address | Responsibility |
| --- | --- | --- | --- |
| `frontend` | React/TypeScript assets, nginx | `127.0.0.1:3000` | Same-origin visitor UI and allowlisted demo API proxy |
| `control-plane` | Java 21 / Spring Boot | `127.0.0.1:8080` | Durable run/outbox/inbox, Kafka worker, rules, allocation, human review, journal verification |
| `kafka` | `confluentinc/cp-kafka:7.6.0`, KRaft | `127.0.0.1:9092` | Actual publication and consumption on `inforsight.demo.events.v1` |
| `inference-runtime` | Python / FastAPI | `127.0.0.1:8000` | Verified released-model HTTP score and explanation; no gRPC endpoint |
| `demo-runtime` | Python / FastAPI | Private `demo-runtime:8001` | Read-only fictional source construction, point-in-time projection, valuation, bounded agent |
| `postgres` | `postgres:16-alpine` | `127.0.0.1:5433` | Demo artifacts, case versions, decisions, append-only journal, local checkpoint |

The internal broker address is `kafka:29092`; PostgreSQL uses internal port
5432. Override `INFORSIGHT_DEMO_PORT` or `INFORSIGHT_POSTGRES_PORT` for host port
conflicts. Credentials in Compose are local development values. Services bind
to loopback on the host, and the read-only adapter has no database or external
execution tools. The gateway rejects legacy `/api/` routes.

Compose explicitly enables the persistence profile and new demo journey,
selects HTTP inference, and disables external execution. The older general
streaming consumer is not the new demo worker; its default setting does not
describe the actual demo topic consumer. The HTTP journey validates the exact
released bundle and never falls back to bounded hash scoring.

### Historical P5-04 qualification

The older `make p5-04-demo-check` harness supplies a policy ID without feature
snapshots. Run it with the explicit review-only overlay:

```sh
docker compose -f infra/docker-compose.yml -f infra/docker-compose.p5-04.yml up --build -d --wait
make p5-04-demo-check
docker compose -f infra/docker-compose.yml -f infra/docker-compose.p5-04.yml down
```

This overlay selects bounded test scoring and disables the visitor journey.
It qualifies persisted abstention, human rejection and audit only; it is not
released-model or Kafka journey evidence. Never apply it to the public
deployment. The default local and public configurations retain HTTP scoring;
use `make demo-check` to qualify the complete visitor journey.

## Commands

```sh
make demo-up
docker compose -f infra/docker-compose.yml ps
curl --fail http://localhost:3000/api/v1/demo/scenarios
curl --fail http://localhost:8080/actuator/health
curl --fail http://localhost:8000/health
make demo-check
make demo-browser-check
make demo-down
```

`demo-up` returns after starting containers; allow health/startup to complete
before opening a case. `demo-check` deliberately interrupts dedicated demo
containers to test failure and restart recovery, so use it when no interactive
review is in progress. Python and browser-check dependencies are documented in
the [runbook](../docs/showcase/local-demo.md).

`make demo-down` preserves named PostgreSQL and Kafka volumes. Use
`make demo-reset` to stop the dedicated project **and delete its fictional
volumes**, then `make demo-up` to start clean. Existing run URLs will no longer
resolve after reset. There is no public reset endpoint and no per-run retention
or cleanup scheduler. Export evidence before deleting storage.

## Durability and scope

Flyway migrations V6/V7 create isolated `demo_*` tables and ingress quarantine.
Each stage completion is committed with its run projection and journal entry;
case insertion and human review use the same transaction boundary. Kafka and
PostgreSQL retain state across service restarts. A single Java worker resumes
persisted unfinished work, skips committed stages, and deduplicates ingestion.
Broker redelivery and repeated read-only HTTP calls remain possible: this is
not distributed exactly-once execution or a multi-worker deployment.

The journal hashes exact stored payload bytes and compares a checkpoint in the
same PostgreSQL trust domain. A trigger rejects normal row updates/deletes.
This detects the tested corruption modes; it is not externally anchored,
KMS-backed, or resistant to a database administrator rewriting all evidence.

## Existing deployment artifacts

The [Phase 4.06 architecture record](../Documents/phase_docs/phase-04-06-cloud-infrastructure-helm-and-orchestration.md)
and architecture poster remain historical packaging evidence. The Helm chart
is a configuration baseline; it does not yet deploy the full visitor journey.
`make p4-06-check` validates infrastructure structure but is not the end-to-end
acceptance test. `make demo-check` writes the current local acceptance result
and component evidence to `artifacts/local-demo/acceptance.json`.

No cloud resources are provisioned by this local workflow. A cloud design must
separately qualify deployment, telemetry, cost/teardown controls, and the same
full journey before GCP can become an available environment.

The [GCP deployment recommendation](../docs/architecture/gcp-demo-deployment-recommendation.md)
compares Cloud Run/Pub/Sub and Compute Engine/Kafka with cost, observability,
teardown, and P4-07 qualification requirements. It is a proposal, not deployed
infrastructure.
