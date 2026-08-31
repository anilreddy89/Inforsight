# Phase 2R.10 v3 Evaluation Pipeline Implementation Contract

## Contract metadata

| Field | Value |
| --- | --- |
| Phase | R2-10 |
| Issue | [#59](https://github.com/anilreddy89/Inforsight/issues/59) |
| Evaluation split contract | `3.0.0` |
| Feature dictionary contract | `3.0.0` |
| Feature pipeline contract | `3.0.0` |
| Candidate selection contract | `3.0.0` |
| Scoring authorization contract | `3.0.0` |
| Governing substrate | `docs/modeling/phase-02r-08-v3-statistical-substrate-contract.md` |
| Acceptance protocol | `2.0.0`; execution remains R2-11 work |
| Final release holdout | `not_materialized` |
| Status | Implementation started; folds and feature registry are the first implemented slice |

This implementation contract closes only engineering details already assigned to R2-10. It does not amend any frozen statistical choice in ADR 0005, substrate contract `3.0.0`, or acceptance protocol `2.0.0`.

## Implemented first slice

The first R2-10 slice is separately namespaced in `inforsight_simulator.v3_evaluation` and freezes:

- the three rolling-origin acceptance folds and the selection fold;
- canonical caller-order normalization by `(as_of, policy_id, observation_id)`;
- fit/evaluation role isolation, policy isolation, episode isolation, strict cutoff chronology, and the 90-day outcome embargo;
- fail-closed support of at least 500 eligible uncensored observations, 50 positives, 50 negatives, and all four billing frequencies per governed membership;
- exclusion of censored observations from fitting and metric memberships;
- contract-version and public-feature validation before modeling; and
- a closed, exactly-once mapping of all `V3Features` fields to the five approved driver groups.

Aggregate class counts may be inspected only for the predeclared structural support gate. Acceptance-role rows may not enter preprocessing, diagnostics, candidate fitting, selection, prediction, or metrics until R2-11 authorizes its governed execution.

## Initial structural finding

The deterministic structural-support evidence confirms that all three frozen acceptance folds pass the implemented chronology, isolation, frequency, and minimum-count checks. The separately frozen selection interval fails closed with 467 eligible observations: 80 positive, 387 negative, zero right-censored, and all four billing frequencies represented. The only recorded selection failure is the frozen minimum of 500 eligible observations.

Machine-readable and human-readable evidence is published at:

```text
docs/experiments/phase-02r-10-v3-structural-support.json
docs/experiments/phase-02r-10-v3-structural-support.md
```

It regenerates through `scripts/check_v3_evaluation_support.py --write` and verifies byte-for-byte through `--check`.

This is a pre-model structural finding. R2-10 must not widen the selection interval, lower the minimum, reassign policies, replace the seed, or otherwise repair the result inside implementation code. Candidate fitting and selection remain blocked until the governing contract is reviewed and, if necessary, amended through its versioned change process.

## Remaining implementation slices

The next slices must add, in order:

1. the machine-readable feature dictionary with lineage and protected-concept validation;
2. fold-local fit-only preprocessing and frozen unknown-category behavior;
3. deterministic non-final diagnostics and complete dispositions;
4. the frozen logistic and boosted candidates plus exact AUC/Brier/logistic selection;
5. scoring authorization `3.0.0` bound to artifact, matrix, target, fit, preprocessing, model, role, fold, purpose, and contract digests; and
6. deterministic manifests, reports, write/check commands, repository integration, and historical-artifact checks.

No remaining slice may materialize a final holdout, produce an acceptance-role prediction or metric, run protocol `2.0.0`, change a frozen statistical setting, or overwrite v1/v2 historical evidence.
