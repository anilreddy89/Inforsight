"""Unit tests for dashboard services, engine bridge, and cohort loader."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import matplotlib.pyplot as plt

from inforsight_simulator.workflow.models import (
    ActionResourceRequirement,
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
        self.assertTrue(self.summary["allocation_id"].startswith("alloc_"))
        self.assertEqual(self.summary["allocator_version"], "1.0.0")
        self.assertLessEqual(
            self.summary["budget_used_usd_micros"],
            self.summary["budget_capacity_usd_micros"],
        )
        self.assertLessEqual(
            self.summary["personnel_used_seconds"],
            self.summary["personnel_capacity_seconds"],
        )
        self.assertEqual(self.summary["budget_overflow_usd_micros"], 0)
        self.assertEqual(self.summary["personnel_overflow_seconds"], 0)
        self.assertEqual(len(self.summary["allocation_binding_sha256"]), 64)
        self.assertGreaterEqual(self.summary["capacity_version"], 1)
        self.assertGreaterEqual(self.summary["reservation_version"], 0)
        comparison = self.summary["strategy_comparison"]
        self.assertEqual(
            [row["strategy_id"] for row in comparison],
            ["non_intervention", "operational_rules_only", "risk_ranked", "allocation_engine"],
        )
        self.assertEqual(len({row["comparison_context_sha256"] for row in comparison}), 1)

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
            self.assertEqual(it.snapshot.status, "unknown")
            self.assertIsNone(it.coverage_amount)
            self.assertEqual(it.eligible_action_set.eligible_actions, ())
            self.assertEqual(
                it.eligible_action_set.freeze_reason, "insufficient_domain_evidence"
            )
            self.assertEqual(it.recommended_action, "abstain")

    def test_specialist_approval_workflow(self) -> None:
        """Verifies human specialist approval transitions case to HUMAN_REVIEWED and EXECUTED."""
        item = self.items[0]
        with self.assertRaises(IneligibleOverrideError):
            self.bridge.submit_specialist_decision(
                case_id=item.case_id,
                reviewer_id="usr_lead_analyst_1",
                action=SpecialistReviewAction.APPROVE_RECOMMENDATION,
                rationale_code="APPROVE_OPTIMAL_RECOMMENDATION",
                justification="Review verified policy risk and optimal action.",
            )

    def test_refresh_rebinds_allocation_to_current_reservations(self) -> None:
        audit_path = Path(self.temp_dir.name) / "refresh-audit.jsonl"
        bridge = EngineBridge(audit_log_path=audit_path)
        _, before = load_dashboard_cohort(bridge, policy_count=8)
        capacity = bridge.workflow_service.capacity_snapshot()
        bridge.workflow_service.replace_reservation(
            case_id="case_refresh000000000001",
            action_type="courtesy_reminder",
            requirement=ActionResourceRequirement(
                personnel_seconds=300, direct_cost_usd_micros=2_000_000
            ),
            expected_capacity_version=capacity["capacity_version"],
        )
        _, after = load_dashboard_cohort(bridge, policy_count=8)
        self.assertNotEqual(before["allocation_id"], after["allocation_id"])
        self.assertNotEqual(
            before["allocation_binding_sha256"], after["allocation_binding_sha256"]
        )
        self.assertEqual(after["reservation_version"], before["reservation_version"] + 1)
        self.assertGreaterEqual(after["personnel_used_seconds"], 300)
        self.assertGreaterEqual(after["budget_used_usd_micros"], 2_000_000)

    def test_specialist_override_workflow(self) -> None:
        """Verifies specialist override with eligible action succeeds and logs to audit ledger."""
        item = self.items[1]
        with self.assertRaises(IneligibleOverrideError):
            self.bridge.submit_specialist_decision(
                case_id=item.case_id,
                reviewer_id="usr_specialist_482",
                action=SpecialistReviewAction.OVERRIDE_ACTION,
                rationale_code="OVERRIDE_SPECIALIST_DISCRETION_PREMIUM_DISPUTE",
                justification="Policyholder requested alternative communication channel.",
                selected_action="courtesy_reminder",
            )

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
