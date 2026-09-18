# Bounded reviewer walkthrough

This walkthrough describes the reviewer journey demonstrated by the local
reference implementation. It is a synthetic, bounded product walkthrough, not
a production operating procedure.

## 1. Establish the review context

Load the fictional cohort, policy identifier, observation cutoff, model bundle
identity, semantic catalog, economics contract, and allocation capacities. The
review context must be bound to a point-in-time snapshot; later events cannot
change the visible facts.

## 2. Inspect predictive perception

The inference runtime scores the point-in-time feature record and presents a
calibrated 90-day combined lapse-or-surrender risk estimate with bounded
directional explanations. The score prioritizes review; it does not select or
execute an action.

## 3. Inspect eligibility and evidence

The rules engine evaluates every action independently of the predictive score.
Missing or unknown servicing facts fail closed. An eligible action carries its
action, channel, safety, snapshot, catalog, and contract identities. An
ineligible action remains visible with a stable reason rather than becoming an
implicit approval or a fabricated negative fact.

## 4. Inspect economics and portfolio allocation

For each eligible action, the reviewer can inspect the signed modeled
combined-termination effect, exact direct cost in USD micros, personnel use in
seconds, gross modeled value, and net modeled value. The RH-05 allocator selects
one action or abstain across the portfolio under fixed capacities and stable
tie-breaking. Its output is advisory and carries `authorized_to_act: false`.

The RH-12 evidence report compares four strategies against one identical
context: non-intervention, operational rules-only, risk-ranked, and allocation
engine. Its primary estimand reruns the allocation procedure on policy-cluster
resamples while holding total capacity fixed.

## 5. Review the dossier and recommendation

The dashboard dossier combines the snapshot, risk score, explanation, safety
evidence, eligible actions, modeled valuation, and allocation identity. It
should show unavailable states explicitly and should not describe modeled value
as profit or a realized customer outcome.

## 6. Make a human decision

Only an accountable human reviewer may approve, reject, or request more
information. Current eligibility, exact reviewed identity, evidence binding,
freshness, idempotency, capacity, and concurrency are revalidated at the
execution boundary. A recommendation is never an execution authority.

## 7. Preserve the audit trail

The local reference workflow records the decision, actor, justification,
context identities, and audit transition. RH-10 defines the bounded local
recovery semantics and trust boundary. This walkthrough does not claim
distributed exactly-once behavior, attacker-resistant storage, or production
availability.

## Evidence and limitations

- Corrected portfolio evidence: [RH-12 report](../experiments/phase-rh-12-evidence-reconciliation-1.0.0.md).
- Contract boundaries: [RH-04](../hardening/rh-04-economics-resource-contract.md), [RH-05](../hardening/rh-05-portfolio-allocation-contract.md), and [RH-03](../hardening/rh-03-authority-boundary.md).
- Realism boundary: [docs/realism-boundary.md](../realism-boundary.md).
- The final holdout is not accessed by this walkthrough.
