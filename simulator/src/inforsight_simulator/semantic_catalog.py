"""Versioned semantic catalog access for RH-01 operational consumers."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


CATALOG_VERSION = "1.0.0"
SNAPSHOT_VERSION = "1.0.0"
PREPROCESSING_PROFILE_ID = "v6-coefficient-transform-then-bundle-zscore/1.0.0"
SUPPORTED_SOURCE_PROFILES = frozenset(
    {"legacy-policy-events/1.0.0", "v6-policy-events/6.0.0"}
)


class CatalogContractError(ValueError):
    """Raised when a catalog or semantic adapter is incompatible."""

    code = "INCOMPATIBLE_CONTRACT"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a contract value using the RH-01 canonical JSON rules."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CatalogContractError("value is not canonical JSON") from exc


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class SemanticCatalog:
    """Validated immutable semantic catalog and its canonical digest."""

    version: str
    snapshot_version: str
    sha256: str
    data: Mapping[str, Any]
    repository_root: Path

    def require_source_profile(self, source_profile: str) -> None:
        if source_profile not in SUPPORTED_SOURCE_PROFILES:
            raise CatalogContractError(f"unsupported source profile {source_profile!r}")
        if source_profile not in self.data["source_profiles"]:
            raise CatalogContractError(f"catalog does not declare {source_profile!r}")

    def require_preprocessing_profile(self, profile_id: str) -> None:
        if profile_id != self.data["preprocessing"]["profile_id"]:
            raise CatalogContractError(f"unsupported preprocessing profile {profile_id!r}")

    def risk_tier(self, probability: float) -> str:
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise CatalogContractError("probability must be numeric")
        value = float(probability)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise CatalogContractError("probability must be finite and in [0, 1]")
        for tier in self.data["risk_tiers"]:
            lower = float(tier["min_inclusive"])
            upper = float(tier["max"])
            if value >= lower and (value < upper or tier["max_inclusive"] and value == upper):
                return str(tier["id"])
        raise CatalogContractError("probability is outside catalog tier intervals")

    def map_risk_tier(self, value: str, *, adapter_profile: str | None = None) -> str:
        canonical = {str(item["id"]): str(item["display_name"]) for item in self.data["risk_tiers"]}
        if value in canonical:
            return value
        display_to_id = {display: tier_id for tier_id, display in canonical.items()}
        if adapter_profile == "historical-bundle-display/1.0.0" and value in display_to_id:
            return display_to_id[value]
        if adapter_profile == "provisional-proto-risk-tier/1.0.0":
            mapped = self.data["provisional_proto_aliases"].get(value)
            if mapped is not None:
                return str(mapped)
        raise CatalogContractError(f"unsupported risk tier {value!r}")

    def risk_tier_display(self, tier_id: str) -> str:
        canonical = {str(item["id"]): str(item["display_name"]) for item in self.data["risk_tiers"]}
        try:
            return canonical[tier_id]
        except KeyError as exc:
            raise CatalogContractError(f"unsupported risk tier {tier_id!r}") from exc

    def risk_tier_rank(self, tier_id: str) -> int:
        for item in self.data["risk_tiers"]:
            if item["id"] == tier_id:
                return int(item["severity_rank"])
        raise CatalogContractError(f"unsupported risk tier {tier_id!r}")

    def action_id(self, value: str, *, adapter_profile: str | None = None) -> str:
        canonical = {str(item["action_id"]) for item in self.data["actions"]}
        if value in canonical:
            return value
        if adapter_profile == "legacy-action-id/1.0.0":
            mapped = self.data["action_aliases"].get(value)
            if mapped is not None:
                return str(mapped)
        raise CatalogContractError(f"unsupported action id {value!r}")


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_semantic_catalog(
    version: str = CATALOG_VERSION,
    *,
    repository_root: Path | None = None,
    verify_dependencies: bool = True,
) -> SemanticCatalog:
    """Load and validate one exact catalog version and its pinned dependencies."""

    if version != CATALOG_VERSION:
        raise CatalogContractError(f"unsupported catalog version {version!r}")
    root = (repository_root or _repository_root()).resolve()
    contract_dir = root / "data-contracts" / "rh" / "v1"
    catalog_path = contract_dir / "semantic-catalog.json"
    schema_path = contract_dir / "semantic-catalog.schema.json"
    try:
        raw = catalog_path.read_bytes()
        data = json.loads(raw)
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogContractError("semantic catalog resources are unavailable or invalid") from exc
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        path = ".".join(str(part) for part in errors[0].absolute_path)
        raise CatalogContractError(f"semantic catalog fails schema at {path or '<root>'}")
    if data["catalog_version"] != version or data["snapshot_version"] != SNAPSHOT_VERSION:
        raise CatalogContractError("catalog and snapshot versions are incompatible")
    digest = sha256(canonical_json_bytes(data)).hexdigest()
    if verify_dependencies:
        preprocessing = data["preprocessing"]
        for path_key, digest_key in (
            ("dictionary_path", "dictionary_sha256"),
            ("bundle_path", "bundle_file_sha256"),
        ):
            path = (root / preprocessing[path_key]).resolve()
            if root not in path.parents or not path.is_file():
                raise CatalogContractError(f"pinned dependency {preprocessing[path_key]!r} is unavailable")
            if sha256(path.read_bytes()).hexdigest() != preprocessing[digest_key]:
                raise CatalogContractError(f"pinned dependency {preprocessing[path_key]!r} changed")
    return SemanticCatalog(
        version=version,
        snapshot_version=str(data["snapshot_version"]),
        sha256=digest,
        data=_freeze(data),
        repository_root=root,
    )
