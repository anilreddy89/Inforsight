"""Deterministic synthetic demonstration cohort loader for the conservation dashboard."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from inforsight_simulator.assistant import CaseBrief
from inforsight_simulator.bundle import ScoringResult
from inforsight_simulator.domain_snapshot import DomainSnapshot, reconstruct_domain_snapshot
from inforsight_simulator.economics import USD_MICROS_PER_USD
from inforsight_simulator.optimization import OptimalRecommendation, PolicyValuation
from inforsight_simulator.rules import EligibleActionSet
from inforsight_simulator.semantic_catalog import PREPROCESSING_PROFILE_ID
from inforsight_simulator.v6_corpus import V6CorpusConfig, generate_v6_corpus
from inforsight_simulator.v6_evaluation import _feature_map

from dashboard.config import DEFAULT_BUDGET, DEFAULT_MAX_SPECIALIST_HOURS, RISK_TIERS
from dashboard.services.engine_bridge import EngineBridge


@dataclass(frozen=True)
class TriagePolicyItem:
    """Consolidated point-in-time record for an individual policy in the triage queue."""

    policy_id: str
    snapshot: DomainSnapshot
    as_of_date: str
    product_type: str
    monthly_premium: float
    annual_premium: float
    coverage_amount: float | None
    tenure_months: int
    in_grace_period: bool | None
    days_in_grace: int | None
    billing_channel: str
    status: str
    risk_score: float
    risk_tier_id: str
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

    prepared: list[dict[str, Any]] = []

    for pid, obs in latest_obs_by_policy.items():
        feat_map = _feature_map(obs)
        # Parse timestamps and parameters
        as_of_dt = obs.as_of if isinstance(obs.as_of, datetime) else datetime.fromisoformat(str(obs.as_of))
        if as_of_dt.tzinfo is None:
            as_of_dt = as_of_dt.replace(tzinfo=timezone.utc)
        as_of_str = as_of_dt.isoformat().replace("+00:00", "Z")

        events = policy_events.get(pid, [])
        snapshot = reconstruct_domain_snapshot(
            events,
            policy_id=pid,
            as_of=as_of_dt,
            source_profile="v6-policy-events/6.0.0",
            catalog=engine_bridge.semantic_catalog,
        )
        if snapshot is None:
            continue
        score_res = engine_bridge.score_observation(
            feat_map,
            preprocessing_profile=PREPROCESSING_PROFILE_ID,
            snapshot=snapshot,
            policy_id=pid,
            as_of=as_of_dt,
        )
        risk_tier_id = engine_bridge.semantic_catalog.map_risk_tier(
            score_res.risk_tier, adapter_profile="historical-bundle-display/1.0.0"
        )
        eligible_set = engine_bridge.evaluate_snapshot(snapshot)

        # Valuation
        annual_prem = snapshot.annual_premium_cents / 100
        monthly_prem = annual_prem / 12
        face_amt = None
        valuation = PolicyValuation(
            policy_id=pid,
            annual_premium_usd=annual_prem,
            customer_lifetime_value_usd=annual_prem,  # ignored compatibility field
            snapshot_id=snapshot.snapshot_id,
            snapshot_version=snapshot.snapshot_version,
            catalog_sha256=snapshot.catalog_sha256,
        )
        optimal_rec = engine_bridge.optimize_action(
            eligible_action_set=eligible_set,
            policy_valuation=valuation,
            calibrated_probability=score_res.calibrated_probability,
        )

        visible_ids = {item.event_id for item in snapshot.provenance}
        visible_events = [e for e in events if e.get("event_id") in visible_ids]
        # Format summary for events
        formatted_events = []
        for e in visible_events:
            etype = e.get("event_type", "UNKNOWN")
            eff = e.get("effective_at", as_of_str)
            amt = e.get("amount") or e.get("payment_amount") or e.get("premium_amount")
            amt_str = f" (${amt:,.2f})" if amt else ""
            summary = f"{etype.replace('_', ' ').title()}{amt_str}"
            formatted_events.append({
                "event_type": etype,
                "effective_time": eff,
                "summary": summary,
                "amount": float(amt) if amt else None,
            })

        prepared.append(
            {
                "pid": pid,
                "snapshot": snapshot,
                "as_of_dt": as_of_dt,
                "as_of_str": as_of_str,
                "score_res": score_res,
                "risk_tier_id": risk_tier_id,
                "eligible_set": eligible_set,
                "annual_prem": annual_prem,
                "monthly_prem": monthly_prem,
                "face_amt": face_amt,
                "unconstrained_rec": optimal_rec,
                "formatted_events": formatted_events,
            }
        )

    if prepared:
        cutoff = max(entry["as_of_dt"] for entry in prepared)
    else:
        cutoff = datetime.now(timezone.utc)
    # Terminal decisions are already represented by current reservations and
    # cannot be selected again on refresh.
    for entry in prepared:
        existing = engine_bridge.workflow_service.get_case(
            engine_bridge.workflow_case_id(entry["pid"], entry["as_of_str"])
        )
        if existing and existing.state_machine.current_state.value in {
            "EXECUTED", "DISMISSED", "RESOLVED"
        }:
            rec = entry["unconstrained_rec"]
            abstain = rec.action_utilities["abstain"]
            entry["unconstrained_rec"] = replace(
                rec,
                recommended_action="abstain",
                expected_net_utility_usd=0.0,
                uplift_quadrant=abstain.uplift_quadrant,
                rank_score=0.0,
            )
    capacity_state = engine_bridge.workflow_service.capacity_snapshot()
    available_budget_micros = min(
        int(DEFAULT_BUDGET * USD_MICROS_PER_USD),
        capacity_state["remaining_cost_usd_micros"],
    )
    available_personnel_seconds = min(
        int(max_specialist_hours * 3_600), capacity_state["remaining_seconds"]
    )
    allocation = engine_bridge.allocate_portfolio(
        [entry["unconstrained_rec"] for entry in prepared],
        budget_capacity_usd_micros=available_budget_micros,
        personnel_capacity_seconds=available_personnel_seconds,
        as_of=cutoff,
        portfolio_id=f"dashboard-v6-{seed}-{actual_count}",
    )
    selected_by_policy = {rec.policy_id: rec for rec in allocation.recommendations}
    allocation_binding = engine_bridge.allocation_binding(allocation.allocation_id)
    strategy_comparison = engine_bridge.compare_portfolio_strategies(
        [entry["unconstrained_rec"] for entry in prepared],
        risk_scores={entry["pid"]: entry["score_res"].calibrated_probability for entry in prepared},
        budget_capacity_usd_micros=available_budget_micros,
        personnel_capacity_seconds=available_personnel_seconds,
        as_of=cutoff,
        portfolio_id=f"dashboard-v6-{seed}-{actual_count}",
    )
    items: list[TriagePolicyItem] = []

    # Allocation is complete before any brief, recommendation case, or summary is emitted.
    for entry in prepared:
        pid = entry["pid"]
        snapshot = entry["snapshot"]
        as_of_str = entry["as_of_str"]
        score_res = entry["score_res"]
        risk_tier_id = entry["risk_tier_id"]
        eligible_set = entry["eligible_set"]
        annual_prem = entry["annual_prem"]
        monthly_prem = entry["monthly_prem"]
        face_amt = entry["face_amt"]
        optimal_rec = selected_by_policy[pid]
        formatted_events = entry["formatted_events"]

        # Synthesize the brief directly from reconstructed evidence. Unknown source
        # facts remain unknown instead of being coerced into permissive defaults.
        case_brief = engine_bridge.synthesize_case_brief(
            policy_id=pid,
            as_of_date=as_of_str,
            scoring_result=score_res,
            eligible_action_set=eligible_set,
            optimal_rec=optimal_rec,
            policy_context=None,
            timeline_events=formatted_events,
            annual_premium=annual_prem,
            monthly_premium=monthly_prem,
            coverage_amount=face_amt,
            total_premiums_paid=None,
            snapshot=snapshot,
        )

        # Initialize workflow case
        reconstructed = {
            "policy_id": pid,
            "snapshot_id": snapshot.snapshot_id,
            "as_of": snapshot.as_of,
            "status": snapshot.status,
            "product_type": snapshot.product_type,
            "monthly_premium": monthly_prem,
            "tenure_days": snapshot.tenure_days,
            "in_grace_period": snapshot.in_grace_period,
            "days_past_due": snapshot.days_past_due,
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
                snapshot=snapshot,
                as_of_date=as_of_str,
                product_type=snapshot.product_type,
                monthly_premium=monthly_prem,
                annual_premium=annual_prem,
                coverage_amount=face_amt,
                tenure_months=snapshot.tenure_days // 30,
                in_grace_period=snapshot.in_grace_period,
                days_in_grace=snapshot.days_in_grace,
                billing_channel="unknown",
                status=snapshot.status,
                risk_score=score_res.calibrated_probability,
                risk_tier_id=risk_tier_id,
                risk_tier=engine_bridge.semantic_catalog.risk_tier_display(risk_tier_id),
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

    for item in items:
        tier_counts[item.risk_tier] = tier_counts.get(item.risk_tier, 0) + 1
        action_counts[item.recommended_action] = action_counts.get(item.recommended_action, 0) + 1
        if item.in_grace_period is True:
            active_grace_count += 1
        if engine_bridge.semantic_catalog.risk_tier_rank(item.risk_tier_id) >= 3:
            total_val_at_risk += item.annual_premium

    reserved_personnel_seconds = (
        capacity_state["capacity_seconds"] - capacity_state["remaining_seconds"]
    )
    reserved_budget_micros = (
        capacity_state["capacity_cost_usd_micros"]
        - capacity_state["remaining_cost_usd_micros"]
    )
    total_personnel_used_seconds = reserved_personnel_seconds + allocation.personnel_used_seconds
    total_budget_used_micros = reserved_budget_micros + allocation.budget_used_usd_micros
    allocated_specialist_hours = total_personnel_used_seconds / 3_600
    cap_util = (
        total_personnel_used_seconds / capacity_state["capacity_seconds"] * 100
        if capacity_state["capacity_seconds"]
        else 0.0
    )

    summary = {
        "total_policies": len(items),
        "active_grace_count": active_grace_count,
        "tier_counts": tier_counts,
        "total_value_at_risk": total_val_at_risk,
        "allocated_specialist_hours": round(allocated_specialist_hours, 1),
        "max_specialist_hours": max_specialist_hours,
        "capacity_utilization_pct": round(cap_util, 1),
        "action_counts": action_counts,
        "allocation_id": allocation.allocation_id,
        "allocator_version": allocation.allocator_version,
        "allocation_binding_sha256": allocation_binding["binding_sha256"],
        "capacity_version": allocation_binding["capacity_version"],
        "reservation_version": allocation_binding["reservation_version"],
        "budget_capacity_usd_micros": capacity_state["capacity_cost_usd_micros"],
        "budget_used_usd_micros": total_budget_used_micros,
        "budget_available_usd_micros": capacity_state["capacity_cost_usd_micros"] - total_budget_used_micros,
        "budget_overflow_usd_micros": 0,
        "personnel_capacity_seconds": capacity_state["capacity_seconds"],
        "personnel_used_seconds": total_personnel_used_seconds,
        "personnel_available_seconds": capacity_state["capacity_seconds"] - total_personnel_used_seconds,
        "personnel_overflow_seconds": 0,
        "modeled_expected_net_value_usd_micros": allocation.objective_usd_micros,
        "strategy_comparison": strategy_comparison,
    }

    return items, summary
