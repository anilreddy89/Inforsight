#!/usr/bin/env python3
"""Build or verify deterministic read-only R2-10 structural support evidence."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator import (  # noqa: E402
    V3CorpusConfig, generate_v3_corpus, v3_structural_support_report,
)


EXPERIMENTS = ROOT / "docs" / "experiments"
JSON_REPORT = EXPERIMENTS / "phase-02r-10-v3-structural-support.json"
MARKDOWN_REPORT = EXPERIMENTS / "phase-02r-10-v3-structural-support.md"
UPSTREAM = EXPERIMENTS / "phase-02r-09-v3-corpus-manifest.json"


def build_report() -> dict[str, object]:
    corpus = generate_v3_corpus(V3CorpusConfig())
    report = v3_structural_support_report(corpus.observations)
    source_digest = sha256(b"".join(
        (ROOT / path).read_bytes() for path in (
            "simulator/src/inforsight_simulator/v3_evaluation.py",
            "scripts/check_v3_evaluation_support.py",
        )
    )).hexdigest()
    report["issue"] = 59
    report["lineage"] = {
        "r2_09_manifest_sha256": sha256(UPSTREAM.read_bytes()).hexdigest(),
        "source_sha256": source_digest,
        "dependency_lock_sha256": sha256(
            (ROOT / "simulator" / "pyproject.toml").read_bytes()
        ).hexdigest(),
        "command_sha256": sha256(
            b"python3 scripts/check_v3_evaluation_support.py --write\n"
        ).hexdigest(),
    }
    report["materialization"] = {
        "raw_observations": "regenerated_not_committed",
        "feature_matrices": "not_created",
        "predictions": "not_created",
        "model_metrics": "not_created",
        "oracle_sidecars": "not_accessed",
        "final_holdout": "not_materialized",
    }
    return report


def json_bytes(report: dict[str, object]) -> bytes:
    return json.dumps(report, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"


def markdown_bytes(report: dict[str, object]) -> bytes:
    lines = [
        "# Phase 2R.10 v3 Structural Support", "",
        f"Overall status: `{report['overall_status']}`.", "",
        "| Membership | Role | Eligible | Positive | Negative | Censored | Frequencies | Status |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in report["memberships"]:
        evaluation = item["evaluation"]
        frequencies = ", ".join(
            f"{name}={count}" for name, count in evaluation["billing_frequency"].items()
        )
        lines.append(
            f"| {item['name']} | {item['evaluation_role']} | "
            f"{evaluation['eligible_uncensored_observations']} | {evaluation['positive']} | "
            f"{evaluation['negative']} | {evaluation['right_censored_observations']} | "
            f"{frequencies} | {item['support_status']} |"
        )
    lines.extend(("", "## Failures", ""))
    failures = [
        f"- `{item['name']}`: {failure}"
        for item in report["memberships"] for failure in item["support_failures"]
    ]
    lines.extend(failures or ["- None."])
    lines.extend((
        "", "## Boundaries", "",
        "This report contains structural counts and membership digests only. It does not fit preprocessing or models, produce predictions or model metrics, access protected oracle sidecars, or materialize a final release holdout.",
        "", "The frozen selection support failure is retained as evidence. No date, role, seed, threshold, or corpus setting was changed in response.", "",
    ))
    return "\n".join(lines).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    expected = {JSON_REPORT: json_bytes(report), MARKDOWN_REPORT: markdown_bytes(report)}
    if args.write:
        EXPERIMENTS.mkdir(parents=True, exist_ok=True)
        for path, content in expected.items():
            path.write_bytes(content)
            print(f"Wrote {path.relative_to(ROOT)}")
        return 0
    stale = [str(path.relative_to(ROOT)) for path, content in expected.items()
             if not path.exists() or path.read_bytes() != content]
    if stale:
        print(f"R2-10 structural support evidence is missing or stale: {', '.join(stale)}", file=sys.stderr)
        return 1
    print("R2-10 v3 structural support reproducibility check: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
