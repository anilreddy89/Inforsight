"""Packaged, byte-verified RH-01 semantic catalog access."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib import resources
import json
import math
from types import MappingProxyType
from typing import Any, Mapping

from .errors import CatalogContractError, ErrorCode


CATALOG_VERSION = "1.0.0"
SNAPSHOT_VERSION = "1.0.0"
PREPROCESSING_PROFILE_ID = "v6-coefficient-transform-then-bundle-zscore/1.0.0"
CATALOG_FILE_SHA256 = "d360ed670337912f6b0094d587b5a979c5b8de2ed0a528a184eac36b393f4005"
SUPPORTED_SOURCE_PROFILES = frozenset(
    {"legacy-policy-events/1.0.0", "v6-policy-events/6.0.0"}
)


def _reject_constant(_: str) -> None:
    raise ValueError("non-finite JSON number")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _strict_json(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CatalogContractError(
            ErrorCode.CATALOG_IDENTITY_MISMATCH,
            "packaged semantic catalog is not valid strict JSON",
        ) from exc
    if not isinstance(value, dict):
        raise CatalogContractError(
            ErrorCode.CATALOG_IDENTITY_MISMATCH,
            "packaged semantic catalog root must be an object",
        )
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class SemanticCatalog:
    version: str
    snapshot_version: str
    sha256: str
    data: Mapping[str, Any]

    def require_source_profile(self, source_profile: str) -> None:
        if source_profile not in SUPPORTED_SOURCE_PROFILES or source_profile not in self.data["source_profiles"]:
            raise CatalogContractError(
                ErrorCode.CATALOG_IDENTITY_MISMATCH, "unsupported source profile"
            )

    def require_preprocessing_profile(self, profile_id: str) -> None:
        if profile_id != self.data["preprocessing"]["profile_id"]:
            raise CatalogContractError(
                ErrorCode.PREPROCESSING_IDENTITY_MISMATCH,
                "unsupported preprocessing profile",
            )

    def risk_tier(self, probability: float) -> str:
        if isinstance(probability, bool) or not isinstance(probability, (int, float)):
            raise CatalogContractError(
                ErrorCode.CATALOG_IDENTITY_MISMATCH, "probability must be numeric"
            )
        value = float(probability)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise CatalogContractError(
                ErrorCode.CATALOG_IDENTITY_MISMATCH,
                "probability must be finite and in range",
            )
        for tier in self.data["risk_tiers"]:
            lower = float(tier["min_inclusive"])
            upper = float(tier["max"])
            if value >= lower and (value < upper or tier["max_inclusive"] and value == upper):
                return str(tier["id"])
        raise CatalogContractError(
            ErrorCode.CATALOG_IDENTITY_MISMATCH, "probability is outside tier intervals"
        )

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
        raise CatalogContractError(
            ErrorCode.CATALOG_IDENTITY_MISMATCH, "unsupported risk tier"
        )

    def risk_tier_display(self, tier_id: str) -> str:
        for item in self.data["risk_tiers"]:
            if item["id"] == tier_id:
                return str(item["display_name"])
        raise CatalogContractError(ErrorCode.CATALOG_IDENTITY_MISMATCH, "unsupported risk tier")

    def risk_tier_rank(self, tier_id: str) -> int:
        for item in self.data["risk_tiers"]:
            if item["id"] == tier_id:
                return int(item["severity_rank"])
        raise CatalogContractError(ErrorCode.CATALOG_IDENTITY_MISMATCH, "unsupported risk tier")

    def action_id(self, value: str, *, adapter_profile: str | None = None) -> str:
        canonical = {str(item["action_id"]) for item in self.data["actions"]}
        if value in canonical:
            return value
        if adapter_profile == "legacy-action-id/1.0.0":
            mapped = self.data["action_aliases"].get(value)
            if mapped is not None:
                return str(mapped)
        raise CatalogContractError(ErrorCode.CATALOG_IDENTITY_MISMATCH, "unsupported action id")


def load_semantic_catalog(version: str = CATALOG_VERSION) -> SemanticCatalog:
    """Load the package asset and verify its exact accepted byte identity."""

    if version != CATALOG_VERSION:
        raise CatalogContractError(
            ErrorCode.CATALOG_IDENTITY_MISMATCH, "unsupported catalog version"
        )
    try:
        raw = resources.files("inforsight_inference").joinpath(
            "assets/semantic-catalog.json"
        ).read_bytes()
    except OSError as exc:
        raise CatalogContractError(
            ErrorCode.CATALOG_IDENTITY_MISMATCH,
            "packaged semantic catalog is unavailable",
        ) from exc
    digest = sha256(raw).hexdigest()
    if digest != CATALOG_FILE_SHA256:
        raise CatalogContractError(
            ErrorCode.CATALOG_IDENTITY_MISMATCH,
            "packaged semantic catalog digest is incompatible",
        )
    data = _strict_json(raw)
    try:
        compatible = (
            data["catalog_version"] == CATALOG_VERSION
            and data["snapshot_version"] == SNAPSHOT_VERSION
            and data["preprocessing"]["profile_id"] == PREPROCESSING_PROFILE_ID
        )
    except (KeyError, TypeError) as exc:
        raise CatalogContractError(
            ErrorCode.CATALOG_IDENTITY_MISMATCH,
            "packaged semantic catalog structure is incompatible",
        ) from exc
    if not compatible:
        raise CatalogContractError(
            ErrorCode.CATALOG_IDENTITY_MISMATCH,
            "packaged semantic catalog version is incompatible",
        )
    return SemanticCatalog(
        version=CATALOG_VERSION,
        snapshot_version=SNAPSHOT_VERSION,
        sha256=digest,
        data=_freeze(data),
    )
