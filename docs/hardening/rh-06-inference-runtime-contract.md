# RH-06D: Inference runtime packaging and startup contract 1.0.0

## Status and ownership

This contract is the RH-06D design deliverable for issue #160. It governs the bounded Python inference package and HTTP serving image that RH-06I will implement. The machine-readable companion is `data-contracts/rh/inference-runtime/v1/inference-runtime-contract.json`.

| Field | Value |
| --- | --- |
| Contract ID | `inforsight.inference-runtime` |
| Contract version | `1.0.0` |
| Runtime distribution | `inforsight-inference-runtime` |
| Runtime import namespace | `inforsight_inference` |
| Runtime source root | `inference-runtime/src/inforsight_inference` |
| Minimum Python | 3.11 |
| Parent outcome | RH-06 |
| Design issue | [#160](https://github.com/anilreddy89/Inforsight/issues/160) |
| Implementation owner | RH-06I after RH-06D merges |

The contract extracts an installable inference boundary; it does not change the model, bundle bytes, preprocessing, calibration, score, tier, queue, explanation, or authority semantics. The accepted release bundle remains `docs/experiments/phase-02-10-model-bundle.json`, with byte SHA-256 `7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656`.

## Package boundary

RH-06I creates a PEP 517 distribution rooted at `inference-runtime/pyproject.toml`. The installed namespace is narrow and must not execute simulator package initialization.

| Runtime module | Ownership |
| --- | --- |
| `inforsight_inference.__init__` | Explicit runtime public exports and runtime version only |
| `inforsight_inference.bundle` | Immutable bundle schema types, parse/load operations, structural and semantic validation |
| `inforsight_inference.engine` | NumPy-only transform, logit, calibration, tier/queue, and additive explanation calculations |
| `inforsight_inference.errors` | Stable typed runtime and startup errors |
| `inforsight_inference.catalog` | Load and verify the packaged byte-identical RH-01 semantic catalog asset |
| `inforsight_inference/assets/semantic-catalog.json` | Build-copied bytes from `data-contracts/rh/v1/semantic-catalog.json`; never independently edited |

The runtime distribution may depend only on `numpy==2.5.2` beyond the Python standard library. Build tooling is build-time only. FastAPI, Uvicorn, Pydantic, and HTTPX are serving or test dependencies and must not be declared as core runtime dependencies.

The following distributions are prohibited from the installed runtime dependency graph: `scikit-learn`, `xgboost`, `scipy`, `pandas`, `matplotlib`, `streamlit`, and the `inforsight-simulator` distribution. The runtime import/start/score path must not load modules matching `sklearn`, `xgboost`, `scipy`, `pandas`, `matplotlib`, `streamlit`, or these `inforsight_simulator` families: modeling, boosted modeling, calibration fitting, explanations training, corpus generation, evaluation, diagnostics, final evaluation, counterfactual evaluation, or qualification.

Runtime code cannot expose fit, train, calibrator fitting, candidate selection, metric evaluation, corpus generation, artifact generation, or qualification entry points.

## Training compatibility boundary

Training and historical evidence code remains in `inforsight_simulator`. The existing `inforsight_simulator.bundle` module becomes a training-side compatibility facade:

1. Runtime types and `BundledInferenceEngine` are re-exported from `inforsight_inference` for existing imports.
2. Bundle construction, fitting, export, and historical verification remain training-side functions in the simulator distribution.
3. The runtime package never imports the compatibility facade or the simulator root.
4. Scoring-only consumers migrate directly to `inforsight_inference`.
5. Historical generation/evaluation tests may retain the compatibility facade when they intentionally exercise training-side behavior.

This direction prevents a circular dependency: the simulator may depend on or use the runtime distribution, but the runtime distribution cannot depend on the simulator.

## Semantic catalog packaging

The RH-01 catalog is package data, not a forked source of truth. RH-06I must copy `data-contracts/rh/v1/semantic-catalog.json` byte-for-byte into the built wheel and verify its SHA-256 against `d360ed670337912f6b0094d587b5a979c5b8de2ed0a528a184eac36b393f4005`.

The runtime accepts catalog version `1.0.0`, preprocessing profile `v6-coefficient-transform-then-bundle-zscore/1.0.0`, bundle ID `inforsight-v6-logistic-platt-20260817`, and bundle version `1.0.0`. A mismatch is a startup failure. Build and focused tests must compare the packaged catalog bytes with the canonical source bytes.

## Bundle selection and trusted identity

The following configuration is authoritative:

| Variable | Required behavior |
| --- | --- |
| `INFORSIGHT_MODEL_BUNDLE_PATH` | Optional for repository development; required/pinned in the canonical image. If present, it is the only candidate and cannot fall back. |
| `INFORSIGHT_EXPECTED_BUNDLE_SHA256` | Required for the canonical image and production-like startup; exact lowercase 64-character SHA-256. |
| `INFORSIGHT_EXPECTED_BUNDLE_ID` | Required for the canonical image and production-like startup. |
| `INFORSIGHT_EXPECTED_BUNDLE_VERSION` | Required for the canonical image and production-like startup. |
| `INFORSIGHT_REQUIRE_TRUSTED_BUNDLE` | `true` in the canonical image. Local library callers may provide expectations directly to the load API. |

When no bundle path is configured, repository-local development may use the documented release bundle path. This default is forbidden after an explicit path is supplied. Tests must remove ambient variables before exercising the development default.

Trusted expectations come from explicit caller arguments, deployment configuration, or immutable image configuration; they are not read from the candidate bundle itself. Startup validates in this order:

1. Resolve the sole configured/default path.
2. Require that it exists, is a regular readable file, and can be read once as bytes.
3. Calculate the SHA-256 of those exact bytes and compare it with the trusted expected digest.
4. Decode UTF-8 and parse strict JSON, rejecting duplicate keys and non-finite numbers.
5. Validate required structure, types, finite numeric values, ordered-column uniqueness, coefficient alignment, tier/queue bounds, and authority marker.
6. Compare bundle ID, bundle version, bundle schema/contract, preprocessing profile, and RH-01 catalog identity with supported trusted values.
7. Construct the inference engine.
8. Mark readiness true and expose only the already verified identities.

The implementation must not reread a different file between digest verification and parsing.

## Stable startup failures

| Code | Meaning |
| --- | --- |
| `BUNDLE_PATH_MISSING` | An explicit path was empty or the selected path does not exist |
| `BUNDLE_NOT_REGULAR_FILE` | The selected path is not a regular file |
| `BUNDLE_UNREADABLE` | Exact bytes cannot be read |
| `TRUST_CONFIGURATION_MISSING` | Trusted identity is required but digest, ID, or version is absent/invalid |
| `BUNDLE_DIGEST_MISMATCH` | Exact bytes do not match the trusted SHA-256 |
| `BUNDLE_ENCODING_INVALID` | Bytes are not valid UTF-8 |
| `BUNDLE_JSON_INVALID` | JSON is malformed, contains duplicate keys, or contains non-finite values |
| `BUNDLE_SCHEMA_INVALID` | Required structure, types, dimensions, or numeric constraints fail |
| `BUNDLE_ID_MISMATCH` | Parsed bundle ID differs from the trusted expectation |
| `BUNDLE_VERSION_UNSUPPORTED` | Bundle or bundle-contract version is unsupported or differs from the trusted expectation |
| `PREPROCESSING_IDENTITY_MISMATCH` | Preprocessing profile, columns, or dictionary identity is incompatible |
| `CATALOG_IDENTITY_MISMATCH` | Packaged catalog bytes/version or tier mapping is incompatible |
| `ENGINE_INITIALIZATION_FAILED` | Validated inputs cannot construct the bounded engine |

Errors must carry a stable code and safe summary. They must not include feature payloads, environment secrets, or complete bundle contents. Startup failure leaves readiness false and must terminate canonical ASGI application startup rather than serve a healthy fallback.

## Serving contract

The serving layer is an adapter over `inforsight_inference`; it is not part of the core distribution.

| Property | Contract 1.0.0 |
| --- | --- |
| ASGI target | `serving.app:app` |
| HTTP bind | `0.0.0.0:8000` |
| Liveness/readiness route | `GET /health` |
| Model identity route | `GET /v1/model/info` |
| Single score route | `POST /v1/score` |
| Batch score route | `POST /v1/score/batch` |
| Monitoring route | `GET /v1/diagnostics`, retained but governed by RH-07 for evidence claims |
| Implemented protocols | HTTP/REST only |
| Action authority | Every score remains `authorized_to_act: false` |

For the bounded single-process application, `/health` is both liveness and readiness. It returns HTTP 200 only after trusted startup verification and engine construction; otherwise the application fails startup or returns 503 before readiness. A healthy response proves only that the declared runtime loaded the declared trusted bundle and can accept requests. It does not prove model quality, monitoring health, factual truth, authority, external validity, or production readiness.

The health response must expose status, runtime contract/version, verified bundle digest, bundle ID, bundle version, and engine readiness. Score validation errors remain request failures and cannot alter the process-wide trusted model identity.

## Canonical container and scaffold dispositions

`serving/Dockerfile` becomes the single canonical RH-06 HTTP image. It must build/install the runtime wheel, install serving-only dependencies, copy the exact release bundle and verified catalog asset, pin the trusted identity variables, run as a non-root user, expose only port 8000, target `serving.app:app`, and probe `GET /health`.

`infra/docker/Dockerfile.inference` remains a P4-01 historical scaffold and must be marked non-runnable, or become a documented pointer to the canonical HTTP Dockerfile without carrying a second configuration. It must not claim gRPC availability.

The `inference-runtime` block in `infra/docker-compose.yml` remains a non-runnable Phase 4 topology sketch until Phase 4 is resumed and its dependencies exist. Active comments/documentation must say so. It cannot be used as RH-06 verification evidence.

`infra/docker/Dockerfile.control-plane` remains non-runnable until a real JAR is built in authorized Phase 4 work. Kafka, PostgreSQL, Java, and gRPC are outside RH-06.

## Consumer migration matrix

| Consumer | RH-06I disposition |
| --- | --- |
| `serving/app.py` and gateway tests | Import bundle, engine, result, and errors directly from `inforsight_inference` |
| Serving monitoring baseline/tests | Import runtime bundle types directly; RH-07 still owns monitoring-state correctness |
| Dashboard engine bridge/cohort loader | Import scoring-only types and engine from `inforsight_inference` |
| OPE script and qualification runtime callers | Import scoring-only types and engine from `inforsight_inference`; do not change evidence |
| Final-evaluation and model-bundle tests | Use the simulator training compatibility facade where export/evaluation behavior is intentional |
| `scripts/run_model_bundle.py` | Remain training-side and use explicit simulator export/build APIs |
| `inforsight_simulator.__init__` | Stop being required for inference; historical root exports remain a simulator compatibility concern |
| P4 protobuf/Java/gRPC consumers | No runtime implementation in RH-06; RH-09 owns final contracts |

## Predeclared RH-06I verification

The immutable fixture catalog is `data-contracts/rh/inference-runtime/v1/acceptance-fixtures.json`. RH-06I must implement every case before claiming completion.

1. Build wheel and sdist, inspect file contents and `Requires-Dist`, and install the wheel in a new temporary virtual environment.
2. Install only the runtime wheel and its declared dependencies. Confirm `scikit-learn`, `xgboost`, and the simulator distribution are absent.
3. Run direct import/load/single/batch scoring with an import blocker and inspect `sys.modules` for prohibited names.
4. Compare representative scores, category handling, tier thresholds, queue flags, and additive explanation fields with the frozen compatibility path under the accepted tolerance.
5. Exercise each stable startup failure using copied fictional/mutated fixtures, never by changing the release bundle.
6. Start the ASGI application with explicit trusted identity and test health, model info, single score, and batch score.
7. Build the canonical image from a clean context without relying on an already populated cache; inspect the effective non-root user, files, ports, environment, command, and health check.
8. Run the container and exercise the same HTTP routes.
9. Run affected serving, dashboard, OPE, qualification, final-evaluation, and bundle tests, then full headless `make check`.
10. Verify the release bundle, semantic catalog source, and historical evaluation/qualification artifacts remain byte-identical.

The clean-environment gate fails if success depends on an undeclared globally installed package, repository `PYTHONPATH`, editable simulator install, copied simulator tree, or build cache.

## Claims and boundaries

After RH-06I passes, the allowed claim is: the bounded Python inference runtime can be independently installed, verify and score the accepted frozen bundle without importing or installing the project training/evaluation stack, and run through the canonical verified HTTP image.

This contract does not establish production readiness, model external validity, action authority, evidence-bearing monitoring, gRPC or Java availability, full Compose deployment, distributed security, sustained load, network latency, autoscaling, or customer-data readiness.

RH-06D changes no runtime code and authorizes no final-holdout access, model fitting, artifact regeneration, Phase 4 implementation, or historical evidence rewrite.
