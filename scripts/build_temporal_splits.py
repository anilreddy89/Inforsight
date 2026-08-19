#!/usr/bin/env python3
"""Build or verify the Phase 2.03 temporal split manifest."""

from __future__ import annotations

import argparse
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
    FEATURE_GUARD_VERSION,
    LABEL_HORIZON_DAYS,
    LABEL_POLICY_VERSION,
    OBSERVATION_CONTRACT_VERSION,
    TEMPORAL_SPLIT_CONTRACT_VERSION,
    GeneratorConfig,
    assign_temporal_splits,
    build_first_billing_observations,
    first_billing_observation_time,
    generate_policy_histories,
    generation_provenance,
    source_observation_digest,
    summarize_temporal_split,
)


MANIFEST_ID = "inforsight-phase-02-03-temporal-splits"
MANIFEST_VERSION = "1.0.0"
SEED = 20260817
POLICY_COUNT = 100
EXPERIMENTS_DIR = REPOSITORY_ROOT / "docs" / "experiments"
RESULT_PATH = EXPERIMENTS_DIR / "phase-02-03-temporal-split-manifest.json"


def build_manifest() -> dict:
    """Return canonical deterministic Phase 2.03 split evidence."""

    config = GeneratorConfig(seed=SEED, policy_count=POLICY_COUNT)
    histories = generate_policy_histories(config.seed, config.policy_count)
    cutoffs = [first_billing_observation_time(history) for history in histories]
    follow_up_through = max(
        cutoff + timedelta(days=LABEL_HORIZON_DAYS) for cutoff in cutoffs
    )
    records = build_first_billing_observations(
        histories,
        follow_up_through=follow_up_through,
    )
    result = assign_temporal_splits(
        records, CANONICAL_TEMPORAL_SPLIT_SPECIFICATION
    )
    summary = summarize_temporal_split(result)
    expected_counts = {
        "train": 26,
        "embargoed": 22,
        "validation": 27,
        "calendar_gap": 0,
        "test": 25,
        "excluded": 0,
    }
    actual_counts = {
        name: details["observation_count"] for name, details in summary.items()
    }
    if actual_counts != expected_counts:
        raise ValueError(f"canonical temporal split counts changed: {actual_counts}")

    assignments = {
        name: [record.observation_id for record in assigned]
        for name, assigned in result.disposition_items()
    }
    generation = generation_provenance(config)
    return {
        "manifest_id": MANIFEST_ID,
        "manifest_version": MANIFEST_VERSION,
        "decision": "pipeline_engineering_only",
        "decision_rationale": (
            "The strict chronological split demonstrates reproducible partitioning and "
            "embargo mechanics, but first-billing timing separates billing-frequency "
            "categories across partitions and cannot support temporal-performance claims."
        ),
        "contracts": {
            "temporal_split_contract_version": TEMPORAL_SPLIT_CONTRACT_VERSION,
            "observation_contract_version": OBSERVATION_CONTRACT_VERSION,
            "label_policy_version": LABEL_POLICY_VERSION,
            "feature_guard_version": FEATURE_GUARD_VERSION,
            "generator_version": generation["generator_version"],
            "event_schema_version": generation["schema_version"],
        },
        "generation": generation,
        "evaluation": {
            "follow_up_through": follow_up_through.isoformat(timespec="seconds").replace(
                "+00:00", "Z"
            ),
            "label_horizon_days": LABEL_HORIZON_DAYS,
            "embargo_rule": (
                "max(earlier.horizon_end) < min(later.as_of); equality is overlap"
            ),
        },
        "boundaries": result.specification.to_dict(),
        "source": {
            "observation_count": len(records),
            "canonical_identity_temporal_sha256": source_observation_digest(records),
        },
        "assignments": assignments,
        "summary": summary,
        "isolation": {
            "cross_partition_policy_overlap_count": 0,
            "cross_partition_outcome_episode_overlap_count": 0,
            "duplicate_observation_assignment_count": 0,
            "unaccounted_observation_count": 0,
        },
        "limitations": [
            "Observation time is strongly associated with billing frequency in the canonical generator.",
            "Training contains monthly policies, validation contains semiannual policies, and test contains annual policies.",
            "Quarterly observations are embargoed and cannot be reassigned to improve results.",
            "The 100-policy balanced fictional corpus supports pipeline mechanics only, not real-world performance claims.",
            "Test data must not influence preprocessing, model selection, calibration, or threshold choices.",
        ],
    }


def canonical_bytes() -> bytes:
    return (json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def write_artifact() -> None:
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_bytes(canonical_bytes())
    print(f"wrote {RESULT_PATH.relative_to(REPOSITORY_ROOT)}")


def check_artifact() -> bool:
    if not RESULT_PATH.is_file():
        print(f"missing temporal split manifest: {RESULT_PATH.relative_to(REPOSITORY_ROOT)}")
        return False
    if RESULT_PATH.read_bytes() != canonical_bytes():
        print(f"stale temporal split manifest: {RESULT_PATH.relative_to(REPOSITORY_ROOT)}")
        return False
    print("Phase 2.03 temporal split manifest is reproducible.")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or verify Phase 2.03 temporal split evidence."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify committed artifact")
    mode.add_argument("--write", action="store_true", help="replace committed artifact")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.write:
        write_artifact()
        return 0
    return 0 if check_artifact() else 1


if __name__ == "__main__":
    raise SystemExit(main())
