# ADR 0001: Use a clean-room, synthetic-data-only development model

- Status: Accepted
- Date: 2026-08-16

## Context

Inforsight must be independently publishable and must not imply access to an insurer's private data, rules, workflows, or systems.

## Decision

Use fictional data, fictional procedures, public references, and original implementation only. Every generated dataset will carry provenance, generator version, seed, and an explicit synthetic-data notice. Ambiguous inputs are excluded until their provenance is resolved.

## Consequences

- The repository can be reviewed publicly without exposing customer or employer material.
- Synthetic results cannot support production accuracy or business-impact claims.
- Domain behavior must be documented as project assumptions rather than presented as universal industry fact.
