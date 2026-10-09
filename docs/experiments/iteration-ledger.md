# Inforsight Iteration Ledger: Methods, Failures, Root Causes, and Architectural Decisions

Last updated: 2026-10-09 (factual corrections; see [Corrections](#corrections-2026-10-09))
Scope: Complete engineering and statistical progression from Phase 0 (Foundation) through Phase 2R.14BB (Post-v4 Redesign Diagnostics). Generation v6 and the `v0.2.0-risk-model` release are outside this scope; see ADR 0012, ADR 0013 and `MODEL_CARD.md`.

Where this ledger and a primary record (ADR, decision note, report or manifest) disagree, the primary record governs.

---

## Executive Summary

Inforsight operates under a **fail-closed, clean-room engineering standard**. When an iteration fails an automated boundary, statistical recovery test, or mathematical constraint, the system does not move the goalposts or fudge data. Instead, it halts, records the failure as an immutable record, publishes an Architecture Decision Record (ADR), and executes a principled redesign. Within this ledger's scope, no acceptance threshold was changed after its results were seen. Later, for generation v6, ADR 0013 revised four secondary thresholds after the Protocol `3.0.0` results, with every primary gate unchanged.

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
| **v1: Baseline Pipeline**<br>*(Phase 1 – 2.07)* | • Seeded scenario generator: four outcome scenarios in equal shares, shuffled independently of policy attributes<br>• Point-in-time state reconstruction<br>• Logistic regression & XGBoost<br>• Issuance within the first 30 days, first-billing cutoff | • Train/test confounding (`LIM-002-001`)<br>• Near-chance validation discrimination ($\text{AUC}$ $0.564$ logistic, $0.533$ XGBoost; 27 records)<br>• Reviewer bypassed scoring guard (`LIM-002-003`) | • All policies were issued within the first 30 days, so billing frequency set the first-billing cutoff: monthly policies landed in train, annual in test.<br>• Generator had zero pre-cutoff feature-to-outcome causality (`LIM-002-002`).<br>• Partition check relied on string naming rather than bound digests. | **`pipeline_engineering_only`**<br><br>ADR 0001 (Clean Room)<br>ADR 0002 (Separate Risk/Action)<br>ADR 0003 (Local Execution) | Launched Phase 2R remediation. Reclassified the v1 test fixture as review-exposed historical evidence; R2-03 added digest-bound scoring authorization. |
| **v2: Multi-Cohort & Frailty**<br>*(Phase 2R.04 – 2R.07)* | • Multi-cohort staggered issuance<br>• Recurring observation windows<br>• Monthly discrete-time competing hazards (lapse, surrender)<br>• Latent frailty ($\sigma=0.35$)<br>• Protocol 1.0.0 pre-declared gate | • Automated readiness stop before the acceptance run fitted any model (`READINESS-DUAL-TIME-VISIBILITY` and seven other failed readiness rules)<br>• Earlier R2-06 baselines: $\text{AUC}$ $0.543$ (logistic), $0.551$ (XGBoost) | • Ingestion delay leakage: events with `effective_at <= as_of` were ingested into the database after cutoff (`ingested_at > as_of`), leaking retroactive paperwork (`LIM-002-004`). | **`stop`** (fail-closed)<br><br>ADR 0004 (Predeclared Gate) | Prohibited model fitting or test scoring. Required dual-time bitemporal predicate (`effective_at <= as_of AND ingested_at <= as_of`). |
| **v3: Event-First Dual-Time**<br>*(Phase 2R.08 – 2R.11)* | • Dual-time event-first substrate<br>• Matched-null random streams<br>• Explicit oracle sidecars<br>• Temporal folds (embargoed)<br>• Protocol 2.2.0 (20-seed acceptance) | • Decisive signal-recovery failure:<br>  - Median signal AUC: $0.519$ (required $\ge 0.68$); seeds with AUC $\ge 0.65$: $0/20$ (required $16/20$)<br>  - Null lift: $+0.016$ (target $\ge +0.10$; $0/20$ passed) | • R2-13 diagnostics: even the oracle restricted to observable features reached median $\text{AUC}$ $0.533$ ($0/20$ seeds $\ge 0.65$), so the simulated observable signal was too weak.<br>• `rolling_payment_count`, a registered driver, was nearly constant.<br>• ADR 0007 treated coefficient size and latent frailty ($\sigma = 0.35$) as diagnosed mechanism classes. | **`redesign`** (fail-closed)<br><br>ADR 0005 (v3 Dual-Time Substrate)<br>ADR 0006 (v4 Diagnostic Boundary) | Halted model qualification. Authorized 6 diagnostic hypotheses (`H1`–`H6`) to isolate failure mechanics before coding. |
| **v4: Signal Amplification**<br>*(Phase 2R.12 – 2R.14)* | • Doubled public coefficients ($\beta \times 2$)<br>• Latent frailty $\sigma$ reduced from $0.35$ to $0.20$<br>• Scheduled payment opportunities at each policy's billing frequency<br>• Recalibrated cause-specific intercepts<br>• Qualification protocol (20 seeds) | • Median observable-oracle $\text{AUC}$ $0.567$ ($0/20$ seeds $\ge 0.65$); median AP lift $0.022$<br>• $0/20$ reference fits $\ge 0.65$<br>• Maximum monthly terminal hazard $0.2185$ against $< 0.20$ (1 of 20 seeds)<br>• Oracle probability-quality gate failed (median Brier skill $+0.0035$) | • ADR 0008: the evidence rejected R2-15 entry but did not isolate the remaining failure mechanism.<br>• Doubling coefficients raised observable-oracle $\text{AUC}$ only from $0.533$ to $0.567$, while the hazard tail crossed the ceiling. | **`redesign`** (fail-closed)<br><br>ADR 0007 (v4 Redesign)<br>ADR 0008 (Post-v4 Diagnostics) | Blocked R2-15 acceptance. Predeclared 17 diagnostics (`D1`–`D17`) and 320-cell feasibility surface to test if proportional hazards can ever work. |
| **v5 Preflight: Contract Governance**<br>*(Phase 2R.14B)* | • Fail-closed pre-result readiness runner<br>• 17 diagnostic procedures (`D1`–`D17`)<br>• 320 Cartesian parameter cells<br>• Contract 1.0.0 | • Runner halted at readiness with decision `stop_contract_not_executable` | • Contract 1.0.0 lacked quantitative, mechanical thresholds distinguishing `supported` from `rejected` for hypotheses `H1`–`H5`.<br>• Allowing analysts to pick thresholds post-hoc would introduce researcher discretion / p-hacking. | **`stop_contract_not_executable`**<br><br>ADR 0009 (Readiness Stop) | No authorized unit ran ($0/120$ executed). An uncommitted local attempt with implementation-defined thresholds was excluded as unauthorized evidence (ADR 0009). Seeds `20280101..20280120` stayed unspent by an authorized run. |
| **v5 Contract Amendment**<br>*(Phase 2R.14BA)* | • Contract 1.1.0 freezing quantitative truth tables and fail-closed tokens | • None (Governance pre-clearance) | • Replaced contract ambiguity with explicit numerical truth tables ($\text{std} < 0.35$, $\text{AUC} < 0.60$, $\Delta \text{AUC} < 0.02$, hazard $\ge 0.20$). | **`authorized`**<br><br>ADR 0010 (Contract Amendment)<br>Merge `627e698` | Authorized Phase 2R.14BB execution on unspent development seeds without caller discretion. |
| **v5 Diagnostic Execution & Feasibility**<br>*(Phase 2R.14BB)* | • 120 inventory units executed (20 seeds $\times$ 2 scenarios $\times$ 3 folds)<br>• 320-cell Cartesian feasibility surface<br>• Contract 1.1.0 automated truth tables | • **Infeasibility**: Exactly **0 of 320 cells** satisfy recovery ($\text{AUC} \ge 0.70$ and AP lift $\ge 0.10$) together with the hazard ceiling ($< 0.20$). | • **The Proportional Hazards Trilemma** (ADR 0011): the additive proportional-hazards specification cannot simultaneously recover the signal and respect the monthly hazard bound.<br>• In the committed grid no cell reached $\text{AUC}$ $0.70$: the best was $0.593$ (max AP lift $0.043$). AUC stayed at $0.591$–$0.593$ at every coefficient scale from $1.0$ to $3.0$, while peak hazard rose from $0.05$ to $0.88$; 219 of 320 cells breached the ceiling. | **`stop_infeasible_design`**<br><br>ADR 0011 (Record Design Infeasibility) | Halted proportional hazards track. Kept Phase 2R.14C blocked. Concluded that a different hazard specification was required (ADR 0012 later adopted a bounded sigmoid link). |

---

## Detailed Deep-Dives by Generation

### Generation 1: The Pipeline Engineering Baseline (Phases 1.01 – 2.07)
- **Primary Goal**: Establish event sourcing, temporal point-in-time reconstruction, feature pipelines, and baseline machine learning models (Logistic Regression and XGBoost).
- **The Method**: Four outcome scenarios (active, recovered, lapsed, surrendered) were assigned in equal shares and shuffled, independent of policy attributes. Observations taken at the policy's first bill date with a 90-day forward outcome window.
- **The Failure**:
  1. *Temporal Confounding (`LIM-002-001`)*: Because all policies were issued within the first 30 days, first billing fell about 30 days after issue for monthly, 90 for quarterly, 182 for semiannual and 365 for annual policies. When split chronologically, training got monthly policies, validation semiannual and test annual.
  2. *Zero Feature Signal (`LIM-002-002`)*: Outcomes were assigned at random, independent of the features. Validation AUC was $0.564$ (logistic regression) and $0.533$ (XGBoost) on 27 records, near chance.
  3. *Scoring Security Vulnerability (`LIM-002-003`)*: The evaluation code authorized test scoring based on a caller-supplied string label (`partition="validation"`), which could be tricked.
- **The Architectural Response**:
  - Bound all v1 results to `pipeline_engineering_only`.
  - Added digest-bound scoring authorization (R2-03, scoring authorization contract `1.0.0`) that binds exact membership, row order and matrix identity. It is a local integrity guard, not a hard security boundary.
  - Reclassified the v1 test fixture as review-exposed historical evidence; it is no longer described as untouched.

### Generation 2: Multi-Cohort & The Ingestion Leakage Stop (Phases 2R.04 – 2R.07)
- **Primary Goal**: Introduce multi-cohort issuance to eliminate billing frequency confounding, add recurring observation windows, and introduce a stochastic monthly competing-hazards risk mechanism.
- **The Method**: Staggered policy start dates over multiple calendar years. Added coefficients for observable drivers (billing frequency, arrears, service contacts) and latent frailty ($\sigma = 0.35$).
- **The Failure (`LIM-002-004`)**:
  - The automated preflight readiness audit (`READINESS-DUAL-TIME-VISIBILITY`) caught an event where `effective_at <= as_of` but `ingested_at > as_of`.
  - The feature engineering pipeline had processed the event because its effective date was in the past, even though in the real world the paperwork had not yet arrived at the cutoff date!
  - It was one of eight failed readiness rules.
- **The Architectural Response**:
  - **Fail-Closed Stop**: The runner aborted immediately with decision `stop`. The acceptance run fitted no model. (The earlier R2-06 baseline comparison had fitted logistic regression and XGBoost: AUC $0.543$ and $0.551$ on 269 selection records.)
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
- **The Method**: Doubled public coefficients ($\beta \times 2$), reduced latent frailty $\sigma$ from $0.35$ to $0.20$, introduced scheduled payment opportunities at each policy's billing frequency, and recalibrated cause-specific intercepts.
- **The Failure**:
  - Median observable-oracle AUC rose only to $0.567$ ($0/20$ seeds $\ge 0.65$; median AP lift $0.022$), and no reference fit reached $0.65$.
  - The maximum monthly terminal hazard was $0.2185$ against the $< 0.20$ rule; one of 20 seeds crossed it.
  - The oracle probability-quality gate failed (median Brier skill $+0.0035$).
- **The Architectural Response**:
  - **Fail-Closed Redesign**: Blocked R2-15 acceptance and model deployment.
  - **ADR 0008**: Recorded that this evidence did not isolate the failure mechanism, and authorized an exhaustive 320-cell feasibility grid and 17 diagnostics to evaluate whether any parameter combination of the proportional-hazards model could work.

### Generation 5: The Feasibility Surface & Proof of Infeasibility (Phases 2R.14B – 2R.14BB)
- **Primary Goal**: Run 17 diagnostics across 120 inventory units (20 unspent seeds $\times$ 2 scenarios $\times$ 3 folds) and exhaustively evaluate all 320 Cartesian parameter combinations across coefficient scale, frailty variance, and baseline intercepts.
- **The Method**:
  - *Phase 2R.14B*: Fail-closed readiness caught missing quantitative thresholds in Contract 1.0.0; halted at readiness (`stop_contract_not_executable`, ADR 0009).
  - *Phase 2R.14BA*: Approved Contract 1.1.0 with frozen numerical truth tables (ADR 0010, commit `627e698`).
  - *Phase 2R.14BB*: Executed all 120 units and evaluated all 320 cells under strict automated rules.
- **The Empirical Finding**:
  - **$0$ of $320$ cells** satisfy recovery ($\text{AUC} \ge 0.70$ and AP lift $\ge 0.10$) together with actuarial bounds (hazard $< 0.20$).
  - What the committed grid shows (`phase-02r-14bb-v5-redesign-diagnostic-manifest.json`):
    - No cell reached $\text{AUC}$ $0.70$. The best was $0.593$, and the largest AP lift was $0.043$.
    - AUC stayed at $0.591$–$0.593$ at every public coefficient scale from $1.0$ to $3.0$, while peak monthly hazard rose from $0.05$ to $0.88$.
    - 101 cells kept hazard below $0.20$; the other 219 breached it.
- **The Architectural Response**:
  - **`stop_infeasible_design`**: Proposed **ADR 0011**.
  - Recorded that no searched setting of the additive proportional-hazards specification recovered the signal within the hazard bound.
  - Halted R2-14C substrate implementation for the infeasible design.

---

## Architectural Lessons for Real-World AI Systems

1. **Pre-commit to thresholds BEFORE looking at outputs**: If you pick your pass/fail line after seeing model scores, you are deceiving yourself and your stakeholders.
2. **Automated gates prevent human bias**: From v2 to v5, mechanical gates under versioned protocols returned every verdict, and no acceptance threshold was changed after results. v1 had no acceptance gate; its limits came from an independent review. (Outside this ledger's scope, ADR 0013 revised four secondary v6 thresholds after the Protocol `3.0.0` results, with primary gates unchanged.)
3. **Documenting what failed is more valuable than fake success**: ADR 0011 permanently preserves the evidence that the searched additive proportional-hazards settings failed under realistic hazard bounds, so the design is not repeated.
4. **Clean-room holdouts must remain unmaterialized**: Through all 5 generations, the reserved acceptance seeds (`20271201..20271220`) and the final release holdout have remained strictly untouched.

---

## Corrections (2026-10-09)

Earlier versions of this ledger disagreed with the primary records below. Each claim was corrected to match the record; nothing else changed.

| Section | Earlier claim | Corrected from |
| --- | --- | --- |
| v1 | Markov generator with independent Bernoulli event draws; all policies issued at Day 0 | `simulator/src/inforsight_simulator/generator.py`: four outcome scenarios in equal shares, shuffled; issue dates in the first 30 days |
| v1 | AUC ≈ 0.53 | `phase-02-05` and `phase-02-06` reports: validation AUC 0.564 (logistic) and 0.533 (XGBoost) on 27 records |
| v1 | Cryptographic scoring authorization created by ADR 0004 | `LIM-002-003`: R2-03 digest-bound scoring authorization, a local integrity guard rather than a security boundary |
| v2 | Proportional hazards; latent frailty σ = 0.20 | `phase-02r-04-v2-statistical-simulator-and-observation-contract.md`: monthly discrete-time competing hazards; frailty σ = 0.35 |
| v2 | Zero models were fitted | R2-07 decision: the acceptance run fitted none; `phase-02r-06-v2-baseline-comparison-report.md`: baselines AUC 0.5427 and 0.5514 |
| v3 | Signal AUC 0.519 against target ≥ 0.65 | `phase-02r-11-v3-statistical-acceptance-report.md`: median 0.519 against ≥ 0.68; 0/20 seeds ≥ 0.65 against 16/20 required |
| v3 | Narrow score spread (std < 0.35) as a root cause | ADR 0007: the R2-13 findings were weak observable-oracle separability (median AUC 0.533) and a near-constant driver; the std < 0.35 measure comes from the later v5 diagnostics |
| v4 | Frailty halved to σ = 0.10; 100% of seeds breached the hazard ceiling at 0.25–0.45; Brier skill below zero; early cohort depletion | ADR 0007: σ 0.35 → 0.20. ADR 0008 and `phase-02r-14-v4-qualification-report.md`: peak hazard 0.2185 (1 of 20 seeds over 0.20), median Brier skill +0.0035; no depletion finding is recorded |
| v4 | Exponential blowup of high-risk policies in months 1–3 as the root cause | ADR 0008: the evidence did not isolate the failure mechanism |
| v5 | Stopped before running a single seed | ADR 0009: no authorized unit ran; an uncommitted local attempt was excluded as unauthorized evidence |
| v5 | Recovery defined as AUC ≥ 0.70 only; raising coefficients for AUC ≥ 0.70 drives hazard to 0.30–0.50; a "mathematical proof" of infeasibility | ADR 0011 and the v5 manifest: recovery also needs AP lift ≥ 0.10; no cell exceeded AUC 0.593 at any coefficient scale while peak hazard reached 0.88. The earlier argument was heuristic and is not supported by the grid |
| Lessons | Automated scripts prevented threshold changes in every generation, including v1 | v1 had no acceptance gate; ADR 0013 later revised four secondary v6 thresholds after results |
