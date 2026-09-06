"""Automated Grounding Guard and Post-Processing Validator for Case Intelligence.

Enforces strict factual verification against reconstructed point-in-time evidence,
prohibits references to disqualified actions, and implements fail-closed fallback
and redaction under ADR 0002.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from inforsight_simulator.assistant.context import CaseEvidenceContext
from inforsight_simulator.assistant.models import (
    GroundingAudit,
    ValidationStatus,
)


CURRENCY_REGEX = re.compile(r"\$([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)")
ISO_DATE_REGEX = re.compile(r"\b(20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\b")


class GroundingGuard:
    """Post-processing validation firewall inspecting generative narratives."""

    def __init__(self, tolerance: float = 0.05) -> None:
        self.tolerance = tolerance

    def extract_currencies(self, text: str) -> list[float]:
        """Extract all dollar currency values from text as floats."""
        currencies: list[float] = []
        for match in CURRENCY_REGEX.finditer(text):
            cleaned = match.group(1).replace(",", "")
            try:
                currencies.append(float(cleaned))
            except ValueError:
                continue
        return currencies

    def extract_dates(self, text: str) -> list[str]:
        """Extract all ISO-formatted dates (YYYY-MM-DD) from text."""
        return ISO_DATE_REGEX.findall(text)

    def contains_disqualified_action_reference(
        self,
        text: str,
        disqualified_actions: set[str],
    ) -> Optional[str]:
        """Check if text references or recommends any disqualified action."""
        text_lower = text.lower().replace("-", "_")
        for disq in disqualified_actions:
            # Check exact identifier
            if disq in text_lower:
                return disq
            # Check human-readable representation
            disq_phrase = disq.replace("_", " ")
            if disq_phrase in text_lower:
                return disq
        return None

    def validate(
        self,
        candidate_narrative: dict[str, Any],
        context: CaseEvidenceContext,
    ) -> tuple[dict[str, Any], GroundingAudit]:
        """Validate candidate narrative against evidence context ground truth.

        Returns:
            Tuple of (validated_narrative_dict, GroundingAudit).
            If critical violations occur, validation_status is FALLBACK_TO_TEMPLATE.
        """
        violations: list[str] = []
        gt = context.ground_truth_entities
        disqualified_set: set[str] = gt["disqualified_actions"]
        allowed_currencies: set[float] = gt["currency_numbers"]
        valid_dates: set[str] = gt["valid_dates"]

        headline = candidate_narrative.get("headline", "")
        narrative = candidate_narrative.get("narrative", "")
        talking_points = list(candidate_narrative.get("talking_points", []))

        full_text = f"{headline} {narrative} {' '.join(talking_points)}"

        # ---------------------------------------------------------------------
        # 1. Critical Check: Disqualified Action Firewall
        # ---------------------------------------------------------------------
        matched_disq = self.contains_disqualified_action_reference(full_text, disqualified_set)
        if matched_disq:
            violations.append(
                f"Disqualified action firewall violation: Narrative references disqualified action '{matched_disq}'."
            )
            return candidate_narrative, GroundingAudit(
                validation_status=ValidationStatus.FALLBACK_TO_TEMPLATE,
                verified_entity_count=0,
                hallucination_detected=True,
                violations=tuple(violations),
            )

        # ---------------------------------------------------------------------
        # 2. Critical Check: Legal / Dispute Freeze Invariant
        # ---------------------------------------------------------------------
        if gt["has_legal_dispute_freeze"]:
            # If legal freeze is active, any active outreach recommendation is forbidden
            active_outreach_terms = ["call", "phone", "sms", "text message", "consultation", "reach out"]
            if any(term in full_text.lower() for term in active_outreach_terms):
                violations.append(
                    "Legal freeze invariant violation: Outreach recommended on account with active dispute/legal hold."
                )
                return candidate_narrative, GroundingAudit(
                    validation_status=ValidationStatus.FALLBACK_TO_TEMPLATE,
                    verified_entity_count=0,
                    hallucination_detected=True,
                    violations=tuple(violations),
                )

        # ---------------------------------------------------------------------
        # 3. Currency Entity Grounding Verification
        # ---------------------------------------------------------------------
        redacted_sentences: list[str] = []
        valid_currencies_found = 0
        cleaned_sentences: list[str] = []

        # Split narrative into sentences for granular redaction
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", narrative) if s.strip()]

        for sent in sentences:
            sent_currencies = self.extract_currencies(sent)
            sent_valid = True
            for c in sent_currencies:
                # Check if matches any allowed currency within tolerance
                matches = any(abs(c - allowed) <= self.tolerance for allowed in allowed_currencies)
                if not matches:
                    sent_valid = False
                    violations.append(
                        f"Ungrounded currency figure: Cited '${c:.2f}' not present in policy ground truth."
                    )
                else:
                    valid_currencies_found += 1

            if sent_valid:
                cleaned_sentences.append(sent)
            else:
                # Redact sentence
                redacted_sentences.append(sent)

        # ---------------------------------------------------------------------
        # 4. Date Entity Grounding Verification
        # ---------------------------------------------------------------------
        final_sentences: list[str] = []
        valid_dates_found = 0

        for sent in cleaned_sentences:
            sent_dates = self.extract_dates(sent)
            sent_valid = True
            for d in sent_dates:
                if d not in valid_dates:
                    sent_valid = False
                    violations.append(
                        f"Ungrounded date reference: Cited date '{d}' not present in historical timeline."
                    )
                else:
                    valid_dates_found += 1

            if sent_valid:
                final_sentences.append(sent)
            else:
                redacted_sentences.append(sent)

        # ---------------------------------------------------------------------
        # 5. Talking Points Entity Verification
        # ---------------------------------------------------------------------
        cleaned_talking_points: list[str] = []
        for pt in talking_points:
            pt_currencies = self.extract_currencies(pt)
            pt_valid = True
            for c in pt_currencies:
                matches = any(abs(c - allowed) <= self.tolerance for allowed in allowed_currencies)
                if not matches:
                    pt_valid = False
                    violations.append(f"Ungrounded currency in talking points: '${c:.2f}'.")
                else:
                    valid_currencies_found += 1

            pt_dates = self.extract_dates(pt)
            for d in pt_dates:
                if d not in valid_dates:
                    pt_valid = False
                    violations.append(f"Ungrounded date in talking points: '{d}'.")
                else:
                    valid_dates_found += 1

            if pt_valid:
                cleaned_talking_points.append(pt)

        # If too many sentences were redacted (e.g. empty narrative), fall back to template
        if not final_sentences or not cleaned_talking_points:
            if redacted_sentences:
                violations.append("Excessive grounding violations: Narrative gutted by redaction.")
                return candidate_narrative, GroundingAudit(
                    validation_status=ValidationStatus.FALLBACK_TO_TEMPLATE,
                    verified_entity_count=valid_currencies_found + valid_dates_found,
                    hallucination_detected=True,
                    violations=tuple(violations),
                )

        validated_narrative = {
            "headline": headline,
            "narrative": " ".join(final_sentences),
            "talking_points": cleaned_talking_points,
        }

        # Determine status
        if violations:
            status = ValidationStatus.PASSED_WITH_REDACTION
            hallucination_detected = True
        else:
            status = ValidationStatus.PASSED_CLEAN
            hallucination_detected = False

        verified_count = 5 + valid_currencies_found + valid_dates_found

        return validated_narrative, GroundingAudit(
            validation_status=status,
            verified_entity_count=verified_count,
            hallucination_detected=hallucination_detected,
            violations=tuple(violations),
        )

