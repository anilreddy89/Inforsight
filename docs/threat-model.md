# Initial Threat Model

## Assets

- Repository integrity and provenance.
- Synthetic-data guarantees.
- Secrets and cloud credentials introduced in later phases.
- Point-in-time correctness of evidence and model features.
- Human-review and audit boundaries.

## Early threats and controls

| Threat | Initial control |
| --- | --- |
| Real or proprietary data enters the repository | Clean-room policy, contributor review, forbidden-content check |
| Secret committed accidentally | `.gitignore`, CI pattern scan, hosting-platform secret scanning |
| Future information leaks into a feature | Explicit observation timestamps and dedicated leakage tests |
| Generated record resembles a real identity | Synthetic identifiers and no external joins |
| Model output is treated as an action | Risk/action ADR and typed separation in later contracts |
| Dependency introduces known risk | Minimal dependencies, review, SBOM, and vulnerability scanning before release |
| Agent bypasses rules or human approval | Deferred implementation with hard tool and authorization boundaries |

This document evolves as concrete services and data flows are introduced.
