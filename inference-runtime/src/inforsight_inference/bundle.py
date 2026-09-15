"""Immutable bundle types and fail-closed trusted loading."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

from .catalog import (
    CATALOG_FILE_SHA256,
    CATALOG_VERSION,
    PREPROCESSING_PROFILE_ID,
    SemanticCatalog,
    load_semantic_catalog,
)
from .engine import CATEGORICAL_FEATURES, NUMERIC_FEATURES, BundledInferenceEngine
from .errors import BundleLoadError, ErrorCode, InferenceRuntimeError


MODEL_BUNDLE_VERSION = "1.0.0"
MODEL_BUNDLE_CONTRACT_VERSION = "1.0.0"
MODEL_BUNDLE_ARTIFACT_VERSION = "1.0.0"
MODEL_ID = "inforsight-v6-logistic-platt-20260817"
RUNTIME_CONTRACT_ID = "inforsight.inference-runtime"
RUNTIME_CONTRACT_VERSION = "1.0.0"
TRUSTED_BUNDLE_SHA256 = "7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656"
EXPECTED_AUTHORITY_BOUNDARIES = {
    "non_causal_boundary": "Attributions describe statistical correlations (P(y|x)), not causal levers (P(y|do(x))). Altering observed features manually does not guarantee customer risk reduction.",
    "tier_1_perception_role": "Attributions quantify mathematical associations in the perception layer. They possess zero autonomous authority to trigger workflows, alter premiums, or send communications.",
    "tier_2_deterministic_rules_required": "All candidate accounts must pass deterministic eligibility filters (grace period checks, cooling-off periods, communication caps) before any intervention.",
    "tier_4_licensed_human_approval": "Final approval for all customer retention interventions remains with licensed human conservation officers.",
}


@dataclass(frozen=True)
class NumericFeatureSpec:
    name: str
    mean: float
    scale: float


@dataclass(frozen=True)
class CategoricalFeatureSpec:
    name: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class PreprocessorSpec:
    numeric: dict[str, NumericFeatureSpec]
    categorical: dict[str, CategoricalFeatureSpec]
    ordered_columns: tuple[str, ...]
    schema_version: str = "6.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "feature_count": len(self.ordered_columns),
            "numeric": {key: asdict(value) for key, value in self.numeric.items()},
            "categorical": {
                key: {"name": value.name, "categories": list(value.categories)}
                for key, value in self.categorical.items()
            },
            "ordered_columns": list(self.ordered_columns),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> PreprocessorSpec:
        return cls(
            numeric={
                key: NumericFeatureSpec(
                    name=item["name"], mean=float(item["mean"]), scale=float(item["scale"])
                )
                for key, item in value["numeric"].items()
            },
            categorical={
                key: CategoricalFeatureSpec(
                    name=item["name"], categories=tuple(item["categories"])
                )
                for key, item in value["categorical"].items()
            },
            ordered_columns=tuple(value["ordered_columns"]),
            schema_version=value["schema_version"],
        )


@dataclass(frozen=True)
class BaseModelSpec:
    family: str
    penalty: str
    c_param: float
    solver: str
    random_seed: int
    raw_intercept: float
    raw_coefficients: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> BaseModelSpec:
        return cls(
            family=value["family"], penalty=value["penalty"],
            c_param=float(value["c_param"]), solver=value["solver"],
            random_seed=int(value["random_seed"]),
            raw_intercept=float(value["raw_intercept"]),
            raw_coefficients={key: float(item) for key, item in value["raw_coefficients"].items()},
        )


@dataclass(frozen=True)
class CalibratorSpec:
    method: str
    param_a: float
    param_b: float
    calibrated_intercept: float
    calibrated_coefficients: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CalibratorSpec:
        return cls(
            method=value["method"], param_a=float(value["param_a"]),
            param_b=float(value["param_b"]),
            calibrated_intercept=float(value["calibrated_intercept"]),
            calibrated_coefficients={
                key: float(item) for key, item in value["calibrated_coefficients"].items()
            },
        )


@dataclass(frozen=True)
class ExplainerReferenceSpec:
    background_observation_count: int
    base_value_logit: float
    base_value_probability: float
    background_column_means: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ExplainerReferenceSpec:
        return cls(
            background_observation_count=int(value["background_observation_count"]),
            base_value_logit=float(value["base_value_logit"]),
            base_value_probability=float(value["base_value_probability"]),
            background_column_means={
                key: float(item) for key, item in value["background_column_means"].items()
            },
        )


@dataclass(frozen=True)
class RiskTierThreshold:
    name: str
    min_prob: float
    max_prob: float
    action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewQueueCapacity:
    capacity_percentile: float
    cutoff_probability: float
    expected_precision: float
    expected_recall: float
    lift: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OperationalPolicySpec:
    risk_tiers: tuple[RiskTierThreshold, ...]
    review_queues: tuple[ReviewQueueCapacity, ...]
    authority_boundaries: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_tiers": [item.to_dict() for item in self.risk_tiers],
            "review_queues": [item.to_dict() for item in self.review_queues],
            "authority_boundaries": dict(self.authority_boundaries),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> OperationalPolicySpec:
        return cls(
            risk_tiers=tuple(
                RiskTierThreshold(
                    name=item["name"], min_prob=float(item["min_prob"]),
                    max_prob=float(item["max_prob"]), action=item["action"],
                )
                for item in value["risk_tiers"]
            ),
            review_queues=tuple(
                ReviewQueueCapacity(
                    capacity_percentile=float(item["capacity_percentile"]),
                    cutoff_probability=float(item["cutoff_probability"]),
                    expected_precision=float(item["expected_precision"]),
                    expected_recall=float(item["expected_recall"]),
                    lift=float(item["lift"]),
                )
                for item in value["review_queues"]
            ),
            authority_boundaries=dict(value["authority_boundaries"]),
        )


@dataclass(frozen=True)
class RuntimeEnvironment:
    python_version: str
    platform: str
    library_versions: dict[str, str]
    dependency_lock_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RuntimeEnvironment:
        return cls(
            python_version=value["python_version"], platform=value["platform"],
            library_versions=dict(value["library_versions"]),
            dependency_lock_sha256=value["dependency_lock_sha256"],
        )


@dataclass(frozen=True)
class ModelBundle:
    bundle_version: str
    bundle_id: str
    created_at_utc: str
    runtime_environment: RuntimeEnvironment
    preprocessor: PreprocessorSpec
    base_model: BaseModelSpec
    calibrator: CalibratorSpec
    explainer_reference: ExplainerReferenceSpec
    operational_policy: OperationalPolicySpec

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_version": self.bundle_version, "bundle_id": self.bundle_id,
            "created_at_utc": self.created_at_utc,
            "runtime_environment": self.runtime_environment.to_dict(),
            "preprocessor": self.preprocessor.to_dict(),
            "base_model": self.base_model.to_dict(),
            "calibrator": self.calibrator.to_dict(),
            "explainer_reference": self.explainer_reference.to_dict(),
            "operational_policy": self.operational_policy.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ModelBundle:
        _validate_bundle_data(value)
        return cls(
            bundle_version=value["bundle_version"], bundle_id=value["bundle_id"],
            created_at_utc=value["created_at_utc"],
            runtime_environment=RuntimeEnvironment.from_dict(value["runtime_environment"]),
            preprocessor=PreprocessorSpec.from_dict(value["preprocessor"]),
            base_model=BaseModelSpec.from_dict(value["base_model"]),
            calibrator=CalibratorSpec.from_dict(value["calibrator"]),
            explainer_reference=ExplainerReferenceSpec.from_dict(value["explainer_reference"]),
            operational_policy=OperationalPolicySpec.from_dict(value["operational_policy"]),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, allow_nan=False)

    @classmethod
    def from_json(cls, text: str) -> ModelBundle:
        return cls.from_dict(_parse_json_text(text))

    def compute_digest(self) -> str:
        return sha256(self.to_json().encode("utf-8")).hexdigest()

    def save(self, path: Path | str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json() + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> ModelBundle:
        try:
            raw = Path(path).read_bytes()
        except OSError as exc:
            raise BundleLoadError(ErrorCode.BUNDLE_UNREADABLE, "bundle bytes are unreadable") from exc
        return cls.from_dict(_parse_bundle_bytes(raw))


@dataclass(frozen=True)
class VerifiedRuntime:
    bundle: ModelBundle
    engine: BundledInferenceEngine
    catalog: SemanticCatalog
    bundle_sha256: str
    ready: bool = True


def _schema_error(summary: str = "bundle structure or values are invalid") -> BundleLoadError:
    return BundleLoadError(ErrorCode.BUNDLE_SCHEMA_INVALID, summary)


def _finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def _validate_bundle_data(value: Mapping[str, Any]) -> None:
    try:
        if not isinstance(value, dict):
            raise _schema_error()
        required = {
            "bundle_version", "bundle_id", "created_at_utc", "runtime_environment",
            "preprocessor", "base_model", "calibrator", "explainer_reference",
            "operational_policy",
        }
        if set(value) != required:
            raise _schema_error()
        if not all(isinstance(value[key], str) and value[key] for key in ("bundle_version", "bundle_id", "created_at_utc")):
            raise _schema_error()

        preprocessor = value["preprocessor"]
        if not isinstance(preprocessor, dict) or set(preprocessor) != {
            "schema_version", "feature_count", "numeric", "categorical", "ordered_columns"
        }:
            raise _schema_error()
        numeric = preprocessor["numeric"]
        categorical = preprocessor["categorical"]
        columns = preprocessor["ordered_columns"]
        if set(numeric) != set(NUMERIC_FEATURES) or set(categorical) != set(CATEGORICAL_FEATURES):
            raise _schema_error()
        if not isinstance(columns, list) or not columns or len(set(columns)) != len(columns):
            raise _schema_error()
        if isinstance(preprocessor["feature_count"], bool) or preprocessor["feature_count"] != len(columns):
            raise _schema_error()
        expected_columns = list(NUMERIC_FEATURES)
        for name in CATEGORICAL_FEATURES:
            item = categorical[name]
            if not isinstance(item, dict) or item.get("name") != name:
                raise _schema_error()
            categories = item.get("categories")
            if not isinstance(categories, list) or not categories or categories[-1] != "__unknown__" or len(set(categories)) != len(categories):
                raise _schema_error()
            if not all(isinstance(category, str) and category for category in categories):
                raise _schema_error()
            expected_columns.extend(f"{name}={category}" for category in categories)
        if columns != expected_columns:
            raise _schema_error()
        for name in NUMERIC_FEATURES:
            item = numeric[name]
            if not isinstance(item, dict) or item.get("name") != name:
                raise _schema_error()
            if not _finite_number(item.get("mean")) or not _finite_number(item.get("scale")) or float(item["scale"]) <= 0.0:
                raise _schema_error()

        model = value["base_model"]
        calibrator = value["calibrator"]
        reference = value["explainer_reference"]
        if not isinstance(model, dict) or set(model) != {
            "family", "penalty", "c_param", "solver", "random_seed",
            "raw_intercept", "raw_coefficients",
        }:
            raise _schema_error()
        if not isinstance(calibrator, dict) or set(calibrator) != {
            "method", "param_a", "param_b", "calibrated_intercept",
            "calibrated_coefficients",
        }:
            raise _schema_error()
        if not isinstance(reference, dict) or set(reference) != {
            "background_observation_count", "base_value_logit",
            "base_value_probability", "background_column_means",
        }:
            raise _schema_error()
        if not all(
            isinstance(model[field], str) and model[field]
            for field in ("family", "penalty", "solver")
        ):
            raise _schema_error()
        if isinstance(model["random_seed"], bool) or not isinstance(model["random_seed"], int):
            raise _schema_error()
        if not isinstance(calibrator["method"], str) or not calibrator["method"]:
            raise _schema_error()
        for mapping, field in (
            (model, "raw_coefficients"),
            (calibrator, "calibrated_coefficients"),
            (reference, "background_column_means"),
        ):
            if not isinstance(mapping, dict) or not isinstance(mapping.get(field), dict):
                raise _schema_error()
            if set(mapping[field]) != set(columns) or not all(_finite_number(item) for item in mapping[field].values()):
                raise _schema_error()
        scalar_fields = (
            (model, ("c_param", "raw_intercept")),
            (calibrator, ("param_a", "param_b", "calibrated_intercept")),
            (reference, ("base_value_logit", "base_value_probability")),
        )
        if any(not _finite_number(mapping.get(field)) for mapping, fields in scalar_fields for field in fields):
            raise _schema_error()
        if not 0.0 <= float(reference["base_value_probability"]) <= 1.0:
            raise _schema_error()
        if isinstance(reference.get("background_observation_count"), bool) or not isinstance(reference.get("background_observation_count"), int) or reference["background_observation_count"] <= 0:
            raise _schema_error()

        policy = value["operational_policy"]
        tiers = policy.get("risk_tiers") if isinstance(policy, dict) else None
        queues = policy.get("review_queues") if isinstance(policy, dict) else None
        boundaries = policy.get("authority_boundaries") if isinstance(policy, dict) else None
        if not isinstance(tiers, list) or not tiers or not isinstance(queues, list) or not queues:
            raise _schema_error()
        previous_max = 0.0
        tier_names: set[str] = set()
        for tier in tiers:
            if not isinstance(tier, dict) or set(tier) != {"name", "min_prob", "max_prob", "action"}:
                raise _schema_error()
            if not isinstance(tier["name"], str) or not tier["name"] or tier["name"] in tier_names or not isinstance(tier["action"], str) or not tier["action"]:
                raise _schema_error()
            if not _finite_number(tier["min_prob"]) or not _finite_number(tier["max_prob"]):
                raise _schema_error()
            minimum, maximum = float(tier["min_prob"]), float(tier["max_prob"])
            if minimum != previous_max or not 0.0 <= minimum < maximum <= 1.0:
                raise _schema_error()
            tier_names.add(tier["name"])
            previous_max = maximum
        if previous_max != 1.0:
            raise _schema_error()
        capacities: set[float] = set()
        for queue in queues:
            if not isinstance(queue, dict) or set(queue) != {"capacity_percentile", "cutoff_probability", "expected_precision", "expected_recall", "lift"}:
                raise _schema_error()
            if not all(_finite_number(queue[field]) for field in queue):
                raise _schema_error()
            capacity = float(queue["capacity_percentile"])
            if capacity in capacities or not 0.0 < capacity <= 100.0:
                raise _schema_error()
            if not all(0.0 <= float(queue[field]) <= 1.0 for field in ("cutoff_probability", "expected_precision", "expected_recall")) or float(queue["lift"]) < 0.0:
                raise _schema_error()
            capacities.add(capacity)
        if boundaries != EXPECTED_AUTHORITY_BOUNDARIES:
            raise _schema_error()
        runtime = value["runtime_environment"]
        if not isinstance(runtime, dict) or set(runtime) != {"python_version", "platform", "library_versions", "dependency_lock_sha256"}:
            raise _schema_error()
        if not all(
            isinstance(runtime[field], str) and runtime[field]
            for field in ("python_version", "platform", "dependency_lock_sha256")
        ):
            raise _schema_error()
        if not isinstance(runtime["library_versions"], dict) or not runtime["library_versions"] or not all(isinstance(key, str) and key and isinstance(item, str) and item for key, item in runtime["library_versions"].items()):
            raise _schema_error()
    except BundleLoadError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise _schema_error() from exc


def _reject_constant(_: str) -> None:
    raise ValueError("non-finite JSON number")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = item
    return result


def _parse_json_text(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise BundleLoadError(ErrorCode.BUNDLE_JSON_INVALID, "bundle is not valid strict JSON") from exc
    if not isinstance(value, dict):
        raise _schema_error()
    return value


def _parse_bundle_bytes(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BundleLoadError(ErrorCode.BUNDLE_ENCODING_INVALID, "bundle is not valid UTF-8") from exc
    return _parse_json_text(text)


def _validate_trust(digest: str | None, bundle_id: str | None, bundle_version: str | None) -> tuple[str, str, str]:
    valid_digest = isinstance(digest, str) and len(digest) == 64 and digest == digest.lower()
    if valid_digest:
        try:
            int(digest, 16)
        except ValueError:
            valid_digest = False
    if not valid_digest or not bundle_id or not bundle_version:
        raise BundleLoadError(
            ErrorCode.TRUST_CONFIGURATION_MISSING,
            "trusted bundle digest, ID, and version are required",
        )
    return digest, bundle_id, bundle_version


def _verify_catalog_identity(bundle: ModelBundle, catalog: SemanticCatalog) -> None:
    preprocessing = catalog.data["preprocessing"]
    if preprocessing["profile_id"] != PREPROCESSING_PROFILE_ID:
        raise BundleLoadError(ErrorCode.PREPROCESSING_IDENTITY_MISMATCH, "preprocessing profile is incompatible")
    if bundle.preprocessor.to_dict() != _thaw(preprocessing["bundle_preprocessor"]):
        raise BundleLoadError(ErrorCode.PREPROCESSING_IDENTITY_MISMATCH, "bundle preprocessing identity is incompatible")
    if preprocessing["bundle_id"] != bundle.bundle_id or preprocessing["bundle_version"] != bundle.bundle_version:
        raise BundleLoadError(ErrorCode.CATALOG_IDENTITY_MISMATCH, "catalog bundle identity is incompatible")
    catalog_tiers = tuple(
        (item["display_name"], float(item["min_inclusive"]), float(item["max"]))
        for item in catalog.data["risk_tiers"]
    )
    bundle_tiers = tuple((item.name, item.min_prob, item.max_prob) for item in bundle.operational_policy.risk_tiers)
    if bundle_tiers != catalog_tiers:
        raise BundleLoadError(ErrorCode.CATALOG_IDENTITY_MISMATCH, "catalog tier identity is incompatible")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def load_verified_runtime(
    path: Path | str,
    *,
    expected_sha256: str | None,
    expected_bundle_id: str | None,
    expected_bundle_version: str | None,
) -> VerifiedRuntime:
    """Read once, verify byte identity, validate, and construct a ready engine."""

    digest_expected, id_expected, version_expected = _validate_trust(
        expected_sha256, expected_bundle_id, expected_bundle_version
    )
    target = Path(path)
    if not target.exists():
        raise BundleLoadError(ErrorCode.BUNDLE_PATH_MISSING, "selected bundle path does not exist")
    if not target.is_file():
        raise BundleLoadError(ErrorCode.BUNDLE_NOT_REGULAR_FILE, "selected bundle path is not a regular file")
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise BundleLoadError(ErrorCode.BUNDLE_UNREADABLE, "bundle bytes are unreadable") from exc
    digest = sha256(raw).hexdigest()
    if digest != digest_expected:
        raise BundleLoadError(ErrorCode.BUNDLE_DIGEST_MISMATCH, "bundle digest does not match trusted identity")
    bundle = ModelBundle.from_dict(_parse_bundle_bytes(raw))
    if bundle.bundle_id != id_expected:
        raise BundleLoadError(ErrorCode.BUNDLE_ID_MISMATCH, "bundle ID does not match trusted identity")
    if bundle.bundle_version != version_expected or bundle.bundle_version != MODEL_BUNDLE_VERSION:
        raise BundleLoadError(ErrorCode.BUNDLE_VERSION_UNSUPPORTED, "bundle version is unsupported")
    try:
        catalog = load_semantic_catalog()
    except InferenceRuntimeError as exc:
        raise BundleLoadError(ErrorCode.CATALOG_IDENTITY_MISMATCH, exc.summary) from exc
    _verify_catalog_identity(bundle, catalog)
    try:
        engine = BundledInferenceEngine(bundle)
    except Exception as exc:
        raise BundleLoadError(ErrorCode.ENGINE_INITIALIZATION_FAILED, "engine initialization failed") from exc
    return VerifiedRuntime(bundle=bundle, engine=engine, catalog=catalog, bundle_sha256=digest)


def load_configured_runtime(
    default_path: Path | str,
    *,
    bundle_path: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> VerifiedRuntime:
    """Resolve local/deployment configuration without explicit-path fallback."""

    env = os.environ if environ is None else environ
    if bundle_path is not None:
        selected = Path(bundle_path)
    elif "INFORSIGHT_MODEL_BUNDLE_PATH" in env:
        configured = env.get("INFORSIGHT_MODEL_BUNDLE_PATH", "")
        if not configured.strip():
            raise BundleLoadError(ErrorCode.BUNDLE_PATH_MISSING, "configured bundle path is empty")
        selected = Path(configured)
    else:
        selected = Path(default_path)

    require_value = env.get("INFORSIGHT_REQUIRE_TRUSTED_BUNDLE", "false").strip().lower()
    if require_value not in {"true", "false"}:
        raise BundleLoadError(ErrorCode.TRUST_CONFIGURATION_MISSING, "trusted bundle mode is invalid")
    require_configured = require_value == "true"
    expected_digest = env.get("INFORSIGHT_EXPECTED_BUNDLE_SHA256")
    expected_id = env.get("INFORSIGHT_EXPECTED_BUNDLE_ID")
    expected_version = env.get("INFORSIGHT_EXPECTED_BUNDLE_VERSION")
    if not require_configured:
        expected_digest = expected_digest or TRUSTED_BUNDLE_SHA256
        expected_id = expected_id or MODEL_ID
        expected_version = expected_version or MODEL_BUNDLE_VERSION
    return load_verified_runtime(
        selected,
        expected_sha256=expected_digest,
        expected_bundle_id=expected_id,
        expected_bundle_version=expected_version,
    )
