# Phase 4.07 — Enterprise Scale Qualification and Release

P4-07 is the final Phase 4 qualification gate. It evaluates the bounded
distributed deployment baseline under a reproducible 100,000-policy synthetic
workload, verifies the six predeclared Enterprise Performance Gates, and
prepares the `v0.4.0-enterprise-scale` release only if the evidence passes.
This phase does not turn synthetic qualification into a production, customer,
regulatory, or autonomous-execution claim.

| Field | Value |
| --- | --- |
| Phase | Phase 4 — Enterprise Integration & Scale |
| Milestone | `v0.4.0-enterprise-scale` (Milestone #5) |
| Status | In progress; cloud-environment qualification remains pending through [issue #195](https://github.com/anilreddy89/Inforsight/issues/195) |
| Depends on | P4-06, ADR 0002 human authority boundary |
| Blocks | `v0.4.0-enterprise-scale` release, Milestone #5 closeout, and enterprise-scale claims; not the start of Phase 5 cloud-environment work |
| Tracking issue | [#195](https://github.com/anilreddy89/Inforsight/issues/195) |
| Pull request | [#196](https://github.com/anilreddy89/Inforsight/pull/196) |
| Branch | `implementation/p4-07-enterprise-scale-qualification` |

## Objective

Establish a reproducible, fail-closed qualification protocol for the declared
Kafka, Java control plane, Python inference, PostgreSQL, and audit-ledger
topology. The result must bind workload identity, topology/configuration,
runtime versions, gate thresholds, and cryptographic evidence before any
release decision is made.

## Enterprise Performance Gates

| Gate | Requirement | Failure condition |
| --- | --- | --- |
| E1 — Streaming ingestion throughput | At least 5,000 events/sec with zero drops | Throughput below threshold or any unaccounted event |
| E2 — End-to-end latency | P99 ingress-to-scored-case latency at or below 50 ms | P99 exceeds threshold or timing evidence is incomplete |
| E3 — Authority isolation | 100% rejection of unapproved external action | Any autonomous or unapproved dispatch succeeds |
| E4 — Audit immutability | 100% detection of declared ledger tampering | Any mutation, deletion, reorder, or fork is missed |
| E5 — Fault tolerance and recovery | Zero data loss across simulated worker failure/restart | Any event or audit record is lost or unreconciled |
| E6 — Reproducibility and parity | Bit-for-bit Java/Python decision and allocation parity | Any authorized fixture diverges or identity binding is incomplete |

Gate thresholds, workload dimensions, sampling rules, warm-up policy, timeout
semantics, and failure dispositions must be frozen before qualification runs.

### Local validation profile (non-authoritative)

The E2 threshold remains a production qualification requirement and is not
relaxed by local development results. Docker Desktop on a developer Mac is
useful for regression detection, but it is not a controlled enterprise
benchmark environment. Local runs may therefore use this separate diagnostic
profile:

| Local band | Interpretation |
| --- | --- |
| P99 scored-case <= 250 ms | Acceptable local development baseline |
| P99 scored-case 250–400 ms | Warning; investigate runtime or topology variance |
| P99 scored-case > 400 ms | Local regression or invalid environment; do not use as release evidence |

The local profile requires healthy services, explicit warm-up, five repeated
100-event runs, median and worst-run reporting, zero dropped events, no
consumer failures, and complete audit-tail verification. It cannot mark E2
passed, authorize the release, or replace a controlled Linux qualification
run. The 50 ms production threshold remains unchanged.

## Scope

- Define the qualification contract and exact workload/configuration identity.
- Build or harden the distributed stress runner for 100,000 fictional
  synthetic policies and the declared event streams.
- Exercise throughput, latency, authority, tamper, restart/recovery, and
  cross-runtime parity scenarios.
- Produce a cryptographic qualification manifest and human-readable report.
- Update release notes, limitation language, and milestone status only after a
  governed decision.

## Explicit non-goals

- No final holdout access, real policyholder data, credentials, or proprietary
  material.
- No live CRM, telephony, payment, or other external action execution.
- No claim of production cloud readiness, multi-region disaster recovery,
  regulatory approval, or real-customer SLO compliance.
- No demographic fairness claim without a separately governed real-world data
  program.
- No `v0.4.0-enterprise-scale` tag or Milestone #5 closeout before all six
  gates pass and required CI/review checks are complete.

## Acceptance checks

- [x] E1–E6 are frozen with exact thresholds, workload, and failure semantics.
- [x] The 100,000-policy workload is reproducible and cryptographically bound
  to its configuration and runtime versions.
- [ ] The formal arrival profile, topology identity, resource allocation, and
  scored-case persistence boundary are versioned and frozen before acceptance.
- [ ] Throughput and latency evidence is complete, bounded, and reproducible.
- [ ] Authority isolation and audit tamper scenarios fail closed.
- [ ] Worker restart/recovery evidence accounts for every event and audit row.
- [ ] Java/Python decision and allocation parity is bit-for-bit for the declared
  authorized fixtures.
- [ ] Qualification report and cryptographic manifest reproduce byte-for-byte.
- [ ] `make check`, focused qualification checks, and required PR CI pass.
- [ ] Release notes and limitation statements accurately describe the result.
- [ ] The release tag and milestone closeout occur only after a passing decision.

## Evidence plan

- Frozen qualification contract and gate matrix.
- Workload/configuration manifest and cryptographic identity.
- Distributed runner output, gate report, and tamper/recovery evidence.
- Java/Python parity fixtures and exact comparison report.
- Full repository and CI results.
- Release notes and final decision record, including any failed or deferred
  gate and the resulting claim boundary.

## Next qualification step

One set of five warmed 100-event runs passed the **local** 50 ms diagnostic
(median 18.590 ms; worst 25.946 ms), but a later repeat failed (worst 193.314
ms, dominated by 185.913 ms ingress-to-broker-ack p99). One frozen-identity
200,000-event run reached 46.480 ms at 6,251.60 scored events/sec; other
full-load trials exceeded 50 ms. See the
[detailed topology findings](../../docs/experiments/p4-07-latency-topology-findings.md)
for the workload, counterexamples, measurement boundary, and limitations.

The next P4-07 task is a controlled **dedicated** Linux qualification run
outside a shared developer VM. Before it, the arrival profile, resource
allocation, and scored-case persistence boundary need a versioned decision.
The run must fix JVM/Python worker counts, isolate Kafka and PostgreSQL,
record stable runtime versions, and report repeated full-cardinality latency,
throughput, event accounting, audit-tail verification, and E3–E6 evidence.

The controlled run may either prove E2 at P99 <= 50 ms or provide bounded
evidence for a formal target review. It must not silently substitute the local
250 ms development band for the production gate.

## Sequencing decision — 2026-09-25

P4-07 remains **open, not passed** while a production-matched cloud
qualification environment is built in a later increment. Phase 5 work needed
to provision and validate that environment may proceed without treating P4-07
as complete. This is a dependency change for starting that work, not a waiver
of E1–E6 or permission to release `v0.4.0-enterprise-scale`. Other Phase 5
initiatives still require their own prerequisites and claim reviews.

The present local topology is not sufficient to decide the production 50 ms
gate. Local hardware or virtualization may contribute to variance, but the
observed broker-acknowledgement spike and the in-memory case/deferred-audit
measurement boundary prevent attributing the gap solely to hardware. The
[latency/topology findings](../../docs/experiments/p4-07-latency-topology-findings.md)
retain the passing and failing local runs without promoting either to release
evidence.

When the later cloud environment is available, resume this same P4-07 issue
and qualification contract. Before the run, version and freeze the actual
topology, resource allocation, runtime versions, arrival profile, warm-up,
measurement boundary, and persistent scored-case behavior. Re-run the frozen
100,000-policy/200,000-event workload with complete event and audit accounting,
repeatable E1 throughput and E2 p99 latency, and bound E3–E6 evidence. Record
the result and a governed pass/fail decision. A failing gate leaves P4-07 and
the release blocked; any change to a threshold or contract needs a separately
reviewed amendment, not a retrospective reinterpretation of local evidence.

## Implementation evidence

### Qualification findings log

| Evidence run | Command or harness | Result | Qualification meaning |
| --- | --- | --- | --- |
| Contract preflight | `make p4-07-check` | 10 Python contract tests and 9 deterministic Java tests passed | Contract, authority, audit-hash, streaming, and parity seams are structurally guarded; this is not distributed qualification. |
| E1 bounded ingress, historical shared topic | `make p4-07-integration-check` with external Compose Kafka | Previously reported 200,000 accepted and 15,552.36 events/sec | The test reused a retained topic; later rerun showed historical records can contaminate accepted counts. Do not use this figure as authoritative E1 evidence; the test now creates unique topics. |
| E1 isolated-topic ingress and restart | `make p4-07-integration-check` against local Compose Kafka, per-run topics, explicit producer acknowledgements | 200,000/200,000 broker-acknowledged and accepted at 151,382.95 events/sec; separate 4,000/4,000 restart probe; all three integration tests passed | Valid bounded broker-to-consumer evidence after test isolation. The synthetic publisher uses bounded retries without idempotence to avoid local broker sequence faults; this is not the frozen end-to-end producer/topology or full E1–E6 report. |
| E2 HTTP component | `make p4-07-latency-integration-check` | 100 warmed samples; p99 4.748 ms | HTTP inference-to-case component floor exceeded; Kafka ingress queueing was excluded. |
| E3 authority | deterministic connector preflight tests | External execution remains disabled and `authorized_to_act` remains false | Local authority isolation evidence only; no live connector dispatch was attempted. |
| E4 persistence | `make p4-07-postgres-integration-check` | Tamper probe detected mutation; Flyway and chained verification passed in clean Compose state | Persistence probe passed; final run still needs clean-run identity and bound evidence. |
| E5 recovery | Kafka restart test plus PostgreSQL repository rehydration test | 4,000 Kafka events recovered exactly; committed case and audit hash rehydrated | Bounded recovery probes passed; one combined distributed recovery report remains open. |
| E6 parity | Java eligibility/allocation fixture checks | 3 parity/allocation fixture tests passed | Declared fixtures match; full production-path parity evidence remains open. |
| Combined topology | `make p4-07-combined-integration-check` | 100/100 measured events processed; hybrid reruns observed p99 between 212.747 ms and 1,557.413 ms | Capability binding succeeded; E2 remains above 50 ms, while checkpoint-bounded tail verification isolates prior local data. |
| Minimal response optimization | Same combined harness with `/v1/score/minimal` and four inference workers | 100/100 measured events processed; p99 546.152 ms | Diagnostic response serialization was removed from the control-plane path and the contract is covered by a serving test; E2 remains above 50 ms. |
| Minimal batch optimization | Same combined harness with `/v1/score/minimal/batch`, one request per Kafka poll, and Kafka `fetch.max.wait.ms=25` | 100/100 measured events processed; p99 648.437 ms | The batch contract and Kafka path are operational, but this rerun did not improve p99; no performance credit is claimed and E2 remains open. |
| Vectorized minimal scoring | Same combined harness after replacing per-record explanation scoring with vectorized minimal scoring | 100/100 measured events processed; p99 779.079 ms; inference batch 369.158 ms; case/audit 162.961 ms | The optimized code path is exercised and parity tests pass, but this run was slower; runtime variance remains material and E2 remains open. |
| Pooled transactional audit | Same combined harness with Hikari pooling and one transaction around the ledger append | 100/100 measured events processed; p99 540.976 ms; inference batch 220.549 ms; case/audit 122.675 ms | Latest run improved over the prior vectorized run, but remains above 50 ms; E2 is still open. |
| Four-partition consumer path and bounded polling | Four Kafka partitions/consumers, Hikari pooling, serialized audit transaction scope, and 5 ms Kafka fetch/poll waits | 100/100 measured events processed; audit-tail verification passed; p99 167.133 ms; inference batch 79.398 ms; case/audit 34.117 ms | Best valid result at that stage; queueing and audit-chain correctness improved, but E2 remained above 50 ms. |
| Asynchronous scored-case/audit split | Qualification-only single ordered audit writer; scored-case completion is measured before audit drain, with the full audit suffix verified before test completion | 100/100 measured events processed; scored-case p99 184.695 ms; audit-tail verification passed; case/audit 46.667 ms | Improves the explicitly measured E2 boundary versus the prior 469.785 ms run, but remains above 50 ms. This does not change P4-04 production ACID semantics. |
| Controlled Linux local profile | Five repeated warm runs on OrbStack Linux (12 CPUs, ~8 GB RAM), one inference worker, isolated services | Median p99 95.243 ms; worst p99 112.806 ms; all runs 100/100 | Local validation band passed and confirmed a large Docker Desktop scheduling effect; production E2 remains open. |
| Controlled Linux worker comparison | Same five-run profile with four inference workers | Median p99 104.645 ms; worst p99 128.632 ms; all runs 100/100 | Four workers were slower and more variable; the one-worker topology remains the local baseline. |
| Linux-network 50 ms diagnostic | `make p4-07-linux-latency-check`; five full-path warmed 100-event runs | Per-run p99 16.727, 18.590, 18.756, 25.946, and 17.786 ms; median 18.590 ms; worst 25.946 ms; all audit tails verified | Passes an opt-in **local** 50 ms diagnostic, not production E2 or release qualification. |
| Linux-network diagnostic repeat | Same command after isolated-topic Kafka integration | Per-run p99 18.032, 29.898, 19.112, 18.248, and 193.314 ms; worst ingress-to-ack p99 185.913 ms | Strict local 50 ms diagnostic failed on repetition; the earlier passing set is not a stable result. |
| Frozen 200,000-event candidate, paced 100/16 ms | One Linux-network run with frozen event digest, one Kafka consumer/inference worker, and deferred audit | 6,251.60 scored events/sec; scored-case p99 46.480 ms; all events and audit tail verified | One local numerical E1/E2 pass, but not repeatable/formal or on persistent scored-case path. Other 200,000-event trials observed 79.732 ms at the same feed with timed ID construction, 66.701 ms at 100/19 ms, and 444.620 ms with smaller polls. |
| Standard Java test suite | `mvn -q -f services/control-plane/pom.xml test` with local test socket/attach access | Passed; opt-in distributed integration scenarios remain separate | Regression check only, not formal E1–E6 evidence. |

The local Docker results in this phase are diagnostic only. Observed scored-case
values between approximately 183 ms and 470 ms demonstrate environment and
topology variance, not a production SLO. A controlled Linux run with reserved
CPU, fixed worker counts, isolated Kafka/PostgreSQL, and repeated-run
distribution is required before deciding whether the remaining gap is
environmental, architectural, or both.

The first OrbStack Linux profile materially reduced the local variance but
remained above 50 ms. Moving Java into the same Linux network, completing
warm-up through inference/audit, and tuning one-consumer fetch/poll batching
subsequently produced the local sub-50 ms observations recorded above. Worker
multiplication and CPU pinning were not credited as improvements. The one
full-cardinality passing run does not override the counterexamples or pass
the production E2 gate.

The evidence above is intentionally separated by run. It must not be merged
into a passing E1–E6 report until one declared run binds the exact workload,
topology identity, measurement window, event accounting, and all six gate
metrics. Component passes do not compensate for the combined E2 failure.

- `make p4-07-check` passes with 10 Python contract tests and 9 focused Java
  authority, audit, streaming, parity, and allocation tests.
- The dependency-free preflight freezes the 100,000-policy/200,000-event
  workload and E1–E6 gate inventory.
- Stable manifest SHA-256: `00c7af00458fcd9cefc69864523eac984b125ed70d7640cb60b8bbc7c7499228`.
- Missing or non-numeric runtime measurements produce `stop` with
  `insufficient_evidence`; even a synthetic all-gates pass does not set
  `release_authorized` to true.
- Runtime measurements must bind a run ID, distributed measurement source,
  topology identity, exact workload digest and event count, zero drops,
  positive measurement window, and authority/tamper/restart/parity probe
  counts.
- Runtime evidence must also prove the capabilities needed for an end-to-end
  claim: Kafka ingress, a control-plane consumer, inference HTTP, PostgreSQL
  audit, restart/replay, and parity fixtures. The bounded consumer seam now
  satisfies the consumer capability, but the remaining end-to-end capabilities
  and E1–E6 gates remain open.
- A disabled-by-default Java Kafka consumer seam is now implemented with
  allowlisted topics, envelope validation, event-key binding, idempotency
  deduplication, and commit-after-handler semantics. Enabling it in a
  qualification topology remains a separate integration step.
- The opt-in `make p4-07-integration-check` is wired to a real Testcontainers
  Kafka broker and an explicit external-bootstrap path. Testcontainers could
  not use the current Docker Desktop API metadata, but the same consumer test
  passed against the healthy Compose Kafka broker at `localhost:9092`: the
  governed envelope was consumed and its duplicate replay was deduplicated.
- The original external-Kafka test reused a retained topic, so its earlier
  200,000-event/15,552.36 events/sec observation is no longer treated as
  authoritative: a later rerun consumed historical records and failed exact
  restart accounting. The test now creates a unique topic for every scenario,
  checks broker acknowledgements, and has a bounded producer timeout. After
  resolving local broker leader/producer-sequence faults in the **synthetic
  test publisher only**, the full integration suite passed with 200,000/200,000
  events at 151,382.95 events/sec and a separate exact 4,000-event restart.
  This is still only broker-to-consumer evidence; inference, PostgreSQL
  audit, latency, authority, tamper, restart, and parity must be bound for
  final E1–E6 qualification.
- The same external-broker harness restarted the consumer with the same Kafka
  group after a bounded 4,000-event workload. The two consumer instances
  accounted for exactly 4,000 accepted events with no loss; this is bounded
  Kafka restart/replay evidence, not yet the complete persistence-backed E5
  qualification report.
- The opt-in `make p4-07-postgres-integration-check` now exercises Compose
  PostgreSQL directly. It passed Flyway validation, detected a tampered audit
  payload through the chained ledger verifier, and rehydrated a committed
  case plus its audit hash after repository recreation. These are bounded E4/E5
  persistence probes; they do not yet constitute the single distributed run
  required by the final qualification report.
- The opt-in `make p4-07-latency-integration-check` measured 100 warmed HTTP
  inference-to-case samples against the healthy Compose inference runtime. The
  observed p99 was 4.748 ms, below the frozen 50 ms floor. This is bounded
  HTTP component evidence only; Kafka ingress-to-case timing is still required
  before E2 can be marked complete.
- The combined opt-in topology smoke bound Kafka ingress, HTTP inference, case
  creation, and PostgreSQL audit in one run. It processed 101/101 events and
  verified the resulting audit chain in the initial clean run, but observed p99
  ingress-to-audit latency of 3,790.833 ms. This is a recorded E2 failure, not
  a qualification pass; the serial consumer/audit path requires performance
  work before the 50 ms end-to-end floor can be reconsidered.
- An audit append optimization now uses PostgreSQL `INSERT ... RETURNING` to
  return the committed ledger sequence directly, removing a redundant lookup
  per event while preserving parent-hash locking and append-only semantics.
  The optimized rerun processed 101/101 events and measured 3,273.151 ms p99,
  an observed improvement of 517.682 ms (13.65%), but it still failed the
  50 ms E2 floor. The rerun also exposed that persistent local test data can
  make whole-ledger verification fail after prior qualification attempts;
  clean-run isolation or an explicit checkpoint-bounded verifier is required
  before using the combined run as final evidence.
- A second optimization added a virtual-thread batch handler seam and an
  ordered multi-row PostgreSQL audit insert. Inference work now runs
  concurrently per Kafka poll while audit entries are chained and committed
  in order. The hybrid smoke processed all 100 measured events, reduced the
  combined test wall time in the best run to about 3.9 seconds, and produced
  observed p99 values from 212.747 ms to 1,557.413 ms across reruns. The
  variance itself is qualification evidence: the path is not yet stable, and
  every observed p99 remains above the 50 ms E2 floor.
- The inference image now exposes `INFORSIGHT_INFERENCE_WORKERS` explicitly.
  A four-worker Compose run measured 642.293 ms p99 and an eight-worker run
  measured 660.538 ms p99. The lack of improvement from 4 to 8 workers shows
  that Python worker count alone is not the controlling bottleneck; the
  default remains one worker until a topology-level capacity plan is declared.
- The control-plane path now uses a dedicated `/v1/score/minimal` response
  profile containing only the decision metadata required for case creation,
  bundle identity, and the human-review authority boundary. The endpoint has
  a strict serving contract test. With four inference workers, the latest
  combined run measured 546.152 ms p99, an improvement over the earlier
  642.293 ms four-worker full-response run, but still more than ten times the
  50 ms E2 floor. This optimization reduces payload work; it does not resolve
  the remaining topology bottleneck.
- A subsequent bounded batch path sends one minimal inference request per Kafka
  poll and lowers Kafka `fetch.max.wait.ms` to 25 ms. The corrected run
  processed 100/100 events but measured 648.437 ms p99, worse than the earlier
  546.152 ms single-request-profile run. This confirms the result is sensitive
  to topology/runtime variance and that fetch wait is not the controlling
  bottleneck; the batch path remains a structural optimization, not a passing
  E2 measurement.
- The minimal batch implementation now vectorizes logits and probability
  calculation and skips explanation construction entirely. The latest bound
  run decomposed to 369.158 ms inference and 162.961 ms case/audit, with
  779.079 ms end-to-end p99. This historical trial was slower than prior runs
  despite lower algorithmic work; it motivated service/runtime stabilization
  and repeated-run distributions.
- The qualification harness now uses a Hikari connection pool and wraps the
  audit checkpoint/append work in one transaction. The next run improved to
  540.976 ms p99, with 220.549 ms inference and 122.675 ms case/audit. This
  confirms connection and transaction setup were material contributors, but
  the remaining gap still requires topology-level concurrency and further
  reduction of synchronous work on the critical path.
- The Kafka qualification path now exercises four partitions with four
  consumers, bounds both broker fetch wait and consumer poll wait at 5 ms, and
  serializes the full audit transaction scope so concurrent appends cannot fork
  the hash chain before commit. The best valid rerun processed 100/100 events,
  passed checkpoint-bounded audit-tail verification, and measured 167.133 ms
  p99 (79.398 ms inference batch; 34.117 ms case/audit). Another 224.023 ms
  four-partition reading failed ledger-tail verification and is intentionally
  excluded from evidence. A subsequent all-partition warmup experiment was
  slower and is also excluded from the performance claim.
- The combined harness now reports the E2 boundary explicitly at scored-case
  creation, separately from the durable audit append, and waits five seconds
  after consumer startup to avoid measuring initial group formation. The latest
  readiness-bounded rerun processed 100/100 events, passed audit-tail
  verification, and measured 469.785 ms ingress-to-scored-case p99 and
  479.611 ms ingress-to-audit p99. This historical comparison showed large
  variance before the Linux-network candidate was introduced.
- A qualification-only asynchronous audit writer then moved the durable ledger
  append off the scored-case handler path while retaining a single ordered
  writer and requiring the complete audit suffix to drain and verify before the
  test passed. This produced 100/100 accepted events, 184.695 ms scored-case
  p99, and 46.667 ms case/audit transaction time. The design is evidence for a
  possible future topology split only; P4-04's production case-plus-audit ACID
  boundary remains unchanged.
- A later Linux-network candidate achieved one frozen-cardinality 46.480 ms
  scored-case p99 run at 6,251.60 events/sec, but a different arrival profile
  and a smaller Kafka poll exceeded 50 ms; the fast path still uses in-memory
  cases and asynchronous audit. [The findings record](../../docs/experiments/p4-07-latency-topology-findings.md)
  distinguishes the candidate from formal acceptance evidence.
- The current E2 disposition is `OPEN — insufficient repeatable, production-path
  evidence`, not `PASS`; no release authorization or enterprise-scale claim is
  inferred. Combined fault/restart, tamper, authority, and Java/Python
  production-path parity evidence remain open.

## Current status

P4-06 is merged and provides the local/container deployment baseline. P4-07
owns distributed qualification and release evidence; it must not infer scale
readiness from Helm rendering or local health checks alone.
