"""Unit tests for dashboard services, engine bridge, and cohort loader."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt

from inforsight_simulator.workflow.models import (
    CaseState,
    IneligibleOverrideError,
    InvalidReviewerCredentialsError,
    MissingJustificationError,
    SpecialistReviewAction,
)

from dashboard.services.chart_utils import (
    plot_intervention_mix,
    plot_risk_distribution,
    plot_shap_waterfall,
)
from dashboard.services.cohort_loader import load_dashboard_cohort
from dashboard.services.engine_bridge import EngineBridge


class TestDashboardServices(unittest.TestCase):
    """Tests core backend coordination, cohort generation, and workflow execution for the dashboard."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.temp_audit_log = Path(cls.temp_dir.name) / "test-audit-log.jsonl"
        cls.bridge = EngineBridge(audit_log_path=cls.temp_audit_log)
        cls.items, cls.summary = load_dashboard_cohort(cls.bridge, policy_count=12)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_engine_bridge_initialization(self) -> None:
        """Verifies EngineBridge correctly loads the release bundle and initializes subsystems."""
        self.assertIsNotNone(self.bridge.bundle)
        self.assertEqual(self.bridge.bundle.bundle_id, "inforsight-v6-logistic-platt-20260817")
        self.assertIsNotNone(self.bridge.inference_engine)
        self.assertIsNotNone(self.bridge.workflow_service)
        self.assertIsNotNone(self.bridge.rules_engine)
        self.assertIsNotNone(self.bridge.assistant)

    def test_cohort_loading_and_scoring(self) -> None:
        """Verifies deterministic cohort generation, scoring, and priority ranking."""
        self.assertEqual(len(self.items), 12)
        self.assertEqual(self.summary["total_policies"], 12)
        self.assertIn("tier_counts", self.summary)
        self.assertIn("action_counts", self.summary)

        # Assert priority ranking invariant (descending order of net utility)
        for i in range(len(self.items) - 1):
            self.assertGreaterEqual(
                self.items[i].net_utility,
                self.items[i + 1].net_utility,
                f"Triage queue must be sorted descending by net utility: {self.items[i].net_utility} < {self.items[i+1].net_utility}",
            )

        # Invariant checks on individual policy items
        for it in self.items:
            self.assertTrue(it.policy_id.startswith("v6-pol-"))
            self.assertGreaterEqual(it.risk_score, 0.0)
            self.assertLessEqual(it.risk_score, 1.0)
            self.assertIn("Tier", it.risk_tier)
            self.assertIsNotNone(it.recommended_action)
            self.assertIsNotNone(it.case_brief)
            self.assertTrue(it.case_brief.authorized_to_act is False)
            self.assertEqual(it.case_brief.status, "PENDING_HUMAN_REVIEW")

    def test_specialist_approval_workflow(self) -> None:
        """Verifies human specialist approval transitions case to HUMAN_REVIEWED and EXECUTED."""
        item = self.items[0]
        rev_ev, exec_ev = self.bridge.submit_specialist_decision(
            case_id=item.case_id,
            reviewer_id="usr_lead_analyst_1",
            action=SpecialistReviewAction.APPROVE_RECOMMENDATION,
            rationale_code="APPROVE_OPTIMAL_RECOMMENDATION",
            justification="Review verified policy risk and optimal action.",
        )
        self.assertEqual(rev_ev.to_state, CaseState.HUMAN_REVIEWED)
        self.assertIsNotNone(exec_ev)
        self.assertIn(exec_ev.to_state, (CaseState.EXECUTED, CaseState.DISMISSED))

    def test_specialist_override_workflow(self) -> None:
        """Verifies specialist override with eligible action succeeds and logs to audit ledger."""
        item = self.items[1]
        eligible_actions = list(item.eligible_action_set.eligible_actions)
        override_action = eligible_actions[0]

        rev_ev, exec_ev = self.bridge.submit_specialist_decision(
            case_id=item.case_id,
            reviewer_id="usr_specialist_482",
            action=SpecialistReviewAction.OVERRIDE_ACTION,
            rationale_code="OVERRIDE_SPECIALIST_DISCRETION_PREMIUM_DISPUTE",
            justification="Policyholder requested alternative communication channel.",
            selected_action=override_action,
        )
        self.assertEqual(rev_ev.to_state, CaseState.HUMAN_REVIEWED)
        self.assertIsNotNone(exec_ev)

    def test_specialist_rejection_workflow(self) -> None:
        """Verifies specialist rejection transitions case to HUMAN_REVIEWED, DISMISSED, and RESOLVED."""
        item = self.items[2]
        rev_ev, exec_ev = self.bridge.submit_specialist_decision(
            case_id=item.case_id,
            reviewer_id="usr_compliance_lead",
            action=SpecialistReviewAction.REJECT_AND_CLOSE,
            rationale_code="REJECT_CUSTOMER_REQUESTED_NO_CONTACT",
            justification="Confirmed formal no-contact preference on file.",
        )
        self.assertEqual(rev_ev.to_state, CaseState.HUMAN_REVIEWED)
        self.assertIsNotNone(exec_ev)
        self.assertEqual(exec_ev.to_state, CaseState.RESOLVED)

    def test_chart_utilities(self) -> None:
        """Verifies chart generation functions produce valid figures without errors."""
        item = self.items[0]

        # SHAP Waterfall
        fig_waterfall = plot_shap_waterfall(
            root_attributions=item.scoring_result.root_attributions_log_odds,
            base_value_logit=-0.7107,
            calibrated_logit=item.scoring_result.calibrated_logit,
        )
        self.assertIsInstance(fig_waterfall, plt.Figure)
        plt.close(fig_waterfall)

        # Risk distribution donut
        fig_donut = plot_risk_distribution(self.summary["tier_counts"])
        self.assertIsInstance(fig_donut, plt.Figure)
        plt.close(fig_donut)

        # Intervention mix bar
        fig_bar = plot_intervention_mix(self.summary["action_counts"])
        self.assertIsInstance(fig_bar, plt.Figure)
        plt.close(fig_bar)


if __name__ == "__main__":
    unittest.main()
