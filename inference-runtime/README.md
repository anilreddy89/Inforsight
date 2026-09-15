# Inforsight inference runtime

`inforsight-inference-runtime` is the bounded, inference-only distribution for
the accepted frozen Inforsight risk model. Its core dependency is
`numpy==2.5.2`; it does not install or import the simulator or training stack.

The public API verifies a caller- or deployment-trusted bundle digest, ID, and
version before strict parsing, catalog compatibility checks, engine creation,
or readiness:

```python
from inforsight_inference import load_verified_runtime

runtime = load_verified_runtime(
    "model-bundle.json",
    expected_sha256="<trusted lowercase SHA-256>",
    expected_bundle_id="inforsight-v6-logistic-platt-20260817",
    expected_bundle_version="1.0.0",
)
result = runtime.engine.score_record(raw_v6_features)
```

This package performs perception-layer scoring only. It exposes no training,
fitting, evaluation, workflow, or action-authority API.
