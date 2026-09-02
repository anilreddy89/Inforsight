# ADR 0007: Approve the v4 signal-recovery design

- Status: Accepted through R2-13 issue #69; pull-request review pending
- Date: 2026-09-01
- Decision owner: Anil Jonnala
- Evidence: R2-13 diagnostic manifest and interpretation amendment `1.1.0`
- Supersedes for new development: ADR 0005 mechanism design
- Preserves: ADR 0005, ADR 0006, and every v1/v2/v3 artifact as historical evidence
- Enables: R2-14 implementation and development qualification only

## Context

The complete R2-13 development block produced these mechanical dispositions:

| Hypothesis | Disposition |
| --- | --- |
| Observable-oracle separability | `supported` |
| Realized driver support | `supported` |
| Mechanism/feature parity | `rejected` |
| Episode or weighting dilution | `rejected` |
| Candidate learning failure | `unresolved` |
| Temporal instability | `rejected` |

Observable-oracle median AUC was `0.533299464504321`, with `0/20` seeds meeting
the `0.65` rule. `rolling_payment_count`, a nonzero registered term, was near
constant. Exact parity had zero mismatches, policy/episode sensitivity had median
absolute AUC difference `0.0`, and median oracle fold spread was
`0.03917027146857244`.

## Decision

Create a separate v4 substrate under contract `4.0.0`. Preserve the event-first
dual-time boundary, 90-day union estimand, roles, folds, features, candidates,
random-stream ownership, matched null, policy grouping, and protected oracle.

Change only the diagnosed mechanism classes:

1. use coefficient registry `2.0.0`, doubling each nonzero public coefficient;
2. reduce latent frailty standard deviation from `0.35` to `0.20`;
3. generate scheduled billing/payment opportunities at the policy's actual billing
   frequency so rolling 365-day payment count has governed variation; and
4. recalibrate only the cause-specific intercepts to `-4.85` lapse and `-5.55`
   surrender, subject to the predeclared qualification gates.

R2-14 must implement this design once and run the development qualification gates.
A failed gate returns to reviewed design; it does not permit iterative use of the
future acceptance block.

## Alternatives considered

- Candidate-only redesign: rejected because H1 is supported and H5 unresolved.
- Fold or weighting changes: rejected because H4 and H6 are rejected.
- Feature-contract repair: rejected because H3 is rejected.
- Coefficient-only change: rejected because it does not address the supported
  realized-support finding.
- Broader corpus or estimand redesign: rejected as larger than the evidence needs.

## Consequences

- V4 requires separate types, identities, artifacts, schemas, and tests.
- Historical v3 results remain failed evidence and are never overwritten.
- The unchanged candidate set cannot be interpreted until v4 qualification passes.
- Qualification may reject the chosen magnitudes; that failure requires review,
  not tuning against future acceptance.
- The design supports only fictional-mechanism recovery testing.

## Claim and holdout boundary

This decision does not establish real-world performance, actuarial validity,
causality, fairness, operational utility, production readiness, or release
readiness. Future acceptance seeds `20271201..20271220` and the final holdout remain
`not_materialized` throughout R2-14 and R2-15.

## Supersession

Supersede this ADR if implementation cannot reproduce the equations, violates
matched-stream or dual-time invariants, fails any frozen qualification gate, or
requires a change outside the two supported diagnostic classes.
