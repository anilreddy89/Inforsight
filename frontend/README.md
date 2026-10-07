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
