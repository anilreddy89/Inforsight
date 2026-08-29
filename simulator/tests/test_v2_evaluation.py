from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from inforsight_simulator.v2_config import V2CorpusConfig
from inforsight_simulator.v2_corpus import generate_v2_corpus, validate_v2_feature_payload
from inforsight_simulator.v2_evaluation import (
    FINAL_HOLDOUT_STATUS, PORTABLE_ARTIFACT_DECIMALS, UNKNOWN_CATEGORY, authorize, build_selection_fold,
    build_temporal_folds, fit_preprocessor, matrix_digest, preprocessor_digest,
    transform, validate_authorization, validate_temporal_fold,
)


class V2EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = generate_v2_corpus(V2CorpusConfig(seed=20260901, run_namespace="r2-05-default"))
        cls.fold = build_selection_fold(cls.corpus.observations)
        cls.fitted = fit_preprocessor(cls.fold)
        cls.train = transform(cls.fitted, cls.fold.fit, purpose="fit", role="fit")
        cls.selection = transform(cls.fitted, cls.fold.acceptance, purpose="selection", role="selection")

    def test_frozen_rolling_origin_folds_pass_structural_checks(self):
        folds = build_temporal_folds(self.corpus.observations)
        self.assertEqual([fold.name for fold in folds], ["fold_1", "fold_2", "fold_3"])
        for fold in folds:
            validate_temporal_fold(fold)
            self.assertFalse({row.policy_id for row in fold.fit} & {row.policy_id for row in fold.acceptance})
            self.assertFalse({row.outcome_episode_id for row in fold.fit} & {row.outcome_episode_id for row in fold.acceptance})

    def test_selection_has_frequency_and_class_support(self):
        for rows in (self.fold.fit, self.fold.acceptance):
            self.assertEqual({row.label_value for row in rows}, {0, 1})
            self.assertEqual({row.features.billing_frequency for row in rows}, {"monthly", "quarterly", "semiannual", "annual"})

    def test_preprocessing_is_fit_only_and_deterministic(self):
        again = fit_preprocessor(self.fold)
        self.assertEqual(preprocessor_digest(self.fitted), preprocessor_digest(again))
        mutated = replace(self.fold.acceptance[0], features=replace(self.fold.acceptance[0].features, premium_amount_cents=999999))
        changed = transform(self.fitted, (mutated,) + self.fold.acceptance[1:], purpose="selection", role="selection")
        self.assertNotEqual(matrix_digest(self.selection), matrix_digest(changed))
        self.assertEqual(preprocessor_digest(self.fitted), preprocessor_digest(again))

    def test_unknown_category_does_not_change_width(self):
        mutated = replace(self.fold.acceptance[0], features=replace(self.fold.acceptance[0].features, contact_category="post_fit_category"))
        matrix = transform(self.fitted, (mutated,) + self.fold.acceptance[1:], purpose="selection", role="selection")
        unknown_index = matrix.feature_names.index(f"contact_category={UNKNOWN_CATEGORY}")
        self.assertEqual(matrix.values[0][unknown_index], 1.0)
        self.assertEqual(matrix.feature_names, self.selection.feature_names)

    def test_authorization_rejects_relabel_and_content_mutation(self):
        auth = authorize(self.train, self.selection, self.fitted)
        validate_authorization(auth, self.selection, matrix_digest(self.train))
        with self.assertRaises(ValueError):
            validate_authorization(auth, replace(self.selection, role="fit"), matrix_digest(self.train))
        changed = replace(self.selection, targets=(1 - self.selection.targets[0],) + self.selection.targets[1:])
        with self.assertRaises(ValueError):
            validate_authorization(auth, changed, matrix_digest(self.train))

    def test_authorization_rejects_reordering_and_cross_fold_use(self):
        auth = authorize(self.train, self.selection, self.fitted)
        reordered = replace(
            self.selection,
            observation_ids=tuple(reversed(self.selection.observation_ids)),
            policy_ids=tuple(reversed(self.selection.policy_ids)),
            episode_ids=tuple(reversed(self.selection.episode_ids)),
            values=tuple(reversed(self.selection.values)),
            targets=tuple(reversed(self.selection.targets)),
        )
        with self.assertRaises(ValueError):
            validate_authorization(auth, reordered, matrix_digest(self.train))
        with self.assertRaises(ValueError):
            authorize(self.train, replace(self.selection, fold="fold_3"), self.fitted)

    def test_fold_validation_rejects_horizon_and_policy_overlap(self):
        invalid_horizon = replace(self.fold.fit[-1], horizon_end=self.fold.acceptance[0].as_of)
        with self.assertRaises(ValueError):
            validate_temporal_fold(replace(self.fold, fit=self.fold.fit[:-1] + (invalid_horizon,)))
        overlapping = replace(self.fold.acceptance[0], policy_id=self.fold.fit[0].policy_id)
        with self.assertRaises(ValueError):
            validate_temporal_fold(replace(self.fold, acceptance=(overlapping,) + self.fold.acceptance[1:]))

    def test_protected_feature_mutations_are_rejected(self):
        payload = vars(self.fold.fit[0].features).copy()
        payload["oracle_probability"] = 0.5
        with self.assertRaises(ValueError):
            validate_v2_feature_payload(payload)
        payload = vars(self.fold.fit[0].features).copy()
        payload["nested"] = {"latent_frailty": 0.1}
        with self.assertRaises(ValueError):
            validate_v2_feature_payload(payload)

    def test_committed_artifacts_bind_lineage_and_complete_dispositions(self):
        root = Path(__file__).resolve().parents[2]
        split = json.loads((root / "docs/experiments/phase-02r-06-v2-split-manifest.json").read_text())
        diagnostic = json.loads((root / "docs/experiments/phase-02r-06-v2-feature-diagnostics-manifest.json").read_text())
        baseline = json.loads((root / "docs/experiments/phase-02r-06-v2-baseline-comparison-manifest.json").read_text())
        self.assertEqual(split["final_holdout_status"], "not_materialized")
        self.assertEqual(baseline["final_holdout_status"], "not_materialized")
        self.assertTrue(baseline["explicit_state_reload_verified"])
        self.assertEqual({item["id"] for item in diagnostic["flags"]}, {item["flag"] for item in diagnostic["dispositions"]})
        self.assertTrue(diagnostic["targeted_perturbations"])
        for artifact in (split, diagnostic, baseline):
            self.assertIn("public_observations_sha256", artifact["lineage"])

    def test_final_holdout_is_not_materialized(self):
        self.assertEqual(FINAL_HOLDOUT_STATUS, "not_materialized")
        self.assertFalse(any(row.role == "final_release_holdout" for row in self.corpus.observations))

    def test_portability_boundary_absorbs_subprecision_noise(self):
        value = 0.1234
        noise = 0.4 * 10 ** (-PORTABLE_ARTIFACT_DECIMALS)
        self.assertEqual(round(value + noise, PORTABLE_ARTIFACT_DECIMALS), value)


if __name__ == "__main__":
    unittest.main()
