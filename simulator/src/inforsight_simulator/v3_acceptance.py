"""Governed R2-11 statistical acceptance primitives and decision aggregation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
import warnings
import xgboost as xgb
from xgboost import XGBClassifier

from .v3_config import primitive_uniform
from .v3_1_config import V31CorpusConfig
from .v3_evaluation import (
    RANDOM_SEED, V3Matrix, V3Preprocessor, authorize, matrix_digest,
    preprocessor_digest, validate_authorization,
)

R2_V3_ACCEPTANCE_VERSION = "1.0.0"
R2_V3_ACCEPTANCE_SEEDS = tuple(range(20261001, 20261021))
R2_V3_ACCEPTANCE_FOLDS = ("fold_1", "fold_2", "fold_3")
R2_V3_BOOTSTRAP_REPLICATES = 1000
FINAL_HOLDOUT_STATUS = "not_materialized"
_READINESS_FILES = {
    "support": "docs/experiments/phase-02r-10-v3-structural-support-3.2.0.json",
    "split": "docs/experiments/phase-02r-10-v3-split-manifest-3.2.0.json",
    "feature": "docs/experiments/phase-02r-10-v3-feature-pipeline-manifest-3.2.0.json",
    "diagnostic": "docs/experiments/phase-02r-10-v3-feature-diagnostics-manifest-3.2.0.json",
    "candidate": "docs/experiments/phase-02r-10-v3-candidate-selection-manifest-3.2.0.json",
}


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    family: str
    scope: str
    inputs: dict[str, Any]
    comparator: str
    threshold: Any
    observed: Any
    status: str
    failure_classification: str
    evidence_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in {"pass", "fail"}:
            raise ValueError("rule status must be pass or fail")
        if self.failure_classification not in {"redesign", "stop"}:
            raise ValueError("failure classification must be redesign or stop")
        if not self.rule_id or not self.family or not self.scope:
            raise ValueError("rule identity is incomplete")
        if not self.evidence_digests:
            raise ValueError("rule requires evidence")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_digests"] = list(self.evidence_digests)
        return value


@dataclass(frozen=True)
class AuthorizedPredictions:
    candidate: str
    model_sha256: str
    authorization_sha256: str
    observation_ids: tuple[str, ...]
    probabilities: tuple[float, ...]
    prediction_sha256: str


def aggregate_decision(results: Iterable[RuleResult]) -> str:
    items = tuple(results)
    if not items:
        return "redesign"
    failures = tuple(item for item in items if item.status == "fail")
    if any(item.failure_classification == "stop" for item in failures):
        return "stop"
    if failures:
        return "redesign"
    return "proceed"


def evaluate_readiness(root: Path) -> tuple[RuleResult, ...]:
    """Validate merged R2-10 authority without fitting or scoring."""

    payloads = {}
    digests = {}
    for name, relative in _READINESS_FILES.items():
        raw = (root / relative).read_bytes()
        payloads[name] = json.loads(raw)
        digests[name] = sha256(raw).hexdigest()
    rules = list(evaluate_readiness_payloads(payloads, digests))
    lineage = payloads["support"].get("lineage", {})
    protected = {
        "pre_amendment_failure_json_sha256":
            "docs/experiments/phase-02r-10-v3-structural-support.json",
        "pre_amendment_failure_markdown_sha256":
            "docs/experiments/phase-02r-10-v3-structural-support.md",
        "invalidated_v3_1_disposition_sha256":
            "docs/experiments/phase-02r-10-v3.1-pre-remediation-disposition.json",
        "r2_09_manifest_sha256":
            "docs/experiments/phase-02r-09-v3-corpus-manifest.json",
    }
    observed = {
        key: sha256((root / path).read_bytes()).hexdigest()
        for key, path in protected.items()
    }
    preserved = all(lineage.get(key) == digest for key, digest in observed.items())
    rules.append(RuleResult(
        "READINESS-HISTORICAL-IMMUTABILITY", "lineage", "r2-11-readiness", {},
        "equals", True, preserved, "pass" if preserved else "fail", "stop",
        tuple(observed.values()),
    ))
    corpus = json.loads((root / protected["r2_09_manifest_sha256"]).read_bytes())
    invariants = corpus.get("invariants", {})
    upstream_ok = (
        invariants.get("dual_time_visibility") == "tested"
        and invariants.get("event_first_generation") == "tested"
        and invariants.get("feature_lineage_complete") is True
        and invariants.get("oracle_sidecars_protected") is True
        and invariants.get("random_stream_registry") == "1.0.0"
    )
    rules.append(RuleResult(
        "READINESS-UPSTREAM-INVARIANTS", "lineage", "r2-11-readiness", {},
        "equals", True, invariants, "pass" if upstream_ok else "fail", "stop",
        (observed["r2_09_manifest_sha256"],),
    ))
    return tuple(rules)


def evaluate_readiness_payloads(payloads: dict[str, dict[str, Any]],
                                digests: dict[str, str]) -> tuple[RuleResult, ...]:
    """Pure readiness evaluation used by mutation tests."""

    missing = sorted(set(_READINESS_FILES) - set(payloads))
    if missing:
        raise ValueError(f"missing readiness payloads: {missing}")
    support, split = payloads["support"], payloads["split"]
    feature, diagnostic, candidate = (payloads[name] for name in
                                      ("feature", "diagnostic", "candidate"))
    evidence = tuple(digests[name] for name in sorted(_READINESS_FILES))
    rules = []

    def add(rule_id: str, family: str, observed: Any, passed: bool,
            classification: str = "redesign", threshold: Any = True) -> None:
        rules.append(RuleResult(rule_id, family, "r2-11-readiness", {}, "equals",
                                threshold, observed, "pass" if passed else "fail",
                                classification, evidence))

    versions = {
        "simulator": support.get("simulator_contract_version"),
        "evaluation": support.get("split_contract_version"),
        "protocol": support.get("acceptance_protocol_version"),
    }
    add("READINESS-VERSIONS", "lineage", versions,
        versions == {"simulator": "3.1.0", "evaluation": "3.2.0", "protocol": "2.2.0"})
    artifact_ids = {item.get("artifact_id") for item in payloads.values()}
    add("READINESS-ARTIFACT-IDENTITY", "lineage", sorted(str(x) for x in artifact_ids),
        len(artifact_ids) == 1 and None not in artifact_ids, "stop")

    memberships = {item.get("name"): item for item in support.get("memberships", [])}
    folds_ok = support.get("overall_status") == "pass" and all(
        memberships.get(name, {}).get("support_status") == "pass"
        for name in (*R2_V3_ACCEPTANCE_FOLDS, "selection")
    )
    add("READINESS-STRUCTURAL-SUPPORT", "support", support.get("overall_status"), folds_ok)
    acceptance_names = tuple(item.get("name") for item in split.get("acceptance_folds", []))
    boundaries_ok = acceptance_names == R2_V3_ACCEPTANCE_FOLDS and all(
        item.get("policy_overlap") == 0 and item.get("outcome_episode_overlap") == 0
        and item.get("latest_fit_horizon", "z") < item.get("earliest_evaluation_cutoff", "")
        for item in split.get("acceptance_folds", [])
    )
    add("READINESS-FOLD-BOUNDARIES", "chronology", list(acceptance_names), boundaries_ok,
        "stop")

    feature_ok = (feature.get("split_version") == "3.2.0"
                  and feature.get("fit_only_preprocessing") is True
                  and feature.get("unknown_category_path_frozen") is True
                  and feature.get("output_width") == len(feature.get("output_feature_names", []))
                  and len(feature.get("acceptance_fold_fit_preprocessor_sha256", {})) == 3)
    add("READINESS-FEATURE-PREPROCESSING", "features", feature_ok, feature_ok, "stop")
    diagnostic_ok = (diagnostic.get("decision") == "allow"
                     and diagnostic.get("strongest_group") == "recent_payment"
                     and diagnostic.get("designed_zero_group") == "missingness"
                     and set(diagnostic.get("driver_groups", {})) == {
                         "static", "recent_payment", "rolling_history",
                         "service_notice", "missingness",
                     })
    add("READINESS-DIAGNOSTICS", "features", diagnostic.get("decision"), diagnostic_ok)

    selection = candidate.get("selection", {})
    candidate_ok = (selection.get("selected_candidate") == "xgboost"
                    and selection.get("selected_model_sha256")
                    and selection.get("authorization_sha256")
                    and candidate.get("explicit_state_reload_verified") is True
                    and candidate.get("acceptance_protocol_version") == "2.2.0"
                    and candidate.get("split_version") == "3.2.0")
    add("READINESS-SELECTED-CANDIDATE", "model", selection, bool(candidate_ok), "stop")

    holdout_values = [item.get("final_holdout_status") for item in payloads.values()]
    materialized = any(
        value not in {None, "not_materialized", "not_created", "not_accessed",
                      "not_committed", "regenerated_not_committed"}
        for item in payloads.values() for value in item.get("materialization", {}).values()
        if "holdout" in str(value).lower()
    )
    holdout_ok = set(holdout_values) == {FINAL_HOLDOUT_STATUS} and not materialized
    add("READINESS-FINAL-HOLDOUT", "holdout", holdout_values, holdout_ok, "stop")
    add("READINESS-RUN-INVENTORY", "inventory",
        {"seeds": len(R2_V3_ACCEPTANCE_SEEDS), "folds": len(R2_V3_ACCEPTANCE_FOLDS)},
        len(R2_V3_ACCEPTANCE_SEEDS) == 20 and len(R2_V3_ACCEPTANCE_FOLDS) == 3)
    return tuple(rules)


def build_readiness_manifest(root: Path) -> dict[str, Any]:
    rules = evaluate_readiness(root)
    decision = aggregate_decision(rules)
    return {
        "phase": "R2-11",
        "issue": 64,
        "execution_version": R2_V3_ACCEPTANCE_VERSION,
        "simulator_contract_version": "3.1.0",
        "evaluation_contract_version": "3.2.0",
        "acceptance_protocol_version": "2.2.0",
        "readiness_status": "pass" if decision == "proceed" else "fail",
        "readiness_decision_if_failed": None if decision == "proceed" else decision,
        "result_producing_execution_authorized": decision == "proceed",
        "planned_inventory": {
            "seeds": list(R2_V3_ACCEPTANCE_SEEDS),
            "folds": list(R2_V3_ACCEPTANCE_FOLDS),
            "signal_replications": 20,
            "matched_null_replications": 20,
        },
        "rules": [item.to_dict() for item in rules],
        "acceptance_results_generated": False,
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }


def fit_authorized_candidates(train: V3Matrix, evaluation: V3Matrix,
                              fitted: V3Preprocessor, *,
                              candidates: Sequence[str] = ("logistic", "xgboost"),
                              ) -> tuple[AuthorizedPredictions, ...]:
    """Fit frozen specifications and score one exact authorized membership in memory."""

    if train.purpose != "fit" or train.role != "fit":
        raise ValueError("candidate fitting requires a governed fit matrix")
    if evaluation.purpose != "acceptance" or evaluation.role != "acceptance":
        raise ValueError("R2-11 scoring requires an acceptance matrix")
    if tuple(candidates) not in (("logistic",), ("xgboost",), ("logistic", "xgboost")):
        raise ValueError("candidate set is not frozen")
    outputs = []
    for name in candidates:
        if name == "logistic":
            model = LogisticRegression(
                penalty="l2", C=1.0, solver="liblinear", tol=1e-8,
                max_iter=1000, fit_intercept=True, class_weight=None,
                random_state=RANDOM_SEED,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                model.fit(train.values, train.targets)
            probabilities = tuple(float(value) for value in
                                  model.predict_proba(evaluation.values)[:, 1])
            state = {
                "candidate": name,
                "feature_names": list(train.feature_names),
                "intercept": float(model.intercept_[0]),
                "coefficients": [float(value) for value in model.coef_[0]],
                "iterations": int(model.n_iter_[0]),
            }
        else:
            model = XGBClassifier(
                objective="binary:logistic", n_estimators=25, learning_rate=0.1,
                max_depth=2, min_child_weight=2.0, gamma=0.0, subsample=1.0,
                colsample_bytree=1.0, colsample_bylevel=1.0,
                colsample_bynode=1.0, reg_alpha=0.0, reg_lambda=1.0,
                scale_pos_weight=1.0, base_score=0.5, tree_method="exact",
                n_jobs=1, random_state=RANDOM_SEED, eval_metric="logloss",
                verbosity=0,
            )
            model.fit(train.values, train.targets, verbose=False)
            probabilities = tuple(float(value) for value in
                                  model.predict_proba(evaluation.values)[:, 1])
            native = bytes(model.get_booster().save_raw(raw_format="json"))
            state = {
                "candidate": name,
                "feature_names": list(train.feature_names),
                "model_json_sha256": sha256(native).hexdigest(),
                "trained_tree_count": len(model.get_booster().get_dump()),
            }
        if not probabilities or any(not math.isfinite(value) or value < 0 or value > 1
                                    for value in probabilities):
            raise ValueError("candidate produced invalid probabilities")
        model_sha = sha256(json.dumps(state, allow_nan=False, sort_keys=True,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()
        authority = authorize(train, evaluation, fitted, model_sha256=model_sha)
        validate_authorization(
            authority, evaluation, fit_matrix_sha256=matrix_digest(train),
            preprocessor_sha256=preprocessor_digest(fitted), model_sha256=model_sha,
        )
        prediction_sha = sha256(json.dumps(
            list(zip(evaluation.observation_ids, probabilities, strict=True)),
            allow_nan=False, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        outputs.append(AuthorizedPredictions(
            name, model_sha, authority.authorization_sha256,
            evaluation.observation_ids, probabilities, prediction_sha,
        ))
    return tuple(outputs)


def roc_auc(targets: Sequence[int], probabilities: Sequence[float]) -> float:
    _validate_scores(targets, probabilities)
    positives = sum(targets)
    negatives = len(targets) - positives
    if not positives or not negatives:
        raise ValueError("ROC AUC requires both classes")
    ordered = sorted(zip(probabilities, targets), key=lambda item: item[0])
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        rank_sum += average_rank * sum(label for _, label in ordered[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def brier_score(targets: Sequence[int], probabilities: Sequence[float]) -> float:
    _validate_scores(targets, probabilities)
    return sum((label - probability) ** 2 for label, probability in zip(
        targets, probabilities, strict=True,
    )) / len(targets)


def average_precision(targets: Sequence[int], probabilities: Sequence[float]) -> float:
    _validate_scores(targets, probabilities)
    positives = sum(targets)
    if not positives:
        raise ValueError("average precision requires a positive class")
    ordered = sorted(zip(probabilities, targets), key=lambda item: item[0], reverse=True)
    found = 0
    total = 0.0
    for rank, (_, label) in enumerate(ordered, 1):
        if label:
            found += 1
            total += found / rank
    return total / positives


def policy_label_shuffle(config: V31CorpusConfig, *, seed: int, fold: str,
                         policy_ids: Sequence[str], targets: Sequence[int]) -> tuple[int, ...]:
    """Assign whole ordered policy label vectors through the frozen cyclic shuffle."""

    if len(policy_ids) != len(targets) or not policy_ids:
        raise ValueError("shuffle membership must be non-empty and aligned")
    vectors: dict[str, list[int]] = {}
    positions: dict[str, list[int]] = {}
    for index, (policy, label) in enumerate(zip(policy_ids, targets, strict=True)):
        if label not in {0, 1}:
            raise ValueError("shuffle targets must be binary")
        vectors.setdefault(policy, []).append(label)
        positions.setdefault(policy, []).append(index)
    policies = tuple(sorted(vectors, key=lambda policy: (
        primitive_uniform(config, "label_shuffle", seed, fold, policy), policy,
    )))
    if len(policies) < 2:
        raise ValueError("shuffle requires at least two policies")
    rotation_uniform = primitive_uniform(config, "label_shuffle", seed, fold, "rotation")
    rotation = 1 + math.floor(rotation_uniform * (len(policies) - 1))
    output = [0] * len(targets)
    for position, recipient in enumerate(policies):
        donor = policies[(position + rotation) % len(policies)]
        donor_labels = vectors[donor]
        for offset, row_index in enumerate(positions[recipient]):
            output[row_index] = donor_labels[offset % len(donor_labels)]
    return tuple(output)


def policy_cluster_interval(config: V31CorpusConfig, *, seed: int, fold: str,
                            metric: str, policy_ids: Sequence[str],
                            targets: Sequence[int], probabilities: Sequence[float],
                            replicates: int = R2_V3_BOOTSTRAP_REPLICATES,
                            ) -> tuple[tuple[float, float], int]:
    """Return the frozen percentile interval and retained valid replicate count."""

    _validate_scores(targets, probabilities)
    if len(policy_ids) != len(targets):
        raise ValueError("bootstrap membership is not aligned")
    unique = tuple(sorted(set(policy_ids)))
    rows = {policy: [] for policy in unique}
    for index, policy in enumerate(policy_ids):
        rows[policy].append(index)
    function = {"roc_auc": roc_auc, "brier_score": brier_score}.get(metric)
    if function is None:
        raise ValueError("unsupported bootstrap metric")
    values = []
    for replicate in range(replicates):
        sampled = bootstrap_policy_indices(
            config, seed=seed, fold=fold, metric=metric, replicate=replicate,
            policy_ids=unique,
        )
        indices = [row for sampled_index in sampled for row in rows[unique[sampled_index]]]
        sample_targets = tuple(targets[index] for index in indices)
        sample_probabilities = tuple(probabilities[index] for index in indices)
        try:
            value = function(sample_targets, sample_probabilities)
        except ValueError:
            continue
        if math.isfinite(value):
            values.append(value)
    if replicates == R2_V3_BOOTSTRAP_REPLICATES and len(values) < 950:
        raise ValueError("fewer than 950 valid bootstrap replicates")
    return percentile_interval(values), len(values)


def percentile_interval(values: Sequence[float]) -> tuple[float, float]:
    if len(values) < 1 or not all(math.isfinite(value) for value in values):
        raise ValueError("interval values must be finite and non-empty")
    ordered = sorted(values)
    last = len(ordered) - 1
    return ordered[math.floor(0.025 * last)], ordered[math.ceil(0.975 * last)]


def bootstrap_policy_indices(config: V31CorpusConfig, *, seed: int, fold: str,
                             metric: str, replicate: int,
                             policy_ids: Sequence[str]) -> tuple[int, ...]:
    unique = tuple(sorted(set(policy_ids)))
    if not unique:
        raise ValueError("bootstrap requires policies")
    sampled = []
    for draw in range(len(unique)):
        uniform = primitive_uniform(config, "bootstrap", seed, fold, metric, replicate, draw)
        sampled.append(math.floor(uniform * len(unique)))
    return tuple(sampled)


def _validate_scores(targets: Sequence[int], probabilities: Sequence[float]) -> None:
    if not targets or len(targets) != len(probabilities):
        raise ValueError("targets and probabilities must be non-empty and aligned")
    if any(label not in {0, 1} for label in targets):
        raise ValueError("targets must be binary")
    if any(not math.isfinite(value) or value < 0 or value > 1 for value in probabilities):
        raise ValueError("probabilities must be finite values in [0, 1]")
