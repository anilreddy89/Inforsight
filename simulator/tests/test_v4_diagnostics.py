from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import unittest

from inforsight_simulator.v4_diagnostics import (
    DEVELOPMENT_DIAGNOSTIC_SEEDS, FUTURE_ACCEPTANCE_SEEDS, GOVERNED_FOLDS,
    GOVERNED_SCENARIOS, HYPOTHESIS_REGISTRY, SPENT_ACCEPTANCE_SEEDS,
    authorize_diagnostic, build_readiness_manifest, evaluate_readiness,
    planned_inventory, project_aggregate, readiness_decision,
    validate_authorization,
)


ROOT = Path(__file__).resolve().parents[2]
DIGEST = "a" * 64


class V4DiagnosticReadinessTests(unittest.TestCase):
    def test_domains_are_exact_and_disjoint(self) -> None:
        self.assertEqual(DEVELOPMENT_DIAGNOSTIC_SEEDS,
                         tuple(range(20271101, 20271121)))
        self.assertEqual(FUTURE_ACCEPTANCE_SEEDS, tuple(range(20271201, 20271221)))
        self.assertFalse(set(SPENT_ACCEPTANCE_SEEDS) & set(DEVELOPMENT_DIAGNOSTIC_SEEDS))
        self.assertFalse(set(DEVELOPMENT_DIAGNOSTIC_SEEDS) & set(FUTURE_ACCEPTANCE_SEEDS))

    def test_inventory_is_complete_and_unique(self) -> None:
        inventory = planned_inventory()
        expected = (20 * len(GOVERNED_SCENARIOS) * len(GOVERNED_FOLDS)
                    * sum(len(value) for value in HYPOTHESIS_REGISTRY.values()))
        self.assertEqual(len(inventory), expected)
        self.assertEqual(len({tuple(sorted(item.items())) for item in inventory}), expected)

    def test_approved_interpretation_amendment_authorizes_results(self) -> None:
        checks = evaluate_readiness(ROOT)
        self.assertEqual(readiness_decision(checks), "authorized")
        by_id = {item.check_id: item for item in checks}
        self.assertEqual(by_id["READINESS-INTERPRETATION-AUTHORITY"].status, "pass")
        manifest = build_readiness_manifest(ROOT)
        self.assertTrue(manifest["result_producing_execution_authorized"])
        self.assertFalse(manifest["diagnostic_results_generated"])
        self.assertEqual(manifest["future_acceptance_status"], "not_materialized")
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")

    def test_authorization_rejects_domain_purpose_and_digest_mutations(self) -> None:
        kwargs = dict(
            seed=20271101, scenario="signal", fold="fold_1",
            purpose="observable_oracle", ordered_membership_sha256=DIGEST,
            input_artifact_sha256=DIGEST, target_sha256=DIGEST,
            feature_or_mechanism_sha256=DIGEST,
        )
        authorization = authorize_diagnostic(**kwargs)
        validate_authorization(authorization, **kwargs)
        with self.assertRaisesRegex(ValueError, "development domain"):
            authorize_diagnostic(**{**kwargs, "seed": 20271201})
        with self.assertRaisesRegex(ValueError, "not registered"):
            authorize_diagnostic(**{**kwargs, "purpose": "exploration"})
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            authorize_diagnostic(**{**kwargs, "target_sha256": "bad"})
        with self.assertRaisesRegex(ValueError, "mismatch"):
            validate_authorization(replace(authorization, target_sha256="b" * 64),
                                   **kwargs)

    def test_small_cells_are_suppressed_and_nonfinite_values_fail(self) -> None:
        suppressed = project_aggregate(unique_policy_count=9, observed=0.75)
        self.assertEqual(suppressed["status"], "suppressed")
        self.assertIsNone(suppressed["observed"])
        reported = project_aggregate(unique_policy_count=10, observed={"auc": 0.75})
        self.assertEqual(reported["status"], "reported")
        with self.assertRaises(ValueError):
            project_aggregate(unique_policy_count=10, observed=float("nan"))

    def test_committed_diagnostic_evidence_is_complete_and_bounded(self) -> None:
        path = ROOT / "docs/experiments/phase-02r-13-v4-redesign-diagnostic-manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["issue"], 69)
        self.assertEqual(manifest["seed_count"], 20)
        self.assertEqual(manifest["seeds"], list(range(20271101, 20271121)))
        self.assertEqual(len(manifest["seed_evidence"]), 20)
        self.assertEqual(manifest["hypothesis_dispositions"], {
            "H1_ORACLE_SEPARABILITY": "supported",
            "H2_DRIVER_SUPPORT": "supported",
            "H3_TRANSFORM_PARITY": "rejected",
            "H4_EPISODE_DILUTION": "rejected",
            "H5_CANDIDATE_LEARNING": "unresolved",
            "H6_TEMPORAL_STABILITY": "rejected",
        })
        self.assertEqual(manifest["summary"]["observable_oracle_auc_pass_count"], 0)
        self.assertEqual(manifest["summary"]["parity_mismatch_count"], 0)
        self.assertFalse(manifest["protected_intermediates_committed"])
        self.assertEqual(manifest["future_acceptance_status"], "not_materialized")
        self.assertEqual(manifest["final_holdout_status"], "not_materialized")
        rendered = path.read_text(encoding="utf-8")
        for prohibited in ("outcome_uniforms", "latent_frailty", "probabilities",
                           "matrix_values", "final_holdout_seed"):
            self.assertNotIn(prohibited, rendered)


if __name__ == "__main__":
    unittest.main()
