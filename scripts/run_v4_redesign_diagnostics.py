#!/usr/bin/env python3
"""Run the R2-13 pre-result readiness boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v4_diagnostics import (  # noqa: E402
    DEVELOPMENT_DIAGNOSTIC_SEEDS, aggregate_diagnostics,
    build_readiness_manifest, evaluate_transform_parity_seed,
    execute_diagnostic_seed,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--readiness-check", action="store_true")
    modes.add_argument("--seed", type=int)
    modes.add_argument("--parity-seed", type=int)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    parser.add_argument(
        "--expect-blocked", action="store_true",
        help="succeed only when the proposed interpretation amendment still blocks results",
    )
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "tmp/r2-13-diagnostics")
    args = parser.parse_args()
    manifest = build_readiness_manifest(ROOT)
    if args.seed is not None:
        if manifest["readiness_decision"] != "authorized":
            print("R2-13 readiness does not authorize results", file=sys.stderr)
            return 1
        result = execute_diagnostic_seed(args.seed)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / f"seed-{args.seed}.json"
        path.write_text(json.dumps(result, allow_nan=False, indent=2,
                                   sort_keys=True) + "\n", encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")
        return 0
    if args.parity_seed is not None:
        if manifest["readiness_decision"] != "authorized":
            print("R2-13 readiness does not authorize parity results", file=sys.stderr)
            return 1
        parity = evaluate_transform_parity_seed(args.parity_seed)
        path = args.output_dir / f"seed-{args.parity_seed}.json"
        if not path.is_file():
            print("primary seed evidence is missing", file=sys.stderr)
            return 1
        result = json.loads(path.read_text(encoding="utf-8"))
        for scenario, folds in parity["scenarios"].items():
            by_fold = {item["fold"]: item for item in folds}
            for fold in result["variants"][scenario]["folds"]:
                fold["transform_parity"] = by_fold[fold["fold"]]
        path.write_text(json.dumps(result, allow_nan=False, indent=2,
                                   sort_keys=True) + "\n", encoding="utf-8")
        print(f"Updated parity in {path.relative_to(ROOT)}")
        return 0
    if args.write or args.check:
        paths = [args.output_dir / f"seed-{seed}.json"
                 for seed in DEVELOPMENT_DIAGNOSTIC_SEEDS]
        committed_manifest = ROOT / "docs/experiments/phase-02r-13-v4-redesign-diagnostic-manifest.json"
        if args.check and any(not path.is_file() for path in paths) and committed_manifest.is_file():
            aggregate = json.loads(committed_manifest.read_text(encoding="utf-8"))
        elif any(not path.is_file() for path in paths):
            print("complete R2-13 seed evidence is missing", file=sys.stderr)
            return 1
        else:
            aggregate = aggregate_diagnostics(
                json.loads(path.read_text(encoding="utf-8")) for path in paths
            )
        artifacts = _render_artifacts(aggregate)
        destinations = {
            "manifest": ROOT / "docs/experiments/phase-02r-13-v4-redesign-diagnostic-manifest.json",
            "report": ROOT / "docs/experiments/phase-02r-13-v4-redesign-diagnostic-report.md",
            "disposition": ROOT / "docs/experiments/phase-02r-13-v4-redesign-hypothesis-disposition.md",
        }
        if args.check:
            stale = [name for name, path in destinations.items()
                     if not path.is_file() or path.read_bytes() != artifacts[name]]
            if stale:
                print(f"R2-13 artifacts are stale: {', '.join(stale)}", file=sys.stderr)
                return 1
            print("R2-13 diagnostic artifacts reproduce", file=sys.stderr)
            return 0
        for name, path in destinations.items():
            path.write_bytes(artifacts[name])
            print(f"Wrote {path.relative_to(ROOT)}")
        return 0
    print(json.dumps(manifest, allow_nan=False, indent=2, sort_keys=True))
    if args.expect_blocked:
        if (manifest["readiness_decision"] == "redesign_required"
                and not manifest["result_producing_execution_authorized"]):
            print("R2-13 readiness correctly remains blocked before amendment review",
                  file=sys.stderr)
            return 0
        print("R2-13 pre-review blocked-state expectation failed", file=sys.stderr)
        return 1
    if manifest["readiness_decision"] != "authorized":
        print("R2-13 readiness failed closed", file=sys.stderr)
        return 1
    print("R2-13 readiness check passed; diagnostic execution is authorized", file=sys.stderr)
    return 0


def _render_artifacts(aggregate: dict) -> dict[str, bytes]:
    manifest = json.dumps(aggregate, allow_nan=False, indent=2,
                          sort_keys=True).encode() + b"\n"
    summary = aggregate["summary"]
    dispositions = aggregate["hypothesis_dispositions"]
    report_lines = [
        "# Phase 2R.13 v4 Redesign Diagnostic Report", "",
        "Issue: #69", "", "## Aggregate results", "",
        "| Measure | Observed |", "| --- | ---: |",
    ]
    summary_order = (
        "observable_oracle_auc_pass_count",
        "median_observable_oracle_auc",
        "median_observable_oracle_ap_lift",
        "median_observable_oracle_brier_skill",
        "median_xgboost_auc",
        "median_logistic_auc",
        "median_policy_episode_auc_difference",
        "median_oracle_fold_spread",
        "parity_mismatch_count",
        "near_constant_public_terms",
    )
    if set(summary) != set(summary_order):
        raise ValueError("R2-13 report summary schema changed")
    report_lines.extend(
        f"| `{key}` | `{summary[key]}` |" for key in summary_order
    )
    report_lines.extend([
        "", "## Hypothesis dispositions", "",
        "| Hypothesis | Disposition |", "| --- | --- |",
    ])
    report_lines.extend(f"| `{key}` | `{value}` |" for key, value in dispositions.items())
    report_lines.extend([
        "", "## Decision boundary", "",
        f"Selected response: `{aggregate['selected_response']}`.", "",
        "This evidence diagnoses only recovery of a fictional synthetic mechanism. ",
        "Future acceptance and the final holdout remain `not_materialized`.", "",
    ])
    disposition_lines = [
        "# Phase 2R.13 v4 Redesign Hypothesis Disposition", "",
        "The following dispositions are mechanical projections of the manifest:", "",
    ]
    disposition_lines.extend(f"- `{key}`: `{value}`" for key, value in dispositions.items())
    disposition_lines.extend([
        "", f"Permitted response: `{aggregate['selected_response']}`.", "",
        "No v4 implementation or acceptance execution is authorized by this note.",
        "The future acceptance block and final holdout remain `not_materialized`.", "",
    ])
    return {
        "manifest": manifest,
        "report": "\n".join(report_lines).encode(),
        "disposition": "\n".join(disposition_lines).encode(),
    }


if __name__ == "__main__":
    raise SystemExit(main())
