#!/usr/bin/env python3
"""Build or verify deterministic R2-15 Generation v6 evaluation artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulator" / "src"))

from inforsight_simulator.v6_config import (  # noqa: E402
    V6_SIMULATOR_CONTRACT_VERSION, V6CorpusConfig,
)
from inforsight_simulator.v6_corpus import generate_v6_corpus  # noqa: E402
from inforsight_simulator.v6_evaluation import (  # noqa: E402
    PORTABLE_ARTIFACT_DECIMALS, V6_CANDIDATE_SELECTION_MEMBERSHIP_VERSION,
    V6_CANDIDATE_VERSION, V6_DIAGNOSTIC_VERSION,
    V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION, V6_FEATURE_DICTIONARY_VERSION,
    V6_FEATURE_PIPELINE_VERSION, V6_FINAL_HOLDOUT_STATUS, V6_SPLIT_VERSION,
    V6_STRUCTURAL_SUPPORT_VERSION, build_selection_fold, build_temporal_folds,
    compare_candidates, diagnostics, fit_preprocessor, matrix_digest,
    preprocessor_digest, structural_support_report, transform,
)


EXPERIMENTS = ROOT / "docs" / "experiments"
FILES = {
    "support": EXPERIMENTS / "phase-02r-15-v6-structural-support.json",
    "support_report": EXPERIMENTS / "phase-02r-15-v6-structural-support.md",
    "split": EXPERIMENTS / "phase-02r-15-v6-split-manifest.json",
    "feature": EXPERIMENTS / "phase-02r-15-v6-feature-pipeline-manifest.json",
    "diagnostic": EXPERIMENTS / "phase-02r-15-v6-feature-diagnostics-manifest.json",
    "diagnostic_report": EXPERIMENTS / "phase-02r-15-v6-feature-diagnostics-report.md",
    "candidate": EXPERIMENTS / "phase-02r-15-v6-candidate-selection-manifest.json",
    "candidate_report": EXPERIMENTS / "phase-02r-15-v6-candidate-selection-report.md",
}
FEATURE_DICTIONARY = ROOT / "docs/modeling/phase-02r-15-v6-feature-dictionary.json"
UPSTREAM = EXPERIMENTS / "phase-02r-14d-v6-qualification-manifest.json"
SUBSTRATE_CONTRACT = ROOT / "docs/modeling/phase-02r-14c-v6-bounded-sigmoid-substrate-contract.md"
ADR_0012 = ROOT / "docs/adr/0012-authorize-bounded-sigmoid-hazard-link-v6.md"
EVALUATION_CONTRACT = ROOT / "docs/modeling/phase-02r-15-v6-evaluation-pipeline-contract.md"


def build_artifacts() -> dict[str, bytes]:
    corpus = generate_v6_corpus(V6CorpusConfig(base_seed=20280201))
    support = structural_support_report(corpus.observations)
    if support["overall_status"] != "pass":
        raise ValueError("v6 structural support must pass before evaluation artifacts")
    folds = build_temporal_folds(corpus.observations)
    selection_fold = build_selection_fold(corpus.observations)
    fitted = fit_preprocessor(selection_fold)
    train = transform(fitted, selection_fold.fit, purpose="fit", role="fit")
    selection = transform(
        fitted, selection_fold.evaluation, purpose="selection", role="selection",
    )
    diagnostic = diagnostics(train, selection, fitted)
    if diagnostic["decision"] != "allow":
        raise ValueError("v6 diagnostics did not authorize candidate comparison")
    candidate = compare_candidates(train, selection, fitted)
    source_digest = sha256(b"".join(
        (ROOT / path).read_bytes() for path in (
            "simulator/src/inforsight_simulator/v6_evaluation.py",
            "simulator/src/inforsight_simulator/v6_config.py",
            "simulator/src/inforsight_simulator/v6_corpus.py",
            "scripts/build_v6_evaluation_pipeline.py",
        )
    )).hexdigest()
    lineage = {
        "upstream_qualification_manifest_sha256": sha256(UPSTREAM.read_bytes()).hexdigest(),
        "substrate_contract_sha256": sha256(SUBSTRATE_CONTRACT.read_bytes()).hexdigest(),
        "adr_0012_sha256": sha256(ADR_0012.read_bytes()).hexdigest(),
        "evaluation_contract_sha256": sha256(EVALUATION_CONTRACT.read_bytes()).hexdigest(),
        "feature_dictionary_sha256": sha256(FEATURE_DICTIONARY.read_bytes()).hexdigest(),
        "source_sha256": source_digest,
        "dependency_lock_sha256": sha256(
            (ROOT / "simulator/pyproject.toml").read_bytes()
        ).hexdigest(),
        "command_sha256": sha256(
            b"python3 scripts/build_v6_evaluation_pipeline.py --write\n"
        ).hexdigest(),
    }
    support.update({
        "issue": 90,
        "simulator_contract_version": V6_SIMULATOR_CONTRACT_VERSION,
        "lineage": lineage,
        "acceptance_protocol_version": V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION,
        "materialization": _materialization(),
    })
    split = {
        "artifact_version": V6_SPLIT_VERSION,
        "candidate_selection_membership_version": V6_CANDIDATE_SELECTION_MEMBERSHIP_VERSION,
        "acceptance_protocol_version": V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION,
        "phase": "R2-15",
        "artifact_id": corpus.provenance["artifact_id"],
        "lineage": lineage,
        "selection": _fold_summary(selection_fold),
        "acceptance_folds": [_fold_summary(fold) for fold in folds],
        "claim_boundary": "role_isolated_synthetic_recovery_not_prospective_backtest",
        "final_holdout_status": V6_FINAL_HOLDOUT_STATUS,
    }
    fold_preprocessors = {fold.name: preprocessor_digest(fit_preprocessor(fold)) for fold in folds}
    feature = {
        "artifact_version": V6_FEATURE_PIPELINE_VERSION,
        "feature_dictionary_version": V6_FEATURE_DICTIONARY_VERSION,
        "split_version": V6_SPLIT_VERSION,
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
        "final_holdout_status": V6_FINAL_HOLDOUT_STATUS,
    }
    feature = _portable(feature)
    diagnostic.update({
        "phase": "R2-15",
        "artifact_version": V6_DIAGNOSTIC_VERSION,
        "artifact_id": corpus.provenance["artifact_id"],
        "lineage": {
            **lineage, "feature_manifest_sha256": sha256(_json(feature)).hexdigest(),
        },
        "final_holdout_status": V6_FINAL_HOLDOUT_STATUS,
    })
    candidate.update({
        "phase": "R2-15",
        "artifact_version": V6_CANDIDATE_VERSION,
        "split_version": V6_SPLIT_VERSION,
        "acceptance_protocol_version": V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION,
        "artifact_id": corpus.provenance["artifact_id"],
        "lineage": {
            **lineage, "feature_manifest_sha256": sha256(_json(feature)).hexdigest(),
            "diagnostic_manifest_sha256": sha256(_json(_portable(diagnostic))).hexdigest(),
        },
        "claim_boundary": "synthetic_candidate_selection_only",
        "final_holdout_status": V6_FINAL_HOLDOUT_STATUS,
    })
    candidate = _portable_candidate(candidate)
    support = _portable(support)
    diagnostic = _portable(diagnostic)
    candidate = _portable(candidate)
    return {
        "support": _json(support),
        "support_report": _support_report(support).encode("utf-8"),
        "split": _json(split),
        "feature": _json(feature),
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
    logistic = dict(result["logistic"])
    logistic_state = logistic.pop("safe_fitted_state")
    logistic.pop("prediction_sha256")
    logistic["portable_fit_evidence"] = {
        "state_sha256": logistic.pop("safe_fitted_state_sha256"),
        "feature_count": len(logistic_state["feature_names"]),
        "runtime_prediction_reload_verified": True,
        "committed_executable_state": False,
    }
    boosted = dict(result["xgboost"])
    boosted_state = boosted.pop("safe_fitted_state")
    boosted.pop("safe_fitted_state_sha256")
    boosted.pop("prediction_sha256")
    boosted["portable_fit_evidence"] = {
        "feature_count": len(boosted_state["feature_names"]),
        "trained_tree_count": boosted_state["trained_tree_count"],
        "runtime_prediction_reload_verified": True,
        "committed_executable_state": False,
        "reason": (
            "Native fitted numeric bytes vary across supported operating systems; "
            "runtime reload is verified before portable evidence is emitted."
        ),
    }
    result["logistic"] = logistic
    result["xgboost"] = boosted
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
        "# Phase 2R.15 Generation v6 Structural Support", "",
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
        "# Phase 2R.15 Generation v6 Feature Diagnostics", "",
        f"Decision: `{value['decision']}`.", "",
        f"Flags with explicit dispositions: {len(value['flags'])}.",
        "The strongest group remains `recent_payment`; the designed-zero group remains `missingness`.",
        "Missingness findings are associative synthetic diagnostics and are not causal.",
        "No acceptance role or final holdout was scored.", "",
    ))


def _candidate_report(value: dict) -> str:
    lines = [
        "# Phase 2R.15 Generation v6 Candidate Selection", "",
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
        print(f"R2-15 v6 artifacts are missing or stale: {', '.join(stale)}", file=sys.stderr)
        import difflib
        for key in stale:
            path = FILES[key]
            if path.exists():
                committed = path.read_text("utf-8").splitlines()
                generated = artifacts[key].decode("utf-8").splitlines()
                diff = "\n".join(difflib.unified_diff(
                    committed, generated, fromfile=f"committed:{key}", tofile=f"generated:{key}",
                ))
                print(f"--- Diff for {key} ---\n{diff}\n--- End diff ---", file=sys.stderr)
        return 1
    print("R2-15 Generation v6 evaluation artifact reproducibility check: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
