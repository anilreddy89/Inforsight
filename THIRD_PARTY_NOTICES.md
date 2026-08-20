# Third-Party Notices

The simulator's Phase 2 baseline uses the runtime modeling dependency listed below. Contract tests use the development dependencies listed below.

As dependencies are introduced, record each material package, version, source, license, and required notice here. Automated dependency and SBOM reports will supplement—but not replace—this human-readable record.

| Component | Version | Source | License | Notes |
| --- | --- | --- | --- | --- |
| jsonschema | 4.26.0 | https://pypi.org/project/jsonschema/ | MIT | Test-only JSON Schema validation |
| referencing | 0.37.0 | https://pypi.org/project/referencing/ | MIT | Test-only local JSON Schema reference registry |
| rfc3339-validator | 0.1.4 | https://pypi.org/project/rfc3339-validator/ | MIT | Test-only RFC 3339 date-time format validation |
| scikit-learn | 1.7.2 | https://pypi.org/project/scikit-learn/ | BSD-3-Clause | Runtime logistic-regression estimator and metric primitives |
| NumPy | >=1.22 | https://pypi.org/project/numpy/ | BSD-3-Clause | Transitive numerical-array dependency of scikit-learn |
| SciPy | >=1.8 | https://pypi.org/project/scipy/ | BSD-3-Clause | Transitive numerical-optimization dependency of scikit-learn |
| joblib | >=1.2 | https://pypi.org/project/joblib/ | BSD-3-Clause | Transitive execution dependency of scikit-learn |
| threadpoolctl | >=3.1 | https://pypi.org/project/threadpoolctl/ | BSD-3-Clause | Transitive native thread-pool control dependency of scikit-learn |
