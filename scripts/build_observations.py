#!/usr/bin/env python3
"""Build or verify the Phase 2.01 observation sufficiency artifact."""

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
    GeneratorConfig,
    LABEL_HORIZON_DAYS,
    LABEL_POLICY_VERSION,
    OBSERVATION_CONTRACT_VERSION,
    build_first_billing_observations,
    first_billing_observation_time,
    generate_policy_histories,
    generation_provenance,
    summarize_observations,
)


ASSESSMENT_ID = "inforsight-phase-02-01-observation-sufficiency"
ASSESSMENT_VERSION = "1.0.0"
SEED = 20260817
POLICY_COUNT = 100
EXPERIMENTS_DIR = REPOSITORY_ROOT / "docs" / "experiments"
RESULT_PATH = EXPERIMENTS_DIR / "phase-02-01-observation-sufficiency.json"


def build_assessment() -> dict:
    """Return the canonical deterministic Phase 2.01 gate evidence."""

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
    counts = summarize_observations(records)
    expected = {
        "observation_count": 100,
        "eligible_observation_count": 100,
        "ineligible_observation_count": 0,
        "label_status_counts": {
            "observed_negative": 50,
            "observed_positive": 50,
        },
        "outcome_type_counts": {
            "outcome.lapsed": 25,
            "outcome.surrendered": 25,
        },
        "unique_policy_count": 100,
    }
    if counts != expected:
        raise ValueError(f"canonical observation counts changed: {counts}")

    return {
        "assessment_id": ASSESSMENT_ID,
        "assessment_version": ASSESSMENT_VERSION,
        "decision": "proceed_with_limitations",
        "decision_rationale": (
            "The current contract supports one deterministic first-billing observation "
            "per policy with explicit follow-up, but its balanced scenarios, simplified "
            "single-cycle paths, and small corpus cannot support real-world performance claims."
        ),
        "generation": generation_provenance(config),
        "observation_contract": {
            "version": OBSERVATION_CONTRACT_VERSION,
            "label_policy_version": LABEL_POLICY_VERSION,
            "cadence": "one_observation_at_first_billing_due_ingestion",
            "eligibility": "policy status is active at as_of under dual-time visibility",
            "feature_visibility": "effective_at <= as_of and ingested_at <= as_of",
            "horizon_days": LABEL_HORIZON_DAYS,
            "horizon_interval": "(as_of, as_of_plus_90_days]",
            "outcome_policy": "binary adverse termination: lapse or surrender",
            "negative_policy": "no qualifying outcome and complete explicit follow-up",
            "censoring_policy": (
                "right-censor when follow-up ends before the horizon or a horizon "
                "outcome is not ingested by the evaluation watermark"
            ),
        },
        "evaluation": {
            "follow_up_through": follow_up_through.isoformat(timespec="seconds").replace(
                "+00:00", "Z"
            ),
            "first_as_of": min(record.as_of for record in records),
            "last_as_of": max(record.as_of for record in records),
            "last_horizon_end": max(record.horizon_end for record in records),
            "counts": counts,
        },
        "field_inventory": {
            "available": [
                "active status at cutoff",
                "product variant",
                "billing frequency",
                "premium amount and currency",
                "policy age in days",
                "visible event counts by supported family",
            ],
            "prohibited": [
                "future-effective events",
                "future-ingested events",
                "terminal outcomes and final status in features",
                "scenario identifiers",
                "policy or event identifiers in features",
            ],
            "deferred_not_required_for_narrow_baseline": [
                "issue age",
                "face amount",
                "acquisition channel",
                "reinstatement and maturity",
                "loans and cash value",
                "account-change activity",
                "prior conservation attempts",
            ],
        },
        "limitations": [
            "The 50 percent positive fraction is engineered scenario coverage, not prevalence.",
            "One observation per policy does not establish a production observation cadence.",
            "The explicit evaluation watermark is an experiment boundary, not an event inferred from history end.",
            "The corpus contains simplified one-cycle paths and only 100 fictional policies.",
            "The gate supports engineering evaluation only, not actuarial, fairness, causal, or business claims.",
        ],
    }


def canonical_bytes() -> bytes:
    return (json.dumps(build_assessment(), indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def write_artifact() -> None:
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_bytes(canonical_bytes())
    print(f"wrote {RESULT_PATH.relative_to(REPOSITORY_ROOT)}")


def check_artifact() -> bool:
    if not RESULT_PATH.is_file():
        print(f"missing observation artifact: {RESULT_PATH.relative_to(REPOSITORY_ROOT)}")
        return False
    if RESULT_PATH.read_bytes() != canonical_bytes():
        print(f"stale observation artifact: {RESULT_PATH.relative_to(REPOSITORY_ROOT)}")
        return False
    print("Phase 2.01 observation sufficiency artifact is reproducible.")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or verify Phase 2.01 observation sufficiency evidence."
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
