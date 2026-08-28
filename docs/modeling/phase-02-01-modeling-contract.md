# Phase 2.01 Modeling and Observation Contract

## Status and decision

| Field | Value |
| --- | --- |
| Contract version | `1.0.0` |
| Label-policy version | `1.0.0` |
| Observation cadence | One observation at the ingestion time of the first `billing.premium_due` event |
| Label horizon | 90 elapsed days |
| Data-sufficiency decision | Proceed with limitations |
| Canonical evidence | `docs/experiments/phase-02-01-observation-sufficiency.json` |

The current fictional event contract supports a narrow, reproducible baseline engineering experiment. It does not support claims about real-world prevalence, predictive performance, actuarial validity, fairness, causality, or business value.

## Prediction question

For a fictional policy that is visible and active at `as_of`, does a structured lapse or surrender outcome become effective during the following 90 elapsed days, using only feature inputs that were both effective and ingested by `as_of`?

The resulting binary label is an adverse-termination engineering target. Lapse and surrender remain distinct in label provenance even though both map to label value `1`. A score derived later from this target cannot authorize an intervention.

## Unit of observation

One record represents one synthetic policy at one UTC `as_of` cutoff. Version `1.0.0` creates exactly one observation per policy at the ingestion timestamp of its first billing-due event.

The observation identifier is the prefix `obs_` plus the first 24 hexadecimal characters of SHA-256 over:

```text
observation_contract_version|policy_id|as_of
```

Records are ordered by `(as_of, policy_id)`. Duplicate identifiers fail construction. Version `1.0.0` does not create recurring policy-month rows, overlapping outcome episodes, or observations after recovery.

## Temporal visibility

Feature visibility is inclusive and requires both conditions:

```text
event.effective_at <= as_of
and
event.ingested_at <= as_of
```

An effective fact that has not been ingested is not visible. An ingested event whose effective time is still in the future is also not visible. All contract times use UTC with an explicit `Z` suffix.

This differs intentionally from `reconstruct_policy_state`, which is an effective-time lifecycle replay API. Observation construction validates the complete history, applies the dual-time filter, and reconstructs the narrow visible state from that filtered set.

## Eligibility

A record is eligible only when:

1. The complete policy history passes history validation.
2. A `policy.issued` event is visible under the dual-time rule.
3. The visible lifecycle status at `as_of` is `active`.

Policies not yet visible or in grace period, lapsed, or surrendered are ineligible. An ineligible record has `features: null`, label status `not_applicable`, and no numeric label.

Version `1.0.0` anchors the cutoff at first-billing ingestion. Under the canonical generator, all 100 policies are active at that instant. This is an engineered property of the simulator, not an eligibility rate estimate.

## Feature boundary

The observation contract exposes a small baseline feature surface:

| Feature | Definition at `as_of` |
| --- | --- |
| `current_status` | Visible lifecycle status; always `active` for eligible records |
| `product_variant` | Value from visible issuance |
| `billing_frequency` | Value from visible issuance |
| `premium_amount_cents` | Integer fictional premium from visible issuance |
| `currency` | Currency from visible issuance |
| `policy_age_days` | Whole elapsed days from effective issuance to `as_of` |
| `visible_event_count` | Count of all dual-time-visible events |
| `visible_billing_count` | Visible `billing.premium_due` count |
| `visible_failed_payment_count` | Visible `payment.failed` count |
| `visible_received_payment_count` | Visible `payment.received` count |
| `visible_notice_count` | Visible `notice.sent` count |
| `visible_service_contact_count` | Visible `service.contact_recorded` count |

Features are nested separately from identity, cutoff, label, audit provenance, and visible event identifiers. Policy IDs, event IDs, scenario identifiers, final status, outcomes, label fields, and label-source fields are prohibited from the feature surface.

This is the observation-contract feature surface, not the final Phase 2 feature dictionary. Transformations, encodings, missing-value policy, and feature selection remain later versioned work.

## Label policy

The horizon is:

```text
(as_of, as_of + 90 elapsed days]
```

The start is exclusive and the end is inclusive. A qualifying outcome is a validated `outcome.lapsed` or `outcome.surrendered` event whose effective timestamp is inside that interval and whose ingestion timestamp is at or before the explicit evaluation watermark.

Label states are:

| Status | Value | Meaning |
| --- | --- | --- |
| `observed_positive` | `1` | A lapse or surrender is effective in the horizon and ingested by the watermark |
| `observed_negative` | `0` | The watermark covers the full horizon and no qualifying outcome exists |
| `right_censored` | `null` | Follow-up ends early or a horizon outcome is not ingested by the watermark |
| `not_applicable` | `null` | The policy is not eligible at `as_of` |

Positive labels retain outcome type, source event ID, effective time, and ingestion time for audit. Those fields remain outside `features`.

The event contract already rejects conflicting or repeated terminal outcomes and requires each terminal outcome to pair with the corresponding status transition at the same effective time. Observation construction additionally rejects more than one qualifying outcome episode in a horizon.

R2-02 hardens this historical contract without changing its meaning: the serialized observation schema uses mutually exclusive label and eligibility variants, runtime domain construction enforces the same state matrix and temporal relations, and raw policy histories enter through schema-first `validate_policy_history` validation before cross-event semantics.

## Follow-up and censoring

Negative labels require an explicit `follow_up_through` watermark at or after the horizon end. A history's last event is not treated as proof that observation continued afterward.

An observation is right-censored when:

- `follow_up_through` is before the horizon end; or
- a qualifying outcome is effective in the horizon but is ingested after the watermark.

A positive observed before an early watermark remains positive because its outcome time is known. The canonical assessment chooses one shared watermark equal to the latest horizon end across all generated observations.

The shared watermark is an explicit experiment boundary. It is not emitted by the Phase 1 generator and must not be inferred from silence after a policy's last event.

## Data-sufficiency gate

The canonical seed-`20260817` 100-policy corpus produces:

| Measure | Count |
| --- | ---: |
| Policies | 100 |
| Observations | 100 |
| Eligible observations | 100 |
| Ineligible observations | 0 |
| Positive adverse-termination labels | 50 |
| Negative labels | 50 |
| Lapse outcomes | 25 |
| Surrender outcomes | 25 |
| Censored observations | 0 |

The decision is **proceed with limitations** because the current fields are sufficient to exercise leakage-safe construction, temporal splitting, feature versioning, and model-training reproducibility. No deferred Phase 1 fields are required for that narrow engineering purpose.

The limitations are material:

- The 50% positive fraction is fixed scenario coverage, not prevalence.
- The paths cover one simplified billing episode rather than recurring exposure.
- One observation per policy is not a production cadence.
- The corpus contains only 100 synthetic policies.
- Many plausible real-world variables are absent by design.
- Later metrics can demonstrate pipeline behavior only, not external validity.

Issue age, face amount, acquisition channel, reinstatement, maturity, loans, cash value, account changes, and prior conservation attempts remain deferred. They must not be invented in the observation builder. A later experiment that requires any of them must first add a separate versioned event-contract and generator change.

## Reproducibility

Regenerate the small machine-readable gate artifact:

```bash
python3 scripts/build_observations.py --write
```

Verify it without changing files:

```bash
python3 scripts/build_observations.py --check
```

The artifact records generator and schema versions, seed, policy count, simulation start, observation and label contract versions, cutoff range, follow-up watermark, counts, field inventory, decision, and limitations. Raw 100-policy observation records are generated in memory and are not committed.

## Clean-room and authority boundaries

- Every record is fictional and derived from original repository code.
- No customer, personal, insurer-confidential, or proprietary data is used.
- Synthetic model metrics must not be described as production accuracy or actuarial evidence.
- Risk estimation remains separate from deterministic action eligibility.
- No observation, label, future model score, or explanation can authorize customer contact or policy action.
- Human review and auditable evidence remain required for any future intervention workflow.

## Deferred work

- Dedicated adversarial leakage and simulator-shortcut testing beyond this contract's fixed feature surface.
- Policy-aware temporal train, validation, and test splits.
- Versioned transformations and a complete feature dictionary.
- Logistic-regression and boosted-model training.
- Probability calibration and operational threshold selection.
- Explanations, model card, experiment decision, and release marker.
