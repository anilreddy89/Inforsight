#!/usr/bin/env python3
"""Build or verify the sealed-test feature-diagnostic artifacts."""

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
    DIAGNOSTIC_CONFIGURATION_VERSION,
    DIAGNOSTIC_RANDOM_SEED,
    FEATURE_DIAGNOSTICS_VERSION,
    FEATURE_DICTIONARY_VERSION,
    FEATURE_PIPELINE_VERSION,
    FROZEN_DIAGNOSTIC_SPECIFICATION,
    LABEL_HORIZON_DAYS,
    assign_temporal_splits,
    build_feature_pipeline,
    build_first_billing_observations,
    diagnostic_flags,
    first_billing_observation_time,
    fit_boosted_model,
    fit_logistic_baseline,
    fitted_baseline_bytes,
    fitted_boosted_bytes,
    fitted_state_bytes,
    generate_legacy_policy_histories,
    legacy_generation_provenance,
    identifier_and_cardinality_checks,
    matrix_digest,
    perturbation_flags,
    shallow_feature_models,
    source_feature_groups,
    targeted_permutation_checks,
    training_mutual_information,
    validate_dispositions,
)


MANIFEST_ID = "inforsight-phase-02-07-feature-diagnostics"
MANIFEST_VERSION = "1.0.0"
SEED = 20260817
POLICY_COUNT = 100
ARTIFACT_DECIMAL_PLACES = 10
EXPERIMENTS_DIR = REPOSITORY_ROOT / "docs" / "experiments"
MANIFEST_PATH = EXPERIMENTS_DIR / "phase-02-07-feature-diagnostics-manifest.json"
REPORT_PATH = EXPERIMENTS_DIR / "phase-02-07-feature-diagnostics-report.md"
UPSTREAM_PATHS = (
    EXPERIMENTS_DIR / "phase-02-04-feature-pipeline-manifest.json",
    EXPERIMENTS_DIR / "phase-02-05-logistic-baseline-manifest.json",
    EXPERIMENTS_DIR / "phase-02-05-logistic-baseline-report.md",
    EXPERIMENTS_DIR / "phase-02-06-boosted-comparison-manifest.json",
    EXPERIMENTS_DIR / "phase-02-06-boosted-comparison-report.md",
)


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


def _decision_registry(flagged_sources: set[str]) -> dict[str, dict[str, str]]:
    decisions = {}
    for source in sorted(flagged_sources):
        if source == "billing_frequency":
            decisions[source] = {
                "decision": "investigate",
                "rationale": "Billing frequency is temporally valid but confounded with observation time; diagnostic strength cannot be separated from LIM-002-001 in the current corpus.",
                "owner": "Inforsight maintainer",
                "decision_date": "2026-08-20",
                "follow_up": "Resolve or explicitly disposition LIM-002-001 before the Phase 2 evaluation gate.",
            }
        else:
            decisions[source] = {
                "decision": "allow",
                "rationale": "The source is contract-approved and cutoff-visible; the triggered screen is review evidence, not proof of an identifier, future-data leak, terminal-outcome proxy, or simulator marker.",
                "owner": "Inforsight maintainer",
                "decision_date": "2026-08-20",
                "follow_up": "Retain under the existing leakage guards and re-evaluate after the corpus limitation is resolved.",
            }
    return decisions


def build_diagnostics() -> dict:
    before_upstream = {path.name: path.read_bytes() for path in UPSTREAM_PATHS}
    histories = generate_legacy_policy_histories(SEED, POLICY_COUNT)
    cutoffs = [first_billing_observation_time(history) for history in histories]
    watermark = max(value + timedelta(days=LABEL_HORIZON_DAYS) for value in cutoffs)
    records = build_first_billing_observations(histories, follow_up_through=watermark)
    split = assign_temporal_splits(records, CANONICAL_TEMPORAL_SPLIT_SPECIFICATION)
    pipeline = build_feature_pipeline(split)
    preprocessor_before = fitted_state_bytes(pipeline.preprocessor)
    logistic = fit_logistic_baseline(pipeline.train)
    boosted = fit_boosted_model(pipeline.train)
    logistic_before = fitted_baseline_bytes(logistic)
    boosted_before = fitted_boosted_bytes(boosted)

    mutual_information = training_mutual_information(pipeline.train)
    shallow_models = shallow_feature_models(pipeline.train, pipeline.validation)
    cardinality = identifier_and_cardinality_checks(pipeline.train, pipeline.validation)
    initial_flags = diagnostic_flags(mutual_information, shallow_models, cardinality)
    targets = tuple(sorted({flag["source_feature"] for flag in initial_flags}))
    permutations = targeted_permutation_checks(logistic, boosted, pipeline.validation, targets)
    all_flags = tuple(
        sorted(
            {flag["flag_id"]: flag for flag in initial_flags + perturbation_flags(permutations)}.values(),
            key=lambda value: value["flag_id"],
        )
    )
    dispositions = validate_dispositions(
        all_flags, _decision_registry({flag["source_feature"] for flag in all_flags})
    )

    upstream_unchanged = all(path.read_bytes() == before_upstream[path.name] for path in UPSTREAM_PATHS)
    state_unchanged = {
        "preprocessor": fitted_state_bytes(pipeline.preprocessor) == preprocessor_before,
        "logistic_regression": fitted_baseline_bytes(logistic) == logistic_before,
        "xgboost": fitted_boosted_bytes(boosted) == boosted_before,
    }
    manifest = {
        "manifest_id": MANIFEST_ID,
        "manifest_version": MANIFEST_VERSION,
        "decision": "pipeline_engineering_only",
        "test_partition_status": "sealed_not_scored",
        "contracts": {
            "feature_diagnostics_version": FEATURE_DIAGNOSTICS_VERSION,
            "diagnostic_configuration_version": DIAGNOSTIC_CONFIGURATION_VERSION,
            "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
            "feature_dictionary_version": FEATURE_DICTIONARY_VERSION,
        },
        "configuration": {
            **FROZEN_DIAGNOSTIC_SPECIFICATION.to_dict(),
            "scikit_learn_version": "1.7.2",
            "artifact_decimal_places": ARTIFACT_DECIMAL_PLACES,
        },
        "generation": legacy_generation_provenance(SEED, POLICY_COUNT),
        "source": {
            "upstream_artifact_sha256": {
                path.name: sha256(before_upstream[path.name]).hexdigest() for path in UPSTREAM_PATHS
            },
            "input_matrices": {
                name: {
                    "observation_ids": list(getattr(pipeline, name).observation_ids),
                    "matrix_sha256": matrix_digest(getattr(pipeline, name)),
                    "row_count": len(getattr(pipeline, name).values),
                    "column_count": len(getattr(pipeline, name).feature_names),
                }
                for name in ("train", "validation")
            },
            "identity_policy": "observation IDs and targets are audit sidecars and never diagnostic feature columns",
        },
        "source_feature_groups": [
            {
                "source_feature": source,
                "output_features": [pipeline.train.feature_names[index] for index in indices],
            }
            for source, indices in source_feature_groups(pipeline.train)
        ],
        "diagnostics": {
            "training_mutual_information": mutual_information,
            "train_fit_validation_scored_shallow_models": shallow_models,
            "identifier_and_cardinality": cardinality,
            "targeted_validation_permutation": permutations,
        },
        "flags": all_flags,
        "dispositions": dispositions,
        "integrity": {
            "upstream_artifacts_unchanged": upstream_unchanged,
            "fitted_state_unchanged": state_unchanged,
            "targeted_source_features": list(targets),
        },
        "limitations": [
            "LIM-002-001 remains claim-blocking and unresolved.",
            "The corpus is small and synthetic; diagnostic estimates are unstable screening evidence.",
            "Training is monthly-only and validation is semiannual-only, so billing frequency is confounded with observation time.",
            "Association, mutual information, shallow-model strength, and permutation impact do not by themselves prove leakage.",
            "The canonical test partition remains sealed and was not inspected or scored.",
            "No feature change, model tuning, preprocessing refit, calibration, threshold selection, or release decision occurs here.",
        ],
    }
    if not upstream_unchanged or not all(state_unchanged.values()):
        raise ValueError("diagnostic execution mutated frozen state or upstream artifacts")
    return _canonicalize(manifest)


def report_bytes(manifest: dict) -> bytes:
    flags_by_source = {}
    for flag in manifest["flags"]:
        flags_by_source.setdefault(flag["source_feature"], []).append(flag["rule"])
    disposition_by_source = {item["source_feature"]: item for item in manifest["dispositions"]}
    rows = []
    for group in manifest["source_feature_groups"]:
        source = group["source_feature"]
        disposition = disposition_by_source.get(source)
        rows.append(
            f"| `{source}` | {', '.join(flags_by_source.get(source, [])) or 'None'} | "
            f"{disposition['decision'] if disposition else 'not_flagged'} | "
            f"{disposition['follow_up'] if disposition else 'No action from this screen.'} |"
        )
    mi_rows = "\n".join(
        f"| `{item['source_feature']}` | {item['maximum_mutual_information']:.6f} |"
        for item in manifest["diagnostics"]["training_mutual_information"]
    )
    shallow_rows = "\n".join(
        f"| `{item['source_feature']}` | {item['metrics']['log_loss']:.6f} | {item['metrics']['roc_auc']:.6f} | {item['metrics']['brier_score']:.6f} |"
        for item in manifest["diagnostics"]["train_fit_validation_scored_shallow_models"]
    )
    text = f"""# Feature-Sanity and Shortcut-Diagnostics Report

## Decision

The frozen train and validation matrices were screened reproducibly without opening the canonical test partition. Results remain `pipeline_engineering_only`: a flag prioritizes review and does not by itself prove leakage. `LIM-002-001` remains unresolved.

## Training-only mutual information

| Source feature | Maximum univariate MI |
| --- | ---: |
{mi_rows}

## Train-fit, validation-scored shallow models

| Source feature | Log loss | ROC AUC | Brier score |
| --- | ---: | ---: | ---: |
{shallow_rows}

## Flags and dispositions

| Source feature | Triggered rules | Disposition | Follow-up |
| --- | --- | --- | --- |
{chr(10).join(rows)}

Identifier/cardinality checks and deterministic targeted validation permutations are recorded in the machine-readable manifest. One-hot outputs are reviewed as source-feature groups. Observation IDs and targets remain sidecars.

## Integrity and limitations

- Test status: `sealed_not_scored`.
- Frozen preprocessing, logistic-regression state, and XGBoost state remained unchanged.
- Phase 2.04, Phase 2.05, and Phase 2.06 artifacts remained byte-identical.
- The small synthetic corpus makes mutual information, shallow-model scores, and permutation changes unstable.
- Billing frequency is confounded with observation time under `LIM-002-001`.
- No feature exclusion, model retraining, tuning, calibration, threshold selection, explanation, or release decision occurred.

## Reproduction

```bash
python3 scripts/run_feature_diagnostics.py --check
```
"""
    return text.encode("utf-8")


def artifact_bytes() -> tuple[bytes, bytes]:
    manifest = build_diagnostics()
    return _canonical_json(manifest), report_bytes(manifest)


def write_artifacts() -> None:
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest, report = artifact_bytes()
    MANIFEST_PATH.write_bytes(manifest)
    REPORT_PATH.write_bytes(report)
    print(f"wrote {MANIFEST_PATH.relative_to(REPOSITORY_ROOT)}")
    print(f"wrote {REPORT_PATH.relative_to(REPOSITORY_ROOT)}")


def check_artifacts() -> bool:
    manifest, report = artifact_bytes()
    expected = ((MANIFEST_PATH, manifest), (REPORT_PATH, report))
    valid = True
    for path, content in expected:
        if not path.is_file():
            print(f"missing Phase 2.07 artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
        elif path.read_bytes() != content:
            print(f"stale Phase 2.07 artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
    if valid:
        print("Feature-diagnostic artifacts are reproducible; test remains sealed.")
    return valid


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify Phase 2.07 diagnostic artifacts.")
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
