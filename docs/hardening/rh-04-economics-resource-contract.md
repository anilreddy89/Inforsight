# RH-04D: Signed treatment effects and shared economics 1.0.0

Status: proposed through [issue #148](https://github.com/anilreddy89/Inforsight/issues/148). This document is a design contract; runtime migration is RH-04I.

## Boundary and normative artifacts

[ADR 0016](../adr/0016-signed-treatment-effects-and-shared-economics.md) establishes one versioned synthetic economics/resource boundary. Normative artifacts are under `data-contracts/rh/economics/v1/`:

- `economics-resource-contract.json`: exact assumptions, units, action resources, estimands, and compatibility rules.
- `economics-resource-contract.schema.json`: closed JSON Schema for version 1.0.0.
- `acceptance-fixtures.json`: eight fictional design cases for RH-04I.

Contract 1.0.0 is additive and pins RH-01 semantic catalog 1.0.0 by SHA-256. Consumers load both by explicit version and expected digest. Unknown versions, actions, currencies, or mismatched catalog bytes fail; no consumer merges assumptions from two versions. All values are synthetic reference assumptions, not actuarial, causal, accounting, or production forecasts.

## Treatment-effect estimand and sign

The sole primary effect in v1 is the absolute 90-day combined termination risk reduction:

`tau(i,a) = P(lapse OR surrender within 90 days | control,i) - P(lapse OR surrender within 90 days | action a,i)`.

The valid closed interval is `[-1, 1]`. Positive is beneficial, zero neutral, and negative harmful. Missing or nonfinite effects, values outside the interval, an incompatible target/horizon, or cause-specific effects whose sum does not equal a supplied combined effect make valuation unavailable. Do not clip, absolute-value, replace, or silently coerce these inputs. Abstain has exactly zero effect, zero cost, and zero personnel use.

Signed gross expected value is preserved even when selection correctly chooses abstain. A harmful action therefore has negative gross value and becomes still more negative after direct cost. Ineligible actions remain distinct from eligible harmful actions: ineligibility is an authority/rules result, while harm is an effect/value result. Quadrant display may describe the sign but cannot replace the numeric effect.

This contract does not establish causal identification. Existing Phase 3 effects are synthetic simulator assumptions and must be labeled accordingly. RH-12 owns corrected result generation and scientific-claim reconciliation.

## Money, rounding, and resources

Authoritative computed money uses integer `usd_micro`, where USD 1 = 1,000,000 micros and one source cent = 10,000 micros. This retains exact sub-cent expected values without binary floating-point storage. Multiply a decimal effect by integer annual-premium cents and 10,000, then round once to integer micros with decimal `ROUND_HALF_EVEN`. Subtract integer direct-cost micros afterward. Aggregate integer micros; convert to decimal USD only at a display/export boundary. A display conversion is never fed back into allocation or evaluation.

Personnel capacity and consumption use nonnegative integer seconds. One hour is 3,600 seconds. Aggregate and enforce seconds; divide by 3,600 only for display. Never truncate to whole hours, coerce a duration to a count of specialist actions, or derive staff time from elapsed-day units. RH-04I migrates shared representation; RH-05 owns portfolio constraint enforcement and optimizer validation.

The action rows reproduce RH-01 catalog 1.0.0 exactly: reminder USD 1.50/0 seconds, consultation USD 25/1,800 seconds, specialist USD 65/3,600 seconds, remediation USD 3/360 seconds, abstain USD 0/0 seconds. They supersede the conflicting OPE and dashboard constants only after RH-04I. A different cost, duration, currency, effect model, or value basis requires a new contract version.

## Economic meaning and combined-outcome mapping

Source `annual_premium_cents` is a domain fact from the matching RH-01 snapshot. It is not CLV, profit, cash surrender value, revenue recognized, or a realized retention outcome. Missing annual premium makes valuation unavailable; the optimizer must not insert a default.

Contract 1.0.0 defines one synthetic operational value basis: one year of annual premium preserved per avoided combined termination. Both lapse and surrender multipliers equal 1.0. This equality is the explicit bridge that permits the identified combined effect to be multiplied by annual premium without inventing cause-specific effects:

`gross_expected_value = tau_combined * annual_premium`.

If diagnostic cause-specific effects are present, lapse and surrender contributions are computed separately with the same multiplier and must sum exactly to the combined result after one aggregate rounding step. Their presence does not convert the combined predictive model into a cause-specific model. If a future contract assigns different lapse and surrender values, combined-only tau is insufficient: cause-specific effects or a separately governed allocation model become required. Cash surrender value, margin, acquisition cost, future-duration assumptions, and taxes are absent from v1; no adapter may manufacture them.

Required metric names and meanings:

| Metric | Meaning |
| --- | --- |
| `annual_premium_cents` | Source-derived annualized billed premium in cents |
| `modeled_expected_annual_premium_preserved_usd_micros` | Signed tau times the synthetic one-year premium basis |
| `modeled_expected_net_value_usd_micros` | Expected premium-preservation value less direct cost |
| `direct_cost_usd_micros` | Synthetic intervention cost assumption |
| `realized_annual_premium_preserved_usd_micros` | Unavailable until an observed, governed outcome and attribution contract exists |
| `profit_usd_micros` | Not defined by v1 and must not be derived or displayed |

New dashboard/report text must say “combined terminations expected to be avoided,” not “lapses prevented,” and “modeled expected annual premium preserved,” not “profit,” “generated value,” or “realized value.” Historical artifacts retain their bytes and receive contextual legacy labels rather than edits.

## Selection and serialization

Every valuation binds policy ID, snapshot ID/version/catalog digest, economics contract ID/version/digest, action ID, signed effect ID/value, annual premium, direct cost, personnel seconds, and calculation status. RH-04I will define immutable runtime models and canonical serialization. An available calculation carries integer gross, cost, and net amounts even when negative. An unavailable calculation carries a stable error code and no numeric substitute.

For eligible actions, selection maximizes signed net expected value using deterministic action-ID tie-breaking after comparing exact integer micros. Abstain is always the zero reference and wins when all other net values are `<= 0`. The losing harmful/neutral action rows stay in the decision evidence; selecting abstain must not overwrite their signed values with zero.

Required errors include `INCOMPATIBLE_ECONOMICS_CONTRACT`, `INCOMPATIBLE_SEMANTIC_CATALOG`, `UNKNOWN_ACTION`, `INVALID_EFFECT`, `TARGET_MISMATCH`, `VALUATION_UNAVAILABLE`, and `CONTEXT_MISMATCH`. Errors contain identifiers, not source payloads or customer data.

## Predeclared evaluation protocol

RH-12 reports two primary estimands separately:

1. **Frozen-assignment sampling uncertainty:** portfolio totals for already frozen action assignments, scores, effects, and economics assumptions across policy-cluster resamples. This does not rerun allocation and makes no new-portfolio procedure claim.
2. **New-portfolio allocation-procedure performance:** rerun the accepted RH-05 allocation procedure on each policy-cluster resample using frozen policy scores/effects and the original portfolio's fixed total money and personnel capacities. This estimates procedure behavior on portfolios sampled from the evaluation population, conditional on the frozen predictive model and assumptions.

The cluster is `policy_id`. Draw exactly the original number of unique policies with replacement. Each duplicate occurrence is retained and receives `policy_id#draw_index` as an occurrence identity; source policy ID remains the join key for frozen facts. Each occurrence contributes separately to totals and allocation. No deduplication, jitter, model refit, recalibration, or effect re-estimation is permitted.

For the frozen-assignment estimand, resampled resource totals are reported as observed and may exceed the original cap because assignments are not changed. For the allocation-procedure estimand, total budget micros and personnel seconds remain fixed at original portfolio values; they do not scale with sampled duplicates or portfolio composition. Report the seed, resample count, source cohort/snapshot identities, model/calibration identity, assignment or allocator identity, and economics contract digest.

Intervals are labeled “policy-cluster bootstrap sampling intervals conditional on frozen model, effect, and economics assumptions.” They are not uncertainty intervals for intervention efficacy, costs, causal identification, or the value basis.

## Sensitivity protocol

Run a separately labeled, predeclared scenario grid over at least treatment-effect scale, harmful-effect magnitude, direct-cost scale, and annual-premium value multiplier. Include a no-effect scenario, stronger-harm scenario, and higher-cost scenario. Each scenario has its own ID and complete assumptions. Do not pool scenario variation into bootstrap intervals or select scenarios after reviewing results. If allocation changes under a scenario, report this as procedure sensitivity rather than fixed-assignment sampling uncertainty.

## Consumer migration and ownership

| Surface | RH-04I migration | Later owner |
| --- | --- | --- |
| RH-01 semantic catalog / rules | Load pinned action IDs, cents, and seconds; rules do not calculate value | RH-04I version bridge; RH-02 eligibility |
| `optimization/uplift.py` | Preserve signed combined-termination effect; reject invalid inputs; bind effect identity | RH-04I |
| `optimization/models.py`, `utility.py` | Replace float USD/CLV defaults with versioned micros and source annual premium; retain negative rows | RH-04I |
| `optimization/solver.py` | Consume exact money/seconds contract without slot conversion | RH-05 enforces and validates allocation |
| `counterfactual/models.py`, policies, simulator, evaluator | Remove independent costs/hours; preserve signed harm; rename combined-target and expected-value metrics; implement both declared estimands | RH-04I contract bridge; RH-12 regeneration |
| dashboard config/bridge/loader/components | Remove local economics constants; display decimal conversions and honest labels; preserve unavailable states | RH-04I; RH-05 portfolio enforcement |
| qualification and reports | Derive assumptions/version from contract; do not mutate frozen Phase 3 artifacts | RH-12 regenerated evidence |
| workflow capacity | Reserve exact authoritative money and seconds with contract identity | RH-03 boundary; RH-05 capacity behavior |
| JSON Schema, Protobuf, OpenAPI | Add explicit units/version/effect/metric names and reject incompatible versions | RH-09 wire reconciliation |

Compatibility adapters may read a named legacy profile but must immediately convert cents/dollars and hours to authoritative integer units, attach the legacy source profile, and never emit them as contract 1.0.0 results unless all required identities and semantics match. Existing CLV-based optimizer results and Phase 3 OPE cost tables are legacy economics; they cannot be silently relabeled.

## Verification and rollout

RH-04D validates the closed schema, catalog pin, action conversions, exact signed fixture arithmetic, nontruncating personnel conversion, metric labels, and evaluation declarations. These tests do not prove runtime repair. RH-04I adds failing runtime regressions first, implements models/adapters, and verifies rules, optimization, OPE, dashboard, reports, qualification, and workflow consumers without regenerating historical evidence.

Run focused contract tests, full `make check` with headless plotting, repository boundary checks, and `git diff --check`. Restore any timing-only historical artifact rewrite and confirm frozen files remain byte-identical. No final-holdout access, model fitting, or corrected result inspection is authorized by RH-04D.
