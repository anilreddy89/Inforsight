"""RH-06I compatibility evidence between historical and extracted scorers."""

from __future__ import annotations

from pathlib import Path
import unittest

from inforsight_inference import load_configured_runtime
from inforsight_simulator.bundle import (
    BundledInferenceEngine as HistoricalInferenceEngine,
    ModelBundle as HistoricalModelBundle,
)


ROOT = Path(__file__).resolve().parents[2]
BUNDLE_PATH = ROOT / "docs/experiments/phase-02-10-model-bundle.json"


def _features() -> dict[str, object]:
    return {
        "tenure_days": 0.55,
        "premium_amount_cents": 0.96,
        "recent_delay_days": 0.11,
        "recent_failed_payment_count": 0.01,
        "recent_retry_count": 0.01,
        "recent_recovery_count": 0.008,
        "arrears_duration_days": 0.012,
        "rolling_on_time_rate": 0.27,
        "rolling_payment_count": 0.16,
        "recent_notice_count": 0.11,
        "recent_contact_count": 0.10,
        "payment_attribute_missing": 0.02,
        "contact_attribute_missing": 0.0,
        "product_type": "fictional_term_life",
        "billing_frequency": "monthly",
        "notice_category": "none",
        "contact_category": "none",
    }


class InferenceRuntimeCompatibilityTests(unittest.TestCase):
    def test_representative_and_unknown_category_scores_match_historical_engine(self) -> None:
        runtime = load_configured_runtime(BUNDLE_PATH, environ={})
        historical = HistoricalInferenceEngine(HistoricalModelBundle.load(BUNDLE_PATH))
        records = [_features(), {**_features(), "product_type": "fictional_unseen_product"}]

        for record in records:
            expected = historical.score_record(record)
            actual = runtime.engine.score_record(record)
            self.assertAlmostEqual(actual.raw_logit, expected.raw_logit, places=12)
            self.assertAlmostEqual(actual.calibrated_logit, expected.calibrated_logit, places=12)
            self.assertAlmostEqual(
                actual.calibrated_probability,
                expected.calibrated_probability,
                places=12,
            )
            self.assertEqual(actual.risk_tier, expected.risk_tier)
            self.assertEqual(
                actual.review_queue_eligibility,
                expected.review_queue_eligibility,
            )
            self.assertEqual(
                actual.root_attributions_log_odds,
                expected.root_attributions_log_odds,
            )
            self.assertEqual(actual.root_centered_shap, expected.root_centered_shap)
            self.assertEqual(actual.top_risk_drivers, expected.top_risk_drivers)
            self.assertEqual(actual.top_protective_drivers, expected.top_protective_drivers)


if __name__ == "__main__":
    unittest.main()
