"""Main entry point for the Inforsight Conservation Intelligence Dashboard.

Launches the interactive Streamlit application uniting executive portfolio visibility,
prioritized triage queues, point-in-time case dossiers, SHAP explanations,
and human-in-the-loop decision controls under ADR 0002.
"""

from __future__ import annotations

from pathlib import Path
import sys

# Ensure repository root is on sys.path for standalone streamlit execution
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from dashboard.components.decision_console import render_decision_console
from dashboard.components.dossier_view import render_dossier_view
from dashboard.components.portfolio_view import render_portfolio_view
from dashboard.components.queue_view import render_queue_view
from dashboard.components.telemetry_view import render_telemetry_view
from dashboard.config import (
    DEFAULT_AUDIT_LOG_PATH,
    DEFAULT_BUNDLE_PATH,
    DEFAULT_MAX_SPECIALIST_HOURS,
)
from dashboard.services.cohort_loader import TriagePolicyItem, load_dashboard_cohort
from dashboard.services.engine_bridge import EngineBridge

# 1. Page Configuration
st.set_page_config(
    page_title="Inforsight | Conservation Decision Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished interface styling
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.75rem;
        font-weight: 700;
    }
    .stAlert {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_engine_bridge() -> EngineBridge:
    """Initializes and caches the central engine bridge."""
    return EngineBridge(
        bundle_path=DEFAULT_BUNDLE_PATH,
        audit_log_path=DEFAULT_AUDIT_LOG_PATH,
    )


@st.cache_data
def get_cohort_data(_bridge: EngineBridge, policy_count: int = 48) -> tuple[list[TriagePolicyItem], dict]:
    """Generates and caches the scored demonstration cohort."""
    return load_dashboard_cohort(_bridge, policy_count=policy_count)


def main() -> None:
    # 2. Initialize Core Services & Cohort
    bridge = get_engine_bridge()
    items, summary = get_cohort_data(bridge, policy_count=48)

    # 3. Session State Initialization
    if "selected_policy_id" not in st.session_state or not st.session_state["selected_policy_id"]:
        st.session_state["selected_policy_id"] = items[0].policy_id if items else ""

    if "current_view" not in st.session_state:
        st.session_state["current_view"] = "📊 Executive Portfolio"

    # Callbacks for cross-view navigation
    def select_policy_and_open_dossier(pid: str) -> None:
        st.session_state["selected_policy_id"] = pid
        st.session_state["current_view"] = "🔍 Policy Dossier"

    def proceed_to_decision(pid: str) -> None:
        st.session_state["selected_policy_id"] = pid
        st.session_state["current_view"] = "⚖️ Decision Console"

    # 4. Sidebar Navigation & Branding
    with st.sidebar:
        st.title("🛡️ Inforsight")
        st.caption("Policy Conservation Decision Engine (ADR 0002)")
        st.markdown("---")

        views = [
            "📊 Executive Portfolio",
            "📋 Triage Queue",
            "🔍 Policy Dossier",
            "⚖️ Decision Console",
            "📈 Telemetry & Drift",
        ]
        chosen_view = st.radio("Navigation", views, key="current_view")

        st.markdown("---")

        # Global Policy Switcher
        st.markdown("### 🎯 Quick Policy Switcher")
        all_pids = [it.policy_id for it in items]
        curr_idx = all_pids.index(st.session_state["selected_policy_id"]) if st.session_state["selected_policy_id"] in all_pids else 0
        selected_pid = st.selectbox(
            "Active Policy",
            all_pids,
            index=curr_idx,
            format_func=lambda pid: f"{pid[:18]}... ({next((it.risk_tier.split(':')[0] for it in items if it.policy_id == pid), '')})",
        )
        if selected_pid != st.session_state["selected_policy_id"]:
            st.session_state["selected_policy_id"] = selected_pid

        st.markdown("---")
        st.markdown(
            "**Milestone:** `v0.3.0-decision-engine`\n\n"
            "**Model Bundle:** `inforsight-v6-logistic-platt`\n\n"
            "**Governance:** ADR 0001 / ADR 0002"
        )

    # Find the active item
    active_item = next(
        (it for it in items if it.policy_id == st.session_state["selected_policy_id"]),
        items[0] if items else None,
    )

    # 5. Main Content Area Dispatch
    if chosen_view == "📊 Executive Portfolio":
        render_portfolio_view(summary=summary, items=items)

    elif chosen_view == "📋 Triage Queue":
        render_queue_view(
            items=items,
            on_select_policy=select_policy_and_open_dossier,
        )

    elif chosen_view == "🔍 Policy Dossier":
        if active_item:
            render_dossier_view(
                item=active_item,
                on_proceed_to_decision=proceed_to_decision,
            )
        else:
            st.warning("No policy selected. Please select a policy from the Triage Queue.")

    elif chosen_view == "⚖️ Decision Console":
        if active_item:
            render_decision_console(
                item=active_item,
                engine_bridge=bridge,
            )
        else:
            st.warning("No policy selected. Please select a policy from the Triage Queue.")

    elif chosen_view == "📈 Telemetry & Drift":
        render_telemetry_view()


if __name__ == "__main__":
    main()
