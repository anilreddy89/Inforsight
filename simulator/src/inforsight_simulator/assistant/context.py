"""Context compiler and ground-truth entity container for case intelligence.

Consolidates point-in-time policy facts, scoring outputs, eligibility rules,
and uplift optimization into an immutable evidence package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from inforsight_simulator.assistant.models import (
    DisqualifiedActionSummary,
    FactualTimelineEvent,
    RiskDriver,
)


@dataclass(frozen=True)
class CaseEvidenceContext:
    """Consolidated ground-truth evidence context for a conservation case."""

    # Policy Identification & Cutoff
    policy_id: str
    as_of_date: str
    case_id: str

    # Core Policy Facts (from reconstructed state)
    product_type: str
    annual_premium: float
    monthly_premium: float
    coverage_amount: float | None
    tenure_months: int
    total_premiums_paid: float | None
    policy_status: str
    in_grace_period: bool | None
    days_past_due: int | None
    payment_frequency: str
    initial_payment_method: str
    risk_class: str
    servicing_advisor_id: str
    has_active_claim: bool | None = None
    has_legal_hold: bool | None = None
    has_registered_dispute: bool | None = None

    # Scoring & Attribution (from Model Gateway / Bundle)
    calibrated_probability: float = 0.05
    operational_tier: str = "Tier 1: Low Risk"
    top_risk_drivers: tuple[RiskDriver, ...] = ()

    # Action Eligibility (from Rules Engine)
    eligible_actions: tuple[str, ...] = ("courtesy_reminder", "abstain")
    disqualified_actions: tuple[DisqualifiedActionSummary, ...] = ()

    # Uplift Optimization (from Optimization Solver)
    primary_action: str = "courtesy_reminder"
    uplift_quadrant: str = "PERSUADABLE"
    expected_net_utility: float = 50.0
    alternative_actions: tuple[str, ...] = ("abstain",)

    # Historical Event Timeline up to Cutoff
    timeline_events: tuple[FactualTimelineEvent, ...] = ()

    @property
    def has_legal_dispute_freeze(self) -> bool:
        """Indicates if any legal, hold, or dispute freeze is active."""
        return any(value is True for value in (
            self.has_active_claim, self.has_legal_hold, self.has_registered_dispute
        ))

    @property
    def ground_truth_entities(self) -> dict[str, Any]:
        """Compile a dictionary of canonical ground-truth entities for validation."""
        # Gather all valid dates from timeline and cutoff
        valid_dates: set[str] = set()
        if self.as_of_date:
            valid_dates.add(self.as_of_date[:10])  # YYYY-MM-DD
        for ev in self.timeline_events:
            if ev.occurred_at:
                valid_dates.add(ev.occurred_at[:10])

        # Gather currency numbers
        currency_numbers: set[float] = {
            round(float(self.annual_premium), 2),
            round(float(self.monthly_premium), 2),
            round(float(self.expected_net_utility), 2),
        }
        for optional_value in (self.coverage_amount, self.total_premiums_paid):
            if optional_value is not None:
                currency_numbers.add(round(float(optional_value), 2))

        # Gather text representation of currencies (e.g. 154.17, "154.17", "1850", "250000")
        currency_strings: set[str] = set()
        for num in currency_numbers:
            currency_strings.add(f"{num:.2f}")
            if num.is_integer():
                currency_strings.add(str(int(num)))

        disqualified_ids = {d.action_id for d in self.disqualified_actions}

        return {
            "policy_id": self.policy_id,
            "case_id": self.case_id,
            "product_type": self.product_type,
            "tenure_months": self.tenure_months,
            "policy_status": self.policy_status,
            "payment_frequency": self.payment_frequency,
            "valid_dates": valid_dates,
            "currency_numbers": currency_numbers,
            "currency_strings": currency_strings,
            "eligible_actions": set(self.eligible_actions),
            "disqualified_actions": disqualified_ids,
            "has_legal_dispute_freeze": self.has_legal_dispute_freeze,
            "calibrated_probability": self.calibrated_probability,
            "operational_tier": self.operational_tier,
        }
