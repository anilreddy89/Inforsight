# Phase 2R.10 v3 Arrears Remediation Contract 3.1.0

## Decision

Issue [#61](https://github.com/anilreddy89/Inforsight/issues/61) authorizes a separately versioned correction to the nonfunctional v3 arrears driver. Historical simulator contract `3.0.0`, the R2-09 manifest, and every earlier R2-10 artifact remain immutable.

The effective version set is:

| Boundary | Version |
| --- | --- |
| Simulator statistical contract | `3.1.0` |
| Evaluation and candidate-selection membership | `3.2.0` |
| Statistical acceptance protocol | `2.2.0` |
| Public observation and feature surface | `3.0.0`, unchanged |
| Random-stream registry | `1.0.0`, unchanged |
| Final release holdout | `not_materialized` |

## Frozen correction

For each failed payment, contract `3.1.0` retains the historical failure draw and obtains arrears from a distinct registered primitive:

```text
behavior_value(policy_id, payment, episode, arrears_days)
arrears_days = 1 + floor(60 * u)
```

Nonfailed payments retain `arrears_days = 0`. The existing stream-set identity is preserved; the simulator artifact identity changes because the contract version changes.

Introducing nonzero arrears increased a small number of generated-state total terminal hazards beyond the frozen strict `0.20` bound. Contract `3.1.0` therefore shifts both cause-specific log-odds intercepts by `-0.70`: lapse changes from `-3.35` to `-4.05`, and surrender from `-4.05` to `-4.75`. The shared shift preserves relative cause odds and is enforced only in the new namespace. Complete-corpus generation remains fail closed on any nonfinite or `>= 0.20` generated-state hazard.

## Evidence disposition

The initial `3.1.0` evaluation artifacts are retained as a historical failed attempt. Their exact digests and reasons are recorded in `docs/experiments/phase-02r-10-v3.1-pre-remediation-disposition.json`; they cannot authorize R2-11.

Only artifacts generated from simulator contract `3.1.0`, evaluation contract `3.2.0`, and protocol `2.2.0` may constitute R2-10 completion evidence. They may select a candidate from the governed selection role, but they must not create acceptance predictions or metrics, access oracle sidecars, or materialize the final release holdout.
