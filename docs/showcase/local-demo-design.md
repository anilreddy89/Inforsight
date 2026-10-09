# Local visitor journey: design and implementation map

The product lets a visitor submit one fictional policy event, inspect why each
component produced its result, make a fictional human decision, and verify the
record. The delivered frontend is a React/TypeScript application with a Vite
build and same-origin nginx API gateway. It is separate from Streamlit's local
Python decision-engine demonstration.

## Screen flow and navigation

**Landing → scenario picker → live journey → dossier → human review → audit.**
Architecture is available from the header on every page, the landing hero and
its architecture showcase, the live journey, the run navigation, and the footer. The
model timeline is available from the header, a landing band, the case dossier and
the footer. The
run's correlation ID stays in `?run=<id>` across view changes and refresh.
A resume field accepts an existing correlation ID. There is one local
environment; **GCP is Planned** and has no environment selector.

| View | Main components | Example copy and truthful behavior |
| --- | --- | --- |
| Landing | One-sentence explanation, static journey overview, primary CTA, model-history band, architecture entry | “From one event. To an informed human decision.” The overview is labeled as a target journey, not live execution. |
| Scenario picker | Three backend-enabled cards, safe JSON input inspector, submission, resume | “Submit one event and follow what the services actually record.” Disabled or absent capabilities do not become runnable through UI defaults. |
| Live journey | Eleven expandable stages, status and producer, correlation ID, evidence links, failure/retry notice | “Awaiting service result” while processing. Timestamps and duration come from committed backend records. |
| Case dossier | Facts at cutoff, unknown safety evidence, excluded future source IDs, score and explanations, eligibility reasons, modeled valuation/allocation, cited draft | “Unknown — evidence unavailable.” No fabricated negative fact or measured agent confidence. |
| Human review | Exact case evidence, approve/reject/request-information choices, required rationale, version, recorded outcome | “The agent has no action authority.” Approval is disabled for abstention and rejected server-side. |
| Audit trail | Verification result/scope, current case and reviewer decision, expandable journal events and hashes | Validity comes from an explicit verification request. Partial chain validity is not whole-run completion. |
| Architecture | Seven linked views (system map, request sequence, data and model lineage, run lifecycle, security layers, audit chain, database schema) with an inspector, numbered dataflow and illustrative walkthrough; deployment status with GCP Planned | Highlighting follows recorded stage status from the existing polling, and live chips show persisted values. Without a run, the reference design is shown. Fast completed work remains inspectable even if no active highlight was observed. |
| Model timeline | Groundwork, six data-design generations and the release as a vertical timeline with verdicts, headline figures and record links; generation chips; development counts; judging principles; released bundle identity | “Six generations to one model we could defend.” Every figure comes from a decision record pinned to the release tag. The page states that the results recover a synthetic process and do not establish real-world performance. |

Desktop uses a constrained content width, an ordered journey rail, and adjacent
summary/evidence panels. Mobile stacks panels, keeps the stage list readable,
and allows the view navigation to scroll horizontally. Technical JSON appears
under native disclosure controls; the primary explanation remains plain text.

## Visual system

The source of truth is [`frontend/src/styles.css`](../../frontend/src/styles.css).
The palette uses a white surface, cool gray canvas, dark navy text, and a blue
primary action. Status always has a text label and icon, not color alone.

| Token or rule | Implementation |
| --- | --- |
| Canvas / surface | `#F6F8FB` / `#FFFFFF` |
| Primary text / muted text | `#172D50` / `#536680`; supporting text uses a minimum 11px size; body copy is 13–14px |
| Accent / border | `#245DE3` / `#DFE5EE` |
| Focus | Visible 3px outline, offset 4px |
| Typography | Inter when available, then native system sans-serif; local monospace stack for hashes/IDs/payloads; no external font dependency |
| Hierarchy | Large landing headline, distinct view and panel titles, compact supporting labels, expandable technical detail |
| Spacing | Repeated 4/8/12/16/24/32px rhythm with wider section spacing; generous panel padding and a maximum content width |
| Shapes | Restrained rounded panels/buttons and thin borders; shadows used sparingly |
| Icons | Lucide outline icons, paired with labels where they communicate meaning |
| Waiting / processing | Neutral slate / blue |
| Completed / abstained | Green / amber; abstention is a recorded outcome, not a failure |
| Blocked / failed | Muted violet / red |
| Motion | Brief status/outline transitions tied to real state updates; no animated elapsed-progress percentages or fabricated steps |
| Reduced motion | `prefers-reduced-motion: reduce` removes animation, transitions, and smooth scrolling |

Keyboard behavior uses real buttons, anchors, radio inputs, labels, fieldsets,
native disclosure controls, focus indication, and a skip link. Status changes
have an accessible announcement. Layout, keyboard, contrast, and reduced-motion
checks belong to the browser validation; source styling alone is not proof of
accessibility conformance.

## Implementation-gap map

At initial inspection, the components were implemented separately and no stage
was connected and verified for the complete requested path. Durable run status,
resume/retry, and request information were missing. The new local journey now
has a passing 22-check API/broker/database/fault-recovery record for
`run_254f7735fdb240baaa53603b900e9568`. See the
[acceptance evidence](local-demo-acceptance.md) for component identities,
timestamps, exact commands, and the separate browser evidence.

Classifications below apply to this bounded local implementation and recorded
acceptance, not every historical route or a cloud/production deployment.

| Stage or capability | Current classification | Implemented connection and persisted evidence |
| --- | --- | --- |
| Submission | Connected and verified | New opt-in run API atomically writes source, run, submission journal, and outbox; idempotency key binds the request. |
| Kafka publication/ingestion | Connected and verified | Dedicated topic and worker; broker acknowledgement, durable inbox and source-envelope binding, duplicate delivery handling, invalid-envelope quarantine. |
| Point-in-time snapshot/features | Connected and verified | Private Python projection reuses domain/safety reconstruction and V6 features; source IDs, cutoff, unknowns, excluded events, catalog and snapshot digests persist. |
| Released model | Connected and verified | Actual HTTP score, exact released bundle digest and preprocessing profile checked; independently replayed score; no hash fallback. |
| Eligibility | Connected and verified | Java results and reasons persist for every action with rule/snapshot identity. |
| Allocation | Connected and verified | Python modeled economics feed Java multiple-choice allocation; at most one action per policy; fixed one-policy $30/1,800-second demo capacities. |
| Case | Connected and verified | Dedicated PostgreSQL `demo_case` references upstream evidence digests. |
| Bounded agent | Connected and verified | Containerized deterministic planner is called after case commit; trusted citations, worker identity, draft/abstention, and input digest persist. |
| Human approve/reject | Connected and verified | Dedicated versioned decision API retains rationale/notes and fictional reviewer label; verifies integrity and blocks approval of abstention. |
| Request information outcome | Connected and verified | Records a versioned review outcome and verified audit; this completes the run without collecting new evidence. |
| Audit | Connected and verified | Complete local stage journal and checkpoint, displayed-artifact/case binding, independent export recomputation and corruption checks. |
| Status/resume/retry | Connected and verified | Durable run projection and append-only journal; polling and correlation-ID resume; explicit failed-run retry; unfinished work resumes after Java restart. |
| Demo isolation/reset | Implemented but not integrated into this journey | Named Compose project/volumes, isolated `demo_*` tables, loopback ports, safe input allowlist; destructive volume reset is an operator command outside an individual run. |
| Follow-up evidence/re-review | Not implemented | Request information has no new evidence submission or reopen transition. |
| Multi-policy enterprise qualification | Implemented but not integrated into this journey | Separate allocator and P4-07 qualification work exist; this one-policy acceptance does not close that gate. |
| GCP journey | Not implemented | **Planned**. No infrastructure provisioned or available environment. |

The acceptance runner writes per-component evidence and two separate results to
`artifacts/local-demo/acceptance.json`. The [runbook](local-demo.md) defines the
required proof and exact commands. No historical phase document is rewritten
as evidence for this new path.

## Backend contract and dependency order

The public contract is
[`api/openapi/demo-journey-v1.yaml`](../../api/openapi/demo-journey-v1.yaml).
The minimum routes are scenario discovery, create/resume run, retry, human
decision, and audit verification. The browser never calls inference, Kafka, or
the agent directly. Polling is the deliberately small first transport: serial
reads every 1.5 seconds, backing off to 10 seconds on transport errors, with
background reads suspended. An SSE adapter could later emit the same durable
journal without changing evidence semantics; it is not implemented.

The implementation follows this dependency order:

1. PostgreSQL run/outbox/inbox/case/decision/journal/checkpoint migrations and
   transactional idempotency.
2. Actual Kafka publish/consume and persisted envelope binding.
3. Point-in-time projection and explicit raw-feature preprocessing contract.
4. Verified released-model HTTP score and identity checks.
5. Persisted Java rules and one-policy allocation using modeled valuation.
6. Case persistence followed by bounded agent draft or abstention.
7. Versioned fictional human review and full-chain verification.
8. Frontend polling, resume, accessible inspection, API/database qualification,
   and browser checks against the same gateway.

Each completed stage includes `producer`, `attempt`, `started_at`,
`completed_at`, `duration_ms`, `input_refs`, `output_refs`, and `evidence`.
The durable journal adds sequence, journal event identity, source event identity,
case version, exact payload bytes, parent hash, and current hash. Hashes link
inputs/outputs; the UI cannot create a completed backend stage.

## Deliberate limits and remaining work

- Allocation is one fictional policy under fixed resource capacity, not a
  qualified multi-policy production portfolio.
- One local Java worker owns orchestration. Broker redelivery and repeated
  read-only calls are possible after interruption; multi-worker claiming and
  distributed exactly-once guarantees are not implemented.
- Fictional reviewer labels are not identity verification. This loopback demo
  does not provide public multi-tenant authentication or an execution API.
- The agent uses deterministic evidence/procedure checks, not a live generative
  model or measured confidence estimate.
- Audit verification shares a PostgreSQL trust domain with its checkpoint;
  external anchoring and privileged-administrator resistance are not claimed.
- Request information records an outcome; reopening with new evidence remains
  unavailable. Retention scheduling and per-run deletion are also absent.
- GCP deployment, hosted ingress/authentication, full observability, cost
  controls and teardown verification require a separately reviewed design.
  P4-07 persistent enterprise-scale qualification remains open.

The [proposed cloud deployment design](../architecture/gcp-demo-deployment-recommendation.md)
compares both deployment paths after local acceptance; GCP remains Planned.
