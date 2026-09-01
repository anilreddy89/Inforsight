#!/usr/bin/env python3
"""Verify immutable pre-amendment R2-10 structural evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    ROOT / "docs/experiments/phase-02r-10-v3-structural-support.json":
        "611406e6eb3057217d305c3fd6b36832dc7e2b74017202db33874bd626ab1636",
    ROOT / "docs/experiments/phase-02r-10-v3-structural-support.md":
        "f94250ec0acdb49e85cf185987465ca3dceccd40da1ab7f4cc8619239cf13f0a",
}
DISPOSITION = ROOT / "docs/experiments/phase-02r-10-v3.1-pre-remediation-disposition.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    failures = []
    for path, expected in FILES.items():
        actual = sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"
        if actual != expected:
            failures.append(f"{path.relative_to(ROOT)}: expected {expected}, found {actual}")
    if not DISPOSITION.exists():
        failures.append(f"{DISPOSITION.relative_to(ROOT)}: missing")
    else:
        disposition = json.loads(DISPOSITION.read_text(encoding="utf-8"))
        if disposition.get("decision") != "invalidated_and_retained":
            failures.append(f"{DISPOSITION.relative_to(ROOT)}: invalid decision")
        for name, expected in disposition.get("retained_artifacts", {}).items():
            path = DISPOSITION.parent / name
            actual = sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"
            if actual != expected:
                failures.append(f"{path.relative_to(ROOT)}: expected {expected}, found {actual}")
    if failures:
        print("Immutable R2-10 v3.0 structural evidence changed:\n" + "\n".join(failures), file=sys.stderr)
        return 1
    print("R2-10 historical v3.0 and invalidated v3.1 evidence integrity check: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
