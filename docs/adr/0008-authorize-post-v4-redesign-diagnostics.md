# ADR 0008: Authorize post-v4 redesign diagnostics

- Status: Proposed through [issue #76](https://github.com/anilreddy89/Inforsight/issues/76)
- Date: 2026-09-03
- Decision owner: Anil Jonnala
- Trigger: R2-14 mechanical `redesign` under protocol `3.0.0`
- Preserves: ADR 0007 and all v1 through v4 evidence as immutable audit records
- Enables: R2-14B diagnostic execution only after this ADR and its contract merge

## Context

R2-14 implemented v4 substrate `4.0.0` and completed all 20 development seeds.
Driver support, transform parity, matched-null behavior, and structural controls
passed. Observable recovery, aggregate recovery, probability quality, reference
recovery, and hazard validity failed. Median observable-oracle AUC was
`0.5666277193591145`, `0/20` seeds reached `0.65`, median AP lift was
`0.021991623169585837`, `0/20` reference fits reached `0.65`, and maximum monthly
terminal hazard was `0.21847588960475323` against the `<0.20` rule.

This evidence rejects immediate R2-15 entry but does not isolate the remaining
failure mechanism. Reusing protected qualification rows or adjusting v4 in place
would turn a frozen qualification block into tuning data.

## Decision

Treat seeds `20271101..20271120` as spent v4 development evidence. Only their
committed aggregates may inform the successor diagnostic questions.

Approve the documentation-only boundary in
`docs/modeling/phase-02r-14a-v5-diagnostic-authorization-contract.md`. It freezes
six hypotheses, exact diagnostic families and interpretations, protected access,
aggregate output, a constrained feasibility design, and a causal response table.

Freeze `20280101..20280120` as the v5 diagnostic development block. Preserve
`20271201..20271220` as reserved, unassigned, unmaterialized, and inaccessible.
The final holdout remains undefined and `not_materialized`.

R2-14A produces no diagnostic result and authorizes no v5 implementation. R2-14B
may execute only the frozen development inventory after this decision and contract
are merged. A later reviewed ADR must approve any v5 design before R2-14C.

## Alternatives considered

### Proceed to R2-15

Rejected because required v4 qualification gates failed.

### Tune v4 or selected qualification seeds

Rejected because v4 and its complete development block are spent evidence.

### Lower failed thresholds

Rejected because failure is not independent justification for threshold change.

### Inspect reserved acceptance seeds

Rejected because doing so would spend the untouched block before design freeze.

### Freeze bounded diagnostics on a new development block

Accepted because it preserves evidence and links any successor proposal to a
predeclared failure hypothesis.

## Consequences

- R2-14B adds a governed diagnostic increment before successor implementation.
- The fixed diagnostic block may return an unresolved result or `stop`.
- No diagnostic reference or feasibility grid point becomes a candidate by
  virtue of its result.
- R2-15, R2-16, and P2-08 through P2-12 remain blocked.

## Claim boundary

This decision establishes diagnostic governance only. It makes no statistical,
real-world, actuarial, causal, fairness, operational, customer-impact,
production-readiness, or release claim.

## Reversal or supersession

Supersede this ADR before R2-14B if any diagnostic retains caller discretion, a
seed domain overlaps, protected evidence can become a model input, the feasibility
grid can change after results, thresholds can drift, or reserved acceptance or
final-holdout material exists. Supersession preserves this decision historically.

