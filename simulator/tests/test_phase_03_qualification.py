"""Automated tests for Phase 3.09 Pre-Release System Qualification Gates (S1–S6)."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from inforsight_simulator.bundle import BundledInferenceEngine, ModelBundle
from inforsight_simulator.qualification import (
    QualificationRunner,
    build_qualification_manifest,
    evaluate_gate_s1_authority_isolation,
    evaluate_gate_s2_eligibility_firewall,
    evaluate_gate_s3_capacity_adherence,
    evaluate_gate_s4_audit_tamper_resistance,
    evaluate_gate_s5_latency_sla,
    evaluate_gate_s6_reproducibility,
    generate_qualification_report,
)
from inforsight_simulator.rules import EligibilityRulesEngine
from inforsight_simulator.v6_corpus import V6CorpusConfig, generate_v6_corpus

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUNDLE_PATH = REPO_ROOT / "docs" / "experiments" / "phase-02-10-model-bundle.json"


class TestPhase03QualificationGates(unittest.TestCase):
    """Test suite certifying individual qualification gates S1–S6 and the complete runner."""

    @classmethod
    def setUpClass(cls) -> None:
        with open(BUNDLE_PATH, "r", encoding="utf-8") as f:
            cls.bundle_dict = json.load(f)
        cls.bundle = ModelBundle.from_dict(cls.bundle_dict)
        cls.engine = BundledInferenceEngine(cls.bundle)

        # Generate a small 100-policy test corpus for fast unit evaluations
        config = V6CorpusConfig(
            base_seed=20280201,
            policy_count=100,
            cohort_count=2,
            policies_per_cohort=50,
        )
        cls.corpus = generate_v6_corpus(config)

        # Extract latest observation per policy
        latest: dict[str, Any] = {}
        for obs in cls.corpus.observations:
            pid = obs.policy_id
            if pid not in latest or obs.as_of > latest[pid].as_of:
                latest[pid] = obs
        cls.observations = sorted(latest.values(), key=lambda o: o.policy_id)

    def test_gate_s1_authority_isolation(self) -> None:
        """Gate S1: Verify that unauthorized dispatch attempts fail closed and authority invariants hold."""
        res = evaluate_gate_s1_authority_isolation(self.engine, self.observations[0])
        self.assertTrue(res.passed, f"Gate S1 failed: {res.error_message}")
        self.assertEqual(res.details["rejection_rate"], 1.0)
        self.assertEqual(res.details["blocked_attempts"], 2)
        self.assertTrue(res.details["non_authority_markers_valid"])

    def test_gate_s2_eligibility_firewall(self) -> None:
        """Gate S2: Verify that legal disputes, active claims, and non-viable policies are 100% disqualified."""
        rules_engine = EligibilityRulesEngine()
        res = evaluate_gate_s2_eligibility_firewall(rules_engine, self.observations)
        self.assertTrue(res.passed, f"Gate S2 failed: {res.error_message}")
        self.assertEqual(res.details["false_positive_actions"], 0)
        self.assertEqual(res.details["firewall_pass_rate"], 1.0)
        self.assertIn("DISQUALIFIED_LEGAL_DISPUTE_FREEZE", res.details["dispute_reasons_observed"])
        self.assertIn("DISQUALIFIED_ACTIVE_CLAIM", res.details["dispute_reasons_observed"])
        self.assertIn("DISQUALIFIED_LEGAL_HOLD", res.details["dispute_reasons_observed"])

    def test_gate_s3_capacity_adherence(self) -> None:
        """Gate S3: Verify greedy knapsack optimizer strictly respects specialist capacity and budget caps."""
        from inforsight_simulator.optimization import PolicyValuation
        from inforsight_simulator.rules import PolicyContext
        from datetime import datetime, timezone

        rules_engine = EligibilityRulesEngine()
        eligible_sets = []
        valuations = {}
        risk_scores = {}
        dpd_map = {}

        for obs in self.observations:
            pid = obs.policy_id
            dpd = int(obs.features.recent_delay_days or 0)
            dpd_map[pid] = dpd
            risk_scores[pid] = 0.40  # force high risk to stress capacity
            valuations[pid] = PolicyValuation(
                policy_id=pid,
                annual_premium_usd=1500.0,
                customer_lifetime_value_usd=6000.0,
            )
            ctx = PolicyContext(
                policy_id=pid,
                as_of=datetime.now(timezone.utc),
                status="grace_period" if (0 < dpd <= 30) else "active",
                tenure_days=obs.features.tenure_days,
                in_grace_period=(0 < dpd <= 30),
                days_past_due=dpd,
            )
            eligible_sets.append(rules_engine.evaluate(ctx))

        # Test standard capacity (K=10, Budget=$1000)
        res = evaluate_gate_s3_capacity_adherence(
            eligible_sets=eligible_sets,
            valuations=valuations,
            risk_scores=risk_scores,
            days_past_due_map=dpd_map,
            specialist_capacity=10,
            budget_cap_usd=1000.0,
        )
        self.assertTrue(res.passed, f"Gate S3 failed: {res.error_message}")
        self.assertLessEqual(res.details["specialist_allocated"], 10)
        self.assertLessEqual(res.details["total_allocated_spend_usd"], 1000.0)
        self.assertEqual(res.details["capacity_overflow"], 0)
        self.assertEqual(res.details["budget_overflow_usd"], 0.0)

    def test_gate_s4_audit_tamper_resistance(self) -> None:
        """Gate S4: Verify that payload mutation, deletion, reordering, and injection are 100% detected."""
        res = evaluate_gate_s4_audit_tamper_resistance()
        self.assertTrue(res.passed, f"Gate S4 failed: {res.error_message}")
        self.assertTrue(res.details["pristine_chain_valid"])
        self.assertEqual(res.details["tamper_detection_rate"], 1.0)
        self.assertEqual(res.details["attacks_detected"], 4)

    def test_gate_s5_latency_sla(self) -> None:
        """Gate S5: Verify that local inference latency meets single-policy (<= 10ms) and batch (<= 100ms) SLAs."""
        res = evaluate_gate_s5_latency_sla(
            self.engine,
            self.observations,
            single_sla_ms=10.0,
            batch_sla_ms=100.0,
        )
        self.assertTrue(res.passed, f"Gate S5 failed: {res.error_message}")
        self.assertLessEqual(res.details["latency_p99_ms"], 10.0)
        self.assertLessEqual(res.details["batch_50_elapsed_ms"], 100.0)

    def test_gate_s6_reproducibility(self) -> None:
        """Gate S6: Verify that matching digests yield a passing reproducibility certification."""
        digest = "a" * 64
        res_pass = evaluate_gate_s6_reproducibility(
            digest_run_1=digest,
            digest_run_2=digest,
            identical_allocations=True,
            identical_scores=True,
        )
        self.assertTrue(res_pass.passed)

        # Mismatch must fail
        res_fail = evaluate_gate_s6_reproducibility(
            digest_run_1=digest,
            digest_run_2="b" * 64,
            identical_allocations=True,
            identical_scores=True,
        )
        self.assertFalse(res_fail.passed)

    def test_manifest_and_report_generation(self) -> None:
        """Verify that manifest and report generators produce valid schemas and Markdown."""
        runner = QualificationRunner(
            bundle_path=BUNDLE_PATH,
            seed=20280201,
            policy_count=50,
            specialist_capacity=5,
            budget_cap_usd=500.0,
        )
        res = runner.run()
        manifest = build_qualification_manifest(res)

        self.assertEqual(manifest["schema_version"], "1.0.0")
        self.assertEqual(manifest["phase"], "Phase 3.09")
        self.assertIn("manifest_digest", manifest)
        self.assertEqual(len(manifest["manifest_digest"]), 64)
        self.assertEqual(manifest["overall_decision"], "RELEASE_QUALIFIED")

        report = generate_qualification_report(manifest)
        self.assertIn("# Phase 3.09 — End-to-End System Qualification & Integration Gate Report", report)
        self.assertIn("Scorecard", report)
        self.assertIn("RELEASE_QUALIFIED", report)


if __name__ == "__main__":
    unittest.main()
