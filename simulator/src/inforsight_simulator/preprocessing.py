"""Training-only fitted preprocessing for frozen temporal partitions."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import sqrt
from typing import Any, Iterable

from .features import (
    FEATURE_DICTIONARY_VERSION,
    FEATURE_PIPELINE_VERSION,
    INCLUDED_CATEGORICAL_FEATURES,
    INCLUDED_NUMERIC_FEATURES,
    ExtractedFeatureRow,
    extract_feature_row,
)
from .observations import ObservationRecord
from .splitting import TemporalSplitResult, validate_temporal_split


UNKNOWN_CATEGORY = "__unknown__"
SUPPORTED_PARTITIONS = ("train", "validation", "test")


@dataclass(frozen=True)
class NumericFit:
    source_name: str
    mean: float
    scale: float

    def to_dict(self) -> dict[str, Any]:
        return {"source_name": self.source_name, "mean": self.mean, "scale": self.scale}


@dataclass(frozen=True)
class CategoricalFit:
    source_name: str
    categories: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"source_name": self.source_name, "categories": list(self.categories)}


@dataclass(frozen=True)
class FittedPreprocessor:
    """Immutable training-derived state and frozen partition membership."""

    feature_pipeline_version: str
    feature_dictionary_version: str
    training_observation_ids: tuple[str, ...]
    partition_observation_ids: tuple[tuple[str, tuple[str, ...]], ...]
    numeric_fits: tuple[NumericFit, ...]
    categorical_fits: tuple[CategoricalFit, ...]
    output_feature_names: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_pipeline_version": self.feature_pipeline_version,
            "feature_dictionary_version": self.feature_dictionary_version,
            "training_observation_ids": list(self.training_observation_ids),
            "partition_observation_ids": {
                name: list(values) for name, values in self.partition_observation_ids
            },
            "numeric_fits": [value.to_dict() for value in self.numeric_fits],
            "categorical_fits": [value.to_dict() for value in self.categorical_fits],
            "output_feature_names": list(self.output_feature_names),
            "unknown_category": UNKNOWN_CATEGORY,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> FittedPreprocessor:
        """Reconstruct explicit fitted state without executable deserialization."""

        if value.get("unknown_category") != UNKNOWN_CATEGORY:
            raise ValueError("unsupported unknown-category marker")
        try:
            fitted = cls(
                feature_pipeline_version=value["feature_pipeline_version"],
                feature_dictionary_version=value["feature_dictionary_version"],
                training_observation_ids=tuple(value["training_observation_ids"]),
                partition_observation_ids=tuple(
                    (name, tuple(value["partition_observation_ids"][name]))
                    for name in SUPPORTED_PARTITIONS
                ),
                numeric_fits=tuple(
                    NumericFit(item["source_name"], item["mean"], item["scale"])
                    for item in value["numeric_fits"]
                ),
                categorical_fits=tuple(
                    CategoricalFit(item["source_name"], tuple(item["categories"]))
                    for item in value["categorical_fits"]
                ),
                output_feature_names=tuple(value["output_feature_names"]),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError("malformed fitted preprocessing state") from exc
        _validate_fitted(fitted)
        return fitted


@dataclass(frozen=True)
class ModelMatrix:
    """Ordered numeric inputs with identity and targets kept as sidecars."""

    partition: str
    observation_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    targets: tuple[int, ...]


@dataclass(frozen=True)
class FeaturePipelineResult:
    preprocessor: FittedPreprocessor
    train: ModelMatrix
    validation: ModelMatrix
    test: ModelMatrix


def fit_preprocessor(result: TemporalSplitResult) -> FittedPreprocessor:
    """Fit categorical vocabularies and numeric statistics from train only."""

    validate_temporal_split(result)
    train_rows = _extract_rows(result.train)
    if not train_rows:
        raise ValueError("training partition must not be empty")

    categorical_fits_list: list[CategoricalFit] = []
    for name in INCLUDED_CATEGORICAL_FEATURES:
        categories = tuple(sorted({str(row.value_map()[name]) for row in train_rows}))
        if UNKNOWN_CATEGORY in categories:
            raise ValueError(f"training category collides with reserved marker: {name}")
        categorical_fits_list.append(
            CategoricalFit(name, categories + (UNKNOWN_CATEGORY,))
        )
    categorical_fits = tuple(categorical_fits_list)
    numeric_fits = tuple(
        _fit_numeric(name, train_rows) for name in INCLUDED_NUMERIC_FEATURES
    )
    output_names = tuple(
        [fit.source_name for fit in numeric_fits]
        + [
            f"{fit.source_name}={category}"
            for fit in categorical_fits
            for category in fit.categories
        ]
    )
    partition_ids = tuple(
        (name, tuple(record.observation_id for record in getattr(result, name)))
        for name in SUPPORTED_PARTITIONS
    )
    return FittedPreprocessor(
        feature_pipeline_version=FEATURE_PIPELINE_VERSION,
        feature_dictionary_version=FEATURE_DICTIONARY_VERSION,
        training_observation_ids=partition_ids[0][1],
        partition_observation_ids=partition_ids,
        numeric_fits=numeric_fits,
        categorical_fits=categorical_fits,
        output_feature_names=output_names,
    )


def transform_partition(
    fitted: FittedPreprocessor,
    records: Iterable[ObservationRecord],
    partition: str,
) -> ModelMatrix:
    """Apply frozen preprocessing without changing fitted state."""

    _validate_fitted(fitted)
    if partition not in SUPPORTED_PARTITIONS:
        raise ValueError(f"unsupported modeling partition: {partition}")
    materialized = tuple(records)
    expected_ids = dict(fitted.partition_observation_ids)[partition]
    actual_ids = tuple(record.observation_id for record in materialized)
    if actual_ids != expected_ids:
        raise ValueError(f"{partition} records do not match frozen partition membership/order")
    rows = _extract_rows(materialized)
    transformed = tuple(_transform_row(fitted, row) for row in rows)
    return ModelMatrix(
        partition=partition,
        observation_ids=actual_ids,
        feature_names=fitted.output_feature_names,
        values=transformed,
        targets=tuple(row.target for row in rows),
    )


def build_feature_pipeline(result: TemporalSplitResult) -> FeaturePipelineResult:
    """Fit on train and apply the same immutable state to all modeling partitions."""

    fitted = fit_preprocessor(result)
    before = fitted_state_bytes(fitted)
    matrices = {
        name: transform_partition(fitted, getattr(result, name), name)
        for name in SUPPORTED_PARTITIONS
    }
    if fitted_state_bytes(fitted) != before:
        raise ValueError("held-out transformation mutated fitted preprocessing state")
    return FeaturePipelineResult(preprocessor=fitted, **matrices)


def fitted_state_bytes(fitted: FittedPreprocessor) -> bytes:
    """Serialize fitted state canonically for drift and mutation checks."""

    return (json.dumps(fitted.to_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def matrix_digest(matrix: ModelMatrix) -> str:
    """Hash ordered model inputs and sidecars without publishing row data."""

    material = {
        "partition": matrix.partition,
        "observation_ids": list(matrix.observation_ids),
        "feature_names": list(matrix.feature_names),
        "values": [list(row) for row in matrix.values],
        "targets": list(matrix.targets),
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _extract_rows(records: Iterable[ObservationRecord]) -> tuple[ExtractedFeatureRow, ...]:
    rows = tuple(extract_feature_row(record) for record in records)
    ids = [row.observation_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("modeling rows contain duplicate observation IDs")
    return rows


def _fit_numeric(name: str, rows: tuple[ExtractedFeatureRow, ...]) -> NumericFit:
    values = [float(row.value_map()[name]) for row in rows]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    scale = sqrt(variance)
    if scale == 0.0:
        scale = 1.0
    return NumericFit(name, mean, scale)


def _transform_row(fitted: FittedPreprocessor, row: ExtractedFeatureRow) -> tuple[float, ...]:
    values = row.value_map()
    output = [
        (float(values[fit.source_name]) - fit.mean) / fit.scale
        for fit in fitted.numeric_fits
    ]
    for fit in fitted.categorical_fits:
        raw = str(values[fit.source_name])
        selected = raw if raw in fit.categories[:-1] else UNKNOWN_CATEGORY
        output.extend(1.0 if category == selected else 0.0 for category in fit.categories)
    result = tuple(output)
    if len(result) != len(fitted.output_feature_names):
        raise ValueError("transformed feature width does not match frozen output names")
    return result


def _validate_fitted(fitted: FittedPreprocessor) -> None:
    if fitted.feature_pipeline_version != FEATURE_PIPELINE_VERSION:
        raise ValueError("unsupported feature pipeline version")
    if fitted.feature_dictionary_version != FEATURE_DICTIONARY_VERSION:
        raise ValueError("unsupported feature dictionary version")
    if dict(fitted.partition_observation_ids).get("train") != fitted.training_observation_ids:
        raise ValueError("fitted training IDs do not match frozen train membership")
    if tuple(name for name, _ in fitted.partition_observation_ids) != SUPPORTED_PARTITIONS:
        raise ValueError("fitted partition membership is incomplete or unordered")
    for fit in fitted.categorical_fits:
        if not fit.categories or fit.categories[-1] != UNKNOWN_CATEGORY:
            raise ValueError("fitted categorical vocabulary lacks the frozen unknown marker")
        if len(fit.categories) != len(set(fit.categories)):
            raise ValueError("fitted categorical vocabulary contains duplicates")
    if any(fit.scale <= 0.0 for fit in fitted.numeric_fits):
        raise ValueError("fitted numeric scale must be positive")
    expected_names = tuple(
        [fit.source_name for fit in fitted.numeric_fits]
        + [
            f"{fit.source_name}={category}"
            for fit in fitted.categorical_fits
            for category in fit.categories
        ]
    )
    if expected_names != fitted.output_feature_names:
        raise ValueError("fitted output feature names are inconsistent")
