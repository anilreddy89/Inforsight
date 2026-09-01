#!/usr/bin/env python3
"""Execute R2-11 readiness; result-producing protocol stages follow this gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v3_acceptance import build_readiness_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--readiness-check", action="store_true",
        help="validate all pre-result prerequisites without fitting or scoring",
    )
    args = parser.parse_args()
    if not args.readiness_check:
        parser.error("use --readiness-check; --write/--check unlock only after readiness integration")
    manifest = build_readiness_manifest(ROOT)
    print(json.dumps(manifest, sort_keys=True, indent=2))
    if manifest["readiness_status"] != "pass":
        print("R2-11 readiness failed closed", file=sys.stderr)
        return 1
    print("R2-11 readiness check: passed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
