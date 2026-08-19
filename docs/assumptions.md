# Fictional Domain Assumptions

These assumptions define the first simulator boundary. They are deliberately simplified and are not representations of any insurer's procedures.

## Portfolio

- All policies, products, people, identifiers, amounts, and dates are fictional.
- The first release models fictional term-life and whole-life product variants.
- Currency is USD and dates use ISO 8601 in UTC unless a contract states otherwise.
- Monetary amounts are represented as integer cents.
- Policy identifiers are synthetic and cannot be joined to external records.

## Policy lifecycle

- A policy has a versioned status and an effective date.
- Supported lifecycle statuses are active, grace period, lapsed, and surrendered.
- New policies begin active and use monthly, quarterly, semiannual, or annual billing.
- Billing, payment, notice, service, and policy-change events are immutable facts.
- Notices and service contacts contain structured categories only, without message text or personal content.
- Corrections are represented by new events rather than rewriting history.
- State reconstruction uses events whose `effective_at` time is on or before the requested as-of time; an event exactly at the cutoff is included.
- A valid reconstruction cutoff before issuance has no policy state and returns no result.
- Effective-time reconstruction does not represent what was known by an ingestion-time cutoff; bitemporal known-at queries remain deferred.
- The current supported transitions are `active` to `grace_period`, `grace_period` to `active`, `grace_period` to `lapsed`, and `active` to `surrendered`.
- Lapsed and surrendered are terminal in the current MVP. Each terminal status change is paired with its matching outcome at the same effective instant.
- A lapse follows a failed payment and lapse warning; a surrender follows a structured surrender inquiry. These are fictional scenario-coherence rules, not representations of insurer procedures.
- History replay uses `(effective_at, occurred_at, event_id)` as its total order and does not rely on caller-provided list order.
- Ingestion cannot precede occurrence. A retroactively effective event may have `effective_at` before `occurred_at`; correction and supersession semantics remain deferred.

## Initial generator

- The deterministic development corpus contains 100 policies by default.
- The fixed simulation start is `2024-01-01T00:00:00Z`; generated issue times and later events are derived from it rather than the wall clock.
- The default corpus uses equal fictional weights for active, recovered-from-grace, lapsed, and surrendered scenarios so every MVP path is exercised predictably.
- Premium amounts, scenario weights, payment methods, notice channels, service contacts, and outcome reasons are invented engineering inputs rather than calibrated real-world distributions.
- Billing intervals use simplified 30-day monthly, 90-day quarterly, 182-day semiannual, and 365-day annual schedules.
- An event is ingested one hour after it occurs in the initial generator. Complex late-arriving events and corrections remain deferred.
- The current nine-event contract is an intentional MVP subset; richer lifecycle concepts require separate contract changes before generation.
- The 100-policy corpus is generated during tests and development but is not committed as a dataset.
- The published sample selects the first two complete histories per scenario from the canonical seed-`20260817` 100-policy corpus. Its balanced eight-policy composition exists for inspection and coverage, not as an estimate of real-world prevalence.
- The Phase 1 synthetic-rate assessment retains the equal four-scenario allocation as a deterministic coverage fixture. It is not calibrated to an annual lapse, surrender, recovery, or retention rate.
- Current policy proportions cover one generated scenario path and have no policy-year exposure denominator. They must not be annualized or compared numerically with exposure-based public experience rates.
- Annual lapse or surrender calibration remains deferred until multi-period exposure, policy duration, and compatible product definitions exist. Scenario weights may be parameterized separately later without changing the canonical coverage corpus.

## Risk outcome

- The initial prediction horizon is 90 days.
- Phase 2.01 uses one observation per policy at the ingestion time of its first billing-due event. Recurring policy-month observations remain deferred.
- An observation is eligible only when the policy is active at `as_of` under dual visibility: both `effective_at` and `ingested_at` are on or before the cutoff.
- The version `1.0.0` label horizon is `(as_of, as_of + 90 elapsed days]`, with an exclusive start and inclusive end.
- Lapse and surrender remain distinct in audit provenance but combine into a binary adverse-termination label for the narrow baseline experiment.
- A label is derived separately from feature-visible data and cannot be used as a feature.
- A negative label requires an explicit evaluation watermark covering the full 90-day horizon. Incomplete follow-up or a horizon outcome ingested after the watermark is right-censored.
- The canonical Phase 2.01 sufficiency gate proceeds with limitations: 100 policies produce 50 positive and 50 negative labels because of engineered scenario coverage, not observed prevalence.
- Deferred lifecycle fields are not required for the narrow engineering baseline and must not be invented inside observation construction.
- Synthetic-data results demonstrate engineering method, not real-world predictive performance.

## Intervention boundary

- Risk score and action eligibility are separate outputs.
- Deterministic rules decide which fictional actions are allowed.
- Missing or conflicting evidence can require abstention or human review.
- No component sends communications or changes policy state autonomously.

## Open questions

- Which grace-period and notice assumptions should be configurable rather than fixed?
- Should a later outcome contract use competing-risk evaluation while preserving the binary baseline comparison?
- What recurring observation cadence becomes defensible after multi-period exposure exists?
