"""Inforsight's clean-room fictional policy-event simulator."""

from .config import GeneratorConfig
from .generator import generate_policy_histories, generation_provenance
from .features import (
    FEATURE_DEFINITIONS,
    FEATURE_DICTIONARY_VERSION,
    FEATURE_PIPELINE_VERSION,
    ExtractedFeatureRow,
    FeatureDefinition,
    extract_feature_row,
    feature_dictionary,
    validate_feature_dictionary,
)
from .leakage import (
    FEATURE_GUARD_VERSION,
    find_exact_deterministic_proxies,
    validate_feature_payload,
    validate_observation_records,
)
from .observations import (
    LABEL_HORIZON_DAYS,
    LABEL_POLICY_VERSION,
    OBSERVATION_CONTRACT_VERSION,
    ObservationFeatures,
    ObservationRecord,
    OutcomeLabel,
    build_first_billing_observations,
    build_observation,
    first_billing_observation_time,
    summarize_observations,
)
from .reconstruction import PolicyState, reconstruct_policy_state
from .preprocessing import (
    UNKNOWN_CATEGORY,
    FeaturePipelineResult,
    FittedPreprocessor,
    ModelMatrix,
    build_feature_pipeline,
    fit_preprocessor,
    fitted_state_bytes,
    matrix_digest,
    transform_partition,
)
from .serialization import histories_to_jsonl
from .splitting import (
    CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
    TEMPORAL_SPLIT_CONTRACT_VERSION,
    TemporalSplitResult,
    TemporalSplitSpecification,
    assign_temporal_splits,
    source_observation_digest,
    summarize_temporal_split,
    validate_temporal_split,
)
from .validation import validate_policy_history


__version__ = "0.1.0"

__all__ = [
    "GeneratorConfig",
    "FEATURE_DEFINITIONS",
    "FEATURE_DICTIONARY_VERSION",
    "FEATURE_GUARD_VERSION",
    "FEATURE_PIPELINE_VERSION",
    "LABEL_HORIZON_DAYS",
    "LABEL_POLICY_VERSION",
    "OBSERVATION_CONTRACT_VERSION",
    "CANONICAL_TEMPORAL_SPLIT_SPECIFICATION",
    "TEMPORAL_SPLIT_CONTRACT_VERSION",
    "ObservationFeatures",
    "ObservationRecord",
    "OutcomeLabel",
    "ExtractedFeatureRow",
    "FeatureDefinition",
    "FeaturePipelineResult",
    "FittedPreprocessor",
    "ModelMatrix",
    "TemporalSplitResult",
    "TemporalSplitSpecification",
    "UNKNOWN_CATEGORY",
    "assign_temporal_splits",
    "build_first_billing_observations",
    "build_feature_pipeline",
    "build_observation",
    "first_billing_observation_time",
    "fit_preprocessor",
    "fitted_state_bytes",
    "find_exact_deterministic_proxies",
    "generate_policy_histories",
    "generation_provenance",
    "extract_feature_row",
    "feature_dictionary",
    "histories_to_jsonl",
    "PolicyState",
    "project_identity",
    "reconstruct_policy_state",
    "source_observation_digest",
    "matrix_digest",
    "summarize_observations",
    "summarize_temporal_split",
    "validate_feature_payload",
    "validate_feature_dictionary",
    "validate_observation_records",
    "validate_policy_history",
    "validate_temporal_split",
    "transform_partition",
]


def project_identity() -> dict[str, str]:
    """Return public project metadata used by the scaffold smoke test."""
    return {
        "name": "Inforsight",
        "tagline": "See Risk. Shape Action.",
        "data_policy": "synthetic-only",
    }
