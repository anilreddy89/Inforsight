#!/usr/bin/env python3
"""Build or verify the sealed-test Phase 2.05 logistic baseline artifacts."""

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
    CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
    FEATURE_DICTIONARY_VERSION,
    FEATURE_PIPELINE_VERSION,
    FROZEN_LOGISTIC_SPECIFICATION,
    LABEL_HORIZON_DAYS,
    LOGISTIC_BASELINE_VERSION,
    TRAINING_CONFIGURATION_VERSION,
    assign_temporal_splits,
    build_feature_pipeline,
    build_first_billing_observations,
    coefficient_summary,
    evaluate_logistic_baseline,
    first_billing_observation_time,
    fit_logistic_baseline,
    fitted_baseline_bytes,
    generate_legacy_policy_histories,
    legacy_generation_provenance,
    matrix_digest,
)


MANIFEST_ID = "inforsight-phase-02-05-logistic-baseline"
MANIFEST_VERSION = "1.0.0"
SEED = 20260817
POLICY_COUNT = 100
ARTIFACT_DECIMAL_PLACES = 10
EXPERIMENTS_DIR = REPOSITORY_ROOT / "docs" / "experiments"
MANIFEST_PATH = EXPERIMENTS_DIR / "phase-02-05-logistic-baseline-manifest.json"
REPORT_PATH = EXPERIMENTS_DIR / "phase-02-05-logistic-baseline-report.md"
FEATURE_MANIFEST_PATH = EXPERIMENTS_DIR / "phase-02-04-feature-pipeline-manifest.json"


def _canonical_json(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _canonicalize_artifact_numbers(value):
    if isinstance(value, float):
        rounded = round(value, ARTIFACT_DECIMAL_PLACES)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _canonicalize_artifact_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize_artifact_numbers(item) for item in value]
    if isinstance(value, tuple):
        return [_canonicalize_artifact_numbers(item) for item in value]
    return value


def build_baseline() -> tuple[dict, bytes]:
    histories = generate_legacy_policy_histories(SEED, POLICY_COUNT)
    cutoffs = [first_billing_observation_time(history) for history in histories]
    watermark = max(cutoff + timedelta(days=LABEL_HORIZON_DAYS) for cutoff in cutoffs)
    records = build_first_billing_observations(histories, follow_up_through=watermark)
    split = assign_temporal_splits(records, CANONICAL_TEMPORAL_SPLIT_SPECIFICATION)
    pipeline = build_feature_pipeline(split)
    fitted = fit_logistic_baseline(pipeline.train)
    train = evaluate_logistic_baseline(fitted, pipeline.train)
    validation = evaluate_logistic_baseline(fitted, pipeline.validation)
    fitted_bytes = fitted_baseline_bytes(fitted)
    manifest = {
        "manifest_id": MANIFEST_ID,
        "manifest_version": MANIFEST_VERSION,
        "decision": "pipeline_engineering_only",
        "test_partition_status": "sealed_not_scored",
        "contracts": {
            "logistic_baseline_version": LOGISTIC_BASELINE_VERSION,
            "training_configuration_version": TRAINING_CONFIGURATION_VERSION,
            "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
            "feature_dictionary_version": FEATURE_DICTIONARY_VERSION,
        },
        "generation": legacy_generation_provenance(SEED, POLICY_COUNT),
        "source": {
            "feature_pipeline_manifest_sha256": sha256(FEATURE_MANIFEST_PATH.read_bytes()).hexdigest(),
            "input_matrices": {
                "train": {
                    "observation_ids": list(pipeline.train.observation_ids),
                    "matrix_sha256": matrix_digest(pipeline.train),
                },
                "validation": {
                    "observation_ids": list(pipeline.validation.observation_ids),
                    "matrix_sha256": matrix_digest(pipeline.validation),
                },
            },
        },
        "fit": {
            **fitted.to_dict(),
            "fitted_state_sha256": sha256(fitted_bytes).hexdigest(),
            "converged": True,
        },
        "coefficients": list(coefficient_summary(fitted)),
        "evaluation": {
            "train": {
                "metrics": train.metrics.to_dict(),
                "prediction_sha256": train.prediction_sha256,
            },
            "validation": {
                "metrics": validation.metrics.to_dict(),
                "prediction_sha256": validation.prediction_sha256,
            },
        },
        "limitations": [
            "LIM-002-001 remains claim-blocking and unresolved.",
            "Training is monthly-only and validation is semiannual-only; billing frequency is confounded with observation time.",
            "Metrics demonstrate pipeline mechanics and are not evidence of temporal generalization or real-world performance.",
            "The canonical test partition remains sealed and was not scored.",
            "No calibration, threshold selection, resampling, feature selection, or model comparison occurs in this phase.",
            "Coefficients describe this fitted synthetic model and are not causal or action-authorizing effects.",
        ],
    }
    return _canonicalize_artifact_numbers(manifest), fitted_bytes


def manifest_bytes() -> bytes:
    manifest, _ = build_baseline()
    return _canonical_json(manifest)


def report_bytes(manifest: dict) -> bytes:
    train = manifest["evaluation"]["train"]["metrics"]
    validation = manifest["evaluation"]["validation"]["metrics"]
    rows = "\n".join(
        f"| `{item['feature_name']}` | {item['coefficient']:.10g} | {item['odds_ratio']:.10g} |"
        for item in manifest["coefficients"]
    )
    text = f"""# Phase 2.05 Logistic-Regression Baseline Report

## Decision

This seeded logistic-regression run is a reproducible pipeline-engineering benchmark only. `LIM-002-001` remains unresolved, and the canonical test partition stayed sealed.

## Frozen configuration

- Baseline version: `{manifest['contracts']['logistic_baseline_version']}`
- Training configuration: `{manifest['contracts']['training_configuration_version']}`
- Seed: `{manifest['fit']['specification']['random_seed']}`
- Solver: `{manifest['fit']['specification']['solver']}`
- Penalty and C: `{manifest['fit']['specification']['penalty']}`, `{manifest['fit']['specification']['regularization_strength']}`
- scikit-learn: `{manifest['fit']['sklearn_version']}`
- Fit partition: train only
- Test status: sealed and not scored

## Predeclared diagnostics

| Partition | Records | Positive | Log loss | ROC AUC | Brier score | Mean prediction | Observed fraction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | {train['record_count']} | {train['class_distribution']['positive']} | {train['log_loss']:.6f} | {train['roc_auc']:.6f} | {train['brier_score']:.6f} | {train['average_predicted_probability']:.6f} | {train['observed_positive_fraction']:.6f} |
| Validation | {validation['record_count']} | {validation['class_distribution']['positive']} | {validation['log_loss']:.6f} | {validation['roc_auc']:.6f} | {validation['brier_score']:.6f} | {validation['average_predicted_probability']:.6f} | {validation['observed_positive_fraction']:.6f} |

These values were not used to tune the estimator, preprocessing, calibration, or a decision threshold.

## Coefficients

| Frozen transformed feature | Coefficient | Odds ratio |
| --- | ---: | ---: |
{rows}

Coefficients operate on standardized numeric fields and frozen one-hot columns. They are associations in a small, deliberately engineered synthetic corpus; they are not causal effects, actuarial factors, customer-impact evidence, or authority for conservation action.

## Limitations

- Billing frequency is confounded with first-billing observation time: train is monthly-only and validation is semiannual-only.
- Unseen held-out categories use the Phase 2.04 frozen unknown-category columns.
- The balanced fictional outcome mix is not a prevalence estimate.
- No canonical test result, calibration assessment, threshold, capacity analysis, fairness conclusion, or production claim is provided.

## Reproduction

```bash
python3 scripts/train_logistic_baseline.py --check
```
"""
    return text.encode("utf-8")


def artifact_bytes() -> tuple[bytes, bytes]:
    manifest, _ = build_baseline()
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
            print(f"missing Phase 2.05 artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
        elif path.read_bytes() != content:
            print(f"stale Phase 2.05 artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
    if valid:
        print("Phase 2.05 logistic baseline artifacts are reproducible; test remains sealed.")
    return valid


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify Phase 2.05 baseline artifacts.")
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
