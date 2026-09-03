#!/usr/bin/env python3
"""Build or verify the governed R2-14B readiness-stop evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v5_diagnostics import (  # noqa: E402
    build_governed_stop_manifest,
    build_readiness_manifest,
    render_artifacts,
)

DESTINATIONS = {
    "manifest": ROOT
    / "docs/experiments/phase-02r-14b-v5-redesign-diagnostic-manifest.json",
    "report": ROOT
    / "docs/experiments/phase-02r-14b-v5-redesign-diagnostic-report.md",
    "disposition": ROOT
    / "docs/experiments/phase-02r-14b-v5-hypothesis-disposition.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify the R2-14B readiness-stop evidence."
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--readiness-check",
        action="store_true",
        help="Print readiness and return nonzero for the governed stop.",
    )
    modes.add_argument("--write", action="store_true", help="Write stop artifacts.")
    modes.add_argument("--check", action="store_true", help="Verify stop artifacts.")
    args = parser.parse_args()

    readiness = build_readiness_manifest(ROOT)
    if args.readiness_check:
        print(json.dumps(readiness, indent=2, sort_keys=True))
        if readiness["readiness_decision"] != "authorized":
            print("R2-14B readiness failed closed", file=sys.stderr)
            return 1
        print("R2-14B readiness passed", file=sys.stderr)
        return 0

    if readiness["readiness_decision"] != "stop":
        print("R2-14B stop evidence requires a readiness stop", file=sys.stderr)
        return 1

    artifacts = render_artifacts(build_governed_stop_manifest(readiness))
    if args.check:
        stale = [
            name
            for name, destination in DESTINATIONS.items()
            if not destination.is_file()
            or destination.read_bytes() != artifacts[name]
        ]
        if stale:
            print(f"R2-14B artifacts are stale: {', '.join(stale)}", file=sys.stderr)
            return 1
        print("R2-14B readiness-stop artifacts reproduce byte-for-byte")
        return 0

    for name, destination in DESTINATIONS.items():
        destination.write_bytes(artifacts[name])
        print(f"Wrote {destination.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
