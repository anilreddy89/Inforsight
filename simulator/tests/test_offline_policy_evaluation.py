"""Integration tests for Offline Policy Evaluation (OPE) and policy-cluster bootstrap."""

import unittest
from inforsight_simulator.counterfactual import (
    ControlPolicy,
    CounterfactualSimulator,
    DecisionEnginePolicy,
    HeuristicPolicy,
    NaiveMLPolicy,
    OfflinePolicyEvaluator,
    RandomPolicy,
    build_ope_manifest,
    compute_policy_metrics,
    run_cluster_bootstrap,
)
from inforsight_simulator.v6_corpus import V6Features, V6Observation


def create_mock_observations(count: int = 100) -> list[V6Observation]:
    """Generate mock observations with varying risk profiles for testing."""
    observations: list[V6Observation] = []
    for i in range(count):
        pid = f"pol_{i:04d}"
        # Alternate risk profiles: some high risk grace, some lost causes, some low risk
        if i % 5 == 0:
            # Persuadable grace period policy
            dpd = 14.0
            failed = 1
            tenure = 730
            prem = 15000  # $150/mo
            on_time = 0.85
        elif i % 5 == 1:
            # Lost cause: deep arrears, zero on-time, high contacts
            dpd = 75.0
            failed = 3
            tenure = 90
            prem = 8000
            on_time = 0.20
        elif i % 5 == 2:
            # Sleeping dog: high irritation / contact fatigue
            dpd = 0.0
            failed = 0
            tenure = 1200
            prem = 25000
            on_time = 0.95
        else:
            # Moderate / low risk
            dpd = 0.0
            failed = 0
            tenure = 500
            prem = 10000
            on_time = 0.90

        features = V6Features(
            tenure_days=tenure,
            premium_amount_cents=prem,
            product_type="fictional_term_life",
            billing_frequency="monthly",
            recent_delay_days=dpd,
            recent_failed_payment_count=failed,
            recent_retry_count=0,
            recent_recovery_count=0,
            arrears_duration_days=int(dpd),
            rolling_on_time_rate=on_time,
            rolling_payment_count=12,
            recent_notice_count=1 if dpd > 0 else 0,
            notice_category="grace_warning" if dpd > 0 else "billing_reminder",
            recent_contact_count=3 if i % 5 == 1 else 0,
            contact_category="billing_question",
            payment_attribute_missing=False,
            contact_attribute_missing=False,
        )

        obs = V6Observation(
            observation_contract_version="6.0.0",
            label_policy_version="3.0.0",
            artifact_id="test_art",
            observation_id=f"obs_{i:04d}",
            outcome_episode_id=f"ep_{i:04d}",
            policy_id=pid,
            role="evaluation",
            cohort="v6_test",
            as_of="2026-08-17T00:00:00Z",
            horizon_end="2026-11-15T00:00:00Z",
            follow_up_through="2026-11-15T00:00:00Z",
            features=features,
            feature_lineage={},
            visible_event_ids=(),
            visible_events_sha256="",
            label_status="labeled",
            label_value=None,
            outcome_type=None,
            censoring_reason=None,
        )
        observations.append(obs)

    return observations


class TestOfflinePolicyEvaluation(unittest.TestCase):
    """Verifies OPE comparative evaluation, constraints, and bootstrap reproducibility."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.observations = create_mock_observations(100)
        # Mock risk scores correlated with delay and payment failures
        cls.risk_scores = {
            obs.policy_id: min(
                0.90,
                0.05
                + (0.35 if (obs.features.recent_delay_days or 0) > 0 else 0.0)
                + (0.30 if obs.features.recent_failed_payment_count > 0 else 0.0)
                + (0.20 if obs.features.rolling_on_time_rate < 0.50 else 0.0),
            )
            for obs in cls.observations
        }
        simulator = CounterfactualSimulator()
        cls.potential_outcomes = simulator.simulate_cohort(cls.observations)

    def test_all_five_policies_execute_and_produce_metrics(self) -> None:
        """Every candidate policy must produce complete metrics without error."""
        evaluator = OfflinePolicyEvaluator(
            specialist_capacity_hours=10.0,
            budget_cap_usd=2_000.0,
        )
        results = evaluator.evaluate(
            self.observations,
            self.risk_scores,
            self.potential_outcomes,
        )

        expected_policies = {"decision_engine", "naive_ml", "heuristic", "random", "control"}
        self.assertEqual(set(results.keys()), expected_policies)

        for p_name, (metrics, assignments) in results.items():
            self.assertEqual(metrics.cohort_size, len(self.observations))
            self.assertEqual(len(assignments), len(self.observations))
            self.assertGreaterEqual(metrics.total_lapses, 0.0)
            self.assertGreaterEqual(metrics.total_spend_usd, 0.0)
            self.assertLessEqual(metrics.specialist_hours_used, 10.0 + 1e-6)

    def test_decision_engine_superiority(self) -> None:
        """Decision Engine must achieve higher Net Preserved Value than baselines."""
        evaluator = OfflinePolicyEvaluator(
            specialist_capacity_hours=10.0,
            budget_cap_usd=2_000.0,
        )
        results = evaluator.evaluate(
            self.observations,
            self.risk_scores,
            self.potential_outcomes,
        )

        m_engine = results["decision_engine"][0]
        m_naive = results["naive_ml"][0]
        m_heuristic = results["heuristic"][0]
        m_random = results["random"][0]
        m_control = results["control"][0]

        # Decision Engine must preserve strictly positive net value
        self.assertGreater(m_engine.net_preserved_usd, 0.0)
        self.assertGreater(m_engine.net_preserved_usd, m_control.net_preserved_usd)
        self.assertGreater(m_engine.net_preserved_usd, m_random.net_preserved_usd)
        self.assertGreater(m_engine.net_preserved_usd, m_naive.net_preserved_usd)
        self.assertGreater(m_engine.net_preserved_usd, m_heuristic.net_preserved_usd)

        # ROCS must be positive and substantial
        self.assertGreater(m_engine.rocs, 0.50)

    def test_policy_cluster_bootstrap_reproducibility(self) -> None:
        """Bootstrap CI estimates must reproduce bit-for-bit with fixed seed."""
        evaluator = OfflinePolicyEvaluator(
            specialist_capacity_hours=10.0,
            budget_cap_usd=2_000.0,
        )
        results = evaluator.evaluate(
            self.observations,
            self.risk_scores,
            self.potential_outcomes,
        )

        intervals_1, contrasts_1 = run_cluster_bootstrap(results, n_bootstraps=50, seed=12345)
        intervals_2, contrasts_2 = run_cluster_bootstrap(results, n_bootstraps=50, seed=12345)

        for p in ("decision_engine", "naive_ml", "heuristic"):
            self.assertEqual(
                intervals_1[p]["net_preserved_usd"].median,
                intervals_2[p]["net_preserved_usd"].median,
            )
            self.assertEqual(
                intervals_1[p]["net_preserved_usd"].ci_lower,
                intervals_2[p]["net_preserved_usd"].ci_lower,
            )

        for c in ("naive_ml", "heuristic"):
            self.assertEqual(
                contrasts_1[c].delta_net_preserved_usd.median,
                contrasts_2[c].delta_net_preserved_usd.median,
            )
            self.assertEqual(
                contrasts_1[c].p_value_superiority,
                contrasts_2[c].p_value_superiority,
            )

    def test_ope_manifest_generation_and_digest(self) -> None:
        """OPEResultManifest must correctly serialize and generate cryptographic digest."""
        evaluator = OfflinePolicyEvaluator(
            specialist_capacity_hours=10.0,
            budget_cap_usd=2_000.0,
        )
        results = evaluator.evaluate(
            self.observations,
            self.risk_scores,
            self.potential_outcomes,
        )
        intervals, contrasts = run_cluster_bootstrap(results, n_bootstraps=50, seed=42)

        manifest = build_ope_manifest(
            eval_results=results,
            policy_intervals=intervals,
            pairwise_contrasts=contrasts,
            seed=42,
            bootstrap_samples=50,
            specialist_capacity_hours=10.0,
            budget_cap_usd=2000.0,
        )

        self.assertEqual(manifest.schema_version, "1.0.0")
        self.assertGreater(len(manifest.manifest_digest), 32)
        self.assertIn("decision_engine", manifest.policy_metrics)
        self.assertTrue(manifest.verifications["specialist_capacity_adherence"])


if __name__ == "__main__":
    unittest.main()
