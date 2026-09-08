# ADR 0015 — Canonical dual-time domain snapshot

- Status: Accepted through [PR #137](https://github.com/anilreddy89/Inforsight/pull/137), merge `fde664ec`.
- Date: 2026-09-07
- Work: [RH-01D / #136](https://github.com/anilreddy89/Inforsight/issues/136)

## Context

The legacy reconstructor intentionally answers effective-time queries. Operational adapters now need facts known at the observation cutoff, but currently recover policy values from transformed model features and use inconsistent status, tier and unit conventions. v6 source events do not contain explicit active/grace lifecycle facts. Defaults conceal those gaps.

## Decision

Introduce a separate immutable dual-time snapshot and one versioned semantic catalog, following [the RH-01 contract](../hardening/rh-01-domain-snapshot-contract.md). Require both effective and ingestion timestamps to be at or before the cutoff. Preserve source values and provenance, represent unsupported facts as unknown, and keep the model feature pipeline separate and explicitly identified.

Preserve the legacy effective-only API and historical artifacts. Migrate local consumers through explicit versioned adapters. Keep provisional wire changes with RH-09 and full safety enforcement with RH-02; RH-01I must prevent unknown facts entering permissive legacy defaults during that transition.

## Alternatives

- Change the legacy API in place: rejected because existing effective-only callers and evidence would silently change meaning.
- Reconstruct domain values from model features: rejected because clipping, scaling and imputation destroy source information.
- Give each consumer its own replay: rejected because cutoff, unknown-value and catalog semantics would drift again.
- Add new lifecycle/safety data to the frozen v6 corpus: rejected because it changes historical evidence and expands this bounded repair.

## Consequences

The demo will explicitly lack some facts and recommendations until supported evidence exists. One shared identity and catalog make disagreement detectable but do not provide authentication, causal evidence or execution authority. RH-01I may now begin from updated `main`; the accepted design itself does not repair runtime behavior or unblock Phase 4.
