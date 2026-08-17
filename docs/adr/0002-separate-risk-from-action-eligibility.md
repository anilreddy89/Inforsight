# ADR 0002: Separate probabilistic risk from deterministic action eligibility

- Status: Accepted
- Date: 2026-08-16

## Context

A policy may have elevated lapse risk while a proposed action is unavailable, inappropriate, unsupported by evidence, or subject to mandatory review.

## Decision

The predictive layer produces a versioned, time-bounded risk estimate. A separate deterministic rules layer evaluates allowed actions. Assistive components may assemble evidence and draft a recommendation, but a human reviewer makes the final decision.

## Consequences

- Model performance can be evaluated independently from workflow policy.
- Rules remain testable, explainable, and versioned.
- Missing evidence can lead to abstention instead of a fabricated recommendation.
- No model or assistant receives authority to execute an intervention.
