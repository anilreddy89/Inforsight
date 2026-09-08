"""Immutable dual-time domain snapshots governed by RH-01 contract 1.0.0."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from typing import Any, Iterable, Mapping, Sequence

from .semantic_catalog import (
    CATALOG_VERSION,
    SNAPSHOT_VERSION,
    CatalogContractError,
    SemanticCatalog,
    canonical_json_bytes,
)
from .validation import _policy_event_validator


LEGACY_PROFILE = "legacy-policy-events/1.0.0"
V6_PROFILE = "v6-policy-events/6.0.0"
_VERSIONS = {LEGACY_PROFILE: "1.0.0", V6_PROFILE: "6.0.0"}
_LEGACY_TYPES = {
    "policy.issued", "policy.status_changed", "billing.premium_due",
    "payment.received", "payment.failed", "notice.sent",
    "service.contact_recorded", "outcome.lapsed", "outcome.surrendered",
}
_V6_TYPES = {
    "policy.issued", "payment.recorded", "notice.sent", "service.contact",
    "event.corrected", "outcome.lapsed", "outcome.surrendered",
}
_TRANSITIONS = {
    ("active", "grace_period"), ("active", "surrendered"),
    ("grace_period", "active"), ("grace_period", "lapsed"),
    ("grace_period", "surrendered"),
}


class SnapshotContractError(ValueError):
    """Stable, payload-safe failure raised by snapshot reconstruction."""

    def __init__(self, code: str, event_id: str | None = None) -> None:
        self.code = code
        self.event_id = event_id
        suffix = f" (event_id={event_id})" if event_id else ""
        super().__init__(f"{code}{suffix}")


@dataclass(frozen=True)
class EventProvenance:
    event_id: str
    event_sha256: str


@dataclass(frozen=True)
class SafetyFacts:
    has_active_claim: None = None
    has_legal_hold: None = None
    has_registered_dispute: None = None
    sms_opt_out: None = None
    email_opt_out: None = None
    phone_opt_out: None = None
    dnc_registered: None = None


@dataclass(frozen=True)
class FieldEvidence:
    issuance: tuple[str, ...]
    status: tuple[str, ...]
    grace: tuple[str, ...]
    days_past_due: tuple[str, ...]


@dataclass(frozen=True)
class DomainSnapshot:
    snapshot_version: str
    catalog_version: str
    catalog_sha256: str
    source_profile: str
    snapshot_id: str
    policy_id: str
    as_of: str
    issued_at: str
    product_type: str
    status: str
    billing_frequency: str
    premium_amount_cents: int
    currency: str
    annual_premium_cents: int
    tenure_days: int
    in_grace_period: bool | None
    days_in_grace: int | None
    grace_entered_at: str | None
    days_past_due: int | None
    coverage_amount_cents: None
    total_premiums_paid_cents: None
    safety: SafetyFacts
    provenance: tuple[EventProvenance, ...]
    field_evidence: FieldEvidence

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["provenance"] = list(value["provenance"])
        for field, evidence in value["field_evidence"].items():
            value["field_evidence"][field] = list(evidence)
        return value

    def validate_identity(self, catalog: SemanticCatalog) -> None:
        if (
            self.snapshot_version != SNAPSHOT_VERSION
            or self.catalog_version != catalog.version
            or self.catalog_sha256 != catalog.sha256
            or _snapshot_id(self.to_dict()) != self.snapshot_id
        ):
            raise SnapshotContractError("INCOMPATIBLE_CONTRACT")

    def validate_context(
        self, *, policy_id: str, as_of: datetime | str, catalog: SemanticCatalog
    ) -> None:
        """Require a consumer context to name this exact policy and cutoff."""

        self.validate_identity(catalog)
        if policy_id != self.policy_id or _timestamp(_parse_cutoff(as_of)) != self.as_of:
            raise SnapshotContractError("CONTEXT_MISMATCH")


@dataclass(frozen=True)
class _PreparedEvent:
    event: Mapping[str, Any]
    effective_at: datetime
    ingested_at: datetime
    occurred_at: datetime | None


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_cutoff(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise SnapshotContractError("INVALID_TIME")
        return value.astimezone(timezone.utc)
    if not isinstance(value, str):
        raise SnapshotContractError("INVALID_TIME")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotContractError("INVALID_TIME") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SnapshotContractError("INVALID_TIME")
    return parsed.astimezone(timezone.utc)


def _parse_source_time(value: Any, event_id: str | None) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SnapshotContractError("INVALID_ENVELOPE", event_id)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise SnapshotContractError("INVALID_ENVELOPE", event_id) from exc
    return parsed.astimezone(timezone.utc)


def _finite_json(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_json(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_finite_json(item) for item in value)
    return value is None or isinstance(value, (str, int, bool))


def _prepare_envelopes(
    history: Iterable[Mapping[str, Any]], policy_id: str, source_profile: str
) -> tuple[_PreparedEvent, ...]:
    if not isinstance(policy_id, str) or not policy_id:
        raise SnapshotContractError("INVALID_ENVELOPE")
    expected_version = _VERSIONS.get(source_profile)
    if expected_version is None:
        raise SnapshotContractError("INCOMPATIBLE_CONTRACT")
    try:
        events = tuple(history)
    except TypeError as exc:
        raise SnapshotContractError("INVALID_ENVELOPE") from exc
    prepared: list[_PreparedEvent] = []
    for raw in events:
        if not isinstance(raw, Mapping):
            raise SnapshotContractError("INVALID_ENVELOPE")
        event_id = raw.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise SnapshotContractError("INVALID_ENVELOPE")
        if raw.get("policy_id") != policy_id or raw.get("schema_version") != expected_version:
            raise SnapshotContractError("INVALID_ENVELOPE", event_id)
        if not isinstance(raw.get("event_type"), str) or not isinstance(raw.get("payload"), Mapping):
            raise SnapshotContractError("INVALID_ENVELOPE", event_id)
        if not _finite_json(raw):
            raise SnapshotContractError("INVALID_ENVELOPE", event_id)
        effective = _parse_source_time(raw.get("effective_at"), event_id)
        ingested = _parse_source_time(raw.get("ingested_at"), event_id)
        occurred = None
        if source_profile == LEGACY_PROFILE:
            occurred = _parse_source_time(raw.get("occurred_at"), event_id)
        prepared.append(_PreparedEvent(dict(raw), effective, ingested, occurred))
    return tuple(prepared)


def select_visible_events(
    history: Iterable[Mapping[str, Any]], *, policy_id: str, as_of: datetime | str,
    source_profile: str,
) -> tuple[Mapping[str, Any], ...]:
    """Return validated envelopes visible at a dual-time cutoff, in replay order."""

    cutoff = _parse_cutoff(as_of)
    selected = [
        item for item in _prepare_envelopes(history, policy_id, source_profile)
        if item.effective_at <= cutoff and item.ingested_at <= cutoff
    ]
    if source_profile == LEGACY_PROFILE:
        selected.sort(key=lambda item: (item.effective_at, item.occurred_at, item.event["event_id"]))
    else:
        selected.sort(key=lambda item: (item.effective_at, item.event["event_id"]))
    return tuple(item.event for item in selected)


def _require_exact_keys(payload: Mapping[str, Any], required: set[str], event_id: str) -> None:
    if set(payload) != required:
        raise SnapshotContractError("INVALID_PAYLOAD", event_id)


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_payload(event: Mapping[str, Any], profile: str) -> None:
    event_id = str(event["event_id"])
    kind = event["event_type"]
    payload = event["payload"]
    allowed = _LEGACY_TYPES if profile == LEGACY_PROFILE else _V6_TYPES
    if kind not in allowed:
        raise SnapshotContractError("UNSUPPORTED_EVENT", event_id)
    if profile == LEGACY_PROFILE:
        if list(_policy_event_validator().iter_errors(dict(event))):
            raise SnapshotContractError("INVALID_PAYLOAD", event_id)
        if kind == "policy.issued":
            keys = {"billing_frequency", "premium_amount_cents", "currency", "product_variant", "initial_status"}
            _require_exact_keys(payload, keys, event_id)
            valid = payload["initial_status"] == "active"
        elif kind == "policy.status_changed":
            _require_exact_keys(payload, {"previous_status", "new_status", "reason"}, event_id)
            valid = all(isinstance(payload[key], str) and payload[key] for key in payload)
        else:
            return
    else:
        if kind == "policy.issued":
            _require_exact_keys(payload, {"billing_frequency", "premium_amount_cents", "currency", "product_type"}, event_id)
            valid = True
        elif kind == "payment.recorded":
            keys = {"arrears_days", "delay_days", "failed", "on_time", "recovered", "retry", "scheduled_opportunity_ordinal"}
            _require_exact_keys(payload, keys, event_id)
            valid = (
                _nonnegative_int(payload["arrears_days"])
                and (payload["delay_days"] is None or isinstance(payload["delay_days"], (int, float)) and not isinstance(payload["delay_days"], bool) and payload["delay_days"] >= 0)
                and all(payload[key] in (0, 1) and not isinstance(payload[key], bool) for key in ("failed", "on_time", "recovered", "retry"))
                and _nonnegative_int(payload["scheduled_opportunity_ordinal"])
            )
        elif kind == "event.corrected":
            _require_exact_keys(payload, {"target_event_id", "replacement_delay_days"}, event_id)
            valid = isinstance(payload["target_event_id"], str) and bool(payload["target_event_id"]) and isinstance(payload["replacement_delay_days"], (int, float)) and not isinstance(payload["replacement_delay_days"], bool) and payload["replacement_delay_days"] >= 0
        elif kind in {"notice.sent", "service.contact"}:
            _require_exact_keys(payload, {"category"}, event_id)
            categories = (
                {"billing_reminder", "grace_warning", "policy_update"}
                if kind == "notice.sent"
                else {"billing_question", "coverage_question", "service_request"}
            )
            valid = payload["category"] in categories
        else:
            _require_exact_keys(payload, {"cause"}, event_id)
            valid = payload["cause"] == kind.split(".", 1)[1]
    if kind == "policy.issued":
        valid = valid and payload.get("billing_frequency") in {"monthly", "quarterly", "semiannual", "annual"} and payload.get("currency") == "USD" and _positive_int(payload.get("premium_amount_cents")) and payload.get("product_variant", payload.get("product_type")) in {"fictional_term_life", "fictional_whole_life"}
    if not valid:
        raise SnapshotContractError("INVALID_PAYLOAD", event_id)


def _snapshot_id(data: Mapping[str, Any]) -> str:
    content = dict(data)
    content.pop("snapshot_id", None)
    return sha256(canonical_json_bytes(content)).hexdigest()


def reconstruct_domain_snapshot(
    history: Iterable[Mapping[str, Any]], *, policy_id: str, as_of: datetime | str,
    source_profile: str, catalog: SemanticCatalog,
) -> DomainSnapshot | None:
    """Reconstruct one immutable domain snapshot from cutoff-visible source facts."""

    cutoff = _parse_cutoff(as_of)
    try:
        catalog.require_source_profile(source_profile)
    except CatalogContractError as exc:
        raise SnapshotContractError("INCOMPATIBLE_CONTRACT") from exc
    if catalog.version != CATALOG_VERSION or catalog.snapshot_version != SNAPSHOT_VERSION:
        raise SnapshotContractError("INCOMPATIBLE_CONTRACT")
    selected = select_visible_events(
        history, policy_id=policy_id, as_of=cutoff, source_profile=source_profile
    )
    if not selected:
        return None
    seen: set[str] = set()
    for event in selected:
        event_id = str(event["event_id"])
        if event_id in seen:
            raise SnapshotContractError("DUPLICATE_EVENT", event_id)
        seen.add(event_id)
        _validate_payload(event, source_profile)
    issuances = [event for event in selected if event["event_type"] == "policy.issued"]
    if not issuances:
        raise SnapshotContractError("MISSING_ISSUANCE")
    if len(issuances) > 1:
        raise SnapshotContractError("MULTIPLE_ISSUANCE")
    issuance = issuances[0]
    issued_at = _parse_source_time(issuance["effective_at"], str(issuance["event_id"]))
    if any(_parse_source_time(event["effective_at"], str(event["event_id"])) < issued_at for event in selected):
        raise SnapshotContractError("BEFORE_ISSUANCE")

    status = "active" if source_profile == LEGACY_PROFILE else "unknown"
    status_evidence = (str(issuance["event_id"]),) if source_profile == LEGACY_PROFILE else ()
    grace_entered: datetime | None = None
    grace_evidence: tuple[str, ...] = status_evidence
    days_past_due: int | None = None
    arrears_evidence: tuple[str, ...] = ()
    payments: dict[str, Mapping[str, Any]] = {}
    status_instants: set[datetime] = set()
    terminal: tuple[str, str] | None = None

    for event in selected:
        kind = event["event_type"]
        event_id = str(event["event_id"])
        effective = _parse_source_time(event["effective_at"], event_id)
        payload = event["payload"]
        if event is issuance:
            continue
        if source_profile == LEGACY_PROFILE and kind == "policy.status_changed":
            if effective in status_instants:
                raise SnapshotContractError("AMBIGUOUS_STATUS", event_id)
            status_instants.add(effective)
            previous, new = payload["previous_status"], payload["new_status"]
            if previous != status or (previous, new) not in _TRANSITIONS:
                raise SnapshotContractError("INVALID_TRANSITION", event_id)
            status = new
            status_evidence = (event_id,)
            if new == "grace_period":
                grace_entered = effective
                grace_evidence = (event_id,)
            else:
                grace_entered = None
                grace_evidence = status_evidence
        elif source_profile == V6_PROFILE and kind in {"outcome.lapsed", "outcome.surrendered"}:
            new_status = kind.split(".", 1)[1]
            if terminal is not None:
                raise SnapshotContractError("AMBIGUOUS_STATUS", event_id)
            terminal = (new_status, event_id)
            status, status_evidence = new_status, (event_id,)
            grace_evidence = status_evidence
        elif source_profile == V6_PROFILE and kind == "payment.recorded":
            payments[event_id] = event
            days_past_due = int(payload["arrears_days"])
            arrears_evidence = (event_id,)
        elif source_profile == V6_PROFILE and kind == "event.corrected":
            target = payload["target_event_id"]
            if target not in payments:
                raise SnapshotContractError("INVALID_CORRECTION", event_id)

    issuance_payload = issuance["payload"]
    billing = str(issuance_payload["billing_frequency"])
    premium = int(issuance_payload["premium_amount_cents"])
    product = str(issuance_payload.get("product_variant", issuance_payload.get("product_type")))
    if status == "grace_period":
        assert grace_entered is not None
        in_grace, days_in_grace, grace_at = True, int((cutoff - grace_entered).total_seconds() // 86400), _timestamp(grace_entered)
    elif status == "unknown":
        in_grace, days_in_grace, grace_at = None, None, None
    else:
        in_grace, days_in_grace, grace_at = False, 0, None
    provenance = tuple(
        EventProvenance(str(event["event_id"]), sha256(canonical_json_bytes(event)).hexdigest())
        for event in selected
    )
    snapshot = DomainSnapshot(
        snapshot_version=SNAPSHOT_VERSION,
        catalog_version=catalog.version,
        catalog_sha256=catalog.sha256,
        source_profile=source_profile,
        snapshot_id="",
        policy_id=policy_id,
        as_of=_timestamp(cutoff),
        issued_at=_timestamp(issued_at),
        product_type=product,
        status=status,
        billing_frequency=billing,
        premium_amount_cents=premium,
        currency=str(issuance_payload["currency"]),
        annual_premium_cents=premium * int(catalog.data["billing_periods_per_year"][billing]),
        tenure_days=int((cutoff - issued_at).total_seconds() // 86400),
        in_grace_period=in_grace,
        days_in_grace=days_in_grace,
        grace_entered_at=grace_at,
        days_past_due=days_past_due,
        coverage_amount_cents=None,
        total_premiums_paid_cents=None,
        safety=SafetyFacts(),
        provenance=provenance,
        field_evidence=FieldEvidence(
            issuance=(str(issuance["event_id"]),),
            status=status_evidence,
            grace=grace_evidence,
            days_past_due=arrears_evidence,
        ),
    )
    return replace(snapshot, snapshot_id=_snapshot_id(snapshot.to_dict()))


def load_json_events(value: str) -> Any:
    """Parse JSON while rejecting duplicate object keys and nonfinite numbers."""

    def object_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise SnapshotContractError("INVALID_ENVELOPE")
            result[key] = item
        return result

    try:
        return json.loads(
            value,
            object_pairs_hook=object_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(SnapshotContractError("INVALID_ENVELOPE")),
        )
    except json.JSONDecodeError as exc:
        raise SnapshotContractError("INVALID_ENVELOPE") from exc
