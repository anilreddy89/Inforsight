"""Fail-closed leakage guards for model-visible observation features."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
import re
from typing import Any


FEATURE_GUARD_VERSION = "1.0.0"

ALLOWED_FEATURE_KEYS = frozenset(
    {
        "current_status",
        "product_variant",
        "billing_frequency",
        "premium_amount_cents",
        "currency",
        "policy_age_days",
        "visible_event_count",
        "visible_billing_count",
        "visible_failed_payment_count",
        "visible_received_payment_count",
        "visible_notice_count",
        "visible_service_contact_count",
    }
)

PROHIBITED_FEATURE_CONCEPTS = frozenset(
    {
        "censoring_reason",
        "event_id",
        "final_status",
        "follow_up_through",
        "generator_branch",
        "generator_order",
        "generator_seed",
        "horizon_end",
        "horizon_start",
        "label",
        "label_policy_version",
        "label_source",
        "label_status",
        "label_value",
        "observation_id",
        "outcome",
        "outcome_event_id",
        "outcome_type",
        "policy_id",
        "scenario",
        "scenario_assignment",
        "scenario_id",
        "seed",
        "source_effective_at",
        "source_event_id",
        "source_ingested_at",
        "terminal_outcome",
        "terminal_status",
        "visible_event_ids",
    }
)

PROHIBITED_CATEGORICAL_VALUES = frozenset(
    {
        "active_after_payment",
        "active_after_service_contact",
        "lapsed",
        "outcome_lapsed",
        "outcome_surrendered",
        "surrendered",
    }
)


def normalize_feature_name(value: str) -> str:
    """Normalize casing and separators before applying guard rules."""

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9]+", "_", separated.lower()).strip("_")


def validate_feature_payload(payload: Any) -> None:
    """Reject content outside the versioned model-visible feature boundary.

    The current observation contract has a flat, explicit allowlist. Recursive
    traversal is intentional so nested leakage cannot be hidden behind a benign
    container name if a future caller validates a serialized or transformed
    payload.
    """

    if is_dataclass(payload) and not isinstance(payload, type):
        payload = asdict(payload)
    if not isinstance(payload, Mapping):
        raise ValueError("feature payload must be a mapping")
    _validate_node(payload, path="features", root=True)


def validate_observation_records(records: Iterable[Any]) -> None:
    """Validate feature separation and uniqueness across observations."""

    seen_observations: set[str] = set()
    seen_policy_cutoffs: set[tuple[str, str]] = set()
    seen_outcomes: set[str] = set()

    for index, record in enumerate(records):
        observation_id = _field(record, "observation_id")
        policy_id = _field(record, "policy_id")
        as_of = _field(record, "as_of")
        features = _field(record, "features")
        label = _field(record, "label")

        if observation_id in seen_observations:
            raise ValueError(f"duplicate observation_id at records[{index}]: {observation_id}")
        seen_observations.add(observation_id)

        policy_cutoff = (policy_id, as_of)
        if policy_cutoff in seen_policy_cutoffs:
            raise ValueError(
                "duplicate policy/as_of observation at "
                f"records[{index}]: {policy_id}|{as_of}"
            )
        seen_policy_cutoffs.add(policy_cutoff)

        if features is not None:
            validate_feature_payload(features)

        source_event_id = _field(label, "source_event_id")
        if source_event_id is not None:
            if source_event_id in seen_outcomes:
                raise ValueError(
                    "duplicate outcome episode at "
                    f"records[{index}]: {source_event_id}"
                )
            seen_outcomes.add(source_event_id)


def find_exact_deterministic_proxies(
    feature_rows: Iterable[Mapping[str, Any]],
    targets: Iterable[Any],
) -> tuple[str, ...]:
    """Report fields whose values map exactly to one target in the supplied data.

    This is a review diagnostic, not an automatic exclusion rule. Direct
    simulator construction metadata is rejected by ``validate_feature_payload``;
    observable fields reported here need an explicit allow/exclude decision.
    """

    rows = list(feature_rows)
    target_values = list(targets)
    if not rows or len(rows) != len(target_values):
        raise ValueError("feature rows and targets must be non-empty and equal length")
    keys = set(rows[0])
    if any(set(row) != keys for row in rows):
        raise ValueError("feature rows must have identical keys")
    if len(set(target_values)) < 2:
        raise ValueError("proxy diagnostic requires at least two target classes")

    proxies: list[str] = []
    for key in sorted(keys):
        mapping: dict[Any, set[Any]] = defaultdict(set)
        try:
            for row, target in zip(rows, target_values, strict=True):
                mapping[row[key]].add(target)
        except TypeError as exc:
            raise ValueError(f"feature {key!r} contains an unhashable value") from exc
        if len(mapping) > 1 and all(len(values) == 1 for values in mapping.values()):
            proxies.append(key)
    return tuple(proxies)


def _validate_node(value: Any, *, path: str, root: bool = False) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if not isinstance(raw_key, str):
                raise ValueError(f"feature key at {path} must be a string")
            key = normalize_feature_name(raw_key)
            child_path = f"{path}.{raw_key}"
            if key in PROHIBITED_FEATURE_CONCEPTS:
                raise ValueError(f"feature payload contains prohibited path: {child_path}")
            if root and key not in ALLOWED_FEATURE_KEYS:
                raise ValueError(f"feature payload contains unapproved path: {child_path}")
            _validate_node(child, path=child_path)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _validate_node(child, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        normalized = normalize_feature_name(value)
        if normalized in PROHIBITED_CATEGORICAL_VALUES:
            raise ValueError(f"feature payload contains prohibited value at {path}: {value}")


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        if name not in value:
            raise ValueError(f"observation is missing required field: {name}")
        return value[name]
    try:
        return getattr(value, name)
    except AttributeError as exc:
        raise ValueError(f"observation is missing required field: {name}") from exc
