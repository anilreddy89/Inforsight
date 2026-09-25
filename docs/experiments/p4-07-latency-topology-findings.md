# P4-07 latency and topology findings — 2026-09-22

## Question and decision boundary

Can the P4-07 Kafka → Java control plane → Python inference → scored-case path
meet the frozen E2 p99 ingress-to-scored-case threshold of 50 ms while scoring
the 100,000-policy/200,000-event synthetic workload at the E1 floor of 5,000
events/second? This record is local diagnostic evidence, **not** a passing
E1–E6 qualification report or authorization for `v0.4.0-enterprise-scale`.
The 50 ms threshold has not been relaxed.

## Workload and measurement method

- Frozen event identity: 100,000 fictional policies, two events each, seed
  `4072026`, namespace `p4-07-enterprise-scale-synthetic`. The 200,000-event
  ordered workload SHA-256 is
  `c2cc1d0b524dc2b2bdd7e342adb7a63040d8429be2175403369309fb2e031a33`.
  The Java harness checks this against the Python qualification generator.
- The benchmark used local OrbStack Linux networking on a Mac, not dedicated
  production hardware. Kafka, PostgreSQL, and the one-worker Python inference
  service ran in Compose; Java/Maven ran in a Linux container on the same
  network. The candidate topology used 12 Kafka partitions, one consumer,
  `fetch.min.bytes=32768`, `fetch.max.wait.ms=5`, `max.poll.records=500`, and
  producer `linger.ms=2`. After unsuccessful CPU-pinning trials, the services
  were restored to the VM's effective 12-CPU set. This is a measured candidate,
  not a frozen release topology.
- Before each measured run, 100 synthetic warm-up events traversed Kafka,
  inference, case creation, and audit append. The harness waited for the
  warm-up audit tail to drain. Earlier warm-up logic skipped inference, which
  made those latency comparisons cold and non-equivalent.
- Each measured event records `System.nanoTime()` immediately before
  `KafkaProducer.send`. E2-like latency ends after `CaseStore.create` for the
  poll batch, **before** the qualification-only asynchronous PostgreSQL audit
  append. Producer acknowledgements, handler entry, inference batch, case
  completion, and audit-batch duration are separately sampled. P99 uses
  nearest-rank order statistics. The harness checks every measured event was
  acknowledged and scored, waits for all audit entries, verifies the hash
  suffix from its starting checkpoint, and compares the final database head.
- Scored throughput is 200,000 divided by elapsed time from the first
  scheduled measured send to the last scored-case completion. A paced
  `100 events / 16 ms` candidate targets 6,250 offered events/second; the
  arrival schedule is **not** part of the frozen workload identity and needs a
  versioned qualification-protocol decision before a formal E1/E2 claim.

## Observations

The rows below are separate experiments. Different workload sizes, arrival
rates, or topologies must not be combined into a single passing gate result.
Values are p99 ingress-to-scored-case unless the row says otherwise.

| Configuration and workload | Observed result | Interpretation |
| --- | --- | --- |
| Earlier Mac-host Java with OrbStack services; five warmed 100-event runs | Median 95.243 ms; worst 112.806 ms | Local baseline; above 50 ms. |
| Linux-container Java, 12 partitions, one consumer/worker, frozen-style 100-event samples; two earlier five-run sets | Median/worst 19.874/32.565 ms and 18.563/24.369 ms | Same-VM Linux networking removes much of the host↔VM scheduling cost; small-sample evidence only. |
| First strict `make p4-07-linux-latency-check`, five warmed 100-event runs | Per-run p99 16.727, 18.590, 18.756, 25.946, 17.786 ms; median 18.590 ms; worst 25.946 ms; all 100/100 and audit tails verified | This local 50 ms **diagnostic set** passed, not production E2; the later repeat below failed. |
| Later repeat of the same five-run local diagnostic, after Kafka ingress tests | Per-run p99 18.032, 29.898, 19.112, 18.248, 193.314 ms; median 19.112 ms; worst 193.314 ms. The fifth run had ingress-to-broker-ack p99 185.913 ms, versus inference-batch p99 10.226 ms | Strict 50 ms local diagnostic **failed** on repetition. The long tail was concentrated before broker acknowledgement; this is direct evidence against claiming repeatability. |
| 10,000-event unpaced burst (pre-frozen event identities) | 15,158.41 scored events/s; p99 617.396 ms | Throughput alone did not control queue latency. Not an E2 pass or frozen-workload result. |
| 10,000 events paced 100/16 ms (pre-frozen identities) | 6,287.18 scored events/s; p99 30.996 ms | Pacing reduced queueing in this local trial. |
| 200,000 paced events before frozen identity was matched | 6,251.64 scored events/s; p99 26.213 ms | Invalid as frozen-workload evidence; IDs did not match the declared digest. |
| 200,000 frozen-identity events paced 100/16 ms, IDs constructed in the timed producer loop | 6,250.99 scored events/s; p99 79.732 ms | The producer-side identity construction and resulting send clumping mattered. E2 failed. |
| 200,000 frozen-identity events paced 100/16 ms, IDs/digest precomputed before measurement | 6,251.60 scored events/s; p99 46.480 ms; inference-batch p99 19.383 ms; audit-batch p99 57.913 ms; all events and audit tail verified | One bounded local run met numerical E1/E2 thresholds. Audit p99 is batch duration and lies outside the measured scored-case boundary. This is not a formal gate pass. |
| Same frozen identity paced 100/19 ms | 5,264.71 scored events/s; p99 66.701 ms | A slower feed did not guarantee lower tail latency; topology variance remains material. |
| Same frozen identity paced 100/16 ms but `max.poll.records=100` | 6,250.67 scored events/s; p99 444.620 ms | Smaller polls increased batch and audit-queue pressure; rejected for this candidate topology. |
| Two inference workers/two consumers, five 100-event runs | 74.119, 75.094, 70.530, 30.829, 76.429 ms | Adding workers/consumers was unstable and did not improve the local tail. |
| CPU-pinned services and benchmark, five 100-event runs | Median 50.889 ms; worst 58.585 ms | Pinning within the shared local VM worsened this candidate; all CPUs were restored. |

The earlier failed 200,000-event frozen trial found a harness defect: the
second event for a policy reused `(case_id, case_version, event_type)`, violating
the audit ledger's uniqueness constraint. The audit writer exited while the
consumer blocked on a full queue. The harness now uses the created case ID,
checks writer failure while offering to the bounded queue, and fails visibly.
That rolled-back PostgreSQL insert also demonstrated that `BIGSERIAL` can skip
numbers without a committed row being deleted. [ADR 0017](../adr/0017-verify-committed-audit-chain-across-sequence-gaps.md)
records the corrected verification rule: strictly increasing committed
sequences, valid parent/current hashes, and an independently retained head
checkpoint. These are correctness fixes, not latency evidence.

An external-Kafka integration rerun exposed a separate test-isolation flaw:
its shared retained topic yielded 4,001 observed events for a 4,000-event
restart probe. The integration test now creates a unique topic per scenario
and run, maps that synthetic topic to the handler's fixed production allowlist
only inside the test, and requires exact broker acknowledgements. A prior
200,000-event throughput figure from the shared topic may have been
contaminated by historical records and must not be used as an E1 result.
The local broker subsequently showed `OutOfOrderSequenceException` and
`NotLeaderOrFollowerException` during synthetic publishing. The test publisher
now waits for partition leaders, uses a bounded delivery timeout and retries,
and disables idempotent-sequence mode **only for this consumer probe**; the
production publisher is unchanged. The corrected three-test integration suite
passed with 200,000/200,000 acknowledged and accepted at 151,382.95 events/s
and a separate 4,000/4,000 restart run. This is bounded Kafka ingress/recovery
evidence, not the full frozen topology or authoritative E1/E5 qualification.
The PostgreSQL-backed rollback-gap regression test also passed against the
local Compose database.

## What the result does and does not prove

The local candidate demonstrates a plausible sub-50 ms path for some small
warmed samples and one full-cardinality synthetic run. A subsequent five-run
repeat failed the strict local diagnostic, so even the small-sample result is
not stable. It does **not** establish that
P4-07 is complete. The fast harness uses an in-memory `CaseStore`, with audit
append deferred until after the scored-case measurement; it does not exercise
the P4-04 persistent case-plus-audit atomic transaction on the measured E2
path. It has not bound authority, tamper, restart/replay, and Java/Python
parity probes into one cryptographic E1–E6 report. There is no approved
dedicated Linux qualification environment, versioned arrival profile,
repeatable full-cardinality result, or release decision. The local 50 ms
diagnostic cannot be substituted for the frozen production qualification gate.

## Next qualification decision

1. Review and freeze a versioned arrival profile (including burst shape),
   topology/worker counts, measurement boundary, warm-up, repeated-run policy,
   and resource allocation before treating another run as acceptance evidence.
2. Exercise the persistent scored-case path, or explicitly amend the E2
   contract through an architecture decision if asynchronous audit is intended
   to be authoritative. Preserve the P4-04 ACID and human-authority guarantees.
3. On isolated, dedicated Linux resources, repeat the entire frozen workload
   with exact event accounting, p99 and throughput, committed audit verification,
   E3–E6 probes, runtime/topology identities, and a cryptographic report.
4. Keep E2 and P4-07 **open** until the complete bound run passes; publish a
   fail-closed decision if it does not. Do not tag the release or close
   Milestone #5 on the strength of these local measurements.
