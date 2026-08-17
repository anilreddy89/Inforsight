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
- State reconstruction uses events whose occurrence time is on or before the requested as-of time.

## Risk outcome

- The initial prediction horizon is 90 days.
- Lapse and surrender are modeled as distinct outcomes, even if the baseline later combines them into a binary review label.
- A label is derived from events after the observation date and cannot be used as a feature.
- Synthetic-data results demonstrate engineering method, not real-world predictive performance.

## Intervention boundary

- Risk score and action eligibility are separate outputs.
- Deterministic rules decide which fictional actions are allowed.
- Missing or conflicting evidence can require abstention or human review.
- No component sends communications or changes policy state autonomously.

## Open questions

- Which grace-period and notice assumptions should be configurable rather than fixed?
- Should the baseline label combine lapse and surrender or report competing outcomes separately?
