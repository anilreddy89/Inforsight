#!/usr/bin/env python3
"""Build or verify the Phase 2.04 feature dictionary and pipeline manifest."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_SRC = REPOSITORY_ROOT / "simulator" / "src"
sys.path.insert(0, str(SIMULATOR_SRC))

from inforsight_simulator import (  # noqa: E402
    CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
    FEATURE_DICTIONARY_VERSION,
    FEATURE_GUARD_VERSION,
    FEATURE_PIPELINE_VERSION,
    LABEL_HORIZON_DAYS,
    LABEL_POLICY_VERSION,
    OBSERVATION_CONTRACT_VERSION,
    TEMPORAL_SPLIT_CONTRACT_VERSION,
    assign_temporal_splits,
    build_feature_pipeline,
    build_first_billing_observations,
    feature_dictionary,
    first_billing_observation_time,
    fitted_state_bytes,
    generate_legacy_policy_histories,
    legacy_generation_provenance,
    matrix_digest,
    source_observation_digest,
)


MANIFEST_ID = "inforsight-phase-02-04-feature-pipeline"
MANIFEST_VERSION = "1.0.0"
SEED = 20260817
POLICY_COUNT = 100
MODELING_DIR = REPOSITORY_ROOT / "docs" / "modeling"
EXPERIMENTS_DIR = REPOSITORY_ROOT / "docs" / "experiments"
DICTIONARY_PATH = MODELING_DIR / "phase-02-04-feature-dictionary.json"
MANIFEST_PATH = EXPERIMENTS_DIR / "phase-02-04-feature-pipeline-manifest.json"
TEMPORAL_MANIFEST_PATH = EXPERIMENTS_DIR / "phase-02-03-temporal-split-manifest.json"


def _canonical_json(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def dictionary_bytes() -> bytes:
    return _canonical_json(feature_dictionary())


def build_manifest() -> dict:
    histories = generate_legacy_policy_histories(SEED, POLICY_COUNT)
    cutoffs = [first_billing_observation_time(history) for history in histories]
    watermark = max(cutoff + timedelta(days=LABEL_HORIZON_DAYS) for cutoff in cutoffs)
    records = build_first_billing_observations(histories, follow_up_through=watermark)
    split = assign_temporal_splits(records, CANONICAL_TEMPORAL_SPLIT_SPECIFICATION)
    pipeline = build_feature_pipeline(split)
    fitted_bytes = fitted_state_bytes(pipeline.preprocessor)
    generation = legacy_generation_provenance(SEED, POLICY_COUNT)
    matrices = {
        name: {
            "row_count": len(getattr(pipeline, name).values),
            "column_count": len(getattr(pipeline, name).feature_names),
            "matrix_sha256": matrix_digest(getattr(pipeline, name)),
        }
        for name in ("train", "validation", "test")
    }
    return {
        "manifest_id": MANIFEST_ID,
        "manifest_version": MANIFEST_VERSION,
        "decision": "pipeline_engineering_only",
        "contracts": {
            "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
            "feature_dictionary_version": FEATURE_DICTIONARY_VERSION,
            "feature_guard_version": FEATURE_GUARD_VERSION,
            "temporal_split_contract_version": TEMPORAL_SPLIT_CONTRACT_VERSION,
            "observation_contract_version": OBSERVATION_CONTRACT_VERSION,
            "label_policy_version": LABEL_POLICY_VERSION,
            "generator_version": generation["generator_version"],
            "event_schema_version": generation["schema_version"],
        },
        "generation": generation,
        "source": {
            "observation_count": len(records),
            "canonical_identity_temporal_sha256": source_observation_digest(records),
            "temporal_split_manifest_sha256": sha256(
                TEMPORAL_MANIFEST_PATH.read_bytes()
            ).hexdigest(),
            "feature_dictionary_sha256": sha256(dictionary_bytes()).hexdigest(),
        },
        "fit": {
            "partition": "train",
            "training_observation_ids": list(
                pipeline.preprocessor.training_observation_ids
            ),
            "numeric_fits": [
                value.to_dict() for value in pipeline.preprocessor.numeric_fits
            ],
            "categorical_fits": [
                value.to_dict() for value in pipeline.preprocessor.categorical_fits
            ],
            "fitted_state_sha256": sha256(fitted_bytes).hexdigest(),
        },
        "output": {
            "feature_names": list(pipeline.preprocessor.output_feature_names),
            "partition_summaries": matrices,
            "identity_policy": "observation IDs are audit sidecars, never model columns",
            "missingness_policy": "reject_missing_required_values",
            "unknown_category_policy": "map_to_predeclared_unknown_output_column",
        },
        "limitations": [
            "LIM-002-001 remains claim-blocking and unresolved.",
            "Training is monthly-only; validation is semiannual-only; test is annual-only.",
            "Unknown-category handling demonstrates safe mechanics, not temporal generalization.",
            "The balanced fictional corpus is not representative of real-world prevalence or performance.",
            "No model fitting, resampling, calibration, or threshold selection occurs in this phase.",
        ],
    }


def manifest_bytes() -> bytes:
    return _canonical_json(build_manifest())


def write_artifacts() -> None:
    MODELING_DIR.mkdir(parents=True, exist_ok=True)
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    DICTIONARY_PATH.write_bytes(dictionary_bytes())
    MANIFEST_PATH.write_bytes(manifest_bytes())
    print(f"wrote {DICTIONARY_PATH.relative_to(REPOSITORY_ROOT)}")
    print(f"wrote {MANIFEST_PATH.relative_to(REPOSITORY_ROOT)}")


def check_artifacts() -> bool:
    expected = ((DICTIONARY_PATH, dictionary_bytes()), (MANIFEST_PATH, manifest_bytes()))
    valid = True
    for path, content in expected:
        if not path.is_file():
            print(f"missing Phase 2.04 artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
        elif path.read_bytes() != content:
            print(f"stale Phase 2.04 artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
    if valid:
        print("Phase 2.04 feature pipeline artifacts are reproducible.")
    return valid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or verify Phase 2.04 feature artifacts.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify committed artifacts")
    mode.add_argument("--write", action="store_true", help="replace committed artifacts")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.write:
        write_artifacts()
        return 0
    return 0 if check_artifacts() else 1


if __name__ == "__main__":
    raise SystemExit(main())
