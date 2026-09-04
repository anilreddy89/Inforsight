from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from inforsight_simulator.v6_config import V6CorpusConfig
from inforsight_simulator.v6_corpus import generate_v6_corpus
from inforsight_simulator.v6_evaluation import (
    FEATURE_GROUPS, UNKNOWN_CATEGORY, V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION,
    V6_FINAL_HOLDOUT_STATUS, V6_SPLIT_VERSION, authorize, build_selection_fold,
    build_temporal_folds, compare_candidates, diagnostics, fit_preprocessor,
    matrix_digest, preprocessor_digest, structural_support_report, transform,
    validate_authorization, validate_feature_registry, validate_temporal_fold,
)


class V6EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = generate_v6_corpus(V6CorpusConfig(base_seed=20280201))
        cls.selection_fold = build_selection_fold(cls.corpus.observations)
        cls.fitted = fit_preprocessor(cls.selection_fold)
        cls.train = transform(cls.fitted, cls.selection_fold.fit, purpose="fit", role="fit")
        cls.selection = transform(
            cls.fitted, cls.selection_fold.evaluation,
            purpose="selection", role="selection",
        )
        cls.diagnostic = diagnostics(cls.train, cls.selection, cls.fitted)
        cls.candidates = compare_candidates(cls.train, cls.selection, cls.fitted)

    def test_feature_registry_is_closed_and_assigns_every_feature_once(self) -> None:
        validate_feature_registry()
        assigned = [feature for group in FEATURE_GROUPS.values() for feature in group]
        self.assertEqual(len(assigned), len(set(assigned)))
        self.assertEqual(FEATURE_GROUPS["recent_payment"][0], "recent_delay_days")
        dictionary = json.loads((
            Path(__file__).resolve().parents[2]
            / "docs/modeling/phase-02r-15-v6-feature-dictionary.json"
        ).read_text())
        documented = {
            item["name"]: item["driver_group"] for item in dictionary["features"]
        }
        self.assertEqual(
            documented,
            {feature: group for group, features in FEATURE_GROUPS.items()
             for feature in features},
        )

    def test_frozen_folds_are_supported_and_canonically_ordered(self) -> None:
        folds = build_temporal_folds(reversed(self.corpus.observations))
        self.assertEqual([fold.name for fold in folds], ["fold_1", "fold_2", "fold_3"])
        for fold in folds:
            validate_temporal_fold(fold)
            self.assertFalse({row.policy_id for row in fold.fit} & {row.policy_id for row in fold.evaluation})

    def test_selection_fold_passes_support_thresholds(self) -> None:
        self.assertEqual(V6_SPLIT_VERSION, "6.0.0")
        self.assertEqual(V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION, "3.0.0")
        self.assertGreaterEqual(len(self.selection_fold.evaluation), 500)
        positives = sum(row.label_value for row in self.selection_fold.evaluation)
        self.assertGreaterEqual(positives, 50)
        self.assertGreaterEqual(len(self.selection_fold.evaluation) - positives, 50)
        validate_temporal_fold(self.selection_fold)

    def test_structural_report_passes(self) -> None:
        report = structural_support_report(self.corpus.observations)
        memberships = {item["name"]: item for item in report["memberships"]}
        self.assertEqual(report["overall_status"], "pass")
        self.assertTrue(all(memberships[name]["support_status"] == "pass"
                            for name in ("fold_1", "fold_2", "fold_3")))
        self.assertEqual(memberships["selection"]["support_status"], "pass")
        self.assertEqual(
            memberships["selection"]["evaluation"]["eligible_uncensored_observations"],
            len(self.selection_fold.evaluation),
        )
        self.assertEqual(
            memberships["selection"]["evaluation"]["unique_policies"],
            len({row.policy_id for row in self.selection_fold.evaluation}),
        )
        self.assertEqual(report["final_holdout_status"], "not_materialized")

    def test_preprocessing_is_fit_only_and_unknown_category_is_frozen(self) -> None:
        again = fit_preprocessor(self.selection_fold)
        self.assertEqual(preprocessor_digest(self.fitted), preprocessor_digest(again))
        mutated = replace(
            self.selection_fold.evaluation[0],
            features=replace(
                self.selection_fold.evaluation[0].features,
                contact_category="post_fit_category",
            ),
        )
        matrix = transform(
            self.fitted, (mutated,) + self.selection_fold.evaluation[1:],
            purpose="selection", role="selection",
        )
        unknown_index = matrix.feature_names.index(f"contact_category={UNKNOWN_CATEGORY}")
        self.assertEqual(matrix.values[0][unknown_index], 1.0)
        self.assertEqual(matrix.feature_names, self.selection.feature_names)

    def test_diagnostics_authorize_candidate_comparison(self) -> None:
        self.assertEqual(self.diagnostic["decision"], "allow")
        self.assertEqual(self.diagnostic["identifier_and_protected_screen"]["status"], "passed")
        self.assertEqual(self.diagnostic["strongest_group"], "recent_payment")
        self.assertEqual(self.diagnostic["designed_zero_group"], "missingness")

    def test_candidate_selection_rule_selects_one_model(self) -> None:
        selection = self.candidates["selection"]
        self.assertIn(selection["selected_candidate"], {"logistic", "xgboost"})
        self.assertTrue(self.candidates["explicit_state_reload_verified"])
        logistic_auc = self.candidates["logistic"]["metrics"]["roc_auc"]
        boosted_auc = self.candidates["xgboost"]["metrics"]["roc_auc"]
        self.assertGreater(logistic_auc, 0.65)
        self.assertGreater(boosted_auc, 0.65)

    def test_scoring_authorization_cryptographic_binding(self) -> None:
        model_sha = self.candidates["selection"]["selected_model_sha256"]
        auth = authorize(self.train, self.selection, self.fitted, model_sha256=model_sha)
        validate_authorization(
            auth, self.selection,
            fit_matrix_sha256=matrix_digest(self.train),
            preprocessor_sha256=preprocessor_digest(self.fitted),
            model_sha256=model_sha,
        )
        # Verify tampering detection
        tampered_auth = replace(auth, authorization_sha256="0" * 64)
        with self.assertRaises(ValueError):
            validate_authorization(
                tampered_auth, self.selection,
                fit_matrix_sha256=matrix_digest(self.train),
                preprocessor_sha256=preprocessor_digest(self.fitted),
                model_sha256=model_sha,
            )

    def test_final_holdout_remains_unmaterialized(self) -> None:
        self.assertEqual(V6_FINAL_HOLDOUT_STATUS, "not_materialized")
        for row in self.corpus.observations:
            self.assertNotEqual(row.role, "final_holdout")


if __name__ == "__main__":
    unittest.main()
