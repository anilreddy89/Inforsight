# Zero-cost public deployment decision

**Date:** 2026-10-04. **Status:** Mac/Cloudflare preview verified and live; Oracle
deployment blocked on account access and actual Always Free capacity.
No paid resources or charge-enabling account changes are authorized.

Keep the actual Kafka/PostgreSQL/Java/Python journey. The immediate free option
is a Cloudflare Tunnel to the hardened, isolated local gateway. A static host
cannot execute this system. The preview's conditions and operator commands are
in [public-preview.md](../showcase/public-preview.md).
The [public acceptance record](../showcase/public-demo-acceptance.md) reports
22 passing HTTPS API checks and 23 passing public browser checks.

## Current Oracle eligibility

The current official Always Free allocation is **1,500 A1 OCPU-hours and 9,000
GB-hours per month**, equivalent to **2 OCPU and 12 GB RAM** for an Always Free
tenancy. Older 4-OCPU/24-GB guidance is not a safe planning assumption. Use the
tenancy's home region and a console image explicitly labeled Always Free
eligible. The allowance includes 200 GB combined boot/block storage, five
volume backups and 20 GB object storage. Capacity is not guaranteed; an
out-of-host-capacity response does not authorize a paid alternative. Idle VMs
can be reclaimed. [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)

At initial inspection, neither the OCI CLI nor `~/.oci` account configuration
was present. Therefore tenancy eligibility, home region, remaining quota,
account type and available A1 capacity are **unverified**. No launch was
attempted. The smallest next step is secure user sign-in to the Oracle Cloud
Console, selecting the existing account/home region and confirming its Always
Free allocation. Credentials must stay in the console/local credential store,
not chat. Do not upgrade to Pay As You Go or consume promotional trial credits
as a substitute for Always Free. Oracle says a credit card is not charged
unless the account is upgraded. [Free Tier account lifecycle](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)

## Compatibility and resource gate

The actual built images on this Mac are `linux/arm64`: frontend/Nginx, Java 21
control plane, Python inference, Python demo runtime, Confluent Kafka 7.6.0 and
PostgreSQL 16. This is direct image inspection, not an inference from the base
image names. The public deployment manifest records exact image IDs, model
digest and commit. A1 runs Arm containers without x86 emulation.

The public runtime caps sum to **3.375 GiB**: Kafka 1 GiB; Java 1 GiB; PostgreSQL
512 MiB; each Python runtime 384 MiB; gateway 128 MiB. The target is one
2-OCPU/12-GB A1 VM, leaving memory for Linux, Docker page cache and startup
headroom. The first cold startup of the hardened public Compose project on
2026-10-04 reached healthy state with no OOM/restarts. The sum of individual
cgroup `memory.peak` values was **889.9 MiB** (Kafka 437.7, Java 238.4,
PostgreSQL 88.5, Python 55.4 each, gateway 14.6). This is a conservative sum
of component peaks, not simultaneous host RSS, and excludes the host/build.
The local manifest records the exact images and limits.
Build images on the Mac/CI and transfer immutable image archives;
do not compile Java/Node on the small public host. The same caps apply locally
and must pass cold startup plus a real concurrent/recovery run before any VM
is considered qualified. A cap is a limit, not a measured peak. Capture actual
container peak RSS/cgroup memory during startup and qualification, and reject
an OOM/restart loop. Cloud runtime peaks remain unverified until deployment.

Do not use the two 1-GB x86 micro VMs as a replacement: each is too small for
this co-located Kafka/Java topology at its declared resource caps. A different
split architecture would require its own evidence and cannot inherit the
local qualification.

## Prepared Always Free topology and guardrails

After secure account access is available, perform read-only inventory before
creating anything: confirm the home region, account type, existing A1 CPU/RAM
usage across availability domains, boot/block storage, backups, network
resources and Always Free labels. A 31-day month at 2 OCPU/12 GB uses 1,488
OCPU-hours/8,928 GB-hours; any other A1 allocation reduces the remaining budget.

Use a dedicated compartment and one availability domain only. Proposed
resources: one `VM.Standard.A1.Flex` at 2 OCPU/12 GB, an Always Free Ubuntu Arm
image, one 50-GB boot volume and one 50-GB data volume. Keep total tenancy
usage under the verified allowance. Do not create a load balancer, NAT gateway,
paid image, paid support plan, managed database, GPU or automatic scaling.
Use the existing Compose private network and bind the gateway to loopback.

Run `cloudflared` on the host for outbound HTTPS access. The VM can be in a
public subnet with inbound rules empty, an internet gateway for outbound
traffic, and no listening public application/service ports. If a public IP is
needed for ordinary outbound connectivity, its presence does not grant inbound
access: the security list/NSG must still deny it. Administrative access should
use an expiring OCI Bastion session; do not open SSH to `0.0.0.0/0`. Confirm each
network/Bastion option is included before creation. A stable public hostname
still requires a domain already connected to Cloudflare.

Keep `/var/lib/docker` or the named-volume data under the attached persistent
data filesystem; startup must fail if the mount is absent. Use the tested cold
backup of Kafka/PostgreSQL plus signing secrets, protected on encrypted storage.
Retain at most three recent volume backups (out of the tenancy's verified five)
and a bounded off-host logical evidence export; first verify enough free
storage/request allowance remains. Never schedule backups that silently spill
into paid capacity. Restore to an isolated namespace and independently verify
the saved case/audit head before enabling ingress.

Set compartment quotas for A1 CPU and memory, zero unused compute families,
and restrict creation to the selected region/domain. Quotas are scoped per
availability domain, so a 2-core quota independently applied in several domains
does not enforce a tenancy-wide 2-core total. Verify exact quota names with the
account's service limits rather than pasting a stale policy. Use an IAM policy
that cannot create resources outside the deployment compartment. [Compute quotas](https://docs.oracle.com/en-us/iaas/Content/Quotas/Concepts/resourcequotas_topic-Compute_Quotas.htm),
[quota scope and syntax](https://docs.oracle.com/en-us/iaas/Content/Quotas/Concepts/quota_policy_syntax.htm)

Set a $1 diagnostic budget with an actual-spend alert at $0.01 and forecast
alert at $0.01 to the owner's configured address, where supported. This is an
alarm threshold, **not permission to spend $1**. Budgets are soft limits and
notifications can lag; they do not stop charges. Hard resource/identity limits
and the non-upgraded Always Free account are the primary boundary.
[Budget behavior](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm),
[budget minimum and alerts](https://docs.oracle.com/en-us/iaas/Content/Billing/Tasks/create-budget.htm)

Collect bounded health, CPU/memory, disk, broker lag, application capacity,
failed stages and audit verification errors. Avoid request bodies, cookies,
CSRF tokens and session IDs in logs. Docker rotation is capped at three 10-MB
files per service. Use included OCI host metrics; verify their current usage
allowance before enabling exports. Alarm on disk 75%, OOM/restarts and audit
failure. Low utilization can lead to free-VM reclamation; do not generate fake
load to evade that policy. Backups and reproducible recovery are necessary.

## Deployment and verification sequence

1. Save the local/public acceptance report, clean commit, model digest, Docker
   image IDs and Arm image archives. Verify archive checksums after transfer.
2. Record the account's explicit Always Free labels, available quota, region,
   shape/image IDs and $0 reviewed resource plan. If capacity is absent, stop
   here; keep the Mac preview live. Do not retry with another paid shape.
3. Create only the approved free resources. Install Docker/Compose and deploy
   the same `infra/docker-compose.public.yml`; generate new protected secrets
   locally on the VM. Enable Docker at boot and mount-before-service ordering.
4. Before starting the named tunnel, prove private ports, denied external
   actions, session ownership/CSRF/rates, persistence and healthy cold startup.
5. Run the identical public HTTPS API/browser acceptance with operator probes
   explicitly targeting this VM. Record actual topic/partition/offset, model
   digest, persisted case/version/decision and independently verified audit.
   Test reboot and restoration. A successful local run is not cloud evidence.
6. Save resource IDs and inventory, inspect cost analysis after it updates, and
   hand over the stable hostname only when this deployment's acceptance passes.

Cloud acceptance is currently **FAIL / not deployed**. A concrete authenticated
account plan can be prepared without creating resources; this document does
not contain an executable paid fallback or an automatic provisioning loop.

## Teardown

On the VM, use the same `public_demo.py tunnel-stop`, verified backup, and
`compose down --volumes` commands. Remove only this deployment's named tunnel
and DNS record. Then terminate the exact VM with boot-volume preservation
disabled, detach/delete its data volume, delete its backups/exports, and remove
the dedicated NSG/subnet/internet gateway/VCN, Bastion sessions, alarms, budget,
policies and compartment after reconciling their recorded IDs. Do not delete
shared tenancy resources. Re-list instances, all boot/block volumes and backups,
public IPs, buckets and networking in the home region, and inspect cost analysis
after reporting catches up. Stopping a VM is not teardown.

## Concrete paid fallback — not approved or created

If A1 is unavailable, keep the free Mac preview and offer a single Hetzner
**CAX21** Arm VM in Germany/Finland: 4 vCPU, 8 GB, 80 GB local NVMe. The current
monthly cap is **$12.49**, excluding VAT and IPv4. Optional automatic backups
add 20%, giving **$14.99/month** before tax. Run an outbound Cloudflare Tunnel
over included IPv6, avoiding a separate IPv4 charge; verify the chosen location
can reach Cloudflare over IPv6 before purchase. Capacity is subject to the
provider's current inventory. This alternative uses the existing Arm images
and the same acceptance gate. [Current price schedule](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/),
[CAX21 specification](https://www.hetzner.com/cloud/cost-optimized/),
[backup billing](https://docs.hetzner.com/cloud/billing/faq/)

No new domain, paid monitoring, additional volume, snapshot accumulation or
traffic overage is included. A 20% contingency makes the planning ceiling
about **$18/month before tax**, but it is not a spending authorization. Reprice
the final cart, confirm capacity and request explicit paid approval before
creating it. Delete the server and separately retained snapshots/IPs to stop
charges; turning it off does not stop server billing.
