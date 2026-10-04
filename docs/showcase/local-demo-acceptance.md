# Local demo acceptance evidence

Recorded **2026-10-04** through the public local gateway at
**http://localhost:3000**. These are bounded fictional-demo results, separate
from historical P5 qualification and the open P4-07 enterprise-scale gate.

| Acceptance target | Result | Evidence |
| --- | --- | --- |
| Local end-to-end journey | **PASS** | 22 API/database/broker/fault-recovery checks and 17 real browser checks; all eleven displayed stages backed by persisted journal evidence. |
| GCP deployment and journey | **FAIL — Planned** | No cloud resources provisioned, deployment endpoint, or cloud run evidence. |

## Reproduce

From the repository root, with the stack and development dependencies installed:

```sh
make demo-up
PYTHONPATH=.:inference-runtime/src:simulator/src .venv/bin/python scripts/run_local_demo_acceptance.py --faults
make demo-browser-check
```

`make demo-check` invokes the same API acceptance script with `--faults` using
Make's selected Python. Setup and Node 22/Chromium installation are in the
[runbook](local-demo.md). The machine-readable records are generated at
`artifacts/local-demo/acceptance.json` and `artifacts/local-demo/browser.json`;
new executions replace those local records with their own identities/results.

## Primary API journey

- Correlation ID: `run_254f7735fdb240baaa53603b900e9568`.
- Event ID: `evt_cdd2d5d5c9fa45a791199505f37a3520`.
- Policy ID: `pol_d1325660e7e64644a939bcbfb18c897f`.
- Case ID: `case_814fca6a68a6428abfa69f1b0496617c`; final version **1**.
- Created: `2026-10-04T15:46:41.003124835Z`; completed: `2026-10-04T15:46:43.573043003Z`.
- Resume URL: http://localhost:3000/?run=run_254f7735fdb240baaa53603b900e9568 (while this local database is retained).
- Final run status: **COMPLETED**; every stage below completed on attempt **1**.

Times below are UTC on 2026-10-04. Durations describe this run's producer-side
stage work; they are not a performance benchmark or sustained-load SLO.

| Stage | Recorded completion (UTC) | Duration | Component evidence |
| --- | --- | --- | --- |
| submission | 15:46:41.003124835Z | 0 ms | Source event `evt_cdd2d5d5c9fa45a791199505f37a3520`; source, run and outbox committed together. |
| publication | 15:46:41.315460002Z | 40 ms | Broker topic `inforsight.demo.events.v1`, partition `0`, offset `14`, `acks=all`. |
| ingestion | 15:46:41.327649919Z | 3 ms | Same topic/partition/offset and event ID; inbox consumer group `inforsight-demo-journey-v1`. |
| snapshot | 15:46:41.356620794Z | 17 ms | Independent replay agrees; fixed observation cutoff; future recovery excluded; snapshot digest below. |
| score | 15:46:41.388891169Z | 21 ms | Released HTTP score `0.078781` matches independently loaded bundle; score/explanations and preprocessing identity retained. |
| rules | 15:46:41.411490544Z | 14 ms | Java per-action eligibility, reasons, and `java-eligibility/1.0.0` retained. |
| allocation | 15:46:41.429659002Z | 12 ms | Java selects `payment_method_remediation`; $3 direct cost and 360 seconds within $30 / 1,800 seconds; modeled net value $44.268. |
| case | 15:46:41.444969419Z | 7 ms | `demo_case` persisted `case_814fca6a68a6428abfa69f1b0496617c` at version 0 with upstream digests. |
| agent | 15:46:41.466347669Z | 10 ms | `DRAFT_FOR_REVIEW`; two real source citations and `fictional-local-review@1.0.0`; actual worker ID retained. |
| decision | 15:46:43.558131878Z | 1 ms | `APPROVED` by fictional reviewer; rationale/notes committed, case version 0 → 1; action authority remains false. |
| audit | 15:46:43.571379545Z | 12 ms | Transactional verification of decision prefix; final receipt separately recomputes all 21 entries, including the audit completion record. |

The snapshot ID is
`1be18b2f2c860f743990b2433499f0eb4828db8f30e5a5987983b09c53e78bcd`.
The released bundle is `inforsight-v6-logistic-platt-20260817`, version `1.0.0`,
SHA-256 `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`.
The explicit preprocessing profile is
`v6-coefficient-transform-then-bundle-zscore/1.0.0`.
The original model bundle is unchanged; the HTTP gateway now performs the
required coefficient transform before the bundle's z-score.

The agent producer was `bounded-worker-3b74c3ff9d534988aab57bd1328673dd`;
workflow `inforsight-bounded-agent/1.0.0`. It cites the submitted payment
and the independently sourced fictional safety facts, and retains
`authorized_to_act: false` and `human_review_required: true`.

The persisted SQL check returned **`1|1|1|1`**: one inbox row, one case, one
human decision, and case version 1. Replaying the submitted event through Kafka
left those counts and the audit checkpoint unchanged. A malformed broker record
was quarantined, and the next valid public event completed and verified.

The final audit receipt was verified at `2026-10-04T15:46:43.623372378Z`:

- `valid: true`, `verified_entries: 21`.
- Head hash: `a4b26163315635c7ec231baa0d78691a4ddde0a77ccab4b79e1426692659ddb2`.
- Scope: `local demo run SHA-256 chain and persisted checkpoint`.
- `externally_anchored: false`.

The verifier independently recomputed every exported chain entry, checked each
completed displayed stage against its hash-bound journal record, detected a
modified export, and confirmed PostgreSQL rejects ordinary journal updates.
The persisted audit stage contains a verification of the decision prefix
(20 entries); the final receipt verifies 21 entries after the audit completion
record itself is appended. These are different, explicit verification scopes,
not conflicting head hashes.

## Recovery and authority checks

All 22 API checks passed, including duplicate/conflicting submission, idempotent
human review, stale-review rejection, point-in-time/model replay, actual Kafka
redelivery and malformed-record quarantine, missing-evidence and legal-hold
abstention, and rejection of attempted approval of abstention. The
missing-evidence run persisted request information; the legal-hold run persisted
rejection. Neither granted execution authority.

Fault probes stopped the real inference service, observed a persisted score
failure with no score output and blocked downstream/review stages, restarted
Java while retaining the failed record, and retried the same event after
restoring inference. A separate probe paused inference and killed Java during
an in-flight score; the restarted worker resumed, and each stage committed
one completed result. No application test endpoint or fabricated success
response was used.

## Browser and focused tests

The final public UI test passed **17 checks** using Node 22.14.0:

```sh
node scripts/local_demo_browser.mjs
```

Its approved run was `run_f3dcd0b63e794998afadf529ad874acb`, created at
`2026-10-04T15:53:10.993839835Z` and completed at
`2026-10-04T15:53:14.637069962Z`. Event
`evt_77f2eb96fd244f7580c4612ec4d8c764` produced case
`case_530cadde69c84cada99239e737264e06`, version **1**. The separate final audit
receipt verified **21 entries** at `2026-10-04T15:53:14.848667837Z`, with head
`1f108103fb72eea737df9f7a75115473eef943cba8fe626c71800e1bb584fd22`.

The test compares rendered statuses with persisted responses and follows stage
input links to upstream evidence. It checks refresh/resume, lost real
submission/decision replies, slow real reads and reconnection, legal-hold
abstention with approval disabled, keyboard scenario navigation, a 390px mobile
viewport without horizontal overflow, reduced motion, and the GCP Planned label.
Six axe WCAG A/AA scans (landing, journey, dossier, review, audit, mobile) reported
**zero violations**. This is automated accessibility evidence, not a claim of
complete assistive-technology or accessibility conformance testing.

The complete browser record is `artifacts/local-demo/browser.json`, with
`axe-*.json` and desktop/mobile screenshots in the same directory. All network
fault probes operate on real service replies; no successful response is mocked.

Focused Python checks passed **74 tests** (9 demo-runtime and 65
serving/monitoring). The final Java suite discovered **46 tests**, executed
**32**, and skipped **14** opt-in legacy integration gates, with **zero
failures**:

```sh
DOCKER_API_VERSION=1.44 INFORSIGHT_RUN_DEMO_INTEGRATION=1 mvn -q -f services/control-plane/pom.xml -Dapi.version=1.44 test
```

The four focused PostgreSQL audit tests include 31 corruption cases and
verification under concurrent writes. Static infrastructure, API syntax,
frontend type/build, and documentation link/whitespace checks passed. These
component checks support the public journey evidence; they do not replace it
or claim the skipped legacy gates ran.

## Limits

- The allocator handles one fictional policy at fixed $30/1,800-second capacity.
  Modeled risk/value and deterministic effect assumptions do not establish
  real-world accuracy, causal uplift, profit, or customer outcomes.
- Reviewers are fictional labels. Approval never enables external execution;
  CRM, telephony, real policies, and authenticated licensed review are absent.
- Request information is a persisted terminal outcome, without a follow-up
  evidence/re-review loop.
- One worker and local retained volumes support the tested recovery cases.
  Multi-worker coordination, production availability, sustained-scale behavior,
  retention automation, and P4-07 qualification remain outside this pass.
- The checkpoint shares PostgreSQL's trust domain. Integrity checks are not
  externally anchored or a guarantee against privileged database rewriting.
- GCP remains Planned. Cloud design/deployment and the cloud journey require
  separate evidence; the local result grants neither acceptance.

The [proposed GCP deployment design](../architecture/gcp-demo-deployment-recommendation.md)
compares the original Cloud Run/Pub/Sub plan with Compute Engine/Kafka, including
cost, observability, teardown, reproducibility, and P4-07 needs. It provisions
no resources and does not change the GCP acceptance result.
