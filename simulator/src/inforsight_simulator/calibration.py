"""Phase 2.08 Probability Calibration and Operational Thresholds engine."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from typing import Any, Iterable, Sequence
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, brier_score_loss, log_loss, roc_auc_score,
)

from .v6_config import V6_SIMULATOR_CONTRACT_VERSION, V6CorpusConfig
from .v6_corpus import V6Observation, generate_v6_corpus
from .v6_evaluation import (
    PORTABLE_ARTIFACT_DECIMALS, RANDOM_SEED, V6Matrix, V6Preprocessor,
    _digest, _row_key, build_selection_fold, fit_preprocessor, matrix_digest,
    transform,
)


V6_CALIBRATION_CONTRACT_VERSION = "1.0.0"
V6_CALIBRATION_ARTIFACT_VERSION = "1.0.0"
DEFAULT_N_BINS = 10
DEFAULT_CAPACITIES = (0.01, 0.02, 0.05, 0.10, 0.15, 0.20)
DEFAULT_COST_RATIOS = (0.02, 0.05, 0.10, 0.15, 0.20, 0.25)
DEFAULT_BOOTSTRAP_REPLICATES = 1000


@dataclass(frozen=True)
class PlattCalibrator:
    """Univariate logistic probability calibrator over model logits."""

    slope: float
    intercept: float
    fit_records: int
    fit_sha256: str

    def predict_proba(self, logits: Sequence[float]) -> tuple[float, ...]:
        """Map raw logits to calibrated probabilities."""
        results = []
        for z in logits:
            val = self.slope * float(z) + self.intercept
            clipped = min(max(val, -30.0), 30.0)
            results.append(1.0 / (1.0 + math.exp(-clipped)))
        return tuple(results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "platt_scaling",
            "slope": round(self.slope, 6),
            "intercept": round(self.intercept, 6),
            "fit_records": self.fit_records,
            "fit_sha256": self.fit_sha256,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlattCalibrator:
        return cls(
            slope=float(data["slope"]),
            intercept=float(data["intercept"]),
            fit_records=int(data["fit_records"]),
            fit_sha256=str(data["fit_sha256"]),
        )


@dataclass(frozen=True)
class IsotonicCalibrator:
    """Piecewise-constant isotonic regression calibrator."""

    x_thresholds: tuple[float, ...]
    y_thresholds: tuple[float, ...]
    fit_records: int
    fit_sha256: str

    def predict_proba(self, probs: Sequence[float]) -> tuple[float, ...]:
        """Interpolate probabilities using fitted step thresholds."""
        xs = np.array(self.x_thresholds)
        ys = np.array(self.y_thresholds)
        input_probs = np.clip(np.array(probs, dtype=float), 0.0, 1.0)
        output = np.interp(input_probs, xs, ys)
        return tuple(float(val) for val in output)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "isotonic_regression",
            "knot_count": len(self.x_thresholds),
            "x_thresholds": [round(val, 6) for val in self.x_thresholds],
            "y_thresholds": [round(val, 6) for val in self.y_thresholds],
            "fit_records": self.fit_records,
            "fit_sha256": self.fit_sha256,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IsotonicCalibrator:
        return cls(
            x_thresholds=tuple(float(val) for val in data["x_thresholds"]),
            y_thresholds=tuple(float(val) for val in data["y_thresholds"]),
            fit_records=int(data["fit_records"]),
            fit_sha256=str(data["fit_sha256"]),
        )


@dataclass(frozen=True)
class CalibrationMetrics:
    """Full quantitative calibration and discrimination evaluation."""

    brier_score: float
    brier_skill_score: float
    ece: float
    mce: float
    reliability: float
    resolution: float
    uncertainty: float
    within_bin_variance: float
    bin_discretization_delta: float
    log_loss: float
    roc_auc: float
    average_precision: float
    calibration_slope: float
    calibration_intercept: float
    bins: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "brier_score": round(self.brier_score, PORTABLE_ARTIFACT_DECIMALS),
            "brier_skill_score": round(self.brier_skill_score, PORTABLE_ARTIFACT_DECIMALS),
            "ece": round(self.ece, PORTABLE_ARTIFACT_DECIMALS),
            "mce": round(self.mce, PORTABLE_ARTIFACT_DECIMALS),
            "reliability": round(self.reliability, PORTABLE_ARTIFACT_DECIMALS + 2),
            "resolution": round(self.resolution, PORTABLE_ARTIFACT_DECIMALS + 2),
            "uncertainty": round(self.uncertainty, PORTABLE_ARTIFACT_DECIMALS + 2),
            "within_bin_variance": round(self.within_bin_variance, PORTABLE_ARTIFACT_DECIMALS + 2),
            "bin_discretization_delta": round(self.bin_discretization_delta, PORTABLE_ARTIFACT_DECIMALS + 2),
            "log_loss": round(self.log_loss, PORTABLE_ARTIFACT_DECIMALS),
            "roc_auc": round(self.roc_auc, PORTABLE_ARTIFACT_DECIMALS),
            "average_precision": round(self.average_precision, PORTABLE_ARTIFACT_DECIMALS),
            "calibration_slope": round(self.calibration_slope, PORTABLE_ARTIFACT_DECIMALS),
            "calibration_intercept": round(self.calibration_intercept, PORTABLE_ARTIFACT_DECIMALS),
            "bins": list(self.bins),
        }


@dataclass(frozen=True)
class OperationalPoint:
    """Performance profile at an operational review capacity."""

    capacity: float
    threshold: float
    reviewed_count: int
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    specificity: float
    lift: float
    nnr: float
    net_benefit: float
    precision_ci_95: tuple[float, float]
    recall_ci_95: tuple[float, float]
    lift_ci_95: tuple[float, float]
    net_benefit_ci_95: tuple[float, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capacity": self.capacity,
            "threshold": round(self.threshold, PORTABLE_ARTIFACT_DECIMALS),
            "reviewed_count": self.reviewed_count,
            "confusion_matrix": {
                "tp": self.tp, "fp": self.fp, "tn": self.tn, "fn": self.fn,
            },
            "precision": round(self.precision, PORTABLE_ARTIFACT_DECIMALS),
            "recall": round(self.recall, PORTABLE_ARTIFACT_DECIMALS),
            "specificity": round(self.specificity, PORTABLE_ARTIFACT_DECIMALS),
            "lift": round(self.lift, PORTABLE_ARTIFACT_DECIMALS),
            "nnr": round(self.nnr, 2),
            "net_benefit": round(self.net_benefit, PORTABLE_ARTIFACT_DECIMALS),
            "precision_ci_95": [round(val, PORTABLE_ARTIFACT_DECIMALS) for val in self.precision_ci_95],
            "recall_ci_95": [round(val, PORTABLE_ARTIFACT_DECIMALS) for val in self.recall_ci_95],
            "lift_ci_95": [round(val, PORTABLE_ARTIFACT_DECIMALS) for val in self.lift_ci_95],
            "net_benefit_ci_95": [round(val, PORTABLE_ARTIFACT_DECIMALS) for val in self.net_benefit_ci_95],
        }


@dataclass(frozen=True)
class RiskTier:
    """Operational action band based on calibrated probability."""

    tier_name: str
    threshold_min: float
    threshold_max: float
    count: int
    fraction: float
    observed_lapses: int
    observed_rate: float
    action_protocol: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier_name": self.tier_name,
            "threshold_range": [round(self.threshold_min, 4), round(self.threshold_max, 4)],
            "count": self.count,
            "fraction": round(self.fraction, PORTABLE_ARTIFACT_DECIMALS),
            "observed_lapses": self.observed_lapses,
            "observed_rate": round(self.observed_rate, PORTABLE_ARTIFACT_DECIMALS),
            "action_protocol": self.action_protocol,
        }


def fit_platt_calibrator(
    logits: Sequence[float], targets: Sequence[int], *, fit_sha256: str = "",
) -> PlattCalibrator:
    """Fit a univariate logistic model over raw candidate logits."""
    x = np.array(logits, dtype=float).reshape(-1, 1)
    y = np.array(targets, dtype=int)
    if len(np.unique(y)) < 2:
        raise ValueError("platt calibration requires both binary classes")

    clf = LogisticRegression(
        penalty=None, solver="lbfgs", fit_intercept=True, tol=1e-8, max_iter=1000,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        clf.fit(x, y)

    slope = float(clf.coef_[0][0])
    intercept = float(clf.intercept_[0])
    return PlattCalibrator(
        slope=slope, intercept=intercept, fit_records=len(targets), fit_sha256=fit_sha256,
    )


def fit_isotonic_calibrator(
    probs: Sequence[float], targets: Sequence[int], *, fit_sha256: str = "",
) -> IsotonicCalibrator:
    """Fit a monotonic isotonic regression step function over raw probabilities."""
    x = np.clip(np.array(probs, dtype=float), 0.0, 1.0)
    y = np.array(targets, dtype=int)
    if len(np.unique(y)) < 2:
        raise ValueError("isotonic calibration requires both binary classes")

    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(x, y)
    return IsotonicCalibrator(
        x_thresholds=tuple(float(val) for val in iso.X_thresholds_),
        y_thresholds=tuple(float(val) for val in iso.y_thresholds_),
        fit_records=len(targets),
        fit_sha256=fit_sha256,
    )


def evaluate_calibration(
    targets: Sequence[int], probs: Sequence[float], *, n_bins: int = DEFAULT_N_BINS,
) -> CalibrationMetrics:
    """Compute complete quantitative calibration metrics and Murphy decomposition."""
    t = np.array(targets, dtype=int)
    p = np.clip(np.array(probs, dtype=float), 1e-12, 1.0 - 1e-12)
    N = len(t)
    if N == 0:
        raise ValueError("cannot evaluate calibration on empty predictions")

    base_rate = float(np.mean(t))
    unc = float(base_rate * (1.0 - base_rate))
    bs = float(brier_score_loss(t, p))
    bss = float(1.0 - (bs / unc)) if unc > 0 else 0.0

    # 10 Quantile Bins for stable sample sizes
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    bin_edges = np.quantile(p, quantiles)
    bin_edges[0] -= 1e-7
    bin_edges[-1] += 1e-7

    ece = 0.0
    mce = 0.0
    rel = 0.0
    res = 0.0
    var_w = 0.0
    cov_w = 0.0
    bins_info = []

    for i in range(n_bins):
        mask = (p > bin_edges[i]) & (p <= bin_edges[i + 1])
        count = int(np.sum(mask))
        if count == 0:
            continue
        p_b = float(np.mean(p[mask]))
        y_b = float(np.mean(t[mask]))
        err = abs(p_b - y_b)
        ece += (count / N) * err
        mce = max(mce, err)
        rel += (count / N) * ((p_b - y_b) ** 2)
        res += (count / N) * ((y_b - base_rate) ** 2)
        var_w += float(np.sum((p[mask] - p_b) ** 2)) / N
        cov_w += float(np.sum((p[mask] - p_b) * (t[mask] - y_b))) / N

        # Wilson score interval for observed rate
        z = 1.96
        denom = 1.0 + (z ** 2) / count
        center = (y_b + (z ** 2) / (2.0 * count)) / denom
        delta = (z * math.sqrt((y_b * (1.0 - y_b) + (z ** 2) / (4.0 * count)) / count)) / denom
        wilson_lb = max(0.0, center - delta)
        wilson_ub = min(1.0, center + delta)

        bins_info.append({
            "bin": i + 1,
            "count": count,
            "mean_pred": round(p_b, PORTABLE_ARTIFACT_DECIMALS),
            "observed_rate": round(y_b, PORTABLE_ARTIFACT_DECIMALS),
            "abs_error": round(err, PORTABLE_ARTIFACT_DECIMALS),
            "wilson_ci_95": [round(wilson_lb, PORTABLE_ARTIFACT_DECIMALS), round(wilson_ub, PORTABLE_ARTIFACT_DECIMALS)],
        })

    delta_w = var_w - 2.0 * cov_w

    # Calibration Slope & Intercept via logistic regression on log-odds
    log_odds = np.log(p / (1.0 - p)).reshape(-1, 1)
    lr_cal = LogisticRegression(penalty=None, solver="lbfgs", fit_intercept=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        lr_cal.fit(log_odds, t)
    cal_slope = float(lr_cal.coef_[0][0])
    cal_intercept = float(lr_cal.intercept_[0])

    roc = float(roc_auc_score(t, p))
    ap = float(average_precision_score(t, p))
    ll = float(log_loss(t, p, labels=[0, 1]))

    return CalibrationMetrics(
        brier_score=bs,
        brier_skill_score=bss,
        ece=ece,
        mce=mce,
        reliability=rel,
        resolution=res,
        uncertainty=unc,
        within_bin_variance=var_w,
        bin_discretization_delta=delta_w,
        log_loss=ll,
        roc_auc=roc,
        average_precision=ap,
        calibration_slope=cal_slope,
        calibration_intercept=cal_intercept,
        bins=tuple(bins_info),
    )


def evaluate_operational_capacities(
    targets: Sequence[int],
    probs: Sequence[float],
    policy_ids: Sequence[str],
    *,
    capacities: Sequence[float] = DEFAULT_CAPACITIES,
    n_bootstraps: int = DEFAULT_BOOTSTRAP_REPLICATES,
    seed: int = RANDOM_SEED,
) -> tuple[OperationalPoint, ...]:
    """Evaluate operational performance across review capacities with cluster bootstrap CIs."""
    t = np.array(targets, dtype=int)
    p = np.array(probs, dtype=float)
    N = len(t)
    prevalence = float(np.mean(t))

    # Base operating points
    results = []
    thresholds_by_cap = {}
    for cap in capacities:
        k = int(round(cap * N))
        k = max(1, min(k, N - 1))
        cutoff = float(np.partition(p, -k)[-k])
        thresholds_by_cap[cap] = cutoff
        flagged = p >= cutoff
        tp = int(np.sum(flagged & (t == 1)))
        fp = int(np.sum(flagged & (t == 0)))
        tn = int(np.sum((~flagged) & (t == 0)))
        fn = int(np.sum((~flagged) & (t == 1)))

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        lift = prec / prevalence if prevalence > 0 else 1.0
        nnr = 1.0 / prec if prec > 0 else float("inf")
        net_ben = (tp / N) - (fp / N) * (cutoff / (1.0 - cutoff)) if cutoff < 1.0 else 0.0

        results.append({
            "capacity": cap,
            "threshold": cutoff,
            "reviewed_count": tp + fp,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": prec, "recall": rec, "specificity": spec,
            "lift": lift, "nnr": nnr, "net_benefit": net_ben,
        })

    # Policy-cluster bootstrap for 95% CIs
    policy_to_indices = defaultdict(list)
    for idx, pid in enumerate(policy_ids):
        policy_to_indices[pid].append(idx)
    unique_pids = np.array(sorted(policy_to_indices.keys()))
    n_clusters = len(unique_pids)

    rng = np.random.default_rng(seed)
    boot_prec = {cap: [] for cap in capacities}
    boot_rec = {cap: [] for cap in capacities}
    boot_lift = {cap: [] for cap in capacities}
    boot_net = {cap: [] for cap in capacities}

    for _ in range(n_bootstraps):
        sampled_pids = rng.choice(unique_pids, size=n_clusters, replace=True)
        sampled_indices = []
        for pid in sampled_pids:
            sampled_indices.extend(policy_to_indices[pid])

        sub_t = t[sampled_indices]
        sub_p = p[sampled_indices]
        n_sub = len(sub_t)
        sub_prev = float(np.mean(sub_t)) if n_sub > 0 else 1e-12

        for cap in capacities:
            k = int(round(cap * n_sub))
            k = max(1, min(k, n_sub - 1))
            cutoff = float(np.partition(sub_p, -k)[-k])
            flagged = sub_p >= cutoff
            tp = int(np.sum(flagged & (sub_t == 1)))
            fp = int(np.sum(flagged & (sub_t == 0)))
            fn = int(np.sum((~flagged) & (sub_t == 1)))

            b_prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            b_rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            b_lift = b_prec / sub_prev if sub_prev > 0 else 1.0
            b_net = (tp / n_sub) - (fp / n_sub) * (cutoff / (1.0 - cutoff)) if cutoff < 1.0 else 0.0

            boot_prec[cap].append(b_prec)
            boot_rec[cap].append(b_rec)
            boot_lift[cap].append(b_lift)
            boot_net[cap].append(b_net)

    points = []
    for item in results:
        cap = item["capacity"]
        prec_ci = (float(np.percentile(boot_prec[cap], 2.5)), float(np.percentile(boot_prec[cap], 97.5)))
        rec_ci = (float(np.percentile(boot_rec[cap], 2.5)), float(np.percentile(boot_rec[cap], 97.5)))
        lift_ci = (float(np.percentile(boot_lift[cap], 2.5)), float(np.percentile(boot_lift[cap], 97.5)))
        net_ci = (float(np.percentile(boot_net[cap], 2.5)), float(np.percentile(boot_net[cap], 97.5)))

        points.append(OperationalPoint(
            capacity=cap,
            threshold=item["threshold"],
            reviewed_count=item["reviewed_count"],
            tp=item["tp"],
            fp=item["fp"],
            tn=item["tn"],
            fn=item["fn"],
            precision=item["precision"],
            recall=item["recall"],
            specificity=item["specificity"],
            lift=item["lift"],
            nnr=item["nnr"],
            net_benefit=item["net_benefit"],
            precision_ci_95=prec_ci,
            recall_ci_95=rec_ci,
            lift_ci_95=lift_ci,
            net_benefit_ci_95=net_ci,
        ))

    return tuple(points)


def evaluate_decision_curves(
    targets: Sequence[int], probs: Sequence[float], *, cost_ratios: Sequence[float] = DEFAULT_COST_RATIOS,
) -> tuple[dict[str, float], ...]:
    """Compute Net Benefit curves across exchange rates (cost ratios r = C_FP / C_FN)."""
    t = np.array(targets, dtype=int)
    p = np.array(probs, dtype=float)
    N = len(t)
    prevalence = float(np.mean(t))

    curves = []
    for r in cost_ratios:
        tau = float(r / (1.0 + r))
        flagged = p >= tau
        tp = float(np.sum(flagged & (t == 1)))
        fp = float(np.sum(flagged & (t == 0)))

        net_model = (tp / N) - (fp / N) * (tau / (1.0 - tau))
        net_treat_all = prevalence - (1.0 - prevalence) * (tau / (1.0 - tau))
        net_treat_none = 0.0

        curves.append({
            "cost_ratio": round(r, 4),
            "implied_threshold": round(tau, 4),
            "net_benefit_model": round(net_model, PORTABLE_ARTIFACT_DECIMALS),
            "net_benefit_treat_all": round(net_treat_all, PORTABLE_ARTIFACT_DECIMALS),
            "net_benefit_treat_none": round(net_treat_none, PORTABLE_ARTIFACT_DECIMALS),
            "benefit_over_treat_all": round(net_model - net_treat_all, PORTABLE_ARTIFACT_DECIMALS),
        })
    return tuple(curves)


def evaluate_risk_tiers(
    targets: Sequence[int],
    probs: Sequence[float],
    *,
    tau_low: float = 0.08,
    tau_high: float = 0.20,
) -> tuple[RiskTier, ...]:
    """Partition predictions into standard operational risk bands."""
    t = np.array(targets, dtype=int)
    p = np.array(probs, dtype=float)
    N = len(t)

    masks = {
        "Tier 1: Low Risk": (p < tau_low, 0.0, tau_low, "Standard automated billing & digital account servicing; zero outreach expense."),
        "Tier 2: Moderate Risk": ((p >= tau_low) & (p < tau_high), tau_low, tau_high, "Automated retention touchpoint (email/SMS billing reminder, mobile app nudge)."),
        "Tier 3: High Risk": (p >= tau_high, tau_high, 1.0, "Priority queue for specialist conservation outreach (phone consultation, premium flexibility)."),
    }

    tiers = []
    for name, (mask, t_min, t_max, action) in masks.items():
        count = int(np.sum(mask))
        lapses = int(np.sum(t[mask]))
        rate = lapses / count if count > 0 else 0.0
        tiers.append(RiskTier(
            tier_name=name,
            threshold_min=t_min,
            threshold_max=t_max,
            count=count,
            fraction=count / N if N > 0 else 0.0,
            observed_lapses=lapses,
            observed_rate=rate,
            action_protocol=action,
        ))
    return tuple(tiers)


def run_calibration_experiment(
    base_seed: int = RANDOM_SEED,
) -> dict[str, Any]:
    """Execute end-to-end Phase 2.08 probability calibration and operational evaluation."""
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

    # Extract calibration role partition and non_final_evaluation partition
    cal_rows = tuple(sorted((r for r in corpus.observations if r.role == "calibration"), key=_row_key))
    eval_rows = tuple(sorted((r for r in corpus.observations if r.role == "non_final_evaluation"), key=_row_key))

    cal_matrix = transform(fitted_preprocessor, cal_rows, purpose="calibration", role="calibration")
    eval_matrix = transform(fitted_preprocessor, eval_rows, purpose="non_final_evaluation", role="non_final_evaluation")

    # Raw candidate scores
    cal_logits = tuple(float(val) for val in base_model.decision_function(cal_matrix.values))
    cal_raw_probs = tuple(float(val) for val in base_model.predict_proba(cal_matrix.values)[:, 1])
    eval_logits = tuple(float(val) for val in base_model.decision_function(eval_matrix.values))
    eval_raw_probs = tuple(float(val) for val in base_model.predict_proba(eval_matrix.values)[:, 1])

    # Fit post-hoc calibrators on calibration partition
    cal_digest = matrix_digest(cal_matrix)
    platt = fit_platt_calibrator(cal_logits, cal_matrix.targets, fit_sha256=cal_digest)
    isotonic = fit_isotonic_calibrator(cal_raw_probs, cal_matrix.targets, fit_sha256=cal_digest)

    # Calibrated probabilities on out-of-sample evaluation partition
    eval_platt_probs = platt.predict_proba(eval_logits)
    eval_iso_probs = isotonic.predict_proba(eval_raw_probs)

    # Compute metrics for all 3 versions on evaluation partition
    metrics_raw = evaluate_calibration(eval_matrix.targets, eval_raw_probs)
    metrics_platt = evaluate_calibration(eval_matrix.targets, eval_platt_probs)
    metrics_iso = evaluate_calibration(eval_matrix.targets, eval_iso_probs)

    # Operational review capacities on calibrated probabilities (Platt)
    capacity_points = evaluate_operational_capacities(
        eval_matrix.targets, eval_platt_probs, eval_matrix.policy_ids, seed=base_seed,
    )

    # Decision Curve Analysis
    decision_curves = evaluate_decision_curves(eval_matrix.targets, eval_platt_probs)

    # Risk Tiers
    risk_tiers = evaluate_risk_tiers(eval_matrix.targets, eval_platt_probs)

    return {
        "calibrators": {
            "platt": platt.to_dict(),
            "isotonic": isotonic.to_dict(),
        },
        "evaluation_partition": {
            "records": len(eval_matrix.targets),
            "positive": sum(eval_matrix.targets),
            "negative": len(eval_matrix.targets) - sum(eval_matrix.targets),
            "prevalence": round(sum(eval_matrix.targets) / len(eval_matrix.targets), PORTABLE_ARTIFACT_DECIMALS),
            "unique_policies": len(set(eval_matrix.policy_ids)),
            "matrix_sha256": matrix_digest(eval_matrix),
        },
        "calibration_partition": {
            "records": len(cal_matrix.targets),
            "positive": sum(cal_matrix.targets),
            "negative": len(cal_matrix.targets) - sum(cal_matrix.targets),
            "prevalence": round(sum(cal_matrix.targets) / len(cal_matrix.targets), PORTABLE_ARTIFACT_DECIMALS),
            "unique_policies": len(set(cal_matrix.policy_ids)),
            "matrix_sha256": cal_digest,
        },
        "metrics": {
            "raw": metrics_raw.to_dict(),
            "platt": metrics_platt.to_dict(),
            "isotonic": metrics_iso.to_dict(),
        },
        "operational_capacities": [point.to_dict() for point in capacity_points],
        "decision_curves": list(decision_curves),
        "risk_tiers": [tier.to_dict() for tier in risk_tiers],
    }


__all__ = [
    "DEFAULT_BOOTSTRAP_REPLICATES", "DEFAULT_CAPACITIES", "DEFAULT_COST_RATIOS",
    "DEFAULT_N_BINS", "IsotonicCalibrator", "PlattCalibrator", "CalibrationMetrics",
    "OperationalPoint", "RiskTier", "V6_CALIBRATION_ARTIFACT_VERSION",
    "V6_CALIBRATION_CONTRACT_VERSION", "evaluate_calibration",
    "evaluate_decision_curves", "evaluate_operational_capacities", "evaluate_risk_tiers",
    "fit_isotonic_calibrator", "fit_platt_calibrator", "run_calibration_experiment",
]

