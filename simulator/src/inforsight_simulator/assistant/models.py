"""Domain models for Phase 3.05 Bounded Case Intelligence Assistant.

Defines immutable data structures representing structured, fact-grounded
Conservation Case Briefs under ADR 0002.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from typing import Any, Optional


DEFAULT_MANDATORY_DISCLAIMER = (
    "ADVISORY ONLY: This brief is generated for decision support under ADR 0002. "
    "Automated execution of conservation outreach is prohibited without prior human "
    "specialist authorization."
)


class SynthesisMode(str, Enum):
    """Synthesis mode used to produce the case brief."""
    TEMPLATE_DETERMINISTIC = "TEMPLATE_DETERMINISTIC"
    LLM_AUGMENTED_GROUNDED = "LLM_AUGMENTED_GROUNDED"


class OperationalUrgency(str, Enum):
    """Urgency level for specialist review triage."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ValidationStatus(str, Enum):
    """Grounding guard post-processing outcome."""
    PASSED_CLEAN = "PASSED_CLEAN"
    PASSED_WITH_REDACTION = "PASSED_WITH_REDACTION"
    FALLBACK_TO_TEMPLATE = "FALLBACK_TO_TEMPLATE"


@dataclass(frozen=True)
class RiskDriver:
    """Individual feature attribution driver."""
    feature_name: str
    attribution: float
    display_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "attribution": float(self.attribution),
            "display_text": self.display_text,
        }


@dataclass(frozen=True)
class RiskAssessment:
    """Calibrated risk probability and key attributions."""
    calibrated_probability: float
    operational_tier: str
    top_risk_drivers: tuple[RiskDriver, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "calibrated_probability": round(float(self.calibrated_probability), 4),
            "operational_tier": self.operational_tier,
            "top_risk_drivers": [d.to_dict() for d in self.top_risk_drivers],
        }


@dataclass(frozen=True)
class ExecutiveSummary:
    """High-level summary of policy standing, risk factors, and urgency."""
    headline: str
    operational_urgency: OperationalUrgency
    narrative: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline": self.headline,
            "operational_urgency": self.operational_urgency.value,
            "narrative": self.narrative,
        }


@dataclass(frozen=True)
class FactualTimelineEvent:
    """Single chronological milestone up to observation cutoff."""
    occurred_at: str
    event_type: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurred_at": self.occurred_at,
            "event_type": self.event_type,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class BriefRecommendation:
    """Intervention recommendations from eligibility and optimization."""
    primary_action: str
    uplift_quadrant: str
    expected_net_utility: float
    talking_points: tuple[str, ...]
    alternative_actions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_action": self.primary_action,
            "uplift_quadrant": self.uplift_quadrant,
            "expected_net_utility": round(float(self.expected_net_utility), 2),
            "talking_points": list(self.talking_points),
            "alternative_actions": list(self.alternative_actions),
        }


@dataclass(frozen=True)
class DisqualifiedActionSummary:
    """Action excluded by deterministic rules with explicit reason."""
    action_id: str
    reason_code: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "reason_code": self.reason_code,
            "description": self.description,
        }


@dataclass(frozen=True)
class GroundingAudit:
    """Audit metadata from automated post-processing validation."""
    validation_status: ValidationStatus
    verified_entity_count: int
    hallucination_detected: bool
    violations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "validation_status": self.validation_status.value,
            "verified_entity_count": int(self.verified_entity_count),
            "hallucination_detected": bool(self.hallucination_detected),
            "violations": list(self.violations),
        }


@dataclass(frozen=True)
class CaseBrief:
    """Master record for a Conservation Case Brief under ADR 0002."""
    brief_id: str
    case_id: str
    policy_id: str
    as_of_date: str
    generated_at: str
    synthesis_mode: SynthesisMode
    executive_summary: ExecutiveSummary
    risk_assessment: RiskAssessment
    factual_timeline: tuple[FactualTimelineEvent, ...]
    intervention_recommendations: BriefRecommendation
    disqualified_actions: tuple[DisqualifiedActionSummary, ...]
    grounding_audit: GroundingAudit
    schema_version: str = "1.0.0"
    status: str = "PENDING_HUMAN_REVIEW"
    authorized_to_act: bool = False
    disclaimer: str = DEFAULT_MANDATORY_DISCLAIMER

    def __post_init__(self) -> None:
        if self.status != "PENDING_HUMAN_REVIEW":
            raise ValueError(
                f"CaseBrief status must be PENDING_HUMAN_REVIEW under ADR 0002, got '{self.status}'"
            )
        if self.authorized_to_act is not False:
            raise ValueError(
                f"CaseBrief authorized_to_act must strictly be False under ADR 0002, got {self.authorized_to_act}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert brief to JSON Schema conforming dictionary."""
        return {
            "schema_version": self.schema_version,
            "brief_id": self.brief_id,
            "case_id": self.case_id,
            "policy_id": self.policy_id,
            "as_of_date": self.as_of_date,
            "generated_at": self.generated_at,
            "synthesis_mode": self.synthesis_mode.value,
            "status": self.status,
            "authorized_to_act": self.authorized_to_act,
            "executive_summary": self.executive_summary.to_dict(),
            "risk_assessment": self.risk_assessment.to_dict(),
            "factual_timeline": [e.to_dict() for e in self.factual_timeline],
            "intervention_recommendations": self.intervention_recommendations.to_dict(),
            "disqualified_actions": [d.to_dict() for d in self.disqualified_actions],
            "grounding_audit": self.grounding_audit.to_dict(),
            "disclaimer": self.disclaimer,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize brief to JSON formatted string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """Render brief as structured Markdown for specialist review."""
        lines: list[str] = [
            f"# Conservation Case Brief: {self.policy_id}",
            "",
            "> [!IMPORTANT]",
            f"> **STATUS: {self.status}**",
            "> *ADVISORY ONLY — Authorized to act: False*",
            f"> {self.disclaimer}",
            "",
            "## Case Metadata",
            "",
            f"- **Brief ID:** `{self.brief_id}`",
            f"- **Case ID:** `{self.case_id}`",
            f"- **Observation Cutoff (as-of):** `{self.as_of_date}`",
            f"- **Generated At:** `{self.generated_at}`",
            f"- **Synthesis Mode:** `{self.synthesis_mode.value}`",
            f"- **Operational Urgency:** **{self.executive_summary.operational_urgency.value}**",
            "",
            "## 1. Executive Summary",
            "",
            f"### {self.executive_summary.headline}",
            "",
            f"{self.executive_summary.narrative}",
            "",
            "## 2. Risk Assessment & Explainability",
            "",
            f"- **Calibrated Lapse Probability:** `{self.risk_assessment.calibrated_probability * 100:.2f}%`",
            f"- **Operational Risk Tier:** **{self.risk_assessment.operational_tier}**",
            "",
            "### Top Attributed Risk Drivers",
            "",
            "| Feature | Attribution | Explanation |",
            "| :--- | :--- | :--- |",
        ]

        if self.risk_assessment.top_risk_drivers:
            for d in self.risk_assessment.top_risk_drivers:
                lines.append(f"| `{d.feature_name}` | `+{d.attribution:.4f}` | {d.display_text} |")
        else:
            lines.append("| *None* | `0.0000` | No significant positive risk drivers identified |")

        lines.extend([
            "",
            "## 3. Factual Timeline (Up to Cutoff Date)",
            "",
        ])

        if self.factual_timeline:
            for event in self.factual_timeline:
                lines.append(f"- **`{event.occurred_at}`** [{event.event_type}]: {event.summary}")
        else:
            lines.append("- *No prior historical events recorded prior to cutoff date.*")

        lines.extend([
            "",
            "## 4. Recommended Intervention Strategy",
            "",
            f"- **Primary Action:** `{self.intervention_recommendations.primary_action}`",
            f"- **Uplift Quadrant:** **{self.intervention_recommendations.uplift_quadrant}**",
            f"- **Expected Net Utility:** `+${self.intervention_recommendations.expected_net_utility:.2f}`",
            "",
            "### Specialist Talking Points",
            "",
        ])

        for pt in self.intervention_recommendations.talking_points:
            lines.append(f"- {pt}")

        if self.intervention_recommendations.alternative_actions:
            lines.extend([
                "",
                "### Alternative Eligible Actions",
                "",
            ])
            for alt in self.intervention_recommendations.alternative_actions:
                lines.append(f"- `{alt}`")

        lines.extend([
            "",
            "## 5. Disqualified Actions & Statutory Restrictions",
            "",
        ])

        if self.disqualified_actions:
            lines.extend([
                "| Action | Reason Code | Compliance Rationale |",
                "| :--- | :--- | :--- |",
            ])
            for d in self.disqualified_actions:
                lines.append(f"| `{d.action_id}` | `{d.reason_code}` | {d.description} |")
        else:
            lines.append("- *All catalog actions are currently permissible.*")

        lines.extend([
            "",
            "## 6. Grounding & Verification Audit",
            "",
            f"- **Validation Status:** `{self.grounding_audit.validation_status.value}`",
            f"- **Verified Entity Facts:** `{self.grounding_audit.verified_entity_count}`",
            f"- **Hallucination Intercepted:** `{self.grounding_audit.hallucination_detected}`",
        ])

        if self.grounding_audit.violations:
            lines.extend([
                "",
                "### Intercepted Violations Log",
                "",
            ])
            for v in self.grounding_audit.violations:
                lines.append(f"- [REDACTED/BLOCKED]: {v}")

        return "\n".join(lines) + "\n"

