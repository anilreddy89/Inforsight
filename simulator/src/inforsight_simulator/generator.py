"""Seeded generation of small, fictional policy-event histories."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from .config import GeneratorConfig


SCHEMA_VERSION = "1.0.0"
GENERATOR_VERSION = "0.1.0"
SCENARIOS = ("active", "recovered", "lapsed", "surrendered")
PRODUCT_VARIANTS = ("fictional_term_life", "fictional_whole_life")
BILLING_FREQUENCIES = ("monthly", "quarterly", "semiannual", "annual")
BILLING_INTERVAL_DAYS = {
    "monthly": 30,
    "quarterly": 90,
    "semiannual": 182,
    "annual": 365,
}
PAYMENT_METHODS = ("electronic_transfer", "card", "check")
FAILURE_REASONS = (
    "insufficient_funds",
    "method_declined",
    "method_expired",
    "processing_error",
)

PolicyEvent = dict[str, Any]
PolicyHistory = list[PolicyEvent]


def generation_provenance(config: GeneratorConfig) -> dict[str, int | str]:
    """Return the stable inputs and versions needed to identify a run."""

    return {
        "generator_version": GENERATOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "seed": config.seed,
        "policy_count": config.policy_count,
        "simulation_start": _timestamp(config.simulation_start),
    }


def generate_policy_histories(
    seed: int,
    policy_count: int = 100,
) -> list[PolicyHistory]:
    """Generate deterministic fictional histories from explicit inputs."""

    config = GeneratorConfig(seed=seed, policy_count=policy_count)
    rng = random.Random(config.seed)
    scenarios = [SCENARIOS[index % len(SCENARIOS)] for index in range(policy_count)]
    rng.shuffle(scenarios)

    return [
        _generate_history(config, rng, policy_index, scenario)
        for policy_index, scenario in enumerate(scenarios, start=1)
    ]


def _generate_history(
    config: GeneratorConfig,
    rng: random.Random,
    policy_index: int,
    scenario: str,
) -> PolicyHistory:
    policy_id = _identifier("pol", policy_index)
    issue_time = config.simulation_start + timedelta(
        days=rng.randint(0, 30), hours=rng.randint(8, 16)
    )
    premium_cents = rng.randrange(5_000, 30_001, 500)
    billing_frequency = rng.choice(BILLING_FREQUENCIES)
    history: PolicyHistory = []

    def add_event(
        event_type: str,
        occurred_at: datetime,
        payload: dict[str, Any],
    ) -> None:
        event_index = len(history) + 1
        history.append(
            {
                "schema_version": SCHEMA_VERSION,
                "event_id": _identifier("evt", policy_index, event_index),
                "policy_id": policy_id,
                "event_type": event_type,
                "occurred_at": _timestamp(occurred_at),
                "effective_at": _timestamp(occurred_at),
                "ingested_at": _timestamp(occurred_at + timedelta(hours=1)),
                "payload": payload,
            }
        )

    add_event(
        "policy.issued",
        issue_time,
        {
            "product_variant": rng.choice(PRODUCT_VARIANTS),
            "initial_status": "active",
            "billing_frequency": billing_frequency,
            "premium_amount_cents": premium_cents,
            "currency": "USD",
        },
    )

    first_due = issue_time + timedelta(days=BILLING_INTERVAL_DAYS[billing_frequency])
    billing_id = _identifier("bil", policy_index, 1)
    add_event(
        "billing.premium_due",
        first_due,
        {
            "billing_id": billing_id,
            "due_date": first_due.date().isoformat(),
            "amount_cents": premium_cents,
            "currency": "USD",
        },
    )

    payment_id = _identifier("pay", policy_index, 1)
    payment_base = {
        "payment_id": payment_id,
        "billing_id": billing_id,
        "amount_cents": premium_cents,
        "currency": "USD",
        "method": rng.choice(PAYMENT_METHODS),
    }

    if scenario == "active":
        add_event("payment.received", first_due + timedelta(days=1), payment_base)
        if policy_index % 2 == 0:
            _add_service_contact(add_event, rng, policy_index, first_due + timedelta(days=8))
        return history

    if scenario == "surrendered":
        add_event("payment.received", first_due + timedelta(days=1), payment_base)
        _add_service_contact(
            add_event,
            rng,
            policy_index,
            first_due + timedelta(days=15),
            reason="surrender_inquiry",
        )
        terminal_time = first_due + timedelta(days=20)
        add_event(
            "outcome.surrendered",
            terminal_time,
            {
                "reason": rng.choice(
                    ("policyholder_request", "financial_need", "product_change", "unknown")
                ),
                "surrender_value_cents": rng.randrange(0, 200_001, 1_000),
                "currency": "USD",
            },
        )
        add_event(
            "policy.status_changed",
            terminal_time,
            {
                "previous_status": "active",
                "new_status": "surrendered",
                "reason": "outcome_recorded",
            },
        )
        return history

    add_event(
        "payment.failed",
        first_due + timedelta(days=1),
        {**payment_base, "failure_reason": rng.choice(FAILURE_REASONS)},
    )
    add_event(
        "notice.sent",
        first_due + timedelta(days=3),
        {
            "notice_id": _identifier("ntc", policy_index, 1),
            "notice_type": "payment_reminder",
            "delivery_channel": rng.choice(("postal_mail", "email", "phone")),
        },
    )
    grace_time = first_due + timedelta(days=5)
    add_event(
        "policy.status_changed",
        grace_time,
        {
            "previous_status": "active",
            "new_status": "grace_period",
            "reason": "payment_overdue",
        },
    )

    if scenario == "recovered":
        recovery_time = first_due + timedelta(days=12)
        add_event(
            "payment.received",
            recovery_time,
            {**payment_base, "payment_id": _identifier("pay", policy_index, 2)},
        )
        add_event(
            "policy.status_changed",
            recovery_time,
            {
                "previous_status": "grace_period",
                "new_status": "active",
                "reason": "payment_current",
            },
        )
        return history

    lapse_time = first_due + timedelta(days=35)
    add_event(
        "notice.sent",
        first_due + timedelta(days=25),
        {
            "notice_id": _identifier("ntc", policy_index, 2),
            "notice_type": "lapse_warning",
            "delivery_channel": rng.choice(("postal_mail", "email", "phone")),
        },
    )
    add_event(
        "outcome.lapsed",
        lapse_time,
        {
            "reason": "nonpayment",
            "outstanding_amount_cents": premium_cents,
            "currency": "USD",
        },
    )
    add_event(
        "policy.status_changed",
        lapse_time,
        {
            "previous_status": "grace_period",
            "new_status": "lapsed",
            "reason": "outcome_recorded",
        },
    )
    return history


def _add_service_contact(
    add_event: Any,
    rng: random.Random,
    policy_index: int,
    occurred_at: datetime,
    reason: str = "policy_review",
) -> None:
    add_event(
        "service.contact_recorded",
        occurred_at,
        {
            "contact_id": _identifier("con", policy_index, 1),
            "direction": rng.choice(("inbound", "outbound")),
            "channel": rng.choice(("phone", "email", "postal_mail")),
            "reason": reason,
            "resolution": rng.choice(("resolved", "follow_up_required", "no_action")),
        },
    )


def _identifier(prefix: str, primary: int, secondary: int = 0) -> str:
    return f"{prefix}_{primary:06x}{secondary:06x}"


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")
