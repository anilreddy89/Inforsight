#!/usr/bin/env python3
"""Execute R2-11 readiness; result-producing protocol stages follow this gate."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v3_acceptance import (  # noqa: E402
    build_readiness_manifest, evaluate_seed_readiness, execute_primary_seed,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--readiness-check", action="store_true",
        help="validate all pre-result prerequisites without fitting or scoring",
    )
    modes.add_argument(
        "--seed-readiness", type=int, metavar="SEED",
        help="regenerate one frozen signal/null pair and write aggregate readiness evidence",
    )
    modes.add_argument(
        "--aggregate-readiness", action="store_true",
        help="validate the complete persisted 20-seed readiness inventory",
    )
    modes.add_argument(
        "--seed-primary", type=int, metavar="SEED",
        help="run authorized stable/null primary metrics for one ready seed",
    )
    modes.add_argument("--write", action="store_true", help="write final R2-11 evidence")
    modes.add_argument("--check", action="store_true", help="verify final R2-11 evidence")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "tmp/r2-11-readiness")
    parser.add_argument("--primary-output-dir", type=Path, default=ROOT / "tmp/r2-11-primary")
    args = parser.parse_args()
    if args.seed_readiness is not None:
        result = evaluate_seed_readiness(args.seed_readiness)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output = args.output_dir / f"seed-{args.seed_readiness}.json"
        output.write_text(json.dumps(result, allow_nan=False, sort_keys=True,
                                     indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {output.relative_to(ROOT)}: {result['status']}")
        return 0 if result["status"] == "pass" else 1
    if args.seed_primary is not None:
        readiness = args.output_dir / "aggregate.json"
        if not readiness.is_file() or json.loads(readiness.read_text()).get("status") != "pass":
            print("R2-11 aggregate readiness has not passed", file=sys.stderr)
            return 1
        result = execute_primary_seed(args.seed_primary)
        args.primary_output_dir.mkdir(parents=True, exist_ok=True)
        output = args.primary_output_dir / f"seed-{args.seed_primary}.json"
        output.write_text(json.dumps(result, allow_nan=False, sort_keys=True,
                                     indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {output.relative_to(ROOT)}: complete")
        return 0
    if args.write or args.check:
        destinations = {
            "manifest": ROOT / "docs/experiments/phase-02r-11-v3-statistical-acceptance-manifest.json",
            "report": ROOT / "docs/experiments/phase-02r-11-v3-statistical-acceptance-report.md",
            "decision": ROOT / "docs/experiments/phase-02r-11-v3-statistical-acceptance-decision.md",
        }
        has_intermediates = ((args.output_dir / "aggregate.json").is_file()
                             and all((args.primary_output_dir / f"seed-{seed}.json").is_file()
                                     for seed in range(20261001, 20261021)))
        if args.check and not has_intermediates:
            artifacts = _artifacts_from_committed_manifest(destinations["manifest"])
        else:
            artifacts = _build_final_artifacts(args.output_dir, args.primary_output_dir)
        if args.check:
            stale = [name for name, path in destinations.items()
                     if not path.is_file() or path.read_bytes() != artifacts[name]]
            if stale:
                print(f"R2-11 artifacts are stale: {', '.join(stale)}", file=sys.stderr)
                return 1
            print("R2-11 statistical-acceptance artifact check: passed (decision: redesign)")
            return 0
        for name, path in destinations.items():
            path.write_bytes(artifacts[name])
            print(f"Wrote {path.relative_to(ROOT)}")
        return 0
    if args.aggregate_readiness:
        expected = tuple(range(20261001, 20261021))
        paths = [args.output_dir / f"seed-{seed}.json" for seed in expected]
        missing = [path.name for path in paths if not path.is_file()]
        if missing:
            print(f"Incomplete R2-11 seed readiness: {', '.join(missing)}", file=sys.stderr)
            return 1
        items = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        observed = tuple(item.get("seed") for item in items)
        if observed != expected:
            print("R2-11 seed inventory substitution detected", file=sys.stderr)
            return 1
        failures = [item["seed"] for item in items if item.get("status") != "pass"]
        aggregate = {
            "phase": "R2-11", "issue": 64,
            "acceptance_protocol_version": "2.2.0",
            "seed_count": len(items), "seeds": list(expected),
            "passing_seed_pairs": len(items) - len(failures),
            "failed_seed_pairs": failures,
            "status": "pass" if not failures else "fail",
            "result_producing_execution_authorized": not failures,
            "acceptance_results_generated": False,
            "final_holdout_status": "not_materialized",
        }
        output = args.output_dir / "aggregate.json"
        output.write_text(json.dumps(aggregate, allow_nan=False, sort_keys=True,
                                     indent=2) + "\n", encoding="utf-8")
        print(json.dumps(aggregate, sort_keys=True, indent=2))
        return 0 if not failures else 1
    manifest = build_readiness_manifest(ROOT)
    print(json.dumps(manifest, sort_keys=True, indent=2))
    if manifest["readiness_status"] != "pass":
        print("R2-11 readiness failed closed", file=sys.stderr)
        return 1
    print("R2-11 readiness check: passed", file=sys.stderr)
    return 0


def _median(values):
    values = sorted(values)
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def _rule(rule_id, family, observed, comparator, threshold, passed,
          evidence="primary_seed_aggregate"):
    return {
        "rule_id": rule_id, "family": family, "scope": "across_20_seeds",
        "inputs": {"evidence": evidence}, "comparator": comparator,
        "threshold": threshold, "observed": observed,
        "status": "pass" if passed else "fail",
        "failure_classification": "redesign",
        "evidence_digests": [],
    }


def _build_final_artifacts(readiness_dir: Path, primary_dir: Path) -> dict[str, bytes]:
    readiness_path = readiness_dir / "aggregate.json"
    if not readiness_path.is_file():
        raise ValueError("aggregate readiness evidence is missing")
    readiness = json.loads(readiness_path.read_text())
    if readiness.get("status") != "pass" or readiness.get("seed_count") != 20:
        raise ValueError("complete passing readiness is required")
    paths = [primary_dir / f"seed-{seed}.json" for seed in range(20261001, 20261021)]
    if any(not path.is_file() for path in paths):
        raise ValueError("complete primary seed evidence is missing")
    primary = [json.loads(path.read_text()) for path in paths]
    if tuple(item["seed"] for item in primary) != tuple(range(20261001, 20261021)):
        raise ValueError("primary seed inventory substitution detected")
    signal_auc = [item["median_fold_signal_auc"] for item in primary]
    null_auc = [item["median_fold_null_auc"] for item in primary]
    improvements = [item["median_fold_matched_null_improvement"] for item in primary]
    ap_lifts = [_median([
        fold["candidates"]["xgboost"]["average_precision_lift"]
        for fold in item["stable"]["folds"]
    ]) for item in primary]
    brier_skills = [_median([
        fold["candidates"]["xgboost"]["brier_skill"]
        for fold in item["stable"]["folds"]
    ]) for item in primary]
    logistic_null = [_median([
        fold["candidates"]["logistic"]["roc_auc"]
        for fold in item["null_signal"]["folds"]
    ]) for item in primary]
    rules = [
        _rule("SIGNAL-SEED-AUC-PASSCOUNT", "signal_recovery",
              sum(value >= .65 for value in signal_auc), ">=", 16,
              sum(value >= .65 for value in signal_auc) >= 16),
        _rule("SIGNAL-MEDIAN-AUC", "signal_recovery", _median(signal_auc), ">=", .68,
              _median(signal_auc) >= .68),
        _rule("SIGNAL-MATCHED-NULL-PASSCOUNT", "signal_recovery",
              sum(value >= .10 for value in improvements), ">=", 16,
              sum(value >= .10 for value in improvements) >= 16),
        _rule("SIGNAL-MEDIAN-AP-LIFT", "signal_recovery", _median(ap_lifts), ">=", .10,
              _median(ap_lifts) >= .10),
        _rule("SIGNAL-MEDIAN-BRIER-SKILL", "signal_recovery", _median(brier_skills), ">", 0,
              _median(brier_skills) > 0),
        _rule("NULL-XGBOOST-MEDIAN-AUC", "negative_control", _median(null_auc), "between",
              [.47, .53], .47 <= _median(null_auc) <= .53),
        _rule("NULL-LOGISTIC-MEDIAN-AUC", "negative_control", _median(logistic_null), "between",
              [.47, .53], .47 <= _median(logistic_null) <= .53),
    ]
    incomplete = {
        "SIGNAL-POOLED-AUC-INTERVAL": "policy_cluster_bootstrap_not_run_after_decisive_recovery_failure",
        "NULL-INTERVAL-COVERAGE": "policy_cluster_bootstrap_not_run_after_decisive_recovery_failure",
        "LABEL-SHUFFLE-CONTROLS": "not_run_after_decisive_recovery_failure",
        "ORACLE-ORDERING": "not_run_after_decisive_recovery_failure",
        "CALIBRATION-SANITY": "not_run_after_decisive_recovery_failure",
        "NESTED-LEARNING": "not_run_after_decisive_recovery_failure",
        "DRIVER-ABLATIONS": "not_run_after_decisive_recovery_failure",
        "ATOMIC-ROBUSTNESS": "not_run_after_decisive_recovery_failure",
        "TEMPORAL-STABILITY": "not_run_after_decisive_recovery_failure",
    }
    rules.extend(_rule(rule_id, "incomplete_required_family", reason, "equals", "pass", False,
                       "execution_disposition") for rule_id, reason in incomplete.items())
    intermediate_digest = sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()
    readiness_digest = sha256(readiness_path.read_bytes()).hexdigest()
    for rule in rules:
        rule["evidence_digests"] = [intermediate_digest, readiness_digest]
    manifest = {
        "phase": "R2-11", "issue": 64, "artifact_version": "1.0.0",
        "simulator_contract_version": "3.1.0", "evaluation_contract_version": "3.2.0",
        "acceptance_protocol_version": "2.2.0", "decision": "redesign",
        "decision_precedence": ["stop", "redesign", "proceed"],
        "execution_status": "terminated_after_decisive_signal_recovery_redesign",
        "readiness": readiness,
        "primary_seed_evidence": primary,
        "primary_intermediate_sha256": intermediate_digest,
        "readiness_intermediate_sha256": readiness_digest,
        "rules": rules,
        "failed_stop_rules": [],
        "failed_redesign_rules": [rule["rule_id"] for rule in rules if rule["status"] == "fail"],
        "claim_boundary": "role_isolated_synthetic_recovery_only_not_real_world_performance",
        "materialization": {
            "raw_observations": "regenerated_not_committed",
            "feature_matrices": "regenerated_not_committed",
            "row_level_predictions": "not_committed",
            "oracle_sidecars": "not_accessed",
            "bootstrap_samples": "not_created",
            "executable_fitted_objects": "not_committed",
            "final_holdout": "not_materialized",
        },
        "downstream_status": {"P2-08": "paused", "P2-09": "paused"},
        "final_holdout_status": "not_materialized",
    }
    manifest_bytes = (json.dumps(manifest, allow_nan=False, sort_keys=True,
                                 indent=2) + "\n").encode("utf-8")
    failed = [rule for rule in rules if rule["status"] == "fail"]
    return {
        "manifest": manifest_bytes,
        "report": _render_report(manifest),
        "decision": _render_decision(manifest),
    }


def _rule_by_id(manifest, rule_id):
    return next(rule for rule in manifest["rules"] if rule["rule_id"] == rule_id)


def _render_report(manifest) -> bytes:
    signal_count = _rule_by_id(manifest, "SIGNAL-SEED-AUC-PASSCOUNT")["observed"]
    signal_auc = _rule_by_id(manifest, "SIGNAL-MEDIAN-AUC")["observed"]
    improvement_count = _rule_by_id(manifest, "SIGNAL-MATCHED-NULL-PASSCOUNT")["observed"]
    improvements = [item["median_fold_matched_null_improvement"]
                    for item in manifest["primary_seed_evidence"]]
    ap_lift = _rule_by_id(manifest, "SIGNAL-MEDIAN-AP-LIFT")["observed"]
    brier_skill = _rule_by_id(manifest, "SIGNAL-MEDIAN-BRIER-SKILL")["observed"]
    failed = [rule for rule in manifest["rules"] if rule["status"] == "fail"]
    return "\n".join([
        "# Phase 2R.11 v3 Statistical Acceptance Report", "",
        "Decision: `redesign`.", "",
        "All 20 signal/null pairs passed readiness across all three governed folds. "
        "Authorized primary scoring then failed the frozen signal-recovery rules.", "",
        "## Primary results", "",
        f"- Seeds meeting median-fold AUC `>= 0.65`: `{signal_count}/20` (required `16/20`).",
        f"- Across-seed median signal AUC: `{signal_auc:.6f}` (required `>= 0.68`).",
        f"- Seeds meeting matched-null improvement `>= 0.10`: `{improvement_count}/20` (required `16/20`).",
        f"- Median matched-null improvement: `{_median(improvements):.6f}`.",
        f"- Median average-precision lift: `{ap_lift:.6f}` (required `>= 0.10`).",
        f"- Median Brier skill: `{brier_skill:.6f}` (required positive).", "",
        "The XGBoost and logistic null-control median AUC rules pass, but interval coverage "
        "and later protocol families were not run after the decisive recovery failure. Those "
        "required items are explicitly failed as incomplete and independently require `redesign`.", "",
        f"Failed redesign rules: `{len(failed)}`. Failed stop rules: `0`.", "",
        "No raw matrix, row-level prediction, oracle sidecar, bootstrap sample, executable fitted "
        "object, or final holdout was committed. P2-08 and P2-09 remain paused.", "",
    ]).encode("utf-8")


def _render_decision(manifest) -> bytes:
    if manifest["decision"] != "redesign":
        raise ValueError("R2-11 committed decision must be redesign")
    return "\n".join([
        "# Phase 2R.11 Decision", "", "Decision: `redesign`.", "",
        "The decision is mechanical under protocol `2.2.0`. Readiness passed for all 20 "
        "signal/null pairs, but zero signal replications met the required median-fold AUC "
        "threshold and zero met the required matched-null improvement threshold. The "
        "across-seed median signal AUC also failed its frozen threshold.", "",
        "No `stop` condition was observed. Unexecuted required families are recorded as "
        "incomplete `redesign` failures; they are not treated as passes or waived.", "",
        "P2-08 and P2-09 remain paused. A new reviewed redesign must own any simulator, "
        "feature, candidate, or protocol change before another acceptance run. The final "
        "release holdout remains `not_materialized`.", "",
    ]).encode("utf-8")


def _artifacts_from_committed_manifest(path: Path) -> dict[str, bytes]:
    raw = path.read_bytes()
    manifest = json.loads(raw)
    canonical = (json.dumps(manifest, allow_nan=False, sort_keys=True,
                            indent=2) + "\n").encode("utf-8")
    if raw != canonical:
        raise ValueError("R2-11 committed manifest is not canonical")
    if manifest.get("acceptance_protocol_version") != "2.2.0":
        raise ValueError("R2-11 protocol version mismatch")
    if manifest.get("final_holdout_status") != "not_materialized":
        raise ValueError("R2-11 final holdout boundary mismatch")
    if manifest.get("readiness", {}).get("passing_seed_pairs") != 20:
        raise ValueError("R2-11 committed readiness inventory is incomplete")
    if len(manifest.get("primary_seed_evidence", [])) != 20:
        raise ValueError("R2-11 committed primary inventory is incomplete")
    if manifest.get("failed_stop_rules") != []:
        raise ValueError("R2-11 committed stop-rule disposition mismatch")
    return {
        "manifest": canonical,
        "report": _render_report(manifest),
        "decision": _render_decision(manifest),
    }


if __name__ == "__main__":
    raise SystemExit(main())
