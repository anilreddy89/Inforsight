"""Unit and invariant tests for counterfactual hazard modulation and potential outcomes."""

import math
import unittest

from inforsight_simulator.counterfactual.hazard import (
    compute_action_logit_shift,
    counterfactual_competing_hazards,
    counterfactual_cumulative_incidence,
    counterfactual_observable_incidence,
)
from inforsight_simulator.counterfactual.models import CANONICAL_INTERVENTIONS
from inforsight_simulator.v6_corpus import V6Features


def make_test_features(
    *,
    tenure_days: int = 365,
    premium_amount_cents: int = 10000,
    product_type: str = "fictional_term_life",
    billing_frequency: str = "monthly",
    recent_delay_days: float | None = 10.0,
    recent_failed_payment_count: int = 1,
    recent_retry_count: int = 0,
    recent_recovery_count: int = 0,
    arrears_duration_days: int = 10,
    rolling_on_time_rate: float = 0.85,
    rolling_payment_count: int = 11,
    recent_notice_count: int = 1,
    notice_category: str = "billing_reminder",
    recent_contact_count: int = 0,
    contact_category: str = "billing_question",
    payment_attribute_missing: bool = False,
    contact_attribute_missing: bool = False,
) -> V6Features:
    return V6Features(
        tenure_days=tenure_days,
        premium_amount_cents=premium_amount_cents,
        product_type=product_type,
        billing_frequency=billing_frequency,
        recent_delay_days=recent_delay_days,
        recent_failed_payment_count=recent_failed_payment_count,
        recent_retry_count=recent_retry_count,
        recent_recovery_count=recent_recovery_count,
        arrears_duration_days=arrears_duration_days,
        rolling_on_time_rate=rolling_on_time_rate,
        rolling_payment_count=rolling_payment_count,
        recent_notice_count=recent_notice_count,
        notice_category=notice_category,
        recent_contact_count=recent_contact_count,
        contact_category=contact_category,
        payment_attribute_missing=payment_attribute_missing,
        contact_attribute_missing=contact_attribute_missing,
    )


class TestCounterfactualHazard(unittest.TestCase):
    """Verifies counterfactual hazard modulation and Generation v6 invariants."""

    def test_total_terminal_hazard_invariant(self) -> None:
        """Total monthly hazard must strictly obey lambda_total <= 0.1500 < 0.2000."""
        features = make_test_features(
            recent_delay_days=60.0,
            recent_failed_payment_count=3,
            arrears_duration_days=90,
            rolling_on_time_rate=0.0,
        )

        for action in CANONICAL_INTERVENTIONS:
            for month in (1, 2, 3):
                for frailty in (-2.0, -1.0, 0.0, 1.0, 2.0):
                    l_h, s_h, cont = counterfactual_competing_hazards(
                        features, frailty, month, action
                    )
                    total_h = l_h + s_h
                    self.assertLess(
                        total_h,
                        0.20,
                        f"Failed hazard bound for {action}, m={month}, f={frailty}",
                    )
                    self.assertAlmostEqual(cont, 1.0 - total_h, places=12)

    def test_monotonicity_of_action_effects(self) -> None:
        """Beneficial interventions must show monotonic logit shift reductions."""
        features = make_test_features()
        shifts = {
            act: compute_action_logit_shift(act, features, month=1)
            for act in CANONICAL_INTERVENTIONS
        }

        self.assertEqual(shifts["abstain"], 0.0)
        self.assertLess(shifts["courtesy_reminder"], 0.0)
        self.assertLess(shifts["payment_method_remediation"], shifts["courtesy_reminder"])
        self.assertLess(shifts["grace_period_consultation"], shifts["payment_method_remediation"])
        self.assertLess(shifts["specialist_phone_outreach"], shifts["grace_period_consultation"])

    def test_temporal_effect_decay(self) -> None:
        """Intervention logit shifts must decay over months 1 to 3."""
        features = make_test_features()
        for act in ("courtesy_reminder", "specialist_phone_outreach"):
            s1 = compute_action_logit_shift(act, features, month=1)
            s2 = compute_action_logit_shift(act, features, month=2)
            s3 = compute_action_logit_shift(act, features, month=3)

            self.assertLess(abs(s2), abs(s1))
            self.assertLess(abs(s3), abs(s2))

    def test_contact_fatigue_attenuation(self) -> None:
        """Repeated contacts should diminish action efficacy."""
        feat_zero_contacts = make_test_features(recent_contact_count=0)
        feat_high_contacts = make_test_features(recent_contact_count=3)

        s_zero = compute_action_logit_shift("specialist_phone_outreach", feat_zero_contacts, month=1)
        s_high = compute_action_logit_shift("specialist_phone_outreach", feat_high_contacts, month=1)

        # More negative shift means stronger effect; zero contacts should be more negative
        self.assertLess(s_zero, s_high)

    def test_payment_recency_modulation(self) -> None:
        """Payment remediation is most potent when failure is recent."""
        feat_recent = make_test_features(recent_delay_days=10.0)
        feat_old = make_test_features(recent_delay_days=75.0)

        s_recent = compute_action_logit_shift("payment_method_remediation", feat_recent, month=1)
        s_old = compute_action_logit_shift("payment_method_remediation", feat_old, month=1)

        self.assertLess(s_recent, s_old)

    def test_sleeping_dog_reaction(self) -> None:
        """Sleeping dogs experience accelerated lapse hazard from outreach."""
        features = make_test_features()
        shift_dog = compute_action_logit_shift(
            "specialist_phone_outreach", features, month=1, is_sleeping_dog=True
        )
        self.assertGreater(shift_dog, 0.0)

        l_h_ctrl, _, _ = counterfactual_competing_hazards(features, 0.0, 1, "abstain")
        l_h_dog, _, _ = counterfactual_competing_hazards(
            features, 0.0, 1, "specialist_phone_outreach", is_sleeping_dog=True
        )
        self.assertGreater(l_h_dog, l_h_ctrl)

    def test_observable_incidence_quadrature_validity(self) -> None:
        """Gauss-Hermite quadrature produces well-bounded probabilities."""
        features = make_test_features()
        for act in CANONICAL_INTERVENTIONS:
            p_lapse, p_surr, p_union = counterfactual_observable_incidence(features, act)
            self.assertGreaterEqual(p_lapse, 0.0)
            self.assertGreaterEqual(p_surr, 0.0)
            self.assertLess(p_union, 1.0)
            self.assertAlmostEqual(p_union, p_lapse + p_surr, places=8)


if __name__ == "__main__":
    unittest.main()

