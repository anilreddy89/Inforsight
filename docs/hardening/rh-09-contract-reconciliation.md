# RH-09D: P4-01 contract reconciliation matrix 1.0.0

This matrix governs issue [#169](https://github.com/anilreddy89/Inforsight/issues/169). It amends the provisional P4-01 architecture documents without implementing distributed services.

Grounding and narrative fields inherit RH-08's input/text consistency boundary; wire contracts must not describe a grounding hash as proof that source input is true.

| Concern | Provisional P4-01 state | RH-09D decision |
| --- | --- | --- |
| Authority | Proto3 `bool` could collapse absent and false | Use `optional bool authorized_to_act`; required consumers reject absent and any true value. Inference remains perception-only. |
| Risk tiers | Wire comments used reversed/non-canonical names | Canonical IDs are `TIER_1_LOW`, `TIER_2_ELEVATED`, `TIER_3_HIGH`, `TIER_4_CRITICAL`; higher ordinal means higher risk, matching RH-01. |
| Authentication | Topology implied trust | Authentication, trusted actor establishment, authorization, and network enforcement are separate contracts. Static topology proves none of them. |
| Reviewer identity | Request-level identity was underspecified | Trusted actor context is established outside the request; request carries reviewer evidence only when a decision requires it. |
| Idempotency | Not consistently required | Mutating decision/override operations require a nonempty idempotency key and expected case version. |
| Concurrency | Case version absent or optional | Mutations require `expected_case_version`; conflicts fail without partial state change. |
| Override | Conditional rules were prose-only | Override requires reason, reviewed context identity, trusted reviewer evidence, and explicit current-eligibility revalidation. |
| Identity binding | Model and domain identities incomplete | Bind snapshot/cutoff, score/model/bundle/preprocessing, safety/economics, grounding, and audit identities where each applies. |
| Errors | Generic HTTP/RPC failures | Use stable machine-readable code, safe summary, and retryability; never echo sensitive payloads. |
| Latency | P99 targets appeared as capability claims | Keep latency as an unmeasured target until a deployed path produces evidence. |
| Deployment | Compose/service names implied readiness | Mark topology and scaffolds as non-runnable architecture history until implemented and qualified. |

## Canonical tier mapping

| Canonical ID | Probability interval | Meaning |
| --- | --- | --- |
| `TIER_1_LOW` | `[0, 0.10)` | Lowest risk |
| `TIER_2_ELEVATED` | `[0.10, 0.25)` | Elevated risk |
| `TIER_3_HIGH` | `[0.25, 0.50)` | High risk |
| `TIER_4_CRITICAL` | `[0.50, 1]` | Critical risk |

No ordinal-only or bare-number alias is accepted. Any legacy alias requires an explicitly named adapter profile and must normalize to a canonical ID before crossing the wire.

## Version and compatibility rules

The amended documents remain version `1.0.0` only for additive presence/description corrections that do not change an implemented runtime. Any incompatible field rename, enum meaning change, required-field addition to an already deployed operation, or semantic change requires a new wire-contract version and migration plan. RH-09I owns compilation, linting, compatibility fixtures, and bounded reference adapters.

RH-09D does not authorize Kafka, Java, PostgreSQL, cloud deployment, external authentication, or P4-02/P4-03 implementation. RH-13 remains the Phase 4 resume gate.

## Stable error categories

`UNAUTHENTICATED`, `AUTHORIZATION_STATE_MISSING`, `AUTHORITY_VIOLATION`, `INVALID_TIER`, `IDENTITY_MISMATCH`, `STALE_CASE_VERSION`, `IDEMPOTENCY_KEY_MISSING`, `OVERRIDE_EVIDENCE_MISSING`, `CONTRACT_VERSION_UNSUPPORTED`, `INVALID_REQUEST`, and `INTERNAL_ERROR` are the initial cross-wire categories. Responses must include only safe summaries and a correlation/request identifier where available.
