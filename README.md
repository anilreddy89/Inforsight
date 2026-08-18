<p align="center">
  <img src="docs/assets/inforsight-readme-banner.png" alt="Inforsight — See Risk. Shape Action." width="900">
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="Apache 2.0 license"></a>
</p>

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

## Target architecture

![Inforsight target architecture](docs/assets/inforsight-target-architecture.png)

This diagram shows the intended long-term system boundary and technology direction. It is not a representation of the current Phase 0 implementation; components will be introduced incrementally only after their assumptions and interfaces are validated.

## Repository map

```text
data-contracts/   Versioned fictional data schemas
simulator/        Seeded policy and event generator (first implementation target)
ml/               Leakage-safe features, experiments, evaluation, and model cards
services/         Java control-plane services and deterministic rules
agents/           Bounded evidence, procedure, and planning assistants
infra/            Local and cloud infrastructure added only when justified
docs/             Assumptions, ADRs, experiments, and published documentation assets
scripts/          Repository validation and developer utilities
```

## Current status

Phase 1 - Policy Digital Twin. The versioned policy-event envelope and strict event payload contracts are complete. Issue #5 is implementing a deterministic seeded generator for 100 fictional policy histories; point-in-time reconstruction remains the next dependent increment.

See [the initial backlog](docs/backlog.md), [domain assumptions](docs/assumptions.md), and [clean-room policy](docs/clean-room-policy.md) before contributing.

## Getting started

The Phase 0 scaffold requires Python 3.11 or newer, GNU Make, and Git. It has no runtime third-party dependencies.

```bash
git clone https://github.com/anilreddy89/Inforsight.git
cd Inforsight
make check
```

The check runs repository boundary validation and the simulator smoke tests. Additional language-specific checks will be added when those components become real.

[GitHub Actions](https://github.com/anilreddy89/Inforsight/actions/workflows/ci.yml) runs the same checks on every push and pull request.

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes. All contributions must follow the fictional-data and clean-room boundaries.

## License

Copyright 2026 Anil Kumar Reddy Jonnala. Licensed under the [Apache License 2.0](LICENSE). Third-party software remains subject to its own license terms.
