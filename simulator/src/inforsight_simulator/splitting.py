"""Deterministic policy-aware temporal splits for observation records."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from typing import Any, Iterable

from .generator import GENERATOR_VERSION, SCHEMA_VERSION
from .leakage import validate_observation_records
from .observations import (
    LABEL_HORIZON_DAYS,
    LABEL_POLICY_VERSION,
    OBSERVATION_CONTRACT_VERSION,
    ObservationRecord,
)
from .validation import parse_utc_timestamp


TEMPORAL_SPLIT_CONTRACT_VERSION = "1.0.0"
MODELING_LABEL_STATUSES = frozenset({"observed_negative", "observed_positive"})
MODELING_DISPOSITIONS = ("train", "validation", "test")
ALL_DISPOSITIONS = (
    "train",
    "embargoed",
    "validation",
    "calendar_gap",
    "test",
    "excluded",
)


@dataclass(frozen=True)
class TemporalSplitSpecification:
    """Explicit half-open UTC boundaries for chronological assignment."""

    train_end: str
    validation_start: str
    validation_end: str
    test_start: str

    def parsed_boundaries(self) -> tuple[datetime, datetime, datetime, datetime]:
        """Return validated UTC boundaries in chronological order."""

        values = (
            parse_utc_timestamp(self.train_end, "train_end"),
            parse_utc_timestamp(self.validation_start, "validation_start"),
            parse_utc_timestamp(self.validation_end, "validation_end"),
            parse_utc_timestamp(self.test_start, "test_start"),
        )
        if not values[0] < values[1] < values[2] < values[3]:
            raise ValueError("temporal split boundaries must be strictly increasing")
        return values

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible description of the boundary contract."""

        return {
            "interval_semantics": "half_open",
            "train": {"as_of_before": self.train_end},
            "embargoed": {
                "as_of_at_or_after": self.train_end,
                "as_of_before": self.validation_start,
            },
            "validation": {
                "as_of_at_or_after": self.validation_start,
                "as_of_before": self.validation_end,
            },
            "calendar_gap": {
                "as_of_at_or_after": self.validation_end,
                "as_of_before": self.test_start,
            },
            "test": {"as_of_at_or_after": self.test_start},
        }


CANONICAL_TEMPORAL_SPLIT_SPECIFICATION = TemporalSplitSpecification(
    train_end="2024-04-01T00:00:00Z",
    validation_start="2024-07-01T00:00:00Z",
    validation_end="2024-10-01T00:00:00Z",
    test_start="2024-12-01T00:00:00Z",
)


@dataclass(frozen=True)
class TemporalSplitResult:
    """Every source observation assigned to exactly one disposition."""

    specification: TemporalSplitSpecification
    train: tuple[ObservationRecord, ...]
    embargoed: tuple[ObservationRecord, ...]
    validation: tuple[ObservationRecord, ...]
    calendar_gap: tuple[ObservationRecord, ...]
    test: tuple[ObservationRecord, ...]
    excluded: tuple[ObservationRecord, ...]

    def disposition_items(self) -> tuple[tuple[str, tuple[ObservationRecord, ...]], ...]:
        """Return dispositions in canonical serialization order."""

        return tuple((name, getattr(self, name)) for name in ALL_DISPOSITIONS)


def assign_temporal_splits(
    records: Iterable[ObservationRecord],
    specification: TemporalSplitSpecification = CANONICAL_TEMPORAL_SPLIT_SPECIFICATION,
) -> TemporalSplitResult:
    """Assign validated observations to deterministic chronological partitions."""

    materialized = sorted(
        records,
        key=lambda record: (record.as_of, record.policy_id, record.observation_id),
    )
    validate_observation_records(materialized)
    specification.parsed_boundaries()
    assigned: dict[str, list[ObservationRecord]] = {
        disposition: [] for disposition in ALL_DISPOSITIONS
    }

    for record in materialized:
        _validate_record_contract(record)
        disposition = _expected_disposition(record, specification)
        assigned[disposition].append(record)

    result = TemporalSplitResult(
        specification=specification,
        **{name: tuple(assigned[name]) for name in ALL_DISPOSITIONS},
    )
    validate_temporal_split(result, source_records=materialized)
    return result


def validate_temporal_split(
    result: TemporalSplitResult,
    *,
    source_records: Iterable[ObservationRecord] | None = None,
) -> None:
    """Fail closed on incomplete accounting, overlap, or temporal leakage."""

    result.specification.parsed_boundaries()
    all_assigned = [
        record
        for _, records in result.disposition_items()
        for record in records
    ]
    assigned_ids = [record.observation_id for record in all_assigned]
    if len(assigned_ids) != len(set(assigned_ids)):
        raise ValueError("an observation_id is assigned to multiple dispositions")

    if source_records is not None:
        source_ids = [record.observation_id for record in source_records]
        if Counter(assigned_ids) != Counter(source_ids):
            raise ValueError("split dispositions do not account for every source observation")

    for name, records in result.disposition_items():
        stable = tuple(
            sorted(
                records,
                key=lambda item: (item.as_of, item.policy_id, item.observation_id),
            )
        )
        if stable != records:
            raise ValueError(f"{name} records are not in deterministic order")
        for record in records:
            _validate_record_contract(record)
            expected = _expected_disposition(record, result.specification)
            if name != expected:
                raise ValueError(
                    f"observation {record.observation_id} belongs in {expected}, not {name}"
                )

    policy_owners: dict[str, str] = {}
    outcome_owners: dict[str, str] = {}
    for name in MODELING_DISPOSITIONS:
        for record in getattr(result, name):
            owner = policy_owners.setdefault(record.policy_id, name)
            if owner != name:
                raise ValueError(
                    f"policy_id appears in multiple modeling partitions: {record.policy_id}"
                )
            source_event_id = record.label.source_event_id
            if source_event_id is not None:
                outcome_owner = outcome_owners.setdefault(source_event_id, name)
                if outcome_owner != name:
                    raise ValueError(
                        "outcome episode appears in multiple modeling partitions: "
                        f"{source_event_id}"
                    )

    _require_nonempty_modeling_partitions(result)
    _require_chronology(result.train, result.validation, "train", "validation")
    _require_chronology(result.validation, result.test, "validation", "test")
    _require_horizon_embargo(result.train, result.validation, "train", "validation")
    _require_horizon_embargo(result.validation, result.test, "validation", "test")


def summarize_temporal_split(result: TemporalSplitResult) -> dict[str, Any]:
    """Return deterministic counts and ranges for a split result."""

    summaries: dict[str, Any] = {}
    for name, records in result.disposition_items():
        labels = Counter(str(record.label.value) for record in records)
        statuses = Counter(record.label.status for record in records)
        outcomes = Counter(
            record.label.outcome_type
            for record in records
            if record.label.outcome_type is not None
        )
        billing = Counter(
            record.features.billing_frequency
            for record in records
            if record.features is not None
        )
        summaries[name] = {
            "observation_count": len(records),
            "label_value_counts": dict(sorted(labels.items())),
            "label_status_counts": dict(sorted(statuses.items())),
            "outcome_type_counts": dict(sorted(outcomes.items())),
            "billing_frequency_counts": dict(sorted(billing.items())),
            "first_as_of": min((record.as_of for record in records), default=None),
            "last_as_of": max((record.as_of for record in records), default=None),
            "first_horizon_end": min(
                (record.horizon_end for record in records), default=None
            ),
            "last_horizon_end": max(
                (record.horizon_end for record in records), default=None
            ),
        }
    return summaries


def source_observation_digest(records: Iterable[ObservationRecord]) -> str:
    """Hash canonical identity and temporal fields without feature payloads."""

    material = [
        {
            "as_of": record.as_of,
            "horizon_end": record.horizon_end,
            "label_policy_version": record.label_policy_version,
            "label_source_event_id": record.label.source_event_id,
            "label_status": record.label.status,
            "label_value": record.label.value,
            "observation_contract_version": record.observation_contract_version,
            "observation_id": record.observation_id,
            "policy_id": record.policy_id,
        }
        for record in sorted(
            records,
            key=lambda item: (item.as_of, item.policy_id, item.observation_id),
        )
    ]
    encoded = json.dumps(
        material, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _is_modeling_eligible(record: ObservationRecord) -> bool:
    return (
        record.eligible
        and record.label.status in MODELING_LABEL_STATUSES
        and record.label.value in (0, 1)
    )


def _expected_disposition(
    record: ObservationRecord,
    specification: TemporalSplitSpecification,
) -> str:
    if not _is_modeling_eligible(record):
        return "excluded"
    train_end, validation_start, validation_end, test_start = (
        specification.parsed_boundaries()
    )
    cutoff = parse_utc_timestamp(record.as_of, "as_of")
    if cutoff < train_end:
        return "train"
    if cutoff < validation_start:
        return "embargoed"
    if cutoff < validation_end:
        return "validation"
    if cutoff < test_start:
        return "calendar_gap"
    return "test"


def _validate_record_contract(record: ObservationRecord) -> None:
    if record.observation_contract_version != OBSERVATION_CONTRACT_VERSION:
        raise ValueError(
            "unsupported observation contract version: "
            f"{record.observation_contract_version}"
        )
    if record.label_policy_version != LABEL_POLICY_VERSION:
        raise ValueError(
            f"unsupported label policy version: {record.label_policy_version}"
        )
    if record.generator_version != GENERATOR_VERSION:
        raise ValueError(f"unsupported generator version: {record.generator_version}")
    if record.event_schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported event schema version: {record.event_schema_version}"
        )
    cutoff = parse_utc_timestamp(record.as_of, "as_of")
    horizon_end = parse_utc_timestamp(record.horizon_end, "horizon_end")
    if (horizon_end - cutoff) != timedelta(days=LABEL_HORIZON_DAYS):
        raise ValueError("observation horizon must equal 90 elapsed days")


def _require_nonempty_modeling_partitions(result: TemporalSplitResult) -> None:
    for name in MODELING_DISPOSITIONS:
        records = getattr(result, name)
        if not records:
            raise ValueError(f"{name} partition must not be empty")
        if {record.label.value for record in records} != {0, 1}:
            raise ValueError(f"{name} partition must contain both label classes")


def _require_chronology(
    earlier: tuple[ObservationRecord, ...],
    later: tuple[ObservationRecord, ...],
    earlier_name: str,
    later_name: str,
) -> None:
    if max(record.as_of for record in earlier) >= min(record.as_of for record in later):
        raise ValueError(f"{earlier_name} observations must precede {later_name}")


def _require_horizon_embargo(
    earlier: tuple[ObservationRecord, ...],
    later: tuple[ObservationRecord, ...],
    earlier_name: str,
    later_name: str,
) -> None:
    latest_horizon = max(
        parse_utc_timestamp(record.horizon_end, "horizon_end") for record in earlier
    )
    earliest_cutoff = min(
        parse_utc_timestamp(record.as_of, "as_of") for record in later
    )
    if latest_horizon >= earliest_cutoff:
        raise ValueError(
            f"{earlier_name} label horizons overlap {later_name} observations"
        )
