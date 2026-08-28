"""Leakage-safe observation records for the fictional policy simulator."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
from typing import Any, Iterable

from .generator import (
    GENERATOR_VERSION,
    LEGACY_GENERATOR_VERSION,
    NAMESPACED_GENERATOR_VERSION,
    SCHEMA_VERSION,
)
from .leakage import validate_feature_payload, validate_observation_records
from .validation import PreparedEvent, parse_utc_timestamp, prepare_and_validate_history


OBSERVATION_CONTRACT_VERSION = "1.0.0"
LABEL_POLICY_VERSION = "1.0.0"
LABEL_HORIZON_DAYS = 90
ELIGIBLE_STATUSES = frozenset({"active"})
OUTCOME_TYPES = frozenset({"outcome.lapsed", "outcome.surrendered"})
LABEL_STATUSES = frozenset(
    {"observed_positive", "observed_negative", "right_censored", "not_applicable"}
)
CENSORING_REASONS = frozenset(
    {"follow_up_ends_before_horizon", "outcome_not_ingested_by_watermark"}
)
SUPPORTED_CURRENCIES = frozenset({"USD"})
SUPPORTED_GENERATOR_VERSIONS = frozenset(
    {LEGACY_GENERATOR_VERSION, NAMESPACED_GENERATOR_VERSION}
)
INELIGIBILITY_REASONS = frozenset(
    {
        "policy_not_visible",
        "status_grace_period_not_eligible",
        "status_lapsed_not_eligible",
        "status_surrendered_not_eligible",
    }
)
_POLICY_ID_PATTERN = re.compile(r"^pol_[a-z0-9]{12,64}$")
_EVENT_ID_PATTERN = re.compile(r"^evt_[a-z0-9]{12,64}$")
_OBSERVATION_ID_PATTERN = re.compile(r"^obs_[0-9a-f]{24}$")
PolicyEvent = dict[str, Any]


@dataclass(frozen=True)
class ObservationFeatures:
    """Small versioned baseline feature surface visible at ``as_of``."""

    current_status: str
    product_variant: str
    billing_frequency: str
    premium_amount_cents: int
    currency: str
    policy_age_days: int
    visible_event_count: int
    visible_billing_count: int
    visible_failed_payment_count: int
    visible_received_payment_count: int
    visible_notice_count: int
    visible_service_contact_count: int

    def __post_init__(self) -> None:
        if self.current_status != "active":
            raise ValueError("observation features current_status must be active")
        for field in ("product_variant", "billing_frequency"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value:
                raise ValueError(f"observation features {field} must be non-empty")
        if self.currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"unsupported observation currency {self.currency!r}")
        count_fields = (
            "premium_amount_cents",
            "policy_age_days",
            "visible_event_count",
            "visible_billing_count",
            "visible_failed_payment_count",
            "visible_received_payment_count",
            "visible_notice_count",
            "visible_service_contact_count",
        )
        for field in count_fields:
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"observation features {field} must be a nonnegative integer")
        if self.visible_event_count < 1:
            raise ValueError("observation features visible_event_count must be positive")


@dataclass(frozen=True)
class OutcomeLabel:
    """Outcome metadata kept separate from the feature surface."""

    status: str
    value: int | None
    outcome_type: str | None
    source_event_id: str | None
    source_effective_at: str | None
    source_ingested_at: str | None
    censoring_reason: str | None

    def __post_init__(self) -> None:
        if self.status not in LABEL_STATUSES:
            raise ValueError(f"unsupported outcome label status {self.status!r}")
        outcome_fields = (
            self.outcome_type,
            self.source_event_id,
            self.source_effective_at,
            self.source_ingested_at,
        )
        if self.status == "observed_positive":
            if self.value != 1 or isinstance(self.value, bool):
                raise ValueError("observed_positive label value must be 1")
            if self.outcome_type not in OUTCOME_TYPES:
                raise ValueError("observed_positive label requires a supported outcome_type")
            if not isinstance(self.source_event_id, str) or not _EVENT_ID_PATTERN.fullmatch(
                self.source_event_id
            ):
                raise ValueError("observed_positive label requires a valid source_event_id")
            _canonical_timestamp(self.source_effective_at, "source_effective_at")
            _canonical_timestamp(self.source_ingested_at, "source_ingested_at")
            if self.censoring_reason is not None:
                raise ValueError("observed_positive label cannot have a censoring_reason")
            return
        if any(value is not None for value in outcome_fields):
            raise ValueError(f"{self.status} label cannot carry outcome provenance")
        if self.status == "observed_negative":
            if self.value != 0 or isinstance(self.value, bool):
                raise ValueError("observed_negative label value must be 0")
            if self.censoring_reason is not None:
                raise ValueError("observed_negative label cannot have a censoring_reason")
        elif self.status == "right_censored":
            if self.value is not None:
                raise ValueError("right_censored label value must be null")
            if self.censoring_reason not in CENSORING_REASONS:
                raise ValueError("right_censored label requires a supported censoring_reason")
        else:
            if self.value is not None or self.censoring_reason is not None:
                raise ValueError("not_applicable label value and censoring_reason must be null")


@dataclass(frozen=True)
class ObservationRecord:
    """One policy at one UTC cutoff with an auditable 90-day label."""

    observation_contract_version: str
    label_policy_version: str
    observation_id: str
    policy_id: str
    as_of: str
    horizon_start: str
    horizon_end: str
    follow_up_through: str
    eligible: bool
    eligibility_reason: str
    features: ObservationFeatures | None
    label: OutcomeLabel
    visible_event_ids: tuple[str, ...]
    generator_version: str
    event_schema_version: str

    def __post_init__(self) -> None:
        _validate_observation_record(self)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible nested representation."""

        result = asdict(self)
        result["visible_event_ids"] = list(self.visible_event_ids)
        return result


def _validate_observation_record(record: ObservationRecord) -> None:
    if record.observation_contract_version != OBSERVATION_CONTRACT_VERSION:
        raise ValueError("unsupported observation_contract_version")
    if record.label_policy_version != LABEL_POLICY_VERSION:
        raise ValueError("unsupported label_policy_version")
    if record.generator_version not in SUPPORTED_GENERATOR_VERSIONS:
        raise ValueError("unsupported generator_version")
    if record.event_schema_version != SCHEMA_VERSION:
        raise ValueError("unsupported event_schema_version")
    if not isinstance(record.observation_id, str) or not _OBSERVATION_ID_PATTERN.fullmatch(
        record.observation_id
    ):
        raise ValueError("observation_id does not satisfy the observation contract")
    if not isinstance(record.policy_id, str) or not _POLICY_ID_PATTERN.fullmatch(
        record.policy_id
    ):
        raise ValueError("policy_id does not satisfy the policy-event contract")
    if not isinstance(record.eligible, bool):
        raise ValueError("eligible must be a Boolean")
    if record.features is not None and not isinstance(record.features, ObservationFeatures):
        raise ValueError("features must be ObservationFeatures or null")
    if not isinstance(record.label, OutcomeLabel):
        raise ValueError("label must be an OutcomeLabel")
    if not isinstance(record.visible_event_ids, tuple):
        raise ValueError("visible_event_ids must be a tuple")
    if len(record.visible_event_ids) != len(set(record.visible_event_ids)):
        raise ValueError("visible_event_ids must be unique")
    if any(
        not isinstance(value, str) or not _EVENT_ID_PATTERN.fullmatch(value)
        for value in record.visible_event_ids
    ):
        raise ValueError("visible_event_ids contains an invalid event identifier")

    cutoff = _canonical_timestamp(record.as_of, "as_of")
    horizon_start = _canonical_timestamp(record.horizon_start, "horizon_start")
    horizon_end = _canonical_timestamp(record.horizon_end, "horizon_end")
    watermark = _canonical_timestamp(record.follow_up_through, "follow_up_through")
    if horizon_start != cutoff:
        raise ValueError("horizon_start must equal as_of")
    if horizon_end != cutoff + timedelta(days=LABEL_HORIZON_DAYS):
        raise ValueError("horizon_end must equal as_of plus the label horizon")
    if watermark < cutoff:
        raise ValueError("follow_up_through must be at or after as_of")

    if record.eligible:
        if record.eligibility_reason != "eligible_active":
            raise ValueError("eligible observation requires eligibility_reason eligible_active")
        if record.features is None:
            raise ValueError("eligible observation requires features")
        if record.label.status == "not_applicable":
            raise ValueError("eligible observation cannot have a not_applicable label")
    else:
        if record.eligibility_reason not in INELIGIBILITY_REASONS:
            raise ValueError("ineligible observation requires a supported eligibility_reason")
        if record.features is not None:
            raise ValueError("ineligible observation cannot have features")
        if record.label.status != "not_applicable":
            raise ValueError("ineligible observation requires a not_applicable label")

    if record.features is not None and (
        record.features.visible_event_count != len(record.visible_event_ids)
    ):
        raise ValueError("visible_event_count must match visible_event_ids")
    if record.label.status == "observed_positive":
        source_effective = _canonical_timestamp(
            record.label.source_effective_at, "source_effective_at"
        )
        source_ingested = _canonical_timestamp(
            record.label.source_ingested_at, "source_ingested_at"
        )
        if not cutoff < source_effective <= horizon_end:
            raise ValueError("positive outcome must be effective inside the label horizon")
        if source_ingested > watermark:
            raise ValueError("positive outcome must be ingested by follow_up_through")
    elif record.label.status == "observed_negative" and watermark < horizon_end:
        raise ValueError("observed_negative requires follow-up through the horizon")
    elif record.label.status == "right_censored":
        if (
            record.label.censoring_reason == "follow_up_ends_before_horizon"
            and watermark >= horizon_end
        ):
            raise ValueError("follow_up_ends_before_horizon requires an early watermark")


def _canonical_timestamp(value: object, field: str) -> datetime:
    parsed = parse_utc_timestamp(value, field)
    if _timestamp(parsed) != value:
        raise ValueError(f"{field} must use canonical seconds-level UTC representation")
    return parsed


def first_billing_observation_time(history: list[PolicyEvent]) -> datetime:
    """Return the ingestion time of the first effective billing-due event."""

    prepared = prepare_and_validate_history(history)
    billings = [
        item for item in prepared if item.event["event_type"] == "billing.premium_due"
    ]
    if not billings:
        raise ValueError("history has no billing.premium_due event")
    first = min(
        billings,
        key=lambda item: (
            item.effective_at,
            item.ingested_at,
            item.event["event_id"],
        ),
    )
    return first.ingested_at


def build_observation(
    history: list[PolicyEvent],
    as_of: datetime | str,
    *,
    follow_up_through: datetime | str,
) -> ObservationRecord:
    """Build one deterministic observation from a validated policy history.

    Feature visibility is inclusive and requires both ``effective_at`` and
    ``ingested_at`` to be at or before ``as_of``. The label horizon is
    ``(as_of, as_of + 90 days]``. A no-outcome label is emitted only when the
    explicit evaluation watermark covers the complete horizon.
    """

    cutoff = _parse_cutoff(as_of, "as_of")
    watermark = _parse_cutoff(follow_up_through, "follow_up_through")
    if watermark < cutoff:
        raise ValueError("follow_up_through must be at or after as_of")

    prepared = prepare_and_validate_history(history)
    policy_id = prepared[0].event["policy_id"]
    visible = [
        item
        for item in prepared
        if item.effective_at <= cutoff and item.ingested_at <= cutoff
    ]
    state = _visible_state(visible)
    eligible = state is not None and state["status"] in ELIGIBLE_STATUSES
    eligibility_reason = (
        "eligible_active"
        if eligible
        else "policy_not_visible"
        if state is None
        else f"status_{state['status']}_not_eligible"
    )

    horizon_end = cutoff + timedelta(days=LABEL_HORIZON_DAYS)
    label = _build_label(prepared, cutoff, horizon_end, watermark, eligible)
    features = _build_features(visible, state, cutoff) if eligible else None
    if features is not None:
        validate_feature_payload(features)

    return ObservationRecord(
        observation_contract_version=OBSERVATION_CONTRACT_VERSION,
        label_policy_version=LABEL_POLICY_VERSION,
        observation_id=_observation_id(policy_id, cutoff),
        policy_id=policy_id,
        as_of=_timestamp(cutoff),
        horizon_start=_timestamp(cutoff),
        horizon_end=_timestamp(horizon_end),
        follow_up_through=_timestamp(watermark),
        eligible=eligible,
        eligibility_reason=eligibility_reason,
        features=features,
        label=label,
        visible_event_ids=tuple(item.event["event_id"] for item in visible),
        generator_version=GENERATOR_VERSION,
        event_schema_version=SCHEMA_VERSION,
    )


def build_first_billing_observations(
    histories: Iterable[list[PolicyEvent]],
    *,
    follow_up_through: datetime | str,
) -> list[ObservationRecord]:
    """Build one first-billing observation per policy in stable order."""

    records = [
        build_observation(
            history,
            first_billing_observation_time(history),
            follow_up_through=follow_up_through,
        )
        for history in histories
    ]
    records.sort(key=lambda record: (record.as_of, record.policy_id))
    validate_observation_records(records)
    return records


def summarize_observations(records: Iterable[ObservationRecord]) -> dict[str, Any]:
    """Return deterministic sufficiency counts for a collection of records."""

    materialized = list(records)
    statuses = Counter(record.label.status for record in materialized)
    outcomes = Counter(
        record.label.outcome_type
        for record in materialized
        if record.label.outcome_type is not None
    )
    eligible = [record for record in materialized if record.eligible]
    return {
        "observation_count": len(materialized),
        "eligible_observation_count": len(eligible),
        "ineligible_observation_count": len(materialized) - len(eligible),
        "label_status_counts": dict(sorted(statuses.items())),
        "outcome_type_counts": dict(sorted(outcomes.items())),
        "unique_policy_count": len({record.policy_id for record in materialized}),
    }


def _visible_state(items: list[PreparedEvent]) -> dict[str, Any] | None:
    state: dict[str, Any] | None = None
    for item in items:
        event = item.event
        payload = event["payload"]
        if event["event_type"] == "policy.issued":
            state = {
                "status": payload["initial_status"],
                "product_variant": payload["product_variant"],
                "billing_frequency": payload["billing_frequency"],
                "premium_amount_cents": payload["premium_amount_cents"],
                "currency": payload["currency"],
                "issued_at": item.effective_at,
            }
        elif event["event_type"] == "policy.status_changed" and state is not None:
            state["status"] = payload["new_status"]
    return state


def _build_features(
    visible: list[PreparedEvent],
    state: dict[str, Any] | None,
    cutoff: datetime,
) -> ObservationFeatures:
    assert state is not None
    counts = Counter(item.event["event_type"] for item in visible)
    return ObservationFeatures(
        current_status=state["status"],
        product_variant=state["product_variant"],
        billing_frequency=state["billing_frequency"],
        premium_amount_cents=state["premium_amount_cents"],
        currency=state["currency"],
        policy_age_days=(cutoff - state["issued_at"]).days,
        visible_event_count=len(visible),
        visible_billing_count=counts["billing.premium_due"],
        visible_failed_payment_count=counts["payment.failed"],
        visible_received_payment_count=counts["payment.received"],
        visible_notice_count=counts["notice.sent"],
        visible_service_contact_count=counts["service.contact_recorded"],
    )


def _build_label(
    prepared: list[PreparedEvent],
    cutoff: datetime,
    horizon_end: datetime,
    watermark: datetime,
    eligible: bool,
) -> OutcomeLabel:
    if not eligible:
        return OutcomeLabel("not_applicable", None, None, None, None, None, None)

    horizon_outcomes = [
        item
        for item in prepared
        if item.event["event_type"] in OUTCOME_TYPES
        and cutoff < item.effective_at <= horizon_end
    ]
    if len(horizon_outcomes) > 1:
        raise ValueError("observation horizon contains duplicate outcome episodes")
    if horizon_outcomes and horizon_outcomes[0].ingested_at <= watermark:
        outcome = horizon_outcomes[0]
        return OutcomeLabel(
            status="observed_positive",
            value=1,
            outcome_type=outcome.event["event_type"],
            source_event_id=outcome.event["event_id"],
            source_effective_at=_timestamp(outcome.effective_at),
            source_ingested_at=_timestamp(outcome.ingested_at),
            censoring_reason=None,
        )
    if horizon_outcomes:
        return OutcomeLabel(
            status="right_censored",
            value=None,
            outcome_type=None,
            source_event_id=None,
            source_effective_at=None,
            source_ingested_at=None,
            censoring_reason="outcome_not_ingested_by_watermark",
        )
    if watermark < horizon_end:
        return OutcomeLabel(
            status="right_censored",
            value=None,
            outcome_type=None,
            source_event_id=None,
            source_effective_at=None,
            source_ingested_at=None,
            censoring_reason="follow_up_ends_before_horizon",
        )
    return OutcomeLabel("observed_negative", 0, None, None, None, None, None)


def _observation_id(policy_id: str, cutoff: datetime) -> str:
    material = (
        f"{OBSERVATION_CONTRACT_VERSION}|{policy_id}|{_timestamp(cutoff)}"
    ).encode("utf-8")
    return "obs_" + sha256(material).hexdigest()[:24]


def _parse_cutoff(value: datetime | str, field: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field} must be timezone-aware and use UTC")
        if value.utcoffset() != timezone.utc.utcoffset(None):
            raise ValueError(f"{field} must use UTC")
        return value.astimezone(timezone.utc)
    return parse_utc_timestamp(value, field)


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")
