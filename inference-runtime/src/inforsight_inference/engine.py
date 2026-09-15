"""NumPy-only transformation, scoring, and additive explanations."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .bundle import ModelBundle


UNKNOWN_CATEGORY = "__unknown__"
NUMERIC_FEATURES = (
    "tenure_days", "premium_amount_cents", "recent_delay_days",
    "recent_failed_payment_count", "recent_retry_count", "recent_recovery_count",
    "arrears_duration_days", "rolling_on_time_rate", "rolling_payment_count",
    "recent_notice_count", "recent_contact_count", "payment_attribute_missing",
    "contact_attribute_missing",
)
CATEGORICAL_FEATURES = (
    "product_type", "billing_frequency", "notice_category", "contact_category",
)


@dataclass(frozen=True)
class ScoringResult:
    raw_logit: float
    calibrated_logit: float
    calibrated_probability: float
    risk_tier: str
    review_queue_eligibility: dict[str, bool]
    root_attributions_log_odds: dict[str, float]
    root_centered_shap: dict[str, float]
    top_risk_drivers: tuple[tuple[str, float], ...]
    top_protective_drivers: tuple[tuple[str, float], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_logit": self.raw_logit,
            "calibrated_logit": self.calibrated_logit,
            "calibrated_probability": self.calibrated_probability,
            "risk_tier": self.risk_tier,
            "review_queue_eligibility": dict(self.review_queue_eligibility),
            "root_attributions_log_odds": dict(self.root_attributions_log_odds),
            "root_centered_shap": dict(self.root_centered_shap),
            "top_risk_drivers": [list(item) for item in self.top_risk_drivers],
            "top_protective_drivers": [list(item) for item in self.top_protective_drivers],
        }


class BundledInferenceEngine:
    """Portable inference engine constructed only from a validated frozen bundle."""

    def __init__(self, bundle: ModelBundle) -> None:
        self.bundle = bundle
        self.preprocessor = bundle.preprocessor
        self.base_model = bundle.base_model
        self.calibrator = bundle.calibrator
        self.explainer_ref = bundle.explainer_reference
        self.policy = bundle.operational_policy
        self.ordered_columns = bundle.preprocessor.ordered_columns
        self.num_cols = len(self.ordered_columns)
        self.raw_intercept = float(bundle.base_model.raw_intercept)
        self.raw_coefs = np.asarray(
            [bundle.base_model.raw_coefficients[col] for col in self.ordered_columns],
            dtype=float,
        )
        self.param_a = float(bundle.calibrator.param_a)
        self.param_b = float(bundle.calibrator.param_b)
        self.calibrated_intercept = float(bundle.calibrator.calibrated_intercept)
        self.calibrated_coefs = np.asarray(
            [bundle.calibrator.calibrated_coefficients[col] for col in self.ordered_columns],
            dtype=float,
        )
        self.bg_means = np.asarray(
            [bundle.explainer_reference.background_column_means[col] for col in self.ordered_columns],
            dtype=float,
        )
        if not all(
            np.isfinite(values).all()
            for values in (self.raw_coefs, self.calibrated_coefs, self.bg_means)
        ):
            raise ValueError("engine vectors must be finite")
        self.base_value_logit = float(bundle.explainer_reference.base_value_logit)
        self.base_value_prob = float(bundle.explainer_reference.base_value_probability)
        self.root_to_indices = {
            root: [] for root in NUMERIC_FEATURES + CATEGORICAL_FEATURES
        }
        for index, column in enumerate(self.ordered_columns):
            if column in self.root_to_indices:
                self.root_to_indices[column].append(index)
                continue
            root = column.partition("=")[0]
            if root in CATEGORICAL_FEATURES:
                self.root_to_indices[root].append(index)

    def transform_features(self, raw_feature_map: Mapping[str, Any]) -> np.ndarray:
        expected = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES)
        if set(raw_feature_map) != expected:
            raise ValueError("feature names do not match the runtime contract")
        vector: list[float] = []
        for name in NUMERIC_FEATURES:
            raw = raw_feature_map[name]
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise ValueError("numeric features must contain finite numbers")
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError("numeric features must contain finite numbers")
            state = self.preprocessor.numeric[name]
            vector.append((value - state.mean) / state.scale)
        for name in CATEGORICAL_FEATURES:
            raw = raw_feature_map[name]
            if not isinstance(raw, str):
                raise ValueError("categorical features must contain strings")
            categories = self.preprocessor.categorical[name].categories
            selected = raw if raw in categories[:-1] else UNKNOWN_CATEGORY
            vector.extend(float(category == selected) for category in categories)
        result = np.asarray(vector, dtype=float)
        if result.shape != (self.num_cols,) or not np.isfinite(result).all():
            raise ValueError("transformed feature vector is incompatible")
        return result

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0.0:
            exp_value = math.exp(-value)
            return 1.0 / (1.0 + exp_value)
        exp_value = math.exp(value)
        return exp_value / (1.0 + exp_value)

    def score_record(self, raw_feature_map: Mapping[str, Any]) -> ScoringResult:
        vector = self.transform_features(raw_feature_map)
        raw_logit = float(self.raw_intercept + np.dot(self.raw_coefs, vector))
        calibrated_logit = float(self.param_a * raw_logit + self.param_b)
        probability = self._sigmoid(calibrated_logit)
        column_attributions = self.calibrated_coefs * vector
        column_shap = self.calibrated_coefs * (vector - self.bg_means)
        root_attributions = {
            root: float(np.sum(column_attributions[indexes]))
            for root, indexes in self.root_to_indices.items()
        }
        root_shap = {
            root: float(np.sum(column_shap[indexes]))
            for root, indexes in self.root_to_indices.items()
        }
        ordered = sorted(root_attributions.items(), key=lambda item: item[1], reverse=True)
        top_risk = tuple(item for item in ordered if item[1] > 0.0)[:3]
        top_protective = tuple(item for item in reversed(ordered) if item[1] < 0.0)[:3]
        risk_tier = self.policy.risk_tiers[-1].name
        for tier in self.policy.risk_tiers:
            if tier.min_prob <= probability < tier.max_prob:
                risk_tier = tier.name
                break
        queues = {
            f"top_{int(queue.capacity_percentile)}_pct": probability >= queue.cutoff_probability
            for queue in self.policy.review_queues
        }
        return ScoringResult(
            raw_logit=raw_logit,
            calibrated_logit=calibrated_logit,
            calibrated_probability=probability,
            risk_tier=risk_tier,
            review_queue_eligibility=queues,
            root_attributions_log_odds=root_attributions,
            root_centered_shap=root_shap,
            top_risk_drivers=top_risk,
            top_protective_drivers=top_protective,
        )

    def score_batch(
        self, raw_feature_maps: Sequence[Mapping[str, Any]]
    ) -> tuple[ScoringResult, ...]:
        return tuple(self.score_record(item) for item in raw_feature_maps)
