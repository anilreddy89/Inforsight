"""RH-04 runtime contract for signed effects, economics, and resources."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .semantic_catalog import SemanticCatalog, canonical_json_bytes, load_semantic_catalog


ECONOMICS_CONTRACT_ID = "inforsight.synthetic-economics-resource"
ECONOMICS_CONTRACT_VERSION = "1.0.0"
EFFECT_ID = "absolute_combined_termination_risk_reduction_90d"
VALUE_METRIC_ID = "modeled_expected_annual_premium_preserved_usd_micros"
USD_MICROS_PER_CENT = 10_000
USD_MICROS_PER_USD = 1_000_000
SECONDS_PER_HOUR = 3_600


class EconomicsContractError(ValueError):
    """A stable, non-sensitive economics contract failure."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


class ValuationStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


def _decimal_probability(value: Decimal | str | int | float) -> Decimal:
    if isinstance(value, bool):
        raise EconomicsContractError("INVALID_TREATMENT_EFFECT", "effect must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise EconomicsContractError("INVALID_TREATMENT_EFFECT", "effect must be numeric") from exc
    if not result.is_finite() or result < Decimal("-1") or result > Decimal("1"):
        raise EconomicsContractError(
            "INVALID_TREATMENT_EFFECT", "effect must be finite and in [-1, 1]"
        )
    return result.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class SignedTreatmentEffect:
    """A signed absolute combined-termination risk reduction."""

    value: Decimal
    effect_id: str = EFFECT_ID

    def __post_init__(self) -> None:
        if self.effect_id != EFFECT_ID:
            raise EconomicsContractError(
                "INCOMPATIBLE_EFFECT", "unsupported treatment-effect identity"
            )
        object.__setattr__(self, "value", _decimal_probability(self.value))

    @property
    def classification(self) -> str:
        if self.value < 0:
            return "harmful"
        if self.value > 0:
            return "beneficial"
        return "neutral"

    def canonical_value(self) -> str:
        return f"{self.value:.6f}"


@dataclass(frozen=True)
class ActionEconomics:
    action_id: str
    action_type: str
    direct_cost_usd_micros: int
    personnel_seconds: int

    @property
    def direct_cost_usd(self) -> float:
        """Legacy display bridge; never use as authoritative storage."""

        return self.direct_cost_usd_micros / USD_MICROS_PER_USD

    @property
    def personnel_hours(self) -> float:
        """Legacy display bridge; never truncate this value."""

        return self.personnel_seconds / SECONDS_PER_HOUR


@dataclass(frozen=True)
class EconomicValuation:
    policy_id: str
    snapshot_id: str
    snapshot_version: str
    catalog_sha256: str
    contract_id: str
    contract_version: str
    contract_sha256: str
    action_id: str
    action_type: str
    effect_id: str
    effect: str
    classification: str
    annual_premium_cents: int | None
    direct_cost_usd_micros: int | None
    personnel_seconds: int | None
    status: ValuationStatus
    gross_expected_value_usd_micros: int | None = None
    net_expected_value_usd_micros: int | None = None
    metric_id: str = VALUE_METRIC_ID
    error_code: str | None = None

    def __post_init__(self) -> None:
        numeric = (
            self.gross_expected_value_usd_micros,
            self.direct_cost_usd_micros,
            self.net_expected_value_usd_micros,
        )
        if self.status is ValuationStatus.AVAILABLE:
            if any(value is None for value in numeric) or self.error_code is not None:
                raise ValueError("available valuation requires numeric amounts and no error")
        elif any(value is not None for value in numeric) or self.error_code is None:
            raise ValueError("unavailable valuation requires an error and no numeric amounts")

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "snapshot_id": self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "catalog_sha256": self.catalog_sha256,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "contract_sha256": self.contract_sha256,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "effect_id": self.effect_id,
            "effect": self.effect,
            "classification": self.classification,
            "annual_premium_cents": self.annual_premium_cents,
            "direct_cost_usd_micros": self.direct_cost_usd_micros,
            "personnel_seconds": self.personnel_seconds,
            "status": self.status.value,
            "gross_expected_value_usd_micros": self.gross_expected_value_usd_micros,
            "net_expected_value_usd_micros": self.net_expected_value_usd_micros,
            "metric_id": self.metric_id,
            "error_code": self.error_code,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


@dataclass(frozen=True)
class EconomicsResourceContract:
    contract_id: str
    version: str
    sha256: str
    catalog: SemanticCatalog
    actions_by_id: Mapping[str, ActionEconomics]
    actions_by_type: Mapping[str, ActionEconomics]
    evaluation_protocol: Mapping[str, Any]

    def action(self, value: str) -> ActionEconomics:
        action = self.actions_by_id.get(value) or self.actions_by_type.get(value)
        if action is None:
            raise EconomicsContractError("UNKNOWN_ACTION_ID", "unknown action identity")
        return action

    def value(
        self,
        *,
        policy_id: str,
        snapshot_id: str,
        snapshot_version: str,
        catalog_sha256: str,
        action: str,
        effect: Decimal | str | int | float | SignedTreatmentEffect,
        annual_premium_cents: int | None,
    ) -> EconomicValuation:
        if not policy_id or not snapshot_id:
            raise EconomicsContractError("INVALID_VALUATION_CONTEXT", "identity is required")
        if snapshot_version != self.catalog.snapshot_version or catalog_sha256 != self.catalog.sha256:
            raise EconomicsContractError(
                "INCOMPATIBLE_SNAPSHOT_CONTRACT", "snapshot or catalog identity mismatch"
            )
        action_economics = self.action(action)
        signed = effect if isinstance(effect, SignedTreatmentEffect) else SignedTreatmentEffect(effect)
        common = dict(
            policy_id=policy_id,
            snapshot_id=snapshot_id,
            snapshot_version=snapshot_version,
            catalog_sha256=catalog_sha256,
            contract_id=self.contract_id,
            contract_version=self.version,
            contract_sha256=self.sha256,
            action_id=action_economics.action_id,
            action_type=action_economics.action_type,
            effect_id=signed.effect_id,
            effect=signed.canonical_value(),
            classification=signed.classification,
        )
        if annual_premium_cents is None:
            return EconomicValuation(
                **common,
                annual_premium_cents=None,
                direct_cost_usd_micros=None,
                personnel_seconds=None,
                status=ValuationStatus.UNAVAILABLE,
                error_code="VALUATION_UNAVAILABLE",
            )
        if isinstance(annual_premium_cents, bool) or not isinstance(annual_premium_cents, int):
            raise EconomicsContractError(
                "INVALID_ANNUAL_PREMIUM", "annual premium must be integer cents"
            )
        if annual_premium_cents < 0:
            raise EconomicsContractError(
                "INVALID_ANNUAL_PREMIUM", "annual premium cannot be negative"
            )
        gross = int(
            (signed.value * Decimal(annual_premium_cents * USD_MICROS_PER_CENT)).quantize(
                Decimal("1"), rounding=ROUND_HALF_EVEN
            )
        )
        return EconomicValuation(
            **common,
            annual_premium_cents=annual_premium_cents,
            direct_cost_usd_micros=action_economics.direct_cost_usd_micros,
            personnel_seconds=action_economics.personnel_seconds,
            status=ValuationStatus.AVAILABLE,
            gross_expected_value_usd_micros=gross,
            net_expected_value_usd_micros=gross - action_economics.direct_cost_usd_micros,
        )


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_economics_resource_contract(
    version: str = ECONOMICS_CONTRACT_VERSION,
    *,
    repository_root: Path | None = None,
    catalog: SemanticCatalog | None = None,
) -> EconomicsResourceContract:
    if version != ECONOMICS_CONTRACT_VERSION:
        raise EconomicsContractError(
            "INCOMPATIBLE_ECONOMICS_CONTRACT", "unsupported economics contract version"
        )
    root = (repository_root or _repository_root()).resolve()
    contract_dir = root / "data-contracts" / "rh" / "economics" / "v1"
    try:
        data = json.loads((contract_dir / "economics-resource-contract.json").read_text())
        schema = json.loads(
            (contract_dir / "economics-resource-contract.schema.json").read_text()
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise EconomicsContractError(
            "INCOMPATIBLE_ECONOMICS_CONTRACT", "contract resources are unavailable"
        ) from exc
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise EconomicsContractError(
            "INCOMPATIBLE_ECONOMICS_CONTRACT", "contract resource fails validation"
        )
    semantic = catalog or load_semantic_catalog(repository_root=root)
    expected_catalog = data["semantic_catalog"]
    catalog_path = root / str(expected_catalog["path"])
    try:
        pinned_catalog_sha256 = sha256(catalog_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise EconomicsContractError(
            "INCOMPATIBLE_ECONOMICS_CONTRACT", "pinned semantic catalog is unavailable"
        ) from exc
    if (
        semantic.version != expected_catalog["version"]
        or pinned_catalog_sha256 != expected_catalog["sha256"]
    ):
        raise EconomicsContractError(
            "INCOMPATIBLE_ECONOMICS_CONTRACT", "pinned semantic catalog identity mismatch"
        )
    catalog_types = {
        str(item["action_id"]): str(item["action_type"])
        for item in semantic.data["actions"]
    }
    actions = tuple(
        ActionEconomics(
            action_id=str(item["action_id"]),
            action_type=catalog_types[str(item["action_id"])],
            direct_cost_usd_micros=int(item["direct_cost_usd_micros"]),
            personnel_seconds=int(item["personnel_seconds"]),
        )
        for item in data["actions"]
    )
    return EconomicsResourceContract(
        contract_id=str(data["contract_id"]),
        version=str(data["contract_version"]),
        sha256=sha256(canonical_json_bytes(data)).hexdigest(),
        catalog=semantic,
        actions_by_id=MappingProxyType({item.action_id: item for item in actions}),
        actions_by_type=MappingProxyType({item.action_type: item for item in actions}),
        evaluation_protocol=_freeze(data["evaluation_protocol"]),
    )
