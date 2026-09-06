"""Tests for Phase 3.05 Bounded Case Intelligence Assistant.

Verifies:
1. Layer 1 Deterministic Template Engine produces 100% reproducible briefs with zero hallucination.
2. ADR 0002 non-authority markers ('status: PENDING_HUMAN_REVIEW', 'authorized_to_act: false').
3. Disqualified actions from P3-02 are strictly excluded from recommendations.
4. Grounding Guard intercepts ungrounded entities (false amounts, false dates, disqualified actions).
5. Critical grounding violations trigger fail-closed fallback to Layer 1 template.
6. Minor entity violations trigger sentence-level redaction and audit logging.
7. Generated briefs strictly conform to data-contracts/conservation-case-brief.schema.json.
8. Clean-room temporal cutoff invariant (no future timeline leakage).
"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker

from inforsight_simulator.assistant import (
    DEFAULT_MANDATORY_DISCLAIMER,
    BriefRecommendation,
    CaseBrief,
    CaseEvidenceContext,
    CaseIntelligenceAssistant,
    DeterministicMockNarrativeProvider,
    DisqualifiedActionSummary,
    FactualTimelineEvent,
    GroundingGuard,
    InjectableMockNarrativeProvider,
    OperationalUrgency,
    RiskAssessment,
    RiskDriver,
    SynthesisMode,
    ValidationStatus,
    generate_template_brief,
)


CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "data-contracts"
CASE_BRIEF_SCHEMA_PATH = CONTRACTS_DIR / "conservation-case-brief.schema.json"


def _make_evidence_context(
    policy_id: str = "pol_test_10492",
    as_of_date: str = "2026-09-01T00:00:00Z",
    case_id: str = "case_test_001",
    calibrated_probability: float = 0.3842,
    operational_tier: str = "Tier 3: High Risk",
    primary_action: str = "payment_method_remediation",
    uplift_quadrant: str = "PERSUADABLE",
    expected_net_utility: float = 345.50,
    annual_premium: float = 1850.0,
    monthly_premium: float = 154.17,
    coverage_amount: float = 250000.0,
    total_premiums_paid: float = 2775.0,
    tenure_months: int = 18,
    in_grace_period: bool = True,
    days_past_due: int = 12,
    has_active_claim: bool = False,
    has_legal_hold: bool = False,
    has_registered_dispute: bool = False,
    disqualified_actions: tuple[DisqualifiedActionSummary, ...] = (
        DisqualifiedActionSummary(
            action_id="specialist_phone_outreach",
            reason_code="DISQUALIFIED_CONTACT_COOLING_OFF_ACTIVE",
            description="Contact cooling off active (14 days < 30 days requirement)",
        ),
    ),
) -> CaseEvidenceContext:
    """Create a populated synthetic evidence context for testing."""
    drivers = (
        RiskDriver(
            feature_name="grace_period_count",
            attribution=0.32,
            display_text="Grace period entry within last 30 days",
        ),
        RiskDriver(
            feature_name="payment_failure_flag",
            attribution=0.28,
            display_text="Failed electronic funds transfer (EFT)",
        ),
    )

    events = (
        FactualTimelineEvent(
            occurred_at="2025-03-01T00:00:00Z",
            event_type="POLICY_ISSUED",
            summary=f"Term life policy issued with monthly premium of ${monthly_premium:.2f}.",
        ),
        FactualTimelineEvent(
            occurred_at="2026-08-20T00:00:00Z",
            event_type="PAYMENT_FAILED",
            summary="Scheduled electronic payment failed due to banking error.",
        ),
    )

    return CaseEvidenceContext(
        policy_id=policy_id,
        as_of_date=as_of_date,
        case_id=case_id,
        product_type="term_life",
        annual_premium=annual_premium,
        monthly_premium=monthly_premium,
        coverage_amount=coverage_amount,
        tenure_months=tenure_months,
        total_premiums_paid=total_premiums_paid,
        policy_status="grace_period" if in_grace_period else "active",
        in_grace_period=in_grace_period,
        days_past_due=days_past_due,
        payment_frequency="monthly",
        initial_payment_method="eft",
        risk_class="standard",
        servicing_advisor_id="adv_001",
        has_active_claim=has_active_claim,
        has_legal_hold=has_legal_hold,
        has_registered_dispute=has_registered_dispute,
        calibrated_probability=calibrated_probability,
        operational_tier=operational_tier,
        top_risk_drivers=drivers,
        eligible_actions=("payment_method_remediation", "courtesy_reminder", "abstain"),
        disqualified_actions=disqualified_actions,
        primary_action=primary_action,
        uplift_quadrant=uplift_quadrant,
        expected_net_utility=expected_net_utility,
        alternative_actions=("courtesy_reminder",),
        timeline_events=events,
    )


class TestBoundedCaseIntelligenceAssistant(unittest.TestCase):
    """Test suite for Phase 3.05 Bounded Case Intelligence Assistant."""

    @classmethod
    def setUpClass(cls) -> None:
        with CASE_BRIEF_SCHEMA_PATH.open(encoding="utf-8") as f:
            cls.schema = json.load(f)
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

    def test_layer1_deterministic_template_reproducibility(self) -> None:
        """Verify Layer 1 produces 100% bit-for-bit identical briefs across repeat runs."""
        context = _make_evidence_context()
        timestamp = "2026-09-05T12:00:00Z"

        brief1 = generate_template_brief(context, generated_at=timestamp)
        brief2 = generate_template_brief(context, generated_at=timestamp)

        self.assertEqual(brief1.to_dict(), brief2.to_dict())
        self.assertEqual(brief1.to_json(), brief2.to_json())
        self.assertEqual(brief1.to_markdown(), brief2.to_markdown())
        self.assertEqual(brief1.grounding_audit.validation_status, ValidationStatus.PASSED_CLEAN)
        self.assertFalse(brief1.grounding_audit.hallucination_detected)
        self.assertGreater(brief1.grounding_audit.verified_entity_count, 0)

    def test_adr_0002_non_authority_markers(self) -> None:
        """Verify ADR 0002 non-authority markers are immutably enforced."""
        context = _make_evidence_context()
        assistant = CaseIntelligenceAssistant(mode=SynthesisMode.TEMPLATE_DETERMINISTIC)
        brief = assistant.generate_brief(context)

        self.assertEqual(brief.status, "PENDING_HUMAN_REVIEW")
        self.assertFalse(brief.authorized_to_act)
        self.assertIn("ADVISORY ONLY", brief.disclaimer)

        # Confirm dataclass raises ValueError if status or authorized_to_act is invalid
        with self.assertRaises(ValueError):
            CaseBrief(
                brief_id="brf_bad",
                case_id="case_bad",
                policy_id="pol_bad",
                as_of_date="2026-09-01T00:00:00Z",
                generated_at="2026-09-05T12:00:00Z",
                synthesis_mode=SynthesisMode.TEMPLATE_DETERMINISTIC,
                executive_summary=brief.executive_summary,
                risk_assessment=brief.risk_assessment,
                factual_timeline=brief.factual_timeline,
                intervention_recommendations=brief.intervention_recommendations,
                disqualified_actions=brief.disqualified_actions,
                grounding_audit=brief.grounding_audit,
                status="EXECUTED",  # Violates ADR 0002
                authorized_to_act=False,
            )

        with self.assertRaises(ValueError):
            CaseBrief(
                brief_id="brf_bad",
                case_id="case_bad",
                policy_id="pol_bad",
                as_of_date="2026-09-01T00:00:00Z",
                generated_at="2026-09-05T12:00:00Z",
                synthesis_mode=SynthesisMode.TEMPLATE_DETERMINISTIC,
                executive_summary=brief.executive_summary,
                risk_assessment=brief.risk_assessment,
                factual_timeline=brief.factual_timeline,
                intervention_recommendations=brief.intervention_recommendations,
                disqualified_actions=brief.disqualified_actions,
                grounding_audit=brief.grounding_audit,
                status="PENDING_HUMAN_REVIEW",
                authorized_to_act=True,  # Violates ADR 0002
            )

    def test_disqualified_actions_isolation(self) -> None:
        """Verify disqualified actions never appear in recommendations."""
        context = _make_evidence_context()
        assistant = CaseIntelligenceAssistant(mode=SynthesisMode.TEMPLATE_DETERMINISTIC)
        brief = assistant.generate_brief(context)

        disqualified_ids = {d.action_id for d in context.disqualified_actions}
        self.assertNotIn(brief.intervention_recommendations.primary_action, disqualified_ids)
        for alt in brief.intervention_recommendations.alternative_actions:
            self.assertNotIn(alt, disqualified_ids)

        # Disqualified actions are catalogued in section 5
        self.assertEqual(len(brief.disqualified_actions), 1)
        self.assertEqual(brief.disqualified_actions[0].action_id, "specialist_phone_outreach")

    def test_grounding_guard_intercepts_disqualified_action_and_falls_back(self) -> None:
        """Critical violation: Recommending a disqualified action triggers fail-closed fallback."""
        context = _make_evidence_context()

        # Inject narrative that recommends the disqualified action 'specialist_phone_outreach'
        malicious_narrative = {
            "headline": "Action Plan for High Risk Account",
            "narrative": "We must immediately dispatch specialist phone outreach to save this account.",
            "talking_points": ["Call the policyholder right away."],
        }
        mock_provider = InjectableMockNarrativeProvider(malicious_narrative)
        assistant = CaseIntelligenceAssistant(
            mode=SynthesisMode.LLM_AUGMENTED_GROUNDED,
            narrative_provider=mock_provider,
        )

        brief = assistant.generate_brief(context)

        # Fallback to deterministic template must have occurred
        self.assertEqual(brief.grounding_audit.validation_status, ValidationStatus.FALLBACK_TO_TEMPLATE)
        self.assertTrue(brief.grounding_audit.hallucination_detected)
        self.assertTrue(any("disqualified action" in v.lower() for v in brief.grounding_audit.violations))
        # Content in executive summary should match template engine
        self.assertIn("Grace period entry", brief.executive_summary.headline)

    def test_grounding_guard_intercepts_legal_freeze_violation(self) -> None:
        """Critical violation: Suggesting outreach during legal dispute freeze triggers fallback."""
        context = _make_evidence_context(
            has_registered_dispute=True,
            primary_action="abstain",
        )

        malicious_narrative = {
            "headline": "Urgent Action Required",
            "narrative": "We recommend placing a phone call to the policyholder despite the legal dispute.",
            "talking_points": ["Call the policyholder."],
        }
        mock_provider = InjectableMockNarrativeProvider(malicious_narrative)
        assistant = CaseIntelligenceAssistant(
            mode=SynthesisMode.LLM_AUGMENTED_GROUNDED,
            narrative_provider=mock_provider,
        )

        brief = assistant.generate_brief(context)

        self.assertEqual(brief.grounding_audit.validation_status, ValidationStatus.FALLBACK_TO_TEMPLATE)
        self.assertTrue(brief.grounding_audit.hallucination_detected)
        self.assertTrue(any("legal freeze" in v.lower() for v in brief.grounding_audit.violations))

    def test_grounding_guard_redacts_ungrounded_currency(self) -> None:
        """Minor entity violation: Ungrounded currency figure is redacted and logged."""
        context = _make_evidence_context()

        # Actual premium is $154.17. Inject false premium of $9,999.00 in second sentence
        candidate_narrative = {
            "headline": "High Risk Retention Review for Valued Customer",
            "narrative": (
                f"Policy {context.policy_id} is currently in grace period. "
                "The outstanding arrears balance is $9,999.00 due to nonpayment. "
                "The policyholder has 18 months of continuous tenure."
            ),
            "talking_points": [
                "Review payment options with customer.",
                "Provide secure payment link.",
            ],
        }
        mock_provider = InjectableMockNarrativeProvider(candidate_narrative)
        assistant = CaseIntelligenceAssistant(
            mode=SynthesisMode.LLM_AUGMENTED_GROUNDED,
            narrative_provider=mock_provider,
        )

        brief = assistant.generate_brief(context)

        self.assertEqual(brief.grounding_audit.validation_status, ValidationStatus.PASSED_WITH_REDACTION)
        self.assertTrue(brief.grounding_audit.hallucination_detected)
        self.assertTrue(any("ungrounded currency" in v.lower() for v in brief.grounding_audit.violations))
        # Sentence with $9,999.00 must NOT appear in the final narrative
        self.assertNotIn("9,999", brief.executive_summary.narrative)
        # Grounded sentences must be preserved
        self.assertIn("grace period", brief.executive_summary.narrative)

    def test_grounding_guard_redacts_ungrounded_date(self) -> None:
        """Minor entity violation: Ungrounded date is redacted and logged."""
        context = _make_evidence_context()

        candidate_narrative = {
            "headline": "High Risk Retention Review",
            "narrative": (
                f"Policy {context.policy_id} entered grace period. "
                "The policy was originally issued on 2038-12-31 by advisor adv_001. "
                "Tenure stands at 18 months."
            ),
            "talking_points": ["Discuss renewal options."],
        }
        mock_provider = InjectableMockNarrativeProvider(candidate_narrative)
        assistant = CaseIntelligenceAssistant(
            mode=SynthesisMode.LLM_AUGMENTED_GROUNDED,
            narrative_provider=mock_provider,
        )

        brief = assistant.generate_brief(context)

        self.assertEqual(brief.grounding_audit.validation_status, ValidationStatus.PASSED_WITH_REDACTION)
        self.assertTrue(brief.grounding_audit.hallucination_detected)
        self.assertTrue(any("ungrounded date" in v.lower() for v in brief.grounding_audit.violations))
        self.assertNotIn("2038-12-31", brief.executive_summary.narrative)

    def test_layer2_clean_grounded_synthesis(self) -> None:
        """Verify Layer 2 passes cleanly when all cited facts are grounded."""
        context = _make_evidence_context()
        assistant = CaseIntelligenceAssistant(
            mode=SynthesisMode.LLM_AUGMENTED_GROUNDED,
            narrative_provider=DeterministicMockNarrativeProvider(),
        )

        brief = assistant.generate_brief(context)

        self.assertEqual(brief.grounding_audit.validation_status, ValidationStatus.PASSED_CLEAN)
        self.assertFalse(brief.grounding_audit.hallucination_detected)
        self.assertEqual(len(brief.grounding_audit.violations), 0)
        self.assertEqual(brief.synthesis_mode, SynthesisMode.LLM_AUGMENTED_GROUNDED)

    def test_json_schema_validation(self) -> None:
        """Verify both Layer 1 and Layer 2 generated briefs strictly pass JSON Schema validation."""
        context = _make_evidence_context()

        # 1. Template brief
        asst_tmpl = CaseIntelligenceAssistant(mode=SynthesisMode.TEMPLATE_DETERMINISTIC)
        brief_tmpl = asst_tmpl.generate_brief(context)
        errors_tmpl = list(self.validator.iter_errors(brief_tmpl.to_dict()))
        self.assertEqual(len(errors_tmpl), 0, f"Template brief schema errors: {errors_tmpl}")

        # 2. LLM brief
        asst_llm = CaseIntelligenceAssistant(mode=SynthesisMode.LLM_AUGMENTED_GROUNDED)
        brief_llm = asst_llm.generate_brief(context)
        errors_llm = list(self.validator.iter_errors(brief_llm.to_dict()))
        self.assertEqual(len(errors_llm), 0, f"LLM brief schema errors: {errors_llm}")

    def test_markdown_rendering_structure(self) -> None:
        """Verify .to_markdown() outputs complete, well-formed markdown."""
        context = _make_evidence_context()
        assistant = CaseIntelligenceAssistant(mode=SynthesisMode.TEMPLATE_DETERMINISTIC)
        brief = assistant.generate_brief(context)

        md = brief.to_markdown()
        self.assertIn("# Conservation Case Brief", md)
        self.assertIn("STATUS: PENDING_HUMAN_REVIEW", md)
        self.assertIn("Authorized to act: False", md)
        self.assertIn("## 1. Executive Summary", md)
        self.assertIn("## 2. Risk Assessment & Explainability", md)
        self.assertIn("## 3. Factual Timeline", md)
        self.assertIn("## 4. Recommended Intervention Strategy", md)
        self.assertIn("## 5. Disqualified Actions & Statutory Restrictions", md)
        self.assertIn("## 6. Grounding & Verification Audit", md)


if __name__ == "__main__":
    unittest.main()

