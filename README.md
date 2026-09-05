<p align="center">
  <img src="docs/assets/inforsight-readme-banner.png" alt="Inforsight — See Risk. Shape Action." width="900">
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="Apache 2.0 license"></a>
  <a href="https://github.com/anilreddy89/Inforsight/actions/workflows/ci.yml"><img src="https://img.shields.io/badge/CI-passing-brightgreen.svg" alt="CI passing"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/phase-Baseline%20ML%20Complete-brightgreen.svg" alt="Phase: Baseline ML Complete">
</p>

**Inforsight** is a clean-room conservation case intelligence system for in-force life-insurance policies. It reconstructs fictional policy timelines from immutable event streams, estimates near-term lapse or surrender risk without leaking future information, separates prediction from action authority, and keeps a human reviewer in control of every intervention.

> **First falsifiable claim**: Can we generate a realistic fictional in-force policy timeline and predict which active policies are likely to lapse within 90 days — using only information available on the observation date?

---

## Why this project exists

Life insurance policy lapses cost the industry billions annually in lost premium and wasted acquisition spend. Conservation teams need to identify at-risk policies early, but building a reliable risk model is harder than it looks:

- **Temporal leakage** — using information that wouldn't have been available yet — silently inflates accuracy.
- **Confounded features** — billing frequency, observation timing, and policy age can masquerade as risk signals.
- **Uncalibrated scores** — ranking ≠ probability; a "high risk" label without calibrated confidence is operationally useless.
- **Autonomous action risk** — a model that directly contacts customers or alters policies without human review is a regulatory and ethical hazard.

Inforsight tackles all four through a **contract-first, fail-closed engineering approach** built entirely from synthetic data, public references, and original code — with every assumption, experiment, failure, and decision recorded.

---

## The journey: 6 generations, 5 failures, 1 solution

Most portfolio projects show a single model and a final accuracy number. This project shows the **full engineering arc** — including the iterations that failed and *why* they failed. Every decision is recorded in an immutable [Architecture Decision Record](docs/adr/README.md).

| Generation | Method | What happened | Decision |
| :--- | :--- | :--- | :---: |
| **v1** | Single-batch generator, logistic + XGBoost | Billing frequency confounded with time; no pre-cutoff risk mechanism; AUC ≈ 0.53 | `pipeline_engineering_only` |
| **v2** | Multi-cohort, proportional hazards, frailty | Automated preflight caught ingestion-time leakage before model fitting | `stop` |
| **v3** | Event-first dual-time, 20-seed acceptance | Signal recovery collapsed: median AUC 0.519 vs. target ≥ 0.65 (0/20 seeds passed) | `redesign` |
| **v4** | Doubled coefficients, halved frailty | Monthly hazard exploded past actuarial ceiling (0.25–0.45 vs. limit < 0.20) | `redesign` |
| **v5** | 320-cell feasibility surface, 17 diagnostics | **0 of 320 cells** satisfy simultaneous AUC ≥ 0.70 and hazard < 0.20 — *mathematically infeasible* | `stop_infeasible_design` |
| **v6** | **Bounded sigmoid hazard link** | Broke the Proportional Hazards Trilemma; 20/20 seeds pass; median AUC 0.7031 | ✅ `proceed` |

> The full iteration history with root-cause analysis is in the [Iteration Ledger](docs/experiments/iteration-ledger.md).

**Generation v6** introduced a bounded logistic hazard link — $\lambda(t) = \lambda_{\max}\sigma(z)$ — that mathematically guarantees monthly hazard ≤ 0.15 while preserving discriminative signal. This architecture passed all 120 inventory units across 20 acceptance seeds under [Protocol 3.1.0](docs/modeling/phase-02r-16-v6-statistical-acceptance-execution-contract.md).

---

## Current baseline results

$L_2$-regularized Logistic Regression ($C{=}1.0$, `liblinear`) with Platt scaling calibration, evaluated out-of-sample on 8,782 observations from 1,440 policies:

| Category | Metric | Value | 95% Clustered Bootstrap CI |
| :--- | :--- | ---: | :---: |
| Discrimination | ROC AUC | **0.6998** | [0.6847, 0.7153] |
| Discrimination | Average Precision | **0.2765** | [0.2560, 0.2994] |
| Calibration | Expected Calibration Error | **0.0115** | — |
| Calibration | Slope | **0.9498** | governed [0.85, 1.15] |
| Probability | Brier Score | **0.1211** | [0.1168, 0.1253] |
| Probability | Brier Skill Score | **+0.0633** | — |

### Operational triage queues

| Review queue | Precision | Recall | Lift | NNR |
| :---: | :---: | :---: | :---: | :---: |
| **Top 1%** | 34.09% | 2.24% | 2.23× | 2.93 |
| **Top 5%** | 35.31% | 11.57% | 2.31× | 2.83 |
| **Top 20%** | 30.24% | 39.63% | 1.98× | 3.31 |

> Full metrics, decision curves, and feature attributions: [MODEL_CARD.md](MODEL_CARD.md)

---

## Authority model

No component in Inforsight can autonomously contact a customer or alter a policy. Risk estimation and action authority are architecturally separated ([ADR 0002](docs/adr/0002-separate-risk-from-action-eligibility.md)):

| Layer | Responsibility | Hard boundary |
| --- | --- | --- |
| **Predictive model** | Estimate time-bounded lapse or surrender risk | Cannot select or execute an action |
| **Deterministic rules** | Decide which actions are allowed | Cannot fabricate facts or override required evidence |
| **Bounded assistants** | Assemble evidence and draft recommendations | Cannot bypass rules or human review |
| **Human reviewer** | Approve, reject, or request more information | All interventions require an accountable decision |
| **Audit trail** | Preserve inputs, versions, recommendations, and decisions | Must support point-in-time replay |

---

## Key engineering decisions

| # | Decision | Why it matters |
| :---: | --- | --- |
| [ADR 0001](docs/adr/0001-clean-room-and-synthetic-data.md) | Clean-room synthetic data foundation | No proprietary data risk; fully open-sourceable |
| [ADR 0002](docs/adr/0002-separate-risk-from-action-eligibility.md) | Separate risk perception from action authority | Architecturally prevents autonomous customer harm |
| [ADR 0003](docs/adr/0003-start-local-and-defer-distributed-infrastructure.md) | Start local, defer distributed infrastructure | Validate assumptions before spending on cloud |
| [ADR 0012](docs/adr/0012-authorize-bounded-sigmoid-hazard-link-v6.md) | Bounded sigmoid hazard link for Generation v6 | Breaks the Proportional Hazards Trilemma |
| [ADR 0013](docs/adr/0013-amend-v6-statistical-acceptance-protocol.md) | Statistical Acceptance Protocol 3.1.0 | Pre-declared thresholds; 20-seed mechanical gate |

> All 13 ADRs with alternatives and rationale: [docs/adr/](docs/adr/README.md)

---

## Target architecture

![Inforsight target architecture](docs/assets/inforsight-target-architecture.png)

This diagram shows the intended long-term system boundary. Components are introduced incrementally only after their assumptions and interfaces are validated. Current implementation covers the event simulation, ML pipeline, and model bundle layers.

---

## Project status

### ✅ Phase 0 — Foundation
Repository scaffold, clean-room policy, domain assumptions, initial ADRs, contribution and security policies, CI.

### ✅ Phase 1 — Policy Digital Twin
Versioned event contracts ([JSON Schema Draft 2020-12](data-contracts/)), deterministic 100-policy generator, point-in-time state reconstruction, cross-event history validation, reproducible [sample dataset](datasets/sample-policy-events.jsonl), and [synthetic-rate assessment](docs/experiments/phase-01-07-synthetic-rate-assessment.md).

### ✅ Phase 2 — Baseline ML
| Step | Description | Status |
| --- | --- | :---: |
| P2-01 | Modeling contract, observation records, 90-day outcome policy | ✅ |
| P2-02 | Leakage and simulator-shortcut guards | ✅ |
| P2-03 | Policy-aware temporal train/validation/test splits | ✅ |
| P2-04 | Versioned 17-feature pipeline and training-only preprocessing | ✅ |
| P2-05 | Seeded logistic-regression baseline | ✅ |
| P2-06 | Frozen XGBoost candidate and controlled comparison | ✅ |
| P2-07 | Leakage-aware feature sanity and shortcut diagnostics | ✅ |
| P2-08 | Probability calibration and operational thresholds | ✅ |
| P2-09 | SHAP-equivalent attribution and explanation boundaries | ✅ |
| P2-10 | Versioned model bundle with bit-for-bit reproducibility | ✅ |
| P2-11 | Final evaluation, MODEL_CARD.md, and Phase 2 decision note | ✅ |
| P2-12 | Release marker `v0.2.0-risk-model` | ✅ |

### ✅ Phase 2R — Modeling Foundation Remediation (24/24 increments complete)
An independent review after P2-07 identified three [claim-blocking limitations](docs/limitations.md). Phase 2R executed a full remediation arc across 6 simulator generations (v1→v6), 13 ADRs, and 24 governed increments — resulting in the Generation v6 bounded sigmoid hazard architecture that passed all acceptance gates.

> Detailed increments: [backlog](docs/backlog.md#phase-2r---modeling-foundation-remediation-gate) · [iteration ledger](docs/experiments/iteration-ledger.md) · [limitation register](docs/limitations.md)

### 🚀 Phase 3 — Policy Conservation Decision Engine (Active)
- Conservation domain contracts and action taxonomy ([ADR 0002](docs/adr/0002-separate-risk-from-action-eligibility.md))
- Deterministic action eligibility rules engine (fail-closed business and regulatory filters)
- Cost-utility and uplift optimization matrix (resource-constrained specialist triage)
- High-throughput zero-dependency model serving gateway (`FastAPI`)
- Model monitoring and drift detection architecture (PSI/CSI & rolling calibration tracking)
- Bounded case intelligence assistant (deterministic template-first with grounded LLM layer)
- Human-in-the-loop workflow and hash-chained audit trail engine
- Counterfactual simulation and offline policy evaluation (OPE)
- Interactive conservation intelligence dashboard (living demonstration)

### ⏳ Future phases (deferred to Phase 4)
- Enterprise distributed infrastructure (Java/Spring microservices, Apache Kafka event streaming)
- Multi-region cloud infrastructure and container orchestration
- Demographic fairness and bias assessment (requires real-world legal and demographic data)

---

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

---

## Repository map

```text
data-contracts/   Versioned fictional data schemas (JSON Schema Draft 2020-12)
simulator/        Seeded policy-event generator and ML pipeline (Python)
ml/               Reserved for finalized modeling artifacts
services/         Java control-plane services and deterministic rules (deferred)
agents/           Bounded evidence, procedure, and planning assistants (deferred)
infra/            Local and cloud infrastructure, added only when justified
docs/             Assumptions, 13 ADRs, 80+ experiment artifacts, modeling contracts
scripts/          Repository validation and developer utilities
datasets/         Published sample dataset with DATA_CARD.md
learnings/        Phase-by-phase R&D notebooks
```

---

## Getting started

**Requirements:** Python 3.11+, GNU Make, Git

```bash
git clone https://github.com/anilreddy89/Inforsight.git
cd Inforsight
make check
```

`make check` runs repository-boundary validation, all published artifact reproducibility checks, focused leakage and model-pipeline tests, data-contract tests, and the complete simulator test suite.

[GitHub Actions](https://github.com/anilreddy89/Inforsight/actions/workflows/ci.yml) runs the same checks on every push and pull request (4 parallel jobs, ~3.5–4.5 min).

---

## Documentation index

| Document | Purpose |
| --- | --- |
| [Problem statement](docs/problem-statement.md) | What we're solving and for whom |
| [Domain assumptions](docs/assumptions.md) | Fictional domain boundaries and simplifications |
| [Limitation register](docs/limitations.md) | Active and resolved claim constraints with closure evidence |
| [Clean-room policy](docs/clean-room-policy.md) | What inputs are allowed and prohibited |
| [Architecture decisions](docs/adr/README.md) | 13 immutable ADRs with alternatives and rationale |
| [Iteration ledger](docs/experiments/iteration-ledger.md) | v1→v6 methods, failures, root causes, and pivots |
| [Backlog](docs/backlog.md) | Ordered roadmap with dependencies and acceptance gates |
| [Threat model](docs/threat-model.md) | Assets, early threats, and controls |
| [MODEL_CARD.md](MODEL_CARD.md) | Full model card with metrics, ethics, and limitations |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution rules and clean-room boundaries |

---

## License

Copyright 2026 Anil Kumar Reddy Jonnala. Licensed under the [Apache License 2.0](LICENSE). Third-party software remains subject to its own license terms.
