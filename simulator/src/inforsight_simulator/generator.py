"""Seeded generation of small, fictional policy-event histories."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from typing import Any

from .config import DEFAULT_SIMULATION_START, GeneratorConfig


SCHEMA_VERSION = "1.0.0"
# Historical observation artifacts import this name and remain version-pinned.
GENERATOR_VERSION = "0.1.0"
LEGACY_GENERATOR_VERSION = GENERATOR_VERSION
NAMESPACED_GENERATOR_VERSION = "0.2.0"
CONFIGURATION_CANONICALIZATION_VERSION = "1.0.0"
CONFIGURATION_DIGEST_ALGORITHM = "sha256"
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


@dataclass(frozen=True)
class _LegacyConfig:
    seed: int
    policy_count: int
    simulation_start: datetime = DEFAULT_SIMULATION_START

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")
        if isinstance(self.policy_count, bool) or not isinstance(self.policy_count, int):
            raise TypeError("policy_count must be an integer")
        if self.policy_count <= 0:
            raise ValueError("policy_count must be greater than zero")


def canonical_configuration(config: GeneratorConfig) -> dict[str, int | str]:
    """Return the complete, versioned configuration used by corrected generation."""

    return {
        "canonicalization_version": CONFIGURATION_CANONICALIZATION_VERSION,
        "generator_version": NAMESPACED_GENERATOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "seed": config.seed,
        "policy_count": config.policy_count,
        "run_namespace": config.run_namespace,
        "simulation_start": _timestamp(config.simulation_start),
    }


def configuration_digest(config: GeneratorConfig) -> str:
    """Return the stable digest of every corrected generation input."""

    encoded = json.dumps(
        canonical_configuration(config),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return sha256(encoded).hexdigest()


def run_identity(config: GeneratorConfig) -> str:
    """Return the deterministic bounded identity for a configured run."""

    return configuration_digest(config)[:24]


def generation_provenance(config: GeneratorConfig) -> dict[str, int | str]:
    """Return provenance bound to the exact corrected generation config."""

    return {
        **canonical_configuration(config),
        "configuration_digest_algorithm": CONFIGURATION_DIGEST_ALGORITHM,
        "configuration_sha256": configuration_digest(config),
        "run_identity": run_identity(config),
        "compatibility_mode": "namespaced",
    }


def verify_generation_provenance(
    config: GeneratorConfig,
    provenance: dict[str, int | str],
) -> None:
    """Reject provenance that is not an exact description of the config."""

    if provenance != generation_provenance(config):
        raise ValueError("generation provenance does not match configuration")


def legacy_generation_provenance(
    seed: int,
    policy_count: int = 100,
) -> dict[str, int | str]:
    """Return truthful provenance for immutable v1 generator output."""

    legacy = _LegacyConfig(
        seed=seed,
        policy_count=policy_count,
    )
    return {
        "generator_version": LEGACY_GENERATOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "seed": legacy.seed,
        "policy_count": legacy.policy_count,
        "simulation_start": _timestamp(legacy.simulation_start),
    }


def generate_policy_histories(config: GeneratorConfig) -> list[PolicyHistory]:
    """Generate corrected, namespaced histories from one exact config."""

    if not isinstance(config, GeneratorConfig):
        raise TypeError("config must be a GeneratorConfig")
    return _generate_policy_histories(
        config,
        run_identity_value=run_identity(config),
    )


def generate_legacy_policy_histories(
    seed: int,
    policy_count: int = 100,
) -> list[PolicyHistory]:
    """Reproduce immutable generator 0.1.0 output with counter-only IDs."""

    config = _LegacyConfig(seed=seed, policy_count=policy_count)
    return _generate_policy_histories(config, run_identity_value=None)


def _generate_policy_histories(
    config: GeneratorConfig | _LegacyConfig,
    *,
    run_identity_value: str | None,
) -> list[PolicyHistory]:
    rng = random.Random(config.seed)
    scenarios = [
        SCENARIOS[index % len(SCENARIOS)] for index in range(config.policy_count)
    ]
    rng.shuffle(scenarios)

    return [
        _generate_history(
            config,
            rng,
            policy_index,
            scenario,
            run_identity_value,
        )
        for policy_index, scenario in enumerate(scenarios, start=1)
    ]


def _generate_history(
    config: GeneratorConfig | _LegacyConfig,
    rng: random.Random,
    policy_index: int,
    scenario: str,
    identity: str | None,
) -> PolicyHistory:
    policy_id = _identifier("pol", policy_index, run_identity_value=identity)
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
                "event_id": _identifier(
                    "evt", policy_index, event_index, run_identity_value=identity
                ),
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
    billing_id = _identifier("bil", policy_index, 1, run_identity_value=identity)
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

    payment_id = _identifier("pay", policy_index, 1, run_identity_value=identity)
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
            _add_service_contact(
                add_event,
                rng,
                policy_index,
                first_due + timedelta(days=8),
                run_identity_value=identity,
            )
        return history

    if scenario == "surrendered":
        add_event("payment.received", first_due + timedelta(days=1), payment_base)
        _add_service_contact(
            add_event,
            rng,
            policy_index,
            first_due + timedelta(days=15),
            run_identity_value=identity,
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
            "notice_id": _identifier(
                "ntc", policy_index, 1, run_identity_value=identity
            ),
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
            {
                **payment_base,
                "payment_id": _identifier(
                    "pay", policy_index, 2, run_identity_value=identity
                ),
            },
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
            "notice_id": _identifier(
                "ntc", policy_index, 2, run_identity_value=identity
            ),
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
    run_identity_value: str | None = None,
    reason: str = "policy_review",
) -> None:
    add_event(
        "service.contact_recorded",
        occurred_at,
        {
            "contact_id": _identifier(
                "con", policy_index, 1, run_identity_value=run_identity_value
            ),
            "direction": rng.choice(("inbound", "outbound")),
            "channel": rng.choice(("phone", "email", "postal_mail")),
            "reason": reason,
            "resolution": rng.choice(("resolved", "follow_up_required", "no_action")),
        },
    )


def _identifier(
    prefix: str,
    primary: int,
    secondary: int = 0,
    *,
    run_identity_value: str | None = None,
) -> str:
    if run_identity_value is not None:
        # The prefix is the derivation domain. Keeping counters as the suffix also
        # preserves deterministic event ordering for equal timestamps.
        return (
            f"{prefix}_{run_identity_value}{primary:06x}{secondary:06x}"
        )
    return f"{prefix}_{primary:06x}{secondary:06x}"


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")
