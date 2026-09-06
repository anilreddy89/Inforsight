"""Layer 2 Grounded Narrative Generation and Provider Abstraction.

Provides generative narrative synthesis with pluggable adapters and an offline
deterministic mock provider for CI testing without network dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from inforsight_simulator.assistant.context import CaseEvidenceContext


class NarrativeProvider(ABC):
    """Abstract interface for generative narrative augmentation."""

    @abstractmethod
    def generate_narrative(self, context: CaseEvidenceContext) -> dict[str, Any]:
        """Synthesize candidate narrative dictionary.

        Expected return structure:
        {
            "headline": str,
            "narrative": str,
            "talking_points": list[str]
        }
        """
        pass


class DeterministicMockNarrativeProvider(NarrativeProvider):
    """Default local provider generating natural, empathetic narratives offline.

    Generates conversational narratives that strictly cite verified entities
    from the evidence context without external API calls.
    """

    def generate_narrative(self, context: CaseEvidenceContext) -> dict[str, Any]:
        tier_str = context.operational_tier.split(":")[0].strip() if ":" in context.operational_tier else context.operational_tier
        tenure_yrs = context.tenure_months // 12
        tenure_phrase = f"{tenure_yrs} years" if tenure_yrs >= 2 else f"{context.tenure_months} months"

        headline = f"{tier_str} Retention Opportunity: Valued Policyholder with {tenure_phrase} Relationship"

        # Construct empathetic, grounded narrative
        driver_text = (
            f"Analysis reveals that the primary factor elevating lapse likelihood is "
            f"{context.top_risk_drivers[0].display_text.lower()}."
            if context.top_risk_drivers else "Lapse risk reflects general portfolio dynamics."
        )

        grace_text = (
            f"The account entered grace period with {context.days_past_due} days past due, "
            f"requiring prompt attention to safeguard coverage."
            if context.in_grace_period else
            "The policy remains active with no current payment delinquency."
        )

        narrative = (
            f"Policy {context.policy_id} represents a significant customer relationship with "
            f"{tenure_phrase} of continuous tenure and ${context.total_premiums_paid:.2f} in paid premiums. "
            f"Current calibrated risk is estimated at {context.calibrated_probability * 100:.2f}% ({context.operational_tier}). "
            f"{driver_text} {grace_text} "
            f"Intervention should proceed with empathy, focusing on {context.primary_action.replace('_', ' ')}."
        )

        # Context-aware conversational talking points
        talking_points = [
            f"Acknowledge and thank the policyholder for their {tenure_phrase} partnership.",
            f"Confirm that policy {context.policy_id} ({context.product_type}) provides critical family protection of ${context.coverage_amount:.2f}.",
            f"Recommend proceeding with {context.primary_action.replace('_', ' ')} to resolve current account friction.",
        ]

        return {
            "headline": headline,
            "narrative": narrative,
            "talking_points": talking_points,
        }


class InjectableMockNarrativeProvider(NarrativeProvider):
    """Provider allowing direct injection of candidate payloads for testing.

    Used specifically by Grounding Guard unit tests to inject synthetic
    hallucinations, disqualified action references, or false dates.
    """

    def __init__(self, response_payload: dict[str, Any]) -> None:
        self.response_payload = response_payload

    def generate_narrative(self, context: CaseEvidenceContext) -> dict[str, Any]:
        return dict(self.response_payload)


class PromptBuilder:
    """Utility to build grounded system and user prompts for external LLM adapters."""

    @staticmethod
    def build_system_prompt() -> str:
        return (
            "You are the Inforsight Conservation Case Intelligence Assistant, a specialized "
            "decision-support copilot for licensed life insurance retention specialists. "
            "Your role is to synthesize factual, empathetic, and clear briefing narratives.\n"
            "STRICT COMPLIANCE INVARIANTS:\n"
            "1. You operate under ADR 0002. You provide perceptual advice only and have ZERO authority to act.\n"
            "2. All factual claims (dates, dollar amounts, tenures, product types) MUST be strictly grounded in the provided evidence.\n"
            "3. You must NEVER recommend or suggest any action that is marked as DISQUALIFIED.\n"
            "4. Return only valid JSON with 'headline', 'narrative', and 'talking_points'."
        )

    @staticmethod
    def build_user_prompt(context: CaseEvidenceContext) -> str:
        disqualified_list = [
            f"- {d.action_id} (Reason: {d.reason_code})" for d in context.disqualified_actions
        ]
        disqualified_str = "\n".join(disqualified_list) if disqualified_list else "None"

        return (
            f"EVIDENCE CONTEXT:\n"
            f"- Policy ID: {context.policy_id}\n"
            f"- As-of Date: {context.as_of_date}\n"
            f"- Product Type: {context.product_type}\n"
            f"- Tenure: {context.tenure_months} months\n"
            f"- Monthly Premium: ${context.monthly_premium:.2f}\n"
            f"- Total Premiums Paid: ${context.total_premiums_paid:.2f}\n"
            f"- Coverage Amount: ${context.coverage_amount:.2f}\n"
            f"- In Grace Period: {context.in_grace_period} (Days past due: {context.days_past_due})\n"
            f"- Calibrated Lapse Risk: {context.calibrated_probability * 100:.2f}% ({context.operational_tier})\n"
            f"- Primary Action Recommended: {context.primary_action} (Uplift Quadrant: {context.uplift_quadrant})\n"
            f"- DISQUALIFIED ACTIONS (STRICTLY PROHIBITED):\n{disqualified_str}\n\n"
            f"Synthesize an executive summary headline, narrative paragraph, and 3 talking points."
        )

