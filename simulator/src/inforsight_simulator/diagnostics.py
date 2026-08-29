"""Deterministic feature-sanity and shortcut diagnostics."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from math import isfinite
import re
from typing import Any, Mapping

from sklearn import __version__ as sklearn_version
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.tree import DecisionTreeClassifier

from .boosted_modeling import FittedBoostedModel, predict_boosted_probabilities
from .features import INCLUDED_CATEGORICAL_FEATURES, INCLUDED_NUMERIC_FEATURES
from .modeling import FittedLogisticBaseline, predict_positive_probabilities
from .preprocessing import ModelMatrix, matrix_digest
from .scoring_authorization import (
    HISTORICAL_TRAIN,
    NON_FINAL_VALIDATION,
    ScoringAuthorization,
    authorize_diagnostic_derivative,
    validate_scoring_authorization,
)


FEATURE_DIAGNOSTICS_VERSION = "1.0.0"
DIAGNOSTIC_CONFIGURATION_VERSION = "1.0.0"
DIAGNOSTIC_RANDOM_SEED = 20260817
ARTIFACT_DECIMAL_PLACES = 10
PERMITTED_PARTITIONS = ("train", "validation")
IDENTIFIER_TOKENS = frozenset(
    {"id", "uuid", "guid", "key", "index", "row", "policy", "observation", "customer", "account", "scenario"}
)
HIGH_CARDINALITY_RATIO = 0.90
NEAR_CONSTANT_RATIO = 0.95
STRONG_MI_THRESHOLD = 0.50
STRONG_SHALLOW_AUC = 0.90
STRONG_SHALLOW_LOG_LOSS = 0.40
MATERIAL_AUC_CHANGE = 0.10
MATERIAL_LOG_LOSS_INCREASE = 0.10


@dataclass(frozen=True)
class DiagnosticSpecification:
    random_seed: int = DIAGNOSTIC_RANDOM_SEED
    mutual_information_neighbors: int = 3
    shallow_criterion: str = "log_loss"
    shallow_max_depth: int = 1
    shallow_min_samples_leaf: int = 2
    high_cardinality_ratio: float = HIGH_CARDINALITY_RATIO
    near_constant_ratio: float = NEAR_CONSTANT_RATIO
    strong_mutual_information: float = STRONG_MI_THRESHOLD
    strong_shallow_auc: float = STRONG_SHALLOW_AUC
    strong_shallow_log_loss: float = STRONG_SHALLOW_LOG_LOSS
    material_auc_change: float = MATERIAL_AUC_CHANGE
    material_log_loss_increase: float = MATERIAL_LOG_LOSS_INCREASE

    def to_dict(self) -> dict[str, Any]:
        return {
            "random_seed": self.random_seed,
            "mutual_information_neighbors": self.mutual_information_neighbors,
            "shallow_model": {
                "estimator": "DecisionTreeClassifier",
                "criterion": self.shallow_criterion,
                "max_depth": self.shallow_max_depth,
                "min_samples_leaf": self.shallow_min_samples_leaf,
                "splitter": "best",
            },
            "thresholds": {
                "high_cardinality_ratio": self.high_cardinality_ratio,
                "near_constant_ratio": self.near_constant_ratio,
                "strong_mutual_information": self.strong_mutual_information,
                "strong_shallow_auc": self.strong_shallow_auc,
                "strong_shallow_log_loss": self.strong_shallow_log_loss,
                "material_auc_change": self.material_auc_change,
                "material_log_loss_increase": self.material_log_loss_increase,
            },
        }


FROZEN_DIAGNOSTIC_SPECIFICATION = DiagnosticSpecification()


def source_feature_groups(matrix: ModelMatrix) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """Map frozen output columns back to reviewed source-feature groups."""

    _validate_matrix(matrix)
    groups: dict[str, list[int]] = {}
    approved = set(INCLUDED_NUMERIC_FEATURES) | set(INCLUDED_CATEGORICAL_FEATURES)
    for index, output_name in enumerate(matrix.feature_names):
        source_name = output_name.split("=", 1)[0]
        if source_name not in approved:
            raise ValueError(f"output feature does not map to an approved source: {output_name}")
        groups.setdefault(source_name, []).append(index)
    expected = tuple(INCLUDED_NUMERIC_FEATURES) + tuple(INCLUDED_CATEGORICAL_FEATURES)
    if set(groups) != set(expected):
        raise ValueError("source-feature grouping is incomplete")
    return tuple((name, tuple(groups[name])) for name in expected)


def training_mutual_information(
    train: ModelMatrix,
    authorization: ScoringAuthorization,
    specification: DiagnosticSpecification = FROZEN_DIAGNOSTIC_SPECIFICATION,
) -> tuple[dict[str, Any], ...]:
    """Compute frozen train-only univariate MI and aggregate by source group."""

    _validate_frozen_specification(specification)
    _validate_matrix(train, "train")
    validate_scoring_authorization(authorization, train, (HISTORICAL_TRAIN,))
    groups = source_feature_groups(train)
    discrete = ["=" in name for name in train.feature_names]
    scores = mutual_info_classif(
        train.values,
        train.targets,
        discrete_features=discrete,
        n_neighbors=specification.mutual_information_neighbors,
        random_state=specification.random_seed,
    )
    return tuple(
        {
            "source_feature": source,
            "output_scores": [
                {"output_feature": train.feature_names[index], "mutual_information": float(scores[index])}
                for index in indices
            ],
            "maximum_mutual_information": max(float(scores[index]) for index in indices),
        }
        for source, indices in groups
    )


def shallow_feature_models(
    train: ModelMatrix,
    validation: ModelMatrix,
    train_authorization: ScoringAuthorization,
    validation_authorization: ScoringAuthorization,
    specification: DiagnosticSpecification = FROZEN_DIAGNOSTIC_SPECIFICATION,
) -> tuple[dict[str, Any], ...]:
    """Fit one train-only decision stump per source group and score validation."""

    _validate_frozen_specification(specification)
    _validate_compatible_matrices(train, validation)
    validate_scoring_authorization(train_authorization, train, (HISTORICAL_TRAIN,))
    validate_scoring_authorization(
        validation_authorization, validation, (NON_FINAL_VALIDATION,)
    )
    results = []
    for source, indices in source_feature_groups(train):
        estimator = DecisionTreeClassifier(
            criterion=specification.shallow_criterion,
            splitter="best",
            max_depth=specification.shallow_max_depth,
            min_samples_leaf=specification.shallow_min_samples_leaf,
            random_state=specification.random_seed,
        )
        train_values = _select_columns(train, indices)
        validation_values = _select_columns(validation, indices)
        estimator.fit(train_values, train.targets)
        probabilities = tuple(float(row[1]) for row in estimator.predict_proba(validation_values))
        results.append(
            {
                "source_feature": source,
                "output_features": [train.feature_names[index] for index in indices],
                "fit_partition": "train",
                "score_partition": "validation",
                "metrics": _probability_metrics(validation, probabilities),
                "prediction_sha256": _prediction_digest(validation, probabilities),
                "trained_depth": int(estimator.get_depth()),
                "leaf_count": int(estimator.get_n_leaves()),
            }
        )
    return tuple(results)


def identifier_and_cardinality_checks(
    train: ModelMatrix,
    validation: ModelMatrix,
    train_authorization: ScoringAuthorization,
    validation_authorization: ScoringAuthorization,
) -> tuple[dict[str, Any], ...]:
    """Screen reviewed source groups for identifier names and row-pattern cardinality."""

    _validate_compatible_matrices(train, validation)
    validate_scoring_authorization(train_authorization, train, (HISTORICAL_TRAIN,))
    validate_scoring_authorization(
        validation_authorization, validation, (NON_FINAL_VALIDATION,)
    )
    results = []
    validation_groups = dict(source_feature_groups(validation))
    for source, indices in source_feature_groups(train):
        output_names = tuple(train.feature_names[index] for index in indices)
        identifier_matches = list(identifier_token_matches(source, output_names))
        train_patterns = _select_columns(train, indices)
        validation_patterns = _select_columns(validation, validation_groups[source])
        train_counts = Counter(train_patterns)
        validation_counts = Counter(validation_patterns)
        train_unique = len(train_counts)
        train_ratio = train_unique / len(train_patterns)
        dominant_ratio = max(train_counts.values()) / len(train_patterns)
        results.append(
            {
                "source_feature": source,
                "output_features": list(output_names),
                "identifier_token_matches": identifier_matches,
                "train_unique_patterns": train_unique,
                "train_uniqueness_ratio": train_ratio,
                "train_dominant_pattern_ratio": dominant_ratio,
                "validation_unique_patterns": len(validation_counts),
                "validation_uniqueness_ratio": len(validation_counts) / len(validation_patterns),
                "constant_in_train": train_unique == 1,
                "near_constant_in_train": train_unique > 1 and dominant_ratio >= NEAR_CONSTANT_RATIO,
                "high_cardinality_in_train": train_unique > 1 and train_ratio >= HIGH_CARDINALITY_RATIO,
            }
        )
    return tuple(results)


def identifier_token_matches(source_name: str, output_names: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Return suspicious identifier tokens without flagging benign `policy_age_days`."""

    tokens = set(_name_tokens(source_name))
    for name in output_names:
        tokens.update(_name_tokens(name.split("=", 1)[0]))
    matches = tokens & IDENTIFIER_TOKENS
    if "policy" in matches and not ({"id", "key", "uuid", "guid"} & tokens):
        matches.remove("policy")
    return tuple(sorted(matches))


def diagnostic_flags(
    mutual_information: tuple[dict[str, Any], ...],
    shallow_models: tuple[dict[str, Any], ...],
    cardinality: tuple[dict[str, Any], ...],
    specification: DiagnosticSpecification = FROZEN_DIAGNOSTIC_SPECIFICATION,
) -> tuple[dict[str, str], ...]:
    """Apply frozen mechanical screens before targeted perturbation."""

    _validate_frozen_specification(specification)
    flags: list[dict[str, str]] = []
    for item in mutual_information:
        if item["maximum_mutual_information"] >= specification.strong_mutual_information:
            flags.append(_flag(item["source_feature"], "strong_mutual_information"))
    for item in shallow_models:
        metrics = item["metrics"]
        if metrics["roc_auc"] >= specification.strong_shallow_auc:
            flags.append(_flag(item["source_feature"], "strong_shallow_auc"))
        if metrics["log_loss"] <= specification.strong_shallow_log_loss:
            flags.append(_flag(item["source_feature"], "strong_shallow_log_loss"))
    for item in cardinality:
        source = item["source_feature"]
        if item["identifier_token_matches"]:
            flags.append(_flag(source, "identifier_token"))
        if item["constant_in_train"]:
            flags.append(_flag(source, "constant"))
        if item["near_constant_in_train"]:
            flags.append(_flag(source, "near_constant"))
        if item["high_cardinality_in_train"]:
            flags.append(_flag(source, "high_cardinality"))
    return tuple(sorted(flags, key=lambda value: value["flag_id"]))


def targeted_permutation_checks(
    logistic: FittedLogisticBaseline,
    boosted: FittedBoostedModel,
    validation: ModelMatrix,
    validation_authorization: ScoringAuthorization,
    targeted_sources: tuple[str, ...],
    specification: DiagnosticSpecification = FROZEN_DIAGNOSTIC_SPECIFICATION,
) -> tuple[dict[str, Any], ...]:
    """Permute flagged validation groups and score unchanged frozen models."""

    import random

    _validate_frozen_specification(specification)
    _validate_matrix(validation, "validation")
    validate_scoring_authorization(
        validation_authorization, validation, (NON_FINAL_VALIDATION,)
    )
    groups = dict(source_feature_groups(validation))
    if len(set(targeted_sources)) != len(targeted_sources) or any(source not in groups for source in targeted_sources):
        raise ValueError("targeted permutation sources are duplicated or unknown")
    baseline_probabilities = {
        "logistic_regression": predict_positive_probabilities(
            logistic, validation, validation_authorization
        ),
        "xgboost": predict_boosted_probabilities(
            boosted, validation, validation_authorization
        ),
    }
    baseline_metrics = {
        name: _probability_metrics(validation, values) for name, values in baseline_probabilities.items()
    }
    results = []
    for source in sorted(targeted_sources):
        order = list(range(len(validation.values)))
        random.Random(f"{specification.random_seed}:{source}").shuffle(order)
        indices = groups[source]
        rows = [list(row) for row in validation.values]
        for destination, source_row in enumerate(order):
            for column in indices:
                rows[destination][column] = validation.values[source_row][column]
        permuted = replace(validation, values=tuple(tuple(row) for row in rows))
        derivative_authorization = authorize_diagnostic_derivative(
            validation_authorization,
            validation,
            permuted,
            transformation={
                "kind": "source_feature_permutation",
                "source_feature": source,
                "random_seed": specification.random_seed,
                "order_sha256": sha256(
                    json.dumps(order, separators=(",", ":")).encode()
                ).hexdigest(),
            },
        )
        model_results = {}
        for name, predictor in (
            ("logistic_regression", predict_positive_probabilities),
            ("xgboost", predict_boosted_probabilities),
        ):
            probabilities = predictor(
                logistic if name == "logistic_regression" else boosted,
                permuted,
                derivative_authorization,
            )
            metrics = _probability_metrics(permuted, probabilities)
            model_results[name] = {
                "metrics": metrics,
                "prediction_sha256": _prediction_digest(permuted, probabilities),
                "delta_log_loss": metrics["log_loss"] - baseline_metrics[name]["log_loss"],
                "delta_roc_auc": metrics["roc_auc"] - baseline_metrics[name]["roc_auc"],
            }
        results.append(
            {
                "source_feature": source,
                "partition": "validation",
                "permutation_order_sha256": sha256(json.dumps(order, separators=(",", ":")).encode()).hexdigest(),
                "models": model_results,
            }
        )
    return tuple(results)


def perturbation_flags(
    results: tuple[dict[str, Any], ...],
    specification: DiagnosticSpecification = FROZEN_DIAGNOSTIC_SPECIFICATION,
) -> tuple[dict[str, str], ...]:
    _validate_frozen_specification(specification)
    flags = []
    for result in results:
        for model, evidence in result["models"].items():
            if evidence["delta_log_loss"] >= specification.material_log_loss_increase:
                flags.append(_flag(result["source_feature"], f"material_permutation_log_loss:{model}"))
            if abs(evidence["delta_roc_auc"]) >= specification.material_auc_change:
                flags.append(_flag(result["source_feature"], f"material_permutation_auc:{model}"))
    return tuple(sorted(flags, key=lambda value: value["flag_id"]))


def validate_dispositions(
    flags: tuple[dict[str, str], ...], dispositions: Mapping[str, Mapping[str, Any]]
) -> tuple[dict[str, Any], ...]:
    """Require one governed disposition for every mechanically flagged source."""

    by_source: dict[str, list[str]] = {}
    for flag in flags:
        by_source.setdefault(flag["source_feature"], []).append(flag["flag_id"])
    if set(dispositions) != set(by_source):
        raise ValueError("dispositions must match the complete set of flagged source features")
    validated = []
    for source in sorted(by_source):
        value = dispositions[source]
        decision = value.get("decision")
        if decision not in {"allow", "exclude", "investigate"}:
            raise ValueError(f"invalid disposition for {source}")
        required = ("rationale", "owner", "decision_date", "follow_up")
        if any(not isinstance(value.get(key), str) or not value[key].strip() for key in required):
            raise ValueError(f"incomplete disposition for {source}")
        validated.append(
            {
                "source_feature": source,
                "flag_ids": sorted(by_source[source]),
                "decision": decision,
                **{key: value[key] for key in required},
            }
        )
    return tuple(validated)


def _validate_frozen_specification(specification: DiagnosticSpecification) -> None:
    if specification != FROZEN_DIAGNOSTIC_SPECIFICATION:
        raise ValueError("diagnostic specification is not frozen")
    if sklearn_version != "1.7.2":
        raise ValueError("installed scikit-learn version does not match the frozen dependency")


def _validate_compatible_matrices(train: ModelMatrix, validation: ModelMatrix) -> None:
    _validate_matrix(train, "train")
    _validate_matrix(validation, "validation")
    if train.feature_names != validation.feature_names:
        raise ValueError("diagnostic matrices do not share frozen feature names and order")


def _validate_matrix(matrix: ModelMatrix, expected: str | None = None) -> None:
    if matrix.partition not in PERMITTED_PARTITIONS:
        raise ValueError(f"diagnostic partition is sealed or unsupported: {matrix.partition}")
    if expected is not None and matrix.partition != expected:
        raise ValueError(f"expected {expected} diagnostic matrix")
    count = len(matrix.observation_ids)
    if count == 0 or len(matrix.values) != count or len(matrix.targets) != count:
        raise ValueError("diagnostic matrix rows and sidecars are empty or misaligned")
    if len(set(matrix.observation_ids)) != count:
        raise ValueError("diagnostic matrix contains duplicate observation IDs")
    width = len(matrix.feature_names)
    if width == 0 or len(set(matrix.feature_names)) != width:
        raise ValueError("diagnostic feature names are empty or duplicated")
    if any(len(row) != width for row in matrix.values):
        raise ValueError("diagnostic matrix feature width is inconsistent")
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) for row in matrix.values for value in row):
        raise ValueError("diagnostic matrix contains non-finite or non-numeric values")
    if any(target not in (0, 1) or isinstance(target, bool) for target in matrix.targets):
        raise ValueError("diagnostic targets must be binary integers")


def _select_columns(matrix: ModelMatrix, indices: tuple[int, ...]) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(row[index] for index in indices) for row in matrix.values)


def _name_tokens(name: str) -> tuple[str, ...]:
    return tuple(token for token in re.split(r"[^a-z0-9]+", name.lower()) if token)


def _probability_metrics(matrix: ModelMatrix, probabilities: tuple[float, ...]) -> dict[str, float | int]:
    if len(probabilities) != len(matrix.targets) or set(matrix.targets) != {0, 1}:
        raise ValueError("diagnostic probabilities or target classes are invalid")
    return {
        "record_count": len(matrix.targets),
        "log_loss": float(log_loss(matrix.targets, probabilities, labels=[0, 1])),
        "roc_auc": float(roc_auc_score(matrix.targets, probabilities)),
        "brier_score": float(brier_score_loss(matrix.targets, probabilities)),
    }


def _prediction_digest(matrix: ModelMatrix, probabilities: tuple[float, ...]) -> str:
    material = {
        "partition": matrix.partition,
        "observation_ids": list(matrix.observation_ids),
        "probabilities": [round(value, ARTIFACT_DECIMAL_PLACES) for value in probabilities],
    }
    return sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _flag(source: str, rule: str) -> dict[str, str]:
    return {"flag_id": f"{source}:{rule}", "source_feature": source, "rule": rule}
