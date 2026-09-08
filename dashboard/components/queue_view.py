"""Component rendering the Prioritized Triage Queue Console."""

from __future__ import annotations

from typing import Callable, Sequence
import pandas as pd
import streamlit as st

from dashboard.config import ACTION_METADATA, RISK_TIERS
from dashboard.services.cohort_loader import TriagePolicyItem


def render_queue_view(
    items: Sequence[TriagePolicyItem],
    on_select_policy: Callable[[str], None],
) -> None:
    """Renders the prioritized, filterable operational triage queue."""
    st.markdown("## 📋 Prioritized Triage Queue Console")
    st.markdown(
        "Ranked list of in-force policies evaluated under the **Cost-Utility Uplift Matrix**. "
        "Select any policy to inspect the full case investigation dossier."
    )

    # 1. Multi-factor Filter Controls
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)

    with f_col1:
        tier_options = ["All Tiers"] + list(RISK_TIERS.keys())
        selected_tier = st.selectbox("Risk Tier Filter", tier_options, index=0)

    with f_col2:
        grace_options = ["All Policies", "In Grace Period Only", "Urgent Grace (≤ 10 days)", "Critical Grace (≤ 5 days)"]
        selected_grace = st.selectbox("Grace Period Urgency", grace_options, index=0)

    with f_col3:
        action_options = ["All Actions"] + list(ACTION_METADATA.keys())
        selected_action = st.selectbox("Recommended Action", action_options, index=0)

    with f_col4:
        search_query = st.text_input("Search Policy ID", placeholder="e.g. v6-pol-6c95...").strip()

    # 2. Filter Execution
    filtered: list[TriagePolicyItem] = []
    for item in items:
        # Tier filter
        if selected_tier != "All Tiers" and item.risk_tier != selected_tier:
            continue
        # Grace filter
        if selected_grace == "In Grace Period Only" and not item.in_grace_period:
            continue
        elif selected_grace == "Urgent Grace (≤ 10 days)":
            if item.in_grace_period is not True or item.days_in_grace is None or item.days_in_grace < 20:
                continue
        elif selected_grace == "Critical Grace (≤ 5 days)":
            if item.in_grace_period is not True or item.days_in_grace is None or item.days_in_grace < 25:
                continue
        # Action filter
        if selected_action != "All Actions" and item.recommended_action != selected_action:
            continue
        # Search filter
        if search_query and search_query.lower() not in item.policy_id.lower():
            continue

        filtered.append(item)

    st.markdown(f"**Showing {len(filtered)} of {len(items)} policies** (ranked by Net Preserved Utility):")

    if not filtered:
        st.warning("No policies match the selected filter criteria.")
        return

    # 3. Format Data for Table Presentation
    table_rows = []
    for idx, it in enumerate(filtered, start=1):
        action_meta = ACTION_METADATA.get(it.recommended_action, {})
        action_disp = f"{action_meta.get('icon', '')} {action_meta.get('title', it.recommended_action)}"

        tier_meta = RISK_TIERS.get(it.risk_tier)
        tier_short = tier_meta.short_label if tier_meta else it.risk_tier

        grace_str = (
            f"⚠️ {it.days_in_grace}d / 30d"
            if it.in_grace_period is True else "Unknown" if it.in_grace_period is None else "Outside grace"
        )

        table_rows.append({
            "Priority Rank": f"#{idx}",
            "Policy ID": it.policy_id,
            "Calibrated Risk (p̂)": f"{it.risk_score:.1%}",
            "Risk Tier": tier_short,
            "Grace Status": grace_str,
            "Monthly Premium": f"${it.monthly_premium:,.2f}",
            "Primary Risk Driver": it.primary_risk_driver.replace("_", " ").title(),
            "Recommended Action": action_disp,
            "Net Utility": f"${it.net_utility:,.2f}",
            "Uplift Segment": it.uplift_quadrant,
        })

    df = pd.DataFrame(table_rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Priority Rank": st.column_config.TextColumn("Rank", width="small"),
            "Policy ID": st.column_config.TextColumn("Policy ID", width="medium"),
            "Calibrated Risk (p̂)": st.column_config.TextColumn("Lapse Risk", width="small"),
            "Risk Tier": st.column_config.TextColumn("Tier", width="small"),
            "Grace Status": st.column_config.TextColumn("Grace Period", width="small"),
            "Monthly Premium": st.column_config.TextColumn("Monthly Premium", width="small"),
            "Primary Risk Driver": st.column_config.TextColumn("Primary Driver", width="medium"),
            "Recommended Action": st.column_config.TextColumn("Optimal Intervention", width="medium"),
            "Net Utility": st.column_config.TextColumn("Net Preserved Value", width="small"),
            "Uplift Segment": st.column_config.TextColumn("Uplift", width="small"),
        },
    )

    # 4. Action Selector: Direct Load into Dossier
    st.markdown("### 🔍 Open Policy Investigation Dossier")
    select_col1, select_col2 = st.columns([3, 1])

    with select_col1:
        policy_choices = [it.policy_id for it in filtered]
        selected_pid = st.selectbox(
            "Select Policy to Investigate",
            policy_choices,
            format_func=lambda pid: f"{pid} (Risk: {next(it.risk_score for it in filtered if it.policy_id == pid):.1%}, Action: {next(it.recommended_action for it in filtered if it.policy_id == pid)})",
        )

    with select_col2:
        st.write("")
        st.write("")
        if st.button("Open Dossier ➡️", type="primary", use_container_width=True):
            if selected_pid:
                on_select_policy(selected_pid)
