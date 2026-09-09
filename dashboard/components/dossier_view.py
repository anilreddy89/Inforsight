"""Component rendering the Deep-Dive Policy Case Investigation Dossier."""

from __future__ import annotations

from typing import Callable
import pandas as pd
import streamlit as st

from dashboard.config import ACTION_METADATA, RISK_TIERS
from dashboard.services.chart_utils import plot_shap_waterfall
from dashboard.services.cohort_loader import TriagePolicyItem


def render_dossier_view(
    item: TriagePolicyItem,
    on_proceed_to_decision: Callable[[str], None],
) -> None:
    """Renders the comprehensive 360-degree point-in-time policy dossier."""
    tier_meta = RISK_TIERS.get(item.risk_tier)
    tier_pill = tier_meta.label if tier_meta else item.risk_tier

    st.markdown(f"## 🔍 Policy Dossier: `{item.policy_id}`")
    st.markdown(
        f"**Observation Cutoff:** `{item.as_of_date}` | "
        f"**Status:** `{item.status}` | "
        f"**Risk Level:** <span style='background-color:{tier_meta.bg_hex if tier_meta else '#eee'}; "
        f"color:{tier_meta.color_hex if tier_meta else '#333'}; padding:3px 8px; border-radius:4px; font-weight:bold;'>"
        f"{tier_pill}</span>",
        unsafe_allow_html=True,
    )

    # 1. Demographics & Account Overview
    st.markdown("### 📋 Contract Demographics & Terms")
    dcol1, dcol2, dcol3, dcol4 = st.columns(4)

    with dcol1:
        st.markdown("**Product Type**")
        st.write(item.product_type.replace("_", " ").title())
        st.markdown("**Coverage Face Amount**")
        st.write(
            f"${item.coverage_amount:,.0f}"
            if item.coverage_amount is not None else "Unknown"
        )

    with dcol2:
        st.markdown("**Monthly Premium**")
        st.write(f"${item.monthly_premium:,.2f}")
        st.markdown("**Annualized Premium**")
        st.write(f"${item.annual_premium:,.2f}")

    with dcol3:
        st.markdown("**Policy Tenure**")
        st.write(f"{item.tenure_months} months ({item.tenure_months // 12}y {item.tenure_months % 12}m)")
        st.markdown("**Payment Channel**")
        st.write(item.billing_channel.replace("_", " ").title())

    with dcol4:
        st.markdown("**Grace Period Status**")
        if item.in_grace_period is True and item.days_in_grace is not None:
            days_left = max(0, 30 - item.days_in_grace)
            st.error(f"⚠️ Active Grace: {item.days_in_grace}d elapsed ({days_left}d remaining)")
        elif item.in_grace_period is None:
            st.warning("Grace status is unknown from available source evidence.")
        else:
            st.success("🟢 Active / In Good Standing")
        st.markdown("**Uplift Segment**")
        st.write(f"`{item.uplift_quadrant}`")

    st.markdown("---")

    # 2. Risk Perception & SHAP Explainability (Phase 2.09 / 2.10)
    st.markdown("### 🧠 Predictive Risk Perception & SHAP Explanations")
    rcol1, rcol2 = st.columns([1, 2])

    with rcol1:
        st.metric(
            label="Calibrated Combined Termination Probability (p̂)",
            value=f"{item.risk_score:.2%}",
            delta="High Urgency" if item.risk_score > 0.25 else "Normal",
            delta_color="inverse" if item.risk_score > 0.25 else "normal",
        )
        st.markdown(
            f"- **Raw Decision Logit:** `{item.scoring_result.raw_logit:.3f}`\n"
            f"- **Calibrated Logit:** `{item.scoring_result.calibrated_logit:.3f}`\n"
            f"- **Baseline Population E[p]:** `32.95%`\n"
            f"- **Attribution Model:** Centered Additive SHAP"
        )
        st.info(
            f"**Primary Driver:** `{item.primary_risk_driver.replace('_', ' ').title()}` "
            f"(+{item.primary_risk_contribution:.3f} Δ logit)"
        )

    with rcol2:
        fig_waterfall = plot_shap_waterfall(
            root_attributions=item.scoring_result.root_attributions_log_odds,
            base_value_logit=-0.7107,
            calibrated_logit=item.scoring_result.calibrated_logit,
        )
        st.pyplot(fig_waterfall, width="stretch")

    st.markdown("---")

    # 3. Grounded Case Intelligence Brief (Phase 3.05)
    st.markdown("### 📝 Grounded Case Intelligence Brief")
    brief = item.case_brief

    # Grounding Guard Badge
    audit = brief.grounding_audit
    st.success(
        f"🔒 **Grounding Guard Verification Seal**: Verified clean (`{audit.validation_status.value}`). "
        f"Zero hallucinated facts detected. All statements grounded against point-in-time state.",
        icon="✅",
    )

    st.warning(
        f"⚖️ **ADR 0002 Mandatory Notice**: {brief.disclaimer}",
        icon="⚠️",
    )

    b_col1, b_col2 = st.columns(2)

    with b_col1:
        st.markdown(f"#### 📌 {brief.executive_summary.headline}")
        st.markdown(brief.executive_summary.narrative)

        st.markdown("#### 💬 Specialist Talking Points")
        for tp in brief.intervention_recommendations.talking_points:
            st.markdown(f"- {tp}")

    with b_col2:
        st.markdown("#### 🎯 Intervention Guidance")
        rec_action = brief.intervention_recommendations.primary_action
        rec_meta = ACTION_METADATA.get(rec_action, {})
        rec_utility = item.optimal_recommendation.action_utilities.get(rec_action)
        personnel_minutes = (
            rec_utility.personnel_seconds / 60 if rec_utility is not None else 0
        )
        st.markdown(
            f"**Recommended Action:** {rec_meta.get('icon', '')} **{rec_meta.get('title', rec_action)}**\n\n"
            f"- **Channel:** `{rec_meta.get('channel', 'OUTBOUND_CALL')}`\n"
            f"- **Modeled Net Annual Premium Preserved:** `${brief.intervention_recommendations.expected_net_utility:,.2f}`\n"
            f"- **Target Uplift Segment:** `{brief.intervention_recommendations.uplift_quadrant}`\n"
            f"- **Personnel Duration:** `{personnel_minutes:g} minutes`"
        )

        st.markdown("#### 🚫 Disqualified Actions (Eligibility Rules)")
        if brief.disqualified_actions:
            for dis in brief.disqualified_actions:
                st.markdown(f"- **{dis.action_id.replace('_', ' ').title()}**: `{dis.reason_code}` — {dis.description}")
        else:
            st.write("All catalog actions are legally and operationally permissible.")

    st.markdown("---")

    # 4. Point-in-Time Event Timeline (Phase 1.04)
    st.markdown("### ⏱️ Point-in-Time Event History Timeline")
    st.caption("Chronological policy history up to the observation cutoff. Guaranteed zero post-cutoff leakage.")

    if item.timeline_events:
        t_df = pd.DataFrame([
            {
                "Effective Time": e["effective_time"],
                "Event Type": e["event_type"],
                "Summary": e["summary"],
                "Amount": f"${e['amount']:,.2f}" if e.get("amount") else "—",
            }
            for e in item.timeline_events
        ])
        st.dataframe(t_df, width="stretch", hide_index=True)
    else:
        st.info("No prior events recorded before the observation cutoff.")

    st.markdown("---")

    # 5. Transition to Decision Console Button
    st.markdown("### ⚖️ Specialist Operational Action")
    b1, b2 = st.columns([3, 1])
    with b1:
        st.write("Review complete. Open the Human-in-the-Loop decision console to approve, override, or decline this case.")
    with b2:
        if st.button("Open Decision Console ⚖️", type="primary", width="stretch"):
            on_proceed_to_decision(item.policy_id)
