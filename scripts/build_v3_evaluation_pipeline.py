#!/usr/bin/env python3
"""Build or verify deterministic R2-10 v3.2 evaluation artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v3_1_config import (  # noqa: E402
    V31_SIMULATOR_CONTRACT_VERSION, V31CorpusConfig,
)
from inforsight_simulator.v3_1_corpus import generate_v3_corpus  # noqa: E402
from inforsight_simulator.v3_evaluation import (  # noqa: E402
    PORTABLE_ARTIFACT_DECIMALS, V3_CANDIDATE_SELECTION_MEMBERSHIP_VERSION,
    V3_CANDIDATE_VERSION, V3_DIAGNOSTIC_VERSION,
    V3_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION, V3_FEATURE_DICTIONARY_VERSION,
    V3_FEATURE_PIPELINE_VERSION, V3_FINAL_HOLDOUT_STATUS, V3_SPLIT_VERSION,
    V3_STRUCTURAL_SUPPORT_VERSION, build_selection_fold, build_temporal_folds,
    compare_candidates, diagnostics, fit_preprocessor, matrix_digest,
    preprocessor_digest, structural_support_report, transform,
)


EXPERIMENTS = ROOT / "docs" / "experiments"
FILES = {
    "support": EXPERIMENTS / "phase-02r-10-v3-structural-support-3.2.0.json",
    "support_report": EXPERIMENTS / "phase-02r-10-v3-structural-support-3.2.0.md",
    "split": EXPERIMENTS / "phase-02r-10-v3-split-manifest-3.2.0.json",
    "feature": EXPERIMENTS / "phase-02r-10-v3-feature-pipeline-manifest-3.2.0.json",
    "diagnostic": EXPERIMENTS / "phase-02r-10-v3-feature-diagnostics-manifest-3.2.0.json",
    "diagnostic_report": EXPERIMENTS / "phase-02r-10-v3-feature-diagnostics-report-3.2.0.md",
    "candidate": EXPERIMENTS / "phase-02r-10-v3-candidate-selection-manifest-3.2.0.json",
    "candidate_report": EXPERIMENTS / "phase-02r-10-v3-candidate-selection-report-3.2.0.md",
}
FEATURE_DICTIONARY = ROOT / "docs/modeling/phase-02r-10-v3-feature-dictionary.json"
UPSTREAM = EXPERIMENTS / "phase-02r-09-v3-corpus-manifest.json"
PRE_AMENDMENT = EXPERIMENTS / "phase-02r-10-v3-structural-support.json"
PRE_AMENDMENT_REPORT = EXPERIMENTS / "phase-02r-10-v3-structural-support.md"
INVALIDATED_ATTEMPT = EXPERIMENTS / "phase-02r-10-v3.1-pre-remediation-disposition.json"


def build_artifacts() -> dict[str, bytes]:
    corpus = generate_v3_corpus(V31CorpusConfig())
    support = structural_support_report(corpus.observations)
    if support["overall_status"] != "pass":
        raise ValueError("v3.2 structural support must pass before evaluation artifacts")
    folds = build_temporal_folds(corpus.observations)
    selection_fold = build_selection_fold(corpus.observations)
    fitted = fit_preprocessor(selection_fold)
    train = transform(fitted, selection_fold.fit, purpose="fit", role="fit")
    selection = transform(
        fitted, selection_fold.evaluation, purpose="selection", role="selection",
    )
    diagnostic = diagnostics(train, selection, fitted)
    if diagnostic["decision"] != "allow":
        raise ValueError("v3 diagnostics did not authorize candidate comparison")
    candidate = compare_candidates(train, selection, fitted)
    source_digest = sha256(b"".join(
        (ROOT / path).read_bytes() for path in (
            "simulator/src/inforsight_simulator/v3_evaluation.py",
            "simulator/src/inforsight_simulator/v3_1_config.py",
            "simulator/src/inforsight_simulator/v3_1_corpus.py",
            "scripts/build_v3_evaluation_pipeline.py",
        )
    )).hexdigest()
    lineage = {
        "r2_09_manifest_sha256": sha256(UPSTREAM.read_bytes()).hexdigest(),
        "pre_amendment_failure_json_sha256": sha256(PRE_AMENDMENT.read_bytes()).hexdigest(),
        "pre_amendment_failure_markdown_sha256": sha256(
            PRE_AMENDMENT_REPORT.read_bytes()
        ).hexdigest(),
        "invalidated_v3_1_disposition_sha256": sha256(
            INVALIDATED_ATTEMPT.read_bytes()
        ).hexdigest(),
        "feature_dictionary_sha256": sha256(FEATURE_DICTIONARY.read_bytes()).hexdigest(),
        "source_sha256": source_digest,
        "dependency_lock_sha256": sha256(
            (ROOT / "simulator/pyproject.toml").read_bytes()
        ).hexdigest(),
        "command_sha256": sha256(
            b"python3 scripts/build_v3_evaluation_pipeline.py --write\n"
        ).hexdigest(),
    }
    support.update({
        "issue": 59, "decision_issue": 60, "remediation_issue": 61,
        "simulator_contract_version": V31_SIMULATOR_CONTRACT_VERSION,
        "lineage": lineage,
        "acceptance_protocol_version": V3_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION,
        "materialization": _materialization(),
    })
    split = {
        "artifact_version": V3_SPLIT_VERSION,
        "candidate_selection_membership_version": V3_CANDIDATE_SELECTION_MEMBERSHIP_VERSION,
        "acceptance_protocol_version": V3_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION,
        "phase": "R2-10", "artifact_id": corpus.provenance["artifact_id"],
        "lineage": lineage,
        "selection": _fold_summary(selection_fold),
        "acceptance_folds": [_fold_summary(fold) for fold in folds],
        "pre_amendment_evidence": {
            "status": "immutable_failure",
            "eligible_selection_observations": 467,
            "json_sha256": lineage["pre_amendment_failure_json_sha256"],
            "markdown_sha256": lineage["pre_amendment_failure_markdown_sha256"],
        },
        "invalidated_v3_1_attempt": {
            "status": "historical_failed_attempt",
            "disposition_sha256": lineage["invalidated_v3_1_disposition_sha256"],
        },
        "claim_boundary": "role_isolated_synthetic_recovery_not_prospective_backtest",
        "final_holdout_status": V3_FINAL_HOLDOUT_STATUS,
    }
    fold_preprocessors = {fold.name: preprocessor_digest(fit_preprocessor(fold)) for fold in folds}
    feature = {
        "artifact_version": V3_FEATURE_PIPELINE_VERSION,
        "feature_dictionary_version": V3_FEATURE_DICTIONARY_VERSION,
        "split_version": V3_SPLIT_VERSION,
        "artifact_id": corpus.provenance["artifact_id"],
        "lineage": {**lineage, "split_manifest_sha256": sha256(_json(split)).hexdigest()},
        "fit_membership_count": len(train.observation_ids),
        "selection_membership_count": len(selection.observation_ids),
        "fit_unique_policies": len(set(train.policy_ids)),
        "selection_unique_policies": len(set(selection.policy_ids)),
        "output_feature_names": list(fitted.feature_names),
        "output_width": len(fitted.feature_names),
        "preprocessor_sha256": preprocessor_digest(fitted),
        "acceptance_fold_fit_preprocessor_sha256": fold_preprocessors,
        "fit_matrix_sha256": matrix_digest(train),
        "selection_matrix_sha256": matrix_digest(selection),
        "numeric_state": [asdict_without_type(item) for item in fitted.numeric],
        "categorical_state": [
            {"name": item.name, "categories": list(item.categories)}
            for item in fitted.categorical
        ],
        "fit_only_preprocessing": True,
        "unknown_category_path_frozen": True,
        "materialization": _materialization(),
        "final_holdout_status": V3_FINAL_HOLDOUT_STATUS,
    }
    feature = _portable(feature)
    diagnostic.update({
        "phase": "R2-10", "artifact_version": V3_DIAGNOSTIC_VERSION,
        "artifact_id": corpus.provenance["artifact_id"],
        "lineage": {
            **lineage, "feature_manifest_sha256": sha256(_json(feature)).hexdigest(),
        },
        "final_holdout_status": V3_FINAL_HOLDOUT_STATUS,
    })
    candidate.update({
        "phase": "R2-10", "artifact_version": V3_CANDIDATE_VERSION,
        "split_version": V3_SPLIT_VERSION,
        "acceptance_protocol_version": V3_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION,
        "artifact_id": corpus.provenance["artifact_id"],
        "lineage": {
            **lineage, "feature_manifest_sha256": sha256(_json(feature)).hexdigest(),
            "diagnostic_manifest_sha256": sha256(_json(_portable(diagnostic))).hexdigest(),
        },
        "claim_boundary": "synthetic_candidate_selection_only",
        "final_holdout_status": V3_FINAL_HOLDOUT_STATUS,
    })
    candidate = _portable_candidate(candidate)
    support = _portable(support)
    diagnostic = _portable(diagnostic)
    candidate = _portable(candidate)
    return {
        "support": _json(support),
        "support_report": _support_report(support).encode("utf-8"),
        "split": _json(split), "feature": _json(feature),
        "diagnostic": _json(diagnostic),
        "diagnostic_report": _diagnostic_report(diagnostic).encode("utf-8"),
        "candidate": _json(candidate),
        "candidate_report": _candidate_report(candidate).encode("utf-8"),
    }


def asdict_without_type(value) -> dict:
    return {name: getattr(value, name) for name in value.__dataclass_fields__}


def _fold_summary(fold) -> dict:
    return {
        "name": fold.name, "fit_through": fold.fit_through,
        "evaluation_start": fold.evaluation_start, "evaluation_end": fold.evaluation_end,
        "fit": _membership(fold.fit), "evaluation": _membership(fold.evaluation),
        "latest_fit_horizon": max(row.horizon_end for row in fold.fit),
        "earliest_evaluation_cutoff": min(row.as_of for row in fold.evaluation),
        "policy_overlap": len({row.policy_id for row in fold.fit} & {row.policy_id for row in fold.evaluation}),
        "outcome_episode_overlap": len(
            {row.outcome_episode_id for row in fold.fit}
            & {row.outcome_episode_id for row in fold.evaluation}
        ),
    }


def _membership(rows) -> dict:
    labels = Counter(row.label_value for row in rows)
    return {
        "observations": len(rows), "policies": len({row.policy_id for row in rows}),
        "negative": labels[0], "positive": labels[1],
        "billing_frequency": dict(sorted(Counter(
            row.features.billing_frequency for row in rows
        ).items())),
        "membership_sha256": sha256(
            ("\n".join(row.observation_id for row in rows) + "\n").encode("utf-8")
        ).hexdigest(),
    }


def _materialization() -> dict:
    return {
        "raw_observations": "regenerated_not_committed",
        "feature_matrices": "regenerated_not_committed",
        "row_level_predictions": "not_committed",
        "executable_fitted_objects": "not_committed",
        "oracle_sidecars": "not_accessed",
        "acceptance_predictions": "not_created",
        "acceptance_metrics": "not_created",
        "final_holdout": "not_materialized",
    }


def _portable_candidate(value: dict) -> dict:
    result = dict(value)
    for name in ("logistic", "xgboost"):
        item = dict(result[name])
        state = item.pop("safe_fitted_state")
        item.pop("prediction_sha256")
        item["portable_fit_evidence"] = {
            "state_sha256": item.pop("safe_fitted_state_sha256"),
            "feature_count": len(state["feature_names"]),
            "runtime_prediction_reload_verified": True,
            "committed_executable_state": False,
        }
        result[name] = item
    result["prediction_boundary"] = {
        "runtime_verified": True, "row_level_predictions_committed": False,
    }
    return result


def _portable(value):
    if isinstance(value, float):
        rounded = round(value, PORTABLE_ARTIFACT_DECIMALS)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _portable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable(item) for item in value]
    return value


def _json(value: dict) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n"


def _support_report(value: dict) -> str:
    lines = [
        "# Phase 2R.10 v3.2 Structural Support", "",
        f"Overall status: `{value['overall_status']}`.", "",
        "| Membership | Role | Eligible | Policies | Positive | Negative | Censored | Status |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in value["memberships"]:
        evaluation = item["evaluation"]
        lines.append(
            f"| {item['name']} | {item['evaluation_role']} | "
            f"{evaluation['eligible_uncensored_observations']} | {evaluation['unique_policies']} | "
            f"{evaluation['positive']} | {evaluation['negative']} | "
            f"{evaluation['right_censored_observations']} | {item['support_status']} |"
        )
    lines.extend((
        "", "Selection may use repeated non-overlapping episodes; they do not increase independent-policy capacity.",
        "", "This is role-isolated synthetic recovery evidence, not a prospective real-world backtest.",
        "", "No acceptance prediction, acceptance metric, oracle access, or final holdout exists.", "",
    ))
    return "\n".join(lines)


def _diagnostic_report(value: dict) -> str:
    return "\n".join((
        "# Phase 2R.10 v3.2 Feature Diagnostics", "",
        f"Decision: `{value['decision']}`.", "",
        f"Flags with explicit dispositions: {len(value['flags'])}.",
        "The strongest group remains `recent_payment`; the designed-zero group remains `missingness`.",
        "Missingness findings are associative synthetic diagnostics and are not causal.",
        "No acceptance role or final holdout was scored.", "",
    ))


def _candidate_report(value: dict) -> str:
    lines = [
        "# Phase 2R.10 v3.2 Candidate Selection", "",
        "Both frozen candidates use identical governed fit and selection memberships.", "",
        "| Candidate | Records | ROC AUC | Brier | Log loss |", "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in ("logistic", "xgboost"):
        metrics = value[name]["metrics"]
        lines.append(
            f"| {name} | {metrics['records']} | {metrics['roc_auc']:.4f} | "
            f"{metrics['brier_score']:.4f} | {metrics['log_loss']:.4f} |"
        )
    lines.extend((
        "", f"Selected candidate: `{value['selection']['selected_candidate']}` "
        f"by `{value['selection']['reason']}`.", "",
        "This is synthetic candidate-selection evidence only. No acceptance or final-holdout result was created.", "",
    ))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build_artifacts()
    if args.write:
        EXPERIMENTS.mkdir(parents=True, exist_ok=True)
        for key, path in FILES.items():
            path.write_bytes(artifacts[key])
            print(f"Wrote {path.relative_to(ROOT)}")
        return 0
    stale = [key for key, path in FILES.items()
             if not path.exists() or path.read_bytes() != artifacts[key]]
    if stale:
        print(f"R2-10 v3.2 artifacts are missing or stale: {', '.join(stale)}", file=sys.stderr)
        return 1
    print("R2-10 v3.2 evaluation artifact reproducibility check: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
