# Fictional local reviewer walkthrough

Open **http://localhost:3000** after `make demo-up`. This walkthrough describes
the new opt-in Docker visitor journey, whose outputs are persisted by the Java
control plane. It is separate from both Streamlit's in-process Python workflow
and the historical P5 synchronous handoff. Setup and acceptance evidence are in
the [local demo runbook](local-demo.md).

## 1. Submit one fictional event

Choose **A payment falls behind** and start the case. Advanced inputs permit
only a bounded payment delay and premium. The scenario's fixed observation time
is **2026-09-25 12:00:00 UTC**. This is a fictional observation cutoff, not the
live processing clock. The scenario includes a later recovery event so the
projection can demonstrate exclusion of future evidence.

The Java endpoint persists the source history, submission journal, and outbox.
The worker publishes the actual envelope to Kafka; the consumer records its
broker location in a deduplicated inbox. The UI displays completion only after
these records commit. Copy the correlation ID or preserve `?run=<id>` to resume.

## 2. Watch and inspect the recorded journey

The Live journey lists submission, publication, ingestion, snapshot, score,
rules, allocation, case persistence, agent, human decision, and audit. Expand a
stage for timestamps, elapsed processing duration, attempt, producing component,
input/output references, and technical evidence. The page polls the backend;
there is no timer that manufactures progress. A quick stage may finish between
polls, but its record remains inspectable.

A dependency failure appears as **failed** and leaves downstream stages
**blocked**. After restoring the service, **Retry** resumes the same event.
Completed outputs remain committed and failed attempts remain in the journal.

## 3. Inspect facts and predictive perception

The Case dossier shows the policy facts, separate safety evidence, raw V6
features and source lineage available at the cutoff. Later effective or ingested
facts do not become visible. Unknown evidence is displayed as unknown.

A separate HTTP inference process verifies the released bundle and scores the
projected features. The gateway applies the governed V6 coefficient transform
before the bundle's own z-score. The score and directional explanations come
from the same response, with bundle and preprocessing identities retained. The
prediction describes modeled 90-day lapse-or-surrender risk; it cannot choose or
execute an intervention.

## 4. Inspect eligibility and allocation

Java evaluates each canonical action and persists reasons, rule version, and
snapshot identity. Missing safety evidence fails closed. The read-only Python
adapter values candidates under existing fictional RH-04 economics; Java's
multiple-choice allocator selects at most one eligible action for this policy
under **$30 direct-cost capacity and 1,800 personnel seconds**.

This is a one-policy demonstration of the allocation component. It does not
prove multi-policy enterprise-scale performance or realized value. Modeled
expected annual premium preserved is not profit, revenue, or causal uplift.

## 5. Inspect the persisted case and bounded agent

Java persists a `demo_case` linked to the snapshot, score, rules, and allocation
digests, then calls the Python bounded planner. The planner cites source event
IDs and the versioned fictional review procedure. Its actual worker identity,
input digest, and draft or abstention are recorded. This slice uses the existing
deterministic planner; it does not require an LLM or hosted-agent credential.

The missing-safety-evidence scenario preserves an unknown legal-hold fact. The
legal-hold scenario supplies a true legal hold. Both allow the visitor to
inspect real rule restrictions and an agent abstention, rather than a scripted
visual outcome.

## 6. Make a fictional human decision

Review the recorded evidence, choose approve, reject, or request more
information, and enter a rationale. Java verifies the current case version and
audit integrity before atomically recording the decision, incrementing the case
version, and completing the audit stage. Duplicate review requests with the same
identity do not increment the version twice. Stale reviews conflict.

The visitor's reviewer ID is a fictional label, not an authenticated licensed
caseworker. Approval of an abstention is unavailable and rejected by the API.
All outcomes retain `authorized_to_act: false`; no call, message, real policy
change, CRM action, or telephony operation is available. Request more information
records a review outcome; collecting new evidence and reopening that run is not
implemented.

## 7. Verify the audit receipt

The Audit trail recomputes the chain from exact stored payload bytes, compares
its local PostgreSQL checkpoint, and checks the displayed artifacts and current
case version against committed evidence. Inspect event IDs, producer identity,
parent/current hashes, human rationale, and versions. Verification of a partial
chain does not mean the full journey has completed.

The checkpoint shares the database trust boundary. This is bounded local
integrity verification, not external anchoring or protection against a database
administrator rewriting all evidence. See the [realism boundary](../realism-boundary.md).

## Related evidence

- [Current API/event contract](../../api/openapi/demo-journey-v1.yaml).
- [Local acceptance and failure/recovery instructions](local-demo.md).
- [Screen flow, design system, and implementation map](local-demo-design.md).
- [Historical P5 qualification](../../Documents/phase_docs/phase-05-06-integrated-local-demo-qualification.md), which excludes this complete Kafka/released-model path.
- [RH-12 portfolio evidence](../experiments/phase-rh-12-evidence-reconciliation-1.0.0.md), a separate synthetic cohort evaluation.
- P4-07 enterprise-scale qualification remains open. GCP is **Planned**.
