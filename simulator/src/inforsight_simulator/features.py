"""Versioned stateless feature extraction for modeling inputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from math import isfinite
from typing import Any, Mapping

from .leakage import ALLOWED_FEATURE_KEYS, validate_feature_payload
from .observations import ObservationRecord


FEATURE_DICTIONARY_VERSION = "1.0.0"
FEATURE_PIPELINE_VERSION = "1.0.0"


@dataclass(frozen=True)
class FeatureDefinition:
    """One reviewed source-feature decision in the Phase 2.04 dictionary."""

    source_name: str
    description: str
    raw_type: str
    semantic_type: str
    nullable: bool
    provenance: str
    temporal_rule: str
    stateless_transformation: str
    learned_preprocessing: str
    unknown_or_missing_behavior: str
    included: bool
    decision_rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_OBSERVATION_PROVENANCE = (
    "ObservationFeatures built from events effective and ingested on or before as_of"
)
_TEMPORAL_RULE = "effective_at <= as_of and ingested_at <= as_of"


FEATURE_DEFINITIONS = (
    FeatureDefinition(
        "current_status", "Point-in-time policy status", "string", "categorical",
        False, _OBSERVATION_PROVENANCE, _TEMPORAL_RULE, "identity",
        "none", "missing values are rejected", False,
        "Eligibility requires active status, so the canonical modeling rows are constant.",
    ),
    FeatureDefinition(
        "product_variant", "Fictional issued product variant", "string", "categorical",
        False, _OBSERVATION_PROVENANCE, _TEMPORAL_RULE, "identity",
        "training-fitted one-hot vocabulary in sorted order",
        "missing values are rejected; unseen values use product_variant=__unknown__",
        True, "Retain as an approved observable baseline categorical feature.",
    ),
    FeatureDefinition(
        "billing_frequency", "Issued premium billing frequency", "string", "categorical",
        False, _OBSERVATION_PROVENANCE, _TEMPORAL_RULE, "identity",
        "training-fitted one-hot vocabulary in sorted order",
        "missing values are rejected; unseen values use billing_frequency=__unknown__",
        True, "Retain with explicit held-out unknown handling required by LIM-002-001.",
    ),
    FeatureDefinition(
        "premium_amount_cents", "Issued fictional premium in integer cents", "integer", "numeric",
        False, _OBSERVATION_PROVENANCE, _TEMPORAL_RULE, "validate nonnegative integer cents",
        "training-fitted z-score using population mean and standard deviation",
        "missing values are rejected", True,
        "Preserve exact cents before training-only scaling; avoid lossy unit conversion.",
    ),
    FeatureDefinition(
        "currency", "Issued premium ISO-style fictional currency", "string", "categorical",
        False, _OBSERVATION_PROVENANCE, _TEMPORAL_RULE, "identity",
        "none", "missing values are rejected", False,
        "The current contract supports only USD, so the field is constant.",
    ),
    FeatureDefinition(
        "policy_age_days", "Elapsed whole days from issue to observation cutoff", "integer", "numeric",
        False, _OBSERVATION_PROVENANCE, _TEMPORAL_RULE, "validate nonnegative integer",
        "training-fitted z-score using population mean and standard deviation",
        "missing values are rejected", True,
        "Retain as an approved point-in-time duration feature.",
    ),
    *tuple(
        FeatureDefinition(
            name, description, "integer", "numeric", False,
            _OBSERVATION_PROVENANCE, _TEMPORAL_RULE, "validate nonnegative integer",
            "training-fitted z-score using population mean and standard deviation",
            "missing values are rejected", True,
            "Retain as an approved point-in-time event-count feature.",
        )
        for name, description in (
            ("visible_event_count", "Count of all events visible at the cutoff"),
            ("visible_billing_count", "Count of visible premium-due events"),
            ("visible_failed_payment_count", "Count of visible failed payments"),
            ("visible_received_payment_count", "Count of visible received payments"),
            ("visible_notice_count", "Count of visible notices"),
            ("visible_service_contact_count", "Count of visible service contacts"),
        )
    ),
)

FEATURE_DEFINITION_BY_NAME = {
    definition.source_name: definition for definition in FEATURE_DEFINITIONS
}
INCLUDED_CATEGORICAL_FEATURES = tuple(
    definition.source_name
    for definition in FEATURE_DEFINITIONS
    if definition.included and definition.semantic_type == "categorical"
)
INCLUDED_NUMERIC_FEATURES = tuple(
    definition.source_name
    for definition in FEATURE_DEFINITIONS
    if definition.included and definition.semantic_type == "numeric"
)


@dataclass(frozen=True)
class ExtractedFeatureRow:
    """One guarded row with identity retained outside its model-visible values."""

    observation_id: str
    values: tuple[tuple[str, str | int], ...]
    target: int

    def value_map(self) -> dict[str, str | int]:
        return dict(self.values)


def feature_dictionary() -> dict[str, Any]:
    """Return the canonical machine-readable feature dictionary."""

    return {
        "feature_dictionary_id": "inforsight-phase-02-04-feature-dictionary",
        "feature_dictionary_version": FEATURE_DICTIONARY_VERSION,
        "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
        "missingness_policy": "reject_missing_required_values",
        "unknown_category_policy": "map_to_predeclared_unknown_output_column",
        "features": [definition.to_dict() for definition in FEATURE_DEFINITIONS],
    }


def validate_feature_dictionary() -> None:
    """Fail if code decisions drift from the guarded observation surface."""

    names = [definition.source_name for definition in FEATURE_DEFINITIONS]
    if len(names) != len(set(names)):
        raise ValueError("feature dictionary contains duplicate source names")
    if set(names) != set(ALLOWED_FEATURE_KEYS):
        raise ValueError("feature dictionary does not match the approved feature allowlist")
    if not INCLUDED_CATEGORICAL_FEATURES or not INCLUDED_NUMERIC_FEATURES:
        raise ValueError("feature dictionary must include categorical and numeric features")


def extract_feature_row(record: ObservationRecord) -> ExtractedFeatureRow:
    """Validate and extract one eligible, observed binary modeling row."""

    validate_feature_dictionary()
    if not record.eligible or record.features is None:
        raise ValueError(f"observation is not modeling eligible: {record.observation_id}")
    if record.label.status not in {"observed_negative", "observed_positive"}:
        raise ValueError(f"observation label is not observed: {record.observation_id}")
    if record.label.value not in (0, 1):
        raise ValueError(f"observation target is not binary: {record.observation_id}")

    payload = _as_mapping(record.features)
    validate_feature_payload(payload)
    expected = set(FEATURE_DEFINITION_BY_NAME)
    if set(payload) != expected:
        missing = sorted(expected - set(payload))
        extra = sorted(set(payload) - expected)
        raise ValueError(f"feature payload shape mismatch; missing={missing}, extra={extra}")

    values: list[tuple[str, str | int]] = []
    for definition in FEATURE_DEFINITIONS:
        raw = payload[definition.source_name]
        _validate_value(definition, raw)
        if definition.included:
            values.append((definition.source_name, raw))
    return ExtractedFeatureRow(record.observation_id, tuple(values), record.label.value)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Mapping):
        return value
    raise ValueError("observation features must be a dataclass or mapping")


def _validate_value(definition: FeatureDefinition, value: Any) -> None:
    if value is None:
        raise ValueError(f"feature {definition.source_name} does not allow missing values")
    if definition.raw_type == "string":
        if not isinstance(value, str) or not value:
            raise ValueError(f"feature {definition.source_name} must be a non-empty string")
        return
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"feature {definition.source_name} must be an integer")
    if not isfinite(value) or value < 0:
        raise ValueError(f"feature {definition.source_name} must be nonnegative and finite")
