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
