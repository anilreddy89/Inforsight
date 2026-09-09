# RH-02 safety evidence contract 1.0.0

Status: implemented through [issue #142](https://github.com/anilreddy89/Inforsight/issues/142) and [PR #143](https://github.com/anilreddy89/Inforsight/pull/143), merged as `3eb74b5` on 2026-09-08. All PR CI checks passed.

## Boundary

`fictional-safety-events/1.0.0` is an additive, synthetic-only source profile. It does not mutate the RH-01 snapshot 1.0.0 schema or any historical corpus. `SafetyEvidence` binds replayed facts to one policy, cutoff, and canonical snapshot ID. Consumers reject a mismatched binding.

Events use the envelope in `data-contracts/rh/v1/safety-event.schema.json`. Visibility requires both `effective_at <= as_of` and `ingested_at <= as_of`. Replay order is `(effective_at, event_id)`. Duplicate IDs, invalid envelopes or payloads, unsupported types, invalid corrections, and contradictory values at the same effective instant fail closed with payload-safe errors.

`safety.facts_recorded` contains one or more Boolean fields. Omission means unknown. `safety.facts_corrected` names an earlier visible record and supplies Boolean replacements only for fields present on that record.

Canonical fields are `has_active_claim`, `has_legal_hold`, `has_registered_dispute`, `sms_opt_out`, `email_opt_out`, `phone_opt_out`, and `dnc_registered`. Each value is confirmed true, confirmed false, or unknown, and each known value cites its governing event ID.

## Action requirement matrix

| Action | Global confirmed-clear evidence | Channel confirmed-clear evidence |
| --- | --- | --- |
| `courtesy_reminder` | active claim, legal hold, registered dispute | SMS opt-out |
| `grace_period_consultation` | active claim, legal hold, registered dispute | phone opt-out, DNC registry |
| `specialist_phone_outreach` | active claim, legal hold, registered dispute | phone opt-out, DNC registry |
| `payment_method_remediation` | active claim, legal hold, registered dispute | SMS opt-out |
| `abstain` | none | none |

Unknown global evidence makes the evaluation unavailable. Unknown channel evidence disqualifies actions on that channel. Confirmed true global blocks freeze contact actions; confirmed true channel facts disqualify that channel. `abstain` remains a non-contact optimization outcome, but an unavailable evidence evaluation exposes no eligible or approvable action.

Eligibility serialization carries `snapshot_id`, `safety_evidence_id`, and `requirements_version=safety-action-requirements/1.0.0`. The workflow decision-context digest therefore binds those identities. RH-03 owns revalidation and authenticated approval at the common execution transition.

## Compatibility and claims

Direct `PolicyContext` fields are tri-state and default to unknown. Mapping omission stays unknown. Historical tests must provide explicit fictional clear evidence through their builders. Model bundles, preprocessing, generators, sealed evaluation artifacts, and the RH-01 snapshot schema remain unchanged.

This contract proves local deterministic evidence handling only. It does not prove source authenticity, legal sufficiency, authenticated authority, production readiness, or permission to resume Phase 4.
