#!/usr/bin/env python3
"""Run or reproduce the governed Phase 2R.16 Generation v6 statistical acceptance protocol."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v6_acceptance import (  # noqa: E402
    RESERVED_ACCEPTANCE_SEEDS, aggregate_acceptance,
    build_readiness_manifest, execute_acceptance_seed,
    render_acceptance_artifacts,
)

DESTINATIONS = {
    "manifest": ROOT / "docs/experiments/phase-02r-16-v6-statistical-acceptance-manifest.json",
    "report": ROOT / "docs/experiments/phase-02r-16-v6-statistical-acceptance-report.md",
    "decision": ROOT / "docs/experiments/phase-02r-16-v6-statistical-acceptance-decision.md",
}


def _run_worker_seed(args_tuple: tuple[int, Path]) -> tuple[int, Path]:
    seed, output_dir = args_tuple
    path = output_dir / f"seed-{seed}.json"
    if not path.is_file():
        res = execute_acceptance_seed(seed, root=ROOT)
        path.write_text(json.dumps(res, allow_nan=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return seed, path


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2R.16 Generation v6 Statistical Acceptance Runner")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--readiness-check", action="store_true", help="verify pre-result prerequisites")
    modes.add_argument("--seed", type=int, help="execute acceptance for a single seed")
    modes.add_argument("--write", action="store_true", help="execute full 20-seed protocol and write artifacts")
    modes.add_argument("--check", action="store_true", help="verify committed artifacts reproduce bit-for-bit")

    parser.add_argument("--output-dir", type=Path, default=ROOT / "tmp/r2-16-acceptance")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4),
                        help="number of parallel worker processes for --write")

    args = parser.parse_args()

    readiness = build_readiness_manifest(ROOT)

    if args.readiness_check:
        print(json.dumps(readiness, indent=2, sort_keys=True))
        return 0 if readiness["readiness_decision"] == "proceed" else 1

    if args.seed is not None:
        if readiness["readiness_decision"] != "proceed":
            print("R2-16 readiness failed closed: cannot execute acceptance seeds", file=sys.stderr)
            return 1
        result = execute_acceptance_seed(args.seed, root=ROOT)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / f"seed-{args.seed}.json"
        path.write_text(json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")
        return 0

    paths = [args.output_dir / f"seed-{seed}.json" for seed in RESERVED_ACCEPTANCE_SEEDS]

    if args.write:
        if readiness["readiness_decision"] != "proceed":
            print("R2-16 readiness failed closed: cannot execute acceptance protocol", file=sys.stderr)
            return 1

        args.output_dir.mkdir(parents=True, exist_ok=True)
        pending_seeds = [seed for seed in RESERVED_ACCEPTANCE_SEEDS if not (args.output_dir / f"seed-{seed}.json").is_file()]

        if pending_seeds:
            print(f"Executing acceptance across {len(pending_seeds)} pending seeds with {args.workers} workers...")
            worker_args = [(seed, args.output_dir) for seed in pending_seeds]
            if args.workers > 1 and len(pending_seeds) > 1:
                with ProcessPoolExecutor(max_workers=args.workers) as executor:
                    for seed, path in executor.map(_run_worker_seed, worker_args):
                        print(f"Completed seed {seed} -> {path.name}")
            else:
                for arg in worker_args:
                    seed, path = _run_worker_seed(arg)
                    print(f"Completed seed {seed} -> {path.name}")

        seed_data = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
        aggregate = aggregate_acceptance(seed_data, readiness)
        artifacts = render_acceptance_artifacts(aggregate)

        for name, dest in DESTINATIONS.items():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(artifacts[name])
            print(f"Wrote {dest.relative_to(ROOT)}")

        print(f"R2-16 acceptance complete. Mechanical decision: {aggregate['decision']}")
        return 0

    if args.check:
        if any(not p.is_file() for p in paths) and DESTINATIONS["manifest"].is_file():
            aggregate = json.loads(DESTINATIONS["manifest"].read_text(encoding="utf-8"))
        elif any(not p.is_file() for p in paths):
            print("Complete R2-16 seed evidence is missing and manifest is absent", file=sys.stderr)
            return 1
        else:
            seed_data = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
            aggregate = aggregate_acceptance(seed_data, readiness)

        artifacts = render_acceptance_artifacts(aggregate)
        stale = [
            name for name, dest in DESTINATIONS.items()
            if not dest.is_file() or dest.read_bytes() != artifacts[name]
        ]
        if stale:
            print(f"R2-16 artifacts are stale or mismatched: {', '.join(stale)}", file=sys.stderr)
            return 1

        print(f"R2-16 statistical acceptance check passed. Mechanical decision: {aggregate['decision']}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
