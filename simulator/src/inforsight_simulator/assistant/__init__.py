"""Phase 3.05 Bounded Case Intelligence Assistant package.

Provides dual-layer Case Brief synthesis (deterministic template foundation
and grounded generative augmentation) under ADR 0002.
"""

from __future__ import annotations

from inforsight_simulator.assistant.context import CaseEvidenceContext
from inforsight_simulator.assistant.engine import CaseIntelligenceAssistant
from inforsight_simulator.assistant.grounding import GroundingGuard
from inforsight_simulator.assistant.llm_layer import (
    DeterministicMockNarrativeProvider,
    InjectableMockNarrativeProvider,
    NarrativeProvider,
    PromptBuilder,
)
from inforsight_simulator.assistant.models import (
    DEFAULT_MANDATORY_DISCLAIMER,
    BriefRecommendation,
    CaseBrief,
    DisqualifiedActionSummary,
    ExecutiveSummary,
    FactualTimelineEvent,
    GroundingAudit,
    OperationalUrgency,
    RiskAssessment,
    RiskDriver,
    SynthesisMode,
    ValidationStatus,
)
from inforsight_simulator.assistant.template_engine import generate_template_brief

__all__ = [
    "BriefRecommendation",
    "CaseBrief",
    "CaseEvidenceContext",
    "CaseIntelligenceAssistant",
    "DEFAULT_MANDATORY_DISCLAIMER",
    "DeterministicMockNarrativeProvider",
    "DisqualifiedActionSummary",
    "ExecutiveSummary",
    "FactualTimelineEvent",
    "GroundingAudit",
    "GroundingGuard",
    "InjectableMockNarrativeProvider",
    "NarrativeProvider",
    "OperationalUrgency",
    "PromptBuilder",
    "RiskAssessment",
    "RiskDriver",
    "SynthesisMode",
    "ValidationStatus",
    "generate_template_brief",
]

