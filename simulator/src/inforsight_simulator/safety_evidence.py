"""Versioned, dual-time safety evidence for RH-02 eligibility decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable, Mapping

from .semantic_catalog import canonical_json_bytes


SAFETY_EVIDENCE_VERSION = "1.0.0"
SAFETY_SOURCE_PROFILE = "fictional-safety-events/1.0.0"
SAFETY_FIELDS = (
    "has_active_claim", "has_legal_hold", "has_registered_dispute",
    "sms_opt_out", "email_opt_out", "phone_opt_out", "dnc_registered",
)


class SafetyEvidenceError(ValueError):
    def __init__(self, code: str, event_id: str | None = None) -> None:
        self.code, self.event_id = code, event_id
        super().__init__(code + (f" (event_id={event_id})" if event_id else ""))


@dataclass(frozen=True)
class SafetyEvidence:
    evidence_version: str
    source_profile: str
    evidence_id: str
    policy_id: str
    as_of: str
    snapshot_id: str
    has_active_claim: bool | None
    has_legal_hold: bool | None
    has_registered_dispute: bool | None
    sms_opt_out: bool | None
    email_opt_out: bool | None
    phone_opt_out: bool | None
    dnc_registered: bool | None
    field_evidence: tuple[tuple[str, tuple[str, ...]], ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["field_evidence"] = {
            field: list(ids) for field, ids in self.field_evidence
        }
        return value

    def validate_context(self, *, policy_id: str, as_of: str, snapshot_id: str) -> None:
        if (policy_id, _time(as_of), snapshot_id) != (
            self.policy_id, self.as_of, self.snapshot_id
        ) or _evidence_id(self.to_dict()) != self.evidence_id:
            raise SafetyEvidenceError("EVIDENCE_CONTEXT_MISMATCH")


def _parse_time(value: Any, event_id: str | None = None) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SafetyEvidenceError("INVALID_SAFETY_ENVELOPE", event_id)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise SafetyEvidenceError("INVALID_SAFETY_ENVELOPE", event_id) from exc
    return parsed.astimezone(timezone.utc)


def _time(value: str) -> str:
    return _parse_time(value).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _evidence_id(value: Mapping[str, Any]) -> str:
    content = dict(value)
    content.pop("evidence_id", None)
    return sha256(canonical_json_bytes(content)).hexdigest()


def reconstruct_safety_evidence(
    history: Iterable[Mapping[str, Any]], *, policy_id: str, as_of: str,
    snapshot_id: str, source_profile: str = SAFETY_SOURCE_PROFILE,
) -> SafetyEvidence:
    """Replay cutoff-visible fictional safety facts into a snapshot-bound artifact."""

    if source_profile != SAFETY_SOURCE_PROFILE or not policy_id or not snapshot_id:
        raise SafetyEvidenceError("INCOMPATIBLE_SAFETY_CONTRACT")
    cutoff = _parse_time(as_of)
    prepared: list[tuple[datetime, str, Mapping[str, Any]]] = []
    for raw in tuple(history):
        event_id = raw.get("event_id") if isinstance(raw, Mapping) else None
        if not isinstance(event_id, str) or not event_id:
            raise SafetyEvidenceError("INVALID_SAFETY_ENVELOPE")
        if set(raw) != {"schema_version", "event_id", "policy_id", "event_type", "effective_at", "ingested_at", "payload"}:
            raise SafetyEvidenceError("INVALID_SAFETY_ENVELOPE", event_id)
        if raw["schema_version"] != SAFETY_EVIDENCE_VERSION or raw["policy_id"] != policy_id:
            raise SafetyEvidenceError("INVALID_SAFETY_ENVELOPE", event_id)
        effective, ingested = _parse_time(raw["effective_at"], event_id), _parse_time(raw["ingested_at"], event_id)
        if effective <= cutoff and ingested <= cutoff:
            prepared.append((effective, event_id, raw))
    prepared.sort(key=lambda item: (item[0], item[1]))
    if len({event_id for _, event_id, _ in prepared}) != len(prepared):
        raise SafetyEvidenceError("DUPLICATE_SAFETY_EVENT")

    facts: dict[str, bool | None] = {field: None for field in SAFETY_FIELDS}
    evidence: dict[str, tuple[str, ...]] = {field: () for field in SAFETY_FIELDS}
    recorded: dict[str, Mapping[str, Any]] = {}
    instants: dict[tuple[datetime, str], bool] = {}
    for effective, event_id, event in prepared:
        kind, payload = event["event_type"], event["payload"]
        if not isinstance(payload, Mapping):
            raise SafetyEvidenceError("INVALID_SAFETY_PAYLOAD", event_id)
        if kind == "safety.facts_recorded":
            if not payload or not set(payload).issubset(SAFETY_FIELDS) or any(type(v) is not bool for v in payload.values()):
                raise SafetyEvidenceError("INVALID_SAFETY_PAYLOAD", event_id)
            recorded[event_id] = dict(payload)
            updates = payload
        elif kind == "safety.facts_corrected":
            if set(payload) != {"target_event_id", "replacement"} or payload["target_event_id"] not in recorded:
                raise SafetyEvidenceError("INVALID_SAFETY_CORRECTION", event_id)
            updates = payload["replacement"]
            if not isinstance(updates, Mapping) or not updates or not set(updates).issubset(recorded[payload["target_event_id"]]) or any(type(v) is not bool for v in updates.values()):
                raise SafetyEvidenceError("INVALID_SAFETY_CORRECTION", event_id)
        else:
            raise SafetyEvidenceError("UNSUPPORTED_SAFETY_EVENT", event_id)
        for field, value in updates.items():
            key = (effective, field)
            if key in instants and instants[key] != value:
                raise SafetyEvidenceError("CONTRADICTORY_SAFETY_EVIDENCE", event_id)
            instants[key] = value
            facts[field], evidence[field] = value, (event_id,)

    item = SafetyEvidence(
        evidence_version=SAFETY_EVIDENCE_VERSION, source_profile=source_profile,
        evidence_id="", policy_id=policy_id, as_of=_time(as_of), snapshot_id=snapshot_id,
        field_evidence=tuple((field, evidence[field]) for field in SAFETY_FIELDS), **facts,
    )
    return replace(item, evidence_id=_evidence_id(item.to_dict()))
