"""Domain models and dataclasses for counterfactual simulation and offline policy evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Mapping

from inforsight_simulator.economics import load_economics_resource_contract


@dataclass(frozen=True)
class InterventionParameters:
    """Action-specific logit shifts and decay parameters."""

    base_shift: float
    direct_cost_usd: float
    is_specialist: bool = False
    resource_hours: float = 0.0


_ECONOMICS = load_economics_resource_contract()


def _params(action_type: str, base_shift: float) -> InterventionParameters:
    action = _ECONOMICS.action(action_type)
    return InterventionParameters(
        base_shift=base_shift,
        direct_cost_usd=action.direct_cost_usd,
        is_specialist=action_type in {
            "grace_period_consultation", "specialist_phone_outreach"
        },
        resource_hours=action.personnel_hours,
    )


# Standard canonical action parameters
CANONICAL_INTERVENTIONS: dict[str, InterventionParameters] = {
    "abstain": _params("abstain", 0.00),
    "courtesy_reminder": _params("courtesy_reminder", -0.35),
    "payment_method_remediation": _params("payment_method_remediation", -0.90),
    "grace_period_consultation": _params("grace_period_consultation", -1.25),
    "specialist_phone_outreach": _params("specialist_phone_outreach", -1.60),
}


@dataclass(frozen=True)
class CounterfactualOutcome:
    """Potential outcomes for a single policy under a specific intervention."""

    policy_id: str
    action_type: str
    baseline_lapse_prob: float
    counterfactual_lapse_prob: float
    baseline_surrender_prob: float
    counterfactual_surrender_prob: float
    treatment_effect_uplift: float  # baseline_lapse - counterfactual_lapse
    monthly_lapse_hazards: tuple[float, float, float]
    monthly_surrender_hazards: tuple[float, float, float]
    direct_cost_usd: float
    combined_termination_treatment_effect: float = 0.0
    direct_cost_usd_micros: int = 0


@dataclass(frozen=True)
class TriageAssignment:
    """Assignment decision for a single policy under a triage policy."""

    policy_id: str
    policy_name: str
    assigned_action: str
    risk_score: float
    annual_premium_usd: float
    direct_cost_usd: float
    counterfactual_lapse_prob: float
    expected_saved_lapse: float  # P_0(lapse) - P_a(lapse)
    expected_gross_preserved_usd: float  # expected_saved_lapse * annual_premium
    expected_net_preserved_usd: float  # gross - direct_cost
    consumes_specialist: bool
    resource_hours: float
    combined_termination_effect: float = 0.0
    annual_premium_cents: int = 0
    direct_cost_usd_micros: int = 0
    gross_expected_value_usd_micros: int = 0
    net_expected_value_usd_micros: int = 0
    personnel_seconds: int = 0


@dataclass(frozen=True)
class PolicyEvaluationMetrics:
    """Aggregated performance metrics for a single triage policy."""

    policy_name: str
    cohort_size: int
    total_lapses: float
    baseline_lapses: float
    lapses_prevented: float
    absolute_lift: float  # lapses_prevented / cohort_size
    relative_reduction_pct: float  # lapses_prevented / baseline_lapses * 100
    total_spend_usd: float
    gross_preserved_usd: float
    net_preserved_usd: float
    cost_per_conserved_policy_usd: float
    rocs: float  # Return on Conservation Spend: net_preserved / total_spend
    specialist_hours_used: float
    specialist_calls_count: int
    action_distribution: dict[str, int] = field(default_factory=dict)
    combined_terminations_avoided: float = 0.0
    total_spend_usd_micros: int = 0
    gross_expected_value_usd_micros: int = 0
    net_expected_value_usd_micros: int = 0
    personnel_seconds_used: int = 0
    metric_id: str = "modeled_expected_annual_premium_preserved_usd_micros"


@dataclass(frozen=True)
class MetricInterval:
    """Median and empirical 95% bootstrap confidence interval."""

    median: float
    ci_lower: float
    ci_upper: float

    def to_dict(self) -> dict[str, float]:
        return {
            "median": round(self.median, 4),
            "ci_lower": round(self.ci_lower, 4),
            "ci_upper": round(self.ci_upper, 4),
        }


@dataclass(frozen=True)
class PairwiseContrast:
    """Comparative contrast between the Decision Engine and a competitor policy."""

    competitor_name: str
    delta_net_preserved_usd: MetricInterval
    delta_lapses_prevented: MetricInterval
    delta_rocs: MetricInterval
    p_value_superiority: float  # P(delta_npv <= 0)


@dataclass(frozen=True)
class OPEResultManifest:
    """Complete cryptographic summary manifest for offline policy evaluation."""

    schema_version: str
    created_at: str
    evaluation_seed: int
    bootstrap_samples: int
    cohort_size: int
    specialist_capacity_hours: float
    budget_cap_usd: float
    policy_metrics: dict[str, dict[str, Any]]
    policy_intervals: dict[str, dict[str, MetricInterval]]
    pairwise_contrasts: dict[str, PairwiseContrast]
    verifications: dict[str, bool]
    manifest_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "evaluation_seed": self.evaluation_seed,
            "bootstrap_samples": self.bootstrap_samples,
            "cohort_size": self.cohort_size,
            "specialist_capacity_hours": self.specialist_capacity_hours,
            "budget_cap_usd": self.budget_cap_usd,
            "policy_metrics": self.policy_metrics,
            "policy_intervals": {
                p_name: {k: v.to_dict() for k, v in intervals.items()}
                for p_name, intervals in self.policy_intervals.items()
            },
            "pairwise_contrasts": {
                c_name: {
                    "competitor_name": c.competitor_name,
                    "delta_net_preserved_usd": c.delta_net_preserved_usd.to_dict(),
                    "delta_lapses_prevented": c.delta_lapses_prevented.to_dict(),
                    "delta_rocs": c.delta_rocs.to_dict(),
                    "p_value_superiority": round(c.p_value_superiority, 6),
                }
                for c_name, c in self.pairwise_contrasts.items()
            },
            "verifications": self.verifications,
            "manifest_digest": self.manifest_digest,
        }
