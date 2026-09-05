"""Tests for Phase 3.02 deterministic action eligibility rules engine.

Verifies:
1. Legal / Dispute Freeze Invariant (disqualify_all except abstain).
2. Policy Viability Invariant (reject lapsed/surrendered/matured/terminated).
3. Channel Opt-Out & DNC Preferences.
4. Regulatory Contact Cooling-Off Window (30-day fatigue guard).
5. Grace Period Prerequisite.
6. Policy Tenure Boundaries.
7. Fail-Closed Safety on missing/malformed attributes.
8. Complete Decoupling from Predictive ML (Static AST enforcement of ADR 0002).
9. Property-based invariant fuzzing.
"""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random
import unittest

from inforsight_simulator.rules import (
    ActionEligibilityResult,
    ConservationActionDefinition,
    DisqualificationReasonCode,
    DISQUALIFICATION_DESCRIPTIONS,
    EligibilityRulesEngine,
    EligibleActionSet,
    PolicyContext,
    evaluate_action_eligibility,
    get_standard_action_catalog,
)


def _make_sample_context(**kwargs) -> PolicyContext:
    """Helper creating a valid baseline in-force policy context."""
    defaults = {
        "policy_id": "pol_synthetic_1001",
        "as_of": datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc),
        "status": "active",
        "tenure_days": 180,
        "in_grace_period": False,
        "days_past_due": 0,
        "has_active_claim": False,
        "has_legal_hold": False,
        "has_registered_dispute": False,
        "sms_opt_out": False,
        "email_opt_out": False,
        "phone_opt_out": False,
        "dnc_registered": False,
        "last_contact_date": None,
    }
    defaults.update(kwargs)
    return PolicyContext(**defaults)


class TestRulesEligibility(unittest.TestCase):
    """Exhaustive test suite for the deterministic eligibility rules engine."""

    def test_standard_catalog_structure(self) -> None:
        """Verify standard catalog contains all 5 actions conforming to Phase 3.01."""
        catalog = get_standard_action_catalog()
        self.assertEqual(len(catalog), 5)
        action_types = {a.action_type for a in catalog}
        expected = {
            "courtesy_reminder",
            "grace_period_consultation",
            "specialist_phone_outreach",
            "payment_method_remediation",
            "abstain",
        }
        self.assertEqual(action_types, expected)

        # Abstain must be free and require zero personnel time
        abstain_act = next(a for a in catalog if a.action_type == "abstain")
        self.assertEqual(abstain_act.direct_cost_usd, 0.0)
        self.assertEqual(abstain_act.personnel_hours, 0.0)
        self.assertEqual(abstain_act.channel, "none")

    def test_baseline_eligible_actions(self) -> None:
        """A standard in-force policy with 180 days tenure has allowed non-grace actions."""
        ctx = _make_sample_context()
        result_set = evaluate_action_eligibility(ctx)

        self.assertFalse(result_set.is_frozen)
        self.assertIsNone(result_set.freeze_reason)

        # Courtesy reminder and payment remediation are eligible
        self.assertTrue(result_set.is_eligible("courtesy_reminder"))
        self.assertTrue(result_set.is_eligible("payment_method_remediation"))
        self.assertTrue(result_set.is_eligible("specialist_phone_outreach"))
        self.assertTrue(result_set.is_eligible("abstain"))

        # Grace period consultation requires active grace period -> ineligible
        self.assertFalse(result_set.is_eligible("grace_period_consultation"))
        self.assertIn(
            DisqualificationReasonCode.DISQUALIFIED_GRACE_PERIOD_REQUIRED.value,
            result_set.get_reasons("grace_period_consultation"),
        )

    def test_legal_dispute_freeze(self) -> None:
        """Active dispute legally freezes all outreach actions deterministically."""
        ctx = _make_sample_context(has_registered_dispute=True)
        result_set = evaluate_action_eligibility(ctx)

        self.assertTrue(result_set.is_frozen)
        self.assertEqual(
            result_set.freeze_reason,
            DisqualificationReasonCode.DISQUALIFIED_LEGAL_DISPUTE_FREEZE.value,
        )
        self.assertEqual(result_set.eligible_actions, ("abstain",))

        for action_type in ("courtesy_reminder", "grace_period_consultation", "specialist_phone_outreach", "payment_method_remediation"):
            self.assertFalse(result_set.is_eligible(action_type))
            self.assertIn(
                DisqualificationReasonCode.DISQUALIFIED_LEGAL_DISPUTE_FREEZE.value,
                result_set.get_reasons(action_type),
            )

    def test_active_claim_freeze(self) -> None:
        """Active claim freezes all conservation outreach deterministically."""
        ctx = _make_sample_context(has_active_claim=True)
        result_set = evaluate_action_eligibility(ctx)

        self.assertTrue(result_set.is_frozen)
        self.assertEqual(
            result_set.freeze_reason,
            DisqualificationReasonCode.DISQUALIFIED_ACTIVE_CLAIM.value,
        )
        self.assertEqual(result_set.eligible_actions, ("abstain",))
        self.assertFalse(result_set.is_eligible("courtesy_reminder"))
        self.assertTrue(result_set.is_eligible("abstain"))

    def test_legal_hold_freeze(self) -> None:
        """Legal hold freezes all conservation outreach deterministically."""
        ctx = _make_sample_context(has_legal_hold=True)
        result_set = evaluate_action_eligibility(ctx)

        self.assertTrue(result_set.is_frozen)
        self.assertEqual(
            result_set.freeze_reason,
            DisqualificationReasonCode.DISQUALIFIED_LEGAL_HOLD.value,
        )
        self.assertEqual(result_set.eligible_actions, ("abstain",))

    def test_policy_viability_invariants(self) -> None:
        """Non-in-force policies are disqualified from all active conservation outreach."""
        invalid_statuses = ("lapsed", "surrendered", "terminated", "matured", "cancelled")
        for status in invalid_statuses:
            with self.subTest(status=status):
                ctx = _make_sample_context(status=status)
                result_set = evaluate_action_eligibility(ctx)
                self.assertFalse(result_set.is_frozen)
                self.assertEqual(result_set.eligible_actions, ("abstain",))
                self.assertFalse(result_set.is_eligible("courtesy_reminder"))

    def test_channel_opt_out_sms(self) -> None:
        """Opting out of SMS disqualifies SMS actions, leaving phone actions eligible."""
        ctx = _make_sample_context(sms_opt_out=True)
        result_set = evaluate_action_eligibility(ctx)

        self.assertFalse(result_set.is_eligible("courtesy_reminder"))
        self.assertIn(
            DisqualificationReasonCode.DISQUALIFIED_CHANNEL_OPT_OUT_SMS.value,
            result_set.get_reasons("courtesy_reminder"),
        )
        self.assertFalse(result_set.is_eligible("payment_method_remediation"))

        # Phone action remains eligible
        self.assertTrue(result_set.is_eligible("specialist_phone_outreach"))

    def test_channel_opt_out_phone(self) -> None:
        """Opting out of phone outreach disqualifies phone interventions."""
        ctx = _make_sample_context(phone_opt_out=True)
        result_set = evaluate_action_eligibility(ctx)

        self.assertFalse(result_set.is_eligible("specialist_phone_outreach"))
        self.assertIn(
            DisqualificationReasonCode.DISQUALIFIED_CHANNEL_OPT_OUT_PHONE.value,
            result_set.get_reasons("specialist_phone_outreach"),
        )
        # SMS remains eligible
        self.assertTrue(result_set.is_eligible("courtesy_reminder"))

    def test_dnc_registry(self) -> None:
        """Do Not Call registration disqualifies phone outreach."""
        ctx = _make_sample_context(dnc_registered=True)
        result_set = evaluate_action_eligibility(ctx)

        self.assertFalse(result_set.is_eligible("specialist_phone_outreach"))
        self.assertIn(
            DisqualificationReasonCode.DISQUALIFIED_DNC_REGISTRY.value,
            result_set.get_reasons("specialist_phone_outreach"),
        )
        self.assertTrue(result_set.is_eligible("courtesy_reminder"))

    def test_contact_cooling_off_window(self) -> None:
        """Recent outreach within cooling-off period disqualifies active outreach."""
        as_of = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)

        # Contact 10 days ago: blocks 30-day and 14-day actions
        ctx_10d = _make_sample_context(
            as_of=as_of,
            last_contact_date=as_of - timedelta(days=10),
        )
        res_10d = evaluate_action_eligibility(ctx_10d)
        self.assertFalse(res_10d.is_eligible("courtesy_reminder"))
        self.assertFalse(res_10d.is_eligible("payment_method_remediation"))
        self.assertIn(
            DisqualificationReasonCode.DISQUALIFIED_CONTACT_COOLING_OFF_ACTIVE.value,
            res_10d.get_reasons("courtesy_reminder"),
        )

        # Contact 20 days ago: 14-day payment remediation is eligible, 30-day actions are not
        ctx_20d = _make_sample_context(
            as_of=as_of,
            last_contact_date=as_of - timedelta(days=20),
        )
        res_20d = evaluate_action_eligibility(ctx_20d)
        self.assertFalse(res_20d.is_eligible("courtesy_reminder"))
        self.assertTrue(res_20d.is_eligible("payment_method_remediation"))

        # Contact 35 days ago: all pass cooling-off
        ctx_35d = _make_sample_context(
            as_of=as_of,
            last_contact_date=as_of - timedelta(days=35),
        )
        res_35d = evaluate_action_eligibility(ctx_35d)
        self.assertTrue(res_35d.is_eligible("courtesy_reminder"))
        self.assertTrue(res_35d.is_eligible("payment_method_remediation"))

    def test_grace_period_prerequisite(self) -> None:
        """Actions requiring active grace period pass when in grace, fail otherwise."""
        # Not in grace
        ctx_active = _make_sample_context(status="active", in_grace_period=False)
        res_active = evaluate_action_eligibility(ctx_active)
        self.assertFalse(res_active.is_eligible("grace_period_consultation"))

        # In grace (via flag or status)
        ctx_grace = _make_sample_context(
            status="grace_period",
            in_grace_period=True,
            days_past_due=15,
        )
        res_grace = evaluate_action_eligibility(ctx_grace)
        self.assertTrue(res_grace.is_eligible("grace_period_consultation"))

    def test_policy_tenure_bounds(self) -> None:
        """Tenure below minimum requirement disqualifies the action."""
        # 15 days tenure (< 30 days minimum for all active actions)
        ctx_new = _make_sample_context(tenure_days=15)
        res_new = evaluate_action_eligibility(ctx_new)

        self.assertFalse(res_new.is_eligible("courtesy_reminder"))
        self.assertIn(
            DisqualificationReasonCode.DISQUALIFIED_MINIMUM_TENURE_NOT_MET.value,
            res_new.get_reasons("courtesy_reminder"),
        )
        self.assertTrue(res_new.is_eligible("abstain"))

        # Custom action with maximum tenure
        custom_action = ConservationActionDefinition(
            action_id="act_new_policy_welcome_v1",
            action_type="courtesy_reminder",
            channel="email",
            direct_cost_usd=1.0,
            personnel_hours=0.0,
            regulatory_cooling_off_days=0,
            minimum_policy_tenure_days=0,
            maximum_policy_tenure_days=60,
            requires_grace_period=False,
        )
        engine = EligibilityRulesEngine(action_catalog=(custom_action,))
        ctx_old = _make_sample_context(tenure_days=100)
        res_custom = engine.evaluate(ctx_old)
        self.assertFalse(res_custom.is_eligible("courtesy_reminder"))
        self.assertIn(
            DisqualificationReasonCode.DISQUALIFIED_MAXIMUM_TENURE_EXCEEDED.value,
            res_custom.get_reasons("courtesy_reminder"),
        )

    def test_fail_closed_on_corrupt_or_missing_input(self) -> None:
        """Invalid or corrupt input dictionaries fail-closed safely into abstention."""
        # Missing policy_id, as_of, status
        corrupt_inputs = [
            {},
            {"policy_id": "pol_123"},
            {"policy_id": "pol_123", "as_of": "not_a_date"},
            {"policy_id": "", "as_of": "2026-08-01T00:00:00Z", "status": "active"},
        ]

        engine = EligibilityRulesEngine()
        for bad_input in corrupt_inputs:
            with self.subTest(bad_input=bad_input):
                result_set = engine.evaluate(bad_input)
                self.assertTrue(result_set.is_frozen)
                self.assertEqual(
                    result_set.freeze_reason,
                    DisqualificationReasonCode.DISQUALIFIED_MISSING_REQUIRED_ATTRIBUTE.value,
                )
                self.assertEqual(result_set.eligible_actions, ("abstain",))

    def test_immutability(self) -> None:
        """Domain structures must be frozen dataclasses to prevent runtime mutation."""
        ctx = _make_sample_context()
        with self.assertRaises(FrozenInstanceError):
            ctx.status = "grace_period"  # type: ignore[misc]

        result_set = evaluate_action_eligibility(ctx)
        with self.assertRaises(FrozenInstanceError):
            result_set.is_frozen = True  # type: ignore[misc]

    def test_serialization_conformance(self) -> None:
        """to_dict() outputs structure matching ADR 0002 decision evidence requirements."""
        ctx = _make_sample_context()
        result_set = evaluate_action_eligibility(ctx)
        d = result_set.to_dict()

        self.assertEqual(d["policy_id"], ctx.policy_id)
        self.assertIn("results", d)
        self.assertIn("eligible_actions", d)
        self.assertIn("is_frozen", d)
        self.assertTrue(isinstance(d["results"]["abstain"]["is_eligible"], bool))

    def test_zero_ml_dependency_ast_enforcement(self) -> None:
        """ADR 0002 Strict Decoupling: static AST verification of simulator/rules/ files.

        Asserts that the rules module has ZERO imports of machine learning libraries
        (sklearn, xgboost, scipy, torch) and simulator modeling modules (modeling,
        bundle, calibration, explanations), and no parameter signatures named 'model',
        'score', 'probability', or 'tier'.
        """
        rules_dir = Path(__file__).resolve().parent.parent / "src" / "inforsight_simulator" / "rules"
        self.assertTrue(rules_dir.is_dir(), f"Rules directory not found: {rules_dir}")

        forbidden_imports = {
            "sklearn",
            "xgboost",
            "scipy",
            "torch",
            "statsmodels",
            "modeling",
            "boosted_modeling",
            "bundle",
            "calibration",
            "explanations",
        }
        forbidden_params = {"model", "score", "scores", "probability", "probabilities", "operational_tier", "risk_tier"}

        for py_file in rules_dir.glob("*.py"):
            with self.subTest(file=py_file.name):
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content, filename=str(py_file))

                # Check imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            root_pkg = alias.name.split(".")[0]
                            self.assertNotIn(
                                root_pkg,
                                forbidden_imports,
                                f"Forbidden ML import '{alias.name}' found in {py_file.name}",
                            )
                    elif isinstance(node, ast.ImportFrom):
                        module_name = node.module or ""
                        root_pkg = module_name.split(".")[0]
                        self.assertNotIn(
                            root_pkg,
                            forbidden_imports,
                            f"Forbidden ML import from '{module_name}' in {py_file.name}",
                        )
                        for alias in node.names:
                            self.assertNotIn(
                                alias.name,
                                forbidden_imports,
                                f"Forbidden ML import '{alias.name}' in {py_file.name}",
                            )

                    # Check function parameter names
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        arg_names = {arg.arg.lower() for arg in node.args.args}
                        inter = arg_names.intersection(forbidden_params)
                        self.assertFalse(
                            bool(inter),
                            f"Function '{node.name}' in {py_file.name} has forbidden ML param: {inter}",
                        )

    def test_property_based_fuzz_invariants(self) -> None:
        """Property test: randomize 100 contexts; verify global invariants always hold.

        Invariants:
        1. 'abstain' is ALWAYS eligible.
        2. 'eligible_actions' is ALWAYS a subset of all evaluated action types.
        3. If 'is_frozen' is True, 'eligible_actions' contains ONLY 'abstain'.
        4. to_dict() never raises an exception and outputs valid JSON types.
        """
        rng = random.Random(20260905)
        statuses = ["active", "grace_period", "lapsed", "surrendered", "terminated", "matured"]

        for i in range(100):
            as_of = datetime(2026, 8, 1, tzinfo=timezone.utc)
            days_ago = rng.choice([None, rng.randint(0, 60)])
            last_contact = (as_of - timedelta(days=days_ago)) if days_ago is not None else None

            ctx = PolicyContext(
                policy_id=f"pol_fuzz_{i:04d}",
                as_of=as_of,
                status=rng.choice(statuses),
                tenure_days=rng.randint(0, 1000),
                in_grace_period=rng.choice([True, False]),
                days_past_due=rng.randint(0, 90),
                has_active_claim=rng.choice([True, False]),
                has_legal_hold=rng.choice([True, False]),
                has_registered_dispute=rng.choice([True, False]),
                sms_opt_out=rng.choice([True, False]),
                email_opt_out=rng.choice([True, False]),
                phone_opt_out=rng.choice([True, False]),
                dnc_registered=rng.choice([True, False]),
                last_contact_date=last_contact,
            )

            result_set = evaluate_action_eligibility(ctx)

            # Invariant 1: abstain is always eligible
            self.assertTrue(result_set.is_eligible("abstain"))

            # Invariant 2: eligible_actions is subset of evaluated actions
            self.assertTrue(set(result_set.eligible_actions).issubset(set(result_set.results.keys())))

            # Invariant 3: if frozen, only abstain is eligible
            if result_set.is_frozen:
                self.assertEqual(result_set.eligible_actions, ("abstain",))

            # Invariant 4: to_dict() validity
            d = result_set.to_dict()
            self.assertEqual(d["policy_id"], ctx.policy_id)


if __name__ == "__main__":
    unittest.main()

