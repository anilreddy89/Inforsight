"""Pure predicate functions evaluating deterministic eligibility invariants.

Each invariant function operates strictly on the immutable PolicyContext and
action properties, returning a tuple:
    (passes_invariant: bool, reason_code: str | None, detail_message: str | None)

Under ADR 0002, these invariants have zero dependency on ML models or scores.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .reasons import DisqualificationReasonCode

if TYPE_CHECKING:
    from .models import PolicyContext


def evaluate_legal_freeze(
    context: PolicyContext,
) -> tuple[bool, str | None, str | None]:
    """Check whether an active claim, legal hold, or dispute freezes outreach.

    Returns:
        (is_frozen, reason_code, detail_message)
    """
    if context.has_legal_hold:
        return (
            True,
            DisqualificationReasonCode.DISQUALIFIED_LEGAL_HOLD.value,
            "Policy is under legal hold; all proactive outreach is frozen.",
        )
    if context.has_active_claim:
        return (
            True,
            DisqualificationReasonCode.DISQUALIFIED_ACTIVE_CLAIM.value,
            "Policy has an active claim pending; conservation outreach is frozen.",
        )
    if context.has_registered_dispute:
        return (
            True,
            DisqualificationReasonCode.DISQUALIFIED_LEGAL_DISPUTE_FREEZE.value,
            "Policy has an active registered dispute; outreach is legally restricted.",
        )
    return False, None, None


def evaluate_policy_viability(
    context: PolicyContext,
) -> tuple[bool, str | None, str | None]:
    """Check whether the policy is currently in force and viable for conservation.

    Returns:
        (is_viable, reason_code, detail_message)
    """
    status = context.status.lower()
    if status in ("active", "grace_period"):
        return True, None, None

    if status == "lapsed":
        return (
            False,
            DisqualificationReasonCode.DISQUALIFIED_POLICY_LAPSED.value,
            f"Policy status is '{context.status}' (lapsed); requires formal reinstatement.",
        )
    if status == "surrendered":
        return (
            False,
            DisqualificationReasonCode.DISQUALIFIED_POLICY_SURRENDERED.value,
            f"Policy status is '{context.status}' (surrendered); coverage has terminated.",
        )
    if status == "terminated":
        return (
            False,
            DisqualificationReasonCode.DISQUALIFIED_POLICY_TERMINATED.value,
            f"Policy status is '{context.status}' (terminated).",
        )
    if status == "matured":
        return (
            False,
            DisqualificationReasonCode.DISQUALIFIED_POLICY_MATURED.value,
            f"Policy status is '{context.status}' (matured); no conservation required.",
        )

    return (
        False,
        DisqualificationReasonCode.DISQUALIFIED_POLICY_NOT_IN_FORCE.value,
        f"Policy status '{context.status}' is not viable for active conservation.",
    )


def evaluate_channel_consent(
    context: PolicyContext, channel: str
) -> tuple[bool, str | None, str | None]:
    """Check channel opt-out and Do Not Call constraints.

    Returns:
        (is_allowed, reason_code, detail_message)
    """
    norm_channel = channel.lower()
    if norm_channel == "sms":
        if context.sms_opt_out:
            return (
                False,
                DisqualificationReasonCode.DISQUALIFIED_CHANNEL_OPT_OUT_SMS.value,
                "Policyholder has opted out of SMS messages.",
            )
        return True, None, None

    if norm_channel == "email":
        if context.email_opt_out:
            return (
                False,
                DisqualificationReasonCode.DISQUALIFIED_CHANNEL_OPT_OUT_EMAIL.value,
                "Policyholder has opted out of email communications.",
            )
        return True, None, None

    if norm_channel == "phone":
        if context.phone_opt_out:
            return (
                False,
                DisqualificationReasonCode.DISQUALIFIED_CHANNEL_OPT_OUT_PHONE.value,
                "Policyholder has opted out of outbound telephone calls.",
            )
        if context.dnc_registered:
            return (
                False,
                DisqualificationReasonCode.DISQUALIFIED_DNC_REGISTRY.value,
                "Phone number is registered on Do Not Call registry.",
            )
        return True, None, None

    # Other channels (postal_mail, in_app_notification, none) are permitted
    return True, None, None


def evaluate_contact_cooling_off(
    context: PolicyContext, cooling_off_days: int
) -> tuple[bool, str | None, str | None]:
    """Check regulatory contact fatigue and cooling-off period.

    Returns:
        (is_cooled_off, reason_code, detail_message)
    """
    if cooling_off_days <= 0:
        return True, None, None

    if context.last_contact_date is None:
        return True, None, None

    elapsed_days = (context.as_of - context.last_contact_date).days
    if elapsed_days < cooling_off_days:
        return (
            False,
            DisqualificationReasonCode.DISQUALIFIED_CONTACT_COOLING_OFF_ACTIVE.value,
            (
                f"Recent contact occurred {elapsed_days} days ago, within the "
                f"mandatory {cooling_off_days}-day cooling-off window."
            ),
        )

    return True, None, None


def evaluate_grace_period(
    context: PolicyContext, requires_grace: bool
) -> tuple[bool, str | None, str | None]:
    """Check whether grace period requirements are satisfied.

    Returns:
        (is_satisfied, reason_code, detail_message)
    """
    if not requires_grace:
        return True, None, None

    in_grace = context.in_grace_period or context.status.lower() == "grace_period"
    if not in_grace:
        return (
            False,
            DisqualificationReasonCode.DISQUALIFIED_GRACE_PERIOD_REQUIRED.value,
            "Action requires active grace period status, but policy is not in grace.",
        )

    return True, None, None


def evaluate_tenure_bounds(
    context: PolicyContext, min_days: int, max_days: int | None
) -> tuple[bool, str | None, str | None]:
    """Check whether policy tenure satisfies min and max boundaries.

    Returns:
        (is_within_bounds, reason_code, detail_message)
    """
    if context.tenure_days < min_days:
        return (
            False,
            DisqualificationReasonCode.DISQUALIFIED_MINIMUM_TENURE_NOT_MET.value,
            (
                f"Policy tenure of {context.tenure_days} days is less than the "
                f"required minimum of {min_days} days."
            ),
        )

    if max_days is not None and context.tenure_days > max_days:
        return (
            False,
            DisqualificationReasonCode.DISQUALIFIED_MAXIMUM_TENURE_EXCEEDED.value,
            (
                f"Policy tenure of {context.tenure_days} days exceeds the "
                f"allowed maximum of {max_days} days."
            ),
        )

    return True, None, None

