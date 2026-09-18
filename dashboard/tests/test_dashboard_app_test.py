"""Headless Streamlit interaction coverage for the dashboard entry point."""

from __future__ import annotations

from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _run_app() -> AppTest:
    return AppTest.from_file(str(APP_PATH), default_timeout=45).run()


def _selectbox(at: AppTest, label: str):
    return next(widget for widget in at.selectbox if widget.label == label)


def _button(at: AppTest, label: str):
    return next(widget for widget in at.button if widget.label == label)


class TestDashboardAppTest(unittest.TestCase):
    def test_portfolio_and_queue_filter_render_without_exceptions(self) -> None:
        at = _run_app()
        self.assertFalse(at.exception)
        self.assertEqual(at.radio(key="current_view").value, "📊 Executive Portfolio")
        self.assertTrue(at.metric)

        at.radio(key="current_view").set_value("📋 Triage Queue").run()
        self.assertFalse(at.exception)
        self.assertTrue(at.dataframe)
        self.assertEqual(_selectbox(at, "Risk Tier Filter").value, "All Tiers")

        _selectbox(at, "Risk Tier Filter").select("Tier 4: Critical Risk").run()
        self.assertFalse(at.exception)
        self.assertTrue(at.dataframe)


    def test_dossier_and_decision_console_are_reachable(self) -> None:
        at = _run_app()
        at.radio(key="current_view").set_value("📋 Triage Queue").run()
        self.assertFalse(at.exception)

        _button(at, "Open Dossier ➡️").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["current_view"], "🔍 Policy Dossier")

        at.radio(key="current_view").set_value("⚖️ Decision Console").run()
        self.assertFalse(at.exception)
        self.assertTrue(any("Specialist Decision Console" in item.value for item in at.markdown))
        self.assertTrue(_button(at, "🔐 Commit Decision to Cryptographic Audit Ledger"))


if __name__ == "__main__":
    unittest.main()
