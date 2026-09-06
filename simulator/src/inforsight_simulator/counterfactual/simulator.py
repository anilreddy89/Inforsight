"""Potential outcome simulator over the 90-day post-cutoff horizon."""

from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from inforsight_simulator.v6_corpus import V6Features, V6Observation, V6OracleRecord

from .hazard import (
    counterfactual_cumulative_incidence,
    counterfactual_observable_incidence,
)
from .models import (
    CANONICAL_INTERVENTIONS,
    CounterfactualOutcome,
)


class CounterfactualSimulator:
    """Simulates potential conservation outcomes for policies under all candidate interventions."""

    def __init__(
        self,
        *,
        signal_scale: float = 1.0,
        drift: float = 0.0,
    ) -> None:
        self.signal_scale = signal_scale
        self.drift = drift

    def simulate_policy_outcomes(
        self,
        policy_id: str,
        features: V6Features,
        frailty: float | None = None,
        is_sleeping_dog: bool = False,
    ) -> dict[str, CounterfactualOutcome]:
        """Simulate potential outcomes under all canonical actions for one policy."""
        # 1. Baseline control outcome under abstain
        if frailty is not None:
            p_0_lapse, p_0_surr, _, m_0_lapse, m_0_surr = counterfactual_cumulative_incidence(
                features,
                frailty,
                "abstain",
                signal_scale=self.signal_scale,
                drift=self.drift,
                is_sleeping_dog=is_sleeping_dog,
            )
        else:
            p_0_lapse, p_0_surr, _ = counterfactual_observable_incidence(
                features,
                "abstain",
                signal_scale=self.signal_scale,
                drift=self.drift,
                is_sleeping_dog=is_sleeping_dog,
            )
            m_0_lapse = (0.0, 0.0, 0.0)
            m_0_surr = (0.0, 0.0, 0.0)

        outcomes: dict[str, CounterfactualOutcome] = {}

        for action_name, params in CANONICAL_INTERVENTIONS.items():
            if action_name == "abstain":
                outcomes["abstain"] = CounterfactualOutcome(
                    policy_id=policy_id,
                    action_type="abstain",
                    baseline_lapse_prob=p_0_lapse,
                    counterfactual_lapse_prob=p_0_lapse,
                    baseline_surrender_prob=p_0_surr,
                    counterfactual_surrender_prob=p_0_surr,
                    treatment_effect_uplift=0.0,
                    monthly_lapse_hazards=m_0_lapse,
                    monthly_surrender_hazards=m_0_surr,
                    direct_cost_usd=0.0,
                )
                continue

            if frailty is not None:
                p_a_lapse, p_a_surr, _, m_a_lapse, m_a_surr = counterfactual_cumulative_incidence(
                    features,
                    frailty,
                    action_name,
                    signal_scale=self.signal_scale,
                    drift=self.drift,
                    is_sleeping_dog=is_sleeping_dog,
                )
            else:
                p_a_lapse, p_a_surr, _ = counterfactual_observable_incidence(
                    features,
                    action_name,
                    signal_scale=self.signal_scale,
                    drift=self.drift,
                    is_sleeping_dog=is_sleeping_dog,
                )
                m_a_lapse = (0.0, 0.0, 0.0)
                m_a_surr = (0.0, 0.0, 0.0)

            uplift = max(-1.0, min(1.0, p_0_lapse - p_a_lapse))

            outcomes[action_name] = CounterfactualOutcome(
                policy_id=policy_id,
                action_type=action_name,
                baseline_lapse_prob=p_0_lapse,
                counterfactual_lapse_prob=p_a_lapse,
                baseline_surrender_prob=p_0_surr,
                counterfactual_surrender_prob=p_a_surr,
                treatment_effect_uplift=uplift,
                monthly_lapse_hazards=m_a_lapse,
                monthly_surrender_hazards=m_a_surr,
                direct_cost_usd=params.direct_cost_usd,
            )

        return outcomes

    def simulate_cohort(
        self,
        observations: Sequence[V6Observation],
        frailty_map: Mapping[str, float] | None = None,
        sleeping_dogs_set: set[str] | None = None,
    ) -> dict[str, dict[str, CounterfactualOutcome]]:
        """Simulate potential outcomes for an entire cohort of observations.

        Returns:
            Dict mapping policy_id -> dict of action_name -> CounterfactualOutcome.
        """
        frailties = frailty_map or {}
        sleeping_dogs = sleeping_dogs_set or set()

        cohort_outcomes: dict[str, dict[str, CounterfactualOutcome]] = {}
        for obs in observations:
            pid = obs.policy_id
            frailty = frailties.get(pid)
            is_sd = pid in sleeping_dogs

            outcomes = self.simulate_policy_outcomes(
                policy_id=pid,
                features=obs.features,
                frailty=frailty,
                is_sleeping_dog=is_sd,
            )
            cohort_outcomes[pid] = outcomes

        return cohort_outcomes

