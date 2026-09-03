# ADR 0009: Record R2-14B readiness stop

- Status: Accepted through [issue #78](https://github.com/anilreddy89/Inforsight/issues/78) and [PR #79](https://github.com/anilreddy89/Inforsight/pull/79), merge commit `3088c4c`
- Date: 2026-09-03
- Decision owner: Anil Jonnala
- Trigger: R2-14B readiness failure under ADR 0008 and contract `1.0.0`
- Preserves: ADR 0007, ADR 0008, and all v1 through v4 evidence
- Blocks: R2-14C and all downstream performance-dependent work

## Context

ADR 0008 permits result-producing R2-14B execution only when the diagnostic
contract removes caller discretion from every material result and disposition.
Contract `1.0.0` freezes the diagnostic IDs, algorithms, information domains,
feasibility grid, evidence paths, and three possible hypothesis dispositions.

The readiness implementation found that the contract does not define the
mechanical `supported` and `rejected` thresholds for hypotheses H1 through H5.
Choosing those thresholds in implementation or after diagnostic access would
change the dispositions and potentially the successor response. This is the
specific ambiguity ADR 0008 requires to fail before result-producing execution.

An uncommitted local diagnostic attempt had used implementation-defined
thresholds. Those outputs are not authorized evidence, are excluded from this
decision, and must not be used to infer a scientific or feasibility result.

## Decision

1. Record the R2-14B execution decision as `stop` at readiness.
2. Record zero executed inventory units and zero D16 feasibility cells.
3. Record `D1` through `D17` as `not_executed` with governed failure
   `readiness_stop_before_result_access`.
4. Leave all six hypothesis dispositions `unresolved`.
5. Select response `stop_contract_not_executable`.
6. Do not authorize R2-14C, R2-15, R2-16, or resumed Phase 2 work.
7. Keep seeds `20280101..20280120` unspent by an authorized run. Any future use
   requires a separately reviewed pre-result contract and authority decision.
8. Preserve reserved seeds `20271201..20271220` and the final holdout as
   unmaterialized and inaccessible.

## Consequences

- The R2-14B manifest, report, and disposition are readiness-only stop records.
- No claim may be made about H1 through H6, D16 feasibility, or a v5 design.
- A future diagnostic attempt requires a new issue and an amended contract that
  freezes complete disposition truth tables before any result access.
- Historical v4 failure evidence and its `redesign` decision remain unchanged.

## Alternatives considered

### Adopt thresholds from the local implementation

Rejected because they were not present in the merged pre-result contract and
were therefore subject to caller discretion after access.

### Treat diagnostic names as sufficient disposition rules

Rejected because a hypothesis label does not specify quantitative support,
rejection, ambiguity, non-finite, missing-evidence, or boundary behavior.

### Continue only D16 and D17

Rejected because the contract requires the complete inventory and mechanical
six-hypothesis disposition vector. Selective execution would violate the frozen
denominator and no-selective-rerun rules.
