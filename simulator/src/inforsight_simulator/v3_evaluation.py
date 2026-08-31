"""Governed R2-10 v3 evaluation memberships and feature registry."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from typing import Iterable

from .v3_config import V3_BILLING_FREQUENCIES, V3_CONTRACT_VERSION
from .v3_corpus import V3Features, V3Observation, validate_v3_feature_payload


V3_SPLIT_VERSION = V3_CONTRACT_VERSION
V3_FEATURE_DICTIONARY_VERSION = V3_CONTRACT_VERSION
V3_FEATURE_PIPELINE_VERSION = V3_CONTRACT_VERSION
V3_SCORING_AUTHORIZATION_VERSION = V3_CONTRACT_VERSION
V3_FINAL_HOLDOUT_STATUS = "not_materialized"
V3_STRUCTURAL_SUPPORT_VERSION = "1.0.0"

MIN_ELIGIBLE_OBSERVATIONS = 500
MIN_CLASS_OBSERVATIONS = 50
FOLDS = (
    ("fold_1", "2023-03-31T23:59:59Z", "2023-07-01T00:00:00Z", "2023-09-30T23:59:59Z"),
    ("fold_2", "2023-09-30T23:59:59Z", "2024-01-01T00:00:00Z", "2024-03-31T23:59:59Z"),
    ("fold_3", "2024-03-31T23:59:59Z", "2024-07-01T00:00:00Z", "2024-09-30T23:59:59Z"),
)
SELECTION_FOLD = (
    "selection", "2024-03-31T23:59:59Z", "2024-07-01T00:00:00Z", "2024-09-30T23:59:59Z",
)

FEATURE_GROUPS = {
    "static": ("tenure_days", "premium_amount_cents", "product_type", "billing_frequency"),
    "recent_payment": (
        "recent_delay_days", "recent_failed_payment_count", "recent_retry_count",
        "recent_recovery_count", "arrears_duration_days",
    ),
    "rolling_history": ("rolling_on_time_rate", "rolling_payment_count"),
    "service_notice": (
        "recent_notice_count", "notice_category", "recent_contact_count", "contact_category",
    ),
    "missingness": ("payment_attribute_missing", "contact_attribute_missing"),
}


@dataclass(frozen=True)
class V3TemporalFold:
    name: str
    fit: tuple[V3Observation, ...]
    evaluation: tuple[V3Observation, ...]
    fit_through: str
    evaluation_start: str
    evaluation_end: str


def validate_feature_registry() -> None:
    """Prove that every public v3 feature has exactly one governed group."""

    registered = [name for names in FEATURE_GROUPS.values() for name in names]
    expected = set(V3Features.__dataclass_fields__)
    if len(registered) != len(set(registered)):
        raise ValueError("v3 feature registry assigns a feature more than once")
    if set(registered) != expected:
        missing = sorted(expected - set(registered))
        extra = sorted(set(registered) - expected)
        raise ValueError(f"v3 feature registry mismatch; missing={missing}, extra={extra}")


def structural_support_report(observations: Iterable[V3Observation]) -> dict[str, object]:
    """Summarize frozen memberships without fitting, transforming, or scoring."""

    rows = _normalized(observations)
    if not rows:
        raise ValueError("v3 observations are empty")
    artifact_ids = {row.artifact_id for row in rows}
    if len(artifact_ids) != 1:
        raise ValueError("v3 structural evidence requires one artifact identity")
    validate_feature_registry()
    memberships = []
    for specification, evaluation_role in (
        *((specification, "acceptance") for specification in FOLDS),
        (SELECTION_FOLD, "selection"),
    ):
        name, fit_end, evaluation_start, evaluation_end = specification
        fit_window = _window(rows, "fit", None, fit_end)
        evaluation_window = _window(rows, evaluation_role, evaluation_start, evaluation_end)
        fit = _observed(fit_window)
        evaluation = _observed(evaluation_window)
        support_failures = [
            *_support_failures(fit, "fit"),
            *_support_failures(evaluation, evaluation_role),
        ]
        latest_fit_cutoff = max(_time(row.as_of) for row in fit)
        latest_fit_horizon = max(_time(row.horizon_end) for row in fit)
        earliest_evaluation = min(_time(row.as_of) for row in evaluation)
        chronology_passed = latest_fit_cutoff < earliest_evaluation
        embargo_passed = latest_fit_horizon < earliest_evaluation
        policy_overlap = len({row.policy_id for row in fit} & {row.policy_id for row in evaluation})
        episode_overlap = len(
            {row.outcome_episode_id for row in fit}
            & {row.outcome_episode_id for row in evaluation}
        )
        if not chronology_passed:
            support_failures.append("feature cutoff chronology is invalid")
        if not embargo_passed:
            support_failures.append("fit outcome horizon crosses the evaluation boundary")
        if policy_overlap:
            support_failures.append("policy identity overlaps governed roles")
        if episode_overlap:
            support_failures.append("outcome episode overlaps governed roles")
        memberships.append({
            "name": name,
            "fit_through": fit_end,
            "evaluation_role": evaluation_role,
            "evaluation_start": evaluation_start,
            "evaluation_end": evaluation_end,
            "fit": _membership_summary(fit_window, fit),
            "evaluation": _membership_summary(evaluation_window, evaluation),
            "boundaries": {
                "latest_fit_cutoff": _timestamp(latest_fit_cutoff),
                "latest_fit_horizon": _timestamp(latest_fit_horizon),
                "earliest_evaluation_cutoff": _timestamp(earliest_evaluation),
                "strict_cutoff_chronology": chronology_passed,
                "full_90_day_embargo": embargo_passed,
                "policy_overlap": policy_overlap,
                "outcome_episode_overlap": episode_overlap,
            },
            "support_status": "pass" if not support_failures else "fail",
            "support_failures": support_failures,
        })
    return {
        "artifact_version": V3_STRUCTURAL_SUPPORT_VERSION,
        "split_contract_version": V3_SPLIT_VERSION,
        "phase": "R2-10",
        "artifact_id": next(iter(artifact_ids)),
        "minimums": {
            "eligible_observations": MIN_ELIGIBLE_OBSERVATIONS,
            "observations_per_class": MIN_CLASS_OBSERVATIONS,
            "required_billing_frequencies": list(V3_BILLING_FREQUENCIES),
        },
        "memberships": memberships,
        "overall_status": "pass" if all(
            membership["support_status"] == "pass" for membership in memberships
        ) else "fail",
        "claim_boundary": "structural_support_only_no_modeling_or_metrics",
        "final_holdout_status": V3_FINAL_HOLDOUT_STATUS,
    }


def build_temporal_folds(observations: Iterable[V3Observation]) -> tuple[V3TemporalFold, ...]:
    rows = _normalized(observations)
    if not rows:
        raise ValueError("v3 observations are empty")
    folds = tuple(_build_fold(rows, specification, "acceptance") for specification in FOLDS)
    return folds


def build_selection_fold(observations: Iterable[V3Observation]) -> V3TemporalFold:
    rows = _normalized(observations)
    if not rows:
        raise ValueError("v3 observations are empty")
    return _build_fold(rows, SELECTION_FOLD, "selection")


def validate_temporal_fold(fold: V3TemporalFold, *, evaluate_support: bool = True) -> None:
    if not fold.fit or not fold.evaluation:
        raise ValueError(f"{fold.name} has an empty governed membership")
    if tuple(sorted(fold.fit, key=_row_key)) != fold.fit or tuple(
        sorted(fold.evaluation, key=_row_key)
    ) != fold.evaluation:
        raise ValueError("governed membership is not canonically ordered")
    if any(row.role != "fit" for row in fold.fit):
        raise ValueError("fit membership contains a non-fit policy role")
    expected_role = "selection" if fold.name == "selection" else "acceptance"
    if any(row.role != expected_role for row in fold.evaluation):
        raise ValueError("evaluation membership contains the wrong policy role")
    if {row.policy_id for row in fold.fit} & {row.policy_id for row in fold.evaluation}:
        raise ValueError("policy identity overlaps governed roles")
    if {row.outcome_episode_id for row in fold.fit} & {
        row.outcome_episode_id for row in fold.evaluation
    }:
        raise ValueError("outcome episode overlaps governed roles")
    earliest_evaluation = min(_time(row.as_of) for row in fold.evaluation)
    if max(_time(row.as_of) for row in fold.fit) >= earliest_evaluation:
        raise ValueError("feature cutoff chronology is invalid")
    if max(_time(row.horizon_end) for row in fold.fit) >= earliest_evaluation:
        raise ValueError("fit outcome horizon crosses the evaluation boundary")
    for row in (*fold.fit, *fold.evaluation):
        if row.observation_contract_version != V3_CONTRACT_VERSION:
            raise ValueError("governed membership contains a non-v3 observation")
        validate_v3_feature_payload(row.to_dict()["features"])
    if evaluate_support:
        _validate_support(fold.fit, "fit")
        _validate_support(fold.evaluation, expected_role)


def _build_fold(
    rows: tuple[V3Observation, ...], specification: tuple[str, str, str, str], role: str,
) -> V3TemporalFold:
    name, fit_end, evaluation_start, evaluation_end = specification
    fold = V3TemporalFold(
        name=name,
        fit=_eligible(rows, "fit", None, fit_end),
        evaluation=_eligible(rows, role, evaluation_start, evaluation_end),
        fit_through=fit_end,
        evaluation_start=evaluation_start,
        evaluation_end=evaluation_end,
    )
    validate_temporal_fold(fold)
    return fold


def _eligible(
    rows: tuple[V3Observation, ...], role: str, start: str | None, end: str,
) -> tuple[V3Observation, ...]:
    return tuple(
        row for row in rows
        if row.role == role
        and row.label_status in {"observed_positive", "observed_negative"}
        and row.label_value in {0, 1}
        and (start is None or _time(row.as_of) >= _time(start))
        and _time(row.as_of) <= _time(end)
    )


def _window(
    rows: tuple[V3Observation, ...], role: str, start: str | None, end: str,
) -> tuple[V3Observation, ...]:
    return tuple(
        row for row in rows
        if row.role == role
        and (start is None or _time(row.as_of) >= _time(start))
        and _time(row.as_of) <= _time(end)
    )


def _observed(rows: tuple[V3Observation, ...]) -> tuple[V3Observation, ...]:
    return tuple(
        row for row in rows
        if row.label_status in {"observed_positive", "observed_negative"}
        and row.label_value in {0, 1}
    )


def _validate_support(rows: tuple[V3Observation, ...], role: str) -> None:
    failures = _support_failures(rows, role)
    if failures:
        raise ValueError(failures[0])


def _support_failures(rows: tuple[V3Observation, ...], role: str) -> list[str]:
    failures = []
    if len(rows) < MIN_ELIGIBLE_OBSERVATIONS:
        failures.append(
            f"{role} membership has fewer than {MIN_ELIGIBLE_OBSERVATIONS} eligible observations"
        )
    labels = [row.label_value for row in rows]
    for value in (0, 1):
        if labels.count(value) < MIN_CLASS_OBSERVATIONS:
            failures.append(
                f"{role} membership has fewer than {MIN_CLASS_OBSERVATIONS} rows for class {value}"
            )
    frequencies = {row.features.billing_frequency for row in rows}
    if frequencies != set(V3_BILLING_FREQUENCIES):
        failures.append(f"{role} membership lacks a supported billing frequency")
    return failures


def _membership_summary(
    window: tuple[V3Observation, ...], eligible: tuple[V3Observation, ...],
) -> dict[str, object]:
    label_status = Counter(row.label_status for row in window)
    labels = Counter(row.label_value for row in eligible)
    frequencies = Counter(row.features.billing_frequency for row in eligible)
    censored = sum(row.label_status not in {"observed_positive", "observed_negative"} for row in window)
    return {
        "window_observations": len(window),
        "eligible_uncensored_observations": len(eligible),
        "right_censored_observations": censored,
        "right_censoring_fraction": censored / len(window) if window else 0.0,
        "positive": labels[1],
        "negative": labels[0],
        "unique_policies": len({row.policy_id for row in eligible}),
        "billing_frequency": dict(sorted(frequencies.items())),
        "label_status": dict(sorted(label_status.items())),
        "earliest_cutoff": min(row.as_of for row in eligible),
        "latest_cutoff": max(row.as_of for row in eligible),
        "membership_sha256": sha256(
            ("\n".join(row.observation_id for row in eligible) + "\n").encode("utf-8")
        ).hexdigest(),
    }


def _normalized(observations: Iterable[V3Observation]) -> tuple[V3Observation, ...]:
    rows = tuple(sorted(observations, key=_row_key))
    ids = [row.observation_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate v3 observation identity")
    return rows


def _row_key(row: V3Observation) -> tuple[str, str, str]:
    return row.as_of, row.policy_id, row.observation_id


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("v3 evaluation timestamps must be UTC")
    return parsed


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
