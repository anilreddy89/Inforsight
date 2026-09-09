# ADR 0016 — Preserve signed treatment effects through shared versioned economics

- Status: Accepted through [RH-04D issue #148](https://github.com/anilreddy89/Inforsight/issues/148) and [PR #149](https://github.com/anilreddy89/Inforsight/pull/149), merge `c9eddcf`
- Date: 2026-09-09
- Contract: [RH-04 economics/resource contract 1.0.0](../hardening/rh-04-economics-resource-contract.md)

## Context

Current optimization, OPE, dashboard, and workflow code uses different costs, floating-point dollar/hour units, CLV or annual-premium value bases, integer specialist slots, and lapse-only labels for a combined lapse-or-surrender target. Harm can be generated but is clipped from aggregate “prevented” metrics. These differences prevent coherent valuation and uncertainty claims.

## Decision

Adopt one explicitly versioned synthetic economics/resource contract. Preserve the signed absolute combined-termination effect from estimation through valuation and evidence. Store computed money as integer USD micros and personnel as integer seconds. Value each avoided lapse or surrender at one source-derived annual premium for the v1 synthetic basis, allowing combined effects to be valued without fabricated cause decomposition. Distinguish expected premium preservation from profit and realized value.

Predeclare two separately reported evaluation estimands: frozen-assignment policy-cluster sampling uncertainty and allocation-procedure performance on resampled portfolios. Keep model predictions frozen, define duplicate identities, hold portfolio capacities fixed for allocation-procedure resamples, and separate assumption sensitivity from bootstrap sampling intervals.

## Alternatives

- Continue floating-point dollars and hours: rejected because independent constants and integer/float conversions already drift and can truncate resource use.
- Use integer cents for expected values: rejected because probability-weighted values legitimately require sub-cent precision; integer micros provide deterministic aggregation and display conversion.
- Use CLV as policy value: rejected because it is an unsupported synthetic default and is not the source annual premium required by the product claim.
- Decompose combined risk using assumed lapse/surrender shares: rejected because the current model does not identify cause-specific effects. Equal v1 outcome multipliers make decomposition unnecessary and explicit.
- Clip harm to zero in portfolio summaries: rejected because it reverses the estimand and hides adverse intervention value.
- Report only the existing fixed-assignment bootstrap: rejected because it cannot support claims about reallocating new portfolios.

## Consequences

Some current valuations become unavailable instead of receiving defaults. Existing dashboards and reports remain legacy evidence until RH-04I and RH-12 migrate them. More fields and version checks are required, but every consumer can reconcile to exact shared assumptions. RH-05 can enforce capacity in seconds, RH-09 can expose unambiguous wire units, and RH-12 can regenerate honestly labeled results without refitting predictive models on evaluation resamples.
