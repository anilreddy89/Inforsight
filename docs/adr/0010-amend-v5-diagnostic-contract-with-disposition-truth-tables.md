# ADR 0010: Amend post-v4 diagnostic authorization contract with disposition truth tables

- Status: Proposed through [issue #80](https://github.com/anilreddy89/Inforsight/issues/80)
- Date: 2026-09-03
- Decision owner: Anil Jonnala
- Trigger: R2-14B readiness failure under ADR 0008, contract `1.0.0`, and ADR 0009
- Preserves: ADR 0007, ADR 0008, ADR 0009, and all v1 through v4 evidence as immutable records
- Enables: Phase 2R.14BB diagnostic execution on unspent development seeds `20280101..20280120`
- Blocks: Phase 2R.14C and all downstream performance-dependent work

## Context

Phase 2R.14A approved ADR 0008 and post-v4 diagnostic authorization contract `1.0.0`.
That contract froze 17 diagnostics (`D1` through `D17`), the 320-cell feasibility
grid, and the causal response table. However, contract `1.0.0` did not define the
quantitative, mechanical numerical criteria distinguishing `supported` from
`rejected` dispositions for hypotheses `H1` through `H5`.

During Phase 2R.14B under issue #78, the fail-closed readiness implementation detected
this material ambiguity. Under ADR 0008, caller or analyst discretion cannot choose
material thresholds in implementation or post-hoc. The runner therefore halted at
readiness with decision `stop_contract_not_executable`.

ADR 0009 recorded that zero diagnostic units and zero feasibility cells were
authorized or executed, left all hypotheses unresolved, reaffirmed development seeds
`20280101..20280120` as unspent, and established that:
> *"A future diagnostic attempt requires a new issue and an amended contract that
> freezes complete disposition truth tables before any result access."*

Issue #78 and ADR 0009 are now merged into `main` via PR #79 (merge commit `3088c4c`).
To enable diagnostic execution without caller discretion, the diagnostic authorization
contract must be amended before any result access.

## Decision

1. Approve Amended Post-v4 Diagnostic Authorization Contract `1.1.0` in
   `docs/modeling/phase-02r-14ba-v5-diagnostic-authorization-contract.md`.
2. Explicitly embed complete, unambiguous, quantitative support and rejection truth
   tables for hypotheses `H1` through `H5`, using the required fail-closed tokens
   (`<HYPOTHESIS_ID> supported when` and `<HYPOTHESIS_ID> rejected when`).
3. Reaffirm that development seeds `20280101..20280120` remain unspent by any
   result-bearing run and authorize their use strictly under successor increment
   Phase 2R.14BB.
4. Preserve reserved acceptance seeds `20271201..20271220` and the final release holdout
   as unmaterialized, unassigned, and strictly inaccessible.
5. Phase 2R.14BA produces zero synthetic data, zero observations, zero model fits, zero
   diagnostic metrics, and zero feasibility results.
6. Keep Phase 2R.14C (v5 substrate qualification), R2-15, R2-16, and Phase 2 resumed
   work (P2-08 through P2-12) blocked.

## Consequences

- Contract `1.1.0` becomes the authoritative diagnostic specification, superseding
  contract `1.0.0` for all future diagnostic execution.
- Successor increment Phase 2R.14BB is unblocked to execute diagnostics `D1` through
  `D17` and the 320-cell feasibility surface without caller discretion.
- Historical v4 qualification evidence (`redesign`), R2-14B readiness stop records
  (`stop_contract_not_executable`), and ADR 0008/ADR 0009 remain immutable audit records.
- No claim may be made regarding v5 design feasibility until Phase 2R.14BB completes.

## Alternatives considered

### Allow runner implementation to adopt discretionary thresholds without contract amendment

Rejected because ADR 0008 and ADR 0009 strictly prohibit post-access caller discretion.
Defining thresholds outside an approved pre-result contract compromises clean-room
governance.

### Combine contract amendment and diagnostic execution in one pull request

Rejected because clean-room protocol requires an approved, peer-reviewed governance
boundary before result-producing execution. Mixing contract definition and execution
creates the risk of tuning thresholds to match observed outputs.

