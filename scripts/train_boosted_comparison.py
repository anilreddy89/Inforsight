#!/usr/bin/env python3
"""Build or verify the sealed-test Phase 2.06 boosted comparison artifacts."""

from __future__ import annotations

import argparse
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_SRC = REPOSITORY_ROOT / "simulator" / "src"
sys.path.insert(0, str(SIMULATOR_SRC))

from inforsight_simulator import (  # noqa: E402
    BOOSTED_MODEL_VERSION,
    BOOSTED_TRAINING_CONFIGURATION_VERSION,
    CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
    FEATURE_DICTIONARY_VERSION,
    FEATURE_PIPELINE_VERSION,
    FROZEN_BOOSTED_SPECIFICATION,
    LABEL_HORIZON_DAYS,
    LOGISTIC_BASELINE_VERSION,
    XGBOOST_PINNED_VERSION,
    assign_temporal_splits,
    build_feature_pipeline,
    authorize_feature_pipeline,
    build_first_billing_observations,
    compare_models,
    first_billing_observation_time,
    fit_boosted_model,
    fit_logistic_baseline,
    fitted_boosted_bytes,
    fitted_baseline_bytes,
    generate_legacy_policy_histories,
    legacy_generation_provenance,
    matrix_digest,
)


MANIFEST_ID = "inforsight-phase-02-06-boosted-comparison"
MANIFEST_VERSION = "1.0.0"
SEED = 20260817
POLICY_COUNT = 100
ARTIFACT_DECIMAL_PLACES = 10
EXPERIMENTS_DIR = REPOSITORY_ROOT / "docs" / "experiments"
MANIFEST_PATH = EXPERIMENTS_DIR / "phase-02-06-boosted-comparison-manifest.json"
REPORT_PATH = EXPERIMENTS_DIR / "phase-02-06-boosted-comparison-report.md"
FEATURE_MANIFEST_PATH = EXPERIMENTS_DIR / "phase-02-04-feature-pipeline-manifest.json"
LOGISTIC_MANIFEST_PATH = EXPERIMENTS_DIR / "phase-02-05-logistic-baseline-manifest.json"
LOGISTIC_REPORT_PATH = EXPERIMENTS_DIR / "phase-02-05-logistic-baseline-report.md"


def _canonical_json(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _canonicalize(value):
    if isinstance(value, float):
        rounded = round(value, ARTIFACT_DECIMAL_PLACES)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _canonicalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def build_comparison() -> dict:
    histories = generate_legacy_policy_histories(SEED, POLICY_COUNT)
    cutoffs = [first_billing_observation_time(history) for history in histories]
    watermark = max(value + timedelta(days=LABEL_HORIZON_DAYS) for value in cutoffs)
    records = build_first_billing_observations(histories, follow_up_through=watermark)
    split = assign_temporal_splits(records, CANONICAL_TEMPORAL_SPLIT_SPECIFICATION)
    pipeline = build_feature_pipeline(split)
    authorizations = authorize_feature_pipeline(pipeline)
    logistic = fit_logistic_baseline(pipeline.train)
    boosted = fit_boosted_model(pipeline.train)
    train = compare_models(logistic, boosted, pipeline.train, authorizations.train)
    validation = compare_models(
        logistic, boosted, pipeline.validation, authorizations.validation
    )
    boosted_bytes = fitted_boosted_bytes(boosted)
    logistic_bytes = fitted_baseline_bytes(logistic)
    manifest = {
        "manifest_id": MANIFEST_ID,
        "manifest_version": MANIFEST_VERSION,
        "decision": "pipeline_engineering_only",
        "engineering_disposition": "comparison_complete_no_production_superiority_claim",
        "test_partition_status": "sealed_not_scored",
        "contracts": {
            "boosted_model_version": BOOSTED_MODEL_VERSION,
            "boosted_training_configuration_version": BOOSTED_TRAINING_CONFIGURATION_VERSION,
            "logistic_baseline_version": LOGISTIC_BASELINE_VERSION,
            "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
            "feature_dictionary_version": FEATURE_DICTIONARY_VERSION,
        },
        "generation": legacy_generation_provenance(SEED, POLICY_COUNT),
        "source": {
            "feature_pipeline_manifest_sha256": sha256(FEATURE_MANIFEST_PATH.read_bytes()).hexdigest(),
            "logistic_manifest_sha256": sha256(LOGISTIC_MANIFEST_PATH.read_bytes()).hexdigest(),
            "logistic_report_sha256": sha256(LOGISTIC_REPORT_PATH.read_bytes()).hexdigest(),
            "input_matrices": {
                "train": {"observation_ids": list(pipeline.train.observation_ids), "matrix_sha256": matrix_digest(pipeline.train)},
                "validation": {"observation_ids": list(pipeline.validation.observation_ids), "matrix_sha256": matrix_digest(pipeline.validation)},
            },
        },
        "candidate_fit": {
            **boosted.to_dict(),
            "fitted_state_sha256": sha256(boosted_bytes).hexdigest(),
            "training_complete": True,
        },
        "baseline_fit": {
            "fitted_state_sha256": sha256(logistic_bytes).hexdigest(),
            "unchanged_phase_02_05_artifacts": True,
        },
        "comparison": {"train": train, "validation": validation},
        "limitations": [
            "LIM-002-001 remains claim-blocking and unresolved.",
            "Only 26 monthly observations are available for training; metrics cannot establish model superiority.",
            "Validation is semiannual-only and billing frequency is confounded with observation time.",
            "The canonical test partition remains sealed and was not scored.",
            "No tuning, early stopping, calibration, threshold selection, feature changes, or preprocessing refit occurred.",
            "Results demonstrate pipeline engineering and are not evidence of temporal generalization or real-world performance.",
        ],
    }
    return _canonicalize(manifest)


def report_bytes(manifest: dict) -> bytes:
    def row(partition: str, model: str, label: str) -> str:
        metrics = manifest["comparison"][partition][model]["metrics"]
        return (
            f"| {partition.title()} | {label} | {metrics['record_count']} | "
            f"{metrics['class_distribution']['positive']} | {metrics['log_loss']:.6f} | "
            f"{metrics['roc_auc']:.6f} | {metrics['brier_score']:.6f} | "
            f"{metrics['average_predicted_probability']:.6f} | {metrics['observed_positive_fraction']:.6f} |"
        )

    rows = "\n".join(
        row(partition, model, label)
        for partition in ("train", "validation")
        for model, label in (("logistic_regression", "Logistic regression"), ("xgboost", "XGBoost"))
    )
    spec = manifest["candidate_fit"]["specification"]
    text = f"""# Phase 2.06 Boosted-Model Comparison Report

## Decision

The frozen XGBoost candidate and Phase 2.05 logistic benchmark were compared reproducibly on identical train and validation observations. This is a `pipeline_engineering_only` result, not a declaration of production superiority. `LIM-002-001` remains unresolved, and the canonical test partition stayed `sealed_not_scored`.

## Frozen candidate

- Library: XGBoost `{manifest['candidate_fit']['xgboost_version']}`
- Estimator: `XGBClassifier`
- Trees, learning rate, maximum depth: `{spec['n_estimators']}`, `{spec['learning_rate']}`, `{spec['max_depth']}`
- Minimum child weight and L2 penalty: `{spec['min_child_weight']}`, `{spec['reg_lambda']}`
- Tree method and workers: `{spec['tree_method']}`, `{spec['n_jobs']}`
- Seed: `{spec['random_seed']}`
- Row and column sampling: `1.0` (no stochastic subsampling)
- Early stopping: disabled
- Fit partition: train only

## Predeclared comparison

| Partition | Model | Records | Positive | Log loss | ROC AUC | Brier score | Mean prediction | Observed fraction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{rows}

These values were not used to replace or tune the candidate, change features or preprocessing, calibrate probabilities, or select a threshold.

## Engineering disposition

The implementation demonstrates deterministic train-only fitting, native JSON model reconstruction, identical comparison membership and metrics, stable prediction digests, and enforcement of the canonical test seal. With only 26 monthly training observations and a semiannual-only validation partition, metric differences cannot establish that either model is generally superior.

## Limitations

- Billing frequency is confounded with observation time under `LIM-002-001`.
- The balanced fictional outcome mix is not a prevalence estimate.
- No test result, calibration assessment, operational threshold, fairness conclusion, or release claim is provided.
- XGBoost model behavior in this engineered corpus is not authority for customer action.

## Reproduction

```bash
python3 scripts/train_boosted_comparison.py --check
```
"""
    return text.encode("utf-8")


def artifact_bytes() -> tuple[bytes, bytes]:
    manifest = build_comparison()
    return _canonical_json(manifest), report_bytes(manifest)


def write_artifacts() -> None:
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest, report = artifact_bytes()
    MANIFEST_PATH.write_bytes(manifest)
    REPORT_PATH.write_bytes(report)
    print(f"wrote {MANIFEST_PATH.relative_to(REPOSITORY_ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(REPOSITORY_ROOT)}")


def check_artifacts() -> bool:
    expected = ((MANIFEST_PATH, artifact_bytes()[0]), (REPORT_PATH, artifact_bytes()[1]))
    valid = True
    for path, content in expected:
        if not path.is_file():
            print(f"missing Phase 2.06 artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
        elif path.read_bytes() != content:
            print(f"stale Phase 2.06 artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
    if valid:
        print("Phase 2.06 boosted comparison artifacts are reproducible; test remains sealed.")
    return valid


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify Phase 2.06 comparison artifacts.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        write_artifacts()
        return 0
    return 0 if check_artifacts() else 1


if __name__ == "__main__":
    raise SystemExit(main())
