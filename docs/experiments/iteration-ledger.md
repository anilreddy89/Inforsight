# Inforsight Iteration Ledger: Methods, Failures, Root Causes, and Architectural Decisions

Last updated: 2026-09-03
Scope: Complete engineering and statistical progression from Phase 0 (Foundation) through Phase 2R.14BB (Post-v4 Redesign Diagnostics)

---

## Executive Summary

Inforsight operates under a **fail-closed, clean-room engineering standard**. When an iteration fails an automated boundary, statistical recovery test, or mathematical constraint, the system does not move the goalposts or fudge data. Instead, it halts, records the failure as an immutable record, publishes an Architecture Decision Record (ADR), and executes a principled redesign.

This document provides the definitive ledger of:
1. What method was attempted in each generation
2. What failed (the observable symptom and metric failure)
3. Why it failed (the mathematical or architectural root cause)
4. What decision was taken (automated gate, ADR, and disposition)
5. What architectural pivot resulted

---

## The Master Iteration Matrix

| Generation / Phase | Method / Modeling Architecture | Observable Failure | Mathematical / System Root Cause | Causal Decision & ADR | Next Architectural Pivot |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **v1: Baseline Pipeline**<br>*(Phase 1 – 2.07)* | • Seeded Markov lifecycle generator<br>• Independent Bernoulli event draws<br>• Point-in-time state reconstruction<br>• Logistic regression & XGBoost<br>• Single-batch issuance, first-billing cutoff | • Train/test confounding (`LIM-002-001`)<br>• Coin-flip discrimination ($\text{AUC} \approx 0.53$)<br>• Reviewer bypassed scoring guard (`LIM-002-003`) | • All policies started at Day 0; first-billing cutoff pushed monthly to train, annual to test.<br>• Generator had zero pre-cutoff feature-to-outcome causality (`LIM-002-002`).<br>• Partition check relied on string naming rather than cryptographic digest. | **`pipeline_engineering_only`**<br><br>ADR 0001 (Clean Room)<br>ADR 0002 (Separate Risk/Action)<br>ADR 0003 (Local Execution) | Launched Phase 2R remediation. Retired v1 test fixture as release holdout; enforced cryptographic scoring authorization. |
| **v2: Multi-Cohort & Frailty**<br>*(Phase 2R.04 – 2R.07)* | • Multi-cohort staggered issuance<br>• Recurring observation windows<br>• Proportional hazards beta coefficients<br>• Latent frailty ($\sigma=0.20$)<br>• Protocol 1.0.0 pre-declared gate | • Automated preflight stop before fitting model (`READINESS-DUAL-TIME-VISIBILITY` failure) | • Ingestion delay leakage: events with `effective_at <= as_of` were ingested into the database after cutoff (`ingested_at > as_of`), leaking retroactive paperwork (`LIM-002-004`). | **`stop`** (fail-closed)<br><br>ADR 0004 (Predeclared Gate) | Prohibited model fitting or test scoring. Required dual-time bitemporal predicate (`effective_at <= as_of AND ingested_at <= as_of`). |
| **v3: Event-First Dual-Time**<br>*(Phase 2R.08 – 2R.11)* | • Dual-time event-first substrate<br>• Matched-null random streams<br>• Explicit oracle sidecars<br>• Temporal folds (embargoed)<br>• Protocol 2.2.0 (20-seed acceptance) | • Decisive signal-recovery failure:<br>  - Signal AUC: $0.519$ (target $\ge 0.65$; $0/20$ passed)<br>  - Null lift: $+0.016$ (target $\ge +0.10$; $0/20$ passed) | • Signal-to-noise ratio in simulator was severely under-specified.<br>• Behavioral log-hazard coefficients produced narrow spread ($\text{std} < 0.35$).<br>• Latent frailty variance overwhelmed observable behavioral signal. | **`redesign`** (fail-closed)<br><br>ADR 0005 (v3 Dual-Time Substrate)<br>ADR 0006 (v4 Diagnostic Boundary) | Halted model qualification. Authorized 6 diagnostic hypotheses (`H1`–`H6`) to isolate failure mechanics before coding. |
| **v4: Signal Amplification**<br>*(Phase 2R.12 – 2R.14)* | • Doubled beta coefficients ($\beta \times 2$)<br>• Halved frailty variance ($\sigma = 0.10$)<br>• Scheduled payment opportunities<br>• Qualification protocol (20 seeds) | • 100% of seeds breached $< 0.20$ monthly hazard ceiling (reached $0.25 - 0.45$)<br>• Brier skill score collapsed ($< 0$)<br>• Extreme early cohort depletion | • **The Exponential Blowup**: In an additive hazard model $\lambda = \lambda_0 \exp(X\beta)$, doubling $\beta$ exponentially explodes the upper tail ($\exp(2) \approx 7.4\times$, $\exp(3) \approx 20\times$).<br>• High-risk policies all lapsed in months 1–3, distorting duration dynamics. | **`redesign`** (fail-closed)<br><br>ADR 0007 (v4 Redesign)<br>ADR 0008 (Post-v4 Diagnostics) | Blocked R2-15 acceptance. Predeclared 17 diagnostics (`D1`–`D17`) and 320-cell feasibility surface to test if proportional hazards can ever work. |
| **v5 Preflight: Contract Governance**<br>*(Phase 2R.14B)* | • Fail-closed pre-result readiness runner<br>• 17 diagnostic procedures (`D1`–`D17`)<br>• 320 Cartesian parameter cells<br>• Contract 1.0.0 | • Runner halted at readiness with decision `stop_contract_not_executable` | • Contract 1.0.0 lacked quantitative, mechanical thresholds distinguishing `supported` from `rejected` for hypotheses `H1`–`H5`.<br>• Allowing analysts to pick thresholds post-hoc would introduce researcher discretion / p-hacking. | **`stop_contract_not_executable`**<br><br>ADR 0009 (Readiness Stop) | Stopped before running a single seed ($0/120$ units executed). Preserved seeds `20280101..20280120` as unspent. |
| **v5 Contract Amendment**<br>*(Phase 2R.14BA)* | • Contract 1.1.0 freezing quantitative truth tables and fail-closed tokens | • None (Governance pre-clearance) | • Replaced contract ambiguity with explicit numerical truth tables ($\text{std} < 0.35$, $\text{AUC} < 0.60$, $\Delta \text{AUC} < 0.02$, hazard $\ge 0.20$). | **`authorized`**<br><br>ADR 0010 (Contract Amendment)<br>Merge `627e698` | Authorized Phase 2R.14BB execution on unspent development seeds without caller discretion. |
| **v5 Diagnostic Execution & Feasibility**<br>*(Phase 2R.14BB)* | • 120 inventory units executed (20 seeds $\times$ 2 scenarios $\times$ 3 folds)<br>• 320-cell Cartesian feasibility surface<br>• Contract 1.1.0 automated truth tables | • **Mathematical Infeasibility**: Exactly **0 of 320 cells** satisfy simultaneous recovery ($\text{AUC} \ge 0.70$) and hazard ceiling ($< 0.20$). | • **The Proportional Hazards Trilemma**: The additive exponential hazards formula ($\lambda_0 \exp(X\beta)$) has NO feasible solution space:<br>  - Keep hazard $< 0.20 \implies$ Score std $< 0.35 \implies \text{AUC} \approx 0.57 - 0.59$ (Failure).<br>  - Scale $\beta$ for $\text{AUC} \ge 0.70 \implies$ Hazard explodes to $0.30 - 0.50$ (Failure). | **`stop_infeasible_design`**<br><br>ADR 0011 (Record Design Infeasibility) | Halted proportional hazards track. Kept Phase 2R.14C blocked. Proves that future success requires a non-exponential / sigmoid link or event-driven state machine. |

---

## Detailed Deep-Dives by Generation

### Generation 1: The Pipeline Engineering Baseline (Phases 1.01 – 2.07)
- **Primary Goal**: Establish event sourcing, temporal point-in-time reconstruction, feature pipelines, and baseline machine learning models (Logistic Regression and XGBoost).
- **The Method**: Policies generated with independent random draws. Observations taken at the policy's first bill date with a 90-day forward outcome window.
- **The Failure**:
  1. *Temporal Confounding (`LIM-002-001`)*: Because all policies were issued at Day 0, first billing occurred at Day 30 for monthly, Day 90 for quarterly, and Day 365 for annual. When split chronologically, training got only monthly policies and test got only annual policies.
  2. *Zero Feature Signal (`LIM-002-002`)*: Lapses were assigned uniformly at random. Models scored $\text{AUC} \approx 0.53$ (barely beating coin flip).
  3. *Scoring Security Vulnerability (`LIM-002-003`)*: The evaluation code authorized test scoring based on a caller-supplied string label (`partition="validation"`), which could be tricked.
- **The Architectural Response**:
  - Bound all v1 results to `pipeline_engineering_only`.
  - Created cryptographic scoring authorization (ADR 0004) requiring SHA-256 matrix digests.
  - Retired the v1 test fixture as an untouched release holdout.

### Generation 2: Multi-Cohort & The Ingestion Leakage Stop (Phases 2R.04 – 2R.07)
- **Primary Goal**: Introduce multi-cohort issuance to eliminate billing frequency confounding, add recurring observation windows, and introduce a proportional hazards risk model.
- **The Method**: Staggered policy start dates over multiple calendar years. Added beta coefficients for behavioral drivers (billing frequency, arrears, customer service contacts) and latent frailty.
- **The Failure (`LIM-002-004`)**:
  - The automated preflight readiness audit (`READINESS-DUAL-TIME-VISIBILITY`) caught an event where `effective_at <= as_of` but `ingested_at > as_of`.
  - The feature engineering pipeline had processed the event because its effective date was in the past, even though in the real world the paperwork had not yet arrived at the cutoff date!
- **The Architectural Response**:
  - **Fail-Closed Stop**: The runner aborted immediately with decision `stop`. Zero models were fitted.
  - **ADR 0005**: Established the strict bitemporal requirement: an event is visible to an ML feature if and only if **both** `effective_at <= as_of` AND `ingested_at <= as_of`.

### Generation 3: Event-First Dual-Time & The Signal Recovery Collapse (Phases 2R.08 – 2R.11)
- **Primary Goal**: Implement the event-first dual-time substrate and execute formal statistical acceptance across 20 independent seed pairs under Protocol 2.2.0.
- **The Method**: 14,400 policies generated with dual timestamps, matched-null control streams (identical random numbers but zero risk signal), and temporal evaluation folds.
- **The Failure**:
  - Model fitting ran cleanly with zero leakage. However, statistical evaluation failed decisively:
    - Target: Signal $\text{AUC} \ge 0.65$ across $\ge 80\%$ of seeds. Observed: Median AUC was **$0.5188$** ($0/20$ passed).
    - Target: Matched-null improvement $\ge +0.10$. Observed: Median lift was **$+0.016$** ($0/20$ passed).
- **The Architectural Response**:
  - **Fail-Closed Redesign**: Rather than lowering the acceptance threshold from $0.65$ to $0.52$, the system triggered a mechanical `redesign` decision.
  - **ADR 0006**: Bounded diagnostic investigation freezing 6 explicit scientific hypotheses (`H1`–`H6`) to isolate why the signal was so weak.

### Generation 4: Signal Amplification & The Hazard Ceiling Explosion (Phases 2R.12 – 2R.14)
- **Primary Goal**: Amplify behavioral signal to achieve the required AUC recovery.
- **The Method**: Doubled behavioral log-hazard coefficients ($\beta \times 2$), halved latent frailty variance ($\sigma = 0.2 \to 0.1$), and introduced scheduled recurring payment opportunities.
- **The Failure**:
  - Diagnostics showed that while oracle AUC rose toward $\sim 0.60$, **100% of seeds breached the $< 0.20$ monthly hazard bound**.
  - In high-risk policies, the exponential hazard exploded ($\lambda > 0.35 - 0.50$). In life insurance, a 30% monthly lapse rate means ~70% of high-risk customers vanish within 90 days.
  - This extreme attrition distorted cohort survival, destroyed Brier skill score, and produced uncalibrated probabilities.
- **The Architectural Response**:
  - **Fail-Closed Redesign**: Blocked R2-15 acceptance and model deployment.
  - **ADR 0008**: Authorized an exhaustive 320-cell feasibility grid and 17 diagnostics to evaluate whether any parameter combination of the exponential hazard model could work.

### Generation 5: The Feasibility Surface & Proof of Infeasibility (Phases 2R.14B – 2R.14BB)
- **Primary Goal**: Run 17 diagnostics across 120 inventory units (20 unspent seeds $\times$ 2 scenarios $\times$ 3 folds) and exhaustively evaluate all 320 Cartesian parameter combinations across coefficient scale, frailty variance, and baseline intercepts.
- **The Method**:
  - *Phase 2R.14B*: Fail-closed readiness caught missing quantitative thresholds in Contract 1.0.0; halted at readiness (`stop_contract_not_executable`, ADR 0009).
  - *Phase 2R.14BA*: Approved Contract 1.1.0 with frozen numerical truth tables (ADR 0010, commit `627e698`).
  - *Phase 2R.14BB*: Executed all 120 units and evaluated all 320 cells under strict automated rules.
- **The Empirical Finding**:
  - **$0$ of $320$ cells** satisfy simultaneous recovery ($\text{AUC} \ge 0.70$) and actuarial bounds (hazard $< 0.20$).
  - Mathematical Proof:
    $$\lambda(t) = \lambda_0(t) \exp(X\beta)$$
    - To get $\text{AUC} \ge 0.70$, $X\beta$ must have standard deviation $\ge 0.8 - 1.0$, producing scores $\ge 2.5 - 3.0$.
    - But $\exp(3.0) \approx 20.1$, which multiplies baseline hazard by $20\times$, blowing past the $0.20$ ceiling.
    - Squeezing coefficients to keep hazard $< 0.20$ squashes score spread to $\text{std} < 0.35$, yielding $\text{AUC} \approx 0.57 - 0.59$.
- **The Architectural Response**:
  - **`stop_infeasible_design`**: Proposed **ADR 0011**.
  - Proved that the additive exponential proportional hazards formulation is mathematically incapable of generating realistic insurance data with learnable signal.
  - Halted R2-14C substrate implementation, saving months of wasted engineering.

---

## Architectural Lessons for Real-World AI Systems

1. **Pre-commit to thresholds BEFORE looking at outputs**: If you pick your pass/fail line after seeing model scores, you are deceiving yourself and your stakeholders.
2. **Automated gates prevent human bias**: In v1, v2, v3, v4, and v5, human temptation would have been to *"just tweak the threshold slightly to make it pass"*. The automated fail-closed scripts prevented this at every step.
3. **Documenting what failed is more valuable than fake success**: ADR 0011 permanently preserves the proof that additive proportional hazards fail under realistic hazard bounds, ensuring the engineering organization never repeats this mistake.
4. **Clean-room holdouts must remain unmaterialized**: Through all 5 generations, the reserved acceptance seeds (`20271201..20271220`) and the final release holdout have remained strictly untouched.

