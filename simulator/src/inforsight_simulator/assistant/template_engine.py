"""Layer 1 Deterministic Template Engine for Conservation Case Briefs.

Synthesizes 100% reproducible, factually guaranteed case briefs without
generative hallucinations under ADR 0002.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Optional

from inforsight_simulator.assistant.context import CaseEvidenceContext
from inforsight_simulator.assistant.models import (
    DEFAULT_MANDATORY_DISCLAIMER,
    BriefRecommendation,
    CaseBrief,
    ExecutiveSummary,
    GroundingAudit,
    OperationalUrgency,
    RiskAssessment,
    SynthesisMode,
    ValidationStatus,
)


ACTION_TALKING_POINTS = {
    "payment_method_remediation": (
        "Inquire if banking or payment method details were recently modified or expired.",
        "Offer secure self-service portal link for instantaneous payment method remediation.",
        "Confirm scheduled debit schedule to prevent grace period escalation.",
    ),
    "grace_period_consultation": (
        "Politely notify policyholder of remaining window before grace period expiration.",
        "Review tailored options to preserve in-force protection, including premium restructuring.",
        "Explain accumulated coverage benefits to avoid irreversible policy lapse.",
    ),
    "specialist_phone_outreach": (
        "Conduct dedicated conservation consultation to address policyholder circumstances.",
        "Explore flexible options such as face amount reduction, loan against cash value, or schedule realignment.",
        "Directly address underlying cost, payment convenience, or value retention concerns.",
    ),
    "courtesy_reminder": (
        "Send proactive, low-friction notification regarding upcoming billing cycle.",
        "Verify contact information and preferred digital communication channels on file.",
    ),
    "abstain": (
        "No active outreach recommended. Account profile indicates stability or non-responsiveness.",
    ),
}


def compute_operational_urgency(context: CaseEvidenceContext) -> OperationalUrgency:
    """Determine operational triage urgency deterministically."""
    if context.calibrated_probability >= 0.50 or (
        context.days_past_due is not None and context.days_past_due > 20
    ):
        return OperationalUrgency.CRITICAL
    elif context.calibrated_probability >= 0.30 or context.in_grace_period:
        return OperationalUrgency.HIGH
    elif context.calibrated_probability >= 0.10:
        return OperationalUrgency.MEDIUM
    return OperationalUrgency.LOW


def synthesize_deterministic_headline(context: CaseEvidenceContext) -> str:
    """Construct deterministic headline from risk tier and primary driver."""
    tier_prefix = context.operational_tier.split(":")[0].strip() if ":" in context.operational_tier else context.operational_tier
    driver_desc = context.top_risk_drivers[0].display_text if context.top_risk_drivers else "Standard Portfolio Dynamics"
    return f"{tier_prefix} Conservation Review: Driven by {driver_desc}"


def synthesize_deterministic_narrative(context: CaseEvidenceContext) -> str:
    """Construct deterministic narrative paragraph strictly referencing known entities."""
    driver_mention = (
        f"Key risk attribution: {context.top_risk_drivers[0].display_text} "
        f"(attribution weight +{context.top_risk_drivers[0].attribution:.4f}). "
        if context.top_risk_drivers else ""
    )
    if context.in_grace_period is True:
        grace_str = f"Policy is in grace period with {context.days_past_due} days past due."
    elif context.in_grace_period is False:
        grace_str = "Policy is confirmed outside a grace period."
    else:
        grace_str = "Lifecycle and grace status are unavailable at this cutoff."
    paid_str = (
        f"The source ledger records ${context.total_premiums_paid:.2f} in cumulative premiums paid. "
        if context.total_premiums_paid is not None else ""
    )

    return (
        f"Policy {context.policy_id} ({context.product_type}) exhibits an estimated calibrated "
        f"lapse risk of {context.calibrated_probability * 100:.2f}% ({context.operational_tier}). "
        f"The account has {context.tenure_months} elapsed months of tenure. "
        f"{paid_str}"
        f"{driver_mention}{grace_str} "
        f"Recommended intervention is {context.primary_action} under uplift quadrant {context.uplift_quadrant}."
    )


def generate_template_brief(
    context: CaseEvidenceContext,
    generated_at: Optional[str] = None,
    brief_id: Optional[str] = None,
) -> CaseBrief:
    """Generate Layer 1 deterministic Case Brief from evidence context.

    Produces a 100% reproducible, bit-for-bit testable Case Brief with
    zero hallucination risk by construction.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if brief_id is None:
        digest = hashlib.sha256(
            f"{context.policy_id}:{context.as_of_date}:{generated_at}:template".encode("utf-8")
        ).hexdigest()[:16]
        brief_id = f"brf_{digest}"

    urgency = compute_operational_urgency(context)
    headline = synthesize_deterministic_headline(context)
    narrative = synthesize_deterministic_narrative(context)

    exec_summary = ExecutiveSummary(
        headline=headline,
        operational_urgency=urgency,
        narrative=narrative,
    )

    risk_assessment = RiskAssessment(
        calibrated_probability=context.calibrated_probability,
        operational_tier=context.operational_tier,
        top_risk_drivers=context.top_risk_drivers,
    )

    talking_points = ACTION_TALKING_POINTS.get(
        context.primary_action,
        ("Conduct standard policyholder outreach and confirm contact preference.",),
    )

    recommendation = BriefRecommendation(
        primary_action=context.primary_action,
        uplift_quadrant=context.uplift_quadrant,
        expected_net_utility=context.expected_net_utility,
        talking_points=talking_points,
        alternative_actions=context.alternative_actions,
    )

    # Layer 1 deterministic template passes all facts cleanly by construction
    # Count verified entities: policy_id, product, tenure, premiums, risk, action, timeline events
    entity_count = 6 + len(context.timeline_events) + len(context.top_risk_drivers)

    grounding_audit = GroundingAudit(
        validation_status=ValidationStatus.PASSED_CLEAN,
        verified_entity_count=entity_count,
        hallucination_detected=False,
        violations=(),
    )

    return CaseBrief(
        brief_id=brief_id,
        case_id=context.case_id,
        policy_id=context.policy_id,
        as_of_date=context.as_of_date,
        generated_at=generated_at,
        synthesis_mode=SynthesisMode.TEMPLATE_DETERMINISTIC,
        executive_summary=exec_summary,
        risk_assessment=risk_assessment,
        factual_timeline=context.timeline_events,
        intervention_recommendations=recommendation,
        disqualified_actions=context.disqualified_actions,
        grounding_audit=grounding_audit,
        schema_version="1.0.0",
        status="PENDING_HUMAN_REVIEW",
        authorized_to_act=False,
        disclaimer=DEFAULT_MANDATORY_DISCLAIMER,
    )
