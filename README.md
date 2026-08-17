# Inforsight

**See Risk. Shape Action.**

Inforsight is a clean-room project for conservation case intelligence on in-force life-insurance policies. It reconstructs fictional policy timelines, estimates near-term lapse or surrender risk, applies deterministic eligibility rules, assembles cited evidence, and keeps a human reviewer in control of every intervention.

## First falsifiable claim

Can we generate a realistic fictional in-force policy timeline and predict which active policies are likely to lapse within 90 days without leaking future information?

The first milestone is deliberately smaller than the complete architecture: generate reproducible fictional policy-event histories, reconstruct state as of a chosen date, and validate that model features contain no future information.

## What Inforsight is

- A policy-lifecycle and conservation decision-support demonstration.
- A clean-room system built from fictional data, fictional procedures, public references, and original code.
- A separation of probabilistic risk estimation, deterministic action eligibility, bounded assistance, human approval, and audit replay.
- A staged engineering project whose assumptions, experiments, limitations, and rejected approaches remain visible.

## What Inforsight is not

- An underwriting or new-business risk classifier.
- A generic churn dashboard.
- An autonomous system that contacts customers or executes financial actions.
- A claim of production accuracy based on synthetic data.
- A reproduction of an insurer's proprietary data, rules, workflows, terminology, or software.

## Authority model

| Layer | Responsibility | Hard boundary |
| --- | --- | --- |
| Predictive model | Estimate time-bounded lapse or surrender risk | Cannot select or execute an action |
| Deterministic rules | Decide which actions are allowed | Cannot fabricate facts or override required evidence |
| Bounded assistants | Assemble evidence and draft recommendations | Cannot bypass rules or human review |
| Human reviewer | Approve, reject, or request more information | All interventions require an accountable decision |
| Audit trail | Preserve inputs, versions, recommendations, and decisions | Must support point-in-time replay |

## Repository map

```text
data-contracts/   Versioned fictional data schemas
simulator/        Seeded policy and event generator (first implementation target)
ml/               Leakage-safe features, experiments, evaluation, and model cards
services/         Java control-plane services and deterministic rules
agents/           Bounded evidence, procedure, and planning assistants
infra/            Local and cloud infrastructure added only when justified
docs/             Assumptions, vocabulary, ADRs, experiments, and backlog
Documents/        Planning briefs, trackers, architecture diagrams, and brand assets
scripts/          Repository validation and developer utilities
```

## Current status

Phase 0 - Foundation. The planning package is complete and the repository scaffold is ready. The next implementation task is the versioned policy-event contract, followed by a seeded generator for 100 fictional policy histories.

See [the initial backlog](docs/backlog.md), [domain assumptions](docs/assumptions.md), and [clean-room policy](docs/clean-room-policy.md) before contributing.

## Local checks

```bash
make check
```

The initial check runs repository boundary validation and the simulator smoke tests. Additional language-specific checks will be added when those components become real.

## License

Copyright 2026 Anil Kumar Reddy Jonnala. Licensed under the [Apache License 2.0](LICENSE). Third-party software remains subject to its own license terms.
