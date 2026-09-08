# RH-01D: Domain snapshot and semantic catalog 1.0.0

Status: accepted on 2026-09-08 through [issue #136](https://github.com/anilreddy89/Inforsight/issues/136) and [PR #137](https://github.com/anilreddy89/Inforsight/pull/137), merge `fde664ec`; implemented through [issue #139](https://github.com/anilreddy89/Inforsight/issues/139) and [PR #140](https://github.com/anilreddy89/Inforsight/pull/140), merge `f0be47e`.

## Boundary and artifacts

[ADR 0015](../adr/0015-canonical-dual-time-domain-snapshot.md) establishes a separate operational domain snapshot. The existing `reconstruct_policy_state` effective-only API remains unchanged.

Normative artifacts in `data-contracts/rh/v1/`:

- `domain-snapshot.schema.json`: serialized immutable snapshot 1.0.0.
- `semantic-catalog.json` and `semantic-catalog.schema.json`: exact catalog 1.0.0, including pinned historical feature dictionary and bundle preprocessing content.
- `acceptance-fixtures.json`: concrete fictional inputs and expected projections/errors for RH-01I.

RH-01I adds `simulator/src/inforsight_simulator/domain_snapshot.py` and `semantic_catalog.py`. Public API: `reconstruct_domain_snapshot(history, *, policy_id, as_of, source_profile, catalog) -> DomainSnapshot | None`. Use frozen dataclasses and tuples recursively; do not retain mutable references to input dictionaries. `None` means no visible issuance. Raise a typed `SnapshotContractError(code, event_id=None)` for invalid input; errors do not contain full input payloads. Snapshot construction does not score a model, select an action, or grant authority.

## Selection, validation, and replay

1. Require one explicit supported profile: `legacy-policy-events/1.0.0` or `v6-policy-events/6.0.0`. Do not auto-detect by payload shape or mix profiles. Older statistical v2–v5 profiles remain outside this first operational API.
2. Accept timezone-aware cutoff datetimes or ISO timestamps with an explicit offset, normalize to UTC, serialize with `Z`. Reject naive or invalid timestamps (`INVALID_TIME`). Source timestamps obey their source contract's UTC requirements. Reject nonfinite numbers and duplicate JSON object keys at ingestion.
3. For every supplied envelope, validate policy identity, nonempty event identity, matching schema version, and valid `effective_at` / `ingested_at`. Failure is `INVALID_ENVELOPE`. The guarantee of invisible-event independence assumes valid selection envelopes; malformed selection metadata cannot safely be classified as invisible.
4. Select only events with **both** timestamps `<= as_of`. Do not read unselected payloads for reconstruction or include them in provenance. Invisible valid envelopes with malformed payloads or unsupported event types do not change an earlier snapshot.
5. Validate selected payloads against the named profile. Reject repeated selected event IDs (`DUPLICATE_EVENT`), even identical duplicates. Unknown selected event types fail `UNSUPPORTED_EVENT`; invalid selected payloads fail `INVALID_PAYLOAD`. No silent repair.
6. Sort visible legacy events by `(effective_at, occurred_at, event_id)` after validating their `occurred_at`; sort v6 by `(effective_at, event_id)`. Ingestion gates visibility, not effective replay precedence. Preserve source event bytes conceptually: normalized replay values must not mutate evidence.
7. An empty visible set returns `None`. A nonempty set without issuance fails `MISSING_ISSUANCE`; multiple issuances fail `MULTIPLE_ISSUANCE`. Events effective before issuance fail `BEFORE_ISSUANCE`. All selected events must have the requested policy ID.
8. Legacy lifecycle replay starts from `initial_status=active`. A status change must match the current `previous_status` and use one of: active→grace_period, active→surrendered, grace_period→active, grace_period→lapsed, grace_period→surrendered. Reject other transitions and multiple status-changing events at the same effective instant (`INVALID_TRANSITION` / `AMBIGUOUS_STATUS`). Terminal status cannot reactivate in this bounded profile. Outcome events are evidence, not substitutes for legacy status-change facts.
9. v6 issuance has no lifecycle-status field. Status remains `unknown` unless a visible terminal outcome establishes `lapsed` or `surrendered`. Two visible terminal outcomes fail `AMBIGUOUS_STATUS`. A payment delay or grace-warning notice cannot establish grace or active status. This deliberately exposes missing source coverage in the current demo.
10. v6 accepts issued, payment.recorded, notice.sent, service.contact, event.corrected, outcome.lapsed, outcome.surrendered as defined by the existing v6 generator. A correction supports only `target_event_id` and `replacement_delay_days`; its target must be a visible earlier payment of the same policy. Apply corrections in replay order to the derived payment view, last correction wins. Missing/incompatible target fails `INVALID_CORRECTION`. Original payment and correction both remain in provenance. Do not reinterpret corrections as lifecycle amendments or edit history.

Full legacy payload validation may reuse the current JSON schemas. Do not call whole-history legacy lifecycle validation before visibility filtering. RH-01I defines strict v6 selected-payload validation from the frozen generator field contract, without widening the event taxonomy or changing the generator. Required issuance keys are billing_frequency, currency, premium_amount_cents and product_type. Payment keys and types follow `v6_corpus._scheduled_payments`; counts/flags must be nonnegative and flags 0/1, delay nullable and nonnegative, arrears a nonnegative integer. Service/notice categories follow the v6 feature dictionary. No oracle sidecars or outcome labels are input facts.

## Facts and missingness

Issuance supplies product (`product_variant` maps to `product_type` for legacy), currency, billing frequency, and premium minor units. Tenure is floor of elapsed UTC seconds / 86400, without clipping. Annual premium is integer premium cents multiplied by 12, 4, 2, or 1 for monthly, quarterly, semiannual, or annual billing. Monthly equivalent is annual cents / 12 and rounded HALF_EVEN only when displayed; no implicit monthly billing assumption.

For legacy grace entry, retain the status event's effective timestamp. An exit clears the current entry; re-entry starts a new period. In-grace days are floor of elapsed seconds / 86400. Confirmed non-grace status yields false/0/null for in_grace_period/days_in_grace/grace_entered_at; unknown status yields null/null/null. Initial active status is supported only by legacy explicit issuance evidence.

`days_past_due` is the latest visible v6 payment `arrears_days` fact, ordered as above, with its event ID; it is not advanced with wall time. It is null for no payment or legacy histories in this bounded implementation. Delay, grace duration and arrears are separate quantities. Corrections to delay do not alter arrears.

Coverage amount and cumulative paid premium are null for both profiles: neither supplies a supported coverage fact or complete paid-amount ledger for this snapshot contract. Safety fields are all required nulls in version 1.0.0: these source profiles carry no authoritative claim, hold, dispute, consent or DNC evidence. A future supported safety source requires a new version and provenance contract. Synthetic fixture flags must never be passed off as these source facts.

`field_evidence` lists IDs supporting issuance, current status, current grace entry, and latest arrears. Unknown facts have empty lists. Confirmed outside-grace state cites current status evidence. All cited IDs must occur in provenance. Values derived from issuance share its evidence; the cutoff is additional provenance for elapsed durations.

## Identity and shared consumers

Canonical JSON means UTF-8, sorted object keys, compact separators, ensure_ascii=True, allow_nan=False, no trailing newline; arrays retain declared order. Event digests hash the complete original selected event object under that serialization, including all source envelope fields. Catalog digest hashes the canonical catalog object. Snapshot ID is SHA-256 of the complete snapshot object excluding `snapshot_id`, including catalog digest, policy/profile/version/cutoff, facts, ordered provenance and field evidence. This is an identity/checksum, not an authenticity or tamper-resistance claim. Normalize output instants to `YYYY-MM-DDTHH:MM:SS.ffffffZ` (six fractional digits); raw source timestamps in event digests stay as supplied.

Only visible events enter the identity. Appending a valid invisible event or reordering input cannot alter the snapshot. Changing the cutoff or any visible event content changes identity, even if the displayed facts happen to match. Snapshot identity does not contain a model result; scoring context separately binds snapshot ID, model bundle ID/digest, and preprocessing profile ID.

Every migrated adapter receives a `DomainSnapshot` plus its matching visible-event tuple, not unrestricted full history or a feature map as domain truth. Validate identity on adapter entry; unknown versions/digests fail `INCOMPATIBLE_CONTRACT`. Timeline/dossier/narrative code cannot traverse future history. Joining domain facts to a score requires identical policy and cutoff; mismatch fails `CONTEXT_MISMATCH`. Workflow context must carry snapshot ID; changing it produces a new context, never reuses stale facts. Approval invalidation/enforcement remains RH-03.

## Catalog semantics

The catalog is the authority for status names, tier direction, target, money, actions, duration and preprocessing definitions. Its schema freezes the exact v1 instance; incompatible or modified values require a new catalog version and explicit migration. New versions must not overwrite this directory. Consumers load by explicit version and expected digest.

Risk increases from TIER_1_LOW to TIER_4_CRITICAL. Probability intervals are [0,.10), [.10,.25), [.25,.50), [.50,1]. NaN, infinity and probabilities outside [0,1] fail. Bundle display names map by exact strings to these IDs. The provisional Protobuf aliases map explicitly by semantic severity, including TIER_2_ELEVATED→TIER_3_HIGH; do not map by ordinal or accept bare numbers. Aliases are accepted only with the named legacy/provisional adapter profile. RH-09 will amend the wire documents. Authority tiers in ADR 0002 are not risk tiers.

The score is 90-day adverse termination risk (lapse OR surrender), with horizon (as_of, as_of+90 days]. Preserve historical labels in historical artifacts; new displays must not call it lapse-only probability. Historical bundle action hints are perception metadata, not canonical eligible actions or authority.

Action IDs, channels, costs, cooldowns, tenure bounds and grace requirement in the catalog are the current standard rules catalog baseline. Costs use USD cents; staff time uses integer seconds (0, 1800, 3600, 360, 0 for reminder, consultation, specialist, remediation, abstain). Conversion to legacy dollars/hours is cents/100 and seconds/3600. No elapsed-day conversion is used for staff time. The fallback abstain ID maps explicitly to the standard abstain ID; reject unknown IDs. These are synthetic reference assumptions. RH-04 can revise economics only under new versions.

The catalog embeds the complete v6 feature dictionary entries (raw type/unit, transforms, missingness and output handling) and exact bundle preprocessor, plus SHA-256 file pins. Model input flow is raw V6Features → coefficient transforms from dictionary 6.0.0 → frozen bundle preprocessing → model/calibration. Use explicit stage/profile types in RH-01I so raw and coefficient-transformed inputs cannot be confused. No inverse transform yields domain truth. Do not refit normalization or change vocabulary/ordered output columns. Domain snapshots remain useful independently of scoring. RH-06 owns later inference packaging; this contract owns identity and semantics.

## Consumer migration and ownership

| Current surface | RH-01I bounded migration | Later owner |
| --- | --- | --- |
| reconstruction.py | Keep effective-only API; new dual-time module with explicit source profiles | RH-01I |
| dashboard/services/cohort_loader.py | Build snapshot before context; remove guessed domain values; filter source envelope dual-time; show unknowns | RH-01I |
| dashboard/services/engine_bridge.py and dossier/queue | Pass matching snapshot/cutoff; catalog tier/display mappings; preserve nulls | RH-01I |
| rules/models.py and engine | Adapter rejects unsupported/unknown required facts before legacy bool defaults; returns unavailable eligibility, never a positive set | RH-02 owns complete action/channel evidence semantics |
| assistant/context.py and workflow context | Use visible evidence and shared identity; unavailable facts not narrated as facts | RH-08 grounding; RH-03 transition enforcement |
| optimization PolicyValuation | Annual premium from snapshot; CLV remains a separately named/versioned synthetic assumption; skip valuation when required facts absent | RH-04 economics |
| serving/models.py and app.py | Explicit preprocessing stage/profile and catalog tier mapping; reject mismatched domain/score contexts | RH-06 packaging |
| conservation JSON contracts | New snapshot schema is additive; retain old schemas and introduce explicit adapters for canonical IDs | RH-01I |
| proto/v1 and api/openapi | Record opposite tier direction; no wire mutation in this issue | RH-09 |

An unavailable legacy rule evaluation is an explicit adapter result with reason `insufficient_domain_evidence`, not an empty success, automatic abstain approval, or fabricated false flag. This conservative compatibility behavior is required in RH-01I so exposing null facts cannot create permission while RH-02 remains open. The current v6 demo will lose unsupported grace/status-dependent recommendations until adequate evidence is available; document that limitation rather than inventing source facts. New lifecycle/safety source events require separately governed contracts.

## Verification and rollout

RH-01D tests validate schemas, pinned catalog dependencies, exact money/time conversions, risk-boundary coverage and fixture envelope visibility expectations. They do not implement the reconstructor or prove runtime invariants. RH-01I must first add failing regression tests for every fixture and adapter invariance check, then implement the shared API and migrate consumers.

The concrete fixture file uses synthetic adapter-level envelopes; legacy IDs are readable fixture IDs rather than source-format envelopes. RH-01I's fixture loader must expand these IDs into deterministic contract-valid IDs before legacy schema validation without altering temporal/value expectations. Assert projections and error codes, plus identity relations stated by each fixture. Add adversarial negative schema tests and execute relevant component suites. Preserve historical bundle/dictionary bytes and all sealed evaluation artifacts.

Run full `make check` in the project virtual environment with `MPLBACKEND=Agg` for headless plotting. The historical function named `execute_final_evaluation` selects `role == "non_final_evaluation"`; this verification does not authorize final-holdout materialization or access. Keep verification read-only with respect to historical artifacts and record the actual output.

RH-01D merge `fde664ec` settled the design, and RH-01I merge `f0be47e` supplied the runtime regressions and bounded consumer migration. Parent RH-01 is complete. Downstream work proceeds only through its declared gates, and no Phase 4 resume or release claim follows before RH-13 records `PROCEED`.
