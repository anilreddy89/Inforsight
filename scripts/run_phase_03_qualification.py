#!/usr/bin/env python3
"""Phase 3.09: End-to-End System Qualification & Integration Gate CLI Runner.

Executes and verifies the 6 Pre-Registered System Qualification Gates (S1–S6)
across 1,000 synthetic policies under Generation v6 substrate.
Generates cryptographic qualification manifest and Markdown report.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure simulator src is on Python path
REPO_ROOT = Path(__file__).resolve().parent.parent
SIMULATOR_SRC = REPO_ROOT / "simulator" / "src"
if str(SIMULATOR_SRC) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_SRC))

from inforsight_simulator.qualification import (
    QualificationRunner,
    build_qualification_manifest,
    generate_qualification_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 3.09 End-to-End System Qualification Gate (S1–S6)."
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20280201,
        help="Base evaluation seed (default: 20280201)",
    )
    parser.add_argument(
        "--policies",
        type=int,
        default=1000,
        help="Number of synthetic policies in evaluation cohort (default: 1000)",
    )
    parser.add_argument(
        "--specialist-capacity",
        type=int,
        default=50,
        help="Specialist capacity limit in cases (default: 50)",
    )
    parser.add_argument(
        "--budget-cap",
        type=float,
        default=5000.0,
        help="Budget cap in USD (default: 5000.0)",
    )
    parser.add_argument(
        "--bundle-path",
        type=str,
        default="docs/experiments/phase-02-10-model-bundle.json",
        help="Path to release model bundle (default: docs/experiments/phase-02-10-model-bundle.json)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="docs/experiments/phase-03-09-qualification-manifest.json",
        help="Output path for JSON manifest (default: docs/experiments/phase-03-09-qualification-manifest.json)",
    )
    parser.add_argument(
        "--output-report",
        type=str,
        default="docs/experiments/phase-03-09-qualification-report.md",
        help="Output path for Markdown report (default: docs/experiments/phase-03-09-qualification-report.md)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Execute qualification and assert 100% pass across all 6 gates",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print("=" * 80)
    print("      INFORSIGHT SYSTEM QUALIFICATION & INTEGRATION GATE (PHASE 3.09)")
    print("=" * 80)
    print(f"Evaluation Seed     : {args.seed}")
    print(f"Synthetic Cohort    : {args.policies:,} policies")
    print(f"Specialist Capacity : {args.specialist_capacity} cases")
    print(f"Budget Cap (USD)    : ${args.budget_cap:,.2f}")
    print(f"Model Bundle Path   : {args.bundle_path}")
    print("-" * 80)

    runner = QualificationRunner(
        bundle_path=args.bundle_path,
        seed=args.seed,
        policy_count=args.policies,
        specialist_capacity=args.specialist_capacity,
        budget_cap_usd=args.budget_cap,
    )

    print("Executing end-to-end qualification pipeline across Gates S1–S6...")
    res = runner.run()

    print("\n--- Gate Results ---")
    for gid in sorted(res.gates.keys()):
        gate = res.gates[gid]
        status_sym = "[PASS]" if gate.passed else "[FAIL]"
        print(f"  {status_sym} {gid:8s} : {gate.name:<45s} | {gate.scorecard_metric}")

    print("-" * 80)
    print(f"Overall Decision    : {res.overall_decision}")
    print(f"All Gates Passed    : {res.all_gates_passed}")
    print(f"Pipeline Digest     : {res.pipeline_digest}")
    print("=" * 80)

    # Build manifest and report
    manifest = build_qualification_manifest(res)
    report_md = generate_qualification_report(manifest)

    # Save manifest
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nSaved qualification manifest -> {out_json}")

    # Save report
    out_report = Path(args.output_report)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    with open(out_report, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"Saved qualification report   -> {out_report}")

    if args.check and not res.all_gates_passed:
        print("\nERROR: Qualification failed! Not all gates passed.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
