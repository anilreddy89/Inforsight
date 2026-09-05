"""Deterministic action eligibility rules engine.

This engine enforces business, legal, and regulatory boundaries on candidate
conservation actions under ADR 0002. It has zero dependency on predictive model
scores, probability thresholds, or loss matrices.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .invariants import (
    evaluate_channel_consent,
    evaluate_contact_cooling_off,
    evaluate_grace_period,
    evaluate_legal_freeze,
    evaluate_policy_viability,
    evaluate_tenure_bounds,
)
from .models import (
    ActionEligibilityResult,
    ConservationActionDefinition,
    EligibleActionSet,
    PolicyContext,
)
from .reasons import DisqualificationReasonCode


def get_standard_action_catalog() -> tuple[ConservationActionDefinition, ...]:
    """Return standard conservation actions conforming to Phase 3.01 schema."""
    return (
        ConservationActionDefinition(
            action_id="act_courtesy_reminder_v1",
            action_type="courtesy_reminder",
            channel="sms",
            direct_cost_usd=1.50,
            personnel_hours=0.0,
            regulatory_cooling_off_days=30,
            minimum_policy_tenure_days=30,
            maximum_policy_tenure_days=None,
            requires_grace_period=False,
        ),
        ConservationActionDefinition(
            action_id="act_grace_period_consultation_v1",
            action_type="grace_period_consultation",
            channel="phone",
            direct_cost_usd=25.00,
            personnel_hours=0.5,
            regulatory_cooling_off_days=30,
            minimum_policy_tenure_days=60,
            maximum_policy_tenure_days=None,
            requires_grace_period=True,
        ),
        ConservationActionDefinition(
            action_id="act_specialist_phone_outreach_v1",
            action_type="specialist_phone_outreach",
            channel="phone",
            direct_cost_usd=65.00,
            personnel_hours=1.0,
            regulatory_cooling_off_days=30,
            minimum_policy_tenure_days=90,
            maximum_policy_tenure_days=None,
            requires_grace_period=False,
        ),
        ConservationActionDefinition(
            action_id="act_payment_remediation_v1",
            action_type="payment_method_remediation",
            channel="sms",
            direct_cost_usd=3.00,
            personnel_hours=0.1,
            regulatory_cooling_off_days=14,
            minimum_policy_tenure_days=30,
            maximum_policy_tenure_days=None,
            requires_grace_period=False,
        ),
        ConservationActionDefinition(
            action_id="act_abstain_do_not_disturb_v1",
            action_type="abstain",
            channel="none",
            direct_cost_usd=0.00,
            personnel_hours=0.0,
            regulatory_cooling_off_days=0,
            minimum_policy_tenure_days=0,
            maximum_policy_tenure_days=None,
            requires_grace_period=False,
        ),
    )


class EligibilityRulesEngine:
    """Pure deterministic evaluator enforcing legal, regulatory, and business boundaries."""

    def __init__(
        self,
        action_catalog: Sequence[ConservationActionDefinition] | None = None,
    ) -> None:
        self._action_catalog = (
            tuple(action_catalog) if action_catalog is not None else get_standard_action_catalog()
        )
        # Ensure abstain is present in the catalog
        if not any(a.action_type == "abstain" for a in self._action_catalog):
            self._action_catalog = self._action_catalog + (
                ConservationActionDefinition(
                    action_id="act_abstain_default_v1",
                    action_type="abstain",
                    channel="none",
                    direct_cost_usd=0.00,
                    personnel_hours=0.0,
                    regulatory_cooling_off_days=0,
                    minimum_policy_tenure_days=0,
                    requires_grace_period=False,
                ),
            )

    @property
    def action_catalog(self) -> tuple[ConservationActionDefinition, ...]:
        return self._action_catalog

    def evaluate(
        self,
        context: PolicyContext | Mapping[str, Any],
    ) -> EligibleActionSet:
        """Evaluate action eligibility for the provided policy context.

        Fails-closed safely if the context is missing required attributes or malformed.
        """
        # Fail-closed guard: ensure context is converted or verified
        if not isinstance(context, PolicyContext):
            try:
                context = PolicyContext.from_dict(context)
            except Exception as exc:
                return self._build_fail_closed_error_set(
                    policy_id=str(getattr(context, "policy_id", "unknown")),
                    reason_code=DisqualificationReasonCode.DISQUALIFIED_MISSING_REQUIRED_ATTRIBUTE.value,
                    detail=f"Fail-closed due to unparseable policy context: {exc}",
                )

        results: dict[str, ActionEligibilityResult] = {}
        eligible_actions_list: list[str] = []

        # 1. Check Legal / Claim / Dispute Freeze
        is_frozen, freeze_code, freeze_detail = evaluate_legal_freeze(context)
        if is_frozen:
            for action in self._action_catalog:
                if action.action_type == "abstain":
                    results[action.action_type] = ActionEligibilityResult(
                        action_type="abstain",
                        is_eligible=True,
                        disqualification_reasons=(),
                        disqualification_details=(),
                    )
                    eligible_actions_list.append("abstain")
                else:
                    results[action.action_type] = ActionEligibilityResult(
                        action_type=action.action_type,
                        is_eligible=False,
                        disqualification_reasons=(freeze_code or "DISQUALIFIED_LEGAL_DISPUTE_FREEZE",),
                        disqualification_details=(freeze_detail or "Action frozen due to legal/claim hold.",),
                    )
            return EligibleActionSet(
                policy_id=context.policy_id,
                as_of=context.as_of,
                is_frozen=True,
                freeze_reason=freeze_code,
                results=results,
                eligible_actions=tuple(eligible_actions_list),
            )

        # 2. Check Policy Viability
        is_viable, viability_code, viability_detail = evaluate_policy_viability(context)
        if not is_viable:
            for action in self._action_catalog:
                if action.action_type == "abstain":
                    results[action.action_type] = ActionEligibilityResult(
                        action_type="abstain",
                        is_eligible=True,
                        disqualification_reasons=(),
                        disqualification_details=(),
                    )
                    eligible_actions_list.append("abstain")
                else:
                    results[action.action_type] = ActionEligibilityResult(
                        action_type=action.action_type,
                        is_eligible=False,
                        disqualification_reasons=(viability_code or "DISQUALIFIED_POLICY_NOT_IN_FORCE",),
                        disqualification_details=(viability_detail or "Policy is not in force.",),
                    )
            return EligibleActionSet(
                policy_id=context.policy_id,
                as_of=context.as_of,
                is_frozen=False,
                freeze_reason=None,
                results=results,
                eligible_actions=tuple(eligible_actions_list),
            )

        # 3. Evaluate Individual Actions against invariants
        for action in self._action_catalog:
            if action.action_type == "abstain":
                results["abstain"] = ActionEligibilityResult(
                    action_type="abstain",
                    is_eligible=True,
                    disqualification_reasons=(),
                    disqualification_details=(),
                )
                eligible_actions_list.append("abstain")
                continue

            reasons: list[str] = []
            details: list[str] = []

            # Channel consent
            passed_chan, chan_code, chan_detail = evaluate_channel_consent(
                context, action.channel
            )
            if not passed_chan and chan_code:
                reasons.append(chan_code)
                if chan_detail:
                    details.append(chan_detail)

            # Contact fatigue / cooling off
            passed_cool, cool_code, cool_detail = evaluate_contact_cooling_off(
                context, action.regulatory_cooling_off_days
            )
            if not passed_cool and cool_code:
                reasons.append(cool_code)
                if cool_detail:
                    details.append(cool_detail)

            # Grace period prerequisite
            passed_grace, grace_code, grace_detail = evaluate_grace_period(
                context, action.requires_grace_period
            )
            if not passed_grace and grace_code:
                reasons.append(grace_code)
                if grace_detail:
                    details.append(grace_detail)

            # Policy tenure bounds
            passed_tenure, tenure_code, tenure_detail = evaluate_tenure_bounds(
                context,
                action.minimum_policy_tenure_days,
                action.maximum_policy_tenure_days,
            )
            if not passed_tenure and tenure_code:
                reasons.append(tenure_code)
                if tenure_detail:
                    details.append(tenure_detail)

            is_eligible = len(reasons) == 0
            if is_eligible:
                eligible_actions_list.append(action.action_type)

            results[action.action_type] = ActionEligibilityResult(
                action_type=action.action_type,
                is_eligible=is_eligible,
                disqualification_reasons=tuple(reasons),
                disqualification_details=tuple(details),
            )

        return EligibleActionSet(
            policy_id=context.policy_id,
            as_of=context.as_of,
            is_frozen=False,
            freeze_reason=None,
            results=results,
            eligible_actions=tuple(eligible_actions_list),
        )

    def _build_fail_closed_error_set(
        self,
        policy_id: str,
        reason_code: str,
        detail: str,
    ) -> EligibleActionSet:
        from datetime import datetime, timezone

        results: dict[str, ActionEligibilityResult] = {}
        for action in self._action_catalog:
            if action.action_type == "abstain":
                results["abstain"] = ActionEligibilityResult(
                    action_type="abstain",
                    is_eligible=True,
                    disqualification_reasons=(),
                    disqualification_details=(),
                )
            else:
                results[action.action_type] = ActionEligibilityResult(
                    action_type=action.action_type,
                    is_eligible=False,
                    disqualification_reasons=(reason_code,),
                    disqualification_details=(detail,),
                )

        return EligibleActionSet(
            policy_id=policy_id,
            as_of=datetime.now(timezone.utc),
            is_frozen=True,
            freeze_reason=reason_code,
            results=results,
            eligible_actions=("abstain",),
        )


def evaluate_action_eligibility(
    context: PolicyContext | Mapping[str, Any],
    action_catalog: Sequence[ConservationActionDefinition] | None = None,
) -> EligibleActionSet:
    """Convenience function evaluating policy context using standard rules engine."""
    engine = EligibilityRulesEngine(action_catalog=action_catalog)
    return engine.evaluate(context)

