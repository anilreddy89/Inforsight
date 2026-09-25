#!/usr/bin/env python3
"""Run the P4-07 qualification contract preflight or render a report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from p4_07_qualification import manifest, qualification_report, validate_contract, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate the frozen contract")
    parser.add_argument("--manifest", action="store_true", help="print the stable manifest")
    parser.add_argument("--report", type=Path, help="write a bounded report using supplied measurements")
    parser.add_argument("--measurements", type=Path, help="JSON measurement object for report mode")
    args = parser.parse_args()

    violations = validate_contract()
    if violations:
        for violation in violations:
            print(f"P4-07 contract violation: {violation}", file=sys.stderr)
        return 1

    if args.check:
        print("P4-07 qualification contract preflight passed")
        print(f"Manifest: {manifest()['manifest_sha256']}")
        print("Decision without runtime measurements: stop (fail closed)")
        return 0

    if args.manifest:
        print(json.dumps(manifest(), indent=2, sort_keys=True))
        return 0

    measurements = {}
    if args.measurements:
        measurements = json.loads(args.measurements.read_text(encoding="utf-8"))
        if not isinstance(measurements, dict):
            raise SystemExit("measurements must be a JSON object")
    report = qualification_report(measurements)
    if args.report:
        write_json(args.report, report)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
