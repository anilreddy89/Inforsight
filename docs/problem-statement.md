# Problem Statement

Life-insurance policies can lapse or surrender after a sequence of billing, payment, notice, service, and policy events. A useful conservation workflow must reconstruct what was known at a specific observation time, estimate near-term risk without future leakage, determine which actions are operationally permitted, and present reviewable evidence to a human decision-maker.

## Initial problem

Build a reproducible fictional policy-event simulator and determine whether active policies likely to lapse or surrender within 90 days can be identified using only information available on the observation date.

## Intended user

The initial user is a fictional conservation reviewer who needs a prioritized, evidence-backed review queue. Later users may include operations leaders, compliance reviewers, and model-development teams.

## Success criteria for the first milestone

- Event histories are reproducible from an explicit seed.
- Events are chronologically valid and follow documented state transitions.
- State can be reconstructed as of any supported observation date.
- Labels are computed strictly after the observation date.
- Features use only information available on or before the observation date.
- The generator produces at least 100 small, reviewable fictional histories.
- Limitations and fictional assumptions are explicit.

## Non-goals

- Production model accuracy, customer targeting, or financial-impact claims.
- Real policyholder or insurer data.
- Autonomous communication or transaction execution.
- Underwriting or new-business classification.
- Cloud deployment, Kafka, Kubernetes, RAG, or multi-agent orchestration in the first milestone.
