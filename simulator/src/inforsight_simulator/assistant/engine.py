"""Case Intelligence Assistant Orchestrator.

Coordinates Layer 1 deterministic template synthesis, Layer 2 generative narrative
augmentation, Grounding Guard inspection, fail-closed fallback, and ADR 0002
boundary enforcement.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Optional

from inforsight_simulator.assistant.context import CaseEvidenceContext
from inforsight_simulator.assistant.grounding import GroundingGuard
from inforsight_simulator.assistant.llm_layer import (
    DeterministicMockNarrativeProvider,
    NarrativeProvider,
)
from inforsight_simulator.assistant.models import (
    DEFAULT_MANDATORY_DISCLAIMER,
    BriefRecommendation,
    CaseBrief,
    ExecutiveSummary,
    GroundingAudit,
    RiskAssessment,
    SynthesisMode,
    ValidationStatus,
)
from inforsight_simulator.assistant.template_engine import (
    compute_operational_urgency,
    generate_template_brief,
)


class CaseIntelligenceAssistant:
    """Bounded assistant synthesizing structured, fact-grounded Case Briefs."""

    def __init__(
        self,
        mode: SynthesisMode = SynthesisMode.TEMPLATE_DETERMINISTIC,
        narrative_provider: Optional[NarrativeProvider] = None,
        grounding_guard: Optional[GroundingGuard] = None,
    ) -> None:
        self.mode = mode
        self.narrative_provider = narrative_provider or DeterministicMockNarrativeProvider()
        self.grounding_guard = grounding_guard or GroundingGuard()

    def generate_brief(
        self,
        context: CaseEvidenceContext,
        generated_at: Optional[str] = None,
        brief_id: Optional[str] = None,
    ) -> CaseBrief:
        """Synthesize a Conservation Case Brief adhering strictly to ADR 0002."""
        if generated_at is None:
            generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if brief_id is None:
            mode_tag = "tmpl" if self.mode == SynthesisMode.TEMPLATE_DETERMINISTIC else "llm"
            digest = hashlib.sha256(
                f"{context.policy_id}:{context.as_of_date}:{generated_at}:{mode_tag}".encode("utf-8")
            ).hexdigest()[:16]
            brief_id = f"brf_{digest}"

        # ---------------------------------------------------------------------
        # Mode 1: Pure Deterministic Template (Zero Hallucination by Construction)
        # ---------------------------------------------------------------------
        if self.mode == SynthesisMode.TEMPLATE_DETERMINISTIC:
            return generate_template_brief(
                context=context,
                generated_at=generated_at,
                brief_id=brief_id,
            )

        # ---------------------------------------------------------------------
        # Mode 2: Generative Narrative with Automated Grounding Guard
        # ---------------------------------------------------------------------
        candidate_narrative = self.narrative_provider.generate_narrative(context)
        validated_narrative, audit = self.grounding_guard.validate(
            candidate_narrative=candidate_narrative,
            context=context,
        )

        # Fail-closed fallback: If critical grounding violations occurred, fall back to Layer 1
        if audit.validation_status == ValidationStatus.FALLBACK_TO_TEMPLATE:
            template_brief = generate_template_brief(
                context=context,
                generated_at=generated_at,
                brief_id=brief_id,
            )
            # Retain the intercepted violation audit log for transparency
            return CaseBrief(
                brief_id=template_brief.brief_id,
                case_id=template_brief.case_id,
                policy_id=template_brief.policy_id,
                as_of_date=template_brief.as_of_date,
                generated_at=template_brief.generated_at,
                synthesis_mode=SynthesisMode.LLM_AUGMENTED_GROUNDED,
                executive_summary=template_brief.executive_summary,
                risk_assessment=template_brief.risk_assessment,
                factual_timeline=template_brief.factual_timeline,
                intervention_recommendations=template_brief.intervention_recommendations,
                disqualified_actions=template_brief.disqualified_actions,
                grounding_audit=audit,
                schema_version=template_brief.schema_version,
                status="PENDING_HUMAN_REVIEW",
                authorized_to_act=False,
                disclaimer=DEFAULT_MANDATORY_DISCLAIMER,
            )

        # Assemble the validated/redacted brief
        urgency = compute_operational_urgency(context)
        exec_summary = ExecutiveSummary(
            headline=validated_narrative["headline"],
            operational_urgency=urgency,
            narrative=validated_narrative["narrative"],
        )

        risk_assessment = RiskAssessment(
            calibrated_probability=context.calibrated_probability,
            operational_tier=context.operational_tier,
            top_risk_drivers=context.top_risk_drivers,
        )

        recommendation = BriefRecommendation(
            primary_action=context.primary_action,
            uplift_quadrant=context.uplift_quadrant,
            expected_net_utility=context.expected_net_utility,
            talking_points=tuple(validated_narrative.get("talking_points", ())),
            alternative_actions=context.alternative_actions,
        )

        return CaseBrief(
            brief_id=brief_id,
            case_id=context.case_id,
            policy_id=context.policy_id,
            as_of_date=context.as_of_date,
            generated_at=generated_at,
            synthesis_mode=SynthesisMode.LLM_AUGMENTED_GROUNDED,
            executive_summary=exec_summary,
            risk_assessment=risk_assessment,
            factual_timeline=context.timeline_events,
            intervention_recommendations=recommendation,
            disqualified_actions=context.disqualified_actions,
            grounding_audit=audit,
            schema_version="1.0.0",
            status="PENDING_HUMAN_REVIEW",
            authorized_to_act=False,
            disclaimer=DEFAULT_MANDATORY_DISCLAIMER,
        )

