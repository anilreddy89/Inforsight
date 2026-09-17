"""Bounded local validators for the reconciled RH-09 P4-01 contracts."""

from dataclasses import dataclass
from typing import Any, Mapping


class ContractViolation(ValueError):
    """Stable, non-sensitive contract failure."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ContractContext:
    case_id: str
    expected_case_version: int
    idempotency_key: str
    actor_id: str
    reviewed_evidence_digest: str


CANONICAL_TIERS = frozenset({"TIER_1_LOW", "TIER_2_ELEVATED", "TIER_3_HIGH", "TIER_4_CRITICAL"})


def require_context(request: Mapping[str, Any]) -> ContractContext:
    """Validate required mutating-request bindings without echoing payload data."""
    required = ("case_id", "expected_case_version", "idempotency_key", "actor_id", "reviewed_evidence_digest")
    if any(request.get(key) in (None, "") for key in required):
        raise ContractViolation("CONTRACT_CONTEXT_REQUIRED")
    if not isinstance(request["expected_case_version"], int) or request["expected_case_version"] < 0:
        raise ContractViolation("INVALID_EXPECTED_CASE_VERSION")
    return ContractContext(*(request[key] for key in required))


def require_authority(value: Any) -> bool:
    """Require explicit boolean authority; absence and unknown values fail closed."""
    if type(value) is not bool:
        raise ContractViolation("AUTHORITY_EXPLICIT_REQUIRED")
    return value


def require_risk_tier(value: Any) -> str:
    if value not in CANONICAL_TIERS:
        raise ContractViolation("UNKNOWN_RISK_TIER")
    return value


def require_override(request: Mapping[str, Any]) -> None:
    """Require trusted review evidence and rationale for an override."""
    if request.get("override") is not True:
        return
    required = ("trusted_reviewer_id", "override_rationale", "reviewed_case_version", "reviewed_evidence_digest")
    if any(request.get(key) in (None, "") for key in required):
        raise ContractViolation("OVERRIDE_EVIDENCE_REQUIRED")
    if not isinstance(request["reviewed_case_version"], int):
        raise ContractViolation("INVALID_REVIEWED_CASE_VERSION")


def require_identity_bindings(request: Mapping[str, Any], expected: Mapping[str, str]) -> None:
    """Reject missing or mismatched semantic identities without exposing values."""
    for name, expected_value in expected.items():
        if request.get(name) in (None, ""):
            raise ContractViolation("IDENTITY_REQUIRED")
        if request[name] != expected_value:
            raise ContractViolation("IDENTITY_MISMATCH")


def require_current_case_version(expected: int, current: int) -> None:
    if expected != current:
        raise ContractViolation("STALE_CASE_VERSION")


class IdempotencyGuard:
    """Small in-memory replay guard for bounded local/reference behavior."""

    def __init__(self):
        self._requests: dict[str, str] = {}

    def check_and_record(self, key: str, request_fingerprint: str) -> None:
        if not key:
            raise ContractViolation("IDEMPOTENCY_KEY_REQUIRED")
        prior = self._requests.get(key)
        if prior is not None:
            if prior != request_fingerprint:
                raise ContractViolation("IDEMPOTENCY_KEY_REUSED")
            raise ContractViolation("REQUEST_REPLAYED")
        self._requests[key] = request_fingerprint
