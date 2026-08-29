# ADR 0004: Introduce a versioned statistical simulator and predeclared evaluation gate

- Status: Proposed in [issue #42](https://github.com/anilreddy89/Inforsight/issues/42)
- Date: 2026-08-29
- Decision owner: Anil Jonnala
- Enables: R2-05 after this ADR and its linked contracts are accepted and merged

## Context

The v1 generator is a deterministic lifecycle-coverage fixture. It validates schemas, replay, point-in-time construction, leakage controls, preprocessing, serialization, and scoring authorization, but it was not designed as a statistical population.

Three recorded limitations prevent performance-dependent work:

- `LIM-002-001`: first-billing observation time is confounded with billing frequency across the v1 chronological split;
- `LIM-002-002`: v1 has no designed pre-cutoff feature-conditioned outcome mechanism; and
- `LIM-002-003`: the v1 test fixture was prediction-accessed during review and cannot be a release holdout.

A replacement must let the repository test whether a governed modeling pipeline can recover a known synthetic mechanism across time and random replications. Its design and success criteria must be fixed before results exist.

## Decision

Preserve v1 unchanged as historical `pipeline_engineering_only` evidence and introduce a separately versioned v2 statistical corpus governed by:

- statistical simulator contract `2.0.0`;
- observation and label contract `2.0.0`;
- evaluation protocol `1.0.0`; and
- the normative specifications in `docs/modeling/phase-02r-04-v2-statistical-simulator-and-observation-contract.md` and `docs/modeling/phase-02r-04-statistical-acceptance-protocol.md`.

V2 will use multiple issuance cohorts, recurring monthly observations, dual effective-time and ingestion-time visibility, a seeded stochastic discrete-time competing-risk mechanism, latent policy frailty, and protected oracle sidecars. It will explicitly model censoring, missingness, ingestion delay, corrections, category arrival, and named temporal-drift scenarios.

The primary estimand is the probability that an eligible active policy has an adverse termination—lapse or surrender—during `(as_of, as_of + 90 elapsed days]`, conditional on information visible at `as_of`. Cause-specific outcomes remain in audit provenance.

Fitting, selection, calibration, non-final evaluation, statistical acceptance, and final release testing have separate roles. The final release holdout will not be materialized during R2-04 through R2-07. A later release issue must freeze the candidate and all artifact digests before authorizing one auditable evaluation.

R2-07 will apply the thresholds frozen in evaluation protocol `1.0.0`. Only a merged `proceed` decision resumes P2-08 and P2-09. A post-result protocol change creates a new protocol version and forces `redesign`; it cannot reinterpret the original run.

## Alternatives considered

### Continue using v1

Rejected for statistical evaluation. V1 has no known pre-cutoff signal and its billing schedule determines observation timing. Favorable metrics cannot distinguish recovery from seed noise or temporal composition.

### Modify only the v1 observation time or use a random split

Rejected. This could conceal the known confounding without adding recurring exposure, a recoverable stochastic mechanism, temporal robustness, or an honest release holdout. It would also rewrite the meaning of historical v1 evidence.

### Build an opaque high-fidelity simulator

Rejected for this gate. Complexity without inspectable probabilities makes falsification, oracle comparison, and failure diagnosis harder. Rich lifecycle behavior remains eligible only when required by the declared estimand.

### Use the transparent versioned v2 design

Accepted. It is complex enough to exercise temporal modeling and realistic failure modes while retaining known ground truth, deterministic reproduction, and reviewable assumptions.

## Consequences

### Positive

- Signal recovery, negative controls, learning behavior, and drift robustness become falsifiable.
- Recurring observations remove the first-billing-only design and allow billing categories to overlap across time.
- Oracle probabilities provide a ceiling and calibration reference without entering model features.
- Separate roles and one-shot holdout rules reduce selection leakage.
- V1 remains byte-reproducible and historically interpretable.

### Costs and risks

- R2-05 and R2-06 require new versioned schemas, artifacts, and tests rather than modifying v1 in place.
- Repeated observations require policy-cluster-aware uncertainty and outcome-episode isolation.
- Synthetic recovery still does not establish external validity or real-world business value.
- A public deterministic repository can provide integrity and misuse guards, not cryptographic secrecy for a locally reproducible holdout.
- Predeclared thresholds may expose a weak design and require a new version rather than adjustment in place.

## Compatibility and versioning

- Generator versions `0.1.0` and `0.2.0`, event schema `1.0.0`, observation contract `1.0.0`, and all committed v1 artifacts remain unchanged.
- V2 identifiers and artifacts use a distinct namespaced run identity and `v2` path or filename segment.
- Any v2 event-schema extension must increment the applicable schema version and retain explicit v1 validation/replay paths.
- Oracle and latent fields use a governed sidecar and are prohibited from public observation features.
- Any change to the estimand, stochastic equations, default parameters, role boundaries, or acceptance thresholds requires a documented version increment.

## Claim boundary

Even a successful R2-07 gate supports only this claim: the implementation recovers a predeclared synthetic signal and preserves specified pipeline invariants across the tested seeds, temporal folds, and stress scenarios. It does not support actuarial, causal, fairness, operational, customer-impact, production-readiness, or real-world predictive claims.

## Reversal or supersession

This decision must be superseded when:

- R2-05 cannot implement the mechanism without violating point-in-time or schema invariants;
- structural checks show the required cohort, category, outcome, or censoring support cannot be produced;
- R2-07 returns `redesign` or `stop`;
- the target use case or estimand changes materially; or
- governed external data creates a different validation obligation.

Supersession must preserve this ADR and the original protocol as an audit record.
