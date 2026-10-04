# Local distributed visitor demo

The visitor demo connects one fictional policy event to actual Kafka,
point-in-time projection, released-model HTTP scoring, Java rules/allocation,
PostgreSQL case persistence, a bounded agent, a fictional human decision, and a
verified audit receipt. **GCP is Planned. No cloud resources are required or
provisioned.**

The recorded local acceptance is **PASS**, with component evidence in the
[acceptance record](local-demo-acceptance.md). GCP remains **FAIL — Planned**.
The implementation and test commands are described here; the authoritative
result for a particular execution is the generated
`artifacts/local-demo/acceptance.json`. A service health response, a UI build,
or the historical P5 qualification is not a substitute for that run evidence.

## Start and open

Requirements for the UI are Docker with Compose and GNU Make. Run from the
repository root:

```sh
make demo-up
docker compose -f infra/docker-compose.yml ps
curl --fail http://localhost:3000/api/v1/demo/scenarios
```

Open **http://localhost:3000** after the services start. Select **Run a fictional
case**, keep the late-payment scenario, and choose **Start this case**. The
journey uses persisted service results, so very fast stages can appear together
when the next poll completes. Nothing waits merely to provide an animation.

The gateway proxies only the new demo API. Host service ports are loopback-only;
Python projection/valuation/agent is private to the Docker network. The named
Compose project is `inforsight-demo`, with dedicated PostgreSQL and Kafka
volumes. `INFORSIGHT_DEMO_PORT` defaults to 3000 and
`INFORSIGHT_POSTGRES_PORT` to 5433. If changing the UI port, pass its URL to the
API acceptance script with `--base-url`.

## Scenarios and safe input

| UI scenario | API scenario ID | Evidence boundary |
| --- | --- | --- |
| A payment falls behind | `late-payment` | Explicit fictional safety facts; computed score, eligibility, allocation, and draft |
| Safety evidence is missing | `missing-safety-evidence` | Legal-hold evidence is absent, remains unknown, and restricts eligibility |
| The agent must abstain | `agent-abstention` | A known legal hold restricts eligible action and leads to abstention |

The observation cutoff is fixed at **2026-09-25T12:00:00Z**, independent of the
current processing time. The source history deliberately includes a later
recovery; it must be excluded from snapshot facts/features. Each submission
gets new fictional policy/event identities. Input overrides may contain only:

```json
{"premium_amount_cents": 12500, "delay_days": 15}
```

Premium must be an integer from 1,000 to 100,000 cents; delay must be an integer
from 1 to 45 days. Unknown fields are rejected. Scores, allowed actions,
procedures, safety flags, observation cutoffs, external destinations, and
credentials cannot be supplied as overrides. Leave `{}` for defaults.

## Navigate and resume

The run URL is `http://localhost:3000/?run=<correlation_id>`. Copy it or use the
landing view's resume control. Refresh reads the same persisted run; it does
not submit another event. The browser retains a pending submission's exact
input and idempotency key in session storage so an interrupted response can be
retried without duplicating the accepted run.

- **Live journey:** eleven stage records with status, producer, attempts,
  timestamps, duration, input/output references, and expandable evidence.
- **Case dossier:** observation facts and unknowns, source lineage, released
  score and directional explanations, rule reasons, modeled valuation,
  allocation, and cited agent output.
- **Human review:** approve a supported draft, reject, or request information;
  enter a rationale and record a fictional decision against the current case
  version. An abstention cannot be approved.
- **Audit trail:** explicitly verify the stored chain and inspect event IDs,
  case versions, producer identities, hashes, and reviewer evidence.
- **Architecture:** component highlighting follows recorded processing states.
  GCP appears as **Planned**, with no environment selector.

Request more information is implemented as a persisted decision and terminal
outcome for this run. A follow-up evidence-submission/re-review cycle is not
implemented. The reviewer ID is a fictional label, not an authenticated real
person. Even human approval retains `authorized_to_act: false` and
`external_execution_enabled: false`.

## Run acceptance

The API verifier also reconstructs the projection and reloads the released
model independently on the host. Use a Python 3.11+ development environment
with simulator and serving dependencies installed. For a fresh environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e simulator -r serving/requirements.txt
make demo-check
```

`make demo-check` runs the exact command:

```sh
.venv/bin/python scripts/run_local_demo_acceptance.py --faults
```

Make chooses `.venv/bin/python` when present, otherwise `python3`; override
`PYTHON` if needed. The `--faults` probes stop/pause inference and restart/kill
only the dedicated demo control-plane container. They recover services in
cleanup paths. Avoid running this qualification while someone is reviewing a
case interactively. For a non-disruptive journey-only replay:

```sh
.venv/bin/python scripts/run_local_demo_acceptance.py
```

The report contains separate `local_result` and `gcp_result`, the primary run
ID, all tested run IDs, pre-review and final artifacts, stage evidence, and the
verified audit entries. It is written to `artifacts/local-demo/acceptance.json`
even if a check fails. Capture the terminal output as well: it contains the
failing assertion or service error. A missing or failed report is not a pass.

The acceptance test checks:

1. Identical submission replay and conflicting idempotency-key reuse.
2. Actual Kafka acknowledgement matching the persisted consumer topic,
   partition, offset, and submitted event ID.
3. Independently reconstructed point-in-time facts/features, with future
   evidence excluded.
4. HTTP score equality to the independently loaded released model, including
   the frozen coefficient preprocessing transform and model digest.
5. Java rule results and at most one eligible allocation within recorded
   money/personnel capacity.
6. Persisted case and a real bounded planner result with trusted source and
   procedure citations; the agent remains without action authority.
7. A persisted human decision, idempotent replay, and rejection of stale
   review; missing-evidence and legal-hold abstentions cannot be approved.
8. Every displayed completed stage matching hash-bound journal evidence,
   independent chain recomputation, changed-export detection, and PostgreSQL
   rejection of ordinary journal updates.
9. With `--faults`: a real inference outage leaves no score artifact, blocks
   downstream work and review, survives Java restart, then retries the same
   event; an in-flight Java crash resumes without duplicate committed stages.

Install Node **22** for browser checks (Docker builds already use their own
Node builder). Install the checked-in frontend dependencies and Chromium:

```sh
npm --prefix frontend ci
./frontend/node_modules/.bin/playwright install chromium
make demo-browser-check
```

The lockfile pins Playwright `1.55.1` and `@axe-core/playwright` `4.10.2`.
Use `DEMO_URL=http://localhost:<port> make demo-browser-check` for a changed UI
port, or `NODE=/path/to/node make demo-browser-check` to select Node 22.

The browser script runs against the real gateway, not mocked API responses.
Browser interaction evidence supplements the API/database verifier; neither a
screenshot nor green UI badges alone prove the journey. See the frontend
[README](../../frontend/README.md) for Vite development and polling behavior.

It writes `artifacts/local-demo/browser.json`, desktop/mobile screenshots, and
`axe-*.json` reports. It checks keyboard scenario selection, a real UI approval
and audit, six automated WCAG A/AA screens, mobile overflow, reduced motion,
refresh/resume, interrupted submission/decision responses, slow real polling
responses, reconnection, legal-hold abstention, and the GCP Planned label.
Network probes interrupt or delay actual service replies; they never fabricate
successful payloads. These automated checks do not establish full accessibility
conformance or replace assistive-technology review.

## Exact component and trust boundaries

| Component | Recorded evidence and limits |
| --- | --- |
| Kafka | `inforsight.demo.events.v1`, group `inforsight-demo-journey-v1`; persisted publication and ingestion metadata; envelope bound to stored source |
| Projection | `fictional-dual-profile-projection/1.0.0`; reconciles legacy policy and V6 payment histories, reconstructs safety evidence, retains lineage and excluded source IDs |
| Released model | `inforsight-v6-logistic-platt-20260817`, version `1.0.0`, SHA-256 `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656` |
| Preprocessing | `v6-coefficient-transform-then-bundle-zscore/1.0.0`; raw V6 features transform before the bundle's own z-score, fixing the gateway's previous raw/coefficient-space mismatch |
| Java rules | `java-eligibility/1.0.0`; all action results and reasons retained |
| Valuation/allocation | Existing fictional RH-04 modeled effects/economics; `java-multiple-choice-knapsack/1.1.0`, one policy, at most one action, $30 and 1,800 seconds |
| Persisted case | Dedicated `demo_case`, bound to snapshot/score/rules/allocation digests; versioned human decision in `demo_decision` |
| Bounded agent | `inforsight-bounded-agent/1.0.0`; deterministic planner in the private Python adapter, actual worker ID and input digest, source citations, `fictional-local-review@1.0.0` procedure |
| Audit | `demo_journal` SHA-256 chain plus `demo_checkpoint` in the same PostgreSQL trust domain; displayed artifacts and current case version also verified |

The planner's internal fixed confidence gate is not measured confidence; the
API labels its result “Not estimated; deterministic evidence gates.” Explanatory
risk drivers are directional model contributions, not causal findings. Modeled
expected value is not realized profit or premium revenue.

The original bundle bytes are unchanged. The serving seam now explicitly
transforms raw features into the coefficient-space inputs expected by that
bundle. Acceptance independently checks the resulting score; historical scoring
runs are not silently rewritten or presented as proof of the corrected path.

## Failure, retry, and shutdown

Polling is serial: a new read starts after the previous one completes. Normal
reads are 1.5 seconds apart; transport failures back off to 10 seconds and show
a stale connection notice. Background tabs suspend reads. These intervals
schedule reads only and never advance a workflow stage.

A processing failure is committed with an error code; dependent stages remain
blocked. Restore the dependency, then choose **Retry**. Failed attempts stay in
the journal and completed artifacts are retained. A control-plane restart
resumes durable `PROCESSING` runs from their first unfinished stage. It does not
automatically retry runs already marked `FAILED`.

The implementation has one local Java orchestration worker. Outbox/inbox
persistence and broker redelivery provide bounded recovery; repeated read-only
HTTP calls and duplicate broker records can occur around crashes. This is not
distributed exactly-once execution, multi-worker claiming, a sustained-load
qualification, or a production SLO. There is no automatic per-run retention
scheduler or public shared-demo authentication/rate-limit system.

```sh
make demo-down
# Later, retain existing runs:
make demo-up
```

To delete all fictional runs and broker state in this named project:

```sh
make demo-reset
make demo-up
```

`demo-reset` deletes the project's PostgreSQL and Kafka volumes; saved run URLs
will no longer resolve. It is a local operator command, not a visitor API.

## Remaining qualification

P4-07's 100,000-policy persistent distributed qualification remains open. This
single-policy slice does not close it. The checkpoint is not externally
anchored, and database superuser compromise is outside the trust guarantee.
No real policies, demographic fairness conclusions, causal effects, customer
outcomes, credentials, or external execution are part of this demonstration.

GCP has **no deployment or cloud journey evidence** and remains **Planned**.
Cloud deployment must be separately approved and verified after local
acceptance; the UI must not expose an environment selector before that exists.
The original P5 documents and Streamlit workflow retain their historical scope.

See the [proposed GCP design comparison](../architecture/gcp-demo-deployment-recommendation.md)
for Cloud Run/Pub/Sub versus Compute Engine/Kafka, a concrete cost estimate,
observability and teardown requirements, and the separate P4-07 boundary.
