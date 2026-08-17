# Initial Backlog

This backlog is ordered for a natural repository history. Each item should become a tracked issue before implementation.

## Phase 0 - Foundation

- [x] Create repository README, clean-room policy, assumptions, and initial ADRs.
- [x] Add contribution, security, licensing, and repository-boundary checks.
- [ ] Create hosted repository and configure branch protection.
- [ ] Convert the first implementation items below into hosted issues and a `v0.1.0-data-foundation` milestone.

## Phase 1 - Policy Digital Twin

- [ ] Define `policy-event.schema.json` with explicit version and timestamps.
- [ ] Define policy, billing, payment, notice, service, and outcome event payloads.
- [ ] Add valid and invalid contract examples.
- [ ] Implement a deterministic seeded generator for 100 policies.
- [ ] Implement point-in-time state reconstruction.
- [ ] Test event ordering, valid transitions, impossible dates, and deterministic replay.
- [ ] Publish a small sample dataset and `DATA_CARD.md`.

## Phase 2 - Baseline ML

- [ ] Define observation records and a 90-day outcome label.
- [ ] Add automated future-leakage tests.
- [ ] Create temporal train, validation, and test splits.
- [ ] Train and document a transparent baseline.
- [ ] Add calibration and top-review-band metrics.
- [ ] Publish `MODEL_CARD.md` and an experiment note.

## Deferred intentionally

Java services, Kafka, cloud deployment, bounded agents, and RAG remain deferred until the data and baseline-model gates pass.
