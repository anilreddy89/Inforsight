from __future__ import annotations

from dataclasses import replace
import unittest

from inforsight_simulator.v3_config import V3CorpusConfig
from inforsight_simulator.v3_corpus import generate_v3_corpus
from inforsight_simulator.v3_evaluation import (
    FEATURE_GROUPS, V3_FINAL_HOLDOUT_STATUS, build_selection_fold,
    build_temporal_folds, validate_feature_registry, validate_temporal_fold,
)


class V3EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = generate_v3_corpus(V3CorpusConfig())

    def test_feature_registry_is_closed_and_assigns_every_feature_once(self) -> None:
        validate_feature_registry()
        assigned = [feature for group in FEATURE_GROUPS.values() for feature in group]
        self.assertEqual(len(assigned), len(set(assigned)))
        self.assertEqual(FEATURE_GROUPS["recent_payment"][0], "recent_delay_days")

    def test_frozen_folds_are_supported_and_canonically_ordered(self) -> None:
        folds = build_temporal_folds(reversed(self.corpus.observations))
        self.assertEqual([fold.name for fold in folds], ["fold_1", "fold_2", "fold_3"])
        for fold in folds:
            validate_temporal_fold(fold)
            self.assertFalse({row.policy_id for row in fold.fit} & {row.policy_id for row in fold.evaluation})

    def test_selection_fold_fails_closed_on_frozen_minimum_support(self) -> None:
        with self.assertRaisesRegex(ValueError, "selection membership has fewer than 500"):
            build_selection_fold(self.corpus.observations)

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
