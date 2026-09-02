#!/usr/bin/env python3
"""Run or reproduce the governed R2-14 v4 development qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v4_qualification import (  # noqa: E402
    DEVELOPMENT_SEEDS, GATE_IDS, aggregate_qualification, build_readiness_manifest,
    execute_qualification_seed,
)

DESTINATIONS = {
    "manifest": ROOT / "docs/experiments/phase-02r-14-v4-qualification-manifest.json",
    "report": ROOT / "docs/experiments/phase-02r-14-v4-qualification-report.md",
    "decision": ROOT / "docs/experiments/phase-02r-14-v4-qualification-decision.md",
}


def render(aggregate: dict) -> dict[str, bytes]:
    manifest = json.dumps(aggregate, allow_nan=False, indent=2,
                          sort_keys=True).encode() + b"\n"
    summary = aggregate["summary"]
    report = ["# Phase 2R.14 v4 Development Qualification Report", "", "Issue: #72", "",
              "## Result", "", f"Mechanical decision: `{aggregate['decision']}`.", "",
              "## Qualification summary", "", "| Measure | Observed |", "| --- | ---: |"]
    for key in ("observable_oracle_auc_pass_count", "median_observable_oracle_auc",
                "median_observable_oracle_ap_lift", "median_observable_oracle_brier_skill",
                "reference_model_auc_pass_count", "median_matched_null_oracle_auc",
                "median_matched_null_candidate_auc", "parity_mismatch_count",
                "maximum_monthly_terminal_hazard"):
        report.append(f"| `{key}` | `{summary[key]}` |")
    report.extend(["", "## Gates", "", "| Gate | Status |", "| --- | --- |"])
    if set(aggregate["gates"]) != set(GATE_IDS):
        raise ValueError("R2-14 report gate schema changed")
    report.extend(f"| `{gate}` | `{result['status']}` |"
                  for gate in GATE_IDS
                  for result in (aggregate["gates"][gate],))
    report.extend(["", "This is development qualification of a fictional synthetic mechanism only.",
                   "Future acceptance and the final holdout remain `not_materialized`.", ""])
    decision = ["# Phase 2R.14 v4 Qualification Decision", "",
                f"The mechanical decision is `{aggregate['decision']}`.", ""]
    if aggregate["decision"] == "qualified":
        decision.append("R2-15 evaluation construction and candidate freeze are authorized after merge.")
    else:
        decision.append("R2-15 remains blocked; return to a reviewed R2-13 design version.")
    decision.extend(["", "R2-16 acceptance is not authorized. Future acceptance and the final holdout remain `not_materialized`.", ""])
    return {"manifest": manifest, "report": "\n".join(report).encode(),
            "decision": "\n".join(decision).encode()}


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--readiness-check", action="store_true")
    modes.add_argument("--seed", type=int)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "tmp/r2-14-qualification")
    args = parser.parse_args()
    readiness = build_readiness_manifest(ROOT)
    if args.readiness_check:
        print(json.dumps(readiness, indent=2, sort_keys=True))
        return 0 if readiness["readiness_decision"] == "authorized" else 1
    if args.seed is not None:
        if readiness["readiness_decision"] != "authorized":
            print("R2-14 readiness failed closed", file=sys.stderr)
            return 1
        result = execute_qualification_seed(args.seed)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / f"seed-{args.seed}.json"
        path.write_text(json.dumps(result, allow_nan=False, indent=2,
                                   sort_keys=True) + "\n")
        print(f"Wrote {path.relative_to(ROOT)}")
        return 0
    paths = [args.output_dir / f"seed-{seed}.json" for seed in DEVELOPMENT_SEEDS]
    if args.check and any(not path.is_file() for path in paths) and DESTINATIONS["manifest"].is_file():
        aggregate = json.loads(DESTINATIONS["manifest"].read_text())
    elif any(not path.is_file() for path in paths):
        print("complete R2-14 seed evidence is missing", file=sys.stderr)
        return 1
    else:
        aggregate = aggregate_qualification(
            (json.loads(path.read_text()) for path in paths), readiness)
    artifacts = render(aggregate)
    if args.check:
        stale = [name for name, path in DESTINATIONS.items()
                 if not path.is_file() or path.read_bytes() != artifacts[name]]
        if stale:
            print(f"R2-14 artifacts are stale: {', '.join(stale)}", file=sys.stderr)
            return 1
        print("R2-14 qualification artifacts reproduce")
        return 0
    for name, path in DESTINATIONS.items():
        path.write_bytes(artifacts[name])
        print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
