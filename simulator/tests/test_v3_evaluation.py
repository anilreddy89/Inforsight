from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from inforsight_simulator.v3_1_config import V31CorpusConfig
from inforsight_simulator.v3_1_corpus import generate_v3_corpus
from inforsight_simulator.v3_evaluation import (
    FEATURE_GROUPS, UNKNOWN_CATEGORY, V3_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION,
    V3_FINAL_HOLDOUT_STATUS, V3_SPLIT_VERSION, authorize, build_selection_fold,
    build_temporal_folds, compare_candidates, diagnostics, fit_preprocessor,
    matrix_digest, preprocessor_digest, structural_support_report, transform,
    validate_authorization, validate_feature_registry, validate_temporal_fold,
)


class V3EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = generate_v3_corpus(V31CorpusConfig())
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
            / "docs/modeling/phase-02r-10-v3-feature-dictionary.json"
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

    def test_amended_selection_fold_passes_support_thresholds(self) -> None:
        self.assertEqual(V3_SPLIT_VERSION, "3.2.0")
        self.assertEqual(V3_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION, "2.2.0")
        self.assertGreaterEqual(len(self.selection_fold.evaluation), 500)
        positives = sum(row.label_value for row in self.selection_fold.evaluation)
        self.assertGreaterEqual(positives, 50)
        self.assertGreaterEqual(len(self.selection_fold.evaluation) - positives, 50)
        validate_temporal_fold(self.selection_fold)

    def test_structural_report_preserves_old_failure_and_new_support(self) -> None:
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

    def test_feature_lineage_and_protected_mutations_fail_before_matrix(self) -> None:
        row = self.selection_fold.evaluation[0]
        missing = dict(row.feature_lineage)
        missing.pop("recent_delay_days")
        with self.assertRaisesRegex(ValueError, "lineage must cover"):
            transform(
                self.fitted, (replace(row, feature_lineage=missing),),
                purpose="selection", role="selection",
            )
        invisible = dict(row.feature_lineage)
        invisible["recent_delay_days"] = ("v3-evt-not-visible",)
        with self.assertRaisesRegex(ValueError, "invisible event"):
            transform(
                self.fitted, (replace(row, feature_lineage=invisible),),
                purpose="selection", role="selection",
            )

    def test_authorization_binds_model_target_membership_and_artifact(self) -> None:
        model_sha = self.candidates["selection"]["selected_model_sha256"]
        authorization = authorize(
            self.train, self.selection, self.fitted, model_sha256=model_sha,
        )
        validate_authorization(
            authorization, self.selection,
            fit_matrix_sha256=matrix_digest(self.train),
            preprocessor_sha256=preprocessor_digest(self.fitted),
            model_sha256=model_sha,
        )
        changed = replace(
            self.selection,
            targets=(1 - self.selection.targets[0],) + self.selection.targets[1:],
        )
        with self.assertRaisesRegex(ValueError, "matrix mismatch"):
            validate_authorization(
                authorization, changed,
                fit_matrix_sha256=matrix_digest(self.train),
                preprocessor_sha256=preprocessor_digest(self.fitted),
                model_sha256=model_sha,
            )
        with self.assertRaisesRegex(ValueError, "model mismatch"):
            validate_authorization(
                authorization, self.selection,
                fit_matrix_sha256=matrix_digest(self.train),
                preprocessor_sha256=preprocessor_digest(self.fitted),
                model_sha256="0" * 64,
            )
        changed_values = replace(
            self.selection,
            values=((self.selection.values[0][0] + 1e-8,) + self.selection.values[0][1:],)
            + self.selection.values[1:],
        )
        self.assertNotEqual(matrix_digest(changed_values), matrix_digest(self.selection))

    def test_candidates_and_diagnostics_are_frozen_before_acceptance(self) -> None:
        self.assertIn(self.candidates["selection"]["selected_candidate"], {"logistic", "xgboost"})
        self.assertEqual(
            self.candidates["selection"]["auc_tolerance"], "0.000000000001",
        )
        self.assertTrue(self.candidates["explicit_state_reload_verified"])
        self.assertEqual(self.diagnostic["decision"], "allow")
        self.assertEqual(self.diagnostic["strongest_group"], "recent_payment")
        self.assertEqual(self.diagnostic["designed_zero_group"], "missingness")
        self.assertEqual(
            {item["flag"] for item in self.diagnostic["dispositions"]},
            {item["id"] for item in self.diagnostic["flags"]},
        )

    def test_committed_structural_evidence_matches_protected_boundary(self) -> None:
        root = Path(__file__).resolve().parents[2]
        report = json.loads((
            root / "docs/experiments/phase-02r-10-v3-structural-support.json"
        ).read_text())
        self.assertEqual(report["materialization"]["feature_matrices"], "not_created")
        self.assertEqual(report["materialization"]["predictions"], "not_created")
        self.assertEqual(report["materialization"]["model_metrics"], "not_created")
        self.assertEqual(report["materialization"]["oracle_sidecars"], "not_accessed")
        self.assertEqual(report["materialization"]["final_holdout"], "not_materialized")

    def test_fold_rejects_policy_overlap_before_modeling(self) -> None:
        fold = build_temporal_folds(self.corpus.observations)[-1]
        overlapping = replace(fold.evaluation[0], policy_id=fold.fit[0].policy_id)
        with self.assertRaisesRegex(ValueError, "policy identity overlaps"):
            validate_temporal_fold(replace(fold, evaluation=(overlapping,) + fold.evaluation[1:]))

    def test_final_holdout_remains_unmaterialized(self) -> None:
        self.assertEqual(V3_FINAL_HOLDOUT_STATUS, "not_materialized")
        self.assertFalse(any(row.role == "final_release_holdout" for row in self.corpus.observations))


if __name__ == "__main__":
    unittest.main()
