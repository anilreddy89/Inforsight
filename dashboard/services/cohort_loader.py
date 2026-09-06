"""Deterministic synthetic demonstration cohort loader for the conservation dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from inforsight_simulator.assistant import CaseBrief
from inforsight_simulator.bundle import ScoringResult
from inforsight_simulator.optimization import OptimalRecommendation, PolicyValuation
from inforsight_simulator.rules import EligibleActionSet, PolicyContext
from inforsight_simulator.v6_corpus import V6CorpusConfig, generate_v6_corpus
from inforsight_simulator.v6_evaluation import _feature_map

from dashboard.config import (
    ACTION_METADATA,
    DEFAULT_MAX_SPECIALIST_HOURS,
    DEFAULT_SPECIALIST_HOURLY_COST,
    RISK_TIERS,
)
from dashboard.services.engine_bridge import EngineBridge


@dataclass(frozen=True)
class TriagePolicyItem:
    """Consolidated point-in-time record for an individual policy in the triage queue."""

    policy_id: str
    as_of_date: str
    product_type: str
    monthly_premium: float
    annual_premium: float
    coverage_amount: float
    tenure_months: int
    in_grace_period: bool
    days_in_grace: int
    billing_channel: str
    status: str
    risk_score: float
    risk_tier: str
    primary_risk_driver: str
    primary_risk_contribution: float
    recommended_action: str
    net_utility: float
    uplift_quadrant: str
    scoring_result: ScoringResult
    eligible_action_set: EligibleActionSet
    optimal_recommendation: OptimalRecommendation
    case_brief: CaseBrief
    case_id: str
    timeline_events: tuple[dict[str, Any], ...]


def load_dashboard_cohort(
    engine_bridge: EngineBridge,
    policy_count: int = 48,
    seed: int = 20280201,
    max_specialist_hours: float = DEFAULT_MAX_SPECIALIST_HOURS,
) -> tuple[list[TriagePolicyItem], dict[str, Any]]:
    """Loads and scores a deterministic demonstration cohort from the Generation v6 simulator."""
    cohort_count = 4
    policies_per_cohort = max(1, policy_count // cohort_count)
    actual_count = cohort_count * policies_per_cohort

    config = V6CorpusConfig(
        base_seed=seed,
        policy_count=actual_count,
        cohort_count=cohort_count,
        policies_per_cohort=policies_per_cohort,
    )
    corpus = generate_v6_corpus(config)

    # 1. Index raw events by policy_id
    policy_events: dict[str, list[dict[str, Any]]] = {}
    for hist in corpus.histories:
        for ev in hist:
            pid = ev.get("policy_id")
            if pid:
                if pid not in policy_events:
                    policy_events[pid] = []
                policy_events[pid].append(ev)

    # 2. Pick latest observation for each policy
    latest_obs_by_policy: dict[str, Any] = {}
    for obs in corpus.observations:
        pid = obs.policy_id
        if pid not in latest_obs_by_policy or obs.as_of > latest_obs_by_policy[pid].as_of:
            latest_obs_by_policy[pid] = obs

    items: list[TriagePolicyItem] = []

    for pid, obs in latest_obs_by_policy.items():
        feat_map = _feature_map(obs)
        score_res = engine_bridge.score_observation(feat_map)

        # Parse timestamps and parameters
        as_of_dt = obs.as_of if isinstance(obs.as_of, datetime) else datetime.fromisoformat(str(obs.as_of))
        if as_of_dt.tzinfo is None:
            as_of_dt = as_of_dt.replace(tzinfo=timezone.utc)
        as_of_str = as_of_dt.isoformat().replace("+00:00", "Z")

        # In grace indicators
        days_grace = int(feat_map.get("days_in_grace", 0))
        is_grace = bool(feat_map.get("is_in_grace", 0) > 0 or days_grace > 0)
        tenure_days = int(feat_map.get("tenure_months", 12)) * 30
        status = "IN_GRACE" if is_grace else "ACTIVE"

        # Construct PolicyContext for rules evaluation
        policy_ctx = PolicyContext(
            policy_id=pid,
            as_of=as_of_dt,
            status=status,
            tenure_days=max(1, tenure_days),
            in_grace_period=is_grace,
            days_past_due=days_grace,
            has_active_claim=False,
            has_legal_hold=False,
            has_registered_dispute=False,
            sms_opt_out=False,
            email_opt_out=False,
            phone_opt_out=False,
            dnc_registered=False,
        )
        eligible_set = engine_bridge.evaluate_eligibility(policy_ctx)

        # Valuation
        monthly_prem = float(feat_map.get("monthly_premium", 150.0))
        annual_prem = monthly_prem * 12.0
        face_amt = float(feat_map.get("coverage_amount", 250000.0))
        clv = annual_prem * 4.5  # Estimate customer lifetime value

        valuation = PolicyValuation(
            policy_id=pid,
            annual_premium_usd=annual_prem,
            customer_lifetime_value_usd=clv,
        )
        optimal_rec = engine_bridge.optimize_action(
            eligible_action_set=eligible_set,
            policy_valuation=valuation,
            calibrated_probability=score_res.calibrated_probability,
        )

        # Filter timeline events up to cutoff
        events = policy_events.get(pid, [])
        visible_events = [
            e for e in events
            if e.get("effective_time", "") <= as_of_str
        ]
        # Format summary for events
        formatted_events = []
        for e in visible_events:
            etype = e.get("event_type", "UNKNOWN")
            eff = e.get("effective_time", as_of_str)
            amt = e.get("amount") or e.get("payment_amount") or e.get("premium_amount")
            amt_str = f" (${amt:,.2f})" if amt else ""
            summary = f"{etype.replace('_', ' ').title()}{amt_str}"
            formatted_events.append({
                "event_type": etype,
                "effective_time": eff,
                "summary": summary,
                "amount": float(amt) if amt else None,
            })

        # Synthesize Brief
        case_brief = engine_bridge.synthesize_case_brief(
            policy_id=pid,
            as_of_date=as_of_str,
            scoring_result=score_res,
            eligible_action_set=eligible_set,
            optimal_rec=optimal_rec,
            policy_context=policy_ctx,
            timeline_events=formatted_events,
            annual_premium=annual_prem,
            monthly_premium=monthly_prem,
            coverage_amount=face_amt,
            total_premiums_paid=monthly_prem * max(1, tenure_days // 30),
        )

        # Initialize workflow case
        reconstructed = {
            "policy_id": pid,
            "status": status,
            "product_type": feat_map.get("product_type", "term_life"),
            "monthly_premium": monthly_prem,
            "payment_method": feat_map.get("payment_method", "direct_debit"),
            "tenure_days": tenure_days,
            "in_grace_period": is_grace,
            "days_past_due": days_grace,
        }
        wf_ctx = engine_bridge.get_or_create_workflow(
            policy_id=pid,
            as_of_date=as_of_str,
            reconstructed_state=reconstructed,
            scoring_result=score_res,
            eligible_action_set=eligible_set,
            case_brief=case_brief,
        )

        top_driver = score_res.top_risk_drivers[0] if score_res.top_risk_drivers else ("none", 0.0)

        items.append(
            TriagePolicyItem(
                policy_id=pid,
                as_of_date=as_of_str,
                product_type=str(feat_map.get("product_type", "term_life")),
                monthly_premium=monthly_prem,
                annual_premium=annual_prem,
                coverage_amount=face_amt,
                tenure_months=tenure_days // 30,
                in_grace_period=is_grace,
                days_in_grace=days_grace,
                billing_channel=str(feat_map.get("payment_method", "direct_debit")),
                status=status,
                risk_score=score_res.calibrated_probability,
                risk_tier=score_res.risk_tier,
                primary_risk_driver=top_driver[0],
                primary_risk_contribution=float(top_driver[1]),
                recommended_action=optimal_rec.recommended_action,
                net_utility=optimal_rec.expected_net_utility_usd,
                uplift_quadrant=optimal_rec.uplift_quadrant.value,
                scoring_result=score_res,
                eligible_action_set=eligible_set,
                optimal_recommendation=optimal_rec,
                case_brief=case_brief,
                case_id=wf_ctx.case_id,
                timeline_events=tuple(formatted_events),
            )
        )

    # Sort descending by Net Expected Utility (triage priority)
    items.sort(key=lambda x: x.net_utility, reverse=True)

    # Compute portfolio summary metrics
    tier_counts = {k: 0 for k in RISK_TIERS}
    action_counts: dict[str, int] = {}
    active_grace_count = 0
    total_val_at_risk = 0.0
    allocated_specialist_minutes = 0

    for item in items:
        tier_counts[item.risk_tier] = tier_counts.get(item.risk_tier, 0) + 1
        action_counts[item.recommended_action] = action_counts.get(item.recommended_action, 0) + 1
        if item.in_grace_period:
            active_grace_count += 1
        if "High" in item.risk_tier or "Critical" in item.risk_tier or "Tier 1" in item.risk_tier or "Tier 2" in item.risk_tier:
            total_val_at_risk += item.annual_premium

        # Specialist duration from metadata
        meta = ACTION_METADATA.get(item.recommended_action, {})
        allocated_specialist_minutes += meta.get("duration_minutes", 0)

    allocated_specialist_hours = allocated_specialist_minutes / 60.0
    cap_util = min(100.0, (allocated_specialist_hours / max_specialist_hours) * 100.0) if max_specialist_hours > 0 else 0.0

    summary = {
        "total_policies": len(items),
        "active_grace_count": active_grace_count,
        "tier_counts": tier_counts,
        "total_value_at_risk": total_val_at_risk,
        "allocated_specialist_hours": round(allocated_specialist_hours, 1),
        "max_specialist_hours": max_specialist_hours,
        "capacity_utilization_pct": round(cap_util, 1),
        "action_counts": action_counts,
    }

    return items, summary
