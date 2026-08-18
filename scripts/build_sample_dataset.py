#!/usr/bin/env python3
"""Build or verify Inforsight's deterministic published sample dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_SRC = REPOSITORY_ROOT / "simulator" / "src"
sys.path.insert(0, str(SIMULATOR_SRC))

from inforsight_simulator import (  # noqa: E402
    GeneratorConfig,
    generate_policy_histories,
    generation_provenance,
    histories_to_jsonl,
)


DATASET_VERSION = "0.1.0"
DATASET_ID = "inforsight-fictional-policy-events-sample"
SEED = 20260817
SOURCE_POLICY_COUNT = 100
HISTORIES_PER_SCENARIO = 2
SCENARIOS = ("active", "recovered", "lapsed", "surrendered")
SELECTION_RULE = "first-two-complete-histories-per-scenario-in-generator-order"
DATASETS_DIR = REPOSITORY_ROOT / "datasets"
DATASET_PATH = DATASETS_DIR / "sample-policy-events.jsonl"
MANIFEST_PATH = DATASETS_DIR / "sample-manifest.json"

PolicyEvent = dict[str, Any]
PolicyHistory = list[PolicyEvent]


def classify_scenario(history: PolicyHistory) -> str:
    """Return the current bounded generator scenario represented by a history."""

    event_types = {event["event_type"] for event in history}
    if "outcome.lapsed" in event_types:
        return "lapsed"
    if "outcome.surrendered" in event_types:
        return "surrendered"
    entered_grace = any(
        event["event_type"] == "policy.status_changed"
        and event["payload"].get("new_status") == "grace_period"
        for event in history
    )
    return "recovered" if entered_grace else "active"


def select_sample_histories(histories: list[PolicyHistory]) -> list[PolicyHistory]:
    """Select complete histories using the published stable selection rule."""

    selected: list[PolicyHistory] = []
    counts: Counter[str] = Counter()
    for history in histories:
        scenario = classify_scenario(history)
        if scenario not in SCENARIOS:
            raise ValueError(f"unsupported scenario: {scenario}")
        if counts[scenario] < HISTORIES_PER_SCENARIO:
            selected.append(history)
            counts[scenario] += 1

    expected = Counter({scenario: HISTORIES_PER_SCENARIO for scenario in SCENARIOS})
    if counts != expected:
        raise ValueError(
            f"source corpus cannot satisfy sample composition: {dict(counts)}"
        )
    return selected


def build_artifacts() -> tuple[bytes, bytes]:
    """Return the canonical dataset and manifest bytes."""

    config = GeneratorConfig(seed=SEED, policy_count=SOURCE_POLICY_COUNT)
    histories = generate_policy_histories(config.seed, config.policy_count)
    selected = select_sample_histories(histories)
    dataset_bytes = histories_to_jsonl(selected).encode("utf-8")
    events = [event for history in selected for event in history]

    scenario_counts = Counter(classify_scenario(history) for history in selected)
    event_type_counts = Counter(event["event_type"] for event in events)
    product_variant_counts = Counter(
        history[0]["payload"]["product_variant"] for history in selected
    )
    provenance = generation_provenance(config)
    manifest = {
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "artifact": {
            "file": DATASET_PATH.name,
            "format": "jsonl",
            "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        },
        "generation": provenance,
        "selection": {
            "histories_per_scenario": HISTORIES_PER_SCENARIO,
            "rule": SELECTION_RULE,
        },
        "composition": {
            "event_count": len(events),
            "event_type_counts": dict(sorted(event_type_counts.items())),
            "policy_count": len(selected),
            "product_variant_counts": dict(sorted(product_variant_counts.items())),
            "scenario_counts": {
                scenario: scenario_counts[scenario] for scenario in SCENARIOS
            },
        },
    }
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return dataset_bytes, manifest_text.encode("utf-8")


def write_artifacts() -> None:
    """Write the canonical artifacts to their repository locations."""

    dataset_bytes, manifest_bytes = build_artifacts()
    DATASETS_DIR.mkdir(exist_ok=True)
    DATASET_PATH.write_bytes(dataset_bytes)
    MANIFEST_PATH.write_bytes(manifest_bytes)
    print(f"wrote {DATASET_PATH.relative_to(REPOSITORY_ROOT)}")
    print(f"wrote {MANIFEST_PATH.relative_to(REPOSITORY_ROOT)}")


def check_artifacts() -> bool:
    """Return whether committed artifacts exactly match canonical bytes."""

    expected = dict(zip((DATASET_PATH, MANIFEST_PATH), build_artifacts()))
    valid = True
    for path, expected_bytes in expected.items():
        if not path.is_file():
            print(f"missing published artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
        elif path.read_bytes() != expected_bytes:
            print(f"stale published artifact: {path.relative_to(REPOSITORY_ROOT)}")
            valid = False
    if valid:
        print("Published sample dataset artifacts are reproducible.")
    return valid


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or verify the deterministic published sample dataset."
    )
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
