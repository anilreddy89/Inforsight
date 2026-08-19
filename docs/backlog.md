# Initial Backlog

This backlog is ordered for a natural repository history. Each item should become a tracked issue before implementation.

## Phase 0 - Foundation

- [x] Create repository README, clean-room policy, assumptions, and initial ADRs.
- [x] Add contribution, security, licensing, and repository-boundary checks.
- [ ] Create hosted repository and configure branch protection.
- [ ] Convert the first implementation items below into hosted issues and a `v0.1.0-data-foundation` milestone.

## Phase 1 - Policy Digital Twin

- [x] Define `policy-event.schema.json` with explicit version and timestamps.
- [x] Define policy, billing, payment, notice, service, and outcome event payloads.
- [x] Add valid and invalid contract examples.
- [x] Implement a deterministic seeded generator for 100 policies.
- [x] Implement point-in-time state reconstruction.
- [x] Test event ordering, valid transitions, impossible dates, and deterministic replay ([issue #10](https://github.com/anilreddy89/Inforsight/issues/10)).
- [x] Publish a small sample dataset and `DATA_CARD.md` ([issue #12](https://github.com/anilreddy89/Inforsight/issues/12)).
- [x] Assess aggregate synthetic rates against cited public references and document calibration assumptions ([issue #14](https://github.com/anilreddy89/Inforsight/issues/14)).

Phase 1 is complete for the repository's documented MVP boundary. The broader 14-week planning materials also envisioned issue age, face amount, acquisition channel, recurring multi-period exposure, payment retries, reinstatement, maturity, loans, cash value, account changes, and prior conservation attempts. Those concepts remain intentionally deferred rather than silently treated as implemented. Phase 2.01 must decide which, if any, are required for a defensible baseline experiment and route each required addition through a separate versioned contract and generator change.

## Phase 2 - Baseline ML

- [ ] Define the Phase 2 modeling contract and data-sufficiency gate: active-policy eligibility, observation cadence, 90-day horizon, lapse-versus-surrender label policy, censoring, required observable fields, and any Phase 1 contract extensions that must be completed before training.
- [ ] Build deterministic observation records with an `as_of` timestamp and explicit effective-time and ingestion-time visibility rules so every feature represents information available by the observation cutoff.
- [ ] Add automated leakage and simulator-shortcut tests that reject post-cutoff events, labels or terminal outcomes in features, future ingestion, scenario identifiers, deterministic outcome proxies, and duplicate outcome episodes.
- [ ] Create policy-aware temporal train, validation, and test splits with documented boundaries, grouping or embargo rules, class distributions, and assertions that prevent random policy-month or outcome-episode leakage.
- [ ] Implement a versioned feature-building pipeline and feature dictionary covering types, missingness, provenance, allowed transformations, and deterministic regeneration.
- [ ] Train and document a seeded logistic-regression baseline as the transparent benchmark.
- [ ] Train a LightGBM or XGBoost tabular model and compare it with logistic regression on the same frozen observations and temporal splits.
- [ ] Calibrate probabilities using validation data only and report held-out discrimination, calibration, precision at operational review capacity, recall in high-risk bands, threshold tradeoffs, and explicit false-positive cost assumptions.
- [ ] Publish SHAP or equivalent attribution examples with feature sanity checks and clear boundaries that explanations describe model behavior rather than authorize conservation actions.
- [ ] Version the training configuration, dependencies, feature contract, split manifest, metrics, and model artifacts so training and held-out scoring reproduce from documented commands.
- [ ] Publish `MODEL_CARD.md`, an experiment report, and a Phase 2 decision note that compare both models, disclose synthetic-data limitations, and demonstrate the acceptance gate: reproducible training, held-out temporal scoring, calibrated probabilities, and explanations without future information.
- [ ] Publish the agreed risk-model release marker and release notes after the Phase 2 gate, reconciling the roadmap's `v0.3.0-risk-model` name with the repository's actual release sequence rather than creating an inconsistent tag.

## Deferred intentionally

- Evaluate richer lifecycle contracts only when the Phase 2 data-sufficiency gate demonstrates that the MVP requires them: issue age, face amount, acquisition channel, recurring exposure, payment retries, reinstatement, maturity, loans, cash value, address and payment-method changes, and prior conservation attempts.
- Add SQL persistence schemas only when a storage consumer requires them.
- Java services, Kafka, cloud deployment, bounded agents, and RAG remain deferred until the data and baseline-model gates pass.
