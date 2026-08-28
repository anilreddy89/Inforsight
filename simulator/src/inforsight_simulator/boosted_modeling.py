"""Frozen Phase 2.06 XGBoost candidate and sealed-test evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from typing import Any

import xgboost as xgb
from xgboost import XGBClassifier

from .features import FEATURE_DICTIONARY_VERSION, FEATURE_PIPELINE_VERSION
from .modeling import BaselineEvaluation, BaselineMetrics, evaluate_logistic_baseline
from .preprocessing import ModelMatrix, matrix_digest
from .scoring_authorization import (
    InferenceMatrix,
    ScoringAuthorization,
    validate_inference_matrix,
    validate_scoring_authorization,
)


BOOSTED_MODEL_VERSION = "1.0.0"
BOOSTED_TRAINING_CONFIGURATION_VERSION = "1.0.0"
BOOSTED_RANDOM_SEED = 20260817
XGBOOST_PINNED_VERSION = "3.3.0"
ARTIFACT_DECIMAL_PLACES = 10


@dataclass(frozen=True)
class BoostedModelSpecification:
    objective: str = "binary:logistic"
    n_estimators: int = 25
    learning_rate: float = 0.1
    max_depth: int = 2
    min_child_weight: float = 2.0
    gamma: float = 0.0
    subsample: float = 1.0
    colsample_bytree: float = 1.0
    colsample_bylevel: float = 1.0
    colsample_bynode: float = 1.0
    reg_alpha: float = 0.0
    reg_lambda: float = 1.0
    scale_pos_weight: float = 1.0
    base_score: float = 0.5
    tree_method: str = "exact"
    n_jobs: int = 1
    random_seed: int = BOOSTED_RANDOM_SEED
    eval_metric: str = "logloss"
    early_stopping_rounds: None = None
    missing: float = float("nan")
    verbosity: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "max_depth": self.max_depth,
            "min_child_weight": self.min_child_weight,
            "gamma": self.gamma,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "colsample_bylevel": self.colsample_bylevel,
            "colsample_bynode": self.colsample_bynode,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "scale_pos_weight": self.scale_pos_weight,
            "base_score": self.base_score,
            "tree_method": self.tree_method,
            "n_jobs": self.n_jobs,
            "random_seed": self.random_seed,
            "eval_metric": self.eval_metric,
            "early_stopping_rounds": self.early_stopping_rounds,
            "missing": "NaN",
            "verbosity": self.verbosity,
        }


FROZEN_BOOSTED_SPECIFICATION = BoostedModelSpecification()


@dataclass(frozen=True)
class FittedBoostedModel:
    model_version: str
    training_configuration_version: str
    feature_pipeline_version: str
    feature_dictionary_version: str
    xgboost_version: str
    specification: BoostedModelSpecification
    training_observation_ids: tuple[str, ...]
    training_matrix_sha256: str
    feature_names: tuple[str, ...]
    model_json: str
    model_json_sha256: str
    trained_tree_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "training_configuration_version": self.training_configuration_version,
            "feature_pipeline_version": self.feature_pipeline_version,
            "feature_dictionary_version": self.feature_dictionary_version,
            "xgboost_version": self.xgboost_version,
            "specification": self.specification.to_dict(),
            "training_observation_ids": list(self.training_observation_ids),
            "training_matrix_sha256": self.training_matrix_sha256,
            "feature_names": list(self.feature_names),
            "model_json": self.model_json,
            "model_json_sha256": self.model_json_sha256,
            "trained_tree_count": self.trained_tree_count,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> FittedBoostedModel:
        try:
            result = cls(
                model_version=value["model_version"],
                training_configuration_version=value["training_configuration_version"],
                feature_pipeline_version=value["feature_pipeline_version"],
                feature_dictionary_version=value["feature_dictionary_version"],
                xgboost_version=value["xgboost_version"],
                specification=_specification_from_dict(value["specification"]),
                training_observation_ids=tuple(value["training_observation_ids"]),
                training_matrix_sha256=value["training_matrix_sha256"],
                feature_names=tuple(value["feature_names"]),
                model_json=value["model_json"],
                model_json_sha256=value["model_json_sha256"],
                trained_tree_count=value["trained_tree_count"],
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("malformed fitted boosted-model state") from exc
        _validate_fitted(result)
        return result


def fit_boosted_model(
    train: ModelMatrix,
    specification: BoostedModelSpecification = FROZEN_BOOSTED_SPECIFICATION,
) -> FittedBoostedModel:
    """Fit the single frozen candidate on the exact train partition only."""

    _validate_matrix(train, expected_partition="train")
    if specification != FROZEN_BOOSTED_SPECIFICATION:
        raise ValueError("boosted-model specification is not the frozen configuration")
    if set(train.targets) != {0, 1}:
        raise ValueError("training targets must contain both binary classes")
    if xgb.__version__ != XGBOOST_PINNED_VERSION:
        raise ValueError("installed XGBoost version does not match the frozen dependency")
    estimator = XGBClassifier(
        objective=specification.objective,
        n_estimators=specification.n_estimators,
        learning_rate=specification.learning_rate,
        max_depth=specification.max_depth,
        min_child_weight=specification.min_child_weight,
        gamma=specification.gamma,
        subsample=specification.subsample,
        colsample_bytree=specification.colsample_bytree,
        colsample_bylevel=specification.colsample_bylevel,
        colsample_bynode=specification.colsample_bynode,
        reg_alpha=specification.reg_alpha,
        reg_lambda=specification.reg_lambda,
        scale_pos_weight=specification.scale_pos_weight,
        base_score=specification.base_score,
        tree_method=specification.tree_method,
        n_jobs=specification.n_jobs,
        random_state=specification.random_seed,
        eval_metric=specification.eval_metric,
        missing=specification.missing,
        verbosity=specification.verbosity,
    )
    estimator.fit(train.values, train.targets, verbose=False)
    if tuple(int(value) for value in estimator.classes_) != (0, 1):
        raise ValueError("estimator class ordering is not the required (0, 1)")
    booster = estimator.get_booster()
    model_bytes = bytes(booster.save_raw(raw_format="json"))
    result = FittedBoostedModel(
        model_version=BOOSTED_MODEL_VERSION,
        training_configuration_version=BOOSTED_TRAINING_CONFIGURATION_VERSION,
        feature_pipeline_version=FEATURE_PIPELINE_VERSION,
        feature_dictionary_version=FEATURE_DICTIONARY_VERSION,
        xgboost_version=xgb.__version__,
        specification=specification,
        training_observation_ids=train.observation_ids,
        training_matrix_sha256=matrix_digest(train),
        feature_names=train.feature_names,
        model_json=model_bytes.decode("utf-8"),
        model_json_sha256=sha256(model_bytes).hexdigest(),
        trained_tree_count=len(booster.get_dump()),
    )
    _validate_fitted(result)
    return result


def predict_boosted_probabilities(
    fitted: FittedBoostedModel,
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
        raise ValueError("model matrix feature names do not match fitted feature order")
    if matrix.partition == "train":
        if matrix.observation_ids != fitted.training_observation_ids:
            raise ValueError("train matrix IDs do not match fitted training membership")
        if matrix_digest(matrix) != fitted.training_matrix_sha256:
            raise ValueError("train matrix digest does not match fitted training data")
    booster = _restore_booster(fitted)
    values = booster.predict(xgb.DMatrix(matrix.values, feature_names=list(matrix.feature_names)))
    probabilities = tuple(float(value) for value in values)
    if len(probabilities) != len(matrix.targets) or any(
        not isfinite(value) or value < 0.0 or value > 1.0 for value in probabilities
    ):
        raise ValueError("boosted-model probabilities are invalid")
    return probabilities


def predict_boosted_inference(
    fitted: FittedBoostedModel, matrix: InferenceMatrix
) -> tuple[float, ...]:
    """Produce probabilities for unlabeled inputs without experiment authority or metrics."""

    _validate_fitted(fitted)
    validate_inference_matrix(matrix, fitted.feature_names)
    booster = _restore_booster(fitted)
    values = booster.predict(xgb.DMatrix(matrix.values, feature_names=list(matrix.feature_names)))
    probabilities = tuple(float(value) for value in values)
    if any(not isfinite(value) or value < 0.0 or value > 1.0 for value in probabilities):
        raise ValueError("boosted-model probabilities are invalid")
    return probabilities


def evaluate_boosted_model(
    fitted: FittedBoostedModel,
    matrix: ModelMatrix,
    authorization: ScoringAuthorization,
) -> BaselineEvaluation:
    probabilities = predict_boosted_probabilities(fitted, matrix, authorization)
    if set(matrix.targets) != {0, 1}:
        raise ValueError("evaluation targets must contain both binary classes")
    # Reuse the frozen Phase 2.05 metric implementation with a prediction-only adapter.
    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

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


def fitted_boosted_bytes(fitted: FittedBoostedModel) -> bytes:
    _validate_fitted(fitted)
    return (json.dumps(fitted.to_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def compare_models(
    logistic_fitted,
    boosted_fitted: FittedBoostedModel,
    matrix: ModelMatrix,
    authorization: ScoringAuthorization,
) -> dict[str, Any]:
    """Evaluate both frozen models on the same permitted matrix."""

    logistic = evaluate_logistic_baseline(logistic_fitted, matrix, authorization)
    boosted = evaluate_boosted_model(boosted_fitted, matrix, authorization)
    if logistic.metrics.record_count != boosted.metrics.record_count:
        raise ValueError("model comparison membership is inconsistent")
    return {
        "observation_ids": list(matrix.observation_ids),
        "logistic_regression": {
            "metrics": logistic.metrics.to_dict(),
            "prediction_sha256": logistic.prediction_sha256,
        },
        "xgboost": {
            "metrics": boosted.metrics.to_dict(),
            "prediction_sha256": boosted.prediction_sha256,
        },
    }


def _restore_booster(fitted: FittedBoostedModel) -> xgb.Booster:
    booster = xgb.Booster({"nthread": fitted.specification.n_jobs})
    try:
        booster.load_model(bytearray(fitted.model_json.encode("utf-8")))
    except xgb.core.XGBoostError as exc:
        raise ValueError("fitted boosted-model JSON cannot be reconstructed") from exc
    return booster


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
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)
        for row in matrix.values for value in row
    ):
        raise ValueError("model matrix contains non-finite or non-numeric values")
    if any(isinstance(target, bool) or target not in (0, 1) for target in matrix.targets):
        raise ValueError("model matrix targets must be binary integers")


def _validate_fitted(fitted: FittedBoostedModel) -> None:
    if fitted.model_version != BOOSTED_MODEL_VERSION:
        raise ValueError("unsupported boosted-model version")
    if fitted.training_configuration_version != BOOSTED_TRAINING_CONFIGURATION_VERSION:
        raise ValueError("unsupported boosted training configuration version")
    if fitted.feature_pipeline_version != FEATURE_PIPELINE_VERSION or fitted.feature_dictionary_version != FEATURE_DICTIONARY_VERSION:
        raise ValueError("fitted boosted model is incompatible with the feature contract")
    if fitted.xgboost_version != XGBOOST_PINNED_VERSION or xgb.__version__ != XGBOOST_PINNED_VERSION:
        raise ValueError("fitted boosted model XGBoost version is incompatible")
    if fitted.specification != FROZEN_BOOSTED_SPECIFICATION:
        raise ValueError("fitted boosted-model specification is not frozen")
    if not fitted.training_observation_ids or len(set(fitted.training_observation_ids)) != len(fitted.training_observation_ids):
        raise ValueError("fitted boosted-model training IDs are empty or duplicated")
    if not fitted.feature_names or len(set(fitted.feature_names)) != len(fitted.feature_names):
        raise ValueError("fitted boosted-model feature names are empty or duplicated")
    if fitted.trained_tree_count != fitted.specification.n_estimators:
        raise ValueError("fitted boosted-model training evidence is incomplete")
    model_bytes = fitted.model_json.encode("utf-8")
    if sha256(model_bytes).hexdigest() != fitted.model_json_sha256:
        raise ValueError("fitted boosted-model JSON digest is invalid")
    try:
        parsed = json.loads(fitted.model_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("fitted boosted-model state is not valid JSON") from exc
    if not isinstance(parsed, dict) or "learner" not in parsed:
        raise ValueError("fitted boosted-model JSON has an invalid structure")


def _specification_from_dict(value: dict[str, Any]) -> BoostedModelSpecification:
    if value.get("missing") != "NaN":
        raise ValueError("unsupported missing-value sentinel")
    return BoostedModelSpecification(
        objective=value["objective"], n_estimators=value["n_estimators"],
        learning_rate=value["learning_rate"], max_depth=value["max_depth"],
        min_child_weight=value["min_child_weight"], gamma=value["gamma"],
        subsample=value["subsample"], colsample_bytree=value["colsample_bytree"],
        colsample_bylevel=value["colsample_bylevel"], colsample_bynode=value["colsample_bynode"],
        reg_alpha=value["reg_alpha"], reg_lambda=value["reg_lambda"],
        scale_pos_weight=value["scale_pos_weight"], base_score=value["base_score"],
        tree_method=value["tree_method"], n_jobs=value["n_jobs"],
        random_seed=value["random_seed"], eval_metric=value["eval_metric"],
        early_stopping_rounds=value["early_stopping_rounds"], verbosity=value["verbosity"],
    )


def _artifact_float(value: float) -> float:
    rounded = round(value, ARTIFACT_DECIMAL_PLACES)
    return 0.0 if rounded == 0.0 else rounded
