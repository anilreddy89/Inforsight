"""RH-08 structured grounding contract implementation.

This module deliberately validates a bounded statement grammar rather than
claiming to prove arbitrary provider prose true.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


GROUNDING_CONTRACT_VERSION = "inforsight.structured-grounding/1.0.0"


class GroundingErrorCode(StrEnum):
    CONTEXT_INVALID = "GROUNDING_CONTEXT_INVALID"
    CONTEXT_MISMATCH = "GROUNDING_CONTEXT_MISMATCH"
    EVIDENCE_MISSING = "GROUNDING_EVIDENCE_MISSING"
    EVIDENCE_UNRESOLVED = "GROUNDING_EVIDENCE_UNRESOLVED"
    UNKNOWN_VALUE = "GROUNDING_UNKNOWN_VALUE"
    STATEMENT_UNSUPPORTED = "GROUNDING_STATEMENT_UNSUPPORTED"
    VALUE_INVALID = "GROUNDING_VALUE_INVALID"
    AUTHORITY_CLAIM = "GROUNDING_AUTHORITY_CLAIM"
    CAUSAL_CLAIM = "GROUNDING_CAUSAL_CLAIM"
    PROVIDER_OUTPUT_INVALID = "GROUNDING_PROVIDER_OUTPUT_INVALID"
    FALLBACK_REQUIRED = "GROUNDING_FALLBACK_REQUIRED"


class GroundingContractError(ValueError):
    """Safe structured-grounding error without source payload echoing."""

    def __init__(self, code: GroundingErrorCode, summary: str) -> None:
        self.code = code
        super().__init__(summary)


class StatementKind(StrEnum):
    POLICY_ID = "POLICY_ID"
    CASE_ID = "CASE_ID"
    CUTOFF_DATE = "CUTOFF_DATE"
    TIMELINE_EVENT = "TIMELINE_EVENT"
    PRODUCT_TYPE = "PRODUCT_TYPE"
    PAYMENT_FREQUENCY = "PAYMENT_FREQUENCY"
    PREMIUM_AMOUNT = "PREMIUM_AMOUNT"
    COVERAGE_AMOUNT = "COVERAGE_AMOUNT"
    TENURE_DURATION = "TENURE_DURATION"
    STATUS = "STATUS"
    DELINQUENCY = "DELINQUENCY"
    RISK_SCORE = "RISK_SCORE"
    RISK_DRIVER = "RISK_DRIVER"
    ELIGIBLE_ACTION = "ELIGIBLE_ACTION"
    RECOMMENDED_ACTION = "RECOMMENDED_ACTION"
    DISQUALIFIED_ACTION = "DISQUALIFIED_ACTION"
    SAFETY_FACT = "SAFETY_FACT"
    DISCLAIMER = "DISCLAIMER"


@dataclass(frozen=True)
class Evidence:
    """One typed evidence item available to a narrative statement."""

    evidence_id: str
    policy_id: str
    cutoff: str
    kind: StatementKind
    value: Any
    identity: str = "snapshot"


@dataclass(frozen=True)
class NarrativeContext:
    """Immutable identity and evidence boundary for RH-08 narratives."""

    policy_id: str
    case_id: str
    cutoff: str
    snapshot_id: str
    evidence: tuple[Evidence, ...]
    score_identity: str | None = None
    eligibility_identity: str | None = None
    grounding_contract_version: str = GROUNDING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.policy_id or not self.case_id or not self.cutoff or not self.snapshot_id:
            raise GroundingContractError(
                GroundingErrorCode.CONTEXT_INVALID,
                "Narrative context requires policy, case, cutoff, and snapshot identities",
            )
        if self.grounding_contract_version != GROUNDING_CONTRACT_VERSION:
            raise GroundingContractError(
                GroundingErrorCode.CONTEXT_INVALID,
                "Unsupported structured-grounding contract version",
            )
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise GroundingContractError(
                GroundingErrorCode.CONTEXT_INVALID,
                "Narrative evidence identifiers must be unique",
            )
        if any(item.policy_id != self.policy_id or item.cutoff > self.cutoff for item in self.evidence):
            raise GroundingContractError(
                GroundingErrorCode.CONTEXT_MISMATCH,
                "Narrative evidence does not match policy or cutoff",
            )

    def resolve(self, statement: "NarrativeStatement") -> tuple[Evidence, ...]:
        if statement.policy_id != self.policy_id:
            raise GroundingContractError(GroundingErrorCode.CONTEXT_MISMATCH, "Statement policy does not match context")
        if not statement.evidence_ids:
            raise GroundingContractError(GroundingErrorCode.EVIDENCE_MISSING, "Statement requires evidence identifiers")
        by_id = {item.evidence_id: item for item in self.evidence}
        resolved: list[Evidence] = []
        for evidence_id in statement.evidence_ids:
            item = by_id.get(evidence_id)
            if item is None:
                raise GroundingContractError(GroundingErrorCode.EVIDENCE_UNRESOLVED, "Statement evidence cannot be resolved")
            if item.kind != statement.kind:
                raise GroundingContractError(GroundingErrorCode.EVIDENCE_UNRESOLVED, "Evidence kind does not support statement kind")
            resolved.append(item)
        return tuple(resolved)


def context_from_case_evidence(context: Any, *, snapshot_id: str = "legacy-case-evidence") -> NarrativeContext:
    """Build a bounded compatibility context from the existing assistant context.

    The adapter is intentionally explicit and names its synthetic identity; it
    does not imply that legacy fields are RH-01 source evidence.
    """
    evidence = [
        Evidence("legacy:policy_id", context.policy_id, context.as_of_date, StatementKind.POLICY_ID, context.policy_id, "legacy-adapter"),
        Evidence("legacy:product_type", context.policy_id, context.as_of_date, StatementKind.PRODUCT_TYPE, context.product_type, "legacy-adapter"),
        Evidence("legacy:status", context.policy_id, context.as_of_date, StatementKind.STATUS, context.policy_status, "legacy-adapter"),
        Evidence("legacy:recommended_action", context.policy_id, context.as_of_date, StatementKind.RECOMMENDED_ACTION, context.primary_action, "legacy-adapter"),
        Evidence("legacy:risk_score", context.policy_id, context.as_of_date, StatementKind.RISK_SCORE, context.calibrated_probability, "legacy-adapter"),
    ]
    return NarrativeContext(
        policy_id=context.policy_id,
        case_id=context.case_id,
        cutoff=context.as_of_date,
        snapshot_id=snapshot_id,
        evidence=tuple(evidence),
        score_identity="legacy-score-context",
        eligibility_identity="legacy-eligibility-context",
    )


@dataclass(frozen=True)
class NarrativeStatement:
    """A grammar-constrained factual statement slot."""

    statement_id: str
    policy_id: str
    kind: StatementKind
    value: Any
    evidence_ids: tuple[str, ...]


_PROHIBITED_KINDS = {
    "AUTHORIZATION", "CONSENT", "EXECUTION", "CAUSAL", "GUARANTEE", "TRUTH", "AUTHENTICITY",
}


def validate_statements(context: NarrativeContext, statements: tuple[NarrativeStatement, ...]) -> tuple[NarrativeStatement, ...]:
    """Validate and return statements in their declared order."""
    accepted: list[NarrativeStatement] = []
    seen: set[str] = set()
    for statement in statements:
        if statement.statement_id in seen:
            raise GroundingContractError(GroundingErrorCode.VALUE_INVALID, "Statement identifiers must be unique")
        seen.add(statement.statement_id)
        if str(statement.kind) in _PROHIBITED_KINDS:
            raise GroundingContractError(GroundingErrorCode.CAUSAL_CLAIM, "Unsupported causal or authority claim")
        evidence = context.resolve(statement)
        if statement.value is None:
            raise GroundingContractError(GroundingErrorCode.UNKNOWN_VALUE, "Unknown values cannot be rendered as factual statements")
        if not any(item.value == statement.value for item in evidence):
            raise GroundingContractError(GroundingErrorCode.VALUE_INVALID, "Statement value does not match bound evidence")
        if statement.kind in {StatementKind.ELIGIBLE_ACTION, StatementKind.RECOMMENDED_ACTION} and not context.eligibility_identity:
            raise GroundingContractError(GroundingErrorCode.CONTEXT_MISMATCH, "Action statement requires eligibility identity")
        if statement.kind == StatementKind.RISK_SCORE and not context.score_identity:
            raise GroundingContractError(GroundingErrorCode.CONTEXT_MISMATCH, "Score statement requires score identity")
        accepted.append(statement)
    return tuple(accepted)


def render_statements(context: NarrativeContext, statements: tuple[NarrativeStatement, ...]) -> tuple[str, ...]:
    """Render accepted statements as deterministic, non-authoritative text."""
    validated = validate_statements(context, statements)
    rendered: list[str] = []
    for statement in validated:
        if statement.kind == StatementKind.RISK_SCORE:
            rendered.append(f"Model-estimated risk: {statement.value}.")
        elif statement.kind == StatementKind.RECOMMENDED_ACTION:
            rendered.append(f"Modeled recommended action: {statement.value}.")
        elif statement.kind == StatementKind.ELIGIBLE_ACTION:
            rendered.append(f"Eligible action: {statement.value}.")
        else:
            rendered.append(f"{statement.kind.value.replace('_', ' ').title()}: {statement.value}.")
    return tuple(rendered)


def validate_provider_payload(payload: Mapping[str, Any], context: NarrativeContext) -> tuple[str, ...]:
    """Accept only a list of grammar statements from a provider adapter."""
    raw = payload.get("statements")
    if not isinstance(raw, list):
        raise GroundingContractError(GroundingErrorCode.PROVIDER_OUTPUT_INVALID, "Provider output must contain statements")
    statements: list[NarrativeStatement] = []
    try:
        for item in raw:
            if not isinstance(item, Mapping):
                raise TypeError
            statements.append(NarrativeStatement(
                statement_id=str(item["statement_id"]),
                policy_id=str(item["policy_id"]),
                kind=StatementKind(str(item["kind"])),
                value=item["value"],
                evidence_ids=tuple(str(value) for value in item["evidence_ids"]),
            ))
    except (KeyError, TypeError, ValueError):
        raise GroundingContractError(GroundingErrorCode.PROVIDER_OUTPUT_INVALID, "Provider output is not a valid statement payload") from None
    return render_statements(context, tuple(statements))
