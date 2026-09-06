"""Headless smoke tests verifying dashboard modules and app initialization."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from dashboard.config import ACTION_METADATA, RISK_TIERS
from dashboard.services.cohort_loader import TriagePolicyItem
from dashboard.services.engine_bridge import EngineBridge


class TestDashboardSmoke(unittest.TestCase):
    """Smoke tests verifying that dashboard components and views can be loaded and executed headlessly."""

    def test_module_imports(self) -> None:
        """Verifies that all dashboard component and service modules import without syntax or symbol errors."""
        import dashboard.app
        import dashboard.config
        import dashboard.services.chart_utils
        import dashboard.services.cohort_loader
        import dashboard.services.engine_bridge
        import dashboard.components.portfolio_view
        import dashboard.components.queue_view
        import dashboard.components.dossier_view
        import dashboard.components.decision_console
        import dashboard.components.telemetry_view

        self.assertTrue(hasattr(dashboard.app, "main"))
        self.assertGreater(len(dashboard.config.RISK_TIERS), 0)
        self.assertGreater(len(dashboard.config.ACTION_METADATA), 0)

    @patch("streamlit.metric")
    @patch("streamlit.progress")
    @patch("streamlit.pyplot")
    def test_portfolio_view_headless(self, mock_pyplot, mock_progress, mock_metric) -> None:
        """Verifies render_portfolio_view runs without uncaught exceptions in headless mode."""
        from dashboard.components.portfolio_view import render_portfolio_view

        fake_summary = {
            "total_policies": 48,
            "active_grace_count": 8,
            "tier_counts": {k: 12 for k in RISK_TIERS},
            "total_value_at_risk": 45000.0,
            "allocated_specialist_hours": 24.5,
            "max_specialist_hours": 50.0,
            "capacity_utilization_pct": 49.0,
            "action_counts": {k: 5 for k in ACTION_METADATA},
        }

        # Should execute cleanly
        render_portfolio_view(fake_summary, [])
        self.assertTrue(mock_metric.called)

    @patch("streamlit.markdown")
    @patch("streamlit.metric")
    @patch("streamlit.dataframe")
    def test_telemetry_view_headless(self, mock_df, mock_metric, mock_md) -> None:
        """Verifies render_telemetry_view runs without errors."""
        from dashboard.components.telemetry_view import render_telemetry_view

        render_telemetry_view()
        self.assertTrue(mock_metric.called)


if __name__ == "__main__":
    unittest.main()
