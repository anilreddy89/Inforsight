"""Fail-closed authorization for governed experiment scoring."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from typing import Iterable

from .features import FEATURE_DICTIONARY_VERSION, FEATURE_PIPELINE_VERSION
from .preprocessing import FeaturePipelineResult, ModelMatrix, fitted_state_bytes, matrix_digest


SCORING_AUTHORIZATION_VERSION = "1.0.0"
HISTORICAL_TRAIN = "historical_train"
NON_FINAL_VALIDATION = "non_final_validation"
DIAGNOSTIC_DERIVATIVE = "diagnostic_derivative"
PERMITTED_BASE_PURPOSES = (HISTORICAL_TRAIN, NON_FINAL_VALIDATION)
PERMITTED_MODEL_PURPOSES = PERMITTED_BASE_PURPOSES + (DIAGNOSTIC_DERIVATIVE,)


@dataclass(frozen=True)
class ScoringAuthorization:
    """Immutable evidence that one exact labeled matrix has an approved local use."""

    contract_version: str
    purpose: str
    partition: str
    observation_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    matrix_sha256: str
    training_matrix_sha256: str
    preprocessor_sha256: str
    source_authorization_sha256: str | None
    transformation_sha256: str | None
    authorization_sha256: str


@dataclass(frozen=True)
class ScoringAuthorizations:
    train: ScoringAuthorization
    validation: ScoringAuthorization


@dataclass(frozen=True)
class InferenceMatrix:
    """Unlabeled feature inputs; experiment membership and targets are deliberately absent."""

    feature_names: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]


def authorize_feature_pipeline(pipeline: FeaturePipelineResult) -> ScoringAuthorizations:
    """Create authority from the named fields of one validated pipeline result.

    The v1 test field is deliberately ignored and cannot receive authorization.
    This is a local integrity boundary, not access control against code modification.
    """

    partition_ids = dict(pipeline.preprocessor.partition_observation_ids)
    if pipeline.train.partition != "train" or pipeline.validation.partition != "validation":
        raise ValueError("pipeline partition labels do not match their trusted fields")
    if pipeline.train.observation_ids != partition_ids.get("train"):
        raise ValueError("train matrix does not match frozen preprocessing membership")
    if pipeline.validation.observation_ids != partition_ids.get("validation"):
        raise ValueError("validation matrix does not match frozen preprocessing membership")
    if pipeline.train.feature_names != pipeline.preprocessor.output_feature_names:
        raise ValueError("train feature contract does not match fitted preprocessing")
    if pipeline.validation.feature_names != pipeline.preprocessor.output_feature_names:
        raise ValueError("validation feature contract does not match fitted preprocessing")
    preprocessor_sha256 = sha256(fitted_state_bytes(pipeline.preprocessor)).hexdigest()
    training_matrix_sha256 = matrix_digest(pipeline.train)
    return ScoringAuthorizations(
        train=_new_authorization(
            pipeline.train,
            HISTORICAL_TRAIN,
            training_matrix_sha256,
            preprocessor_sha256,
            None,
            None,
        ),
        validation=_new_authorization(
            pipeline.validation,
            NON_FINAL_VALIDATION,
            training_matrix_sha256,
            preprocessor_sha256,
            None,
            None,
        ),
    )


def authorize_diagnostic_derivative(
    base: ScoringAuthorization,
    base_matrix: ModelMatrix,
    derived_matrix: ModelMatrix,
    *,
    transformation: dict[str, object],
) -> ScoringAuthorization:
    """Authorize one deterministic derivative of an authorized validation matrix."""

    validate_scoring_authorization(base, base_matrix, (NON_FINAL_VALIDATION,))
    if derived_matrix.partition != "validation":
        raise ValueError("diagnostic derivatives must retain validation provenance")
    if derived_matrix.observation_ids != base_matrix.observation_ids:
        raise ValueError("diagnostic derivative changed observation membership or order")
    if derived_matrix.feature_names != base_matrix.feature_names:
        raise ValueError("diagnostic derivative changed the feature contract")
    if derived_matrix.targets != base_matrix.targets:
        raise ValueError("diagnostic derivative changed evaluation targets")
    encoded = json.dumps(transformation, sort_keys=True, separators=(",", ":")).encode("utf-8")
    transformation_sha256 = sha256(encoded).hexdigest()
    return _new_authorization(
        derived_matrix,
        DIAGNOSTIC_DERIVATIVE,
        base.training_matrix_sha256,
        base.preprocessor_sha256,
        base.authorization_sha256,
        transformation_sha256,
    )


def validate_scoring_authorization(
    authorization: ScoringAuthorization,
    matrix: ModelMatrix,
    allowed_purposes: Iterable[str] = PERMITTED_MODEL_PURPOSES,
) -> None:
    """Fail before prediction unless authority matches the complete labeled matrix."""

    if authorization.contract_version != SCORING_AUTHORIZATION_VERSION:
        raise ValueError("unsupported scoring authorization version")
    if authorization.purpose not in tuple(allowed_purposes):
        raise ValueError(f"scoring purpose is not authorized: {authorization.purpose}")
    if authorization.partition not in ("train", "validation"):
        raise ValueError("test and final-holdout scoring are not authorized")
    if matrix.partition != authorization.partition:
        raise ValueError("matrix partition does not match scoring authorization")
    if matrix.observation_ids != authorization.observation_ids:
        raise ValueError("matrix membership or row order does not match scoring authorization")
    if matrix.feature_names != authorization.feature_names:
        raise ValueError("matrix feature contract does not match scoring authorization")
    if matrix_digest(matrix) != authorization.matrix_sha256:
        raise ValueError("matrix digest does not match scoring authorization")
    expected = _authorization_digest(
        authorization.contract_version,
        authorization.purpose,
        authorization.partition,
        authorization.observation_ids,
        authorization.feature_names,
        authorization.matrix_sha256,
        authorization.training_matrix_sha256,
        authorization.preprocessor_sha256,
        authorization.source_authorization_sha256,
        authorization.transformation_sha256,
    )
    if authorization.authorization_sha256 != expected:
        raise ValueError("scoring authorization integrity digest is invalid")
    if authorization.purpose == DIAGNOSTIC_DERIVATIVE:
        if not authorization.source_authorization_sha256 or not authorization.transformation_sha256:
            raise ValueError("diagnostic derivative authorization lacks provenance")
    elif authorization.source_authorization_sha256 or authorization.transformation_sha256:
        raise ValueError("base scoring authorization contains derivative provenance")


def validate_inference_matrix(matrix: InferenceMatrix, expected_features: tuple[str, ...]) -> None:
    if matrix.feature_names != expected_features:
        raise ValueError("inference feature names do not match fitted feature order")
    if not matrix.values:
        raise ValueError("inference matrix must contain at least one row")
    width = len(matrix.feature_names)
    if width == 0 or len(set(matrix.feature_names)) != width:
        raise ValueError("inference feature names are empty or duplicated")
    if any(len(row) != width for row in matrix.values):
        raise ValueError("inference feature width is inconsistent")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)
        for row in matrix.values
        for value in row
    ):
        raise ValueError("inference matrix contains non-finite or non-numeric values")


def inference_matrix_from_model_matrix(matrix: ModelMatrix) -> InferenceMatrix:
    """Explicitly discard experiment identity and labels for ordinary inference."""

    return InferenceMatrix(feature_names=matrix.feature_names, values=matrix.values)


def _new_authorization(
    matrix: ModelMatrix,
    purpose: str,
    training_matrix_sha256: str,
    preprocessor_sha256: str,
    source_authorization_sha256: str | None,
    transformation_sha256: str | None,
) -> ScoringAuthorization:
    if purpose not in PERMITTED_MODEL_PURPOSES:
        raise ValueError("unsupported scoring purpose")
    matrix_sha256 = matrix_digest(matrix)
    digest = _authorization_digest(
        SCORING_AUTHORIZATION_VERSION,
        purpose,
        matrix.partition,
        matrix.observation_ids,
        matrix.feature_names,
        matrix_sha256,
        training_matrix_sha256,
        preprocessor_sha256,
        source_authorization_sha256,
        transformation_sha256,
    )
    return ScoringAuthorization(
        contract_version=SCORING_AUTHORIZATION_VERSION,
        purpose=purpose,
        partition=matrix.partition,
        observation_ids=matrix.observation_ids,
        feature_names=matrix.feature_names,
        matrix_sha256=matrix_sha256,
        training_matrix_sha256=training_matrix_sha256,
        preprocessor_sha256=preprocessor_sha256,
        source_authorization_sha256=source_authorization_sha256,
        transformation_sha256=transformation_sha256,
        authorization_sha256=digest,
    )


def _authorization_digest(
    contract_version: str,
    purpose: str,
    partition: str,
    observation_ids: tuple[str, ...],
    feature_names: tuple[str, ...],
    matrix_sha256: str,
    training_matrix_sha256: str,
    preprocessor_sha256: str,
    source_authorization_sha256: str | None,
    transformation_sha256: str | None,
) -> str:
    material = {
        "contract_version": contract_version,
        "purpose": purpose,
        "partition": partition,
        "observation_ids": list(observation_ids),
        "feature_names": list(feature_names),
        "matrix_sha256": matrix_sha256,
        "training_matrix_sha256": training_matrix_sha256,
        "preprocessor_sha256": preprocessor_sha256,
        "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
        "feature_dictionary_version": FEATURE_DICTIONARY_VERSION,
        "source_authorization_sha256": source_authorization_sha256,
        "transformation_sha256": transformation_sha256,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()
