"""Deterministic action eligibility rules engine.

This engine enforces business, legal, and regulatory boundaries on candidate
conservation actions under ADR 0002. It has zero dependency on predictive model
scores, probability thresholds, or loss matrices.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from inforsight_simulator.domain_snapshot import DomainSnapshot
from inforsight_simulator.semantic_catalog import SemanticCatalog, load_semantic_catalog
from inforsight_simulator.safety_evidence import SafetyEvidence

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


def get_standard_action_catalog(
    catalog: SemanticCatalog | None = None,
) -> tuple[ConservationActionDefinition, ...]:
    """Adapt the canonical RH catalog into the legacy Phase 3 action type."""

    semantic_catalog = catalog or load_semantic_catalog()
    global_requirements = (
        "has_active_claim", "has_legal_hold", "has_registered_dispute"
    )
    channel_requirements = {
        "sms": ("sms_opt_out",),
        "email": ("email_opt_out",),
        "phone": ("phone_opt_out", "dnc_registered"),
        "none": (),
    }
    return tuple(
        ConservationActionDefinition(
            action_id=str(item["action_id"]),
            action_type=str(item["action_type"]),
            channel=str(item["channel"]),
            direct_cost_usd=int(item["direct_cost_cents"]) / 100,
            personnel_hours=int(item["personnel_seconds"]) / 3600,
            regulatory_cooling_off_days=int(item["regulatory_cooling_off_days"]),
            minimum_policy_tenure_days=int(item["minimum_policy_tenure_days"]),
            maximum_policy_tenure_days=(
                None if item["maximum_policy_tenure_days"] is None
                else int(item["maximum_policy_tenure_days"])
            ),
            requires_grace_period=bool(item["requires_grace_period"]),
            required_safety_evidence=(
                () if item["action_type"] == "abstain" else
                global_requirements + channel_requirements[str(item["channel"])]
            ),
        )
        for item in semantic_catalog.data["actions"]
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

        global_safety = (
            context.has_active_claim, context.has_legal_hold,
            context.has_registered_dispute,
        )
        # A confirmed global block dominates missing companion fields. This keeps
        # an affirmative hold effective even when the rest of the record is partial.
        if not any(value is True for value in global_safety) and any(
            value is None for value in global_safety
        ):
            return self._build_unavailable_set(
                context.policy_id,
                context.as_of.isoformat().replace("+00:00", "Z"),
                reason=DisqualificationReasonCode.DISQUALIFIED_MISSING_SAFETY_EVIDENCE.value,
            )

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
            required_channel_facts = tuple(
                getattr(context, field) for field in action.required_safety_evidence
                if field not in {"has_active_claim", "has_legal_hold", "has_registered_dispute"}
            )
            if any(value is None for value in required_channel_facts):
                passed_chan, chan_code, chan_detail = (
                    False,
                    DisqualificationReasonCode.DISQUALIFIED_MISSING_SAFETY_EVIDENCE.value,
                    f"Confirmed {action.channel} consent evidence is required.",
                )
            else:
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

    def evaluate_snapshot(
        self, snapshot: DomainSnapshot, catalog: SemanticCatalog,
        safety_evidence: SafetyEvidence | None = None,
    ) -> EligibleActionSet:
        """Bridge a canonical snapshot into legacy rules, failing unavailable facts closed."""

        snapshot.validate_identity(catalog)
        required_domain = (
            snapshot.status,
            snapshot.in_grace_period,
        )
        if any(value is None or value == "unknown" for value in required_domain):
            return self._build_unavailable_set(
                snapshot.policy_id, snapshot.as_of, snapshot_id=snapshot.snapshot_id
            )
        if safety_evidence is None:
            return self._build_unavailable_set(
                snapshot.policy_id, snapshot.as_of,
                reason=DisqualificationReasonCode.DISQUALIFIED_MISSING_SAFETY_EVIDENCE.value,
                snapshot_id=snapshot.snapshot_id,
            )
        safety_evidence.validate_context(
            policy_id=snapshot.policy_id, as_of=snapshot.as_of,
            snapshot_id=snapshot.snapshot_id,
        )
        context = PolicyContext(
            policy_id=snapshot.policy_id,
            as_of=datetime.fromisoformat(snapshot.as_of.replace("Z", "+00:00")),
            status=snapshot.status,
            tenure_days=snapshot.tenure_days,
            in_grace_period=bool(snapshot.in_grace_period),
            days_past_due=snapshot.days_past_due,
            has_active_claim=safety_evidence.has_active_claim,
            has_legal_hold=safety_evidence.has_legal_hold,
            has_registered_dispute=safety_evidence.has_registered_dispute,
            sms_opt_out=safety_evidence.sms_opt_out,
            email_opt_out=safety_evidence.email_opt_out,
            phone_opt_out=safety_evidence.phone_opt_out,
            dnc_registered=safety_evidence.dnc_registered,
        )
        result = self.evaluate(context)
        return EligibleActionSet(
            **{**result.__dict__, "snapshot_id": snapshot.snapshot_id,
               "safety_evidence_id": safety_evidence.evidence_id}
        )

    def _build_unavailable_set(
        self, policy_id: str, as_of: str, *,
        reason: str = "insufficient_domain_evidence",
        snapshot_id: str | None = None,
    ) -> EligibleActionSet:
        results = {
            action.action_type: ActionEligibilityResult(
                action_type=action.action_type,
                is_eligible=False,
                disqualification_reasons=(reason,),
                disqualification_details=(
                    "Required domain or safety evidence is unavailable at the snapshot cutoff.",
                ),
            )
            for action in self._action_catalog
        }
        return EligibleActionSet(
            policy_id=policy_id,
            as_of=datetime.fromisoformat(as_of.replace("Z", "+00:00")),
            is_frozen=True,
            freeze_reason=reason,
            results=results,
            eligible_actions=(),
            snapshot_id=snapshot_id,
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
