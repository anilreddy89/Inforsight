#!/usr/bin/env python3
"""Build or verify deterministic R2-06 v2 evaluation artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v2_config import V2CorpusConfig  # noqa: E402
from inforsight_simulator.v2_corpus import corpus_jsonl, generate_v2_corpus  # noqa: E402
from inforsight_simulator.v2_evaluation import (  # noqa: E402
    FINAL_HOLDOUT_STATUS, V2_BASELINE_VERSION, V2_DIAGNOSTIC_VERSION,
    V2_FEATURE_DICTIONARY_VERSION, V2_FEATURE_PIPELINE_VERSION, V2_SPLIT_VERSION,
    PORTABLE_ARTIFACT_DECIMALS,
    build_selection_fold, build_temporal_folds, compare_baselines, diagnostics,
    fit_preprocessor, matrix_digest, preprocessor_digest, transform,
)

EXPERIMENTS = ROOT / "docs" / "experiments"
FILES = {
    "split": EXPERIMENTS / "phase-02r-06-v2-split-manifest.json",
    "feature": EXPERIMENTS / "phase-02r-06-v2-feature-pipeline-manifest.json",
    "diagnostic": EXPERIMENTS / "phase-02r-06-v2-feature-diagnostics-manifest.json",
    "diagnostic_report": EXPERIMENTS / "phase-02r-06-v2-feature-diagnostics-report.md",
    "baseline": EXPERIMENTS / "phase-02r-06-v2-baseline-comparison-manifest.json",
    "baseline_report": EXPERIMENTS / "phase-02r-06-v2-baseline-comparison-report.md",
}
FEATURE_DICTIONARY = ROOT / "docs" / "modeling" / "phase-02r-06-v2-feature-dictionary.json"
UPSTREAM = EXPERIMENTS / "phase-02r-05-v2-corpus-manifest.json"


def build_artifacts() -> dict[str, bytes]:
    corpus = generate_v2_corpus(V2CorpusConfig(seed=20260901, run_namespace="r2-05-default"))
    public_digest = sha256(corpus_jsonl(corpus.observations)).hexdigest()
    upstream_digest = sha256(UPSTREAM.read_bytes()).hexdigest()
    dictionary_digest = sha256(FEATURE_DICTIONARY.read_bytes()).hexdigest()
    folds = build_temporal_folds(corpus.observations)
    selection_fold = build_selection_fold(corpus.observations)
    fold_items = []
    for fold in (*folds, selection_fold):
        fold_items.append({
            "name": fold.name, "fit_through": fold.fit_through,
            "evaluation_start": fold.acceptance_start, "evaluation_end": fold.acceptance_end,
            "fit": _membership(fold.fit), "evaluation": _membership(fold.acceptance),
            "policy_overlap": 0, "outcome_episode_overlap": 0,
            "latest_fit_horizon_end": max(row.horizon_end for row in fold.fit),
            "earliest_evaluation_cutoff": min(row.as_of for row in fold.acceptance),
        })
    lineage = {
        "r2_05_manifest_sha256": upstream_digest,
        "public_observations_sha256": public_digest,
        "feature_dictionary_sha256": dictionary_digest,
    }
    split = {
        "artifact_version": V2_SPLIT_VERSION, "phase": "R2-06", "lineage": lineage,
        "folds": fold_items, "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }
    fitted = fit_preprocessor(selection_fold)
    train = transform(fitted, selection_fold.fit, purpose="fit", role="fit")
    selection = transform(fitted, selection_fold.acceptance, purpose="selection", role="selection")
    feature = {
        "artifact_version": V2_FEATURE_PIPELINE_VERSION,
        "feature_dictionary_version": V2_FEATURE_DICTIONARY_VERSION,
        "lineage": {**lineage, "split_manifest_sha256": sha256(_json(split)).hexdigest()},
        "fit_membership_count": len(train.observation_ids),
        "selection_membership_count": len(selection.observation_ids),
        "output_feature_names": list(fitted.feature_names),
        "output_width": len(fitted.feature_names),
        "preprocessor_sha256": preprocessor_digest(fitted),
        "fit_matrix_sha256": matrix_digest(train),
        "selection_matrix_sha256": matrix_digest(selection),
        "numeric_state": [vars(item) for item in fitted.numeric],
        "categorical_state": [{"name": item.name, "categories": list(item.categories)} for item in fitted.categorical],
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }
    diagnostic = diagnostics(train, selection, fitted)
    diagnostic.update({"phase":"R2-06", "lineage": {**lineage, "feature_manifest_sha256": sha256(_json(feature)).hexdigest()},
                       "final_holdout_status": FINAL_HOLDOUT_STATUS})
    baseline = compare_baselines(train, selection, fitted)
    baseline.update({"phase":"R2-06", "artifact_version":V2_BASELINE_VERSION,
                     "lineage": {**lineage, "feature_manifest_sha256": sha256(_json(feature)).hexdigest()},
                     "final_holdout_status": FINAL_HOLDOUT_STATUS,
                     "claim_boundary":"synthetic_pipeline_engineering_only"})
    baseline = _portable_baseline_evidence(baseline)
    diagnostic = _round_floats(diagnostic, PORTABLE_ARTIFACT_DECIMALS)
    baseline = _round_floats(baseline, PORTABLE_ARTIFACT_DECIMALS)
    return {
        "split": _json(split), "feature": _json(feature), "diagnostic": _json(diagnostic),
        "diagnostic_report": _diagnostic_report(diagnostic).encode(), "baseline": _json(baseline),
        "baseline_report": _baseline_report(baseline).encode(),
    }


def _membership(rows) -> dict:
    labels = Counter(int(row.label_value) for row in rows)
    return {
        "observations": len(rows), "policies": len({row.policy_id for row in rows}),
        "negative": labels[0], "positive": labels[1],
        "billing_frequencies": sorted({row.features.billing_frequency for row in rows}),
        "membership_sha256": sha256("\n".join(row.observation_id for row in rows).encode()).hexdigest(),
    }


def _json(value: dict) -> bytes:
    def normalize(item):
        if isinstance(item, float):
            if not (-float("inf") < item < float("inf")):
                raise ValueError("non-finite artifact value")
            return round(item, 10)
        if isinstance(item, dict): return {key: normalize(value) for key, value in item.items()}
        if isinstance(item, (list, tuple)): return [normalize(value) for value in item]
        return item
    return (json.dumps(normalize(value), indent=2, sort_keys=True) + "\n").encode()


def _round_floats(value, decimals: int):
    if isinstance(value, float):
        rounded = round(value, decimals)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _round_floats(item, decimals) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round_floats(item, decimals) for item in value]
    return value


def _portable_baseline_evidence(value: dict) -> dict:
    """Remove platform-specific solver/tree bytes after runtime reload verification."""

    result = dict(value)
    logistic = dict(result["logistic"])
    logistic_state = logistic.pop("safe_fitted_state")
    logistic.pop("safe_fitted_state_sha256")
    logistic.pop("prediction_sha256")
    logistic["portable_fit_evidence"] = {
        "coefficient_count": len(logistic_state["coefficients"]),
        "feature_count": len(logistic_state["feature_names"]),
        "converged": logistic_state["iterations"] < 1000,
        "runtime_prediction_reload_verified": True,
    }
    boosted = dict(result["xgboost"])
    boosted_state = boosted.pop("safe_fitted_state")
    boosted.pop("safe_fitted_state_sha256")
    boosted.pop("prediction_sha256")
    boosted["portable_fit_evidence"] = {
        "trained_tree_count": boosted_state["trained_tree_count"],
        "expected_tree_count": 25,
        "native_state_format": "xgboost_json",
        "runtime_prediction_reload_verified": True,
        "committed_native_state": False,
        "reason": "Native fitted numeric bytes vary across supported operating systems; runtime reload is verified before portable evidence is emitted.",
    }
    result["logistic"] = logistic
    result["xgboost"] = boosted
    result["prediction_digest_boundary"] = {
        "runtime_verified": True,
        "committed": False,
        "reason": "Platform-specific fitted arithmetic is validated at runtime and excluded from cross-platform committed bytes.",
    }
    return result


def _diagnostic_report(value: dict) -> str:
    return "\n".join((
        "# Phase 2R.06 v2 Feature Diagnostics", "", f"Decision: `{value['decision']}`.", "",
        f"Mechanically flagged source groups: {len(value['flags'])}.",
        f"Disposition: `{value['decision']}` pending the predeclared R2-07 multi-seed gate.",
        "All four billing frequencies are present in fit and selection memberships.",
        "The final release holdout remains `not_materialized`.",
        "These deterministic synthetic diagnostics do not establish real-world performance.\n",
    ))


def _baseline_report(value: dict) -> str:
    lines = ["# Phase 2R.06 v2 Baseline Comparison", "", "Both frozen candidates use identical governed fit and selection memberships.", "",
             "| Model | Records | ROC AUC | Log loss | Brier score |", "| --- | ---: | ---: | ---: | ---: |"]
    for name in ("logistic", "xgboost"):
        metric = value[name]["metrics"]
        lines.append(f"| {name} | {metric['records']} | {metric['roc_auc']:.6f} | {metric['log_loss']:.6f} | {metric['brier_score']:.6f} |")
    lines.extend(("", "The comparison is synthetic pipeline-engineering evidence only.", "The final release holdout remains `not_materialized`.\n"))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    artifacts = build_artifacts()
    if args.check:
        stale = [key for key, path in FILES.items() if not path.exists() or path.read_bytes() != artifacts[key]]
        if stale:
            print(f"R2-06 artifacts are stale: {', '.join(stale)}", file=sys.stderr)
            return 1
        print("R2-06 v2 evaluation artifact reproducibility check: passed")
        return 0
    for key, path in FILES.items():
        path.write_bytes(artifacts[key])
        print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
