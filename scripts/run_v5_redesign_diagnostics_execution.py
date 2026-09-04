#!/usr/bin/env python3
"""Run or verify the governed R2-14BB diagnostic execution and aggregate evidence."""

from __future__ import annotations

import argparse
import json
from multiprocessing import Pool, cpu_count
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v4_config import V4CorpusConfig
from inforsight_simulator.v4_corpus import (
    generate_v4_corpus, public_mechanism_terms,
)
from inforsight_simulator.v3_evaluation import build_temporal_folds
from dataclasses import replace

from inforsight_simulator.v5_diagnostics_execution import (  # noqa: E402
    DEVELOPMENT_SEEDS,
    FEASIBILITY_GRID,
    aggregate_all_diagnostics,
    build_readiness_manifest,
    evaluate_grid_cell,
    execute_seed_diagnostics,
    render_execution_artifacts,
)

DESTINATIONS = {
    "manifest": ROOT
    / "docs/experiments/phase-02r-14bb-v5-redesign-diagnostic-manifest.json",
    "report": ROOT
    / "docs/experiments/phase-02r-14bb-v5-redesign-diagnostic-report.md",
    "disposition": ROOT
    / "docs/experiments/phase-02r-14bb-v5-hypothesis-disposition.md",
}


def _run_seed_worker(seed: int) -> dict:
    return execute_seed_diagnostics(seed)


def run_full_execution(readiness: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_paths = [output_dir / f"seed-{seed}.json" for seed in DEVELOPMENT_SEEDS]

    missing_seeds = [seed for seed, path in zip(DEVELOPMENT_SEEDS, seed_paths, strict=True) if not path.is_file()]

    if missing_seeds:
        workers = min(cpu_count(), len(missing_seeds), 8)
        print(f"Executing {len(missing_seeds)} development seeds using {workers} workers...", file=sys.stderr)
        with Pool(processes=workers) as pool:
            results = pool.map(_run_seed_worker, missing_seeds)
        for seed, result in zip(missing_seeds, results, strict=True):
            path = output_dir / f"seed-{seed}.json"
            path.write_text(json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n")

    seed_results = [json.loads(path.read_text()) for path in seed_paths]

    print("Evaluating 320-cell feasibility surface (D16 / D17)...", file=sys.stderr)
    sample_config = V4CorpusConfig(base_seed=20280101, scenario="stable")
    sample_corpus = generate_v4_corpus(sample_config, enforce_hazard_bound=False)
    compatible = tuple(replace(row, observation_contract_version="3.0.0") for row in sample_corpus.observations)
    folds = build_temporal_folds(compatible)
    eval_ids = {r.observation_id for r in folds[0].evaluation}
    eval_obs = [obs for obs in sample_corpus.observations if obs.observation_id in eval_ids]
    eval_matrix = np.array([list(public_mechanism_terms(obs.features).values()) for obs in eval_obs], dtype=float)
    oracle_map = {row.observation_id: row for row in sample_corpus.oracle_sidecar}
    eval_frailties = np.array([oracle_map[obs.observation_id].latent_frailty for obs in eval_obs], dtype=float)
    eval_targets = np.array([int(obs.label_value) for obs in eval_obs], dtype=int)

    feasibility_results = [
        evaluate_grid_cell(cell, eval_matrix, eval_frailties, eval_targets)
        for cell in FEASIBILITY_GRID
    ]

    return aggregate_all_diagnostics(seed_results, feasibility_results, readiness)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run or verify the R2-14BB diagnostic execution."
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--readiness-check",
        action="store_true",
        help="Print readiness and return 0 if authorized.",
    )
    modes.add_argument(
        "--seed",
        type=int,
        help="Execute diagnostics for a single development seed.",
    )
    modes.add_argument("--write", action="store_true", help="Run diagnostics and write artifacts.")
    modes.add_argument("--check", action="store_true", help="Verify diagnostic artifacts.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "tmp/r2-14bb-diagnostics",
        help="Temporary directory for intermediate seed results.",
    )
    args = parser.parse_args()

    readiness = build_readiness_manifest(ROOT)
    if args.readiness_check:
        print(json.dumps(readiness, indent=2, sort_keys=True))
        if readiness["readiness_decision"] != "authorized":
            print("R2-14BB readiness failed closed", file=sys.stderr)
            return 1
        print("R2-14BB readiness passed: execution authorized", file=sys.stderr)
        return 0

    if readiness["readiness_decision"] != "authorized":
        print("R2-14BB execution requires authorized readiness", file=sys.stderr)
        return 1

    if args.seed is not None:
        result = execute_seed_diagnostics(args.seed)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / f"seed-{args.seed}.json"
        path.write_text(json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n")
        print(f"Wrote {path.relative_to(ROOT)}")
        return 0

    if args.check:
        if not all(dest.is_file() for dest in DESTINATIONS.values()):
            print("R2-14BB artifacts are missing", file=sys.stderr)
            return 1
        existing = json.loads(DESTINATIONS["manifest"].read_text())
        artifacts = render_execution_artifacts(existing)
        stale = [
            name
            for name, destination in DESTINATIONS.items()
            if not destination.is_file()
            or destination.read_bytes() != artifacts[name]
        ]
        if stale:
            print(f"R2-14BB artifacts are stale: {', '.join(stale)}", file=sys.stderr)
            return 1
        print("R2-14BB execution artifacts reproduce byte-for-byte")
        return 0

    aggregate = run_full_execution(readiness, args.output_dir)
    artifacts = render_execution_artifacts(aggregate)

    for name, destination in DESTINATIONS.items():
        destination.write_bytes(artifacts[name])
        print(f"Wrote {destination.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

