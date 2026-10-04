# Public visitor demo acceptance

**Verified 2026-10-04.** Public preview:
[Open Inforsight](https://combined-scheduling-hand-etc.trycloudflare.com).
This temporary hostname works while the Mac, Docker stack and tunnel remain
running. Its current value is also in the operator state directory's
`public-url.txt`; restarting a Quick Tunnel can replace the hostname.

| Acceptance boundary | Result | Evidence |
| --- | --- | --- |
| Local distributed journey | **PASS** | 22 baseline API checks, 17 baseline browser checks; hardened private preflight also passed 22 API and 23 browser checks |
| Public HTTPS journey | **PASS** | Final build passed 22 API/broker/database/fault checks and 23 browser checks |
| Oracle Always Free deployment/journey | **FAIL — not deployed** | Arm and local memory checks pass; secure account access, tenancy eligibility and actual regional capacity remain unverified |
| GCP deployment/journey | **FAIL — Planned** | No GCP resources or deployment/run evidence; provisioning was not authorized |

The API and Chromium clients used the public HTTPS hostname through Cloudflare,
not the loopback URL. TLS certificate verification was enabled. The external
HTTP response identified `Server: cloudflare` and ray
`a455f87e1ceb2290-IAD`. These clients ran on the Mac; this is not a claim of
independent geographic availability or a production SLA.

## Deployment identity and preservation

Runtime, public contracts, Docker configuration and qualification scripts are
committed as **`278c274616a2ad95faa37277d0223e0c0fc958bd`** on
`codex/public-demo-preview`. Documentation was finalized afterward. No runtime
source changed between this build and the final public tests.

The existing 55-file working tree was archived before hardening in ignored
`artifacts/public-demo/baseline/working-tree-before-hardening.tar.gz` with a
source-hash inventory. Commit `00cbf15` preserves that implementation;
`d4d4422` fixes Nginx DNS resolution after Java container recreation. The
original `inforsight-demo` project and its data were preserved.

Released model: `inforsight-v6-logistic-platt-20260817`, version `1.0.0`.
SHA-256: **`7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`**.
The test independently loads that bundle and reproduces the HTTP score.
It does not use the hash adapter or Streamlit workflow.

[Machine-readable evidence](public-demo-evidence.json) records exact image IDs,
runtime platform digests, architectures, tests and report hashes. The live
operator manifest is `~/.local/share/inforsight-public/deployment-manifest.json`.
All six images are Arm64. Cold startup reached healthy state without OOM or
restart; the sum of independent component memory peaks was 889.9 MiB, excluding
host/build overhead. The declared runtime memory caps total 3.375 GiB.

## One complete public API journey

Run **`run_0c28959ff0fd4974a85db491a8e5d682`**;
source event **`evt_50680a5b6e794eb6992c2c9492383cb9`**.
All 11 stages completed with persisted producer, timestamps, references and
hash-bound evidence. Submission was recorded at `17:44:58.722Z`; the audit stage
completed at `17:45:02.081Z` on 2026-10-04.

| Stage | Actual component and evidence |
| --- | --- |
| Submission | Java persisted the fictional late-payment source, run and outbox; idempotent replay returned the same run |
| Publication | Kafka `acks=all`, topic `inforsight.demo.events.v1`, partition `0`, offset `19` |
| Ingestion | Java consumer group `inforsight-demo-journey-v1`; durable inbox matches offset `19` and envelope SHA-256 `c84f78cc0b18259476bae7777c308f9cfe2f150ceaa9f2905fc706652c39170e` |
| Point-in-time snapshot | Python projection, snapshot `65df1e6c20eef859bc113bfa6929e09ac335e616868126ce1d7871fd1657b4d6`; independent replay matches and future evidence is excluded |
| Model score | Released Python HTTP inference; calibrated modeled probability `0.078781`; independent bundle evaluation matches |
| Eligibility | Java rule results and reasons persisted; allocated action is in the eligible set |
| Allocation | Java selects `payment_method_remediation` within the recorded one-policy money/personnel capacity |
| Case | PostgreSQL `case_9add64d5cfba404cb0646d346d29ce93`; exactly one case and one inbox record |
| Agent | Python `inforsight-bounded-agent/1.0.0`, `DRAFT_FOR_REVIEW`; cites payment/safety source IDs and `fictional-local-review@1.0.0`; authority remains false |
| Human decision | `APPROVED`, persisted at `17:45:02.058Z`, case version `0 → 1`; exactly one decision; external execution remains false |
| Audit | Independent SHA-256 reconstruction and persisted checkpoint agree: **21 entries**, head `9fd04ea21958c6c12c5f9b1ae9bd42aaf39d862e79f78089cfbd14c0d012eb33` |

Full evidence: `artifacts/public-demo/public-api.json`. This is a local
hash chain/checkpoint; it is **not externally anchored**. A test run ID is not
an access credential: another browser cannot open its private evidence.

## Actual public browser journey

Run **`run_1f79d548a4c34576863d588a4503ae65`**, event
`evt_6fa6260e0c24498db5d4a0d4f51c9c6a`, case
`case_b5115e342b5e42a68a63e74ef07a9d0e`, version `1`.
A real UI submission reached the reviewer console; clicking approval persisted
`APPROVED` at `2026-10-04T17:47:04.105812045Z`. Refresh retained the same session
and run. Audit verified **21 entries**, head
`a5a317288a3a264030efb4c89fa1d0edaf9fc87b58310d9088d9d8316e1cdcf7`.

The 23 browser checks cover signed Secure/HttpOnly/SameSite cookies, copied-run
access denied in a second visitor context, read/audit/retry/decision ownership,
missing-CSRF and cross-origin rejection, legacy-route denial, actual 429 and
24-second Retry-After recovery, persistent status fidelity, lost submission
and decision responses, refresh, slow/disconnected responses, abstention and
human authority. Six accessibility scans report zero violations; keyboard,
mobile overflow and reduced motion checks pass. No browser console errors.
Desktop landing/audit and mobile journey screenshots were visually inspected.

Full report and screenshots: `artifacts/public-demo/browser-public/`.

## Security, faults, retention and recovery

Java reports: **41 passed, 14 legacy opt-in checks skipped, zero failures**
across the full suite and final focused reruns. All **nine** public security
integration tests run against real isolated PostgreSQL and pass. They cover
signatures/expiry, every ownership route, canonical paths, CSRF/Origin,
persistent session/global quotas, atomic concurrency/retained-run admission,
retention and integrity preservation. The final regression reserves capacity
for an attempted publication whose broker delivery remains unresolved, even
when its acknowledgement was interrupted; retry reuses that reservation.

The HTTPS API qualification also stops real inference, persists a failed stage
and blocked downstream work, restarts Java, retries the same event, kills Java
with inference in flight and proves automatic recovery without duplicate
completed stages. Real duplicate Kafka delivery is deduplicated; malformed
broker input is quarantined and the following valid event completes. Missing
safety evidence and legal hold both produce real abstention and block approval.
Missing evidence records an audited request for more information; legal hold
records a rejection. Modified audit exports are detected.

A cold backup of PostgreSQL, Kafka and matching secrets restored into a fresh,
isolated project. Nine cases, nine inbox/decision/checkpoint records and 193
journal entries matched exactly; all nine chains independently verified.
A new restored journey `run_214dab7f50df42e0b748ddbd2fc0d31f` then passed all
11 stages and human approval, with 21 verified entries and head
`78c8e224019818ac1b0cd204c914d11cadc6bf75ca03284d85e233dc53032ef3`.

Only in that disposable restored project, aging one completed fixture proved
automatic whole-run retention: a verified deletion receipt survived, all other
nine chains stayed valid, and safe broker maintenance advanced the earliest
offset from `0` to `3`, below the retained/consumed safety boundaries. The
disposable project and its copied secrets were removed. The source preview and
private backup were preserved. The operator's ten-minute maintenance LaunchAgent
is loaded and its first execution exited `0`.

Restore/retention evidence and backup paths:
`artifacts/public-demo/backup-restore.json`. The first backup/restore used the
hardened build before the final capacity-only SQL fix; a separate final accepted
snapshot preserves the final images and public qualification runs. No schema
change separates these snapshots.

## Exact qualification commands

Run from the repository root with Docker running. Fault checks intentionally
interrupt the selected preview services; schedule them before sharing ingress
or during an announced maintenance window.

```sh
PYTHONPATH=.:inference-runtime/src:simulator/src .venv/bin/python scripts/run_local_demo_acceptance.py --base-url https://combined-scheduling-hand-etc.trycloudflare.com --compose-file infra/docker-compose.public.yml --public --faults --output artifacts/public-demo/public-api.json
PATH=/Users/anil/.nvm/versions/node/v22.14.0/bin:$PATH DEMO_URL=https://combined-scheduling-hand-etc.trycloudflare.com DEMO_OUTPUT=artifacts/public-demo/browser-public DEMO_BROWSER_LIMITS=1 node scripts/local_demo_browser.mjs
DOCKER_API_VERSION=1.44 INFORSIGHT_RUN_DEMO_INTEGRATION=1 mvn -q -f services/control-plane/pom.xml -Dapi.version=1.44 test
DOCKER_API_VERSION=1.44 INFORSIGHT_RUN_DEMO_INTEGRATION=1 mvn -q -f services/control-plane/pom.xml -Dapi.version=1.44 -Dtest=DemoPublicAccessIntegrationTest test
python3 scripts/public_demo.py validate
python3 scripts/public_demo.py manifest
```

The private preflight uses the same API command with
`--base-url http://localhost:3100 --public --loopback-public`; this explicit
operator exception does not weaken the server's Secure cookie configuration.
The preserved baseline used the default localhost:3000 project and the same
API script with `--faults`; evidence is in `artifacts/public-demo/baseline/`.

## Handover and remaining deployment gates

Topology: public HTTPS → Cloudflare → outbound Mac tunnel → loopback gateway
`127.0.0.1:3100` → private Docker Java/Kafka/PostgreSQL/Python services. Only
static UI, minimal gateway health and session-protected demo APIs are publicly
reachable. No public reset, actuator, model diagnostics, database or broker
port is exposed. Fictional run/evidence/review/audit data requires its owning
session. External actions are disabled server-side and backend containers have
no internet route.

Provisioned vendor hosting cost: **$0/month**, with no paid cloud resources or
charge-enabling account changes. This is not a utility measurement or cloud
invoice audit; existing electricity/internet costs are excluded. Mac sleep,
power/network loss, stopped Docker or a stopped tunnel takes the preview
offline. Quick Tunnel restart changes the hostname and therefore browser-cookie
scope; a copied correlation ID cannot restore access at a different hostname.

[Deployment/update/backup/restore/teardown commands](public-preview.md) and the
[current zero-cost hosting assessment](../architecture/zero-cost-public-deployment.md)
are complete. A stable Cloudflare name needs secure sign-in and an existing
connected domain. Oracle needs secure account access to verify Always Free
eligibility and real capacity before provisioning. No secrets should be sent in
chat. The documented paid fallback is unapproved and unprovisioned. GCP remains
Planned; this preview does not complete P4-07 enterprise-scale qualification.
