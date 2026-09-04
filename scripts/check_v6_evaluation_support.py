#!/usr/bin/env python3
"""Verify Generation v6 R2-15 structural support evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SUPPORT_JSON = ROOT / "docs/experiments/phase-02r-15-v6-structural-support.json"
SUPPORT_MD = ROOT / "docs/experiments/phase-02r-15-v6-structural-support.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    failures = []
    if not SUPPORT_JSON.exists():
        failures.append(f"{SUPPORT_JSON.relative_to(ROOT)}: missing")
    else:
        support = json.loads(SUPPORT_JSON.read_text(encoding="utf-8"))
        if support.get("overall_status") != "pass":
            failures.append(f"{SUPPORT_JSON.relative_to(ROOT)}: overall_status is not pass")
        if support.get("phase") != "R2-15":
            failures.append(f"{SUPPORT_JSON.relative_to(ROOT)}: invalid phase")
        if support.get("issue") != 90:
            failures.append(f"{SUPPORT_JSON.relative_to(ROOT)}: invalid issue")
        if support.get("final_holdout_status") != "not_materialized":
            failures.append(f"{SUPPORT_JSON.relative_to(ROOT)}: final holdout must be not_materialized")
    if not SUPPORT_MD.exists():
        failures.append(f"{SUPPORT_MD.relative_to(ROOT)}: missing")
    if failures:
        print("Generation v6 R2-15 structural support validation failed:\n" + "\n".join(failures), file=sys.stderr)
        return 1
    print("R2-15 Generation v6 structural support check: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
