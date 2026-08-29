#!/usr/bin/env python3
"""Build or verify the deterministic non-final R2-05 v2 corpus manifest."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator import (  # noqa: E402
    V2CorpusConfig,
    corpus_jsonl,
    generate_v2_corpus,
)

MANIFEST = ROOT / "docs" / "experiments" / "phase-02r-05-v2-corpus-manifest.json"
DATA_CARD = ROOT / "datasets" / "v2" / "DATA_CARD.md"


def _bytes(rows: list[dict]) -> bytes:
    return ("\n".join(
        json.dumps(row, allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        for row in rows
    ) + "\n").encode("ascii")


def build_manifest() -> dict:
    config = V2CorpusConfig(seed=20260901, run_namespace="r2-05-default")
    corpus = generate_v2_corpus(config)
    history_bytes = _bytes([event for history in corpus.histories for event in history])
    observation_bytes = corpus_jsonl(corpus.observations)
    oracle_bytes = corpus_jsonl(corpus.oracle_sidecar)
    role_summary = {}
    for role in sorted({row.role for row in corpus.observations}):
        rows = [row for row in corpus.observations if row.role == role]
        role_summary[role] = {
            "observations": len(rows),
            "positive": sum(row.label_value == 1 for row in rows),
            "negative": sum(row.label_value == 0 for row in rows),
            "right_censored": sum(row.label_status == "right_censored" for row in rows),
            "billing_frequencies": sorted({row.features.billing_frequency for row in rows}),
        }
    return {
        "artifact_version": "1.0.0",
        "phase": "R2-05",
        "status": "non_final_synthetic_corpus",
        "intended_use": "synthetic signal and governed pipeline validation only",
        "prohibited_claims": [
            "real_world_prediction", "actuarial", "causal", "fairness",
            "operational_readiness", "production_performance"
        ],
        "final_holdout_status": "not_materialized",
        "provenance": corpus.provenance,
        "counts": {
            "policies": len(corpus.histories),
            "events": sum(len(history) for history in corpus.histories),
            "observations": len(corpus.observations),
            "oracle_records": len(corpus.oracle_sidecar),
            "cohorts": len({row.cohort for row in corpus.observations}),
            "label_status": dict(sorted(Counter(row.label_status for row in corpus.observations).items())),
            "roles": role_summary,
        },
        "sha256": {
            "histories_jsonl": sha256(history_bytes).hexdigest(),
            "observations_jsonl": sha256(observation_bytes).hexdigest(),
            "protected_oracle_sidecar_jsonl": sha256(oracle_bytes).hexdigest(),
            "data_card": sha256(DATA_CARD.read_bytes()).hexdigest(),
        },
        "publication": {
            "raw_histories_committed": False,
            "raw_observations_committed": False,
            "oracle_sidecar_committed": False,
            "reason": "Deterministically regenerated evidence; protected and large raw artifacts are not repository source files."
        }
    }


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n").encode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = canonical_bytes(build_manifest())
    if args.check:
        if not MANIFEST.exists() or MANIFEST.read_bytes() != expected:
            print("R2-05 v2 corpus manifest is stale", file=sys.stderr)
            return 1
        print("R2-05 v2 corpus manifest reproducibility check: passed")
        return 0
    MANIFEST.write_bytes(expected)
    print(f"Wrote {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
