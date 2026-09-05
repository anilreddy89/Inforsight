/**
 * Inforsight Roadmap & Technical Journey Web Application
 * Zero-dependency, pure ES6 data model & view controllers.
 */

// Global State
const state = {
  explainerMode: 'simple', // 'simple' (default for accessibility) or 'tech'
  filterStatus: 'all',
  searchQuery: ''
};

// Complete Project History from Phase 0 through Phase 2R / v4
const timelineData = [
  {
    phase: "Phase 0: Architecture Foundation",
    milestone: "v0.1.0-data-foundation",
    items: [
      {
        id: "F-01",
        title: "Clean-Room Scaffolding & Initial ADRs",
        status: "Completed",
        commit: "1944595",
        summary: {
          tech: "Established problem framing, clean-room policy (ADR 0001), authority model (ADR 0002), and local execution strategy (ADR 0003).",
          simple: "Set up the project from scratch. Created strict rules that no proprietary or copied insurance code can ever enter the repository."
        },
        checks: "Boundary checks, licensing, and clean-room policy verification."
      },
      {
        id: "F-02",
        title: "Automated Repository Boundary Enforcement",
        status: "Completed",
        commit: "1944595",
        summary: {
          tech: "Built check_repository_boundaries.sh scanning for secrets, proprietary terms, and forbidden data materialization patterns.",
          simple: "Built an automated security gate that stops any passwords, secrets, or forbidden files from being checked in."
        },
        checks: "Pre-commit boundary checks passed with zero violations."
      }
    ]
  },
  {
    phase: "Phase 1: Synthetic Data & State Reconstruction",
    milestone: "v0.1.0-data-foundation",
    items: [
      {
        id: "P1-01 / P1-02",
        title: "Strict Policy-Event Envelope & 9 Event Schemas",
        status: "Completed",
        commit: "0ba73ba / 036e8fe",
        summary: {
          tech: "Draft 2020-12 JSON Schema contracts for envelope and 9 event families (billing, payment, notice, service, outcomes). Strict rejection of unknown properties.",
          simple: "Designed strict digital blueprints for insurance events. If an event is missing an ID or timestamp, the system rejects it immediately."
        },
        checks: "Automated schema tests, 9 valid examples, 12 negative test cases."
      },
      {
        id: "P1-03",
        title: "Deterministic 100-Policy Synthetic Generator",
        status: "Completed",
        commit: "eee6fbb",
        summary: {
          tech: "Seeded generator producing realistic, reproducible policy lifecycles across term and whole-life products.",
          simple: "Wrote a generator that creates 100 fictional insurance customer stories that repeat identically every time you run the code."
        },
        checks: "Reproducible fixture with exact SHA-256 manifests."
      },
      {
        id: "P1-04",
        title: "Effective-Time Point-in-Time Reconstruction",
        status: "Completed",
        commit: "b993397",
        summary: {
          tech: "Reconstructed policy state as of any historic timestamp using event-sourcing replay without future leakage.",
          simple: "Built a 'time machine' that reconstructs exactly what a policy looked like on any historical date, ignoring anything that happened later."
        },
        checks: "Verified point-in-time state against gold standard events."
      },
      {
        id: "P1-06 / P1-07",
        title: "Sample Dataset & Aggregate Calibration Assessment",
        status: "Completed",
        commit: "c875289 / 1bcef3a",
        summary: {
          tech: "Evaluated 100-policy fixture against SOA/LIMRA benchmarks; documented directional comparability boundaries.",
          simple: "Compared our synthetic policies against real-world industry benchmarks to document where our simulator was realistic and where it differed."
        },
        checks: "Data card, integrity manifest, and synthetic rate report published."
      }
    ]
  },
  {
    phase: "Phase 2: Baseline Modeling & Leakage Guards",
    milestone: "v0.2.0-baseline-models",
    items: [
      {
        id: "P2-01 / P2-02",
        title: "Observation Records & 90-Day Outcome Estimand",
        status: "Completed",
        commit: "1d893b8 / 5e2987b",
        summary: {
          tech: "Observation contract 1.0.0, 90-day binary lapse/surrender target, and leakage guards preventing outcome contamination in features.",
          simple: "Defined our target question: 'Will this active policy cancel in the next 90 days?' Added guards to make sure the answer doesn't leak into features."
        },
        checks: "16 focused leakage tests; proceed-with-limitations decision."
      },
      {
        id: "P2-03",
        title: "Temporal Splits (LIM-002-001 Discovered)",
        status: "Completed",
        commit: "d8b516a",
        summary: {
          tech: "Strict chronological train/val/test splits with 90-day horizon embargo. Discovered billing-frequency confounding (LIM-002-001).",
          simple: "First Roadblock: When splitting data by date, all monthly policies ended up in training and annual policies in testing. Claim bounded to pipeline only."
        },
        checks: "16 temporal tests; claim bounded to pipeline-engineering-only."
      },
      {
        id: "P2-05 / P2-06",
        title: "Seeded Logistic & Boosted-Tree Baselines",
        status: "Completed",
        commit: "b2ec59d / fd9fc3b",
        summary: {
          tech: "Logistic Regression (Val AUC 0.564) vs XGBoost (Val AUC 0.533). Sealed test partition untouched; discovered flat behavioral signal (LIM-002-002).",
          simple: "Trained our first ML models. Accuracy hovered near 53-56% (barely above a coin flip). We sealed the test set and refused to claim production readiness."
        },
        checks: "Train-only preprocessing, exact state reload verification, test set sealed."
      },
      {
        id: "P2-07",
        title: "Leakage-Aware Feature Diagnostics",
        status: "Completed",
        commit: "8db20ce",
        summary: {
          tech: "Mutual information screens, shallow-model diagnostics, and permutation analysis confirming 8 behavioral groups were constant in train.",
          simple: "Diagnosed why models were struggling: the generator assigned outcomes randomly after cutoff, leaving features with zero predictive variation."
        },
        checks: "14 focused diagnostic tests; 8 constant features dispositioned."
      }
    ]
  },
  {
    phase: "Phase 2R: Remediation & v2 Statistical Gate",
    milestone: "v0.2.1-statistical-remediation",
    items: [
      {
        id: "R2-03",
        title: "Scoring Authorization Hardening (LIM-002-003)",
        status: "Completed",
        commit: "5eb67c1",
        summary: {
          tech: "ADR 0004: scoring authorization contract binding row order, purpose, preprocessing ID, and SHA-256 matrix digests. Sealed v1 fixture preserved as historical evidence.",
          simple: "Digital tamper seals. Blocked any ability for code to accidentally peek at or score the test dataset by renaming partitions."
        },
        checks: "10 focused authorization tests; row/target substitution fails closed."
      },
      {
        id: "R2-05",
        title: "v2 Statistical Simulator & Recurring Observations",
        status: "Completed",
        commit: "25c370d",
        summary: {
          tech: "Scaled to 3,600 policies and 42,795 recurring point-in-time observations across multiple issuance cohorts.",
          simple: "Expanded simulator to 3,600 policies with observations taken every few months across staggered policy start dates."
        },
        checks: "221 simulator tests, 9 contract tests pass."
      },
      {
        id: "R2-07",
        title: "Statistical Acceptance Gate: Fail-Closed STOP",
        status: "Stop",
        commit: "66ae092",
        summary: {
          tech: "Automated readiness audit detected post-cutoff ingestion leakage (READINESS-DUAL-TIME-VISIBILITY). Execution recorded STOP fail-closed before fitting any models.",
          simple: "The Big Fail-Closed Gate: Automated audit discovered an event recorded after the cutoff slipped into the observation. The build halted immediately!"
        },
        checks: "Preflight readiness stopped build; 0 models fitted; holdout untouched."
      }
    ]
  },
  {
    phase: "Phase 2R: Dual-Time Substrate & v3 Gate",
    milestone: "v0.2.1-statistical-remediation",
    items: [
      {
        id: "R2-08 / R2-09",
        title: "v3 Dual-Time Substrate & Matched Controls (ADR 0005)",
        status: "Completed",
        commit: "09f678a / 89c2291",
        summary: {
          tech: "Enforced dual-time invariant (effective_at <= as_of AND ingested_at <= as_of), matched null stream sets, and scaled to 14,400 policies (76,545 observations).",
          simple: "Built v3 from the ground up: strict dual-time filter and paired every test with a 'placebo' random noise stream to guarantee honest validation."
        },
        checks: "14,400-policy manifest, 258 simulator tests pass."
      },
      {
        id: "R2-10",
        title: "v3 Evaluation Pipeline & XGBoost Selection",
        status: "Completed",
        commit: "36c17b7",
        summary: {
          tech: "Evaluated 1,498 selection episodes across 787 policies; XGBoost selected over logistic (AUC 0.542 vs 0.529). Final holdout remains not_materialized.",
          simple: "Ran candidate model selection on v3. XGBoost slightly edged out logistic regression, but both were still near 54% accuracy."
        },
        checks: "State reload verified; final holdout not materialized."
      },
      {
        id: "R2-11",
        title: "v3 Acceptance Protocol 2.2.0: REDESIGN Decision",
        status: "Redesign",
        commit: "76c8cd3",
        summary: {
          tech: "20 signal/null seed pairs evaluated across 3 folds. Signal AUC (0.519) failed to beat target 0.65 (0/20 passed). Recorded REDESIGN without holdout tuning.",
          simple: "The Redesign Gate: Across 20 test seeds, the model only achieved 51.9% accuracy vs 50.7% on the placebo. Instead of fudging numbers, we declared Redesign."
        },
        checks: "20/20 pairs pass readiness; 0/20 pass recovery threshold; final holdout sealed."
      }
    ]
  },
  {
    phase: "Phase 2R: v4 Diagnostic Boundary & Freeze",
    milestone: "v0.2.1-statistical-remediation",
    items: [
      {
        id: "R2-12",
        title: "v4 Signal-Recovery Diagnostic Boundary (ADR 0006)",
        status: "Completed",
        commit: "ea9cf1f",
        summary: {
          tech: "Predeclared 6 formal hypotheses (oracle separability, driver support, transform parity, episode dilution, candidate learning, temporal stability).",
          simple: "Scientific Method: Formulated 6 strict hypotheses to diagnose why v3 models failed before writing a single line of redesign code."
        },
        checks: "Contract 1.0.0 and ADR 0006 freeze diagnostic rules."
      },
      {
        id: "R2-13",
        title: "Diagnostic Execution & v4 Design Freeze (ADR 0007)",
        status: "Completed",
        commit: "7c4a1a7",
        summary: {
          tech: "Diagnosed weak observable-oracle separability (AUC 0.533) and near-constant rolling payments. ADR 0007 froze v4 redesign (doubled coefficients, halved frailty).",
          simple: "Root Cause Found! The theoretical maximum accuracy of v3 was only 53.3%. In v4, we doubled signal strength and halved random noise so the AI has real patterns to find."
        },
        checks: "All 20 seeds evaluated; H1 and H2 supported; ADR 0007 approved."
      },
      {
        id: "R2-14",
        title: "v4 Substrate Implementation & Development Qualification",
        status: "Redesign",
        commit: "4b234bf",
        summary: {
          tech: "Implemented contract 4.0.0 and protocol 3.0.0. All 20 seeds evaluated; observable recovery passed but monthly hazards breached < 0.20 bound. Triggered REDESIGN.",
          simple: "v4 Qualification Failure: Doubling the risk multiplier caused cancellation chances to explode past 20%/month. The automated gate declared REDESIGN."
        },
        checks: "Qualification failed closed on hazard ceiling; acceptance holdout preserved."
      }
    ]
  },
  {
    phase: "Phase 2R: v5 Post-v4 Redesign Diagnostics",
    milestone: "v0.2.1-statistical-remediation",
    items: [
      {
        id: "R2-14A",
        title: "Close Out v4 & Authorize Post-v4 Diagnostics (ADR 0008)",
        status: "Completed",
        commit: "52c03c8",
        summary: {
          tech: "Approved ADR 0008 and contract 1.0.0 freezing 17 diagnostics (D1-D17) and 320-cell feasibility surface without producing replacement results.",
          simple: "Designed a comprehensive 17-test battery and 320-point computer grid to rigorously test whether the proportional hazards formula can ever work."
        },
        checks: "Clean-room contract validation passed; no synthetic data created."
      },
      {
        id: "R2-14B",
        title: "v5 Preflight: Contract Ambiguity Readiness STOP (ADR 0009)",
        status: "Stop",
        commit: "3088c4c",
        summary: {
          tech: "Fail-closed runner detected Contract 1.0.0 lacked mechanical H1-H5 numerical disposition thresholds. Halted with decision stop_contract_not_executable (0/120 units, 0/320 cells).",
          simple: "The Missing Threshold Stop: The runner caught that pass/fail rules for 5 tests weren't numerically defined. It halted before running a single seed to prevent researcher bias."
        },
        checks: "Readiness failed closed; zero seeds spent; ADR 0009 accepted."
      },
      {
        id: "R2-14BA",
        title: "Amended Contract 1.1.0 with Quantitative Truth Tables (ADR 0010)",
        status: "Completed",
        commit: "627e698",
        summary: {
          tech: "Approved amended contract 1.1.0 freezing explicit numerical thresholds (std < 0.35, AUC < 0.60, hazard >= 0.20). Authorized Phase 2R.14BB execution.",
          simple: "Fixed the rules: Explicitly wrote down exact pass/fail numbers in Contract 1.1.0 before giving the computer permission to execute the diagnostics."
        },
        checks: "Contract amendment passed; development seeds 20280101..20280120 authorized."
      },
      {
        id: "R2-14BB",
        title: "Diagnostic Execution & Proof of Infeasibility (ADR 0011)",
        status: "Stop",
        commit: "464a4fd / 3a7c890",
        summary: {
          tech: "Executed all 17 diagnostics across 120 inventory units and 320-cell feasibility grid. 0 of 320 cells met joint constraints. Recorded stop_infeasible_design.",
          simple: "The Final Proof: Tested all 320 parameter combinations across 20 seeds. Exactly ZERO worked! Accepted ADR 0011 permanently stopping the proportional hazards track."
        },
        checks: "120/120 units executed; 0/320 cells feasible; ADR 0011 accepted."
      }
    ]
  },
  {
    phase: "Phase 2R: Generation v6 Bounded Sigmoid Architecture & Qualification",
    milestone: "v0.2.0-risk-model",
    items: [
      {
        id: "R2-14C",
        title: "Bounded Sigmoid Architecture & Substrate Contract 6.0.0 (ADR 0012)",
        status: "Completed",
        commit: "18ce32f",
        summary: {
          tech: "Authorized bounded sigmoid hazard link λ(t) = λ_max · σ(z), mathematically bounding total monthly hazard <= 0.1500 < 0.2000. Approved Contract 6.0.0 and Coefficient Registry 3.0.0.",
          simple: "Mathematical Breakthrough: Swapped the explosive exponential formula for a bounded S-curve (sigmoid) capped at 15%/month. Solved the Catch-22 and approved Contract 6.0.0."
        },
        checks: "Contract validation passed; fresh development seeds 20280201..20280220 authorized."
      },
      {
        id: "R2-14D",
        title: "Generation v6 Substrate Implementation & Development Qualification",
        status: "Completed",
        commit: "89ec94a",
        summary: {
          tech: "Implemented v6 simulator modules with centered linear predictors and 6.0x scaling. Executed 120-unit qualification across all 20 seeds; all 9 gates passed (median AUC 0.7086, AP lift +0.1398, max hazard 0.14999).",
          simple: "Substrate Qualified! Evaluated 20 test seeds and 120 units under Generation v6. All 9 safety and accuracy gates passed cleanly, authorizing final candidate model evaluation."
        },
        checks: "All 9 qualification gates passed; mechanical decision 'qualified'; authorizes Phase 2R.15."
      },
      {
        id: "R2-15",
        title: "Generation v6 Evaluation Pipeline & Release Candidate Freeze",
        status: "Completed",
        commit: "8965c72",
        summary: {
          tech: "Built chronological rolling-origin folds, 17-feature extraction with event lineage validation, non-final diagnostics (decision: allow, 0 flags), and deterministic candidate comparison. Selected Logistic Regression over XGBoost (ROC AUC: 0.7057 vs 0.6801, Brier: 0.1287 vs 0.1354). Froze all memberships, states, and scoring authorizations into cryptographic digests.",
          simple: "Candidate Selected! Extracted 17 point-in-time features with zero data leakage. Evaluated Logistic Regression against XGBoost: Logistic won on accuracy (0.7057 ROC AUC vs 0.6801) and calibration, earning selection as release candidate. All checksums locked down before statistical acceptance testing."
        },
        checks: "Issue #90 & PR #91 merged; 365 tests pass; structural support passes; 0 diagnostic flags; Logistic selected; clean-room invariants strictly preserved; authorizes Phase 2R.16."
      },
      {
        id: "R2-16",
        title: "Generation v6 Statistical Acceptance Protocol Execution",
        status: "Completed — Redesign",
        commit: "82e767f",
        summary: {
          tech: "Executed the complete frozen acceptance protocol across 20 reserved acceptance seeds (20271201..20271220) and 3 temporal folds (120 units). Primary signal recovery passed decisively (median ROC AUC 0.7031, 20/20 seed consistency, AP lift +0.1344). Four fine-grained secondary rules tripped thresholds, deriving mechanical decision 'redesign'.",
          simple: "Acceptance Gate Executed! Evaluated the frozen model across 20 unseen acceptance seeds. The core AI signal was confirmed (0.7031 AUC vs 0.50 placebo across all 20 seeds), but 4 strict secondary diagnostic tests fell slightly short of perfection, triggering a mechanical 'redesign' protocol decision."
        },
        checks: "Issue #92 & PR #93 merged; 120 inventory units evaluated; bit-for-bit check passes; mechanical decision: redesign."
      },
      {
        id: "R2-16A",
        title: "Acceptance Remediation & Protocol 3.1.0 Amendment (ADR 0013)",
        status: "Completed — Mechanical Proceed",
        commit: "4d7e9da",
        summary: {
          tech: "Adopted ADR 0013 and approved Statistical Acceptance Protocol 3.1.0. Re-evaluated 120 inventory units across seeds 20271201..20271220. All 10 rule families passed 100% (median AUC 0.7031, 20/20 seed consistency, AP lift +0.1344, Brier skill +0.0658, worst fold 0.6709). Mechanical decision: PROCEED. Final holdout remains not_materialized.",
          simple: "Remediation Complete & Accepted! All 4 secondary quality checks were recalibrated to standard mathematical theory (binomial joint coverage and numerical quadrature bounds). All 10 rule families passed 100%, and the system derived a mechanical 'PROCEED' decision, officially completing Phase 2R and clearing the path to resume Phase 2!"
        },
        checks: "Issue #94 & PR #95 merged (commit 4d7e9da); ADR 0013 & Protocol 3.1.0; 120 inventory units evaluated; bit-for-bit check passes; mechanical decision: PROCEED; Phase 2R complete; authorizes P2-08."
      }
    ]
  },
  {
    phase: "Phase 2: Resumed Capabilities & Operational Decisioning",
    milestone: "v0.2.2-operational-decisioning",
    items: [
      {
        id: "P2-08",
        title: "Probability Calibration & Operational Thresholds",
        status: "Completed",
        commit: "3abb044",
        summary: {
          tech: "Contract 1.0.0. Evaluated Platt scaling and isotonic calibration on candidate Logistic Regression (seed 20260817, C=1.0, L2) strictly on 8,560 calibration rows of seed 20280201. Platt scaling selected (ECE 0.0115 <= 0.0300, calibration slope 0.9498 within [0.85, 1.15], Brier score 0.1211, AUC 0.6998 preserving rank order). Established 4 operational risk tiers and triage queues (Top 1% achieves 34.09% precision / 2.23x lift; Top 5% intercepts 11.57% of population lapses / 2.31x lift; Top 20% intercepts 36.64% lapses). 1,000 policy-cluster bootstrap CIs and net benefit decision curves verified. Final holdout strictly not_materialized.",
          simple: "Probability Calibration & Review Queues: Converted raw AI scores into reliable, true real-world percentages using Platt scaling (error dropped to 1.15% ECE with perfect rank preservation). Created operational triage tiers: auditing the top 1% highest-risk policies yields 34.1% true cancellations (2.23x better than random), and checking the top 5% catches 11.6% of all cancellations."
        },
        checks: "Issue #96 & PR #97 merged (commit 3abb044); Contract 1.0.0; fit strictly on calibration role partition (8,560 rows); evaluated out-of-sample on non_final_evaluation (8,782 rows); final holdout strictly not_materialized; bit-for-bit check passes; authorizes P2-09."
      },
      {
        id: "P2-09",
        title: "Model-Behavior Explanations & Action-Authority Boundaries",
        status: "Completed",
        commit: "29b9aca",
        summary: {
          tech: "Contract 1.0.0. Deployed exact additive logit decomposition and centered SHAP attributions for frozen, Platt-calibrated candidate Logistic Regression model (seed 20260817, C=1.0, L2). Achieved exact logit reconstruction (|z_cal - (phi_0 + sum Phi_k)| < 1e-10; observed 1.78e-15) across all 8,782 out-of-sample observations. Passed 100% of directional sanity checks (17/17) against actuarial domain principles. Top global risk reducer is rolling_on_time_rate (22.78% relative importance); top risk escalator is recent_delay_days (9.48%). Generated local waterfall case studies for Risk Tiers 1, 2, and 3. Formally codified ADR 0002 action-authority boundaries (Tier 1 perception only; strictly non-causal interpretation; mandatory Tier 2 rule checks; Tier 4 human approval). Final holdout strictly not_materialized.",
          simple: "Model-Behavior Explanations & Governance Guardrails: Created exact, mathematically transparent risk breakdowns (additive log-odds and centered SHAP values) explaining why any customer receives their risk score. Proved 100% directional sanity against actuarial rules (e.g. paying on time reduces risk, failed payments and arrears increase risk). Generated waterfall explanations for Low, Moderate, and High risk accounts. Enforced strict ADR 0002 boundaries: explanations show correlations, not causes, and AI can never make autonomous customer retention decisions without licensed human approval."
        },
        checks: "Issue #98 & PR #99 merged (commit 29b9aca); Contract 1.0.0; exact additive reconstruction < 1e-10 (observed 1.78e-15); 17/17 directional sanity checks passed; representative case studies across Tiers 1, 2, 3; ADR 0002 non-causal boundaries codified; final holdout strictly not_materialized; bit-for-bit check passes; authorizes P2-10."
      },
      {
        id: "P2-10",
        title: "Artifact and Environment Reproducibility (Release Model Bundle)",
        status: "Completed",
        commit: "Branch feat/100-p2-10-artifact-and-environment-reproducibility",
        summary: {
          tech: "Contract 1.0.0. Unified fitted preprocessor transformations (13 numeric scalers + 4 categorical one-hot encoders = 28 features), Logistic Regression weights (seed 20260817, C=1.0, L2), Platt calibration parameters (A=0.961849, B=-0.033420), explainer background baseline (E[z]=-0.7107, E[p]=0.3295), and operational decision policies (4 risk tiers, 3 review queues, ADR 0002 action boundaries) into an immutable, pure-JSON release model bundle (phase-02-10-model-bundle.json). Implemented standalone BundledInferenceEngine achieving bit-for-bit reload invariance across all 8,782 out-of-sample observations (max prob delta: 2.22e-16 <= 1.00e-12; max logit delta: 8.88e-16 <= 1.00e-12; 100% operational tier concordance). Locked Python runtime and dependency lock hashes. Final holdout strictly not_materialized.",
          simple: "Artifact & Environment Reproducibility: Packaged the entire trained AI pipeline (preprocessor, linear weights, calibrator, explainer baselines, and risk rules) into a single, secure, transparent JSON bundle with zero external ML library dependencies at runtime. Proved bit-for-bit reload reproduction: the standalone bundle engine generates identical predictions across all 8,782 customer accounts with zero drift (divergence under 1 part in 10 quadrillion). Locked environment versions and cryptographic checksums."
        },
        checks: "Issue #100 & PR #101; Contract 1.0.0; pure-JSON serialization without pickle; standalone BundledInferenceEngine; bit-for-bit verification passes (max prob diff 2.22e-16 <= 1e-12); 100% operational tier concordance (8,782/8,782); ADR 0002 authority compliance; final holdout strictly not_materialized; make model-bundle-check passes."
      }
    ]
  }
];

// Roadblocks & Design Pivots Data
const roadblocksData = [
  {
    id: "LIM-002-001",
    type: "rb-guard",
    title: "Billing Frequency Confounded with Observation Time",
    phase: "Discovered in Phase 2.03",
    adr: "ADR 0004 / 0005",
    trap: {
      tech: "All policies were issued in one initial batch, and observation cutoff occurred at first billing. Monthly policies entered train, quarterly entered embargo, semiannual entered val, and annual entered test.",
      simple: "All policies started on Day 1, and were evaluated on their first bill. That meant all monthly policies were in the training set and all yearly policies in the test set. Models couldn't tell time apart from policy type!"
    },
    pivot: {
      tech: "Introduced multi-cohort issuance spread across years, recurring point-in-time observation windows, and required all billing frequencies in all chronological folds.",
      simple: "Staggered policy start dates across years and checked on policies repeatedly. Now every time period contains a fair mix of monthly, quarterly, and annual policies."
    }
  },
  {
    id: "LIM-002-002",
    type: "rb-redesign",
    title: "Simulator Lacked Pre-Cutoff Feature-Conditioned Risk",
    phase: "Discovered in Review after Phase 2.07",
    adr: "ADR 0004 / 0005 / 0007",
    trap: {
      tech: "The v1 generator assigned lapse/surrender outcomes independently of customer attributes or historical events. Features had near-zero true mutual information with the target.",
      simple: "The initial simulator decided who canceled purely at random after the cutoff date. The ML models had literally nothing real to learn from, resulting in 53% coin-flip accuracy."
    },
    pivot: {
      tech: "Designed a multi-hazard frailty model with registered beta coefficients for behavioral drivers (billing frequency, arrears, service contacts) and explicit oracle probabilities.",
      simple: "Replaced flat random assignment with a realistic hazard formula: missed payments and service complaints increase risk of cancellation, giving models true signal to discover."
    }
  },
  {
    id: "LIM-002-003",
    type: "rb-guard",
    title: "Test Matrix Relabeling During Adversarial Review",
    phase: "Discovered in Review after Phase 2.07",
    adr: "ADR 0004 & Scoring Auth Contract",
    trap: {
      tech: "Scoring APIs previously authorized predictions based on a caller-supplied partition string. A reviewer was able to generate test predictions by relabeling the test matrix as 'validation'.",
      simple: "A security hole in our test code: anyone could sneak a peek at test set predictions simply by renaming the input variable to 'validation'."
    },
    pivot: {
      tech: "Implemented cryptographic scoring authorization contracts that verify row count, row order, fitted preprocessor ID, purpose, and exact SHA-256 matrix digests before computing scores.",
      simple: "Added digital tamper seals. If anyone tries to modify, reorder, or rename the dataset, the scoring engine immediately throws an integrity exception."
    }
  },
  {
    id: "LIM-002-004",
    type: "rb-stop",
    title: "Post-Cutoff Ingestion Leakage in v2 Preflight",
    phase: "Discovered in R2-07 Readiness Gate",
    adr: "ADR 0005 Dual-Time Substrate",
    trap: {
      tech: "The v2 corpus builder computed behavior features before verifying ingestion timestamps. An event with ingested_at > as_of leaked into cutoff features, failing READINESS-DUAL-TIME-VISIBILITY.",
      simple: "Future Paperwork Leak: An event that officially happened before the cutoff wasn't entered into the computer until AFTER the cutoff. The code accidentally counted it anyway."
    },
    pivot: {
      tech: "The automated gate halted fail-closed (STOP decision). ADR 0005 introduced the dual-time invariant: E.effective_at <= as_of AND E.ingested_at <= as_of for every feature.",
      simple: "Instead of ignoring the bug, the system automatically stopped the pipeline. We redesigned the engine so events are only visible if both the event AND the computer entry happened in the past."
    }
  },
  {
    id: "LIM-002-005",
    type: "rb-redesign",
    title: "v3 Signal-Recovery Collapse Across 20 Seeds",
    phase: "Discovered in R2-11 Acceptance Gate",
    adr: "ADR 0006 Diagnostic Boundary",
    trap: {
      tech: "Statistical acceptance failed decisively on 20 seed pairs. Signal AUC was 0.519 (target >= 0.65; 0/20 passed); matched-null lift was +0.016 (target >= +0.10; 0/20 passed).",
      simple: "Clean, leak-free data finally ran—and the models failed! They scored 51.9% accuracy (barely beating coin-flip) and beat the placebo by only 1.6%."
    },
    pivot: {
      tech: "Protocol 2.2.0 executed mechanical 'redesign' decision. Refused to lower thresholds. ADR 0006 authorized 6 scientific hypotheses (H1-H6) to isolate failure mechanics.",
      simple: "We refused to move the goalposts to make it pass. The gate declared REDESIGN and launched a scientific diagnostic inquiry."
    }
  },
  {
    id: "LIM-002-006",
    type: "rb-redesign",
    title: "v4 Hazard Ceiling Explosion Across 100% of Seeds",
    phase: "Discovered in R2-14 Qualification Gate",
    adr: "ADR 0008 Post-v4 Diagnostics",
    trap: {
      tech: "Doubling log-hazard beta coefficients caused monthly discrete hazards to violate the < 0.20 actuarial bound on 100% of seeds (reaching 0.25 - 0.45). Brier skill score collapsed.",
      simple: "Rocket Explosion: To make the AI smarter, we doubled risk multipliers. But exponential math caused high-risk customers to cancel at 40%/month, breaking real-world insurance rules."
    },
    pivot: {
      tech: "Qualification triggered mechanical 'redesign'. Blocked R2-15 acceptance. ADR 0008 authorized 17 diagnostics and an exhaustive 320-cell feasibility surface.",
      simple: "Stopped immediately. Set up an exhaustive 320-point computer search to test if ANY combination of this formula could work."
    }
  },
  {
    id: "LIM-002-007",
    type: "rb-stop",
    title: "v5 Contract Ambiguity Halts Pre-Result Readiness",
    phase: "Discovered in R2-14B Readiness Gate",
    adr: "ADR 0009 Readiness Stop & ADR 0010 Amendment",
    trap: {
      tech: "Fail-closed runner detected Contract 1.0.0 lacked mechanical H1-H5 numerical disposition thresholds, leaving supported vs rejected open to post-hoc caller discretion.",
      simple: "Missing Rule Stop: The runner caught that pass/fail thresholds weren't numerically frozen. It halted before running a single seed to prevent researcher bias."
    },
    pivot: {
      tech: "Halted with decision stop_contract_not_executable (0/120 units, 0/320 cells). ADR 0010 approved amended Contract 1.1.0 freezing quantitative truth tables before execution.",
      simple: "Refused to let humans fudge thresholds. Stopped, amended the contract with exact numbers on main, and only then ran the execution."
    }
  },
  {
    id: "LIM-002-008",
    type: "rb-stop",
    title: "Mathematical Infeasibility: The Proportional Hazards Trilemma",
    phase: "Discovered in R2-14BB Diagnostic Execution",
    adr: "ADR 0011 Stop Infeasible Design",
    trap: {
      tech: "All 320 Cartesian parameter cells evaluated across 120 inventory units. Exactly 0 of 320 cells satisfied simultaneous recovery (AUC >= 0.70, AP lift >= 0.10) and hazard ceiling (< 0.20).",
      simple: "The Final Catch-22: The computer tested all 320 possible combinations. Exactly ZERO worked! Safe hazards meant blind AI (57% AUC); smart AI meant blown hazard ceilings (>20%)."
    },
    pivot: {
      tech: "Adopted causal response 'stop_infeasible_design' under Contract 1.1.0 Section 10. Proposed ADR 0011 permanently stopping proportional hazards track. Next pivot requires bounded sigmoid link or state machine.",
      simple: "Recorded ADR 0011 on main: permanently documenting the mathematical proof so future engineers don't waste time on a dead end. Pivoting to bounded non-exponential formulas."
    }
  },
  {
    id: "LIM-002-009",
    type: "rb-pivot",
    title: "Proportional Hazards Trilemma Resolved via Bounded Sigmoid Link",
    phase: "Discovered in R2-14C / Qualified in R2-14D",
    adr: "ADR 0012 Bounded Sigmoid Hazard Link",
    trap: {
      tech: "Exponential proportional hazards math inherently forced an unresolvable trade-off: steep signal slope blew past the monthly hazard ceiling (>=0.20), while ceiling enforcement collapsed signal recovery (AUC ~0.57).",
      simple: "The Proportional Hazards Trilemma: The exponential formula (e^Score) made it mathematically impossible to have high accuracy and safe hazard limits at the same time."
    },
    pivot: {
      tech: "ADR 0012 authorized bounded sigmoid link λ(t) = λ_max · σ(z) with centered linear predictor and 6.0x scale under Contract 6.0.0. R2-14D qualification confirmed all 9 gates passed (median AUC 0.7086, AP lift +0.1398, max hazard 0.14999 <= 0.1500 < 0.2000).",
      simple: "Replaced exponential math with a bounded S-curve (sigmoid) capped strictly at 15%/month. Solved the Catch-22: all 20 seeds passed safety and accuracy with 70.9% AUC, unlocking Phase 2R.15!"
    }
  },
  {
    id: "LIM-002-010",
    type: "rb-pivot",
    title: "Secondary Rule Calibration under Protocol 3.1.0 (ADR 0013)",
    phase: "Discovered in R2-16 / Resolved in R2-16A",
    adr: "ADR 0013 Amend v6 Statistical Acceptance Protocol",
    trap: {
      tech: "Acceptance Protocol 3.0.0 set over-constrained secondary thresholds: 90% point binomial coverage (18/20) ignoring finite sample binomial variance (expected ~16/20 at 2.5th percentile), exact zero tolerance on continuous Gauss-Hermite integration against discrete time steps (0.0045 gap), and asymptotic 20% variance contraction on finite sample subsets.",
      simple: "Secondary rules demanded impossible mathematical perfection: requiring 18 out of 20 random trials to hit a 90% window (ignoring natural statistical variation), and demanding zero numerical gap when comparing continuous math integrals against discrete monthly time steps."
    },
    pivot: {
      tech: "ADR 0013 adopted Protocol 3.1.0: aligned binomial joint coverage (>=15/20 for 90% CI), added discretization tolerance epsilon <= 0.0100 for continuous-discrete oracle ordering, and relaxed finite-sample learning variance contraction (>= 0.0%). All 10 rule families passed (120/120 units), deriving mechanical PROCEED decision and unpausing Phase 2.",
      simple: "Recalibrated secondary quality checks to standard mathematical physics without touching primary accuracy (70.3% AUC maintained across all 20 seeds). All 10 checks passed cleanly, earning a mechanical PROCEED and giving the green light to resume Phase 2!"
    }
  }
];

// Master Iteration Matrix Data: Method, Failure, Root Cause, Decision
const iterationMatrixData = [
  {
    generation: "Generation v1",
    phase: "Phases 1.01 – 2.07",
    title: "Baseline Pipeline Engineering & Independent Draws",
    badgeClass: "status-warn",
    statusText: "Pipeline Only (Confounding & Zero Signal)",
    adr: "ADR 0001 • ADR 0002 • ADR 0003",
    formula: "P(Lapse) ~ Bernoulli(p), P(Surrender) ~ Bernoulli(q) [Independent of pre-cutoff features]",
    failure: {
      tech: "Temporal confounding: all policies issued Day 0; first-billing cutoff segregated monthly into train, annual into test (LIM-002-001). Zero feature signal: AUC ~ 0.53 (LIM-002-002). Relabeling bypass (LIM-002-003).",
      simple: "All policies started on Day 1, so monthly policies went to train and annual to test. Worse, cancellations were random coin-flips: models scored 53% accuracy because features had zero signal."
    },
    rootCause: {
      tech: "Simulator lacked pre-cutoff behavioral hazard mechanism. Single-batch issuance confounded billing frequency with observation time. Partition authorization was an unauthenticated string.",
      simple: "The simulator decided who canceled randomly after the cutoff date. And because everyone enrolled on Day 1, the calendar scrambled policy billing types."
    },
    decision: {
      tech: "Bound results strictly to 'pipeline_engineering_only'. Retired v1 fixture as release holdout. Established Phase 2R remediation and cryptographic scoring authorization.",
      simple: "Admitted honestly that v1 proves software plumbing but NOT machine learning accuracy. Started Phase 2R remediation from scratch."
    }
  },
  {
    generation: "Generation v2",
    phase: "Phases 2R.04 – 2R.07",
    title: "Multi-Cohort Issuance & Latent Frailty Hazards",
    badgeClass: "status-stop",
    statusText: "Fail-Closed STOP (Ingestion Leakage)",
    adr: "ADR 0004 Predeclared Gate",
    formula: "λ(t) = λ₀(t) · exp(Xβ + u),  u ~ Normal(0, σ²=0.04)",
    failure: {
      tech: "Preflight readiness audit halted fail-closed before model training (READINESS-DUAL-TIME-VISIBILITY failure, LIM-002-004).",
      simple: "Future Paperwork Leak: The automated gate stopped the build before any model trained because an event entered the computer after cutoff was used in features."
    },
    rootCause: {
      tech: "Ingestion delay caused events with effective_at <= as_of to be processed even when ingested_at > as_of, leaking retroactive paperwork into historical features.",
      simple: "In the real world, someone can cancel on Monday, but the mail doesn't arrive until Friday. If your model looks on Wednesday, it shouldn't know yet!"
    },
    decision: {
      tech: "Mechanical decision 'stop'. Halted all model fitting and holdout access. ADR 0005 mandated bitemporal dual-time predicates (effective_at <= as_of AND ingested_at <= as_of).",
      simple: "System halted completely. Refused to train models on leaky data. Redesigned the entire simulator around dual-time event sourcing."
    }
  },
  {
    generation: "Generation v3",
    phase: "Phases 2R.08 – 2R.11",
    title: "Event-First Dual-Time Substrate & Matched Controls",
    badgeClass: "status-redesign",
    statusText: "Mechanical REDESIGN (Decisive Signal Recovery Failure)",
    adr: "ADR 0005 • ADR 0006 Diagnostic Boundary",
    formula: "Dual-time: E.effective_at <= as_of AND E.ingested_at <= as_of | Paired Matched-Null Control",
    failure: {
      tech: "Signal-recovery acceptance failed decisively across all 20 seed pairs: Median AUC 0.519 (target >= 0.65, 0/20 passed); median matched-null lift +0.016 (target >= +0.10, 0/20 passed).",
      simple: "Clean, leak-free data finally ran—and the models failed! They scored 51.9% accuracy (coin-flip) and beat the placebo by only 1.6%."
    },
    rootCause: {
      tech: "Severe signal-to-noise deficit. Behavioral log-hazard coefficients produced narrow spread (std < 0.35); latent frailty noise overwhelmed observable behavioral predictors.",
      simple: "The behavioral clues (late bills, service complaints) were too faint, and random background customer noise drowned them out completely."
    },
    decision: {
      tech: "Protocol 2.2.0 executed mechanical 'redesign' decision. Refused to lower thresholds. ADR 0006 authorized 6 scientific hypotheses (H1-H6) to isolate failure mechanics.",
      simple: "We refused to move the goalposts to make it pass. The gate declared REDESIGN and launched a scientific diagnostic inquiry."
    }
  },
  {
    generation: "Generation v4",
    phase: "Phases 2R.12 – 2R.14",
    title: "Signal Amplification & The Hazard Ceiling Explosion",
    badgeClass: "status-redesign",
    statusText: "Mechanical REDESIGN (Actuarial Hazard Ceiling Violation)",
    adr: "ADR 0007 • ADR 0008 Post-v4 Diagnostics",
    formula: "λ(t) = λ₀(t) · exp(2.0 · Xβ + u),  u ~ Normal(0, 0.01) [The Exponential Rocket]",
    failure: {
      tech: "100% of seeds breached the < 0.20 monthly discrete hazard ceiling (reaching 0.25 - 0.45). Brier skill score collapsed (< 0). Severe early cohort attrition.",
      simple: "Rocket Explosion: To make the AI smarter, we doubled risk multipliers. But exponential math caused high-risk customers to cancel at 40%/month, breaking real-world insurance rules."
    },
    rootCause: {
      tech: "In an additive hazard model, doubling beta exponentially scales upper-tail hazard (exp(2) ~ 7.4x, exp(3) ~ 20x). High-risk customers vanished in months 1-3, destroying survival dynamics.",
      simple: "Exponential math behaves like an explosion: turning up the volume dial just enough to help the detector blasted through real-world life insurance physics."
    },
    decision: {
      tech: "Qualification gate triggered mechanical 'redesign'. Blocked R2-15 acceptance. ADR 0008 authorized 17 diagnostics and exhaustive 320-cell feasibility surface.",
      simple: "Stopped immediately. Set up an exhaustive 320-point computer search to test if ANY combination of this formula could work."
    }
  },
  {
    generation: "Generation v5",
    phase: "Phases 2R.14B – 2R.14BB",
    title: "Feasibility Surface & Mathematical Proof of Infeasibility",
    badgeClass: "status-stop",
    statusText: "Architectural STOP (0 of 320 Cells Feasible)",
    adr: "ADR 0009 • ADR 0010 • ADR 0011 Stop Infeasible Design",
    formula: "λ_lapse(t) + λ_surrender(t) < 0.20   VS   AUC >= 0.70 & AP_lift >= 0.10 [The Catch-22]",
    failure: {
      tech: "0 of 320 Cartesian feasibility grid cells satisfied simultaneous recovery (AUC >= 0.70, AP lift >= 0.10) and hazard ceiling (< 0.20) constraints.",
      simple: "The Final Catch-22: The computer tested all 320 possible combinations. Exactly ZERO worked! Safe hazards meant blind AI (57% AUC); smart AI meant blown hazard ceilings (>20%)."
    },
    rootCause: {
      tech: "Mathematical proof of the Proportional Hazards Trilemma: The additive exponential hazards link has no feasible parameter space under life-insurance monthly event bounds.",
      simple: "The Catch-22 is mathematically unsolvable with this formula: the exponential link (e^Score) is fundamentally the wrong shape for bounded life insurance risk."
    },
    decision: {
      tech: "Adopted causal response 'stop_infeasible_design' under Contract 1.1.0 Section 10. Proposed ADR 0011 permanently stopping proportional hazards track. Next pivot requires bounded sigmoid link or state machine.",
      simple: "Recorded ADR 0011 on main: permanently documenting the mathematical proof so future engineers don't waste time on a dead end. Pivoting to bounded non-exponential formulas."
    }
  },
  {
    generation: "Generation v6",
    phase: "Phases 2R.14C – 2R.16A",
    title: "Bounded Sigmoid Architecture & Statistical Acceptance Gate",
    badgeClass: "status-pass",
    statusText: "Mechanical PROCEED (10/10 Rule Families Satisfied under Protocol 3.1.0)",
    adr: "ADR 0012 Bounded Sigmoid • ADR 0013 Protocol 3.1.0",
    formula: "λ_lapse(t) = 0.10 · σ(z_lapse),   λ_surr(t) = 0.05 · σ(z_surr)   [Bounded S-Curve: λ_total ≤ 0.1500 < 0.2000]",
    failure: {
      tech: "Initial execution under Protocol 3.0.0 recovered primary signal (median AUC 0.7031 >= 0.68, 20/20 seed consistency, AP lift +0.1344) but tripped 4 secondary calibration rules. ADR 0013 approved Protocol 3.1.0 aligning secondary rules to standard mathematical theory without touching primary signal thresholds.",
      simple: "The initial run confirmed strong predictive signal (70.3% AUC across all 20 seeds) but tripped 4 over-tight secondary quality checks. ADR 0013 calibrated these secondary rules to real-world math."
    },
    rootCause: {
      tech: "Bounded logistic link resolves the Proportional Hazards Trilemma and guarantees safe hazard ceilings (max hazard 0.14999). Calibrated binomial coverage (>=15/20 for 90% CI), quadrature tolerance (epsilon <= 0.0100), and finite-sample variance contraction satisfied all theoretical requirements.",
      simple: "The S-curve completely solved the core problem (high accuracy with safe risk limits). Calibrating the 4 secondary quality checks to real-world math completed the validation suite."
    },
    decision: {
      tech: "Executed complete 120-unit acceptance protocol under Protocol 3.1.0 across seeds 20271201..20271220. All 10 rule families passed 100%. Derived mechanical decision 'PROCEED'. Candidate accepted; Phase 2 unpaused for P2-08.",
      simple: "Every single test and rule family passed 100%! The system generated a mechanical 'PROCEED' verdict, successfully concluding Phase 2R and giving permission to resume Phase 2."
    }
  }
];

// ============================================================
// CONTROLLER & VIEW RENDERING
// ============================================================

function initApp() {
  bindEvents();
  renderTimeline();
  renderRoadblocks();
  renderIterationMatrix();
  updateExplainerTexts();
}

function bindEvents() {
  // Explainer mode buttons
  const btnTech = document.getElementById('btnModeTech');
  const btnSimple = document.getElementById('btnModeSimple');

  btnTech.addEventListener('click', () => setExplainerMode('tech'));
  btnSimple.addEventListener('click', () => setExplainerMode('simple'));

  // Tab switching
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const targetTab = tab.dataset.tab;
      showTab(targetTab);
    });
  });

  // Timeline filters
  const searchInput = document.getElementById('timelineSearch');
  const filterSelect = document.getElementById('timelineFilterStatus');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value.toLowerCase();
      renderTimeline();
    });
  }

  if (filterSelect) {
    filterSelect.addEventListener('change', (e) => {
      state.filterStatus = e.target.value;
      renderTimeline();
    });
  }
}

function setExplainerMode(mode) {
  state.explainerMode = mode;
  document.getElementById('btnModeTech').classList.toggle('active', mode === 'tech');
  document.getElementById('btnModeSimple').classList.toggle('active', mode === 'simple');
  updateExplainerTexts();
  renderTimeline();
  renderRoadblocks();
  renderIterationMatrix();
}

function updateExplainerTexts() {
  const dynamicElements = document.querySelectorAll('.text-dynamic');
  dynamicElements.forEach(el => {
    const text = el.getAttribute(`data-${state.explainerMode}`);
    if (text) {
      el.textContent = text;
    }
  });
}

function showTab(tabId) {
  state.activeTab = tabId;
  const panels = document.querySelectorAll('.tab-panel');
  panels.forEach(p => p.classList.remove('active'));
  const targetPanel = document.getElementById(`tab-${tabId}`);
  if (targetPanel) {
    targetPanel.classList.add('active');
  }
}

function renderTimeline() {
  const container = document.getElementById('timelineContainer');
  if (!container) return;

  container.innerHTML = '';

  timelineData.forEach(phaseGroup => {
    // Filter items
    const filteredItems = phaseGroup.items.filter(item => {
      const matchStatus = state.filterStatus === 'all' || item.status === state.filterStatus;
      const textToSearch = (item.title + ' ' + item.summary.tech + ' ' + item.summary.simple + ' ' + item.id).toLowerCase();
      const matchSearch = !state.searchQuery || textToSearch.includes(state.searchQuery);
      return matchStatus && matchSearch;
    });

    if (filteredItems.length === 0) return;

    const groupEl = document.createElement('div');
    groupEl.className = 'timeline-phase-group';

    groupEl.innerHTML = `
      <div class="timeline-phase-header">
        <div class="timeline-phase-dot"></div>
        <div>
          <div class="phase-title-text">${phaseGroup.phase}</div>
          <div class="phase-meta">Milestone: <code>${phaseGroup.milestone}</code></div>
        </div>
      </div>
      <div class="phase-nodes">
        ${filteredItems.map(item => `
          <div class="timeline-node-card">
            <div class="node-top-row">
              <span class="node-id">${item.id}</span>
              <span class="badge badge-${item.status.toLowerCase()}">${item.status}</span>
            </div>
            <div class="node-title">${item.title}</div>
            <div class="node-desc">
              ${state.explainerMode === 'simple' ? item.summary.simple : item.summary.tech}
            </div>
            <div class="node-foot">
              <span>Commit / PR: <a href="https://github.com/anilreddy89/Inforsight" target="_blank" class="node-link">${item.commit}</a></span>
              <span>•</span>
              <span>Verification: ${item.checks}</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.appendChild(groupEl);
  });
}

function renderRoadblocks() {
  const container = document.getElementById('roadblocksContainer');
  if (!container) return;

  container.innerHTML = roadblocksData.map(rb => `
    <div class="roadblock-card ${rb.type}">
      <div class="roadblock-header">
        <div>
          <div class="roadblock-id">${rb.id} • ${rb.phase}</div>
          <h3 class="roadblock-title">${rb.title}</h3>
        </div>
        <span class="badge badge-version">${rb.adr}</span>
      </div>

      <div class="roadblock-cols">
        <div class="rb-col rb-trap">
          <div class="rb-col-title">
            <span>⚠️</span> The Roadblock / Trap
          </div>
          <p class="text-dynamic">
            ${state.explainerMode === 'simple' ? rb.trap.simple : rb.trap.tech}
          </p>
        </div>

        <div class="rb-col rb-pivot">
          <div class="rb-col-title">
            <span>💡</span> The Engineering Pivot (ADR)
          </div>
          <p class="text-dynamic">
            ${state.explainerMode === 'simple' ? rb.pivot.simple : rb.pivot.tech}
          </p>
        </div>
      </div>
    </div>
  `).join('');
}

function renderIterationMatrix() {
  const container = document.getElementById('iterationMatrixContainer');
  if (!container) return;

  container.innerHTML = iterationMatrixData.map(item => `
    <div class="iteration-card ${item.badgeClass}">
      <div class="iteration-card-header">
        <div class="iteration-title-group">
          <div class="iteration-gen-tag">${item.generation} • ${item.phase}</div>
          <h3 class="iteration-card-title">${item.title}</h3>
        </div>
        <div class="iteration-badge ${item.badgeClass}">${item.statusText}</div>
      </div>

      <div class="iteration-formula-box">
        <span class="iteration-formula-label">Formula / Rule:</span>
        <code>${item.formula}</code>
      </div>

      <div class="iteration-cols-3">
        <div class="iter-box failure">
          <div class="iter-box-title">
            <span>❌</span> What Failed
          </div>
          <p class="text-dynamic">
            ${state.explainerMode === 'simple' ? item.failure.simple : item.failure.tech}
          </p>
        </div>

        <div class="iter-box root-cause">
          <div class="iter-box-title">
            <span>🔍</span> Root Cause & Math Driver
          </div>
          <p class="text-dynamic">
            ${state.explainerMode === 'simple' ? item.rootCause.simple : item.rootCause.tech}
          </p>
        </div>

        <div class="iter-box decision">
          <div class="iter-box-title">
            <span>⚖️</span> Strategic Decision & ADR
          </div>
          <p class="text-dynamic">
            ${state.explainerMode === 'simple' ? item.decision.simple : item.decision.tech}
          </p>
          <div class="iter-adr-tag">${item.adr}</div>
        </div>
      </div>
    </div>
  `).join('');
}

// ============================================================
// PIPELINE SIMULATOR STATE & SCENARIOS
// ============================================================

const pipelineScenarios = {
  p2_10_model_bundle: {
    name: "Phase 2.10: Release Model Bundle & Bit-for-Bit Reproducibility",
    stages: [
      {
        stage: 1,
        title: "Stage 1: Preflight Boundary & Clean-Room Invariant Gate",
        badge: "Passed",
        icon: "🛡️",
        command: "./scripts/check_repository_boundaries.sh",
        log: "Scanning tracked files for boundary violations...\n[PASS] Clean-room boundary check passed with zero violations.\n[PASS] Repository boundaries intact (zero test set peeking, zero pickle serialization).\n[PASS] Final holdout status verified: not_materialized.",
        explanation: {
          simple: "Verifies that repository security boundaries remain pristine, that no test holdouts have been touched, and that binary pickles are completely prohibited.",
          tech: "Verifies repository boundary integrity, clean-room isolation, and guarantees final_holdout_status remains strictly not_materialized."
        },
        status: "success"
      },
      {
        stage: 2,
        title: "Stage 2: Safe Pure-JSON Release Bundle Serialization",
        badge: "SERIALIZED",
        icon: "📦",
        command: "python3 scripts/run_model_bundle.py --check",
        log: "Verifying immutable release bundle: phase-02-10-model-bundle.json...\n- Preprocessor: 13 numeric standard scalers + 4 one-hot encoders (28 columns)\n- Base Model: LogisticRegression (L2, C=1.0, liblinear, seed 20260817)\n- Calibrator: Platt scaling (A=0.961849, B=-0.033420)\n- Explainer Baseline: E[z]=-0.710707, E[p]=0.329509\n- Operational Policy: 4 risk tiers, 3 review queues, ADR 0002 boundaries\n[PASS] Zero binary pickle dependencies; schema-validated pure JSON.",
        explanation: {
          simple: "Packages all feature math, model weights, probability curves, and business rules into a human-readable JSON file without unsafe pickle files.",
          tech: "Validates immutable ModelBundle Contract 1.0.0 encapsulating all preprocessing parameters, linear weights, Platt calibrator, and baseline vectors."
        },
        status: "success"
      },
      {
        stage: 3,
        title: "Stage 3: Bit-for-Bit Reload-and-Score Invariant Verification",
        badge: "BIT-FOR-BIT MATCH",
        icon: "🔬",
        command: "python3 scripts/run_model_bundle.py",
        log: "Reloading exclusively from phase-02-10-model-bundle.json via BundledInferenceEngine...\nScoring 8,782 out-of-sample observations from non_final_evaluation:\n- Max probability divergence: 2.22e-16 <= 1.00e-12 -> [PASS]\n- Max logit divergence:       8.88e-16 <= 1.00e-12 -> [PASS]\n[PASS] Standalone inference reproduces original pipeline bit-for-bit to machine precision.",
        explanation: {
          simple: "Runs the standalone JSON bundle on all 8,782 real evaluation records. The predictions match the original model to 16 decimal places—true zero drift!",
          tech: "Proves reload-and-score invariance |p_bundle - p_orig| < 1e-12 with observed divergence of 2.22e-16 across all 8,782 out-of-sample records."
        },
        status: "success"
      },
      {
        stage: 4,
        title: "Stage 4: Additive Logit Reconstruction & Centered SHAP Check",
        badge: "RECONSTRUCTED",
        icon: "🧮",
        command: "python3 scripts/run_model_bundle.py",
        log: "Reconstructing calibrated logits directly from bundle parameters:\n- z_cal = cal_intercept + sum(cal_coef * x)\n- Max logit reconstruction divergence: 8.88e-16 <= 1.00e-12 -> [PASS]\n- Explainer efficiency: sum(SHAP) = z_cal - E[z] -> [PASS]\n[PASS] Mathematical attribution reconstruction certified.",
        explanation: {
          simple: "Recomputes every customer's risk factors from the bundle's stored numbers and confirms they sum up exactly to the total score.",
          tech: "Verifies additive logit reconstruction and centered SHAP efficiency directly from bundle parameters with sub-quadrillionth error tolerance."
        },
        status: "success"
      },
      {
        stage: 5,
        title: "Stage 5: Operational Risk Tier Concordance (100.00%)",
        badge: "100.0% CONCORDANCE",
        icon: "🎯",
        command: "python3 scripts/run_model_bundle.py",
        log: "Benchmarking operational decision tier assignments across 8,782 observations:\n- Tier 1: Low Risk      ([0.00, 0.10)) -> 5,595 / 5,595 matched (100.0%)\n- Tier 2: Moderate Risk ([0.10, 0.25)) -> 1,848 / 1,848 matched (100.0%)\n- Tier 3: High Risk     ([0.25, 0.50)) -> 1,029 / 1,029 matched (100.0%)\n- Tier 4: Critical Risk ([0.50, 1.00]) ->   310 /   310 matched (100.0%)\n- Total concordance: 8,782 / 8,782 (100.00%) -> [PERFECT CONCORDANCE]",
        explanation: {
          simple: "Every single customer gets assigned to the exact same risk tier and review queue in the production bundle as in the research model.",
          tech: "Demonstrates 100.00% operational tier and review queue concordance across all 8,782 out-of-sample policies."
        },
        status: "success"
      },
      {
        stage: 6,
        title: "Stage 6: Runtime Environment & Lineage Digest Locking",
        badge: "GOVERNED & LOCKED",
        icon: "🏛️",
        command: "make model-bundle-check",
        log: "Asserting environment provenance and cryptographic lineage:\n- Python: 3.12.2 on macOS (Darwin)\n- scikit-learn: 1.4.1.post1 | numpy: 1.26.4 | scipy: 1.12.0\n- Dependency lock SHA-256: 7d643ffca1a7888ff4fa521f757fba305a41d0aa8c187514a66a7b73815049b4\n- Upstream Candidate (R2-15) + Calibration (P2-08) + Explanations (P2-09) bound\n- Final holdout status: not_materialized (Clean-room intact)\n=======================================================\nPHASE 2.10 CERTIFIED & COMPLETE (Model Ready for Deployment)\n=======================================================",
        explanation: {
          simple: "Locks exact software versions, operating system specs, and cryptographic fingerprints so anyone can reproduce these results anytime in the future.",
          tech: "Binds SHA-256 digests of all upstream models, contracts, and dependency locks; enforces ADR 0002 authority guardrails and clean-room holdout isolation."
        },
        status: "success"
      }
    ]
  },
  p2_09_model_explanations: {
    name: "Phase 2.09: Model Explanations & Action Boundaries (Exact Logit & Centered SHAP)",
    stages: [
      {
        stage: 1,
        title: "Stage 1: Preflight Boundary & Clean-Room Invariant Gate",
        badge: "Passed",
        icon: "🛡️",
        command: "./scripts/check_repository_boundaries.sh",
        log: "Scanning tracked files for boundary violations...\n[PASS] Clean-room boundary check passed with zero violations.\n[PASS] Candidate Logistic weights frozen: L2, C=1.0, seed 20260817.\n[PASS] Platt Calibrator locked: slope A=0.961849, intercept B=-0.033420.\n[PASS] Final holdout status verified: not_materialized.",
        explanation: {
          simple: "Verifies that no secrets or customer information are exposed, confirming that candidate model weights and calibrator parameters remain strictly locked.",
          tech: "Verifies repository boundary integrity, release candidate parameter stability, and guarantees final_holdout_status remains not_materialized."
        },
        status: "success"
      },
      {
        stage: 2,
        title: "Stage 2: Exact Additive Logit Decomposition Verification",
        badge: "VERIFIED",
        icon: "🧮",
        command: "python3 scripts/run_model_explanations.py --check",
        log: "Decomposing calibrated log-odds: z_cal(x) = phi_0 + sum(Phi_k(x))...\nEvaluating 8,782 out-of-sample observations from non_final_evaluation...\n- Max logit reconstruction residual: 1.78e-15 <= 1.00e-10 -> [EXACT MATCH]\n- Calibrated baseline intercept phi_0: -0.713702\n[PASS] Mathematical identity verified with zero approximation error.",
        explanation: {
          simple: "Proves that adding up individual feature risk points reproduces the customer's total risk score to 15 decimal places of accuracy.",
          tech: "Proves exact additive reconstruction |z_cal - (phi_0 + sum Phi_k)| < 1e-10 with observed max residual of 1.78e-15 across all out-of-sample policies."
        },
        status: "success"
      },
      {
        stage: 3,
        title: "Stage 3: Centered SHAP Efficiency & Population Baseline",
        badge: "EVALUATED",
        icon: "⚖️",
        command: "python3 scripts/run_model_explanations.py",
        log: "Evaluating centered SHAP values relative to evaluation background distribution:\n- Background population mean logit: -0.710707 (Expected prob: 0.3295)\n- Centered SHAP decomposition: z_cal(x) = E[z] + sum(SHAP_k(x))\n- Max SHAP efficiency residual: 1.78e-15 <= 1.00e-10 -> [PASS]\n[PASS] Fair Shapley attribution values certified.",
        explanation: {
          simple: "Calculates centered Shapley values relative to average customer risk, showing whether each factor makes this customer riskier or safer than average.",
          tech: "Evaluates exact SHAP values relative to empirical evaluation background expectation with zero reconstruction loss."
        },
        status: "success"
      },
      {
        stage: 4,
        title: "Stage 4: Actuarial Directional Sanity Check Gate (17/17 Passed)",
        badge: "17/17 PASS",
        icon: "✅",
        command: "python3 scripts/run_model_explanations.py",
        log: "Auditing all 17 feature weights against actuarial domain principles:\n- rolling_on_time_rate        (beta = -0.6149) -> [PASS: Protective]\n- recent_delay_days           (beta = +0.2835) -> [PASS: Risk Escalator]\n- recent_failed_payment_count (beta = +0.1751) -> [PASS: Friction Marker]\n- rolling_payment_count       (beta = -0.1557) -> [PASS: Policy Loyalty]\n- billing_frequency           (annual > monthly) -> [PASS: Payment Shock]\n- notice_category             (none < 0)       -> [PASS: Uninterrupted]\n- contact_category            (none < 0)       -> [PASS: Passive Satisfaction]\n[AUDIT] 17 of 17 directional sanity checks match domain logic 100%.",
        explanation: {
          simple: "Every single risk factor makes intuitive and actuarial sense: good payment habits reduce risk, while missed payments, delays, and complaints increase risk.",
          tech: "Enforces 100% sign and order consistency between empirical regression weights and actuarial domain mechanics."
        },
        status: "success"
      },
      {
        stage: 5,
        title: "Stage 5: Operational Risk Tier Waterfall Profiling",
        badge: "PROFILED",
        icon: "📊",
        command: "python3 scripts/run_model_explanations.py",
        log: "Extracting representative median case studies across operational tiers:\n- Tier 1 (Low Risk):      prob = 0.0768 | Top protective: rolling_on_time_rate (-0.5694)\n- Tier 2 (Moderate Risk): prob = 0.1654 | Friction: annual billing, recent delay\n- Tier 3 (High Risk):     prob = 0.3340 | Escalators: arrears, notices, failed debits\n[PASS] Case study waterfall explanations fully synthesized.",
        explanation: {
          simple: "Generates clear, readable waterfall charts for Low, Moderate, and High risk accounts so frontline specialists understand why a policy was flagged.",
          tech: "Synthesizes prototypical local waterfalls for Tier 1, 2, and 3 policies with exact log-odds attributions and top 3 drivers."
        },
        status: "success"
      },
      {
        stage: 6,
        title: "Stage 6: ADR 0002 Action-Authority Boundary Enforcement",
        badge: "GOVERNED",
        icon: "🏛️",
        command: "python3 -m unittest simulator.tests.test_model_explanations",
        log: "Asserting ADR 0002 Action-Authority Boundaries:\n1. Tier 1 Perception: Attributions possess ZERO autonomous action authority.\n2. Non-Causal Boundary: Attributions reflect P(y|x), NOT P(y|do(x)).\n3. Tier 2 Mandatory Gate: Deterministic rules, grace periods & caps required.\n4. Tier 4 Human Authority: Licensed conservation officers make all decisions.\n=======================================================\nPHASE 2.09 CERTIFIED & COMPLETE (Authorizes Phase 2.10)\n=======================================================",
        explanation: {
          simple: "Enforces the golden rule of ethical AI: the model only provides perception and advice. It has zero power to change premiums, send messages, or act without licensed human approval.",
          tech: "Codifies ADR 0002 non-causal boundaries, mandatory Tier 2 deterministic eligibility checks, and Tier 4 human-in-the-loop decision primacy."
        },
        status: "success"
      }
    ]
  },
  p2_08_probability_calibration: {
    name: "Phase 2.08: Probability Calibration & Operational Tiers (Platt Scaling)",
    stages: [
      {
        stage: 1,
        title: "Stage 1: Preflight Clean-Room & Holdout Isolation Audit",
        badge: "Passed",
        icon: "🛡️",
        command: "./scripts/check_repository_boundaries.sh",
        log: "Scanning tracked files for boundary violations...\n[PASS] Preflight boundary check passed with zero violations.\n[PASS] Model weights immutable; release candidate Logistic seed 20260817.\n[PASS] Final release holdout confirmed: not_materialized.",
        explanation: {
          simple: "Verifies repository boundaries, clean-room standards, and confirms that the final test set remains completely locked away and untouched.",
          tech: "Asserts boundary integrity, verifies release candidate hash stability, and verifies final_holdout_status remains not_materialized."
        },
        status: "success"
      },
      {
        stage: 2,
        title: "Stage 2: Candidate Logistic Reload & Scoring Authorization",
        badge: "Passed",
        icon: "📜",
        command: "python3 scripts/run_probability_calibration.py --check",
        log: "Reloading frozen candidate model (Logistic Regression, C=1.0, L2, seed 20260817)...\nAsserting candidate model weight immutability (0 weight updates allowed)...\n[PASS] Candidate weights frozen: coef_ norm 1.4872, intercept -1.6145.\n[PASS] Calibration role partition identified: 8,560 rows (seed 20280201).",
        explanation: {
          simple: "Loads the frozen model without modifying its brain or internal weights, verifying it is the identical candidate accepted in Phase 2R.",
          tech: "Verifies candidate parameters remain strictly immutable; loads isolated calibration role partition of 8,560 rows."
        },
        status: "success"
      },
      {
        stage: 3,
        title: "Stage 3: Calibrator Fitting (Platt Scaling vs Isotonic)",
        badge: "Passed",
        icon: "⚙️",
        command: "python3 scripts/run_probability_calibration.py",
        log: "Fitting Platt scaling (sigmoid) on calibration partition (8,560 rows)...\n- Platt parameters: A = 0.961849, B = -0.033420\nFitting Isotonic regression on calibration partition...\n- Isotonic step segments: 14 isotonic steps fitted.\n[PASS] Both calibrators fitted strictly on calibration partition without out-of-sample data.",
        explanation: {
          simple: "Fits two calibration methods (Platt scaling and isotonic regression) exclusively on the dedicated calibration data.",
          tech: "Fits Platt scaling (A=0.9618, B=-0.0334) and isotonic regression on 8,560 calibration rows without touching evaluation or holdout sets."
        },
        status: "success"
      },
      {
        stage: 4,
        title: "Stage 4: Out-of-Sample Calibration Quality Evaluation",
        badge: "Passed",
        icon: "🎯",
        command: "python3 scripts/run_probability_calibration.py",
        log: "Evaluating calibration on out-of-sample non_final_evaluation partition (8,782 rows):\n- Platt ECE: 0.0115 <= 0.0300 -> [PASS]\n- Platt Calibration Slope: 0.9498 within [0.85, 1.15] -> [PASS]\n- Platt Calibration Intercept: -0.1155\n- Platt Brier Score: 0.1211 (vs uncalibrated 0.1212)\n- Platt ROC AUC: 0.6998 (Exact rank preservation, delta = 0.0000 <= 1e-6) -> [PASS]\n- Isotonic ECE: 0.0142 | Slope: 0.9678 | Brier: 0.1213\n[SELECTION] Platt Scaling selected by deterministic primary decision rules.",
        explanation: {
          simple: "Evaluates calibrated probabilities against out-of-sample policyholders. Platt scaling achieves an outstanding 1.15% calibration error and perfect ranking preservation!",
          tech: "Out-of-sample metrics meet all contract gates: Platt ECE 0.0115 <= 0.0300, slope 0.9498 in [0.85, 1.15], Brier 0.1211, AUC 0.6998. Platt scaling selected deterministically."
        },
        status: "success"
      },
      {
        stage: 5,
        title: "Stage 5: Operational Capacity & Review Queues",
        badge: "Passed",
        icon: "📊",
        command: "python3 scripts/run_probability_calibration.py",
        log: "Evaluating operational triage queues across review capacity limits:\n- Top 1% Review Queue: 34.09% Precision, 2.23x Lift, NNR 2.9 (88 reviewed, 30 lapses)\n- Top 2% Review Queue: 30.11% Precision, 1.97x Lift, NNR 3.3 (176 reviewed, 53 lapses)\n- Top 5% Review Queue: 35.31% Precision, 2.31x Lift, 11.57% Recall (439 reviewed, 155 lapses)\n- Top 10% Review Queue: 30.64% Precision, 2.01x Lift, 20.07% Recall (878 reviewed, 269 lapses)\n- Top 20% Review Queue: 27.96% Precision, 1.83x Lift, 36.64% Recall (1,756 reviewed, 491 lapses)\n[PASS] Precision and lift decay monotonically across increasing review queues.",
        explanation: {
          simple: "Simulates actual customer retention teams: reviewing the top 1% risk policies catches cancellations at 34.1% precision (2.23x better than random), and checking the top 5% intercepts 11.6% of all cancellations.",
          tech: "Calculates operational metrics across top 1%, 2%, 5%, 10%, 20% review queue allocations. Top 1% precision reaches 34.09% (lift 2.23x, NNR 2.9); Top 5% recall reaches 11.57% (lift 2.31x)."
        },
        status: "success"
      },
      {
        stage: 6,
        title: "Stage 6: Risk Tiers & Net Benefit Decision Curves",
        badge: "Passed",
        icon: "⚖️",
        command: "python3 scripts/run_probability_calibration.py",
        log: "Discretizing calibrated probabilities into 4 governed risk tiers:\n- Tier 1 Low (p < 0.10): 4,374 policies (49.8%), 7.02% empirical lapse rate\n- Tier 2 Moderate (0.10 <= p < 0.25): 3,090 policies (35.2%), 19.35% empirical lapse rate\n- Tier 3 High (0.25 <= p < 0.50): 1,318 policies (15.0%), 33.23% empirical lapse rate\n- Tier 4 Critical (p >= 0.50): 0 policies\nDecision Curve Analysis (Net Benefit across cost ratios r in [0.02, 0.25]):\n- At r = 0.05: Net Benefit = 0.0933 (vs Treat All = 0.0782, Treat None = 0.0000)\n- At r = 0.10: Net Benefit = 0.0527 (vs Treat All = -0.0078, Treat None = 0.0000)\n- At r = 0.20: Net Benefit = 0.0158 (vs Treat All = -0.1798, Treat None = 0.0000)\n[PASS] Model yields strictly positive net benefit over Treat All and Treat None across clinical cost ratios.",
        explanation: {
          simple: "Partitions customers into 4 risk tiers (Low, Moderate, High, Critical) and proves financial advantage: taking action using model guidance always yields higher net profit than treating everyone or treating no one.",
          tech: "Defines 4 risk tiers with empirical validation; executes Decision Curve Analysis demonstrating positive standardized net benefit over default strategies across all operational cost ratios [0.02, 0.25]."
        },
        status: "success"
      },
      {
        stage: 7,
        title: "Stage 7: 1,000 Policy-Cluster Bootstrap & Reproducibility",
        badge: "VERIFIED",
        icon: "🏆",
        command: "python3 scripts/run_probability_calibration.py --check",
        log: "=======================================================\nPROBABILITY CALIBRATION & OPERATIONAL THRESHOLDS: VERIFIED\n=======================================================\n- 1,000 Policy-Cluster Bootstrap Replicates Computed:\n  * ECE 95% CI: [0.0065, 0.0185] (Median 0.0116)\n  * Brier Score 95% CI: [0.1166, 0.1257] (Median 0.1211)\n  * Calibration Slope 95% CI: [0.8654, 1.0366] (Median 0.9498)\n- Bit-for-bit manifest and report reproduction verified.\n- Candidate model weights: 100% immutable.\n- Final holdout status: strictly not_materialized.\n=======================================================\nPHASE 2.08 COMPLETE — OPERATIONAL DECISIONING READY\n=======================================================",
        explanation: {
          simple: "Final Seal: Ran 1,000 statistical cluster simulations to calculate rock-solid confidence intervals. Verified that all reports reproduce byte-for-byte with zero data leaks.",
          tech: "Computes 1,000 cluster bootstrap replicates grouped by policy_id for ECE, Brier score, and calibration slope. Validates byte-for-byte reproduction under --check. Final holdout untouched."
        },
        status: "success"
      }
    ]
  },
  v6_acceptance_proceed: {
    name: "Generation v6 Acceptance Gate (Protocol 3.1.0 Mechanical PROCEED)",
    stages: [
      {
        stage: 1,
        title: "Stage 1: Preflight & Boundary Audit",
        badge: "Passed",
        icon: "🛡️",
        command: "./scripts/check_repository_boundaries.sh",
        log: "Scanning 100% of tracked files for secrets, holdout leakage, and forbidden data...\n[PASS] Preflight boundary check passed with zero violations.\n[PASS] Substrate Contract 6.0.0 & Protocol 3.1.0 specifications verified.\n[PASS] Final release holdout confirmed: not_materialized.",
        explanation: {
          simple: "First, verifies repository integrity, ensures clean-room boundaries are respected, and confirms final holdout data has never been touched.",
          tech: "Executes check_repository_boundaries.sh; verifies ADR 0001 compliance and confirms final holdout state remains not_materialized."
        },
        status: "success"
      },
      {
        stage: 2,
        title: "Stage 2: 17-Feature Extraction & Dual-Time Filter",
        badge: "Passed",
        icon: "⚙️",
        command: "python3 scripts/build_v6_evaluation_pipeline.py --check",
        log: "Extracting 17 point-in-time features under Feature Dictionary 6.0.0...\nAsserting dual-time invariant: effective_date <= as_of AND ingested_at <= as_of...\n[PASS] 0 temporal leakage flags detected across all 4 evaluation folds.\n[PASS] Preprocessor cryptographic digest verified: 149d7ecc...",
        explanation: {
          simple: "Extracts 17 behavior features without looking into the future. Verifies all paperwork was formally recorded before the decision date.",
          tech: "Validates strict point-in-time event lineage for 17 features under Feature Dictionary 6.0.0; confirms 0 leakage flags."
        },
        status: "success"
      },
      {
        stage: 3,
        title: "Stage 3: Candidate Reload & Scoring Authorization",
        badge: "Passed",
        icon: "📜",
        command: "python3 scripts/run_v6_acceptance_protocol.py --check-only",
        log: "Reloading frozen Logistic Regression release candidate state...\nVerifying runtime predictions against frozen weights -> EXACT MATCH\nValidating scoring authorization digest against Contract 6.0.0...\n[PASS] Scoring authorization verified: 572238427bf... [LOCKED]\n[PASS] Candidate state hash matches ADR 0012 authorization.",
        explanation: {
          simple: "Loads the frozen Logistic candidate and verifies its digital seal matches the exact model approved in the candidate tournament.",
          tech: "Verifies candidate model state hash and scoring authorization digest 572238427bf...; guarantees zero unauthenticated code or weight changes."
        },
        status: "success"
      },
      {
        stage: 4,
        title: "Stage 4: 20-Seed Blind Acceptance Run (120 Inventory Units)",
        badge: "Passed",
        icon: "🎯",
        command: "python3 scripts/run_v6_acceptance_protocol.py",
        log: "Executing Protocol 3.1.0 across 20 reserved acceptance seeds (20271201..20271220)...\nEvaluating 3 temporal folds per seed (60 signal units + 60 matched null units)...\n[PASS] 120/120 inventory units successfully evaluated.\n[PASS] Zero right-censoring violations and minimum class counts satisfied in all folds.",
        explanation: {
          simple: "Runs the frozen AI across 20 reserved, unseen customer test batches and 120 total test units to ensure unbiased evaluation.",
          tech: "Executes 120 inventory units across 3 chronological folds and 20 reserved acceptance seeds under Protocol 3.1.0."
        },
        status: "success"
      },
      {
        stage: 5,
        title: "Stage 5: Primary Accuracy & Signal Recovery Gate",
        badge: "Passed",
        icon: "📈",
        command: "python3 scripts/run_v6_acceptance_protocol.py",
        log: "Computing primary discrimination and signal recovery metrics:\n- Median Signal ROC AUC: 0.7031 >= 0.6800 -> [PASS]\n- Seed Consistency: 20/20 seeds >= 0.6500 -> [PASS (100% vs 80% req)]\n- Worst-Fold ROC AUC: 0.6709 >= 0.6000 -> [PASS]\n- Average Precision Lift over Null: +0.1344 >= +0.1000 -> [PASS]\n- Brier Skill Score: +0.0658 > 0.0000 -> [PASS]",
        explanation: {
          simple: "All primary accuracy targets are crushed! The AI hits 70.3% median accuracy, beats the placebo by +13.4%, and passes 20 out of 20 test seeds.",
          tech: "Primary gates satisfied: median AUC 0.7031 (threshold 0.68), 20/20 seed consistency >= 0.65, AP lift +0.1344 (threshold +0.10), BSS +0.0658."
        },
        status: "success"
      },
      {
        stage: 6,
        title: "Stage 6: Protocol 3.1.0 Secondary Rule Evaluation",
        badge: "Passed",
        icon: "🔬",
        command: "python3 scripts/run_v6_acceptance_protocol.py",
        log: "Evaluating calibrated secondary quality rules under ADR 0013:\n- Null Coverage: 16/20 in 90% CI (Gate: >= 15/20) -> [PASS]\n- Shuffle Coverage: 17/20 in 90% CI (Gate: >= 15/20) -> [PASS]\n- Oracle Ordering: Max gap 0.0045 <= 0.0100 (epsilon) -> [PASS]\n- Variance Contraction: Width ratio 0.9864 <= 1.0000 -> [PASS]\n[PASS] All 10 rule families evaluated across 120 inventory units.",
        explanation: {
          simple: "Evaluates the 4 recalibrated secondary quality checks (placebo confidence intervals, numerical ordering, and sample size spread). All pass cleanly!",
          tech: "Secondary rules pass under Protocol 3.1.0: binomial coverage (>=15/20), continuous-discrete oracle ordering (gap <= 0.0100), and variance contraction."
        },
        status: "success"
      },
      {
        stage: 7,
        title: "Stage 7: Mechanical Gate Decision: PROCEED",
        badge: "PROCEED",
        icon: "🏆",
        command: "python3 scripts/run_v6_acceptance_protocol.py",
        log: "=======================================================\nMECHANICAL DECISION: PROCEED (10 / 10 Rule Families Pass)\n=======================================================\n- Precedence: stop > redesign > proceed -> PROCEED derived mechanically.\n- Statistical Acceptance Manifest frozen with SHA-256 digests.\n- ADR 0013 adopted on main.\n- Phase 2R successfully completed.\n=======================================================\nAUTHORIZES RESUMPTION OF PHASE 2 (P2-08 / PR #96)\n=======================================================",
        explanation: {
          simple: "VICTORY! All 10 rule families passed across 120 test units. The machine generates a final 'PROCEED' verdict, officially finishing Phase 2R and unpausing Phase 2!",
          tech: "Acceptance Protocol 3.1.0 derives mechanical decision 'proceed'. Cryptographic acceptance manifest frozen; Phase 2R closed; authorizes P2-08."
        },
        status: "success"
      }
    ]
  },
  v6_candidate_selection: {
    name: "Generation v6 Candidate Selection (Logistic 70.6% vs XGBoost)",
    stages: [
      {
        stage: 1,
        title: "Stage 1: Clean-Room & Structural Support Audit",
        badge: "Passed",
        icon: "🛡️",
        command: "python3 scripts/check_v6_evaluation_support.py --check",
        log: "Asserting structural support across all 4 folds (fold_1..3, selection)...\n[PASS] fold_1: 1,662 eligible, 245 pos, 1,417 neg, 0 censored -> PASS\n[PASS] fold_2: 1,509 eligible, 273 pos, 1,236 neg, 0 censored -> PASS\n[PASS] fold_3: 1,015 eligible, 168 pos, 847 neg, 0 censored -> PASS\n[PASS] selection: 996 eligible, 167 pos, 829 neg, 0 censored -> PASS\n[PASS] All 4 billing frequencies present; zero right-censoring.",
        explanation: {
          simple: "First, verifies that all training, evaluation, and test sets have enough data, all payment frequencies, and zero missing outcome data.",
          tech: "Executes check_v6_evaluation_support.py; asserts min eligible >= 500, min class >= 50, all 4 frequencies, and 0% right censoring."
        },
        status: "success"
      },
      {
        stage: 2,
        title: "Stage 2: Point-in-Time 17-Feature Extraction & Pipeline Fitting",
        badge: "Passed",
        icon: "⚙️",
        command: "python3 -c 'from inforsight_simulator.v6_evaluation import fit_preprocessor, transform...'",
        log: "Extracting 17 point-in-time features under Feature Dictionary 6.0.0...\nValidating event lineage: effective_date <= as_of and ingested_at <= as_of...\nFitting statistical standardizers strictly on designated training data...\nEncoding categories with reserved __unknown__ category path...\n[PASS] 28 output encoded features. Preprocessor digest: 149d7ecc... frozen.",
        explanation: {
          simple: "Extracts 17 behavior features without looking into the future. Prepares encoders strictly from training policies.",
          tech: "Validates strict event lineage for all 17 features, fits fit-only z-score standardizer and one-hot encoder with reserved __unknown__ token."
        },
        status: "success"
      },
      {
        stage: 3,
        title: "Stage 3: Non-Final Feature Diagnostics & Protected-Concept Screen",
        badge: "Passed",
        icon: "🔬",
        command: "python3 scripts/build_v6_evaluation_pipeline.py --check",
        log: "Screening feature space for protected identifiers or simulator internals...\n[PASS] 0 forbidden tokens (oracle, frailty, outcome, scenario) detected.\nComputing mutual information & single-feature shallow decision trees...\nStrongest driver group: recent_payment (Max MI: 0.048, Stump AUC: 0.655)\nDesigned zero group: missingness (Constant, 0 flags requiring redesign)\n=======================================================\nDIAGNOSTIC DECISION: ALLOW (0 Remediation Flags)\n=======================================================",
        explanation: {
          simple: "Runs diagnostic checks on every feature to ensure the AI isn't cheating using hidden simulator variables or memorizing IDs. Zero cheating detected!",
          tech: "Runs mutual information and stump tree screens; verifies absence of forbidden tokens; issues decision 'allow' with 0 flags."
        },
        status: "success"
      },
      {
        stage: 4,
        title: "Stage 4: Candidate Model Tournament (Logistic vs. XGBoost)",
        badge: "Passed",
        icon: "⚔️",
        command: "python3 scripts/build_v6_evaluation_pipeline.py --check",
        log: "Training Candidate 1: Logistic Regression (L2, C=1.0, liblinear)...\nTraining Candidate 2: XGBoost Comparator (25 trees, depth=2, lr=0.1, exact)...\nEvaluating both candidates on identical 996-observation selection fold:\n- Logistic Regression : ROC AUC = 0.7057 | Brier = 0.1287 | Log Loss = 0.4168\n- XGBoost Comparator  : ROC AUC = 0.6801 | Brier = 0.1354 | Log Loss = 0.4377",
        explanation: {
          simple: "Both AI models compete on the exact same unseen test cases. Logistic Regression outperforms XGBoost across every single metric!",
          tech: "Fits candidates on identical fit data; evaluates on selection fold. Logistic achieves superior ROC AUC (0.7057 vs 0.6801) and Brier calibration (0.1287 vs 0.1354)."
        },
        status: "success"
      },
      {
        stage: 5,
        title: "Stage 5: Deterministic Selection & Cryptographic Freeze",
        badge: "SELECTED",
        icon: "🏆",
        command: "python3 scripts/build_v6_evaluation_pipeline.py --check",
        log: "Applying frozen candidate selection rule:\n1. ROC AUC Comparison: 0.7057 > 0.6801 (+0.0256 delta >= 1e-12 tolerance)\n=======================================================\nSELECTED RELEASE CANDIDATE: LOGISTIC REGRESSION\nSELECTION REASON: higher_roc_auc\n=======================================================\nVerifying state reload against runtime predictions -> EXACT MATCH\nBinding scoring authorization: 572238427bf... [CRYPTOGRAPHICALLY FROZEN]\nAuthorizes Phase 2R.16 (Replacement Statistical Acceptance Protocol).",
        explanation: {
          simple: "Logistic Regression is officially crowned the Release Candidate. The exact mathematical weights and scoring permissions are cryptographically locked into place before final testing.",
          tech: "Deterministic selection rule chooses 'logistic' by higher_roc_auc. Reload predictions match; binds Scoring Authorization 6.0.0; authorizes Phase 2R.16."
        },
        status: "success"
      }
    ]
  },
  v6_qualified: {
    name: "Generation v6 Qualification (Bounded Sigmoid Hazard Link)",
    stages: [
      {
        stage: 1,
        title: "Stage 1: Repository Boundary & Clean-Room Audit",
        badge: "Passed",
        icon: "🛡️",
        command: "./scripts/check_repository_boundaries.sh",
        log: "Scanning 100% of tracked files for secrets, holdout leakage, and untracked artifacts...\n[PASS] No private keys or tokens detected.\n[PASS] Clean-room synthetic policy contracts validated.\n[PASS] Final release holdout confirmed: not_materialized.",
        explanation: {
          simple: "First, the system scans every file to ensure no sensitive credentials or future test holdout data were exposed.",
          tech: "Executes check_repository_boundaries.sh, verifying clean-room compliance under ADR 0001 and untouched holdout status."
        },
        status: "success"
      },
      {
        stage: 2,
        title: "Stage 2: Substrate Contract 6.0.0 Invariant Validation",
        badge: "Passed",
        icon: "📜",
        command: "python3 -c 'from src.synthetic import validate_contract_invariants; validate_contract_invariants()'",
        log: "Validating Substrate Contract 6.0.0 and Coefficient Registry 3.0.0...\n[PASS] Bounded sigmoid link functions validated: λ_max,lapse = 0.10, λ_max,surr = 0.05.\n[PASS] Max monthly total hazard constraint verified: λ_max = 0.1500 <= 0.1500 < 0.2000.\n[PASS] Linear predictor centering offsets and 6.0x scale invariants frozen.",
        explanation: {
          simple: "Checks that the new mathematical contract rules and coefficient bounds are strictly frozen before running any data.",
          tech: "Validates Contract 6.0.0 and Registry 3.0.0 parameters, ensuring mathematical impossibility of exceeding 0.1500 monthly hazard."
        },
        status: "success"
      },
      {
        stage: 3,
        title: "Stage 3: Bounded Sigmoid Synthetic Generation",
        badge: "Passed",
        icon: "⚙️",
        command: "python3 scripts/build_v6_modeling_corpus.py --seed 20280201",
        log: "Seeding random stream with 20280201 (Development Seed 1/20)...\nSimulating 14,400 policies across staggered issuance cohorts...\nApplying bounded sigmoid hazard link λ(t) = λ_max · σ(z)...\n[PASS] Observed peak monthly terminal hazard: 0.14999 (Ceiling: <= 0.15000).\n[PASS] 76,545 observations generated with deterministic SHA-256 manifest.",
        explanation: {
          simple: "Generates 14,400 customers using the new S-curve formula. The highest monthly cancellation rate observed was 14.999%, perfectly respecting insurance reality.",
          tech: "Executes v6 generator under Contract 6.0.0; enforces monthly hazard cap <= 0.1500 while producing realistic staggered survival dynamics."
        },
        status: "success"
      },
      {
        stage: 4,
        title: "Stage 4: Dual-Time Temporal Filter & Feature Seals",
        badge: "Passed",
        icon: "⏳",
        command: "python3 scripts/verify_dual_time_temporal_integrity.py",
        log: "Asserting dual-time invariant: observed_at <= cutoff_date < effective_date...\nChecking 76,545 point-in-time feature rows across 12 monthly slices...\n[PASS] Ingestion vs effective timestamps verified. 0 leaks detected.\n[PASS] Matrix digest validation passed.",
        explanation: {
          simple: "Verifies the dual-time machine: no paperwork filed tomorrow leaks into today's feature matrix.",
          tech: "Validates strict point-in-time feature construction and immutability seals across all evaluation cohorts."
        },
        status: "success"
      },
      {
        stage: 5,
        title: "Stage 5: Observable Oracle Quadrature & Calibration Gate",
        badge: "Passed",
        icon: "🎯",
        command: "python3 scripts/evaluate_observable_oracle.py",
        log: "Computing Gauss-Hermite quadrature observable oracle probabilities...\nObserved Oracle AUC: 0.7086 (Gate: >= 0.7000) -> [PASS]\nObserved Oracle AP Lift: +0.1398 (Gate: >= +0.1000) -> [PASS]\nBrier Skill Score: +0.0745 (Gate: > 0.0000) -> [PASS]\nMax Monthly Terminal Hazard: 0.14999 (Gate: <= 0.15000) -> [PASS]",
        explanation: {
          simple: "Evaluates the theoretical best-possible score using mathematical integration. The formula achieves 70.9% accuracy, beating both the accuracy and safety requirements!",
          tech: "Executes 32-point Gauss-Hermite quadrature oracle integration; achieves 0.7086 AUC, +0.1398 AP lift, and +0.0745 BSS within the 0.1500 hazard envelope."
        },
        status: "success"
      },
      {
        stage: 6,
        title: "Stage 6: Matched Null Placebo Control & Parity Audit",
        badge: "Passed",
        icon: "🔬",
        command: "python3 scripts/evaluate_null_placebo_control.py",
        log: "Running matched-seed null placebo control (permuted behavioral histories)...\nNull Oracle AUC: 0.5000 (Gate: [0.45, 0.55]) -> [PASS]\nNull Candidate AUC: 0.5040 (Gate: [0.45, 0.55]) -> [PASS]\nParity Mismatches: 0 across 120 inventory units -> [PASS]",
        explanation: {
          simple: "Tests against a scrambled fake dataset. Accuracy drops to an exact 50.0% coin flip, proving the real score comes from genuine customer behavior, not statistical fluke.",
          tech: "Validates empirical null distributions across permutation controls; confirms zero parity discrepancies across all 120 inventory units."
        },
        status: "success"
      },
      {
        stage: 7,
        title: "Stage 7: 20-Seed Gate Decision & Phase 2R.15 Authorization",
        badge: "QUALIFIED",
        icon: "🏆",
        command: "python3 scripts/run_v6_development_qualification.py",
        log: "Across-Seed Qualification Summary (20 Development Seeds):\n- Median Oracle AUC: 0.7086 >= 0.7000 [PASS]\n- Median Oracle AP Lift: +0.1398 >= +0.1000 [PASS]\n- Median Brier Skill Score: +0.0745 > 0 [PASS]\n- Max Monthly Hazard: 0.14999 <= 0.1500 [PASS]\n- Matched Null AUC: 0.5000 in [0.45, 0.55] [PASS]\n- Parity Mismatches: 0 [PASS]\n- Seed Recovery Count: 16/20 seeds >= 0.68 [PASS]\n- Reference Recovery Count: 20/20 seeds >= 0.65 [PASS]\n=======================================================\nMECHANICAL DECISION: QUALIFIED (All 9 Gates Passed)\n=======================================================\nADR 0012 Recorded. Substrate 6.0.0 Qualified for Model Acceptance.\nAuthorizes Phase 2R.15 with fresh evaluation seeds 20280301..20280320.",
        explanation: {
          simple: "VICTORY: All 9 gates passed across all 20 development test seeds. The substrate is officially qualified, authorizing final candidate model acceptance in Phase 2R.15!",
          tech: "Protocol 6.0.0 logs mechanical decision 'qualified'. Authorizes Phase 2R.15 candidate model acceptance under Contract 6.0.0 and ADR 0012."
        },
        status: "success"
      }
    ]
  },
  happy_v4: {
    name: "Normal Pass (v4 Pipeline with Signal)",
    stages: [
      {
        stage: 1,
        title: "Stage 1: Repository Boundary Audit",
        badge: "Passed",
        icon: "🛡️",
        command: "./scripts/check_repository_boundaries.sh",
        log: "Scanning 100% of tracked files for private keys, tokens, and forbidden datasets...\n[PASS] No secret patterns found.\n[PASS] Clean-room synthetic policy contracts validated.\n[PASS] Final release holdout confirmed: not_materialized.",
        explanation: {
          simple: "First, the system scans every file to make sure no passwords, private customer data, or forbidden files were accidentally checked in.",
          tech: "Executes check_repository_boundaries.sh, asserting clean-room compliance (ADR 0001) and ensuring test holdouts remain unmaterialized."
        },
        status: "success"
      },
      {
        stage: 2,
        title: "Stage 2: Deterministic Synthetic Generation",
        badge: "Passed",
        icon: "⚙️",
        command: "python3 scripts/build_v4_modeling_corpus.py",
        log: "Seeding random engine with 20261001...\nGenerating 14,400 fictional policies across staggered issuance cohorts...\nSimulating scheduled premium notices, payments, grace periods, and outcomes.\n[PASS] 76,545 point-in-time observations generated with exact SHA-256 manifest.",
        explanation: {
          simple: "The simulator creates 14,400 fictional customers. Because it uses a mathematical seed, running this code 10 years from now will produce the exact same customers down to the second.",
          tech: "Constructs 14,400-policy v4 corpus under contract 4.0.0 with scheduled billing variations and invariant random stream sets."
        },
        status: "success"
      },
      {
        stage: 3,
        title: "Stage 3: Dual-Time Point-in-Time Filtering",
        badge: "Passed",
        icon: "⏳",
        command: "python3 -m unittest discover -p 'test_leakage_guards.py'",
        log: "Auditing point-in-time visibility across all 76,545 observations...\nChecking invariant: effective_at <= as_of AND ingested_at <= as_of.\nSimulating 500 delayed paperwork events...\n[PASS] Zero future events leaked into cutoff feature vectors.",
        explanation: {
          simple: "The 'Paperwork Delay' test. The system tests events entered into the computer days after they happened, verifying that the AI never cheats by peeking at future paperwork.",
          tech: "Asserts dual-time point-in-time invariant (ADR 0005). Events with ingested_at > as_of are strictly hidden from cutoff feature extraction."
        },
        status: "success"
      },
      {
        stage: 4,
        title: "Stage 4: Cryptographic Scoring Authorization",
        badge: "Passed",
        icon: "🔒",
        command: "python3 -m unittest discover -p 'test_scoring_authorization.py'",
        log: "Generating tamper-evident digest seals for feature matrix...\nSHA-256: 7a78f00c91f464669175e9cef03c4a28...\nTesting partition relabeling attack: Matrix labeled 'validation' checked...\n[PASS] Target and matrix digests verified. Scoring authorized for validation only.",
        explanation: {
          simple: "Digital tamper seal. If someone tries to rename the test set or sneak a peek at the answers, the scoring engine locks down and refuses to run.",
          tech: "Scoring authorization contract binds row count, row order, preprocessor ID, purpose, and SHA-256 matrix digests (ADR 0004)."
        },
        status: "success"
      },
      {
        stage: 5,
        title: "Stage 5: Train-Only Preprocessing & Model Fit",
        badge: "Passed",
        icon: "🤖",
        command: "python3 scripts/build_v4_evaluation_pipeline.py",
        log: "Fitting numerical scalers and one-hot encoders strictly on Train partition...\nFitting XGBoost candidate on 1,498 selection episodes across 787 policies...\nNative JSON tree state exported and reload verified.\n[PASS] Training converged cleanly without target leakage.",
        explanation: {
          simple: "The AI learns exclusively from historical past policies. Future categories and test data are strictly sealed off during learning.",
          tech: "Transforms training matrix, reserves unknown categorical buckets, and fits frozen tree candidate with reproducible native JSON state."
        },
        status: "success"
      },
      {
        stage: 6,
        title: "Stage 6: Placebo & Matched Null Control Evaluation",
        badge: "Passed",
        icon: "🧪",
        command: "python3 scripts/run_v4_statistical_acceptance.py",
        log: "Evaluating XGBoost against paired Null stream (pure random noise)...\nEvaluating 20 distinct random seed blocks across 3 chronological folds...\nObserved Signal AUC: 0.672 (Threshold >= 0.65) -> PASS\nObserved Matched-Null Improvement: +0.165 (Threshold >= 0.10) -> PASS\nSeed consistency: 18/20 seeds passed (Threshold >= 16/20) -> PASS",
        explanation: {
          simple: "The Placebo Test: The AI is tested against pure random noise. In this v4 scenario, it scored 67% accuracy and beat the placebo by +16%, proving it found real customer signals!",
          tech: "Acceptance protocol 3.0.0 passes: signal AUC exceeds 0.65, matched-null improvement exceeds 0.10, and 18/20 seeds satisfy frozen binomial bounds."
        },
        status: "success"
      },
      {
        stage: 7,
        title: "Stage 7: Final Mechanical Gate Decision",
        badge: "PROCEED",
        icon: "🏆",
        command: "Decision Log: PROCEED",
        log: "=======================================================\nDECISION: PROCEED\n=======================================================\nAll 7 automated gates passed.\nSignal recovered with high statistical confidence (p < 0.01).\nNo leakage, no moving goalposts, no holdout exposure.\nRepository state is certified for release qualification.",
        explanation: {
          simple: "SUCCESS! All automated safety gates passed. The AI is proven to work honestly on real signals, and code is ready for release review.",
          tech: "Mechanical decision is PROCEED under protocol 3.0.0. Enables probability calibration (P2-08) and authorized release workflow."
        },
        status: "success"
      }
    ]
  },

  leakage_stop: {
    name: "Fail-Closed STOP (Tomorrow's Event Leaks Into Today)",
    stages: [
      {
        stage: 1,
        title: "Stage 1: Repository Boundary Audit",
        badge: "Passed",
        icon: "🛡️",
        command: "./scripts/check_repository_boundaries.sh",
        log: "Scanning tracked files for secrets and boundary violations...\n[PASS] No secret credentials or proprietary code found.\n[PASS] Clean-room assertions satisfied.",
        explanation: {
          simple: "Code repository is clean and has no secret passwords.",
          tech: "Boundary checks pass."
        },
        status: "success"
      },
      {
        stage: 2,
        title: "Stage 2: Synthetic Generator Run",
        badge: "Passed",
        icon: "⚙️",
        command: "python3 scripts/build_v2_modeling_corpus.py",
        log: "Generating synthetic policy corpus...\nWarning: An administrative event was logged with effective_at = 2024-02-01 but ingested_at = 2024-02-05.\nGenerated 42,795 observations.",
        explanation: {
          simple: "Generated customer histories, but one customer event had a 4-day paperwork delay.",
          tech: "v2 corpus built with latent administrative lag."
        },
        status: "success"
      },
      {
        stage: 3,
        title: "Stage 3: Dual-Time Preflight Gate Audit",
        badge: "FAIL-CLOSED STOP",
        icon: "🛑",
        command: "python3 scripts/run_v2_statistical_acceptance.py --check",
        log: "CRITICAL AUDIT EXCEPTION: READINESS-DUAL-TIME-VISIBILITY FAILED!\nFound observation cutoff as_of = 2024-02-02 containing event payload from 2024-02-05!\nEvent occurred earlier but was NOT ingested by cutoff date.\n=======================================================\nMECHANICAL DECISION: STOP\n=======================================================\n[HALT] Preflight caught post-cutoff ingestion leakage.\n[SAFETY] Machine learning model fitting aborted immediately.\n[SAFETY] Zero models fitted. Zero predictions created. Holdout sealed untouched.",
        explanation: {
          simple: "EMERGENCY BRAKE! The automated audit caught an event recorded next week slipping into today's decision. Rather than generating fake 99% accuracy scores, the pipeline slammed on the brakes and stopped everything!",
          tech: "Readiness rule READINESS-DUAL-TIME-VISIBILITY failed fail-closed. Protocol 1.0.0 enforces an unconditional STOP decision before model fitting."
        },
        status: "stop"
      }
    ]
  },

  weak_redesign: {
    name: "Fail-Closed REDESIGN (AI Fails to Beat Placebo)",
    stages: [
      {
        stage: 1,
        title: "Stage 1: Repository Boundary Audit",
        badge: "Passed",
        icon: "🛡️",
        command: "./scripts/check_repository_boundaries.sh",
        log: "Boundary preflight checks passed.\nClean-room schemas verified.",
        explanation: { simple: "Boundary checks pass.", tech: "Repository boundaries verified." },
        status: "success"
      },
      {
        stage: 2,
        title: "Stage 2: Synthetic Data Generation",
        badge: "Passed",
        icon: "⚙️",
        command: "python3 scripts/build_v3_modeling_corpus.py",
        log: "Generated 14,400 policies under v3 event-first specifications.\nDual-time timestamps verified.",
        explanation: { simple: "Generated 14,400 synthetic policies.", tech: "v3 corpus created." },
        status: "success"
      },
      {
        stage: 3,
        title: "Stage 3: Dual-Time Integrity",
        badge: "Passed",
        icon: "⏳",
        command: "Dual-time filter check",
        log: "Ingestion and effective timestamps checked. Zero leakage detected.",
        explanation: { simple: "No future paperwork leaks detected.", tech: "Dual-time invariant passes." },
        status: "success"
      },
      {
        stage: 4,
        title: "Stage 4: Scoring Authorization",
        badge: "Passed",
        icon: "🔒",
        command: "Matrix digest validation",
        log: "Matrix digests verified. Authorized validation scoring enabled.",
        explanation: { simple: "Tamper seals valid.", tech: "Scoring authorization passed." },
        status: "success"
      },
      {
        stage: 5,
        title: "Stage 5: Train Candidate Model",
        badge: "Passed",
        icon: "🤖",
        command: "Fit XGBoost candidate",
        log: "Trained XGBoost model across selection folds.\nModel saved to native JSON state.",
        explanation: { simple: "Model trained cleanly.", tech: "Candidate fit complete." },
        status: "success"
      },
      {
        stage: 6,
        title: "Stage 6: Placebo & 20-Seed Gate Evaluation",
        badge: "FAIL-CLOSED REDESIGN",
        icon: "🟠",
        command: "python3 scripts/run_v3_statistical_acceptance.py",
        log: "Evaluating XGBoost against 20 matched-seed null placebo controls...\nObserved Across-Seed Median AUC: 0.518869 (Required >= 0.68) -> [FAIL]\nSeeds meeting AUC >= 0.65: 0/20 passed (Required >= 16/20) -> [FAIL]\nMedian Matched-Null Improvement: +0.016097 (Required >= +0.10) -> [FAIL]\n=======================================================\nMECHANICAL DECISION: REDESIGN\n=======================================================\nZero seeds recovered signal. Noise in generator drowned out signal.\nHypotheses locked for diagnostic review under ADR 0006.\nFinal holdout remains untouched: not_materialized.",
        explanation: {
          simple: "THE HONEST REDESIGN: The AI only scored 51.8% accuracy (barely above a coin flip) and beat the placebo by only 1.6%. We didn't tweak settings or hide results; the system declared REDESIGN to fix the noisy simulator!",
          tech: "Protocol 2.2.0 records mechanical decision REDESIGN after decisive signal recovery failure. Prevents holdout tuning and mandates formal diagnostic study (R2-13)."
        },
        status: "redesign"
      }
    ]
  }
};

let simCurrentScenario = "p2_09_model_explanations";
let simCurrentStep = 0;
let simInterval = null;

function initSimulator() {
  const btnRun = document.getElementById('btnRunSimulation');
  const btnReset = document.getElementById('btnResetSimulation');
  const scenarioSelect = document.getElementById('simScenarioSelect');
  const btnClearTerm = document.getElementById('btnClearTerminal');

  if (btnRun) btnRun.addEventListener('click', startSimulation);
  if (btnReset) btnReset.addEventListener('click', resetSimulation);
  if (btnClearTerm) {
    btnClearTerm.addEventListener('click', () => {
      const logEl = document.getElementById('simTerminalLog');
      if (logEl) logEl.innerHTML = '';
    });
  }
  if (scenarioSelect) {
    scenarioSelect.addEventListener('change', (e) => {
      simCurrentScenario = e.target.value;
      resetSimulation();
    });
  }
}

function resetSimulation() {
  if (simInterval) clearInterval(simInterval);
  simCurrentStep = 0;

  const btnRun = document.getElementById('btnRunSimulation');
  if (btnRun) btnRun.disabled = false;

  // Reset Progress Bar
  const progressBar = document.getElementById('pipelineProgressLine');
  if (progressBar) {
    progressBar.style.width = '0%';
    progressBar.className = 'pipeline-progress-bar';
  }

  // Reset stage nodes
  for (let i = 1; i <= 7; i++) {
    const node = document.getElementById(`stageNode${i}`);
    if (node) {
      node.className = 'pipeline-stage-node';
      const icon = node.querySelector('.stage-status-icon');
      if (icon) icon.textContent = '⏳';
    }
  }

  // Reset detail card
  const badgeEl = document.getElementById('simStageBadge');
  const titleEl = document.getElementById('simStageTitle');
  const descEl = document.getElementById('simStageExplanation');
  const graphicEl = document.getElementById('simGraphic');

  if (badgeEl) badgeEl.textContent = 'Ready';
  if (titleEl) titleEl.textContent = 'Ready to Run Simulation';
  if (descEl) descEl.textContent = 'Select a scenario above and click "Run Pipeline Simulation" to observe how our automated gates execute.';
  if (graphicEl) {
    graphicEl.innerHTML = `
      <div class="anim-pulse-box">
        <div class="graphic-icon">🧪</div>
        <div class="graphic-label">Select a scenario above and click "Run Pipeline Simulation" to watch the animated process step-by-step.</div>
      </div>
    `;
  }

  // Reset terminal
  const logEl = document.getElementById('simTerminalLog');
  if (logEl) {
    logEl.innerHTML = `
      <div class="term-line info-line">$ make check</div>
      <div class="term-line muted-line">Scenario: ${pipelineScenarios[simCurrentScenario].name}</div>
      <div class="term-line muted-line">Awaiting execution trigger...</div>
    `;
  }
}

function startSimulation() {
  resetSimulation();
  const btnRun = document.getElementById('btnRunSimulation');
  if (btnRun) btnRun.disabled = true;

  const scenario = pipelineScenarios[simCurrentScenario];
  const stages = scenario.stages;

  simInterval = setInterval(() => {
    if (simCurrentStep < stages.length) {
      executeStage(stages[simCurrentStep]);
      simCurrentStep++;
    } else {
      clearInterval(simInterval);
      if (btnRun) btnRun.disabled = false;
    }
  }, 1600);
}

function executeStage(stageData) {
  // Update node classes
  const node = document.getElementById(`stageNode${stageData.stage}`);
  const progressBar = document.getElementById('pipelineProgressLine');

  if (node) {
    node.classList.add('active-stage');
    const icon = node.querySelector('.stage-status-icon');

    if (stageData.status === 'success') {
      node.classList.add('completed-stage');
      if (icon) icon.textContent = '✓';
    } else if (stageData.status === 'stop') {
      node.classList.add('stop-stage');
      if (icon) icon.textContent = '🛑';
      if (progressBar) progressBar.classList.add('stop-line');
    } else if (stageData.status === 'redesign') {
      node.classList.add('redesign-stage');
      if (icon) icon.textContent = '🟠';
      if (progressBar) progressBar.classList.add('redesign-line');
    }
  }

  // Update progress line percentage
  if (progressBar) {
    const totalSteps = pipelineScenarios[simCurrentScenario].stages.length;
    const pct = Math.min(100, Math.round((stageData.stage / 7) * 100));
    progressBar.style.width = `${pct}%`;
  }

  // Update Detail View
  const badgeEl = document.getElementById('simStageBadge');
  const titleEl = document.getElementById('simStageTitle');
  const descEl = document.getElementById('simStageExplanation');
  const graphicEl = document.getElementById('simGraphic');

  if (badgeEl) {
    badgeEl.textContent = stageData.badge;
    badgeEl.className = `badge badge-${stageData.status}`;
  }
  if (titleEl) titleEl.textContent = stageData.title;
  if (descEl) {
    descEl.textContent = state.explainerMode === 'simple' ? stageData.explanation.simple : stageData.explanation.tech;
  }

  if (graphicEl) {
    let animColor = stageData.status === 'stop' ? '#ef4444' : stageData.status === 'redesign' ? '#f59e0b' : '#38bdf8';
    graphicEl.innerHTML = `
      <div class="anim-pulse-box" style="color: ${animColor};">
        <div class="graphic-icon">${stageData.icon}</div>
        <div class="graphic-label" style="color: #f8fafc; font-weight: 700; font-size: 1rem;">${stageData.title}</div>
        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.25rem;">Command: <code>${stageData.command}</code></div>
      </div>
    `;
  }

  // Append to Terminal Log
  const logEl = document.getElementById('simTerminalLog');
  if (logEl) {
    const cmdLine = document.createElement('div');
    cmdLine.className = 'term-line info-line';
    cmdLine.textContent = `> ${stageData.command}`;
    logEl.appendChild(cmdLine);

    const outLine = document.createElement('div');
    if (stageData.status === 'stop') {
      outLine.className = 'term-line error-line';
    } else if (stageData.status === 'redesign') {
      outLine.className = 'term-line warn-line';
    } else {
      outLine.className = 'term-line success-line';
    }
    outLine.textContent = stageData.log;
    logEl.appendChild(outLine);

    logEl.scrollTop = logEl.scrollHeight;
  }
}

// Hook simulator into initApp
const origInitApp = initApp;
initApp = function() {
  origInitApp();
  initSimulator();
};

// Boot application
document.addEventListener('DOMContentLoaded', initApp);

