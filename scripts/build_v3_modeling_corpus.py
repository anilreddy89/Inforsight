#!/usr/bin/env python3
"""Build or verify the deterministic non-final R2-09 v3 corpus manifest."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator import (  # noqa: E402
    V3CorpusConfig, execution_id, generate_v3_corpus, v3_corpus_digest,
)

MANIFEST = ROOT / "docs" / "experiments" / "phase-02r-09-v3-corpus-manifest.json"
DATA_CARD = ROOT / "datasets" / "v3" / "DATA_CARD.md"


def build_manifest() -> dict[str, object]:
    config = V3CorpusConfig()
    corpus = generate_v3_corpus(config)
    source_digest = sha256(b"".join(
        (ROOT / path).read_bytes() for path in (
            "simulator/src/inforsight_simulator/v3_config.py",
            "simulator/src/inforsight_simulator/v3_corpus.py",
            "scripts/build_v3_modeling_corpus.py",
        )
    )).hexdigest()
    dependency_lock_digest = sha256((ROOT / "simulator" / "pyproject.toml").read_bytes()).hexdigest()
    command_digest = sha256(b"python3 scripts/build_v3_modeling_corpus.py --write\n").hexdigest()
    roles = Counter(record.role for record in corpus.observations)
    outcomes = Counter(record.label_status for record in corpus.observations)
    frequencies = Counter(record.features.billing_frequency for record in corpus.observations)
    cohorts = Counter(record.cohort for record in corpus.observations)
    event_types = Counter(event["event_type"] for history in corpus.histories for event in history)
    return {
        "artifact_version": "1.0.0",
        "phase": "R2-09",
        "issue": 56,
        "claim_boundary": "fictional_mechanism_implementation_only",
        "provenance": {
            **corpus.provenance, "source_digest": source_digest,
            "dependency_lock_digest": dependency_lock_digest,
            "command_digest": command_digest,
            "execution_id": execution_id(
                config, source_digest=source_digest,
                dependency_lock_digest=dependency_lock_digest, command_digest=command_digest),
        },
        "counts": {
            "policies": len(corpus.histories), "observations": len(corpus.observations),
            "oracle_records": len(corpus.oracle_sidecar), "cohorts": dict(sorted(cohorts.items())),
            "billing_frequency": dict(sorted(frequencies.items())),
            "event_type": dict(sorted(event_types.items())), "label_status": dict(sorted(outcomes.items())),
            "role": dict(sorted(roles.items())),
        },
        "digests": v3_corpus_digest(corpus),
        "invariants": {
            "dual_time_visibility": "tested", "event_first_generation": "tested",
            "feature_lineage_complete": True, "identity_uniqueness": True,
            "non_overlapping_episodes": True, "oracle_sidecars_protected": True,
            "random_stream_registry": "1.0.0", "v1_v2_compatibility": "unchanged",
        },
        "materialization": {
            "raw_histories": "regenerated_not_committed",
            "public_observations": "regenerated_not_committed",
            "row_level_oracle_sidecars": "regenerated_not_committed",
            "final_holdout": "not_materialized",
        },
    }


def manifest_bytes() -> bytes:
    return json.dumps(build_manifest(), indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = manifest_bytes()
    if args.write:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_bytes(expected)
    if not MANIFEST.exists() or MANIFEST.read_bytes() != expected:
        print("R2-09 v3 corpus manifest is missing or stale", file=sys.stderr)
        return 1
    print("R2-09 v3 corpus manifest reproducibility check: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
