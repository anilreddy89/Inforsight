# Inforsight visitor demo

A React + TypeScript application built with Vite and served by the local Docker
gateway. React supports the linked journey, dossier, review, and audit views;
TypeScript describes the run contract without coupling the browser to Python or
Java internals. Plain CSS provides the responsive design and reduced-motion mode.

The browser uses only same-origin `/api/v1/demo/scenarios` and
`/api/v1/demo/runs` endpoints. The production nginx gateway rejects legacy API
routes. It serves no fixtures, generates no scores, and never infers a stage's
completion from elapsed time. Missing evidence remains unavailable.

## Development

Use Node 22 and the repository's running local Docker services:

```sh
cd frontend
npm ci
npm run dev
```

The development server on port 3000 proxies API requests to localhost:8080.
`npm run build` checks TypeScript and produces the nginx assets in `dist/`.
The repository Compose file builds `frontend/Dockerfile` from the repository root.

## State and resilience

- Run identity is retained in `?run=<correlation_id>` for reload and sharing.
- Serial polling reads persisted state every 1.5 seconds after the previous
  request completes. Transport errors back off to 10 seconds and show a stale
  connection notice. Background tabs suspend reads.
- Timestamps from newer run versions prevent late responses overwriting a newer
  committed decision. Polling never supplies synthetic stage timestamps.
- Pending submissions retain their exact input and idempotency key in browser
  session storage, permitting response-loss recovery after reload.
- Reviewer choices are sent to Java with expected case version and idempotency
  identity. An abstaining agent cannot be approved as an action.
- GCP is shown only as Planned. There is no environment selector.

The root acceptance scripts exercise the real public gateway and backend. Build
success alone is not journey acceptance.

## Transaction flow

Open **Transaction flow** from any case, or follow the **Explore transaction flow**
button in Live journey. The view is also addressable with `?run=<id>&view=flow`.
Its component map follows the eleven persisted checkpoints with selectable
handoffs, input/output evidence, recorded durations, zoom, and drag-to-pan.
The inspector can follow the current checkpoint or stay on a selected component.

Live updates share the existing serial polling; no new requests or workflow
actions are issued by the visualization. Connections describe workflow order.
Payload inspection resolves recorded references and stage outputs, rather than
claiming to capture HTTP or Kafka messages. Missing evidence stays unavailable.

Replay freezes the current record, walks only checkpoints with persisted
timestamps, and continues receiving live updates in the background. Playback is
illustrative, not to scale; return to live to inspect newer evidence. Reduced
motion disables animated packets and starts replay paused. Keyboard users can
move between graph components with arrow keys and operate the timeline, payload
tabs, and replay slider.

Run isolated UI contract and accessibility tests with `npm run test:flow`.
With the local Docker backend available on port 8080, run
`INFORSIGHT_FLOW_LIVE=1 npm run test:flow` to include a real-backend smoke test.
The test server uses port 4173. Test fixtures exist only in the test suite.

## Recent runs

The **Recent runs** button beside **Resume a previous run** opens a searchable
browser history. It keeps up to 20 successfully created or opened cases in
`localStorage`, ordered by last visit, and synchronizes across tabs. Each entry
contains only the correlation ID, scenario, last known status, and timestamps;
case evidence, payloads, and credentials are never saved in the history.

History is scoped to the current visitor session and website origin. Opening a
saved entry uses the normal authenticated run endpoint. Removed or unavailable
runs are labeled after an unsuccessful open; removing an entry or clearing the
list does not delete backend cases. Storage failures fall back to in-tab history.
Earlier runs cannot be backfilled automatically: history starts when this feature
is used, including when an older run is reopened from a saved URL or ID.

Run focused checks with `npx playwright test tests/recent-runs.spec.ts`.

## Architecture explorer

The explorer is reachable from the **Architecture** button in the header on every
page, **Explore the architecture** in the landing hero, the landing showcase (which
opens any view directly), the banner above the live journey's stages, the run
navigation, and the footer. The header button and the run tab show **New** until
the visitor opens the explorer once; that flag lives in session storage only. The
view is addressable with `?view=architecture&lens=<view>`:

| View | `lens` | Shows |
| --- | --- | --- |
| System map | `system` | Containers, Docker networks, published ports, volumes and operator jobs, for the local stack or the Mac-hosted preview |
| Request sequence | `sequence` | The 42 numbered calls of one run across the browser, nginx, Java, PostgreSQL, Kafka and both Python services, grouped by stage |
| Data & model lineage | `lineage` | The offline v6 model factory that produced the pinned bundle, and the per-run evidence chain from source history to verified journal |
| Run lifecycle | `lifecycle` | Run, stage and case state machines with each allowed transition and its trigger |
| Security layers | `security` | Edge, gateway, session, request contract, authority, integrity and container controls |
| Audit chain | `audit` | How journal rows are hashed and the nine checks the verifier runs |
| Database schema | `schema` | The eleven `demo_*` tables, keys and foreign keys from Flyway V6–V8 |

The diagrams are typed data in `src/architecture-model.ts`, and each component
lists the source files it describes. Update the model when Compose, nginx, Java,
Python or migrations change those facts.

With a run open, components, connections, stages and states follow the run's
persisted record through the existing polling. Live chips show recorded values such
as the Kafka offset, calibrated probability, selected action and verified journal
head. The explorer issues no requests of its own; **Load and verify this run's
chain** calls the existing audit endpoint only when the visitor asks. Without a run,
the view shows the reference design. The walkthrough highlights the numbered
dataflow in order: it is illustrative, executes nothing, and starts paused under
reduced motion. Animation marks recorded activity, not captured packets. A fast
stage can finish between polls without ever appearing as processing. GCP remains
Planned.

The explorer loads on demand, so the journey's initial bundle does not grow. Run
`npx playwright test tests/architecture.spec.ts` for isolated contract and
accessibility checks, and `INFORSIGHT_FLOW_LIVE=1 npx playwright test
tests/architecture-live.spec.ts` against the local Docker backend.
