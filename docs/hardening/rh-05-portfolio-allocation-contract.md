# RH-05D: Portfolio allocation contract 1.0.0

Status: accepted on 2026-09-09 through [issue #154](https://github.com/anilreddy89/Inforsight/issues/154) and [PR #155](https://github.com/anilreddy89/Inforsight/pull/155), merge `3645fae`. RH-05I runtime implementation for issue #157 is complete and locally verified on `fix/157-rh-05i-portfolio-allocation`; review and merge remain pending.

## Purpose and claim boundary

This contract defines the bounded local portfolio allocation problem, its deterministic evidence, and the validation required before the dashboard may describe recommendations as capacity-constrained. It consumes RH-04 economics/resource contract 1.0.0. It does not change runtime behavior, regenerate historical evidence, establish causal effects, or certify a production/distributed allocator.

The implementation may be called a **deterministic feasibility-preserving allocation heuristic**. It must not be called globally optimal. Version 1.0.0 accepts the heuristic when every output is feasible and its additive gap from an independent exact reference is no more than `0 usd_micro` on the declared exhaustive small-instance domain. A nonzero gap therefore fails RH-05I acceptance and requires either an exact implementation or a new, reviewed contract version with a justified nonzero threshold.

## Optimization problem

For portfolio occurrences `i` and eligible actions `a`, choose binary `x[i,a]`. Each occurrence selects exactly one action, including abstain. Ineligible or unavailable action rows have `x=0`.

Maximize:

`sum(x[i,a] * modeled_expected_net_value_usd_micros[i,a])`.

Subject to:

- `sum_a x[i,a] = 1` for every occurrence;
- `sum(x[i,a] * direct_cost_usd_micros[i,a]) <= budget_capacity_usd_micros`;
- `sum(x[i,a] * personnel_seconds[i,a]) <= personnel_capacity_seconds`;
- all arithmetic and comparisons use integers; and
- abstain is eligible with zero objective, cost, and personnel use.

Negative or zero non-abstain rows remain evidence but cannot improve on abstain. A missing valuation, unknown action, incompatible identity, invalid resource, or context mismatch is not coerced. The portfolio response must distinguish a rejected row from a failed allocation. Because abstain exists, a structurally valid portfolio is feasible even at zero capacity.

## Inputs, identity, and output

An allocation binds:

- allocator ID `inforsight.portfolio-allocation` and version `1.0.0`;
- portfolio and allocation IDs and one timezone-aware decision cutoff;
- RH-01 snapshot/catalog identity, RH-02 evidence identity, effect identity, and RH-04 economics contract identity for every occurrence;
- source `policy_id` plus distinct `occurrence_id` (required for bootstrap duplicates);
- every eligible, ineligible, harmful, neutral, unavailable, and abstain action row;
- exact budget capacity/use in `usd_micro` and personnel capacity/use in seconds; and
- selected action, objective contribution, rejection reason, calculation status, and deterministic tie-break evidence.

Canonical serialization is UTF-8 JSON with sorted keys, compact separators, no NaN/Infinity, integers for resources/value, and decimal effects already canonicalized by RH-04. Unknown allocator or economics versions fail with stable identifiers and no source payload.

## Determinism and algorithm

RH-05I will implement an exact bounded multiple-choice two-resource allocation procedure or a heuristic that reproduces the exact reference throughout the declared validation domain. Among allocations with equal objective value, compare the ordered vector of `(occurrence_id, selected_action_id)` pairs lexicographically and select the smallest vector. Input order cannot affect output.

The independent reference enumerates the Cartesian product of eligible choices for fictional portfolios containing 1–6 occurrences, 1–4 non-abstain choices per occurrence, nonnegative integer costs from the fixture grid, nonnegative integer personnel seconds from the fixture grid, and signed integer objective values. It filters infeasible assignments, maximizes the integer objective, and applies the same published tie rule. The production implementation must not call the reference.

For a candidate allocation `H` and exact reference `O`, the additive optimality gap is `objective(O) - objective(H)` in `usd_micro`. Feasibility failure is reported separately and always fails. Relative gap is not authoritative because the exact optimum can be zero. The RH-05I acceptance threshold is zero on all checked fixtures; outside the declared bounded reference domain, only feasibility and deterministic behavior are claimed unless the production algorithm is itself exact with documented limits.

## Marginal opportunity cost

Discrete shadow prices are not claimed. Report finite-difference capacity values separately:

- money opportunity value: `objective(B + delta_money, S) - objective(B, S)` for a declared positive integer `delta_money`;
- personnel opportunity value: `objective(B, S + delta_seconds) - objective(B, S)` for a declared positive integer `delta_seconds`.

Each result binds both solved allocation identities and deltas. It is nonnegative when the feasible set only expands. If either solve is unavailable, the opportunity value is unavailable. UI text must say “modeled marginal value for the declared increment,” not shadow price or guaranteed return.

## Dashboard and workflow lifecycle

The dashboard must construct all cutoff-visible snapshots, evidence, scores, effects, valuations, and eligible action rows before one portfolio allocation call. Queue recommendations, briefs, and workflow cases then consume selected rows from that allocation. Summary totals are recomputed from selected rows and current reservations; percentages never hide exact overflow or infeasibility.

An allocation is stale when its portfolio membership, cutoff, snapshot/evidence/effect/economics identity, capacity version, or accepted/rejected/override reservation state changes. Refresh creates a new allocation identity rather than mutating prior evidence.

The RH-03 transition boundary remains authoritative for execution. A specialist override must revalidate current eligibility, bind the reviewed context, and atomically reserve the action's exact money and personnel resources. Replacing a reservation releases the old amount and reserves the new amount in one guarded transition. On version conflict or insufficient remaining capacity, the entire change fails with no partial release. Concurrent requests against one capacity version produce at most one success.

## Strategy comparison protocol

Compare these strategies with identical portfolio occurrences, cutoff, eligibility rows, catalog, signed effects, economics identity, budget, personnel capacity, and frozen predictive scores:

1. non-intervention: abstain for every occurrence;
2. operational rules-only: deterministic eligible action priority without scores or economic objective, followed by the same feasibility boundary;
3. risk-ranked: descending frozen combined-termination risk, stable occurrence tie-break, choosing the declared action policy under the same resources;
4. allocation engine: the accepted RH-05 procedure.

Report feasibility, selected counts, exact resource use, modeled expected net value, combined terminations expected to be avoided, abstentions, unavailable rows, and allocation identity. These are synthetic, conditional comparisons, not causal, realized, or production-performance estimates. RH-12 owns regenerated portfolio results and both RH-04 estimands.

## Failure codes

Required statuses include `AVAILABLE`, `UNAVAILABLE`, and `FAILED`. Required stable codes include `INCOMPATIBLE_ALLOCATOR`, `INCOMPATIBLE_ECONOMICS_CONTRACT`, `CONTEXT_MISMATCH`, `VALUATION_UNAVAILABLE`, `INVALID_RESOURCE`, `INVALID_CAPACITY`, `INFEASIBLE_SELECTION`, `STALE_ALLOCATION`, `CAPACITY_VERSION_CONFLICT`, and `CAPACITY_EXCEEDED`.

## Migration and ownership

RH-05I replaces specialist counts, floating-point budget aggregation, and independent dashboard recommendations on the current operational path. A named legacy adapter may convert dollars/hours/counts for historical callers but cannot label its output contract 1.0.0 without exact RH-04 identities and lossless conversion. Frozen Phase 3 manifests and reports retain their bytes and legacy labels.

RH-09I owns wire reconciliation. RH-11 owns integrated CI and read-only qualification. RH-12 owns corrected evidence and must use allocator version 1.0.0 for the new-portfolio procedure estimand with fixed original portfolio capacities and duplicate occurrence identities. RH-13 owns the release decision.

## Verification

RH-05D validates the machine-readable contract and fixtures, exact reference arithmetic, tie-breaking, zero-gap declaration, resource units, failure vocabulary, dashboard sequencing, override atomicity, and strategy-comparison invariants. RH-05I adds production/reference comparisons, dashboard and workflow regressions, component suites, full `make check`, boundary checks, and `git diff --check`.

No final-holdout access, model fitting, distributed infrastructure, historical artifact rewrite, or corrected-result inspection is authorized by RH-05D.
