# ADR 0006: Approve the v4 signal-recovery diagnostic boundary

> R2-13 issue #69 adds accepted pre-result interpretation amendment `1.1.0` at
> `docs/modeling/phase-02r-13-v4-diagnostic-interpretation-amendment.md`. It
> freezes the algorithms, thresholds, and precedence needed to derive the six
> hypothesis dispositions before development diagnostic output is accessed.

- Status: Accepted through [issue #66](https://github.com/anilreddy89/Inforsight/issues/66) and [PR #67](https://github.com/anilreddy89/Inforsight/pull/67), merge commit `ea9cf1f`
- Date: 2026-09-01
- Decision owner: Anil Jonnala
- Trigger: R2-11 mechanical `redesign` decision under protocol `2.2.0`
- Preserves: ADR 0005 and all v1, v2, and v3 evidence as immutable audit records
- Enables: R2-13 diagnostic execution only after this ADR and its contract merge

## Context

R2-11 passed readiness for all 20 v3 signal/null pairs, then failed the frozen
signal-recovery rules. Zero signal seeds reached the required median-fold AUC or
matched-null improvement thresholds. Across-seed median signal AUC was `0.518869`,
median average-precision lift was `0.009834`, and median Brier skill was
`-0.011851`. No `stop` rule failed. Later required families remained incomplete
`redesign` failures after decisive termination.

The evidence proves that the selected v3 candidate did not recover the fictional
mechanism. It does not determine whether the cause is weak observable-oracle
separation, weak realized driver support, a feature/mechanism mismatch, episode or
weighting dilution, candidate learning failure, temporal instability, or a
combination. Directly increasing coefficients or iterating on the failed seeds
would turn acceptance evidence into development data.

## Decision

Treat v3 acceptance seeds `20261001` through `20261020` as spent evidence. Their
committed aggregate results may explain the redesign trigger, but their row-level
data and results may not select coefficients, features, candidates, thresholds,
or seeds.

Approve the bounded diagnostic design in
`docs/modeling/phase-02r-12-v4-redesign-diagnostic-contract.md`. It freezes six
hypotheses, exact diagnostic families, protected-intermediate handling, output
schemas, and disposition rules before diagnostic output exists.

Freeze these disjoint v4 seed domains:

- development diagnostics: `20271101` through `20271120`;
- future acceptance: `20271201` through `20271220`.

R2-12 materializes neither domain and runs no result-producing diagnostic. R2-13
may execute only the development inventory. The future acceptance domain remains
unmaterialized until a later reviewed v4 implementation, evaluation, and candidate
freeze authorize one acceptance execution.

An R2-13 finding may support only the corresponding response in the frozen
decision table. It does not itself authorize implementation. A superseding ADR,
substrate contract, and protocol must approve v4 before R2-14 begins.

## Alternatives considered

### Tune or rerun v3

Rejected. The v3 acceptance block is spent evidence; using it for selection would
invalidate a later claim of untouched replacement acceptance.

### Increase observable coefficients immediately

Rejected. This assumes low oracle separation without distinguishing transform,
support, episode, candidate, or temporal causes.

### Permit unrestricted exploratory diagnostics

Rejected. Unregistered outputs create caller discretion, multiplicity, and
selective-reporting risk.

### Predeclare bounded diagnostics on a separate development block

Accepted. It preserves the audit trail, isolates future acceptance, and links any
v4 proposal to a diagnosed failure class.

## Consequences

### Positive

- The failed v3 block cannot silently become a tuning set.
- Every diagnostic has a purpose and an evidence-to-action mapping.
- Oracle and mechanism-parity work occurs only inside protected diagnostic
  authorization and cannot contaminate ordinary features.
- A disjoint future acceptance block is frozen before development results.
- Mixed or incomplete evidence fails closed instead of forcing a simulator change.

### Costs and risks

- R2-13 adds a separate diagnostic cycle before v4 implementation.
- The fixed development block may leave a hypothesis unresolved; another reviewed
  diagnostic version would then be required.
- Diagnostic reference models and sensitivities require strict labeling so they
  do not silently change the estimand or release candidate.

## Compatibility and versioning

- ADR 0005, v3 contracts, protocol `2.2.0`, and R2-11 evidence remain unchanged.
- R2-12 adds governance documents and read-only consistency checks only.
- Any simulator, coefficient, corpus, estimand, fold, feature, candidate,
  resampling, metric, threshold, tolerance, or aggregation change requires a new
  reviewed version before future acceptance output.
- Development diagnostics cannot be relabeled as acceptance evidence.

## Claim boundary

R2-12 supports only the claim that the repository predeclared a bounded diagnostic
process after a synthetic signal-recovery failure. It makes no new statistical,
real-world, actuarial, causal, fairness, operational, customer-impact,
production-readiness, or release claim.

## Reversal or supersession

Supersede this ADR before R2-13 if review finds that a diagnostic remains
caller-selected, seed domains can overlap, protected intermediates can enter model
features, an output can expose row-level evidence, or a disposition can authorize
an unrelated design change. Supersession preserves this ADR and all earlier
evidence.
