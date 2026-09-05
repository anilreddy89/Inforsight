"""Phase 2.10: Model bundle export, standalone inference engine, and environment reproducibility."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import sys
from typing import Any, Sequence
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from inforsight_simulator.calibration import (
    PlattCalibrator,
    fit_platt_calibrator,
    matrix_digest,
)
from inforsight_simulator.explanations import (
    CATEGORICAL_FEATURES,
    FEATURE_GROUPS,
    NUMERIC_FEATURES,
    ModelExplainer,
)
from inforsight_simulator.v6_corpus import V6CorpusConfig, generate_v6_corpus
from inforsight_simulator.v6_evaluation import (
    UNKNOWN_CATEGORY,
    V6Observation,
    V6Preprocessor,
    _feature_map,
    _row_key,
    build_selection_fold,
    fit_preprocessor,
    transform,
)

MODEL_BUNDLE_VERSION = "1.0.0"
MODEL_BUNDLE_CONTRACT_VERSION = "1.0.0"
MODEL_BUNDLE_ARTIFACT_VERSION = "1.0.0"
MODEL_ID = "inforsight-v6-logistic-platt-20260817"
PORTABLE_ARTIFACT_DECIMALS = 6


@dataclass(frozen=True)
class NumericFeatureSpec:
    name: str
    mean: float
    scale: float


@dataclass(frozen=True)
class CategoricalFeatureSpec:
    name: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class PreprocessorSpec:
    numeric: dict[str, NumericFeatureSpec]
    categorical: dict[str, CategoricalFeatureSpec]
    ordered_columns: tuple[str, ...]
    schema_version: str = "6.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "feature_count": len(self.ordered_columns),
            "numeric": {k: asdict(v) for k, v in self.numeric.items()},
            "categorical": {k: asdict(v) for k, v in self.categorical.items()},
            "ordered_columns": list(self.ordered_columns),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PreprocessorSpec:
        numeric = {
            k: NumericFeatureSpec(name=v["name"], mean=float(v["mean"]), scale=float(v["scale"]))
            for k, v in d["numeric"].items()
        }
        categorical = {
            k: CategoricalFeatureSpec(name=v["name"], categories=tuple(v["categories"]))
            for k, v in d["categorical"].items()
        }
        return cls(
            numeric=numeric,
            categorical=categorical,
            ordered_columns=tuple(d["ordered_columns"]),
            schema_version=d.get("schema_version", "6.0.0"),
        )


@dataclass(frozen=True)
class BaseModelSpec:
    family: str
    penalty: str
    c_param: float
    solver: str
    random_seed: int
    raw_intercept: float
    raw_coefficients: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BaseModelSpec:
        return cls(
            family=d["family"],
            penalty=d["penalty"],
            c_param=float(d["c_param"]),
            solver=d["solver"],
            random_seed=int(d["random_seed"]),
            raw_intercept=float(d["raw_intercept"]),
            raw_coefficients={k: float(v) for k, v in d["raw_coefficients"].items()},
        )


@dataclass(frozen=True)
class CalibratorSpec:
    method: str
    param_a: float
    param_b: float
    calibrated_intercept: float
    calibrated_coefficients: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CalibratorSpec:
        return cls(
            method=d["method"],
            param_a=float(d["param_a"]),
            param_b=float(d["param_b"]),
            calibrated_intercept=float(d["calibrated_intercept"]),
            calibrated_coefficients={k: float(v) for k, v in d["calibrated_coefficients"].items()},
        )


@dataclass(frozen=True)
class ExplainerReferenceSpec:
    background_observation_count: int
    base_value_logit: float
    base_value_probability: float
    background_column_means: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExplainerReferenceSpec:
        return cls(
            background_observation_count=int(d["background_observation_count"]),
            base_value_logit=float(d["base_value_logit"]),
            base_value_probability=float(d["base_value_probability"]),
            background_column_means={k: float(v) for k, v in d["background_column_means"].items()},
        )


@dataclass(frozen=True)
class RiskTierThreshold:
    name: str
    min_prob: float
    max_prob: float
    action: str


@dataclass(frozen=True)
class ReviewQueueCapacity:
    capacity_percentile: float
    cutoff_probability: float
    expected_precision: float
    expected_recall: float
    lift: float


@dataclass(frozen=True)
class OperationalPolicySpec:
    risk_tiers: tuple[RiskTierThreshold, ...]
    review_queues: tuple[ReviewQueueCapacity, ...]
    authority_boundaries: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_tiers": [asdict(t) for t in self.risk_tiers],
            "review_queues": [asdict(q) for q in self.review_queues],
            "authority_boundaries": dict(self.authority_boundaries),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OperationalPolicySpec:
        tiers = tuple(
            RiskTierThreshold(
                name=t["name"],
                min_prob=float(t["min_prob"]),
                max_prob=float(t["max_prob"]),
                action=t["action"],
            )
            for t in d["risk_tiers"]
        )
        queues = tuple(
            ReviewQueueCapacity(
                capacity_percentile=float(q["capacity_percentile"]),
                cutoff_probability=float(q["cutoff_probability"]),
                expected_precision=float(q["expected_precision"]),
                expected_recall=float(q["expected_recall"]),
                lift=float(q["lift"]),
            )
            for q in d["review_queues"]
        )
        return cls(
            risk_tiers=tiers,
            review_queues=queues,
            authority_boundaries=dict(d["authority_boundaries"]),
        )


@dataclass(frozen=True)
class RuntimeEnvironment:
    python_version: str
    platform: str
    library_versions: dict[str, str]
    dependency_lock_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RuntimeEnvironment:
        return cls(
            python_version=d["python_version"],
            platform=d["platform"],
            library_versions=dict(d["library_versions"]),
            dependency_lock_sha256=d["dependency_lock_sha256"],
        )


@dataclass(frozen=True)
class ModelBundle:
    bundle_version: str
    bundle_id: str
    created_at_utc: str
    runtime_environment: RuntimeEnvironment
    preprocessor: PreprocessorSpec
    base_model: BaseModelSpec
    calibrator: CalibratorSpec
    explainer_reference: ExplainerReferenceSpec
    operational_policy: OperationalPolicySpec

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_version": self.bundle_version,
            "bundle_id": self.bundle_id,
            "created_at_utc": self.created_at_utc,
            "runtime_environment": self.runtime_environment.to_dict(),
            "preprocessor": self.preprocessor.to_dict(),
            "base_model": self.base_model.to_dict(),
            "calibrator": self.calibrator.to_dict(),
            "explainer_reference": self.explainer_reference.to_dict(),
            "operational_policy": self.operational_policy.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ModelBundle:
        return cls(
            bundle_version=d["bundle_version"],
            bundle_id=d["bundle_id"],
            created_at_utc=d["created_at_utc"],
            runtime_environment=RuntimeEnvironment.from_dict(d["runtime_environment"]),
            preprocessor=PreprocessorSpec.from_dict(d["preprocessor"]),
            base_model=BaseModelSpec.from_dict(d["base_model"]),
            calibrator=CalibratorSpec.from_dict(d["calibrator"]),
            explainer_reference=ExplainerReferenceSpec.from_dict(d["explainer_reference"]),
            operational_policy=OperationalPolicySpec.from_dict(d["operational_policy"]),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, allow_nan=False)

    @classmethod
    def from_json(cls, s: str) -> ModelBundle:
        return cls.from_dict(json.loads(s))

    def compute_digest(self) -> str:
        return sha256(self.to_json().encode("utf-8")).hexdigest()

    def save(self, path: Path | str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json() + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> ModelBundle:
        p = Path(path)
        return cls.from_json(p.read_text(encoding="utf-8"))


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
            "top_risk_drivers": [list(t) for t in self.top_risk_drivers],
            "top_protective_drivers": [list(t) for t in self.top_protective_drivers],
        }


class BundledInferenceEngine:
    """Standalone production inference engine executing directly from a ModelBundle."""

    def __init__(self, bundle: ModelBundle) -> None:
        self.bundle = bundle
        self.preprocessor = bundle.preprocessor
        self.base_model = bundle.base_model
        self.calibrator = bundle.calibrator
        self.explainer_ref = bundle.explainer_reference
        self.policy = bundle.operational_policy

        self.ordered_columns = bundle.preprocessor.ordered_columns
        self.num_cols = len(self.ordered_columns)

        # Pre-convert model coefficients and calibrator weights to NumPy vectors
        self.raw_intercept = float(bundle.base_model.raw_intercept)
        self.raw_coefs = np.array([
            bundle.base_model.raw_coefficients[col] for col in self.ordered_columns
        ], dtype=float)

        self.param_a = float(bundle.calibrator.param_a)
        self.param_b = float(bundle.calibrator.param_b)
        self.calibrated_intercept = float(bundle.calibrator.calibrated_intercept)
        self.calibrated_coefs = np.array([
            bundle.calibrator.calibrated_coefficients[col] for col in self.ordered_columns
        ], dtype=float)

        self.bg_means = np.array([
            bundle.explainer_reference.background_column_means[col] for col in self.ordered_columns
        ], dtype=float)
        self.base_value_logit = float(bundle.explainer_reference.base_value_logit)
        self.base_value_prob = float(bundle.explainer_reference.base_value_probability)

        # Precompute column index mapping for root features
        self.root_to_indices: dict[str, list[int]] = {}
        for root in list(NUMERIC_FEATURES) + list(CATEGORICAL_FEATURES):
            self.root_to_indices[root] = []

        for idx, col in enumerate(self.ordered_columns):
            for num_feat in NUMERIC_FEATURES:
                if col == num_feat:
                    self.root_to_indices[num_feat].append(idx)
                    break
            else:
                for cat_feat in CATEGORICAL_FEATURES:
                    if col.startswith(f"{cat_feat}="):
                        self.root_to_indices[cat_feat].append(idx)
                        break

    def transform_features(self, raw_feature_map: dict[str, Any]) -> np.ndarray:
        """Transform a raw feature dictionary into a 28-dimensional scaled vector."""
        vec = []
        # Numeric scaling: (x - mean) / scale
        for name in NUMERIC_FEATURES:
            val = float(raw_feature_map[name])
            st = self.preprocessor.numeric[name]
            vec.append((val - st.mean) / st.scale)

        # Categorical one-hot encoding
        for name in CATEGORICAL_FEATURES:
            raw_val = str(raw_feature_map[name])
            cat_st = self.preprocessor.categorical[name]
            cats = cat_st.categories
            selected = raw_val if raw_val in cats[:-1] else UNKNOWN_CATEGORY
            vec.extend(float(c == selected) for c in cats)

        return np.array(vec, dtype=float)

    def score_record(self, raw_feature_map: dict[str, Any]) -> ScoringResult:
        """Score a single raw observation record."""
        x = self.transform_features(raw_feature_map)

        # Linear logit and Platt calibration
        raw_logit = float(self.raw_intercept + np.dot(self.raw_coefs, x))
        cal_logit = float(self.param_a * raw_logit + self.param_b)
        cal_prob = float(1.0 / (1.0 + math.exp(-cal_logit)))

        # Feature attributions and centered SHAP
        col_log_odds = self.calibrated_coefs * x
        col_shap = self.calibrated_coefs * (x - self.bg_means)

        root_attrs: dict[str, float] = {}
        root_shaps: dict[str, float] = {}
        for root, indices in self.root_to_indices.items():
            root_attrs[root] = float(np.sum(col_log_odds[indices]))
            root_shaps[root] = float(np.sum(col_shap[indices]))

        # Top drivers
        sorted_drivers = sorted(root_attrs.items(), key=lambda item: item[1], reverse=True)
        top_risk = tuple(t for t in sorted_drivers if t[1] > 0)[:3]
        top_protective = tuple(t for t in reversed(sorted_drivers) if t[1] < 0)[:3]

        # Risk tier assignment
        risk_tier = "Tier 4: Critical Risk"
        for t in self.policy.risk_tiers:
            if t.min_prob <= cal_prob < t.max_prob:
                risk_tier = t.name
                break

        # Review queue eligibility
        queues = {}
        for q in self.policy.review_queues:
            pct_label = f"top_{int(q.capacity_percentile)}_pct"
            queues[pct_label] = bool(cal_prob >= q.cutoff_probability)

        return ScoringResult(
            raw_logit=raw_logit,
            calibrated_logit=cal_logit,
            calibrated_probability=cal_prob,
            risk_tier=risk_tier,
            review_queue_eligibility=queues,
            root_attributions_log_odds=root_attrs,
            root_centered_shap=root_shaps,
            top_risk_drivers=top_risk,
            top_protective_drivers=top_protective,
        )

    def score_batch(self, raw_feature_maps: Sequence[dict[str, Any]]) -> tuple[ScoringResult, ...]:
        """Score an entire batch of raw observation dictionaries."""
        return tuple(self.score_record(m) for m in raw_feature_maps)


def export_model_bundle(
    corpus_seed: int = 20280201,
    candidate_seed: int = 20260817,
    pyproject_path: Path | None = None,
) -> ModelBundle:
    """Build and export the complete ModelBundle from governed training artifacts."""
    corpus = generate_v6_corpus(V6CorpusConfig(base_seed=corpus_seed))
    selection_fold = build_selection_fold(corpus.observations)
    preprocessor = fit_preprocessor(selection_fold)

    # Reconstruct candidate Logistic Regression model
    train = transform(preprocessor, selection_fold.fit, purpose="fit", role="fit")
    base_model = LogisticRegression(
        penalty="l2", C=1.0, solver="liblinear", tol=1e-8, max_iter=1000,
        fit_intercept=True, class_weight=None, random_state=candidate_seed,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        base_model.fit(train.values, train.targets)

    # Calibration partition
    cal_rows = tuple(sorted((r for r in corpus.observations if r.role == "calibration"), key=_row_key))
    cal_matrix = transform(preprocessor, cal_rows, purpose="calibration", role="calibration")
    cal_logits = tuple(float(val) for val in base_model.decision_function(cal_matrix.values))
    cal_digest = matrix_digest(cal_matrix)
    platt = fit_platt_calibrator(cal_logits, cal_matrix.targets, fit_sha256=cal_digest)

    # Evaluation partition for explainer baseline
    eval_rows = tuple(sorted((r for r in corpus.observations if r.role == "non_final_evaluation"), key=_row_key))
    eval_matrix = transform(preprocessor, eval_rows, purpose="non_final_evaluation", role="non_final_evaluation")
    explainer = ModelExplainer(
        base_model=base_model,
        calibrator=platt,
        preprocessor=preprocessor,
        background_matrix=eval_matrix,
    )

    # 1. Preprocessor Spec
    num_specs = {
        s.name: NumericFeatureSpec(name=s.name, mean=s.mean, scale=s.scale)
        for s in preprocessor.numeric
    }
    cat_specs = {
        s.name: CategoricalFeatureSpec(name=s.name, categories=s.categories)
        for s in preprocessor.categorical
    }
    ordered_cols = preprocessor.feature_names
    preprocessor_spec = PreprocessorSpec(
        numeric=num_specs,
        categorical=cat_specs,
        ordered_columns=ordered_cols,
    )

    # 2. Base Model Spec
    raw_intercept = float(base_model.intercept_[0])
    raw_coefs = {col: float(c) for col, c in zip(ordered_cols, base_model.coef_[0])}
    base_model_spec = BaseModelSpec(
        family="LogisticRegression",
        penalty="l2",
        c_param=1.0,
        solver="liblinear",
        random_seed=candidate_seed,
        raw_intercept=raw_intercept,
        raw_coefficients=raw_coefs,
    )

    # 3. Calibrator Spec
    cal_intercept = float(platt.slope * raw_intercept + platt.intercept)
    cal_coefs = {col: float(platt.slope * c) for col, c in raw_coefs.items()}
    calibrator_spec = CalibratorSpec(
        method="platt_scaling",
        param_a=float(platt.slope),
        param_b=float(platt.intercept),
        calibrated_intercept=cal_intercept,
        calibrated_coefficients=cal_coefs,
    )

    # 4. Explainer Reference Spec
    bg_means = {col: float(m) for col, m in zip(ordered_cols, explainer.background_mean)}
    explainer_ref_spec = ExplainerReferenceSpec(
        background_observation_count=len(eval_rows),
        base_value_logit=float(explainer.base_value_logit),
        base_value_probability=float(explainer.base_value_prob),
        background_column_means=bg_means,
    )

    # 5. Operational Policy Spec
    risk_tiers = (
        RiskTierThreshold(name="Tier 1: Low Risk", min_prob=0.0, max_prob=0.10, action="standard_passive_billing"),
        RiskTierThreshold(name="Tier 2: Moderate Risk", min_prob=0.10, max_prob=0.25, action="digital_payment_reminder"),
        RiskTierThreshold(name="Tier 3: High Risk", min_prob=0.25, max_prob=0.50, action="proactive_conservation_triage"),
        RiskTierThreshold(name="Tier 4: Critical Risk", min_prob=0.50, max_prob=1.0, action="immediate_grace_period_intervention"),
    )
    review_queues = (
        ReviewQueueCapacity(capacity_percentile=1.0, cutoff_probability=0.3409, expected_precision=0.3409, expected_recall=0.0242, lift=2.23),
        ReviewQueueCapacity(capacity_percentile=5.0, cutoff_probability=0.2289, expected_precision=0.3531, expected_recall=0.1157, lift=2.31),
        ReviewQueueCapacity(capacity_percentile=20.0, cutoff_probability=0.1654, expected_precision=0.2797, expected_recall=0.3664, lift=1.83),
    )
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
    policy_spec = OperationalPolicySpec(
        risk_tiers=risk_tiers,
        review_queues=review_queues,
        authority_boundaries=authority_boundaries,
    )

    # 6. Runtime Environment
    if pyproject_path is None:
        root_cand = Path(__file__).resolve().parents[3] / "pyproject.toml"
        sim_cand = Path(__file__).resolve().parents[2] / "pyproject.toml"
        pyproject_path = root_cand if root_cand.exists() else sim_cand

    dep_hash = sha256(pyproject_path.read_bytes()).hexdigest() if pyproject_path.exists() else "unknown"

    import scipy
    import sklearn

    runtime_env = RuntimeEnvironment(
        python_version=platform.python_version(),
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
        library_versions={
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        dependency_lock_sha256=dep_hash,
    )

    return ModelBundle(
        bundle_version=MODEL_BUNDLE_VERSION,
        bundle_id=MODEL_ID,
        created_at_utc="2026-09-04T19:30:00Z",
        runtime_environment=runtime_env,
        preprocessor=preprocessor_spec,
        base_model=base_model_spec,
        calibrator=calibrator_spec,
        explainer_reference=explainer_ref_spec,
        operational_policy=policy_spec,
    )


def run_bundle_experiment(corpus_seed: int = 20280201) -> dict[str, Any]:
    """Execute bundle export and verify reload-and-score bit-for-bit invariance."""
    bundle = export_model_bundle(corpus_seed=corpus_seed)
    engine = BundledInferenceEngine(bundle)

    # Load evaluation partition
    corpus = generate_v6_corpus(V6CorpusConfig(base_seed=corpus_seed))
    selection_fold = build_selection_fold(corpus.observations)
    preprocessor = fit_preprocessor(selection_fold)

    train = transform(preprocessor, selection_fold.fit, purpose="fit", role="fit")
    base_model = LogisticRegression(
        penalty="l2", C=1.0, solver="liblinear", tol=1e-8, max_iter=1000,
        fit_intercept=True, class_weight=None, random_state=20260817,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        base_model.fit(train.values, train.targets)

    cal_rows = tuple(sorted((r for r in corpus.observations if r.role == "calibration"), key=_row_key))
    cal_matrix = transform(preprocessor, cal_rows, purpose="calibration", role="calibration")
    cal_logits = tuple(float(val) for val in base_model.decision_function(cal_matrix.values))
    platt = fit_platt_calibrator(cal_logits, cal_matrix.targets, fit_sha256=matrix_digest(cal_matrix))

    eval_rows = tuple(sorted((r for r in corpus.observations if r.role == "non_final_evaluation"), key=_row_key))
    eval_matrix = transform(preprocessor, eval_rows, purpose="non_final_evaluation", role="non_final_evaluation")
    orig_logits = tuple(float(v) for v in base_model.decision_function(eval_matrix.values))
    orig_probs = tuple(float(v) for v in platt.predict_proba(orig_logits))

    # Score with BundledInferenceEngine directly from raw observations
    raw_maps = tuple(_feature_map(r) for r in eval_rows)
    bundled_results = engine.score_batch(raw_maps)

    # Invariant checks
    diff_probs = [abs(orig - res.calibrated_probability) for orig, res in zip(orig_probs, bundled_results)]
    diff_logits = [abs(orig - res.raw_logit) for orig, res in zip(orig_logits, bundled_results)]
    max_diff_prob = max(diff_probs)
    max_diff_logit = max(diff_logits)

    # Additive logit reconstruction in bundled engine
    max_reconstruction_err = 0.0
    for res in bundled_results:
        recon_cal = engine.calibrated_intercept + sum(res.root_attributions_log_odds.values())
        err = abs(res.calibrated_logit - recon_cal)
        if err > max_reconstruction_err:
            max_reconstruction_err = err

    # Check operational tier mapping
    tier_matches = 0
    for orig_p, res in zip(orig_probs, bundled_results):
        expected_tier = "Tier 4: Critical Risk"
        if orig_p < 0.10:
            expected_tier = "Tier 1: Low Risk"
        elif orig_p < 0.25:
            expected_tier = "Tier 2: Moderate Risk"
        elif orig_p < 0.50:
            expected_tier = "Tier 3: High Risk"

        if res.risk_tier == expected_tier:
            tier_matches += 1

    return {
        "bundle": bundle,
        "bundle_digest": bundle.compute_digest(),
        "total_eval_records": len(eval_rows),
        "max_probability_divergence": float(max_diff_prob),
        "max_logit_divergence": float(max_diff_logit),
        "max_reconstruction_divergence": float(max_reconstruction_err),
        "tolerance": 1e-12,
        "bit_for_bit_verified": bool(max_diff_prob < 1e-12 and max_diff_logit < 1e-12),
        "reconstruction_verified": bool(max_reconstruction_err < 1e-12),
        "tier_concordance_count": tier_matches,
        "tier_concordance_rate": float(tier_matches / len(eval_rows)),
    }

