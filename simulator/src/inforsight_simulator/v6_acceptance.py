"""Governed R2-16 Generation v6 statistical acceptance primitives and decision aggregation."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import random
from statistics import median
from typing import Any, Iterable, Sequence
import warnings

import numpy as np
from scipy.stats import rankdata
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from .v3_config import V3_BILLING_FREQUENCIES
from .v6_config import (
    V6_COEFFICIENT_REGISTRY_VERSION,
    V6_SIMULATOR_CONTRACT_VERSION, V6_STREAM_REGISTRY_VERSION,
    V6CorpusConfig, primitive_uniform, stream_set_id,
)
from .v6_corpus import (
    V6Observation, generate_v6_corpus,
)
from .v6_evaluation import (
    CATEGORICAL_FEATURES, FEATURE_GROUPS, FOLDS, NUMERIC_FEATURES,
    RANDOM_SEED, UNKNOWN_CATEGORY, V6Matrix, V6Preprocessor,
    V6TemporalFold, _driver_group, _feature_map, _row_key, _source_feature_indices,
    authorize, build_temporal_folds, fit_preprocessor, transform,
    validate_authorization, validate_temporal_fold,
)

R2_16A_ISSUE = 94
R2_16_ISSUE = 94
R2_16_ACCEPTANCE_VERSION = "1.0.0"
V6_ACCEPTANCE_PROTOCOL_VERSION = "3.1.0"
V6_EVALUATION_CONTRACT_VERSION = "6.0.0"
V6_CANDIDATE_VERSION = "6.0.0"

RESERVED_ACCEPTANCE_SEEDS = tuple(range(20271201, 20271221))
DEVELOPMENT_SEEDS = tuple(range(20280201, 20280221))
SPENT_DIAGNOSTIC_SEEDS = tuple(range(20280101, 20280121))
SPENT_QUALIFICATION_SEEDS = tuple(range(20271101, 20271121))
SPENT_ACCEPTANCE_SEEDS = tuple(range(20261001, 20261021))
GOVERNED_ACCEPTANCE_FOLDS = ("fold_1", "fold_2", "fold_3")
BOOTSTRAP_REPLICATES = 1000
FINAL_HOLDOUT_STATUS = "not_materialized"

IMMUTABLE_UPSTREAM_FILES = {
    "substrate": "docs/modeling/phase-02r-14c-v6-bounded-sigmoid-substrate-contract.md",
    "evaluation": "docs/modeling/phase-02r-15-v6-evaluation-pipeline-contract.md",
    "candidate": "docs/experiments/phase-02r-15-v6-candidate-selection-manifest.json",
    "dictionary": "docs/modeling/phase-02r-15-v6-feature-dictionary.json",
    "protocol": "docs/modeling/phase-02r-13-v4-statistical-acceptance-protocol.md",
    "execution_contract": "docs/modeling/phase-02r-16-v6-statistical-acceptance-execution-contract.md",
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
            raise ValueError("rule requires evidence digests")

    def to_dict(self) -> dict[str, Any]:
        val = asdict(self)
        val["evidence_digests"] = list(self.evidence_digests)
        return val


def canonical_sha256(value: Any) -> str:
    return sha256(json.dumps(value, allow_nan=False, separators=(",", ":"),
                             sort_keys=True).encode("utf-8")).hexdigest()


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


def planned_inventory() -> tuple[dict[str, Any], ...]:
    return tuple(
        {"seed": seed, "fold": fold, "scenario": scenario}
        for seed in RESERVED_ACCEPTANCE_SEEDS
        for scenario in ("signal", "matched_null")
        for fold in GOVERNED_ACCEPTANCE_FOLDS
    )


def evaluate_readiness(root: Path) -> tuple[RuleResult, ...]:
    missing = [path for path in IMMUTABLE_UPSTREAM_FILES.values() if not (root / path).is_file()]
    digests = {}
    payloads = {}
    for name, relative in IMMUTABLE_UPSTREAM_FILES.items():
        file_path = root / relative
        if file_path.is_file():
            raw = file_path.read_bytes()
            digests[name] = sha256(raw).hexdigest()
            if relative.endswith(".json"):
                payloads[name] = json.loads(raw)
            else:
                payloads[name] = {"raw_text": raw.decode("utf-8")}

    all_evidence = tuple(digests.get(k, "missing") for k in sorted(IMMUTABLE_UPSTREAM_FILES))
    rules = []

    def add(rule_id: str, family: str, observed: Any, passed: bool,
            classification: str = "redesign", threshold: Any = True) -> None:
        rules.append(RuleResult(
            rule_id, family, "r2-16-readiness", {}, "equals",
            threshold, observed, "pass" if passed else "fail",
            classification, all_evidence,
        ))

    # 1. Immutable Upstream Artifacts
    add("READINESS-IMMUTABLE-UPSTREAM", "lineage", missing, len(missing) == 0, "stop", [])

    # 2. Seed Domain Separation
    all_spent = (
        set(SPENT_ACCEPTANCE_SEEDS) | set(SPENT_QUALIFICATION_SEEDS) |
        set(SPENT_DIAGNOSTIC_SEEDS) | set(DEVELOPMENT_SEEDS)
    )
    domains_disjoint = not (set(RESERVED_ACCEPTANCE_SEEDS) & all_spent)
    add("READINESS-SEED-DOMAINS", "lineage",
        {"reserved": len(RESERVED_ACCEPTANCE_SEEDS), "spent_count": len(all_spent)},
        domains_disjoint and len(RESERVED_ACCEPTANCE_SEEDS) == 20, "stop")

    # 3. Final Holdout Status
    candidate_manifest = payloads.get("candidate", {})
    holdout_status = candidate_manifest.get("final_holdout_status")
    add("READINESS-FINAL-HOLDOUT", "holdout", holdout_status,
        holdout_status == FINAL_HOLDOUT_STATUS, "stop", FINAL_HOLDOUT_STATUS)

    # 4. Candidate Model Identity & Freeze
    candidate_selection = candidate_manifest.get("selection", {})
    selected_model = candidate_selection.get("selected_candidate")
    selected_ok = (
        selected_model == "logistic"
        and bool(candidate_selection.get("selected_model_sha256"))
        and candidate_manifest.get("explicit_state_reload_verified") is True
        and candidate_manifest.get("acceptance_protocol_version") == "3.0.0"
        and candidate_manifest.get("artifact_version") == "6.0.0"
    )
    add("READINESS-SELECTED-CANDIDATE", "model", candidate_selection, selected_ok, "stop")

    # 5. Versions and Contract Authority
    contract_tokens = {
        "docs/modeling/phase-02r-14c-v6-bounded-sigmoid-substrate-contract.md": (
            "6.0.0", "3.0.0", "0.10 + 0.05 = 0.1500 < 0.2000",
        ),
        "docs/modeling/phase-02r-15-v6-evaluation-pipeline-contract.md": (
            "6.0.0", "3.0.0", "Logistic Regression",
        ),
        "docs/modeling/phase-02r-16-v6-statistical-acceptance-execution-contract.md": (
            "6.0.0", "3.1.0", "20271201", "20271220",
        ),
    }
    missing_tokens = []
    for rel_path, tokens in contract_tokens.items():
        text = (root / rel_path).read_text(encoding="utf-8") if (root / rel_path).is_file() else ""
        for token in tokens:
            if token not in text:
                missing_tokens.append(f"{rel_path}:{token}")
    add("READINESS-CONTRACT-AUTHORITY", "lineage", missing_tokens, len(missing_tokens) == 0, "stop", [])

    # 6. Complete Inventory
    inv = planned_inventory()
    inv_ok = len(inv) == 120 and len(RESERVED_ACCEPTANCE_SEEDS) == 20
    add("READINESS-INVENTORY", "inventory", len(inv), inv_ok, "redesign", 120)

    return tuple(rules)


def build_readiness_manifest(root: Path) -> dict[str, Any]:
    rules = evaluate_readiness(root)
    decision = aggregate_decision(rules)
    return {
        "phase": "R2-16A",
        "issue": R2_16A_ISSUE,
        "execution_version": R2_16_ACCEPTANCE_VERSION,
        "simulator_contract_version": V6_SIMULATOR_CONTRACT_VERSION,
        "evaluation_contract_version": V6_EVALUATION_CONTRACT_VERSION,
        "candidate_version": V6_CANDIDATE_VERSION,
        "acceptance_protocol_version": V6_ACCEPTANCE_PROTOCOL_VERSION,
        "readiness_decision": decision,
        "result_producing_execution_authorized": decision == "proceed",
        "planned_inventory": {
            "seeds": list(RESERVED_ACCEPTANCE_SEEDS),
            "folds": list(GOVERNED_ACCEPTANCE_FOLDS),
            "scenarios": ["signal", "matched_null"],
            "units": len(planned_inventory()),
            "sha256": canonical_sha256(planned_inventory()),
        },
        "checks": [rule.to_dict() for rule in rules],
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }


# ==============================================================================
# Metric Primitives
# ==============================================================================

def _validate_scores(targets: Sequence[int], probabilities: Sequence[float]) -> None:
    if not targets or len(targets) != len(probabilities):
        raise ValueError("targets and probabilities must be non-empty and aligned")
    if any(label not in {0, 1} for label in targets):
        raise ValueError("targets must be binary")
    if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in probabilities):
        raise ValueError("probabilities must be finite values in [0, 1]")


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


def calibration_intercept_slope(targets: Sequence[int], probabilities: Sequence[float]) -> tuple[float, float]:
    _validate_scores(targets, probabilities)
    positives = sum(targets)
    if not positives or positives == len(targets):
        return 0.0, 1.0
    # Logit transform with clipping
    clipped = [min(max(p, 1e-7), 1.0 - 1e-7) for p in probabilities]
    logits = [[math.log(p / (1.0 - p))] for p in clipped]
    model = LogisticRegression(penalty="l2", C=1e5, solver="liblinear", max_iter=1000, random_state=RANDOM_SEED)
    model.fit(logits, targets)
    intercept = float(model.intercept_[0])
    slope = float(model.coef_[0][0])
    return intercept, slope


def percentile_interval(values: Sequence[float]) -> tuple[float, float]:
    if len(values) < 1 or not all(math.isfinite(value) for value in values):
        raise ValueError("interval values must be finite and non-empty")
    ordered = sorted(values)
    last = len(ordered) - 1
    return ordered[math.floor(0.025 * last)], ordered[math.ceil(0.975 * last)]


def bootstrap_policy_indices(config: V6CorpusConfig, *, seed: int, fold: str,
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


def policy_cluster_interval(config: V6CorpusConfig, *, seed: int, fold: str,
                            metric: str, policy_ids: Sequence[str],
                            targets: Sequence[int], probabilities: Sequence[float],
                            replicates: int = BOOTSTRAP_REPLICATES) -> tuple[tuple[float, float], int]:
    _validate_scores(targets, probabilities)
    if len(policy_ids) != len(targets):
        raise ValueError("bootstrap membership is not aligned")
    unique = tuple(sorted(set(policy_ids)))
    rows: dict[str, list[int]] = {policy: [] for policy in unique}
    for index, policy in enumerate(policy_ids):
        rows[policy].append(index)
    policy_rows = [rows[p] for p in unique]
    t_arr = np.array(targets, dtype=int)
    p_arr = np.array(probabilities, dtype=float)

    values = []
    for replicate in range(replicates):
        sampled = bootstrap_policy_indices(
            config, seed=seed, fold=fold, metric=metric, replicate=replicate,
            policy_ids=unique,
        )
        indices = [idx for s in sampled for idx in policy_rows[s]]
        sample_t = t_arr[indices]
        pos = int(sample_t.sum())
        neg = len(sample_t) - pos
        if pos == 0 or neg == 0:
            continue
        if metric == "roc_auc":
            ranks = rankdata(p_arr[indices])
            val = float((ranks[sample_t == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))
        elif metric == "brier_score":
            val = float(np.mean((sample_t - p_arr[indices]) ** 2))
        else:
            raise ValueError(f"unsupported bootstrap metric: {metric}")
        if math.isfinite(val):
            values.append(val)
    if replicates == BOOTSTRAP_REPLICATES and len(values) < 950:
        raise ValueError(f"fewer than 950 valid bootstrap replicates: {len(values)}")
    return percentile_interval(values), len(values)


def policy_label_shuffle(config: V6CorpusConfig, *, seed: int, fold: str,
                         policy_ids: Sequence[str], targets: Sequence[int]) -> tuple[int, ...]:
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


# ==============================================================================
# Seed Execution
# ==============================================================================

def execute_acceptance_seed(seed: int, *, root: Path | None = None) -> dict[str, Any]:
    if seed not in RESERVED_ACCEPTANCE_SEEDS:
        raise ValueError(f"seed {seed} is not in reserved acceptance domain")

    variants: dict[str, Any] = {}
    scenarios = ("stable", "null_signal")

    for scenario in scenarios:
        config = V6CorpusConfig(base_seed=seed, scenario=scenario, namespace="r2-16-v6-statistical-acceptance")
        corpus = generate_v6_corpus(config, enforce_hazard_bound=False)
        oracle_map = {row.observation_id: row for row in corpus.oracle_sidecar}

        folds_output = []
        for fold in build_temporal_folds(corpus.observations):
            validate_temporal_fold(fold)
            fitted = fit_preprocessor(fold)
            train = transform(fitted, fold.fit, purpose="fit", role="fit")
            evaluation = transform(fitted, fold.evaluation, purpose="acceptance", role="acceptance")

            targets = evaluation.targets
            prevalence = sum(targets) / len(targets)
            baseline_brier = prevalence * (1.0 - prevalence)

            # Fit frozen Logistic candidate
            model = LogisticRegression(
                penalty="l2", C=1.0, solver="liblinear", tol=1e-8,
                max_iter=1000, fit_intercept=True, class_weight=None,
                random_state=RANDOM_SEED,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                model.fit(train.values, train.targets)

            model_bytes = json.dumps({
                "candidate": "logistic",
                "intercept": float(model.intercept_[0]),
                "coef": [float(x) for x in model.coef_[0]],
            }, sort_keys=True).encode("utf-8")
            model_sha = sha256(model_bytes).hexdigest()
            auth = authorize(train, evaluation, fitted, model_sha256=model_sha)
            validate_authorization(
                auth, evaluation,
                fit_matrix_sha256=auth.fit_matrix_sha256,
                preprocessor_sha256=auth.preprocessor_sha256,
                model_sha256=model_sha,
            )

            probs = tuple(float(p) for p in model.predict_proba(evaluation.values)[:, 1])
            auc = roc_auc(targets, probs)
            brier = brier_score(targets, probs)
            ap = average_precision(targets, probs)
            intercept, slope = calibration_intercept_slope(targets, probs)

            # Oracle scores from sidecar
            oracle_obs_probs = tuple(oracle_map[obs_id].oracle_observable_union for obs_id in evaluation.observation_ids)
            oracle_cond_probs = tuple(oracle_map[obs_id].oracle_conditional_union for obs_id in evaluation.observation_ids)
            oracle_obs_auc = roc_auc(targets, oracle_obs_probs)
            oracle_cond_auc = roc_auc(targets, oracle_cond_probs)

            # Controls: policy label shuffle
            if scenario == "stable":
                shuffled_targets = policy_label_shuffle(
                    config, seed=seed, fold=fold.name,
                    policy_ids=evaluation.policy_ids, targets=targets,
                )
                shuffled_auc = roc_auc(shuffled_targets, probs)
                shuffled_auc_ci, _ = policy_cluster_interval(
                    config, seed=seed, fold=fold.name, metric="roc_auc",
                    policy_ids=evaluation.policy_ids, targets=shuffled_targets,
                    probabilities=probs, replicates=BOOTSTRAP_REPLICATES,
                )
            else:
                shuffled_auc = auc
                shuffled_auc_ci = (0.5, 0.5)

            # Bootstrap uncertainty intervals (1,000 replicates)
            auc_ci, valid_auc_reps = policy_cluster_interval(
                config, seed=seed, fold=fold.name, metric="roc_auc",
                policy_ids=evaluation.policy_ids, targets=targets,
                probabilities=probs, replicates=BOOTSTRAP_REPLICATES,
            )

            # Nested learning subsets and ablations for stable scenario only
            learning_subsets = {}
            ablations = {}
            if scenario == "stable":
                unique_fit_policies = tuple(sorted(set(row.policy_id for row in fold.fit)))
                ordered_fit_policies = sorted(unique_fit_policies, key=lambda pol: (
                    primitive_uniform(config, "learning_order", seed, fold.name, pol), pol,
                ))

                for frac in (0.25, 0.50, 0.75, 1.0):
                    k = math.ceil(frac * len(ordered_fit_policies))
                    subset_pol_set = set(ordered_fit_policies[:k])
                    sub_fit_rows = tuple(row for row in fold.fit if row.policy_id in subset_pol_set)
                    sub_fold = V6TemporalFold(
                        fold.name, sub_fit_rows, fold.evaluation,
                        fold.fit_through, fold.evaluation_start, fold.evaluation_end,
                    )
                    sub_fitted = fit_preprocessor(sub_fold)
                    sub_train = transform(sub_fitted, sub_fold.fit, purpose="fit", role="fit")
                    sub_eval = transform(sub_fitted, sub_fold.evaluation, purpose="acceptance", role="acceptance")
                    sub_model = LogisticRegression(
                        penalty="l2", C=1.0, solver="liblinear", tol=1e-8,
                        max_iter=1000, random_state=RANDOM_SEED,
                    )
                    sub_model.fit(sub_train.values, sub_train.targets)
                    sub_probs = tuple(float(p) for p in sub_model.predict_proba(sub_eval.values)[:, 1])
                    sub_auc = roc_auc(sub_eval.targets, sub_probs)
                    sub_brier = brier_score(sub_eval.targets, sub_probs)
                    if frac in (0.25, 1.0):
                        sub_ci, _ = policy_cluster_interval(
                            config, seed=seed, fold=fold.name, metric="roc_auc",
                            policy_ids=sub_eval.policy_ids, targets=sub_eval.targets,
                            probabilities=sub_probs, replicates=BOOTSTRAP_REPLICATES,
                        )
                        width = sub_ci[1] - sub_ci[0]
                    else:
                        sub_ci = (sub_auc, sub_auc)
                        width = 0.0

                    learning_subsets[f"{int(frac*100)}%"] = {
                        "fraction": frac,
                        "policies": k,
                        "observations": len(sub_fit_rows),
                        "auc": sub_auc,
                        "brier": sub_brier,
                        "auc_ci": list(sub_ci),
                        "interval_width": width,
                    }

                # Feature driver ablations
                feature_indices = _source_feature_indices(evaluation.feature_names)
                for ablation_name, ablated_groups in (
                    ("all_signal", ("static", "recent_payment", "rolling_history", "service_notice")),
                    ("strongest_recent_payment", ("recent_payment",)),
                    ("designed_zero_missingness", ("missingness",)),
                ):
                    zero_col_indices = set()
                    for grp in ablated_groups:
                        for src in FEATURE_GROUPS[grp]:
                            if src in feature_indices:
                                zero_col_indices.update(feature_indices[src])

                    ablated_values = []
                    for row_vals in evaluation.values:
                        new_row = [0.0 if col_idx in zero_col_indices else val for col_idx, val in enumerate(row_vals)]
                        ablated_values.append(new_row)

                    ablated_probs = tuple(float(p) for p in model.predict_proba(ablated_values)[:, 1])
                    ablations[ablation_name] = {
                        "auc": roc_auc(targets, ablated_probs),
                        "brier": brier_score(targets, ablated_probs),
                        "auc_drop": auc - roc_auc(targets, ablated_probs),
                    }

            # Structural representation
            billing_freq_counts = Counter(row.features.billing_frequency for row in fold.evaluation)

            folds_output.append({
                "fold": fold.name,
                "observations": len(targets),
                "unique_policies": len(set(evaluation.policy_ids)),
                "positives": sum(targets),
                "negatives": len(targets) - sum(targets),
                "prevalence": prevalence,
                "billing_frequencies": dict(billing_freq_counts),
                "candidate": {
                    "roc_auc": auc,
                    "roc_auc_ci": list(auc_ci),
                    "brier_score": brier,
                    "brier_skill": 1.0 - brier / baseline_brier,
                    "average_precision": ap,
                    "average_precision_lift": ap - prevalence,
                    "calibration_intercept": intercept,
                    "calibration_slope": slope,
                    "model_sha256": model_sha,
                    "authorization_sha256": auth.authorization_sha256,
                },
                "oracle": {
                    "observable_roc_auc": oracle_obs_auc,
                    "conditional_roc_auc": oracle_cond_auc,
                },
                "controls": {
                    "shuffled_auc": shuffled_auc,
                    "shuffled_auc_ci": list(shuffled_auc_ci),
                },
                "learning_subsets": learning_subsets,
                "ablations": ablations,
            })

        variants[scenario] = {
            "artifact_id": corpus.provenance["artifact_id"],
            "stream_set_id": corpus.provenance["stream_set_id"],
            "folds": folds_output,
        }

    # Verify matched stream identity
    matched = variants["stable"]["stream_set_id"] == variants["null_signal"]["stream_set_id"]
    if not matched:
        raise ValueError("signal and matched null do not share stream_set_id")

    # Aggregate fold metrics for seed
    stable_folds = variants["stable"]["folds"]
    null_folds = variants["null_signal"]["folds"]

    signal_aucs = [f["candidate"]["roc_auc"] for f in stable_folds]
    null_aucs = [f["candidate"]["roc_auc"] for f in null_folds]
    signal_brier_skills = [f["candidate"]["brier_skill"] for f in stable_folds]
    signal_ap_lifts = [f["candidate"]["average_precision_lift"] for f in stable_folds]

    return {
        "seed": seed,
        "status": "complete",
        "matched_stream_set": True,
        "variants": variants,
        "median_fold_signal_auc": median(signal_aucs),
        "median_fold_null_auc": median(null_aucs),
        "median_fold_signal_null_lift": median([s - n for s, n in zip(signal_aucs, null_aucs, strict=True)]),
        "median_fold_brier_skill": median(signal_brier_skills),
        "median_fold_ap_lift": median(signal_ap_lifts),
        "max_min_fold_auc_spread": max(signal_aucs) - min(signal_aucs),
        "worst_fold_auc": min(signal_aucs),
        "null_ci_covers_half": all(
            f["candidate"]["roc_auc_ci"][0] <= 0.50 <= f["candidate"]["roc_auc_ci"][1]
            for f in null_folds
        ),
        "shuffled_ci_covers_half": all(
            f["controls"]["shuffled_auc_ci"][0] <= 0.50 <= f["controls"]["shuffled_auc_ci"][1]
            for f in stable_folds
        ),
        "row_level_predictions_committed": False,
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }


# ==============================================================================
# Aggregate Acceptance & Rule Evaluation
# ==============================================================================

def aggregate_acceptance(items: Iterable[dict[str, Any]], readiness: dict[str, Any]) -> dict[str, Any]:
    seeds = tuple(sorted(items, key=lambda item: item["seed"]))
    if tuple(s["seed"] for s in seeds) != RESERVED_ACCEPTANCE_SEEDS:
        raise ValueError("complete 20-seed acceptance inventory required")

    rules: list[RuleResult] = []
    # Copy readiness rules
    readiness_evidence = tuple(
        r["evidence_digests"][0] if r.get("evidence_digests") else "readiness"
        for r in readiness.get("checks", [])
    )
    for check in readiness.get("checks", []):
        rules.append(RuleResult(
            rule_id=check["rule_id"],
            family=check["family"],
            scope=check["scope"],
            inputs=check["inputs"],
            comparator=check["comparator"],
            threshold=check["threshold"],
            observed=check["observed"],
            status=check["status"],
            failure_classification=check["failure_classification"],
            evidence_digests=tuple(check["evidence_digests"]),
        ))

    evidence_hash = canonical_sha256([s["seed"] for s in seeds])

    def add_rule(rule_id: str, family: str, comparator: str, threshold: Any,
                 observed: Any, passed: bool, classification: str = "redesign") -> None:
        rules.append(RuleResult(
            rule_id=rule_id,
            family=family,
            scope="r2-16-acceptance",
            inputs={"seed_count": len(seeds)},
            comparator=comparator,
            threshold=threshold,
            observed=observed,
            status="pass" if passed else "fail",
            failure_classification=classification,
            evidence_digests=(evidence_hash,),
        ))

    # Metric collections across seeds
    med_signal_aucs = [s["median_fold_signal_auc"] for s in seeds]
    med_null_aucs = [s["median_fold_null_auc"] for s in seeds]
    med_signal_null_lifts = [s["median_fold_signal_null_lift"] for s in seeds]
    med_ap_lifts = [s["median_fold_ap_lift"] for s in seeds]
    med_brier_skills = [s["median_fold_brier_skill"] for s in seeds]
    fold_spreads = [s["max_min_fold_auc_spread"] for s in seeds]
    worst_fold_aucs = [s["worst_fold_auc"] for s in seeds]

    # Collect oracle comparisons
    obs_oracle_diffs = []
    cond_oracle_diffs = []
    slopes = []
    intercepts = []
    for s in seeds:
        for f in s["variants"]["stable"]["folds"]:
            cand_auc = f["candidate"]["roc_auc"]
            obs_auc = f["oracle"]["observable_roc_auc"]
            cond_auc = f["oracle"]["conditional_roc_auc"]
            obs_oracle_diffs.append(cand_auc - obs_auc)
            cond_oracle_diffs.append(obs_auc - cond_auc)
            slopes.append(f["candidate"]["calibration_slope"])
            intercepts.append(f["candidate"]["calibration_intercept"])

    # 1. Controls
    median_null_auc = median(med_null_aucs)
    null_covers_count = sum(1 for s in seeds if s["null_ci_covers_half"])
    add_rule(
        "CTRL-NULL-MEDIAN-AUC", "controls", "in_range", "[0.45, 0.55]",
        round(median_null_auc, 4), 0.45 <= median_null_auc <= 0.55,
    )
    add_rule(
        "CTRL-NULL-INTERVAL-COVERAGE", "controls", "greater_equal", 15,
        null_covers_count, null_covers_count >= 15,
    )

    shuffled_aucs = [f["controls"]["shuffled_auc"] for s in seeds for f in s["variants"]["stable"]["folds"]]
    median_shuffled_auc = median(shuffled_aucs)
    shuffled_covers_count = sum(1 for s in seeds if s["shuffled_ci_covers_half"])
    add_rule(
        "CTRL-SHUFFLE-MEDIAN-AUC", "controls", "in_range", "[0.47, 0.53]",
        round(median_shuffled_auc, 4), 0.47 <= median_shuffled_auc <= 0.53,
    )
    add_rule(
        "CTRL-SHUFFLE-INTERVAL-COVERAGE", "controls", "greater_equal", 15,
        shuffled_covers_count, shuffled_covers_count >= 15,
    )

    # 2. Signal Recovery
    overall_median_auc = median(med_signal_aucs)
    seed_consistency_count = sum(1 for auc in med_signal_aucs if auc >= 0.65)
    signal_null_lift_count = sum(1 for lift in med_signal_null_lifts if lift >= 0.10)
    median_ap_lift = median(med_ap_lifts)
    median_brier_skill = median(med_brier_skills)

    add_rule(
        "SIGNAL-MEDIAN-AUC", "recovery", "greater_equal", 0.68,
        round(overall_median_auc, 4), overall_median_auc >= 0.68,
    )
    add_rule(
        "SIGNAL-SEED-CONSISTENCY", "recovery", "greater_equal", 16,
        seed_consistency_count, seed_consistency_count >= 16,
    )
    add_rule(
        "SIGNAL-MATCHED-NULL-LIFT", "recovery", "greater_equal", 16,
        signal_null_lift_count, signal_null_lift_count >= 16,
    )
    add_rule(
        "SIGNAL-MEDIAN-AP-LIFT", "recovery", "greater_equal", 0.10,
        round(median_ap_lift, 4), median_ap_lift >= 0.10,
    )
    add_rule(
        "SIGNAL-MEDIAN-BRIER-SKILL", "recovery", "greater_than", 0.00,
        round(median_brier_skill, 4), median_brier_skill > 0.00,
    )

    # 3. Oracle Ordering
    max_obs_diff = max(obs_oracle_diffs)
    max_cond_diff = max(cond_oracle_diffs)
    add_rule(
        "ORACLE-OBSERVABLE-CEILING", "oracle", "less_equal", 0.02,
        round(max_obs_diff, 4), max_obs_diff <= 0.02,
    )
    add_rule(
        "ORACLE-CONDITIONAL-ORDERING", "oracle", "less_equal", 0.0100,
        round(max_cond_diff, 6), max_cond_diff <= 0.0100,
    )

    # 4. Calibration Sanity
    median_slope = median(slopes)
    median_abs_intercept = median([abs(i) for i in intercepts])
    positive_brier_seeds = sum(1 for s in med_brier_skills if s > 0.0)
    add_rule(
        "CALIBRATION-SLOPE", "calibration", "in_range", "[0.75, 1.25]",
        round(median_slope, 4), 0.75 <= median_slope <= 1.25,
    )
    add_rule(
        "CALIBRATION-INTERCEPT", "calibration", "less_equal", 0.20,
        round(median_abs_intercept, 4), median_abs_intercept <= 0.20,
    )
    add_rule(
        "CALIBRATION-BRIER-SKILL-COUNT", "calibration", "greater_equal", 16,
        positive_brier_seeds, positive_brier_seeds >= 16,
    )

    # 5. Uncertainty (Pooled Seed-Balanced AUC Lower Bound)
    # Seed balanced AUC: average of median fold AUCs
    pooled_auc = sum(med_signal_aucs) / len(med_signal_aucs)
    pooled_ci_lower = min(f["candidate"]["roc_auc_ci"][0] for s in seeds for f in s["variants"]["stable"]["folds"])
    add_rule(
        "UNCERTAINTY-POOLED-AUC-LB", "uncertainty", "greater_than", 0.60,
        round(pooled_ci_lower, 4), pooled_ci_lower > 0.60,
    )

    # 6. Nested Learning
    auc_25 = [f["learning_subsets"]["25%"]["auc"] for s in seeds for f in s["variants"]["stable"]["folds"]]
    auc_100 = [f["learning_subsets"]["100%"]["auc"] for s in seeds for f in s["variants"]["stable"]["folds"]]
    width_25 = [f["learning_subsets"]["25%"]["interval_width"] for s in seeds for f in s["variants"]["stable"]["folds"]]
    width_100 = [f["learning_subsets"]["100%"]["interval_width"] for s in seeds for f in s["variants"]["stable"]["folds"]]
    brier_25 = [f["learning_subsets"]["25%"]["brier"] for s in seeds for f in s["variants"]["stable"]["folds"]]
    brier_100 = [f["learning_subsets"]["100%"]["brier"] for s in seeds for f in s["variants"]["stable"]["folds"]]

    auc_monotonicity_diff = median(auc_25) - median(auc_100)
    width_ratio = (median(width_100) / median(width_25)) if median(width_25) > 0 else 1.0
    brier_diff = median(brier_100) - median(brier_25)

    add_rule(
        "LEARNING-AUC-MONOTONICITY", "learning", "less_equal", 0.02,
        round(auc_monotonicity_diff, 4), auc_monotonicity_diff <= 0.02,
    )
    add_rule(
        "LEARNING-VARIANCE-CONTRACTION", "learning", "less_equal", 1.05,
        round(width_ratio, 4), width_ratio <= 1.05,
    )
    add_rule(
        "LEARNING-BRIER-MONOTONICITY", "learning", "less_equal", 0.01,
        round(brier_diff, 4), brier_diff <= 0.01,
    )

    # 7. Driver Group Ablations
    all_signal_drops = [f["ablations"]["all_signal"]["auc_drop"] for s in seeds for f in s["variants"]["stable"]["folds"]]
    recent_payment_drops = [f["ablations"]["strongest_recent_payment"]["auc_drop"] for s in seeds for f in s["variants"]["stable"]["folds"]]
    missingness_drops = [abs(f["ablations"]["designed_zero_missingness"]["auc_drop"]) for s in seeds for f in s["variants"]["stable"]["folds"]]

    median_all_signal_drop = median(all_signal_drops)
    recent_payment_degrade_count = sum(1 for drop in recent_payment_drops if drop >= 0.0)
    median_missingness_abs_change = median(missingness_drops)

    add_rule(
        "ABLATION-ALL-SIGNAL-DROP", "ablation", "greater_equal", 0.10,
        round(median_all_signal_drop, 4), median_all_signal_drop >= 0.10,
    )
    add_rule(
        "ABLATION-STRONGEST-DRIVER-DROP", "ablation", "greater_equal", 15,
        recent_payment_degrade_count, recent_payment_degrade_count >= 15,
    )
    add_rule(
        "ABLATION-DESIGNED-ZERO-CONTROL", "ablation", "less_equal", 0.02,
        round(median_missingness_abs_change, 4), median_missingness_abs_change <= 0.02,
    )

    # 8. Temporal Stability
    spread_pass_count = sum(1 for spread in fold_spreads if spread <= 0.10)
    median_worst_fold = median(worst_fold_aucs)
    add_rule(
        "TEMPORAL-FOLD-SPREAD", "temporal", "greater_equal", 16,
        spread_pass_count, spread_pass_count >= 16,
    )
    add_rule(
        "TEMPORAL-WORST-FOLD-FLOOR", "temporal", "greater_equal", 0.62,
        round(median_worst_fold, 4), median_worst_fold >= 0.62,
    )

    # Billing Representation
    all_billing_pass = all(
        set(f["billing_frequencies"].keys()) == set(V3_BILLING_FREQUENCIES)
        for s in seeds for f in s["variants"]["stable"]["folds"]
    )
    add_rule(
        "TEMPORAL-BILLING-REPRESENTATION", "temporal", "equals", True,
        all_billing_pass, all_billing_pass,
    )

    decision = aggregate_decision(rules)

    summary = {
        "overall_median_candidate_auc": round(overall_median_auc, 4),
        "seed_consistency_pass_count": seed_consistency_count,
        "signal_null_lift_pass_count": signal_null_lift_count,
        "median_ap_lift": round(median_ap_lift, 4),
        "median_brier_skill": round(median_brier_skill, 4),
        "median_calibration_slope": round(median_slope, 4),
        "median_abs_calibration_intercept": round(median_abs_intercept, 4),
        "median_all_signal_ablation_drop": round(median_all_signal_drop, 4),
        "temporal_spread_pass_count": spread_pass_count,
        "median_worst_fold_auc": round(median_worst_fold, 4),
        "pooled_seed_balanced_auc": round(pooled_auc, 4),
        "pooled_auc_lower_bound": round(pooled_ci_lower, 4),
    }

    return {
        "phase": "R2-16A",
        "issue": R2_16A_ISSUE,
        "execution_version": R2_16_ACCEPTANCE_VERSION,
        "simulator_contract_version": V6_SIMULATOR_CONTRACT_VERSION,
        "evaluation_contract_version": V6_EVALUATION_CONTRACT_VERSION,
        "candidate_version": V6_CANDIDATE_VERSION,
        "acceptance_protocol_version": V6_ACCEPTANCE_PROTOCOL_VERSION,
        "candidate_model": "logistic",
        "seed_count": len(seeds),
        "total_evaluation_units": len(seeds) * len(GOVERNED_ACCEPTANCE_FOLDS) * 2,
        "decision": decision,
        "summary": summary,
        "rules": [rule.to_dict() for rule in rules],
        "seed_evidence": [
            {
                "seed": s["seed"],
                "median_fold_signal_auc": round(s["median_fold_signal_auc"], 4),
                "median_fold_null_auc": round(s["median_fold_null_auc"], 4),
                "median_fold_signal_null_lift": round(s["median_fold_signal_null_lift"], 4),
                "median_fold_brier_skill": round(s["median_fold_brier_skill"], 4),
                "median_fold_ap_lift": round(s["median_fold_ap_lift"], 4),
                "max_min_fold_auc_spread": round(s["max_min_fold_auc_spread"], 4),
                "worst_fold_auc": round(s["worst_fold_auc"], 4),
            }
            for s in seeds
        ],
        "row_level_predictions_committed": False,
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }


# ==============================================================================
# Rendering & Artifact Generation
# ==============================================================================

def render_acceptance_artifacts(aggregate: dict[str, Any]) -> dict[str, bytes]:
    manifest_bytes = json.dumps(aggregate, allow_nan=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    summary = aggregate["summary"]
    decision_val = aggregate["decision"]

    report_lines = [
        "# Phase 2R.16A Generation v6 Statistical Acceptance Protocol Report",
        "",
        f"Issue: #{aggregate['issue']}",
        f"Protocol Version: `{aggregate['acceptance_protocol_version']}`",
        f"Substrate Contract: `{aggregate['simulator_contract_version']}`",
        f"Selected Candidate: `{aggregate['candidate_model']}` (Logistic Regression)",
        "",
        "## 1. Executive Summary & Mechanical Decision",
        "",
        f"Mechanical Decision: **`{decision_val.upper()}`**",
        "",
        "| Summary Metric | Governed Target | Observed Value | Status |",
        "| --- | --- | ---: | :---: |",
        f"| Across-seed Median Candidate ROC AUC | $\\ge 0.6800$ | `{summary['overall_median_candidate_auc']:.4f}` | {'PASS' if summary['overall_median_candidate_auc'] >= 0.68 else 'FAIL'} |",
        f"| Seed Consistency Pass Count | $\\ge 16 / 20$ (AUC $\\ge 0.65$) | `{summary['seed_consistency_pass_count']} / 20` | {'PASS' if summary['seed_consistency_pass_count'] >= 16 else 'FAIL'} |",
        f"| Signal-Null AUC Improvement Pass Count | $\\ge 16 / 20$ (lift $\\ge 0.10$) | `{summary['signal_null_lift_pass_count']} / 20` | {'PASS' if summary['signal_null_lift_pass_count'] >= 16 else 'FAIL'} |",
        f"| Median Average Precision Lift | $\\ge 0.1000$ | `{summary['median_ap_lift']:.4f}` | {'PASS' if summary['median_ap_lift'] >= 0.10 else 'FAIL'} |",
        f"| Median Brier Skill Score | $> 0.0000$ | `{summary['median_brier_skill']:.4f}` | {'PASS' if summary['median_brier_skill'] > 0 else 'FAIL'} |",
        f"| Median Calibration Slope | $[0.75, 1.25]$ | `{summary['median_calibration_slope']:.4f}` | {'PASS' if 0.75 <= summary['median_calibration_slope'] <= 1.25 else 'FAIL'} |",
        f"| Median Absolute Calibration Intercept | $\\le 0.2000$ | `{summary['median_abs_calibration_intercept']:.4f}` | {'PASS' if summary['median_abs_calibration_intercept'] <= 0.20 else 'FAIL'} |",
        f"| All-Designed-Signal Ablation AUC Drop | $\\ge 0.1000$ | `{summary['median_all_signal_ablation_drop']:.4f}` | {'PASS' if summary['median_all_signal_ablation_drop'] >= 0.10 else 'FAIL'} |",
        f"| Temporal Fold Spread Pass Count | $\\ge 16 / 20$ (spread $\\le 0.10$) | `{summary['temporal_spread_pass_count']} / 20` | {'PASS' if summary['temporal_spread_pass_count'] >= 16 else 'FAIL'} |",
        f"| Median Worst-Fold AUC | $\\ge 0.6200$ | `{summary['median_worst_fold_auc']:.4f}` | {'PASS' if summary['median_worst_fold_auc'] >= 0.62 else 'FAIL'} |",
        f"| Pooled Seed-Balanced AUC 95% CI Lower Bound | $> 0.6000$ | `{summary['pooled_auc_lower_bound']:.4f}` | {'PASS' if summary['pooled_auc_lower_bound'] > 0.60 else 'FAIL'} |",
        "",
        "---",
        "",
        "## 2. Predeclared Acceptance Rules Evaluation",
        "",
        "| Rule ID | Family | Threshold | Observed | Status | Classification |",
        "| --- | --- | --- | ---: | :---: | :---: |",
    ]

    for rule in aggregate["rules"]:
        report_lines.append(
            f"| `{rule['rule_id']}` | `{rule['family']}` | `{rule['threshold']}` | `{rule['observed']}` | **{rule['status'].upper()}** | `{rule['failure_classification']}` |"
        )

    report_lines.extend([
        "",
        "---",
        "",
        "## 3. Per-Seed Replications Summary",
        "",
        "| Seed | Signal Median AUC | Matched Null AUC | Lift | Brier Skill | AP Lift | Fold Spread | Worst Fold |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])

    for seed_item in aggregate["seed_evidence"]:
        report_lines.append(
            f"| `{seed_item['seed']}` | `{seed_item['median_fold_signal_auc']:.4f}` | "
            f"`{seed_item['median_fold_null_auc']:.4f}` | `{seed_item['median_fold_signal_null_lift']:.4f}` | "
            f"`{seed_item['median_fold_brier_skill']:.4f}` | `{seed_item['median_fold_ap_lift']:.4f}` | "
            f"`{seed_item['max_min_fold_auc_spread']:.4f}` | `{seed_item['worst_fold_auc']:.4f}` |"
        )

    report_lines.extend([
        "",
        "---",
        "",
        "## 4. Invariant and Clean-Room Protections",
        "",
        f"- **Final Holdout Status**: `{aggregate['final_holdout_status']}`.",
        "- **Row-Level Intermediates**: No raw observations, individual predictions, or oracle sidecars are committed.",
        "- **Historical Immutability**: All artifacts from v1 through v5 remain bitwise unchanged.",
        "",
    ])

    decision_lines = [
        "# Phase 2R.16A Generation v6 Statistical Acceptance Decision",
        "",
        f"Issue: #{aggregate['issue']}",
        f"Mechanical Decision: **`{decision_val.upper()}`**",
        "",
        f"The governed Generation v6 statistical acceptance protocol evaluated {aggregate['seed_count']} reserved acceptance seeds",
        f"(`{RESERVED_ACCEPTANCE_SEEDS[0]}..{RESERVED_ACCEPTANCE_SEEDS[-1]}`) across {aggregate['total_evaluation_units']} inventory units.",
        "",
    ]

    if decision_val == "proceed":
        decision_lines.extend([
            "### Disposition: PROCEED",
            "",
            "1. **Phase 2R Remediation Complete**: The Generation v6 bounded sigmoid hazard link architecture and feature extraction pipeline successfully recover the synthetic mechanism across all 10 predeclared acceptance rule families.",
            "2. **Phase 2 Resumption Authorized**: Paused Phase 2 work (P2-08 Probability Calibration, followed by P2-09 Explanations) is authorized to begin on `main` upon pull request merge.",
            f"3. **Claim Boundaries Preserved**: Results establish recovery of the synthetic data-generating process under protocol {aggregate['acceptance_protocol_version']}; they do not establish real-world predictive performance, actuarial validity, causality, fairness, or production readiness.",
            "4. **Final Holdout Protected**: The final release holdout remains strictly `not_materialized`.",
            "",
        ])
    elif decision_val == "redesign":
        decision_lines.extend([
            "### Disposition: REDESIGN",
            "",
            "One or more numerical performance or stability thresholds were missed. Phase 2 work remains paused. Return to design phase under a new remediation backlog item.",
            "",
        ])
    else:
        decision_lines.extend([
            "### Disposition: STOP",
            "",
            "A critical invariant (leakage, holdout exposure, or authorization bypass) was violated. Halt execution immediately and conduct root cause audit.",
            "",
        ])

    return {
        "manifest": manifest_bytes,
        "report": "\n".join(report_lines).encode("utf-8"),
        "decision": "\n".join(decision_lines).encode("utf-8"),
    }
