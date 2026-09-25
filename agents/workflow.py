"""P5-01 typed agent seams. All input is fictional and all output is advisory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable


CONTRACT_VERSION = "1.0.0"
MAX_FACTS = 128
MAX_PROCEDURES = 32
MAX_ACTIONS = 16
MAX_FACT_VALUE_CHARS = 512
MAX_PROCEDURE_TEXT_CHARS = 4_096
_INJECTION_MARKERS = (
    "ignore previous", "ignore all", "system prompt", "developer message",
    "override rules", "authorized_to_act", "execute action", "call tool",
)


@dataclass(frozen=True)
class Fact:
    key: str
    value: str
    observed_at: datetime
    source_id: str


@dataclass(frozen=True)
class Procedure:
    procedure_id: str
    version: str
    effective_from: datetime
    effective_until: datetime
    action_ids: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class CaseInput:
    case_id: str
    as_of: datetime
    facts: tuple[Fact, ...]
    procedures: tuple[Procedure, ...]
    allowed_actions: tuple[str, ...]  # Trusted deterministic rules output.
    required_fact_keys: tuple[str, ...]
    minimum_procedure_versions: tuple[tuple[str, str], ...]
    confidence: float


@dataclass(frozen=True)
class ReviewDraft:
    case_id: str
    status: str
    action_id: str | None
    reason_codes: tuple[str, ...]
    evidence_source_ids: tuple[str, ...]
    procedure_citations: tuple[str, ...]
    contract_version: str = CONTRACT_VERSION
    authorized_to_act: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.authorized_to_act is not False or self.human_review_required is not True:
            raise ValueError("agent output cannot grant action authority")
        if self.status not in {"DRAFT_FOR_REVIEW", "ABSTAIN"}:
            raise ValueError("invalid review status")
        if self.status == "ABSTAIN" and self.action_id is not None:
            raise ValueError("abstention cannot contain an action")
        if self.status == "DRAFT_FOR_REVIEW" and (not self.action_id or not self.procedure_citations):
            raise ValueError("recommendations require an action and procedure citation")


def _abstain(case_id: str, *reasons: str) -> ReviewDraft:
    return ReviewDraft(case_id, "ABSTAIN", None, tuple(sorted(set(reasons))), (), ())


def _version(value: str) -> tuple[int, ...]:
    parts = value.split(".")
    if not parts or not all(part.isdecimal() for part in parts):
        raise ValueError("procedure version must be numeric dotted components")
    return tuple(int(part) for part in parts)


def build_review_draft(case: CaseInput, *, clock: Callable[[], None] | None = None) -> ReviewDraft:
    """Run three bounded seams; any uncertain or unsafe input yields abstention."""
    try:
        if clock:
            clock()  # An adapter may raise TimeoutError at a bounded tool boundary.
        if not case.case_id or case.as_of.tzinfo is None:
            return _abstain(case.case_id, "INVALID_CASE_ID_OR_CUTOFF")
        if len(case.facts) > MAX_FACTS or len(case.procedures) > MAX_PROCEDURES or len(case.allowed_actions) > MAX_ACTIONS:
            return _abstain(case.case_id, "INPUT_LIMIT_EXCEEDED")
        if not 0 <= case.confidence <= 1 or case.confidence < 0.8:
            return _abstain(case.case_id, "LOW_CONFIDENCE")
        if not case.facts or not case.required_fact_keys:
            return _abstain(case.case_id, "MISSING_EVIDENCE")
        if not case.allowed_actions or len(set(case.allowed_actions)) != len(case.allowed_actions):
            return _abstain(case.case_id, "NO_TRUSTED_ACTIONS")
        if not case.minimum_procedure_versions or len(set(case.minimum_procedure_versions)) != len(case.minimum_procedure_versions):
            return _abstain(case.case_id, "PROCEDURE_VERSION_REQUIRED")

        # Evidence agent: only point-in-time facts with unambiguous values.
        facts: dict[str, Fact] = {}
        for fact in case.facts:
            if (not fact.key or not fact.value or not fact.source_id or
                    len(fact.value) > MAX_FACT_VALUE_CHARS or fact.observed_at.tzinfo is None):
                return _abstain(case.case_id, "INVALID_EVIDENCE")
            if fact.observed_at > case.as_of:
                return _abstain(case.case_id, "FUTURE_EVIDENCE")
            prior = facts.get(fact.key)
            if prior and prior.value != fact.value:
                return _abstain(case.case_id, "CONFLICTING_EVIDENCE")
            facts[fact.key] = fact
        if any(key not in facts for key in case.required_fact_keys):
            return _abstain(case.case_id, "MISSING_EVIDENCE")
        if clock:
            clock()

        # Procedure agent: data-only citations, version and effective-date checked.
        minimums = dict(case.minimum_procedure_versions)
        candidates: list[Procedure] = []
        for procedure in case.procedures:
            if (not procedure.procedure_id or not procedure.text or not procedure.version or
                    len(procedure.text) > MAX_PROCEDURE_TEXT_CHARS):
                return _abstain(case.case_id, "INVALID_PROCEDURE")
            if any(marker in procedure.text.lower() for marker in _INJECTION_MARKERS):
                return _abstain(case.case_id, "PROCEDURE_INJECTION")
            if procedure.procedure_id in minimums and _version(procedure.version) < _version(minimums[procedure.procedure_id]):
                return _abstain(case.case_id, "PROCEDURE_VERSION_MISMATCH")
            if procedure.effective_from.tzinfo is None or procedure.effective_until.tzinfo is None:
                return _abstain(case.case_id, "INVALID_PROCEDURE_DATES")
            if procedure.effective_from <= case.as_of < procedure.effective_until:
                candidates.append(procedure)
        if any(procedure_id not in {p.procedure_id for p in candidates} for procedure_id in minimums):
            return _abstain(case.case_id, "REQUIRED_PROCEDURE_MISSING")
        if not candidates:
            return _abstain(case.case_id, "NO_CURRENT_PROCEDURE")
        if clock:
            clock()

        # Planner: intersection with the rules allowlist; never infer an action
        # from procedure prose or evidence. Abstain if no cited match exists.
        for action in case.allowed_actions:
            if action == "abstain":
                continue
            matching = sorted((p for p in candidates if action in p.action_ids),
                              key=lambda p: (p.procedure_id, _version(p.version)))
            if matching:
                cited = matching[0]
                return ReviewDraft(case.case_id, "DRAFT_FOR_REVIEW", action, (),
                                   tuple(sorted({fact.source_id for fact in facts.values()})),
                                   (f"{cited.procedure_id}@{cited.version}",))
        return _abstain(case.case_id, "NO_ALLOWED_PROCEDURE_ACTION")
    except TimeoutError:
        return _abstain(case.case_id, "TOOL_TIMEOUT")
    except (TypeError, ValueError):
        return _abstain(case.case_id, "INVALID_INPUT")
