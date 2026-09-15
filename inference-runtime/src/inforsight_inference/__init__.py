"""Public API for the bounded Inforsight inference-only runtime."""

from .bundle import (
    BaseModelSpec,
    CalibratorSpec,
    CategoricalFeatureSpec,
    ExplainerReferenceSpec,
    MODEL_BUNDLE_ARTIFACT_VERSION,
    MODEL_BUNDLE_CONTRACT_VERSION,
    MODEL_BUNDLE_VERSION,
    MODEL_ID,
    ModelBundle,
    NumericFeatureSpec,
    OperationalPolicySpec,
    PreprocessorSpec,
    ReviewQueueCapacity,
    RiskTierThreshold,
    RUNTIME_CONTRACT_ID,
    RUNTIME_CONTRACT_VERSION,
    RuntimeEnvironment,
    TRUSTED_BUNDLE_SHA256,
    VerifiedRuntime,
    load_configured_runtime,
    load_verified_runtime,
)
from .catalog import (
    CATALOG_FILE_SHA256,
    CATALOG_VERSION,
    PREPROCESSING_PROFILE_ID,
    SemanticCatalog,
    load_semantic_catalog,
)
from .engine import BundledInferenceEngine, ScoringResult
from .errors import BundleLoadError, CatalogContractError, ErrorCode, InferenceRuntimeError

__version__ = "1.0.0"

__all__ = [
    "BaseModelSpec", "BundleLoadError", "BundledInferenceEngine",
    "CATALOG_FILE_SHA256", "CATALOG_VERSION", "CalibratorSpec",
    "CatalogContractError", "CategoricalFeatureSpec", "ErrorCode",
    "ExplainerReferenceSpec", "InferenceRuntimeError",
    "MODEL_BUNDLE_ARTIFACT_VERSION", "MODEL_BUNDLE_CONTRACT_VERSION",
    "MODEL_BUNDLE_VERSION", "MODEL_ID", "ModelBundle", "NumericFeatureSpec",
    "OperationalPolicySpec", "PREPROCESSING_PROFILE_ID", "PreprocessorSpec",
    "RUNTIME_CONTRACT_ID", "RUNTIME_CONTRACT_VERSION", "ReviewQueueCapacity",
    "RiskTierThreshold", "RuntimeEnvironment", "ScoringResult", "SemanticCatalog",
    "TRUSTED_BUNDLE_SHA256", "VerifiedRuntime", "load_configured_runtime",
    "load_semantic_catalog", "load_verified_runtime",
]
