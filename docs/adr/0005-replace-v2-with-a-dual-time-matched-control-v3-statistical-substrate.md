# ADR 0005: Replace v2 with a dual-time, matched-control v3 statistical substrate

- Status: Accepted through [issue #53](https://github.com/anilreddy89/Inforsight/issues/53) and [PR #54](https://github.com/anilreddy89/Inforsight/pull/54), merge commit `09f678a`
- Date: 2026-08-29
- Decision owner: Anil Jonnala
- Supersedes: The statistical-substrate and acceptance-execution portions of ADR 0004
- Preserves: ADR 0004, protocol `1.0.0`, and the R2-07 `stop` evidence as immutable audit records
- Enables: R2-09 only after this ADR and its contracts are accepted and merged

## Context

R2-07 stopped before model fitting. Its structural fixture proved that v2 behavior features can contain values from an event whose `ingested_at` is later than the observation cutoff and whose event ID is absent from `visible_event_ids`. Protocol `1.0.0` classifies leakage as `stop`.

The same readiness audit found that protocol `1.0.0` is not executable against the current v2 boundary. Scenario fields participate in run identity, so changing signal, missingness, or drift rerandomizes streams that a matched comparison requires to remain fixed. R2-06 also did not freeze a selected candidate, the five macro driver groups, a strongest and zero-effect group, a canonical coefficient registry, or a label-shuffle domain. The three published acceptance folds have only 23, 19, and 31 positives, below the frozen minimum of 50.

No R2-07 model, prediction, bootstrap, acceptance metric, or final holdout was produced. This allows a replacement design to be predeclared honestly, but does not permit the original decision or protocol to be rewritten.

## Decision

Preserve v1 and v2 as historical evidence and introduce a separately versioned v3 statistical substrate governed by:

- statistical simulator, event, observation, and label contracts `3.0.0`;
- random-stream registry `1.0.0`;
- evaluation split, feature, preprocessing, scoring-authorization, and candidate-selection contracts `3.0.0`;
- acceptance protocol `2.0.0`; and
- the normative specifications in `docs/modeling/phase-02r-08-v3-statistical-substrate-contract.md` and `docs/modeling/phase-02r-08-statistical-acceptance-protocol.md`.

V3 generation is event-first. The generator creates immutable events, an observation builder filters them by both effective and ingestion visibility, and feature reconstruction consumes only that filtered event set. The outcome mechanism consumes the same public cutoff feature values plus governed latent frailty. No feature may be assembled directly from a pre-event generator value.

V3 separates three identities:

1. a scenario-invariant stream-set identity controls paired random draws and stable entity identities;
2. a complete artifact identity includes every intervention and output-affecting setting; and
3. an execution identity binds the artifact identity to code, dependency, contract, and command digests.

Null and robustness variants reuse the same stream-set identity. An intervention changes only its declared transform or threshold. Tests must prove equality of every unaffected primitive draw and event field, not merely equality of aggregate distributions.

The replacement protocol keeps the original estimand, 90-day boundary, 20-replication design, three rolling-origin folds, 1,000 policy-cluster bootstrap replicates, core metrics, and numeric decision thresholds. It makes previously missing procedures exact: candidate selection, driver groups, coefficient provenance, shuffle assignment, bootstrap derivation, nested learning subsets, atomic stress configuration, and readiness aggregation. It uses a new seed block and enlarged corpus solely to address known structural support; realized membership counts still fail closed rather than being forced or selectively regenerated.

The final release holdout remains `not_materialized`. Only a later dedicated release issue may authorize its one-shot creation and access under the existing frozen-candidate boundary.

## Alternatives considered

### Patch v2 and continue protocol 1.0.0

Rejected. V2 output and readiness evidence have already been inspected. In-place changes would obscure lineage and could falsely reinterpret the original predeclared experiment.

### Downgrade `stop`, weaken thresholds, or selectively replace failing seeds

Rejected. Leakage has mechanical precedence under protocol `1.0.0`. Changing its classification, reducing the 500/50/50 rule, or regenerating inconvenient replications would be evidence manipulation.

### Repair only feature leakage

Rejected. That would leave matched controls, random-domain ownership, selection, coefficient/group registries, resampling, stress isolation, and fold support unresolved.

### Introduce a separately versioned v3 substrate and protocol 2.0.0

Accepted. A clean version boundary preserves the audit trail and lets every replacement choice be reviewed before replacement results exist.

## Consequences

### Positive

- Every public feature has inspectable dual-time event provenance.
- Signal/null and stress comparisons share the primitive draws they are supposed to share.
- Candidate selection, ablation meaning, resampling, and learning behavior are reproducible rather than caller-defined.
- Larger role capacity reduces the known fold-support risk without conditioning on favorable outcomes.
- Readiness can fail before expensive model execution or metric production.

### Costs and risks

- V3 requires new generator, observation, evaluation, and artifact paths rather than a small patch.
- Four times the v2 policy count increases generation and acceptance runtime; implementation must measure and document resource use without reducing the frozen replication design.
- Matched scenarios may diverge in later observation membership after their shared outcome draw is interpreted under different hazards. Pairing therefore applies to primitive streams and common eligible identities, not to forced identical outcomes or survival paths.
- Enlarging a stochastic corpus improves expected support but cannot guarantee realized positives. The structural gate remains authoritative.
- Synthetic recovery still provides no evidence of real-world validity, fairness, causal effect, or production readiness.

## Compatibility and versioning

- V1 and current-v2 code paths, schemas, documents, manifests, and experiment artifacts remain unchanged.
- V3 code uses new types, module entry points, artifact names, and explicit `v3` paths; it must not silently route an old configuration through new semantics.
- V3 identifiers use the stream-set identity and stable entity/cutoff components so common entities can be paired across scenarios. Artifact and execution identities remain scenario-specific.
- Any change to the estimand, stochastic equations, coefficient registry, default corpus, stream ownership, fold dates, candidate-selection rule, resampling method, metric, threshold, tolerance, or aggregation rule requires a reviewed version increment before result inspection.
- Protocol `1.0.0` and its R2-07 decision are never amended or reclassified.

## Claim boundary

Even a replacement `proceed` decision supports only this claim: the repository's versioned implementation recovers its predeclared fictional mechanism while preserving the tested temporal, authorization, matched-control, and reproducibility invariants. It does not support actuarial, causal, fairness, operational, customer-impact, production-readiness, or real-world predictive claims.

## Implementation sequence

1. R2-09 implements the v3 event-first corpus and dual-time observation substrate.
2. R2-10 rebuilds v3 folds, features, preprocessing, diagnostics, candidates, selection evidence, and authorization.
3. R2-11 runs protocol `2.0.0` only after a readiness-only check passes.

Each issue begins from merged `main` after its predecessor closes. R2-08 authorizes design only and produces no statistical result.

## Reversal or supersession

This decision must be superseded before implementation continues if review finds that:

- the event-first mechanism cannot preserve the stated estimand and exact oracle;
- the stream registry cannot prove intervention ownership and unaffected-stream equality;
- the role/fold design cannot provide credible structural capacity without outcome conditioning;
- the required runtime is infeasible under documented project constraints; or
- any material rule remains caller-selected after replacement data are inspected.

Supersession preserves this ADR and all earlier evidence.
