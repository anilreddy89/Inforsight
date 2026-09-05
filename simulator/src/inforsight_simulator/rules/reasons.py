"""Canonical disqualification reason codes for policy conservation actions.

Under ADR 0002, all non-eligibility determinations must be auditable,
deterministic, and traceable to explicit business, legal, or regulatory rules.
"""

from __future__ import annotations

from enum import Enum


class DisqualificationReasonCode(str, Enum):
    """Auditable disqualification reason codes for intervention candidates."""

    # Invariant 1: Legal / Claim / Dispute Freeze
    DISQUALIFIED_LEGAL_DISPUTE_FREEZE = "DISQUALIFIED_LEGAL_DISPUTE_FREEZE"
    DISQUALIFIED_ACTIVE_CLAIM = "DISQUALIFIED_ACTIVE_CLAIM"
    DISQUALIFIED_LEGAL_HOLD = "DISQUALIFIED_LEGAL_HOLD"

    # Invariant 2: Policy Viability
    DISQUALIFIED_POLICY_NOT_IN_FORCE = "DISQUALIFIED_POLICY_NOT_IN_FORCE"
    DISQUALIFIED_POLICY_TERMINATED = "DISQUALIFIED_POLICY_TERMINATED"
    DISQUALIFIED_POLICY_SURRENDERED = "DISQUALIFIED_POLICY_SURRENDERED"
    DISQUALIFIED_POLICY_LAPSED = "DISQUALIFIED_POLICY_LAPSED"
    DISQUALIFIED_POLICY_MATURED = "DISQUALIFIED_POLICY_MATURED"

    # Invariant 3: Channel Opt-Out & Consent
    DISQUALIFIED_CHANNEL_OPT_OUT_SMS = "DISQUALIFIED_CHANNEL_OPT_OUT_SMS"
    DISQUALIFIED_CHANNEL_OPT_OUT_EMAIL = "DISQUALIFIED_CHANNEL_OPT_OUT_EMAIL"
    DISQUALIFIED_CHANNEL_OPT_OUT_PHONE = "DISQUALIFIED_CHANNEL_OPT_OUT_PHONE"
    DISQUALIFIED_DNC_REGISTRY = "DISQUALIFIED_DNC_REGISTRY"

    # Invariant 4: Contact Fatigue & Regulatory Cooling-Off
    DISQUALIFIED_CONTACT_COOLING_OFF_ACTIVE = (
        "DISQUALIFIED_CONTACT_COOLING_OFF_ACTIVE"
    )

    # Invariant 5: Grace Period Requirement
    DISQUALIFIED_GRACE_PERIOD_REQUIRED = "DISQUALIFIED_GRACE_PERIOD_REQUIRED"

    # Invariant 6: Policy Tenure Boundaries
    DISQUALIFIED_MINIMUM_TENURE_NOT_MET = "DISQUALIFIED_MINIMUM_TENURE_NOT_MET"
    DISQUALIFIED_MAXIMUM_TENURE_EXCEEDED = "DISQUALIFIED_MAXIMUM_TENURE_EXCEEDED"

    # Fail-Closed Safety
    DISQUALIFIED_MISSING_REQUIRED_ATTRIBUTE = (
        "DISQUALIFIED_MISSING_REQUIRED_ATTRIBUTE"
    )
    DISQUALIFIED_AMBIGUOUS_STATE = "DISQUALIFIED_AMBIGUOUS_STATE"


DISQUALIFICATION_DESCRIPTIONS: dict[DisqualificationReasonCode, str] = {
    DisqualificationReasonCode.DISQUALIFIED_LEGAL_DISPUTE_FREEZE: (
        "Policy has an active registered dispute, legally freezing all outreach."
    ),
    DisqualificationReasonCode.DISQUALIFIED_ACTIVE_CLAIM: (
        "Policy has an active insurance claim in progress, freezing conservation outreach."
    ),
    DisqualificationReasonCode.DISQUALIFIED_LEGAL_HOLD: (
        "Policy is under regulatory or legal litigation hold, freezing outreach."
    ),
    DisqualificationReasonCode.DISQUALIFIED_POLICY_NOT_IN_FORCE: (
        "Policy is not currently in force and cannot receive conservation interventions."
    ),
    DisqualificationReasonCode.DISQUALIFIED_POLICY_TERMINATED: (
        "Policy has terminated and is ineligible for active conservation."
    ),
    DisqualificationReasonCode.DISQUALIFIED_POLICY_SURRENDERED: (
        "Policy has been surrendered and coverage has ceased."
    ),
    DisqualificationReasonCode.DISQUALIFIED_POLICY_LAPSED: (
        "Policy has already lapsed; requires formal reinstatement rather than conservation."
    ),
    DisqualificationReasonCode.DISQUALIFIED_POLICY_MATURED: (
        "Policy has reached maturity; no further premiums or conservation required."
    ),
    DisqualificationReasonCode.DISQUALIFIED_CHANNEL_OPT_OUT_SMS: (
        "Policyholder has revoked consent or opted out of SMS notifications."
    ),
    DisqualificationReasonCode.DISQUALIFIED_CHANNEL_OPT_OUT_EMAIL: (
        "Policyholder has opted out of email communications."
    ),
    DisqualificationReasonCode.DISQUALIFIED_CHANNEL_OPT_OUT_PHONE: (
        "Policyholder has opted out of outbound telephone outreach."
    ),
    DisqualificationReasonCode.DISQUALIFIED_DNC_REGISTRY: (
        "Phone number is registered on internal or national Do Not Call lists."
    ),
    DisqualificationReasonCode.DISQUALIFIED_CONTACT_COOLING_OFF_ACTIVE: (
        "Outreach occurred within mandatory regulatory cooling-off window (30 days)."
    ),
    DisqualificationReasonCode.DISQUALIFIED_GRACE_PERIOD_REQUIRED: (
        "Action strictly requires the policy to be in active grace period status."
    ),
    DisqualificationReasonCode.DISQUALIFIED_MINIMUM_TENURE_NOT_MET: (
        "Policy tenure does not satisfy the minimum tenure requirement for this action."
    ),
    DisqualificationReasonCode.DISQUALIFIED_MAXIMUM_TENURE_EXCEEDED: (
        "Policy tenure exceeds the maximum allowable tenure for this action."
    ),
    DisqualificationReasonCode.DISQUALIFIED_MISSING_REQUIRED_ATTRIBUTE: (
        "Fail-closed: required policy or applicant attribute is missing or null."
    ),
    DisqualificationReasonCode.DISQUALIFIED_AMBIGUOUS_STATE: (
        "Fail-closed: policy state contains contradictory or unparseable values."
    ),
}

