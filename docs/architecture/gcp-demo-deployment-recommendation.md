# Proposed decision: deploy the verified demo on Compute Engine with Kafka

**Status:** Proposed; no cloud implementation or provisioning performed.  
**Assessment date:** 2026-10-04 (America/New_York).  
**Decision owner:** Anil Jonnala.  
**GCP deployment and journey acceptance:** **FAIL — Planned, not deployed.**

Recommend one scheduled, bounded Compute Engine VM for the first cloud copy of
the verified local journey. Preserve Kafka, the Java control plane, HTTP model
inference, Python evidence/agent service, PostgreSQL and the React gateway.
Budget approximately **$20/month for 60 running hours**, or **$74/month for
730 running hours**, including the allowances and 20% headroom below. This is
an estimate, not a quote or a spend ceiling. Select a project, domain, operating
window and spending authorization before implementing or deploying this plan.

## Context and constraints

The current [Compose topology](../../infra/docker-compose.yml) and
[journey contract](../../api/openapi/demo-journey-v1.yaml) now have local API and
browser acceptance evidence. The visitor submits one fictional event; an
outbox publishes it to Kafka; a durable inbox starts reconstruction, released
HTTP model scoring, Java rules/allocation, case persistence, bounded agent
output, human review and audit verification. The worker is a long-running
Kafka consumer. The local audit journal and database are the source of progress;
cloud logs must never substitute for those records.

[P6-01 / issue #212](https://github.com/anilreddy89/Inforsight/issues/212), read
without modification on the assessment date, proposes Cloud Run, Pub/Sub,
Cloud Storage, BigQuery, a later Vertex AI training run, logging and IaC. Its
initial scope expressly excludes resource provisioning and P4-07 qualification.
The accepted [ADR 0014](../adr/0014-enterprise-distributed-architecture.md)
instead names Kafka and preserves local reproducibility. This recommendation
is a proposed change to the first Phase 6 deployment increment; it does not
close #212 or silently replace its acceptance checks.

One read-only `docker stats --no-stream` sample on this date totaled roughly
952 MiB across the six demo containers: Kafka 509.5, Java 272.9, inference 56.3,
PostgreSQL 55.1, demo runtime 46.2 and frontend 11.9 MiB. This excludes the
developer host and unrelated containers. It supports evaluating an 8 GiB VM;
it establishes neither startup peak memory nor cloud capacity. Measure both
before exposing the endpoint.

## Options considered

| Dimension | Cloud Run + Pub/Sub | Compute Engine + Kafka |
| --- | --- | --- |
| Current implementation fit | New Pub/Sub publisher/consumer, delivery receipt contract and request-driven orchestration are required. | Runs the current services and Kafka outbox/inbox semantics with the smallest application change. |
| Event semantics | Persist message identity, publish acknowledgement, subscription/delivery identity, ordering key, attempts and quarantine; acknowledge only after durable acceptance. Pub/Sub has no Kafka partition/offset receipt. | Preserves topic, partition, offset, broker acknowledgement, duplicate handling and quarantine already exercised locally. |
| Execution lifecycle | Request-billed services can scale to zero, but the current background consumer cannot rely on CPU after an HTTP response. Pub/Sub push must process durably within the request, or hand off to separately scheduled durable work. | One continuously running consumer during the demo window; existing recovery runs after VM/service restart. |
| Persistence | Requires durable PostgreSQL outside ephemeral service instances, for example Cloud SQL, with connection budgets and migrations. | PostgreSQL and Kafka reside on persistent disk; host operations and backup/restore become our responsibility. |
| Cost | Low idle application-compute cost after integration. A running Cloud SQL instance, retained data and observability still cost money. | Predictable hourly VM cost and storage floor. Scheduling reduces compute spend; one VM bounds horizontal expansion. |
| Observability | Managed request/instance metrics and service IAM help; trace propagation and durable stage evidence still need implementation. | Ops Agent, application correlation fields and broker/DB health collection need explicit setup. Container-to-container timing resembles local operation. |
| Reproducibility | Image reuse is possible, but emulator results cannot prove managed delivery, IAM, cold starts or Cloud SQL behavior. | Same immutable images and model digest; versioned cloud Compose override. VM architecture and storage/network remain a new qualification environment. |
| Availability and maintenance | Managed services reduce host maintenance and offer regional features. Cold starts and multiple resource/IAM boundaries add integration work. | Single host and zone can fail. No HA claim; patching, TLS renewal, disk capacity and restoration are operator duties. |
| P4-07 fit | Replacing Kafka changes the declared qualification topology and needs an explicit contract decision. | Retains the bus, but this small shared VM still does not meet the dedicated qualification requirements. |

Cloud Run also offers worker pools, so Kafka consumption is technically possible
there. They remain active and billed while running, require explicit instance
scaling, and still need a broker and durable database. That hybrid adds moving
parts without supplying the original scale-to-zero benefit. These lifecycle
assessments follow Google's [Cloud Run container contract](https://docs.cloud.google.com/run/docs/container-contract).

Cloud Run/Pub/Sub remains a reasonable later managed-service demonstration if
learning that platform becomes the priority. Its adapter must reuse the same
domain reconstruction/scoring/rules/journal contract, label the actual bus in
the UI, and pass a separate cloud acceptance run. It cannot claim that a
Kafka-qualified path was merely redeployed.

## Recommended bounded topology

Use one regular Linux `e2-standard-2` VM (2 vCPU, 8 GiB) in `us-central1-a`, with
a 20 GiB balanced boot disk and a separate 40 GiB balanced data disk. Build
`linux/amd64` images in CI, pin image digests and the released model digest,
and pull them from a regional Artifact Registry repository. Do not compile on
the small runtime VM or rely on developer-machine image architecture.

Serve the UI and same-origin API through a TLS reverse proxy using one static
IPv4 and an existing portfolio subdomain. No paid load balancer, Cloud NAT,
GKE, managed Kafka, BigQuery, Vertex training or new domain purchase is included
in this first deployment. Only HTTPS is public; allow HTTP solely for redirect
and certificate validation if the selected TLS method needs it. Keep Kafka,
PostgreSQL, Python and direct Java ports private. Use IAP/OS Login for operator
access, without public SSH. The reviewed cloud override must not inherit
public database or broker port mappings.

Use a dedicated demo project and VM service account, with repository read,
selected secret access, log/metric write and a dedicated evidence-bucket write
scope. No owner/editor roles, service-account key files, CRM credentials or
telephony credentials belong on the host. Fetch secrets into protected runtime
files. Restrict container egress to required internal services; allow host
egress only for the approved registry, Google APIs, patching and TLS operations.
Keep both authority/execution flags false and retain server-side enforcement.

Before internet exposure, add signed fictional visitor sessions, per-session
run ownership, bounded create/review rates and a total queue/run cap. Correlation
IDs are lookup identities, not authorization credentials. The current local
reviewer identity is a fictional label; it must not be described as deployed
authentication. Target at most 5 concurrent visitors, 500 retained runs and
10,000 API requests/month initially. Return an honest capacity response when
the bound is reached.

Persist PostgreSQL and Kafka state under the data mount, with startup blocked
if the expected disk is absent. Use graceful service stop plus the tested
restart recovery. Retain daily database exports and audit checkpoints in a
private regional Standard bucket for seven days, keeping all backups/evidence
under 5 GiB. Test restoration into a fresh isolated namespace and independently
verify its receipts. A checkpoint stored off-host improves separation; it is
not proof against an administrator who can rewrite every copy. Do not claim
external notarization or immutable retention unless those controls are added.

## Cost model and comparison

All figures are USD public on-demand estimates for Iowa, assessed 2026-10-04.
Use 730 hours per month and no committed-use, Spot, trial-credit or promotional
discount. Storage is retained for the full month in both columns. The scheduled
case means 20 booked windows of 3 hours, including startup, not an always
available public endpoint. The rest of the portfolio must state those windows.

| Item and calculation | Scheduled: 60 h | Always running: 730 h |
| --- | ---: | ---: |
| VM: hours × $0.06701142 | $4.02 | $48.92 |
| Balanced persistent disk: 60 GiB × approximately $0.10/GiB-month | $6.00 | $6.00 |
| Static IPv4 attached all month: 730 × $0.005 | $3.65 | $3.65 |
| Artifact Registry: at most 4 GiB × approximately $0.10/GiB-month | $0.40 | $0.40 |
| Logging/monitoring allowance: 2 GiB logs plus sparse bounded metrics | $1.50 | $1.50 |
| Standard backup/evidence storage: 5 GiB × approximately $0.02/GiB-month | $0.10 | $0.10 |
| Storage operations: under 1,000 Class A and 10,000 Class B operations | $0.01 | $0.01 |
| Secrets allowance: 2 active versions plus 2,000 accesses | $0.13 | $0.13 |
| Internet egress allowance: 5 GiB to North America/Europe × $0.12 | $0.60 | $0.60 |
| **Subtotal** | **$16.41** | **$61.31** |
| **With 20% headroom** | **$19.69** | **$73.57** |

Rate sources: [VM](https://cloud.google.com/products/compute/pricing/general-purpose),
[persistent disks](https://cloud.google.com/compute/disks-image-pricing),
[IPv4 and network](https://cloud.google.com/vpc/network-pricing),
[Artifact Registry](https://cloud.google.com/artifact-registry/pricing),
[observability](https://cloud.google.com/products/observability/pricing),
[Cloud Storage](https://cloud.google.com/storage/pricing), and
[Secret Manager](https://cloud.google.com/secret-manager/pricing).

The table conservatively charges retained artifacts, logs, secrets and egress
before their applicable free allowances; those allowances can be shared or
already consumed. Logs cost $0.50/GiB beyond the first 50 GiB/project/month.
Keep custom byte-priced metrics below 1 MiB/month, with no correlation ID as a
metric label; use the included platform metrics and sparse log-based alerts.
The allowance also covers modest query usage. High-volume tracing, synthetic
monitor functions, managed vulnerability scanning and Cloud Build are outside
this estimate; build/scan in existing CI. Reprice before enabling them.

Static IPv4 remains billed while attached to a stopped VM. After detachment
an unreleased static address costs $0.01/hour. Stopping also leaves disks,
artifacts, logs and backups billable. Ephemeral IPv4 would save idle address
cost, but would require DNS changes after restart; retain a static address for
the first visitor demo. Existing DNS hosting is assumed. Taxes, support plans,
domain registration and destinations with higher egress rates are excluded.

For a fair Cloud Run comparison, an illustrative request-driven deployment
using 30,000 active vCPU-seconds, 30,000 GiB-seconds and 100,000 requests/month
costs about **$0.84 gross application compute/requests**, before free allowances,
at $0.000024/vCPU-second, $0.0000025/GiB-second and $0.40/million requests.
This must sum work across all services, including polling and cold starts.
[Cloud Run pricing](https://cloud.google.com/run/pricing?hl=en)

A Cloud SQL `db-g1-small` database at $0.035/hour adds **$25.55/month** in
instance cost alone; it is a shared CPU option without the Cloud SQL SLA.
Database storage, backups, connectivity, artifacts, logs and egress are extra.
This is a cost floor, not an equivalent complete configuration.
[Cloud SQL pricing](https://cloud.google.com/sql/pricing)
Pub/Sub's first 10 GiB/month of basic publish-plus-subscribe throughput per
billing account is free, then $40/TiB; retained message storage has its own
charge. [Pub/Sub pricing](https://cloud.google.com/pubsub/pricing)
Thus a properly integrated serverless design could be cheaper than the
always-running VM. The recommendation favors implementation continuity and
the scheduled demonstration cost, rather than claiming universal VM savings.

## Observability and operating limits

Add structured component logs carrying correlation ID, event ID, stage,
attempt, service/image version and error code. Record queue age/lag, outbox
retries, quarantined messages, stage failures, model digest mismatch, database
availability, disk usage and audit verification failures. Sample routine HTTP
poll logs; never log secret values or full draft/source payloads. Keep debug
logging off and log retention at 30 days or less. Store run exports separately
from diagnostic logs.

Monitor CPU/memory/disk and HTTPS health. Alert on audit failure immediately,
disk over 75%, dependency outage and work stuck beyond its retry bound. Suppress
expected downtime alerts outside booked windows. A recorded processing state
must remain visible during a slow stage; monitoring does not synthesize
completion. Retain deployment identity and a dashboard link with each cloud
acceptance report.

Use a $25 monthly project budget for the scheduled pilot, with 50%, 80%, 100%
actual-spend and forecast alerts. An always-on change would require a fresh
$90 planning budget and review of measured usage. Budget alerts are delayed
notifications, **not hard caps**; the VM count, runtime limit, request/queue
limits, retention and teardown provide the practical bounds.
[Budget behavior](https://docs.cloud.google.com/billing/docs/how-to/budgets)

## Schedule, TTL and teardown plan

The future IaC must label every resource with the deployment ID and expiry.
Choose a seven-day pilot expiry; end the start/stop schedule at that timestamp.
An expiry label alone performs no deletion. A deployment-owner teardown job
must destroy resources at expiry, with a reminder and independent inventory
check if the job fails. Keep Terraform state and the final receipt outside the
disposable project resources.

The commands below are **unexecuted templates**, not installed automation.
Set `INFORSIGHT_GCP_PROJECT`, `INFORSIGHT_GCP_ZONE`, `INFORSIGHT_GCP_REGION`,
`INFORSIGHT_GCP_VM`, and `INFORSIGHT_GCP_EXPIRY` from the reviewed deployment
manifest; expiry must be an explicit RFC 3339 timestamp. Stop an existing VM
before changing its run-time limit:

```sh
gcloud compute instances stop "$INFORSIGHT_GCP_VM" --project="$INFORSIGHT_GCP_PROJECT" --zone="$INFORSIGHT_GCP_ZONE"
gcloud compute instances set-scheduling "$INFORSIGHT_GCP_VM" --project="$INFORSIGHT_GCP_PROJECT" --zone="$INFORSIGHT_GCP_ZONE" --max-run-duration=3h --instance-termination-action=STOP
gcloud compute resource-policies create instance-schedule inforsight-demo-hours --project="$INFORSIGHT_GCP_PROJECT" --region="$INFORSIGHT_GCP_REGION" --vm-start-schedule='0 10 * * 1-5' --vm-stop-schedule='0 13 * * 1-5' --timezone='America/New_York' --end-date="$INFORSIGHT_GCP_EXPIRY"
gcloud compute instances add-resource-policies "$INFORSIGHT_GCP_VM" --project="$INFORSIGHT_GCP_PROJECT" --zone="$INFORSIGHT_GCP_ZONE" --resource-policies=inforsight-demo-hours
```

Validate the chosen schedule/runtime-limit combination during deployment.
Schedules can have timing lag, so include warm-up in the public window and
confirm actual `TERMINATED` state after stop. The runtime limit is an additional
stop bound, not removal of billable storage.
[Instance schedules](https://docs.cloud.google.com/compute/docs/instances/schedule-instance-start-stop),
[VM runtime limits](https://docs.cloud.google.com/compute/docs/instances/limit-vm-runtime).

At expiry: disable new submissions, let durable in-flight work settle, export
and verify the final audit receipts, retain the chosen local evidence copy,
then stop and delete only resources from the deployment manifest. Prefer the
reviewed Terraform destroy plan once that module exists. Manual fallback
commands for the dedicated deployment are:

```sh
gcloud compute instances stop "$INFORSIGHT_GCP_VM" --project="$INFORSIGHT_GCP_PROJECT" --zone="$INFORSIGHT_GCP_ZONE"
gcloud compute instances delete "$INFORSIGHT_GCP_VM" --project="$INFORSIGHT_GCP_PROJECT" --zone="$INFORSIGHT_GCP_ZONE" --delete-disks=all
gcloud compute addresses delete inforsight-demo-ip --project="$INFORSIGHT_GCP_PROJECT" --region="$INFORSIGHT_GCP_REGION"
gcloud compute resource-policies delete inforsight-demo-hours --project="$INFORSIGHT_GCP_PROJECT" --region="$INFORSIGHT_GCP_REGION"
gcloud artifacts repositories delete inforsight-demo --project="$INFORSIGHT_GCP_PROJECT" --location="$INFORSIGHT_GCP_REGION"
gcloud storage rm --recursive "gs://$INFORSIGHT_GCP_EVIDENCE_BUCKET"
```

Also remove the exact deployment's secret versions, firewall rules, subnet,
network, service account/IAM bindings, DNS record, custom log bucket, uptime
checks and alerts. Disable bucket soft deletion in the disposable pilot plan
or explicitly account for its retained objects and charges. Do not enable
locked retention on a throwaway backup bucket. Do not delete shared portfolio
DNS zones, billing budgets or unrelated project resources.

After teardown, save the output of these read-only checks and reconcile it
against the deployment manifest; a surviving disk, snapshot, reserved address,
repository or bucket means teardown is incomplete:

```sh
gcloud compute instances list --project="$INFORSIGHT_GCP_PROJECT"
gcloud compute disks list --project="$INFORSIGHT_GCP_PROJECT"
gcloud compute snapshots list --project="$INFORSIGHT_GCP_PROJECT"
gcloud compute addresses list --project="$INFORSIGHT_GCP_PROJECT"
gcloud compute resource-policies list --project="$INFORSIGHT_GCP_PROJECT"
gcloud artifacts repositories list --project="$INFORSIGHT_GCP_PROJECT" --location=all
gcloud storage buckets list --project="$INFORSIGHT_GCP_PROJECT"
gcloud secrets list --project="$INFORSIGHT_GCP_PROJECT"
gcloud asset search-all-resources --scope="projects/$INFORSIGHT_GCP_PROJECT" --query='labels.deployment=inforsight-demo'
```

Resource inventory, rather than a zero current bill, is the immediate teardown
check. Review billing again after reporting catches up, including retained or
soft-deleted storage. No cloud command in this document was run for this task.

## Deployment acceptance and P4-07 separation

Before marking GCP available, implement and offline-validate Terraform and
the cloud Compose override; bind their digests, commit, image manifests,
model digest, region/zone, resources, IAM and TLS endpoint in a deployment
record. Test the scheduled stop/start, restoration, resource bounds, session
isolation, private service ports and disabled external actions.

Then run the same complete public UI/API journey against HTTPS: record actual
Kafka publication and consumption, point-in-time artifacts, real HTTP score,
Java decisions, persisted case, bounded agent output, human decision and
independent audit verification. Repeat duplicate/poison ingress, dependency
failure and restart probes in the isolated cloud environment. The current
acceptance runner's Docker fault/SQL helpers target the local Compose project;
add an explicit remote operator transport before using those probes in cloud.
Changing only `--base-url` does not constitute remote fault qualification.
Publish cloud run IDs and receipts before enabling an environment selector.

[P4-07](../../Documents/phase_docs/phase-04-07-enterprise-scale-qualification-and-release.md)
remains separate and open. It requires a frozen 100,000-policy/200,000-event
workload, at least 5,000 events/second with no loss, P99 at most 50 ms at the
declared persistent scored-case boundary, and E3–E6 authority, tamper,
recovery and parity evidence. This one-VM, one-worker portfolio demo is not
that workload or topology. Dedicated Linux qualification must isolate Kafka
and PostgreSQL, fix resources and runtime versions, freeze the arrival and
measurement contract, and repeat the full gates. Neither cloud option earns
qualification credit merely by deploying successfully. Budget that separate
benchmark after selecting and freezing its resources.

## Consequences and next actions

The first cloud journey retains the local event evidence and minimizes new
application behavior. It accepts scheduled availability, one host/zone,
manual operating responsibility and a persistent-storage cost floor.

- [ ] Record acceptance or amendment of this proposed deployment decision and reconcile P6-01's Cloud Run-specific checks.
- [ ] Implement offline-validatable IaC, cloud override, IAM, session isolation, retention and stop/teardown automation.
- [ ] Select the dedicated project, domain, seven-day pilot expiry and spend authorization.
- [ ] Deploy, prove the cloud journey and recovery, restore a backup, and verify teardown in the pilot.
- [ ] Keep Pub/Sub integration, BigQuery export, Vertex training and dedicated P4-07 qualification as explicit later increments.

Until those deployment and run records exist, **GCP remains Planned and its
deployment/journey acceptance remains FAIL**. This document changes no cloud
resources and makes no cloud readiness or enterprise-scale claim.
