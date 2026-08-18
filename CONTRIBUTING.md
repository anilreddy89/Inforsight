# Contributing to Inforsight

## Working agreement

1. Create or link an issue before meaningful implementation work.
2. Keep changes small enough to review and explain.
3. Add or update tests with behavioral changes.
4. Record architectural direction changes in `docs/adr/`.
5. Document experiments, including failed or rejected approaches, in `docs/experiments/`.
6. Run `make check` before opening a pull request.

Improvements discovered during implementation, review, or maintenance should follow the [engineering improvement workflow](docs/engineering-improvement-workflow.md). Use a focused follow-up issue when an observation is outside the active issue or is discovered after merge.

## Clean-room requirement

Contributions must use fictional data, fictional procedures, public references, and original implementation. Do not contribute confidential or proprietary insurer data, code, schemas, screenshots, rules, internal terminology, credentials, or customer information. See [the clean-room policy](docs/clean-room-policy.md).

## Claims and evidence

- Do not claim production accuracy or business lift from synthetic data.
- Label assumptions, generated examples, and simulated outcomes clearly.
- Cite public sources used to shape domain assumptions.
- Preserve observation dates and point-in-time boundaries in data and ML work.

## Commit style

Use concise, imperative commit messages that describe a meaningful working increment, for example:

```text
Define versioned policy event contract
Add seeded billing-event generator
Reject features observed after scoring date
```
