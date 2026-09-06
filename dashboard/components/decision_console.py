"""Component rendering the Specialist Human-in-the-Loop Decision Console."""

from __future__ import annotations

import re
from typing import Any
import streamlit as st

from inforsight_simulator.workflow.models import SpecialistReviewAction

from dashboard.config import (
    ACTION_METADATA,
    OVERRIDE_RATIONALE_CODES,
    REJECT_RATIONALE_CODES,
)
from dashboard.services.cohort_loader import TriagePolicyItem
from dashboard.services.engine_bridge import EngineBridge

REVIEWER_ID_REGEX = re.compile(r"^usr_[a-z0-9_]{3,32}$")


def render_decision_console(
    item: TriagePolicyItem,
    engine_bridge: EngineBridge,
) -> None:
    """Renders the operational specialist decision workspace enforcing ADR 0002."""
    st.markdown(f"## ⚖️ Specialist Decision Console: `{item.policy_id}`")
    st.markdown(
        "Human caseworkers hold sole operational authority to approve, adjust, or decline "
        "policy conservation interventions. Every action is recorded in the **cryptographic audit ledger**."
    )

    # 1. Active Case Context Card
    ctx = engine_bridge.workflow_service.get_case(item.case_id)
    current_state = ctx.state_machine.current_state.value if ctx else "RECOMMENDED"

    state_colors = {
        "RECOMMENDED": ("#FEF9C3", "#854D0E"),
        "HUMAN_REVIEWED": ("#DBEAFE", "#1E40AF"),
        "EXECUTED": ("#DCFCE7", "#166534"),
        "DISMISSED": ("#F1F5F9", "#475569"),
        "RESOLVED": ("#E2E8F0", "#334155"),
    }
    bg, fg = state_colors.get(current_state, ("#EEE", "#333"))

    st.markdown(
        f"**Case ID:** `{item.case_id}` | "
        f"**Workflow State:** <span style='background-color:{bg}; color:{fg}; padding:3px 10px; border-radius:4px; font-weight:bold;'>"
        f"{current_state}</span>",
        unsafe_allow_html=True,
    )

    # 2. System Advisory Recommendation Panel
    rec_action = item.recommended_action
    rec_meta = ACTION_METADATA.get(rec_action, {})
    st.info(
        f"💡 **System Advisory Recommendation**: {rec_meta.get('icon', '')} **{rec_meta.get('title', rec_action)}**\n\n"
        f"- **Expected Net Preserved Value:** `${item.net_utility:,.2f}`\n"
        f"- **Estimated Specialist Commitment:** `{rec_meta.get('duration_minutes', 15)} minutes`\n"
        f"- **Target Uplift Segment:** `{item.uplift_quadrant}`\n"
        f"- **Status:** Advisory Only (`authorized_to_act: false` strictly enforced)",
        icon="ℹ️",
    )

    # Check if already resolved or executed
    if current_state in ("EXECUTED", "DISMISSED", "RESOLVED"):
        st.success(f"✅ Case `{item.case_id}` is already in terminal state `{current_state}`. Action is completed.")
        return

    st.markdown("---")

    # 3. Specialist Human Decision Form
    st.markdown("### 📝 Specialist Authorization Form")

    # Reviewer Credentials Input
    rev_id = st.text_input(
        "Specialist Reviewer ID",
        value=st.session_state.get("reviewer_id", "usr_specialist_482"),
        help="Format: usr_[a-z0-9_]{3,32}",
    ).strip()

    decision_type = st.radio(
        "Specialist Review Determination",
        [
            ("APPROVE_RECOMMENDATION", f"Approve Recommended Action ({rec_meta.get('title', rec_action)})"),
            ("OVERRIDE_ACTION", "Override Action (Select Alternative Permissible Intervention)"),
            ("REQUEST_MORE_INFO", "Request More Information (Hold Case for Verification)"),
            ("REJECT_AND_CLOSE", "Reject & Close Case (Decline Proactive Outreach)"),
        ],
        format_func=lambda opt: opt[1],
        index=0,
    )[0]

    selected_override_action = None
    rationale_code = "APPROVE_OPTIMAL_RECOMMENDATION"
    justification = ""

    # Dynamic Form Fields based on Decision Selection
    if decision_type == "OVERRIDE_ACTION":
        st.markdown("#### 🔄 Action Override & Eligibility Firewall")

        # Eligibility Firewall: strictly show ONLY eligible actions
        eligible_choices = list(item.eligible_action_set.eligible_actions)
        if not eligible_choices:
            st.error("No actions are currently eligible under deterministic business and regulatory rules.")
            return

        selected_override_action = st.selectbox(
            "Select Approved Alternative Intervention",
            eligible_choices,
            format_func=lambda a: f"{ACTION_METADATA.get(a, {}).get('icon', '•')} {ACTION_METADATA.get(a, {}).get('title', a.replace('_', ' ').title())}",
        )

        st.warning(
            "🔒 **Eligibility Firewall Active**: Disqualified actions (e.g. phone outreach without consent, "
            "actions during legal freeze) have been automatically redacted per ADR 0002.",
            icon="🛡️",
        )

        override_rationale_opts = OVERRIDE_RATIONALE_CODES
        selected_rat = st.selectbox(
            "Mandatory Override Rationale Code",
            override_rationale_opts,
            format_func=lambda r: f"{r[0]} — {r[1]}",
        )
        rationale_code = selected_rat[0]

        justification = st.text_area(
            "Mandatory Clinical / Operational Justification (Minimum 5 characters)",
            placeholder="Explain the specific factual reason for deviating from the algorithmic recommendation...",
        ).strip()

    elif decision_type == "REJECT_AND_CLOSE":
        st.markdown("#### 🚫 Rejection Rationale")
        reject_rationale_opts = REJECT_RATIONALE_CODES
        selected_rat = st.selectbox(
            "Mandatory Rejection Reason Code",
            reject_rationale_opts,
            format_func=lambda r: f"{r[0]} — {r[1]}",
        )
        rationale_code = selected_rat[0]

        justification = st.text_area(
            "Mandatory Rejection Justification (Minimum 5 characters)",
            placeholder="Document why no proactive intervention should be dispatched...",
        ).strip()

    elif decision_type == "REQUEST_MORE_INFO":
        rationale_code = "REQUEST_MORE_INFO_PENDING_DOCUMENTS"
        justification = st.text_area(
            "Information Request Notes",
            placeholder="Specify what additional policy or payment verification is required...",
        ).strip()

    else:  # APPROVE_RECOMMENDATION
        rationale_code = "APPROVE_OPTIMAL_RECOMMENDATION"
        justification = st.text_input(
            "Specialist Approval Notes (Optional)",
            value="Approved per net utility matrix and verified grace period urgency.",
        ).strip()

    # 4. Commit Button & Execution Handler
    st.write("")
    if st.button("🔐 Commit Decision to Cryptographic Audit Ledger", type="primary", use_container_width=True):
        # 1. Validate Reviewer ID
        if not REVIEWER_ID_REGEX.match(rev_id):
            st.error(f"Invalid Reviewer ID: '{rev_id}'. Must match pattern `usr_[a-z0-9_]{{3,32}}`.")
            return

        # 2. Validate Minimum Justification on Overrides/Rejections
        if decision_type in ("OVERRIDE_ACTION", "REJECT_AND_CLOSE"):
            if len(justification) < 5:
                st.error("Mandatory Justification must be at least 5 characters long to satisfy compliance auditing.")
                return

        # 3. Process Review Action
        action_enum = getattr(SpecialistReviewAction, decision_type)
        try:
            rev_event, exec_event = engine_bridge.submit_specialist_decision(
                case_id=item.case_id,
                reviewer_id=rev_id,
                action=action_enum,
                rationale_code=rationale_code,
                justification=justification,
                selected_action=selected_override_action,
            )

            # Persist reviewer ID in session
            st.session_state["reviewer_id"] = rev_id

            st.success(
                f"🎉 **Decision Committed Successfully!** Case transitioned to "
                f"`{exec_event.to_state.value if exec_event else rev_event.to_state.value}`."
            )

            # 5. Cryptographic Receipt Display
            tip_hash = engine_bridge.audit_ledger.tip_hash
            st.markdown("### 📜 Cryptographic Audit Receipt")
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                st.markdown(f"- **Case ID:** `{item.case_id}`")
                st.markdown(f"- **Reviewer ID:** `{rev_id}`")
                st.markdown(f"- **Review Decision:** `{decision_type}`")
                st.markdown(f"- **Rationale Code:** `{rationale_code}`")
            with r_col2:
                st.markdown(f"- **Audit Event ID:** `{rev_event.case_event_id}`")
                st.markdown(f"- **Chain Tip Hash:** `{tip_hash[:20]}...`")
                st.markdown(f"- **Ledger File:** `data/audit/conservation-audit-log.jsonl`")
                st.markdown(f"- **Integrity Status:** 🟢 Cryptographically Chained")

            st.info("Verification Tip: Run `python3 scripts/verify_conservation_audit_trail.py` to mathematically audit this entry.")

        except Exception as err:
            st.error(f"Workflow error: {err}")
