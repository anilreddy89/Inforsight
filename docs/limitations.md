# Limitation Register

## Purpose

This register tracks implementation findings that constrain what Inforsight can claim or safely do. It complements phase contracts, experiment artifacts, assumptions, and the backlog:

- Phase contracts and experiment artifacts contain the detailed evidence.
- `docs/assumptions.md` records stable project-wide constraints.
- This register records ownership, impact, resolution triggers, and closure evidence.
- `docs/backlog.md` schedules work when a limitation reaches its resolution trigger.

A limitation does not automatically block all subsequent work. Each entry must state what may continue, what is blocked, and the latest point at which resolution or an explicit stop decision is required.

## Status lifecycle

```text
Open -> Accepted temporarily -> Scheduled -> Resolved
                                   |
                                   +-> Superseded
```

| Status | Meaning |
| --- | --- |
| Open | Verified limitation without an approved temporary disposition or scheduled resolution. |
| Accepted temporarily | Work may continue within explicit boundaries until the recorded trigger. |
| Scheduled | A backlog item or issue owns the resolution work. |
| Resolved | Objective closure evidence satisfies the acceptance criteria. |
| Superseded | A later contract or decision replaces the limitation; the replacement is linked. |

## Severity

| Severity | Meaning |
| --- | --- |
| Blocking | Current work cannot continue safely or validly. |
| Claim-blocking | Engineering may continue, but specified evaluation, readiness, or performance claims are prohibited. |
| Material | The limitation affects design or interpretation and must remain visible. |
| Informational | Useful context without a current acceptance-gate impact. |

## Active limitations

### LIM-002-001 — Billing frequency is confounded with observation time

| Field | Value |
| --- | --- |
| Status | Accepted temporarily |
| Severity | Claim-blocking |
| Discovered in | Phase 2.03 policy-aware temporal splits |
| Owner | Unassigned; create a focused issue when the resolution trigger is reached |
| Evidence | `docs/experiments/phase-02-03-temporal-split-manifest.json`; pipeline-only baseline evidence in `docs/experiments/phase-02-05-logistic-baseline-manifest.json` |
| Detailed contract | `docs/modeling/phase-02-03-temporal-split-contract.md` |
| Resolution trigger | Before interpreting held-out metrics as temporal generalization or approving a risk-model release |

#### Finding

Observation contract `1.0.0` creates one observation at first-billing ingestion. The canonical policies are issued during one short initial period, so billing frequency largely determines observation date. The strict chronological split consequently contains monthly policies in train, quarterly policies in the embargo, semiannual policies in validation, and annual policies in test.

Billing frequency is also entangled with policy age at the observation cutoff. A validation or test result therefore cannot distinguish temporal generalization from behavior on feature categories absent from training.

#### Work that may continue

- Versioned feature construction and deterministic regeneration.
- Training-only preprocessing with explicit handling for unknown held-out categories.
- Seeded model training, artifact loading, and scoring-path reproducibility.
- Leakage, isolation, calibration-code, threshold-code, explanation-code, and reporting-mechanics tests.
- Synthetic metrics labeled strictly as pipeline demonstrations.

#### Work or claims blocked

- Claims that held-out results demonstrate temporal generalization.
- Claims of real-world predictive, actuarial, fairness, operational, or business performance.
- Model-release approval based on the current temporal split.
- Changing to a random or stratified split to conceal the temporal confounding.
- Using validation or test results to redesign the existing split after results are observed.

#### Proposed resolution

Introduce a separately versioned generator and observation design with:

- multiple policy-issuance cohorts spread across sufficient calendar duration;
- every supported billing-frequency category represented in train, validation, and test;
- enough observations and outcomes in each chronological partition;
- unchanged dual-time feature visibility and policy/outcome-episode isolation; and
- a preserved 90-day label-horizon embargo.

#### Closure evidence

- [ ] A separately reviewed issue and versioned generator or observation-contract change are merged.
- [ ] Every supported billing frequency appears in train, validation, and test.
- [ ] Train, validation, and test remain strictly chronological.
- [ ] Both 90-day horizon embargo assertions pass.
- [ ] Policy and outcome-episode overlap remain zero.
- [ ] The regenerated versioned split manifest passes deterministic verification.
- [ ] Each modeling partition has an adequate, documented sample and outcome count for the intended claim.
- [ ] The model decision note either authorizes the narrower claim with evidence or records a stop decision.

## Register maintenance

When implementation reveals a new limitation:

1. Give it the next stable identifier in the form `LIM-<phase>-<sequence>`.
2. Record concrete evidence rather than a general concern.
3. State its severity, affected work, allowed work, and prohibited claims.
4. Define the resolution trigger and objective closure evidence.
5. Link the phase contract or experiment where it was discovered.
6. Add a backlog item when the trigger is approaching; create an issue when work is scheduled.
7. Never mark it resolved solely because later work completed or produced favorable metrics.

Resolved and superseded entries remain in this file as an audit trail.
