"""Deterministic train-only logistic-regression baseline."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import exp, isfinite
from typing import Any
import warnings

from sklearn import __version__ as sklearn_version
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from .features import FEATURE_DICTIONARY_VERSION, FEATURE_PIPELINE_VERSION
from .preprocessing import ModelMatrix, matrix_digest
from .scoring_authorization import (
    InferenceMatrix,
    ScoringAuthorization,
    validate_inference_matrix,
    validate_scoring_authorization,
)


LOGISTIC_BASELINE_VERSION = "1.0.0"
TRAINING_CONFIGURATION_VERSION = "1.0.0"
BASELINE_RANDOM_SEED = 20260817
ARTIFACT_DECIMAL_PLACES = 10


@dataclass(frozen=True)
class LogisticBaselineSpecification:
    penalty: str = "l2"
    regularization_strength: float = 1.0
    solver: str = "liblinear"
    tolerance: float = 1e-8
    maximum_iterations: int = 1000
    fit_intercept: bool = True
    class_weight: None = None
    random_seed: int = BASELINE_RANDOM_SEED

    def to_dict(self) -> dict[str, Any]:
        return {
            "penalty": self.penalty,
            "regularization_strength": self.regularization_strength,
            "solver": self.solver,
            "tolerance": self.tolerance,
            "maximum_iterations": self.maximum_iterations,
            "fit_intercept": self.fit_intercept,
            "class_weight": self.class_weight,
            "random_seed": self.random_seed,
        }


FROZEN_LOGISTIC_SPECIFICATION = LogisticBaselineSpecification()


@dataclass(frozen=True)
class BaselineMetrics:
    partition: str
    record_count: int
    negative_count: int
    positive_count: int
    log_loss: float
    roc_auc: float
    brier_score: float
    average_predicted_probability: float
    observed_positive_fraction: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition": self.partition,
            "record_count": self.record_count,
            "class_distribution": {
                "negative": self.negative_count,
                "positive": self.positive_count,
            },
            "log_loss": self.log_loss,
            "roc_auc": self.roc_auc,
            "brier_score": self.brier_score,
            "average_predicted_probability": self.average_predicted_probability,
            "observed_positive_fraction": self.observed_positive_fraction,
        }


@dataclass(frozen=True)
class BaselineEvaluation:
    metrics: BaselineMetrics
    prediction_sha256: str


@dataclass(frozen=True)
class FittedLogisticBaseline:
    baseline_version: str
    training_configuration_version: str
    feature_pipeline_version: str
    feature_dictionary_version: str
    sklearn_version: str
    specification: LogisticBaselineSpecification
    training_observation_ids: tuple[str, ...]
    training_matrix_sha256: str
    feature_names: tuple[str, ...]
    intercept: float
    coefficients: tuple[float, ...]
    iteration_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_version": self.baseline_version,
            "training_configuration_version": self.training_configuration_version,
            "feature_pipeline_version": self.feature_pipeline_version,
            "feature_dictionary_version": self.feature_dictionary_version,
            "sklearn_version": self.sklearn_version,
            "specification": self.specification.to_dict(),
            "training_observation_ids": list(self.training_observation_ids),
            "training_matrix_sha256": self.training_matrix_sha256,
            "feature_names": list(self.feature_names),
            "intercept": self.intercept,
            "coefficients": list(self.coefficients),
            "iteration_count": self.iteration_count,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> FittedLogisticBaseline:
        try:
            spec_value = value["specification"]
            result = cls(
                baseline_version=value["baseline_version"],
                training_configuration_version=value["training_configuration_version"],
                feature_pipeline_version=value["feature_pipeline_version"],
                feature_dictionary_version=value["feature_dictionary_version"],
                sklearn_version=value["sklearn_version"],
                specification=LogisticBaselineSpecification(
                    penalty=spec_value["penalty"],
                    regularization_strength=spec_value["regularization_strength"],
                    solver=spec_value["solver"],
                    tolerance=spec_value["tolerance"],
                    maximum_iterations=spec_value["maximum_iterations"],
                    fit_intercept=spec_value["fit_intercept"],
                    class_weight=spec_value["class_weight"],
                    random_seed=spec_value["random_seed"],
                ),
                training_observation_ids=tuple(value["training_observation_ids"]),
                training_matrix_sha256=value["training_matrix_sha256"],
                feature_names=tuple(value["feature_names"]),
                intercept=value["intercept"],
                coefficients=tuple(value["coefficients"]),
                iteration_count=value["iteration_count"],
            )
        except (KeyError, TypeError) as exc:
            raise ValueError("malformed fitted logistic-baseline state") from exc
        _validate_fitted(result)
        return result


def fit_logistic_baseline(
    train: ModelMatrix,
    specification: LogisticBaselineSpecification = FROZEN_LOGISTIC_SPECIFICATION,
) -> FittedLogisticBaseline:
    """Fit the one frozen baseline configuration on a train matrix only."""

    _validate_matrix(train, expected_partition="train")
    if specification != FROZEN_LOGISTIC_SPECIFICATION:
        raise ValueError("logistic baseline specification is not the frozen configuration")
    if set(train.targets) != {0, 1}:
        raise ValueError("training targets must contain both binary classes")
    estimator = LogisticRegression(
        penalty=specification.penalty,
        C=specification.regularization_strength,
        solver=specification.solver,
        tol=specification.tolerance,
        max_iter=specification.maximum_iterations,
        fit_intercept=specification.fit_intercept,
        class_weight=specification.class_weight,
        random_state=specification.random_seed,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        try:
            estimator.fit(train.values, train.targets)
        except ConvergenceWarning as exc:
            raise ValueError("logistic baseline failed to converge") from exc
    if tuple(int(value) for value in estimator.classes_) != (0, 1):
        raise ValueError("estimator class ordering is not the required (0, 1)")
    coefficients = tuple(float(value) for value in estimator.coef_[0])
    intercept = float(estimator.intercept_[0])
    result = FittedLogisticBaseline(
        baseline_version=LOGISTIC_BASELINE_VERSION,
        training_configuration_version=TRAINING_CONFIGURATION_VERSION,
        feature_pipeline_version=FEATURE_PIPELINE_VERSION,
        feature_dictionary_version=FEATURE_DICTIONARY_VERSION,
        sklearn_version=sklearn_version,
        specification=specification,
        training_observation_ids=train.observation_ids,
        training_matrix_sha256=matrix_digest(train),
        feature_names=train.feature_names,
        intercept=intercept,
        coefficients=coefficients,
        iteration_count=int(estimator.n_iter_[0]),
    )
    _validate_fitted(result)
    return result


def predict_positive_probabilities(
    fitted: FittedLogisticBaseline,
    matrix: ModelMatrix,
    authorization: ScoringAuthorization,
) -> tuple[float, ...]:
    """Score one exactly authorized labeled experiment matrix."""

    _validate_fitted(fitted)
    _validate_matrix(matrix)
    validate_scoring_authorization(authorization, matrix)
    if authorization.training_matrix_sha256 != fitted.training_matrix_sha256:
        raise ValueError("scoring authorization does not match fitted training data")
    if matrix.feature_names != fitted.feature_names:
        raise ValueError("model matrix feature names do not match fitted coefficient order")
    if matrix.partition == "train":
        if matrix.observation_ids != fitted.training_observation_ids:
            raise ValueError("train matrix IDs do not match fitted training membership")
        if matrix_digest(matrix) != fitted.training_matrix_sha256:
            raise ValueError("train matrix digest does not match fitted training data")
    return tuple(_sigmoid(fitted.intercept + _dot(fitted.coefficients, row)) for row in matrix.values)


def predict_logistic_inference(
    fitted: FittedLogisticBaseline, matrix: InferenceMatrix
) -> tuple[float, ...]:
    """Produce probabilities for unlabeled inputs without experiment authority or metrics."""

    _validate_fitted(fitted)
    validate_inference_matrix(matrix, fitted.feature_names)
    return tuple(_sigmoid(fitted.intercept + _dot(fitted.coefficients, row)) for row in matrix.values)


def evaluate_logistic_baseline(
    fitted: FittedLogisticBaseline,
    matrix: ModelMatrix,
    authorization: ScoringAuthorization,
) -> BaselineEvaluation:
    probabilities = predict_positive_probabilities(fitted, matrix, authorization)
    if set(matrix.targets) != {0, 1}:
        raise ValueError("evaluation targets must contain both binary classes")
    count = len(matrix.targets)
    positive = sum(matrix.targets)
    metrics = BaselineMetrics(
        partition=matrix.partition,
        record_count=count,
        negative_count=count - positive,
        positive_count=positive,
        log_loss=float(log_loss(matrix.targets, probabilities, labels=[0, 1])),
        roc_auc=float(roc_auc_score(matrix.targets, probabilities)),
        brier_score=float(brier_score_loss(matrix.targets, probabilities)),
        average_predicted_probability=sum(probabilities) / count,
        observed_positive_fraction=positive / count,
    )
    material = json.dumps(
        {
            "partition": matrix.partition,
            "observation_ids": list(matrix.observation_ids),
            "probabilities": [_artifact_float(value) for value in probabilities],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return BaselineEvaluation(metrics, sha256(material).hexdigest())


def fitted_baseline_bytes(fitted: FittedLogisticBaseline) -> bytes:
    _validate_fitted(fitted)
    state = _canonicalize_artifact_numbers(fitted.to_dict())
    return (json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def coefficient_summary(fitted: FittedLogisticBaseline) -> tuple[dict[str, float | str], ...]:
    _validate_fitted(fitted)
    return tuple(
        {"feature_name": name, "coefficient": coefficient, "odds_ratio": exp(coefficient)}
        for name, coefficient in zip(fitted.feature_names, fitted.coefficients, strict=True)
    )


def _validate_matrix(matrix: ModelMatrix, expected_partition: str | None = None) -> None:
    if expected_partition is not None and matrix.partition != expected_partition:
        raise ValueError(f"expected {expected_partition} model matrix")
    if matrix.partition not in ("train", "validation", "test"):
        raise ValueError("unsupported model matrix partition")
    count = len(matrix.observation_ids)
    if count == 0 or len(matrix.values) != count or len(matrix.targets) != count:
        raise ValueError("model matrix rows and sidecars are empty or misaligned")
    if len(set(matrix.observation_ids)) != count:
        raise ValueError("model matrix contains duplicate observation IDs")
    width = len(matrix.feature_names)
    if width == 0 or len(set(matrix.feature_names)) != width:
        raise ValueError("model matrix feature names are empty or duplicated")
    if any(len(row) != width for row in matrix.values):
        raise ValueError("model matrix feature width is inconsistent")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) for row in matrix.values for value in row):
        raise ValueError("model matrix contains non-finite or non-numeric values")
    if any(isinstance(target, bool) or target not in (0, 1) for target in matrix.targets):
        raise ValueError("model matrix targets must be binary integers")


def _validate_fitted(fitted: FittedLogisticBaseline) -> None:
    if fitted.baseline_version != LOGISTIC_BASELINE_VERSION:
        raise ValueError("unsupported logistic baseline version")
    if fitted.training_configuration_version != TRAINING_CONFIGURATION_VERSION:
        raise ValueError("unsupported training configuration version")
    if fitted.feature_pipeline_version != FEATURE_PIPELINE_VERSION or fitted.feature_dictionary_version != FEATURE_DICTIONARY_VERSION:
        raise ValueError("fitted baseline is incompatible with the feature contract")
    if fitted.sklearn_version != sklearn_version:
        raise ValueError("fitted baseline scikit-learn version is incompatible")
    if fitted.specification != FROZEN_LOGISTIC_SPECIFICATION:
        raise ValueError("fitted baseline specification is not frozen")
    if not fitted.training_observation_ids or len(set(fitted.training_observation_ids)) != len(fitted.training_observation_ids):
        raise ValueError("fitted baseline training IDs are empty or duplicated")
    if len(fitted.feature_names) == 0 or len(fitted.feature_names) != len(fitted.coefficients):
        raise ValueError("fitted coefficients do not align with feature names")
    if not isfinite(fitted.intercept) or any(not isfinite(value) for value in fitted.coefficients):
        raise ValueError("fitted baseline contains non-finite parameters")
    if fitted.iteration_count <= 0 or fitted.iteration_count > fitted.specification.maximum_iterations:
        raise ValueError("fitted baseline iteration count is invalid")


def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        factor = exp(-value)
        return 1.0 / (1.0 + factor)
    factor = exp(value)
    return factor / (1.0 + factor)


def _artifact_float(value: float) -> float:
    """Normalize insignificant cross-platform numeric noise for artifacts only."""

    rounded = round(value, ARTIFACT_DECIMAL_PLACES)
    return 0.0 if rounded == 0.0 else rounded


def _canonicalize_artifact_numbers(value: Any) -> Any:
    if isinstance(value, float):
        return _artifact_float(value)
    if isinstance(value, dict):
        return {key: _canonicalize_artifact_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize_artifact_numbers(item) for item in value]
    if isinstance(value, tuple):
        return [_canonicalize_artifact_numbers(item) for item in value]
    return value
