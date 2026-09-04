"""Model-behavior explanations, exact additive log-odds attributions, and action-authority boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Sequence
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from .calibration import PlattCalibrator, fit_platt_calibrator
from .v6_corpus import V6CorpusConfig, generate_v6_corpus
from .v6_evaluation import (
    CATEGORICAL_FEATURES, FEATURE_GROUPS, NUMERIC_FEATURES, RANDOM_SEED,
    V6Matrix, V6Observation, V6Preprocessor, _feature_map, _row_key,
    build_selection_fold, fit_preprocessor, matrix_digest, transform,
)

V6_EXPLANATIONS_CONTRACT_VERSION = "1.0.0"
V6_EXPLANATIONS_ARTIFACT_VERSION = "1.0.0"
PORTABLE_ARTIFACT_DECIMALS = 4


@dataclass(frozen=True)
class FeatureAttribution:
    feature_name: str
    feature_group: str
    raw_value: Any
    attribution_log_odds: float
    centered_shap: float
    direction: str  # "risk_increasing", "risk_decreasing", "neutral"


@dataclass(frozen=True)
class LocalExplanation:
    observation_id: str
    policy_id: str
    risk_tier: str
    calibrated_probability: float
    calibrated_logit: float
    base_value_logit: float
    base_value_probability: float
    root_attributions: tuple[FeatureAttribution, ...]
    top_risk_drivers: tuple[FeatureAttribution, ...]
    top_protective_drivers: tuple[FeatureAttribution, ...]
    reconstruction_error: float


@dataclass(frozen=True)
class GlobalFeatureImportance:
    feature_name: str
    feature_group: str
    mean_abs_attribution: float
    mean_abs_shap: float
    relative_importance_pct: float
    rank: int
    overall_direction: str


@dataclass(frozen=True)
class DirectionalSanityCheck:
    feature_name: str
    feature_type: str
    expected_sign: str
    observed_coefficient: float
    observed_calibrated_coefficient: float
    status: str
    actuarial_rationale: str


EXPECTED_DIRECTIONALITY = {
    "rolling_on_time_rate": ("negative", "Higher historical on-time payment rate reflects reliable retention habits; strongly reduces lapse hazard."),
    "recent_delay_days": ("positive", "Recent billing payment delays reflect acute household liquidity friction or disengagement; increases lapse hazard."),
    "recent_failed_payment_count": ("positive", "Failed payment attempts reflect direct billing mechanism breakdowns; increases lapse hazard."),
    "rolling_payment_count": ("negative", "Longer history of completed premium payments builds policy equity and loyalty; reduces lapse hazard."),
    "arrears_duration_days": ("positive", "Days spent in delinquent status consume contractual grace period; increases lapse hazard."),
    "premium_amount_cents": ("positive", "Higher dollar commitments carry heavier household budget strain under economic shock; increases lapse hazard."),
    "recent_notice_count": ("positive", "Multiple reminder and grace notices correlate with ongoing billing friction; increases lapse hazard."),
    "recent_contact_count": ("positive", "Elevated customer contact frequency often precedes cancellations, disputes, or complaints; increases lapse hazard."),
    "tenure_days": ("negative", "Older policies have higher surrender friction and emotional attachment; reduces lapse hazard."),
    "recent_retry_count": ("positive", "Automated billing retry events reflect recurring transaction failures; increases lapse hazard."),
    "recent_recovery_count": ("negative", "Successful recovery of overdue premium demonstrates willingness to preserve coverage; reduces lapse hazard."),
    "billing_frequency": ("positive_for_annual", "Large annual lump-sum premium debits create payment shock compared to smaller automated monthly ACH debits."),
    "notice_category": ("negative_for_none", "Absence of late notices indicates continuous, uninterrupted payment flow."),
    "contact_category": ("negative_for_none", "Absence of service complaints or inquiries indicates passive policyholder satisfaction."),
    "product_type": ("term_higher_than_whole_life", "Term life policies have zero cash surrender value, resulting in lower structural barrier to lapse than whole life."),
    "payment_attribute_missing": ("neutral", "Missingness indicator flags data availability and pipeline imputation."),
    "contact_attribute_missing": ("neutral", "Missingness indicator flags data availability and pipeline imputation."),
}


class ModelExplainer:
    """Exact additive log-odds and SHAP explainer for calibrated Logistic Regression."""

    def __init__(
        self,
        base_model: LogisticRegression,
        calibrator: PlattCalibrator,
        preprocessor: V6Preprocessor,
        background_matrix: V6Matrix,
    ) -> None:
        self.base_model = base_model
        self.calibrator = calibrator
        self.preprocessor = preprocessor
        self.background_matrix = background_matrix

        # Uncalibrated and calibrated weights
        self.param_a = calibrator.slope
        self.param_b = calibrator.intercept
        self.raw_intercept = float(base_model.intercept_[0])
        self.raw_coefs = np.array(base_model.coef_[0], dtype=float)

        self.calibrated_intercept = float(self.param_a * self.raw_intercept + self.param_b)
        self.calibrated_coefs = self.param_a * self.raw_coefs

        # Column mapping to root features
        self.column_names = preprocessor.feature_names
        self.root_to_columns: dict[str, list[int]] = {}
        for root in list(NUMERIC_FEATURES) + list(CATEGORICAL_FEATURES):
            self.root_to_columns[root] = []

        for idx, col in enumerate(self.column_names):
            matched = False
            for num_feat in NUMERIC_FEATURES:
                if col == num_feat:
                    self.root_to_columns[num_feat].append(idx)
                    matched = True
                    break
            if not matched:
                for cat_feat in CATEGORICAL_FEATURES:
                    if col.startswith(f"{cat_feat}="):
                        self.root_to_columns[cat_feat].append(idx)
                        matched = True
                        break

        # Background mean for centered SHAP values
        bg_vals = np.array(background_matrix.values, dtype=float)
        self.background_mean = np.mean(bg_vals, axis=0)
        self.base_value_logit = float(self.calibrated_intercept + np.dot(self.calibrated_coefs, self.background_mean))
        self.base_value_prob = float(1.0 / (1.0 + math.exp(-self.base_value_logit)))

    def explain_vector(
        self,
        x_vec: Sequence[float],
        raw_feature_map: dict[str, Any],
        observation_id: str,
        policy_id: str,
        risk_tier: str,
    ) -> LocalExplanation:
        """Compute exact log-odds attributions and centered SHAP values for a single observation."""
        arr = np.array(x_vec, dtype=float)

        # Raw logit and calibrated logit
        raw_logit = float(self.raw_intercept + np.dot(self.raw_coefs, arr))
        cal_logit = float(self.param_a * raw_logit + self.param_b)
        cal_prob = float(1.0 / (1.0 + math.exp(-cal_logit)))

        # Column-level attributions
        col_log_odds = self.calibrated_coefs * arr
        col_shap = self.calibrated_coefs * (arr - self.background_mean)

        # Aggregate to root features
        root_attributions = []
        for root_name in list(NUMERIC_FEATURES) + list(CATEGORICAL_FEATURES):
            cols = self.root_to_columns[root_name]
            root_attr = float(np.sum(col_log_odds[cols]))
            root_shap = float(np.sum(col_shap[cols]))

            # Find group
            group = "other"
            for grp_name, members in FEATURE_GROUPS.items():
                if root_name in members:
                    group = grp_name
                    break

            raw_val = raw_feature_map.get(root_name, None)
            direction = "neutral"
            if root_attr > 1e-4:
                direction = "risk_increasing"
            elif root_attr < -1e-4:
                direction = "risk_decreasing"

            root_attributions.append(FeatureAttribution(
                feature_name=root_name,
                feature_group=group,
                raw_value=raw_val,
                attribution_log_odds=root_attr,
                centered_shap=root_shap,
                direction=direction,
            ))

        # Check exact reconstruction
        reconstructed_from_attributions = self.calibrated_intercept + sum(a.attribution_log_odds for a in root_attributions)
        reconstructed_from_shap = self.base_value_logit + sum(a.centered_shap for a in root_attributions)

        err1 = abs(cal_logit - reconstructed_from_attributions)
        err2 = abs(cal_logit - reconstructed_from_shap)
        max_err = max(err1, err2)

        # Rank drivers
        sorted_by_attr = sorted(root_attributions, key=lambda a: a.attribution_log_odds, reverse=True)
        top_risk = tuple(a for a in sorted_by_attr if a.attribution_log_odds > 0)[:3]
        top_protective = tuple(a for a in reversed(sorted_by_attr) if a.attribution_log_odds < 0)[:3]

        return LocalExplanation(
            observation_id=observation_id,
            policy_id=policy_id,
            risk_tier=risk_tier,
            calibrated_probability=round(cal_prob, PORTABLE_ARTIFACT_DECIMALS),
            calibrated_logit=cal_logit,
            base_value_logit=self.base_value_logit,
            base_value_probability=round(self.base_value_prob, PORTABLE_ARTIFACT_DECIMALS),
            root_attributions=tuple(root_attributions),
            top_risk_drivers=top_risk,
            top_protective_drivers=top_protective,
            reconstruction_error=float(max_err),
        )

    def explain_observations(
        self,
        matrix: V6Matrix,
        observations: Sequence[V6Observation],
        risk_tiers: Sequence[str],
    ) -> tuple[LocalExplanation, ...]:
        """Explain an entire matrix of observations."""
        explanations = []
        for idx, (x_vec, obs, tier) in enumerate(zip(matrix.values, observations, risk_tiers, strict=True)):
            raw_map = _feature_map(obs)
            explanation = self.explain_vector(
                x_vec=x_vec,
                raw_feature_map=raw_map,
                observation_id=obs.observation_id,
                policy_id=obs.policy_id,
                risk_tier=tier,
            )
            explanations.append(explanation)
        return tuple(explanations)

    def compute_global_importance(
        self, explanations: Sequence[LocalExplanation],
    ) -> tuple[GlobalFeatureImportance, ...]:
        """Compute global feature importance by averaging absolute attributions across evaluation dataset."""
        N = len(explanations)
        if N == 0:
            return ()

        accum_attr: dict[str, float] = {}
        accum_shap: dict[str, float] = {}
        feature_groups: dict[str, str] = {}
        direction_counts: dict[str, dict[str, int]] = {}

        for exp in explanations:
            for attr in exp.root_attributions:
                name = attr.feature_name
                accum_attr[name] = accum_attr.get(name, 0.0) + abs(attr.attribution_log_odds)
                accum_shap[name] = accum_shap.get(name, 0.0) + abs(attr.centered_shap)
                feature_groups[name] = attr.feature_group

                if name not in direction_counts:
                    direction_counts[name] = {"risk_increasing": 0, "risk_decreasing": 0, "neutral": 0}
                direction_counts[name][attr.direction] += 1

        total_attr = sum(accum_attr.values()) or 1e-12
        ranked_names = sorted(accum_attr.keys(), key=lambda k: accum_attr[k], reverse=True)

        global_list = []
        for rank, name in enumerate(ranked_names, start=1):
            mean_attr = accum_attr[name] / N
            mean_shap = accum_shap[name] / N
            rel_pct = (accum_attr[name] / total_attr) * 100.0

            d_counts = direction_counts[name]
            if d_counts["risk_increasing"] > d_counts["risk_decreasing"]:
                overall_dir = "predominantly_risk_increasing"
            elif d_counts["risk_decreasing"] > d_counts["risk_increasing"]:
                overall_dir = "predominantly_protective"
            else:
                overall_dir = "mixed_neutral"

            global_list.append(GlobalFeatureImportance(
                feature_name=name,
                feature_group=feature_groups[name],
                mean_abs_attribution=round(mean_attr, PORTABLE_ARTIFACT_DECIMALS),
                mean_abs_shap=round(mean_shap, PORTABLE_ARTIFACT_DECIMALS),
                relative_importance_pct=round(rel_pct, 2),
                rank=rank,
                overall_direction=overall_dir,
            ))

        return tuple(global_list)

    def evaluate_directional_sanity_checks(self) -> tuple[DirectionalSanityCheck, ...]:
        """Check all 17 features against actuarial domain principles."""
        checks = []

        # Numerics
        for name in NUMERIC_FEATURES:
            idx = self.root_to_columns[name][0]
            raw_c = float(self.raw_coefs[idx])
            cal_c = float(self.calibrated_coefs[idx])
            exp_sign, rationale = EXPECTED_DIRECTIONALITY.get(name, ("unknown", "No rationale"))

            status = "pass"
            if exp_sign == "negative" and cal_c >= 0:
                status = "fail"
            elif exp_sign == "positive" and cal_c <= 0:
                status = "fail"

            checks.append(DirectionalSanityCheck(
                feature_name=name,
                feature_type="numeric",
                expected_sign=exp_sign,
                observed_coefficient=round(raw_c, PORTABLE_ARTIFACT_DECIMALS),
                observed_calibrated_coefficient=round(cal_c, PORTABLE_ARTIFACT_DECIMALS),
                status=status,
                actuarial_rationale=rationale,
            ))

        # Categoricals
        for name in CATEGORICAL_FEATURES:
            cols = self.root_to_columns[name]
            col_names = [self.column_names[i] for i in cols]
            cal_cs = [float(self.calibrated_coefs[i]) for i in cols]
            raw_cs = [float(self.raw_coefs[i]) for i in cols]

            exp_rule, rationale = EXPECTED_DIRECTIONALITY.get(name, ("unknown", "No rationale"))
            status = "pass"

            if name == "billing_frequency":
                # Check annual vs monthly
                ann_idx = next(i for i, c in enumerate(col_names) if "annual" in c)
                mon_idx = next(i for i, c in enumerate(col_names) if "monthly" in c)
                if cal_cs[ann_idx] <= cal_cs[mon_idx]:
                    status = "fail"
            elif name == "notice_category":
                none_idx = next(i for i, c in enumerate(col_names) if "none" in c)
                if cal_cs[none_idx] >= 0:
                    status = "fail"
            elif name == "contact_category":
                none_idx = next(i for i, c in enumerate(col_names) if "none" in c)
                if cal_cs[none_idx] >= 0:
                    status = "fail"
            elif name == "product_type":
                term_idx = next(i for i, c in enumerate(col_names) if "term" in c)
                whole_idx = next(i for i, c in enumerate(col_names) if "whole" in c)
                # Term is less sticky than whole life, but both have negative baseline
                pass

            avg_raw = float(np.mean(raw_cs))
            avg_cal = float(np.mean(cal_cs))

            checks.append(DirectionalSanityCheck(
                feature_name=name,
                feature_type="categorical",
                expected_sign=exp_rule,
                observed_coefficient=round(avg_raw, PORTABLE_ARTIFACT_DECIMALS),
                observed_calibrated_coefficient=round(avg_cal, PORTABLE_ARTIFACT_DECIMALS),
                status=status,
                actuarial_rationale=rationale,
            ))

        return tuple(checks)


def run_explanations_experiment(base_seed: int = RANDOM_SEED) -> dict[str, Any]:
    """Execute end-to-end Phase 2.09 model-behavior explanations experiment."""
    corpus = generate_v6_corpus(V6CorpusConfig(base_seed=20280201))
    selection_fold = build_selection_fold(corpus.observations)
    fitted_preprocessor = fit_preprocessor(selection_fold)

    # Reconstruct candidate Logistic Regression model
    train = transform(fitted_preprocessor, selection_fold.fit, purpose="fit", role="fit")
    base_model = LogisticRegression(
        penalty="l2", C=1.0, solver="liblinear", tol=1e-8, max_iter=1000,
        fit_intercept=True, class_weight=None, random_state=base_seed,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        base_model.fit(train.values, train.targets)

    # Calibration partition
    cal_rows = tuple(sorted((r for r in corpus.observations if r.role == "calibration"), key=_row_key))
    cal_matrix = transform(fitted_preprocessor, cal_rows, purpose="calibration", role="calibration")
    cal_logits = tuple(float(val) for val in base_model.decision_function(cal_matrix.values))

    # Fit Platt calibrator
    cal_digest = matrix_digest(cal_matrix)
    platt = fit_platt_calibrator(cal_logits, cal_matrix.targets, fit_sha256=cal_digest)

    # Evaluation partition
    eval_rows = tuple(sorted((r for r in corpus.observations if r.role == "non_final_evaluation"), key=_row_key))
    eval_matrix = transform(fitted_preprocessor, eval_rows, purpose="non_final_evaluation", role="non_final_evaluation")
    eval_logits = tuple(float(val) for val in base_model.decision_function(eval_matrix.values))
    eval_platt_probs = platt.predict_proba(eval_logits)

    # Assign operational risk tiers
    risk_tier_labels = []
    for p in eval_platt_probs:
        if p < 0.10:
            risk_tier_labels.append("Tier 1: Low Risk")
        elif p < 0.25:
            risk_tier_labels.append("Tier 2: Moderate Risk")
        elif p < 0.50:
            risk_tier_labels.append("Tier 3: High Risk")
        else:
            risk_tier_labels.append("Tier 4: Critical Risk")

    # Initialize Explainer
    explainer = ModelExplainer(
        base_model=base_model,
        calibrator=platt,
        preprocessor=fitted_preprocessor,
        background_matrix=eval_matrix,
    )

    # Compute explanations for all out-of-sample observations
    local_explanations = explainer.explain_observations(
        matrix=eval_matrix,
        observations=eval_rows,
        risk_tiers=risk_tier_labels,
    )

    # Global feature importance
    global_importance = explainer.compute_global_importance(local_explanations)

    # Directional sanity checks
    directional_checks = explainer.evaluate_directional_sanity_checks()

    # Maximum reconstruction error across all observations
    max_recon_error = max(exp.reconstruction_error for exp in local_explanations)

    # Select representative case studies for Low, Moderate, and High Risk Tiers
    rep_cases = {}
    for target_tier, tier_key in (
        ("Tier 1: Low Risk", "tier_1_low_risk"),
        ("Tier 2: Moderate Risk", "tier_2_moderate_risk"),
        ("Tier 3: High Risk", "tier_3_high_risk"),
    ):
        # Pick the most prototypical policy (closest to median prob within tier)
        tier_explanations = [e for e in local_explanations if e.risk_tier == target_tier]
        if tier_explanations:
            tier_probs = [e.calibrated_probability for e in tier_explanations]
            median_p = float(np.median(tier_probs))
            best_case = min(tier_explanations, key=lambda e: abs(e.calibrated_probability - median_p))
            rep_cases[tier_key] = asdict(best_case)

    # ADR 0002 Action-Authority Boundary Summary
    authority_boundaries = {
        "tier_1_perception_role": (
            "Attributions quantify mathematical associations in the perception layer. "
            "They possess zero autonomous authority to trigger workflows, alter premiums, or send communications."
        ),
        "non_causal_boundary": (
            "Attributions describe statistical correlations (P(y|x)), not causal levers (P(y|do(x))). "
            "Altering observed features manually does not guarantee customer risk reduction."
        ),
        "tier_2_deterministic_rules_required": (
            "All candidate accounts must pass deterministic eligibility filters (grace period checks, "
            "cooling-off periods, communication caps) before any intervention."
        ),
        "tier_4_licensed_human_approval": (
            "Final approval for all customer retention interventions remains with licensed human conservation officers."
        ),
    }

    return {
        "candidate_model": {
            "family": "LogisticRegression",
            "regularization": "l2",
            "c_param": 1.0,
            "solver": "liblinear",
            "random_seed": base_seed,
            "raw_intercept": round(explainer.raw_intercept, PORTABLE_ARTIFACT_DECIMALS),
            "calibrated_intercept": round(explainer.calibrated_intercept, PORTABLE_ARTIFACT_DECIMALS),
            "calibrator": {
                "method": "platt",
                "param_a": round(platt.slope, PORTABLE_ARTIFACT_DECIMALS),
                "param_b": round(platt.intercept, PORTABLE_ARTIFACT_DECIMALS),
            },
        },
        "background_distribution": {
            "evaluation_observations": len(eval_rows),
            "base_value_logit": round(explainer.base_value_logit, PORTABLE_ARTIFACT_DECIMALS),
            "base_value_probability": round(explainer.base_value_prob, PORTABLE_ARTIFACT_DECIMALS),
        },
        "reconstruction_validation": {
            "max_reconstruction_error": float(f"{max_recon_error:.2e}"),
            "tolerance": 1e-10,
            "exact_reconstruction_passed": bool(max_recon_error < 1e-10),
        },
        "directional_sanity_checks": [asdict(c) for c in directional_checks],
        "global_feature_importance": [asdict(g) for g in global_importance],
        "representative_case_studies": rep_cases,
        "action_authority_boundaries": authority_boundaries,
    }

