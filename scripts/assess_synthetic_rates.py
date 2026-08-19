#!/usr/bin/env python3
"""Build or verify Inforsight's deterministic synthetic-rate assessment."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SIMULATOR_SRC = REPOSITORY_ROOT / "simulator" / "src"
sys.path.insert(0, str(SIMULATOR_SRC))

from inforsight_simulator import (  # noqa: E402
    GeneratorConfig,
    generate_policy_histories,
    generation_provenance,
    validate_policy_history,
)


ASSESSMENT_ID = "inforsight-phase-01-07-synthetic-rate-assessment"
ASSESSMENT_VERSION = "0.1.0"
METRIC_DEFINITION_VERSION = "0.1.0"
SEED = 20260817
POLICY_COUNT = 100
SCENARIOS = ("active", "recovered", "lapsed", "surrendered")
EXPERIMENTS_DIR = REPOSITORY_ROOT / "docs" / "experiments"
RESULT_PATH = EXPERIMENTS_DIR / "phase-01-07-synthetic-rate-assessment.json"

SOA_STUDY_URL = (
    "https://www.soa.org/globalassets/assets/files/resources/experience-studies/"
    "2024/15-22-twlls.pdf"
)
SOA_METHOD_URL = (
    "https://www.soa.org/resources/tables-calcs-tools/experience-study-tool/"
)

PolicyEvent = dict[str, Any]
PolicyHistory = list[PolicyEvent]


def classify_scenario(history: PolicyHistory) -> str:
    """Classify one valid history using its structured lifecycle events."""

    event_types = {event["event_type"] for event in history}
    if "outcome.lapsed" in event_types:
        return "lapsed"
    if "outcome.surrendered" in event_types:
        return "surrendered"
    entered_grace = any(
        event["event_type"] == "policy.status_changed"
        and event["payload"].get("new_status") == "grace_period"
        for event in history
    )
    return "recovered" if entered_grace else "active"


def rate(numerator: int, denominator: int) -> dict[str, int | str]:
    """Return an auditable exact ratio and a stable six-place decimal."""

    if denominator <= 0:
        raise ValueError("rate denominator must be greater than zero")
    value = Fraction(numerator, denominator)
    return {
        "numerator": numerator,
        "denominator": denominator,
        "exact_fraction": f"{value.numerator}/{value.denominator}",
        "decimal": f"{numerator / denominator:.6f}",
    }


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _days_between(start: str, end: str) -> int:
    delta = _parse_timestamp(end) - _parse_timestamp(start)
    if delta.seconds or delta.microseconds:
        raise ValueError("assessment timing interval is not a whole number of days")
    return delta.days


def _event(history: PolicyHistory, event_type: str) -> PolicyEvent:
    matches = [event for event in history if event["event_type"] == event_type]
    if len(matches) != 1:
        raise ValueError(f"expected one {event_type} event, found {len(matches)}")
    return matches[0]


def _events(history: PolicyHistory, event_type: str) -> list[PolicyEvent]:
    return [event for event in history if event["event_type"] == event_type]


def _status_event(history: PolicyHistory, new_status: str) -> PolicyEvent:
    matches = [
        event
        for event in history
        if event["event_type"] == "policy.status_changed"
        and event["payload"]["new_status"] == new_status
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one transition to {new_status}, found {len(matches)}"
        )
    return matches[0]


def _summary(values: Iterable[int]) -> dict[str, int | str]:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot summarize an empty metric")
    mean = Fraction(sum(ordered), len(ordered))
    median = statistics.median(ordered)
    return {
        "count": len(ordered),
        "minimum": ordered[0],
        "median": f"{median:.1f}",
        "mean_exact": f"{mean.numerator}/{mean.denominator}",
        "mean_decimal": f"{float(mean):.2f}",
        "maximum": ordered[-1],
    }


def assess_histories(histories: list[PolicyHistory]) -> dict[str, Any]:
    """Calculate deterministic aggregates from complete validated histories."""

    if not histories:
        raise ValueError("assessment requires at least one policy history")
    for history in histories:
        validate_policy_history(history)

    policy_count = len(histories)
    scenarios = Counter(classify_scenario(history) for history in histories)
    unsupported = set(scenarios) - set(SCENARIOS)
    if unsupported:
        raise ValueError(f"unsupported scenarios: {sorted(unsupported)}")

    issued_events = [_event(history, "policy.issued") for history in histories]
    all_events = [event for history in histories for event in history]
    payment_events = [
        event
        for event in all_events
        if event["event_type"] in ("payment.received", "payment.failed")
    ]
    failed_payments = [
        event for event in payment_events if event["event_type"] == "payment.failed"
    ]
    received_payments = [
        event for event in payment_events if event["event_type"] == "payment.received"
    ]

    grace_histories = [
        history
        for history in histories
        if any(
            event["event_type"] == "policy.status_changed"
            and event["payload"]["new_status"] == "grace_period"
            for event in history
        )
    ]
    recovered_histories = [
        history for history in histories if classify_scenario(history) == "recovered"
    ]
    contact_histories = [
        history
        for history in histories
        if any(event["event_type"] == "service.contact_recorded" for event in history)
    ]

    product_counts = Counter(
        event["payload"]["product_variant"] for event in issued_events
    )
    billing_counts = Counter(
        event["payload"]["billing_frequency"] for event in issued_events
    )
    premium_values = [
        event["payload"]["premium_amount_cents"] for event in issued_events
    ]

    issue_to_due = []
    failure_to_reminder = []
    failure_to_grace = []
    grace_to_recovery = []
    failure_to_lapse = []
    inquiry_to_surrender = []
    for history in histories:
        issued = _event(history, "policy.issued")
        due = _event(history, "billing.premium_due")
        issue_to_due.append(
            _days_between(issued["effective_at"], due["effective_at"])
        )

        scenario = classify_scenario(history)
        if scenario in ("recovered", "lapsed"):
            failure = _event(history, "payment.failed")
            reminder = next(
                event
                for event in _events(history, "notice.sent")
                if event["payload"]["notice_type"] == "payment_reminder"
            )
            grace = _status_event(history, "grace_period")
            failure_to_reminder.append(
                _days_between(failure["effective_at"], reminder["effective_at"])
            )
            failure_to_grace.append(
                _days_between(failure["effective_at"], grace["effective_at"])
            )
            if scenario == "recovered":
                recovery = _status_event(history, "active")
                grace_to_recovery.append(
                    _days_between(grace["effective_at"], recovery["effective_at"])
                )
            else:
                lapse = _event(history, "outcome.lapsed")
                failure_to_lapse.append(
                    _days_between(failure["effective_at"], lapse["effective_at"])
                )

        if scenario == "surrendered":
            inquiry = next(
                event
                for event in _events(history, "service.contact_recorded")
                if event["payload"]["reason"] == "surrender_inquiry"
            )
            surrender = _event(history, "outcome.surrendered")
            inquiry_to_surrender.append(
                _days_between(inquiry["effective_at"], surrender["effective_at"])
            )

    terminal_count = scenarios["lapsed"] + scenarios["surrendered"]
    metrics = {
        "billing_frequency": {
            "definition": "Issued policies grouped by fictional billing frequency.",
            "unit": "policies",
            "counts": dict(sorted(billing_counts.items())),
        },
        "grace_entry": {
            "definition": "Policies with a transition to grace_period / generated policies.",
            "unit": "policy proportion over one generated scenario path",
            "value": rate(len(grace_histories), policy_count),
        },
        "grace_recovery": {
            "definition": "Policies returning to active / policies entering grace_period.",
            "unit": "conditional policy proportion over one generated scenario path",
            "value": rate(len(recovered_histories), len(grace_histories)),
        },
        "payment_events": {
            "definition": "Structured payment events; a recovery can create a second attempt.",
            "unit": "events",
            "attempt_count": len(payment_events),
            "failed_count": len(failed_payments),
            "failure_proportion": rate(len(failed_payments), len(payment_events)),
            "received_count": len(received_payments),
            "received_proportion": rate(len(received_payments), len(payment_events)),
        },
        "policy_count": policy_count,
        "premium_amount_cents": {
            "definition": "Premium amount recorded on policy.issued.",
            "unit": "integer USD cents; premium mode is not annualized",
            "summary": _summary(premium_values),
        },
        "product_variant": {
            "definition": "Issued policies grouped by fictional product variant.",
            "unit": "policies",
            "counts": dict(sorted(product_counts.items())),
        },
        "scenario_mix": {
            "definition": "Policies classified from complete structured histories / generated policies.",
            "unit": "policy proportion over one generated scenario path",
            "counts": {scenario: scenarios[scenario] for scenario in SCENARIOS},
            "proportions": {
                scenario: rate(scenarios[scenario], policy_count)
                for scenario in SCENARIOS
            },
        },
        "service_contact": {
            "definition": "Policies with at least one structured service contact / generated policies.",
            "unit": "policy proportion over one generated scenario path",
            "value": rate(len(contact_histories), policy_count),
        },
        "terminal_outcomes": {
            "definition": "Policies with a generated lapse or surrender outcome / generated policies.",
            "unit": "policy proportion over one generated scenario path; not annualized",
            "combined": rate(terminal_count, policy_count),
            "lapsed": rate(scenarios["lapsed"], policy_count),
            "surrendered": rate(scenarios["surrendered"], policy_count),
        },
        "timing_days": {
            "definition": "Whole-day effective-time intervals imposed by current scenario logic.",
            "unit": "days",
            "failure_to_grace": _summary(failure_to_grace),
            "failure_to_lapse": _summary(failure_to_lapse),
            "failure_to_payment_reminder": _summary(failure_to_reminder),
            "grace_to_recovery": _summary(grace_to_recovery),
            "inquiry_to_surrender": _summary(inquiry_to_surrender),
            "issue_to_first_due": _summary(issue_to_due),
        },
    }
    return metrics


def source_register() -> list[dict[str, Any]]:
    """Return fixed, auditable public-source metadata used by the report."""

    return [
        {
            "source_id": "soa-limra-2015-2022-term-whole-life",
            "organization": "Society of Actuaries Research Institute and LIMRA",
            "title": (
                "2015-2022 Term and Whole Life Insurance Policy "
                "Surrender/Lapse Experience Study Report"
            ),
            "publication_date": "2024-12",
            "access_date": "2026-08-18",
            "url": SOA_STUDY_URL,
            "locators": {
                "scope_and_population": "pages 1-2",
                "study_totals": "page 1",
                "combined_lapse_definition": "page 2",
                "methodology_and_limitations": "page 4",
            },
            "population": (
                "Fully underwritten single-life term and whole-life policies sold "
                "in the United States and its territories; 28 contributing companies."
            ),
            "study_period": (
                "Seven complete study years, 2016-2022, spanning policy "
                "anniversaries in 2015-2022."
            ),
            "exposure_basis": (
                "Policy exposure calculated with the Balducci approach; the report "
                "also discusses face-amount exposure."
            ),
            "published_totals": {
                "approximate_policy_exposures": 135900000,
                "approximate_surrenders_and_lapses": 5400000,
                "derived_termination_to_exposure_ratio": "0.039735",
                "derived_value_warning": (
                    "Computed from rounded headline totals; not presented by the "
                    "source as an official aggregate lapse rate."
                ),
            },
            "definition_note": (
                "The report uses lapse to include terminations with value "
                "(surrenders) and without value (forfeitures)."
            ),
            "limitations": (
                "Detailed segmented results are outside the public report; source "
                "experience is exposure-based and duration-sensitive."
            ),
        },
        {
            "source_id": "soa-experience-study-calculations",
            "organization": "Society of Actuaries Research Institute",
            "title": "Experience Study Calculations Educational Tool",
            "publication_date": "2023-06; materials updated 2024-03",
            "access_date": "2026-08-18",
            "url": SOA_METHOD_URL,
            "locators": {
                "purpose": "web page introduction",
                "partial_rate_year_warning": "web page introduction",
            },
            "population": "Methodological educational material; no portfolio population.",
            "study_period": "Not applicable.",
            "exposure_basis": (
                "Explains experience-rate calculations and warns about errors from "
                "combining partial rate years."
            ),
            "published_totals": {},
            "definition_note": (
                "Used to support the decision not to annualize one-cycle simulator "
                "proportions, not as a numerical calibration target."
            ),
            "limitations": "Methodological reference rather than an experience table.",
        },
    ]


def build_assessment() -> dict[str, Any]:
    """Return the canonical assessment object."""

    config = GeneratorConfig(seed=SEED, policy_count=POLICY_COUNT)
    histories = generate_policy_histories(config.seed, config.policy_count)
    metrics = assess_histories(histories)
    return {
        "assessment_id": ASSESSMENT_ID,
        "assessment_version": ASSESSMENT_VERSION,
        "metric_definition_version": METRIC_DEFINITION_VERSION,
        "generation": generation_provenance(config),
        "metrics": metrics,
        "sources": source_register(),
        "comparisons": [
            {
                "comparison_id": "combined-terminal-outcomes-vs-soa-lapse-surrender",
                "synthetic_metric": "terminal_outcomes.combined",
                "synthetic_value": metrics["terminal_outcomes"]["combined"],
                "reference_source_id": "soa-limra-2015-2022-term-whole-life",
                "reference_value": {
                    "decimal": "0.039735",
                    "status": "derived from approximate rounded headline totals",
                },
                "classification": "not_comparable",
                "rationale": (
                    "The synthetic numerator is forced by one bounded scenario path "
                    "per policy and has no policy-year exposure denominator. The SOA/"
                    "LIMRA value is derived from rounded totals across complete study "
                    "years, uses exposure methodology, combines surrender and "
                    "forfeiture, and reflects duration and product effects absent here."
                ),
            },
            {
                "comparison_id": "fictional-product-mix-vs-soa-exposure-mix",
                "synthetic_metric": "product_variant.counts",
                "synthetic_value": metrics["product_variant"]["counts"],
                "reference_source_id": "soa-limra-2015-2022-term-whole-life",
                "reference_value": {
                    "whole_life_exposure_by_count": "more than 60%"
                },
                "classification": "not_comparable",
                "rationale": (
                    "The generator chooses two fictional labels randomly at issuance; "
                    "they do not encode the source study's plan definitions. The source "
                    "measure is multi-year exposure, while the synthetic measure is an "
                    "issuance count in a 100-policy engineering fixture."
                ),
            },
            {
                "comparison_id": "one-cycle-proportions-vs-experience-rates",
                "synthetic_metric": "all policy proportions",
                "synthetic_value": "one generated path per policy",
                "reference_source_id": "soa-experience-study-calculations",
                "reference_value": "experience-rate calculation guidance",
                "classification": "directional_only",
                "rationale": (
                    "The methodological reference supports exposure-aware rate design "
                    "and warns about partial-year errors. It supports the decision not "
                    "to annualize current simulator proportions but supplies no target."
                ),
            },
        ],
        "calibration_decisions": [
            {
                "assumption": "equal four-scenario allocation",
                "disposition": "retain_as_fixture",
                "reason": (
                    "Guarantees deterministic lifecycle coverage; it is not an "
                    "estimated prevalence distribution."
                ),
            },
            {
                "assumption": "scenario weights configurable independently of coverage",
                "disposition": "parameterize_later",
                "reason": (
                    "A future observation or robustness consumer may require a separate "
                    "configuration while the canonical acceptance fixture stays stable."
                ),
            },
            {
                "assumption": "annual lapse or surrender calibration",
                "disposition": "defer_pending_contract_support",
                "reason": (
                    "Requires multi-period exposure, policy duration, and clearer product "
                    "definitions before a public experience rate is comparable."
                ),
            },
            {
                "assumption": "premium, billing, payment, contact, and timing distributions",
                "disposition": "retain_as_fixture",
                "reason": (
                    "Current values exercise contracts and timelines; no compatible "
                    "public evidence in this assessment justifies calibration."
                ),
            },
            {
                "assumption": "generator or published sample change in Phase 1.07",
                "disposition": "no_change",
                "reason": (
                    "Assessment found no comparable target that warrants a versioned "
                    "generator or dataset change."
                ),
            },
        ],
        "claim_boundaries": [
            "Synthetic results do not represent an insurer or market prevalence.",
            "Aggregate similarity would not establish record-level realism.",
            "This assessment does not establish actuarial credibility, causal validity, fairness, or predictive utility.",
            "Phase 2 model calibration is separate from generator-assumption assessment.",
        ],
    }


def assessment_bytes() -> bytes:
    return (json.dumps(build_assessment(), indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def write_assessment() -> None:
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_bytes(assessment_bytes())
    print(f"wrote {RESULT_PATH.relative_to(REPOSITORY_ROOT)}")


def check_assessment() -> bool:
    if not RESULT_PATH.is_file():
        print(f"missing assessment artifact: {RESULT_PATH.relative_to(REPOSITORY_ROOT)}")
        return False
    if RESULT_PATH.read_bytes() != assessment_bytes():
        print(f"stale assessment artifact: {RESULT_PATH.relative_to(REPOSITORY_ROOT)}")
        return False
    print("Synthetic-rate assessment artifact is reproducible.")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or verify the deterministic synthetic-rate assessment."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify committed results")
    mode.add_argument("--write", action="store_true", help="replace committed results")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.write:
        write_assessment()
        return 0
    return 0 if check_assessment() else 1


if __name__ == "__main__":
    raise SystemExit(main())
