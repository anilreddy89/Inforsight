#!/usr/bin/env python3
"""Build or verify fail-closed R2-07 readiness and decision artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v2_acceptance import build_readiness_manifest  # noqa: E402


EXPERIMENTS = ROOT / "docs" / "experiments"
FILES = {
    "manifest": EXPERIMENTS / "phase-02r-07-v2-statistical-acceptance-manifest.json",
    "report": EXPERIMENTS / "phase-02r-07-v2-statistical-acceptance-report.md",
    "decision": EXPERIMENTS / "phase-02r-07-v2-statistical-acceptance-decision.md",
}


def canonical_json(value: dict[str, Any]) -> bytes:
    rendered = json.dumps(
        value, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True
    )
    return (rendered + "\n").encode("ascii")


def build_artifacts() -> dict[str, bytes]:
    manifest = build_readiness_manifest(ROOT)
    return {
        "manifest": canonical_json(manifest),
        "report": _report(manifest).encode("utf-8"),
        "decision": _decision(manifest).encode("utf-8"),
    }


def _report(manifest: dict[str, Any]) -> str:
    failures = [item for item in manifest["readiness_rules"] if item["status"] == "fail"]
    lines = [
        "# Phase 2R.07 v2 Statistical Acceptance Readiness Report",
        "",
        f"Decision: `{manifest['decision']}`.",
        "",
        "The readiness gate stopped before model fitting or statistical result generation. "
        "Protocol `1.0.0` cannot be executed against the current v2 implementation without "
        "post-result design choices, and a structural audit found post-cutoff ingestion leakage.",
        "",
        "## Readiness results",
        "",
        "| Rule | Status | Consequence |",
        "| --- | --- | --- |",
    ]
    for item in manifest["readiness_rules"]:
        consequence = item["failure_classification"] if item["status"] == "fail" else "none"
        lines.append(f"| `{item['rule_id']}` | `{item['status']}` | `{consequence}` |")
    lines.extend(
        (
            "",
            f"Failed readiness rules: {len(failures)} of {len(manifest['readiness_rules'])}.",
            "",
            "All 20 planned signal/null seed pairs and all three folds are accounted for as "
            "`not_run_protocol_not_executable`. They are not statistical failures and were not "
            "used to compute a performance result.",
            "",
            "No model was fitted, no prediction or bootstrap was produced, and the final release "
            "holdout remains `not_materialized`.",
            "",
            "`LIM-002-001`, `LIM-002-002`, and `LIM-002-003` remain claim-blocking; "
            "`LIM-002-004` is open and blocking. P2-08 and P2-09 remain paused. This evidence "
            "supports only protocol-readiness and synthetic-pipeline correctness conclusions.",
            "",
        )
    )
    return "\n".join(lines)


def _decision(manifest: dict[str, Any]) -> str:
    if manifest["decision"] != "stop":
        raise ValueError("the frozen readiness evidence must currently aggregate to stop")
    failed = [
        item["rule_id"]
        for item in manifest["readiness_rules"]
        if item["status"] == "fail"
    ]
    stop_rules = [
        item["rule_id"]
        for item in manifest["readiness_rules"]
        if item["status"] == "fail" and item["failure_classification"] == "stop"
    ]
    return "\n".join(
        (
            "# Phase 2R.07 Decision",
            "",
            "Decision: `stop`.",
            "",
            "The decision is mechanical under protocol `1.0.0`: the structural readiness audit "
            "found that cutoff features contain behavior values whose owning event was ingested "
            "after the cutoff and was absent from the observation's visible-event membership. "
            "Leakage is a `stop` condition and takes precedence over the independent `redesign` "
            "findings.",
            "",
            f"Failed stop rules: {', '.join(f'`{rule}`' for rule in stop_rules)}.",
            f"All failed readiness rules: {', '.join(f'`{rule}`' for rule in failed)}.",
            "",
            "No R2-07 statistical acceptance run occurred. No model was fitted, no predictions "
            "or metrics were produced, and the final holdout remains `not_materialized`.",
            "",
            "P2-08 and P2-09 remain paused. A focused corrective issue must repair the dual-time "
            "feature boundary and own the versioned matched-control/protocol redesign before "
            "acceptance execution can resume. `LIM-002-001` through `LIM-002-004` remain open.",
            "",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")

    artifacts = build_artifacts()
    if args.check:
        stale = [
            key
            for key, path in FILES.items()
            if not path.exists() or path.read_bytes() != artifacts[key]
        ]
        if stale:
            print(f"R2-07 readiness artifacts are stale: {', '.join(stale)}", file=sys.stderr)
            return 1
        print("R2-07 statistical-acceptance readiness check: passed (decision: stop)")
        return 0

    for key, path in FILES.items():
        path.write_bytes(artifacts[key])
        print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
