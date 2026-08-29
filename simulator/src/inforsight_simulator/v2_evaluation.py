"""Governed R2-06 temporal evaluation, preprocessing, and baseline comparison."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import random
from typing import Any, Iterable
import warnings

from sklearn import __version__ as sklearn_version
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.feature_selection import mutual_info_classif
from sklearn.tree import DecisionTreeClassifier
import xgboost as xgb
from xgboost import XGBClassifier

from .v2_corpus import V2Features, V2Observation, validate_v2_feature_payload


V2_SPLIT_VERSION = "2.0.0"
V2_FEATURE_DICTIONARY_VERSION = "2.0.0"
V2_FEATURE_PIPELINE_VERSION = "2.0.0"
V2_SCORING_AUTHORIZATION_VERSION = "2.0.0"
V2_DIAGNOSTIC_VERSION = "2.0.0"
V2_BASELINE_VERSION = "2.0.0"
UNKNOWN_CATEGORY = "__unknown__"
RANDOM_SEED = 20260817
FINAL_HOLDOUT_STATUS = "not_materialized"
PORTABLE_ARTIFACT_DECIMALS = 4

NUMERIC_FEATURES = (
    "tenure_days", "premium_amount_cents", "due_to_paid_delay_days",
    "rolling_on_time_payment_rate", "recent_failed_payment_count", "recent_retry_count",
    "recent_recovery_count", "arrears_duration_days", "recent_notice_count",
    "recent_service_contact_count", "visible_grace_entries", "visible_grace_recoveries",
    "payment_attribute_missing", "contact_attribute_missing",
)
CATEGORICAL_FEATURES = (
    "product_type", "billing_frequency", "notice_category", "contact_category",
)

FOLDS = (
    ("fold_1", "2023-03-31T23:59:59Z", "2023-07-01T00:00:00Z", "2023-09-30T23:59:59Z"),
    ("fold_2", "2023-09-30T23:59:59Z", "2024-01-01T00:00:00Z", "2024-03-31T23:59:59Z"),
    ("fold_3", "2024-03-31T23:59:59Z", "2024-07-01T00:00:00Z", "2024-09-30T23:59:59Z"),
)


@dataclass(frozen=True)
class V2TemporalFold:
    name: str
    fit: tuple[V2Observation, ...]
    acceptance: tuple[V2Observation, ...]
    fit_through: str
    acceptance_start: str
    acceptance_end: str


@dataclass(frozen=True)
class NumericState:
    name: str
    mean: float
    scale: float


@dataclass(frozen=True)
class CategoryState:
    name: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class V2Preprocessor:
    fold: str
    fit_ids: tuple[str, ...]
    numeric: tuple[NumericState, ...]
    categorical: tuple[CategoryState, ...]
    feature_names: tuple[str, ...]


@dataclass(frozen=True)
class V2Matrix:
    purpose: str
    fold: str
    role: str
    observation_ids: tuple[str, ...]
    policy_ids: tuple[str, ...]
    episode_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    targets: tuple[int, ...]


@dataclass(frozen=True)
class V2ScoringAuthorization:
    version: str
    purpose: str
    fold: str
    role: str
    observation_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    matrix_sha256: str
    training_matrix_sha256: str
    preprocessor_sha256: str
    authorization_sha256: str


def build_temporal_folds(observations: Iterable[V2Observation]) -> tuple[V2TemporalFold, ...]:
    rows = tuple(observations)
    if not rows:
        raise ValueError("v2 observations are empty")
    folds = []
    for name, fit_end, accept_start, accept_end in FOLDS:
        fit = _eligible(rows, role="fit", start=None, end=fit_end)
        acceptance = _eligible(rows, role="r2_acceptance", start=accept_start, end=accept_end)
        fold = V2TemporalFold(name, fit, acceptance, fit_end, accept_start, accept_end)
        validate_temporal_fold(fold)
        folds.append(fold)
    return tuple(folds)


def build_selection_fold(observations: Iterable[V2Observation]) -> V2TemporalFold:
    rows = tuple(observations)
    fold = V2TemporalFold(
        "selection",
        _eligible(rows, role="fit", start=None, end="2024-03-31T23:59:59Z"),
        _eligible(rows, role="selection", start="2024-07-01T00:00:00Z", end="2024-09-30T23:59:59Z"),
        "2024-03-31T23:59:59Z", "2024-07-01T00:00:00Z", "2024-09-30T23:59:59Z",
    )
    validate_temporal_fold(fold)
    return fold


def validate_temporal_fold(fold: V2TemporalFold) -> None:
    if not fold.fit or not fold.acceptance:
        raise ValueError(f"{fold.name} has an empty governed membership")
    if any(row.role != "fit" for row in fold.fit):
        raise ValueError("fit membership contains a non-fit policy role")
    expected_role = "selection" if fold.name == "selection" else "r2_acceptance"
    if any(row.role != expected_role for row in fold.acceptance):
        raise ValueError("evaluation membership contains the wrong policy role")
    fit_policies = {row.policy_id for row in fold.fit}
    acceptance_policies = {row.policy_id for row in fold.acceptance}
    if fit_policies & acceptance_policies:
        raise ValueError("policy identity overlaps governed roles")
    if {row.outcome_episode_id for row in fold.fit} & {row.outcome_episode_id for row in fold.acceptance}:
        raise ValueError("outcome episode overlaps governed roles")
    latest_fit = max(_time(row.as_of) for row in fold.fit)
    earliest_acceptance = min(_time(row.as_of) for row in fold.acceptance)
    if latest_fit >= earliest_acceptance:
        raise ValueError("feature cutoff chronology is invalid")
    if max(_time(row.horizon_end) for row in fold.fit) >= earliest_acceptance:
        raise ValueError("fit outcome horizon crosses the evaluation boundary")
    for membership in (fold.fit, fold.acceptance):
        if set(row.label_value for row in membership) != {0, 1}:
            raise ValueError("governed membership lacks both target classes")
        frequencies = {row.features.billing_frequency for row in membership}
        if frequencies != {"monthly", "quarterly", "semiannual", "annual"}:
            raise ValueError("governed membership lacks a supported billing frequency")


def fit_preprocessor(fold: V2TemporalFold) -> V2Preprocessor:
    validate_temporal_fold(fold)
    maps = tuple(_feature_map(row) for row in fold.fit)
    numeric = []
    for name in NUMERIC_FEATURES:
        values = [float(item[name]) for item in maps]
        mean = sum(values) / len(values)
        scale = math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)) or 1.0
        numeric.append(NumericState(name, mean, scale))
    categorical = []
    for name in CATEGORICAL_FEATURES:
        values = tuple(sorted({str(item[name]) for item in maps}))
        if UNKNOWN_CATEGORY in values:
            raise ValueError("reserved unknown category occurs in fit data")
        categorical.append(CategoryState(name, values + (UNKNOWN_CATEGORY,)))
    names = tuple(NUMERIC_FEATURES) + tuple(
        f"{state.name}={category}" for state in categorical for category in state.categories
    )
    return V2Preprocessor(fold.name, tuple(row.observation_id for row in fold.fit), tuple(numeric), tuple(categorical), names)


def transform(fitted: V2Preprocessor, rows: Iterable[V2Observation], *, purpose: str, role: str) -> V2Matrix:
    materialized = tuple(rows)
    if not materialized:
        raise ValueError("cannot transform empty membership")
    if any(row.role != role for row in materialized):
        raise ValueError("matrix role does not match source observations")
    values = []
    for row in materialized:
        item = _feature_map(row)
        output = [(float(item[state.name]) - state.mean) / state.scale for state in fitted.numeric]
        for state in fitted.categorical:
            raw = str(item[state.name])
            selected = raw if raw in state.categories[:-1] else UNKNOWN_CATEGORY
            output.extend(float(category == selected) for category in state.categories)
        values.append(tuple(output))
    return V2Matrix(
        purpose, fitted.fold, role,
        tuple(row.observation_id for row in materialized),
        tuple(row.policy_id for row in materialized),
        tuple(row.outcome_episode_id for row in materialized),
        fitted.feature_names, tuple(values), tuple(int(row.label_value) for row in materialized),
    )


def authorize(train: V2Matrix, matrix: V2Matrix, fitted: V2Preprocessor) -> V2ScoringAuthorization:
    if train.purpose != "fit" or matrix.purpose not in ("fit", "selection", "r2_acceptance"):
        raise ValueError("unsupported v2 scoring purpose")
    if train.fold != matrix.fold or train.fold != fitted.fold:
        raise ValueError("cross-fold scoring is prohibited")
    if train.observation_ids != fitted.fit_ids:
        raise ValueError("training membership does not match fitted preprocessing")
    matrix_sha = matrix_digest(matrix)
    train_sha = matrix_digest(train)
    pre_sha = preprocessor_digest(fitted)
    fields = (V2_SCORING_AUTHORIZATION_VERSION, matrix.purpose, matrix.fold, matrix.role,
              matrix.observation_ids, matrix.feature_names, matrix_sha, train_sha, pre_sha)
    return V2ScoringAuthorization(*fields, _digest(fields))


def validate_authorization(auth: V2ScoringAuthorization, matrix: V2Matrix, train_sha: str) -> None:
    fields = (auth.version, auth.purpose, auth.fold, auth.role, auth.observation_ids,
              auth.feature_names, auth.matrix_sha256, auth.training_matrix_sha256,
              auth.preprocessor_sha256)
    if auth.version != V2_SCORING_AUTHORIZATION_VERSION or auth.authorization_sha256 != _digest(fields):
        raise ValueError("v2 scoring authorization integrity failure")
    if (auth.purpose, auth.fold, auth.role, auth.observation_ids, auth.feature_names) != (
        matrix.purpose, matrix.fold, matrix.role, matrix.observation_ids, matrix.feature_names
    ):
        raise ValueError("v2 scoring authorization metadata mismatch")
    if auth.matrix_sha256 != matrix_digest(matrix) or auth.training_matrix_sha256 != train_sha:
        raise ValueError("v2 scoring authorization content mismatch")


def compare_baselines(train: V2Matrix, selection: V2Matrix, fitted: V2Preprocessor) -> dict[str, Any]:
    train_auth = authorize(train, train, fitted)
    selection_auth = authorize(train, selection, fitted)
    train_sha = matrix_digest(train)
    validate_authorization(train_auth, train, train_sha)
    validate_authorization(selection_auth, selection, train_sha)
    logistic = LogisticRegression(penalty="l2", C=1.0, solver="liblinear", tol=1e-8,
                                  max_iter=1000, fit_intercept=True, class_weight=None,
                                  random_state=RANDOM_SEED)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        logistic.fit(train.values, train.targets)
    boosted = XGBClassifier(objective="binary:logistic", n_estimators=25, learning_rate=0.1,
                            max_depth=2, min_child_weight=2.0, gamma=0.0, subsample=1.0,
                            colsample_bytree=1.0, colsample_bylevel=1.0, colsample_bynode=1.0,
                            reg_alpha=0.0, reg_lambda=1.0, scale_pos_weight=1.0,
                            base_score=0.5, tree_method="exact", n_jobs=1,
                            random_state=RANDOM_SEED, eval_metric="logloss", verbosity=0)
    boosted.fit(train.values, train.targets, verbose=False)
    logistic_prob = tuple(float(v) for v in logistic.predict_proba(selection.values)[:, 1])
    boosted_prob = tuple(float(v) for v in boosted.predict_proba(selection.values)[:, 1])
    logistic_state = {
        "intercept": float(logistic.intercept_[0]),
        "coefficients": [float(v) for v in logistic.coef_[0]],
        "iterations": int(logistic.n_iter_[0]),
        "feature_names": list(train.feature_names),
    }
    logistic_reload = tuple(
        1.0 / (1.0 + math.exp(-(logistic_state["intercept"] + sum(coefficient * value for coefficient, value in zip(logistic_state["coefficients"], row, strict=True)))))
        for row in selection.values
    )
    runtime_model_json = bytes(boosted.get_booster().save_raw(raw_format="json"))
    normalized_model_json = json.dumps(
        _normalize_model_state(json.loads(runtime_model_json)),
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    restored = xgb.Booster()
    restored.load_model(bytearray(normalized_model_json))
    boosted_reload = tuple(float(v) for v in restored.predict(xgb.DMatrix(selection.values, feature_names=list(selection.feature_names))))
    if _prediction_digest(selection.observation_ids, logistic_prob) != _prediction_digest(selection.observation_ids, logistic_reload):
        raise ValueError("logistic explicit state did not reproduce predictions")
    if max(abs(expected - actual) for expected, actual in zip(boosted_prob, boosted_reload, strict=True)) > 10 ** (-PORTABLE_ARTIFACT_DECIMALS):
        raise ValueError("boosted explicit state did not reproduce predictions within the portability boundary")
    return {
        "versions": {"baseline": V2_BASELINE_VERSION, "scikit_learn": sklearn_version,
                     "xgboost": xgb.__version__},
        "specifications": {
            "logistic": {"penalty":"l2","C":1.0,"solver":"liblinear","tol":1e-8,
                         "max_iter":1000,"random_seed":RANDOM_SEED},
            "xgboost": {"n_estimators":25,"learning_rate":0.1,"max_depth":2,
                        "min_child_weight":2.0,"tree_method":"exact","n_jobs":1,
                        "random_seed":RANDOM_SEED,"early_stopping":False},
        },
        "membership_sha256": sha256("\n".join(selection.observation_ids).encode()).hexdigest(),
        "training_matrix_sha256": train_sha,
        "selection_matrix_sha256": matrix_digest(selection),
        "preprocessor_sha256": preprocessor_digest(fitted),
        "authorization_sha256": selection_auth.authorization_sha256,
        "logistic": _model_result(selection, logistic_prob, logistic_state),
        "xgboost": _model_result(selection, boosted_prob, {
            "model_json": normalized_model_json.decode("utf-8"),
            "model_json_sha256": sha256(normalized_model_json).hexdigest(),
            "model_numeric_normalization_decimals": PORTABLE_ARTIFACT_DECIMALS,
            "trained_tree_count": len(boosted.get_booster().get_dump()),
        }),
        "explicit_state_reload_verified": True,
    }


def diagnostics(train: V2Matrix, selection: V2Matrix, fitted: V2Preprocessor) -> dict[str, Any]:
    groups = _feature_groups(fitted.feature_names)
    flags: list[dict[str, Any]] = []
    results = []
    for source, indices in groups.items():
        train_patterns = [tuple(row[index] for index in indices) for row in train.values]
        selection_patterns = [tuple(row[index] for index in indices) for row in selection.values]
        counts = {pattern: train_patterns.count(pattern) for pattern in set(train_patterns)}
        uniqueness = len(counts) / len(train_patterns)
        majority = max(counts.values()) / len(train_patterns)
        discrete = all("=" in fitted.feature_names[index] for index in indices)
        mi_values = mutual_info_classif(
            [[row[index] for index in indices] for row in train.values], train.targets,
            discrete_features=discrete, n_neighbors=3, random_state=RANDOM_SEED,
        )
        tree = DecisionTreeClassifier(max_depth=1, criterion="log_loss", splitter="best",
                                      min_samples_leaf=2, random_state=RANDOM_SEED)
        tree.fit([[row[index] for index in indices] for row in train.values], train.targets)
        probabilities = tuple(float(value) for value in tree.predict_proba(
            [[row[index] for index in indices] for row in selection.values]
        )[:, 1])
        shallow = _metrics(selection.targets, probabilities)
        source_flags = []
        if len(counts) == 1:
            source_flags.append("fit_constant")
        elif majority >= 0.95:
            source_flags.append("fit_near_constant")
        if len(counts) > 1 and uniqueness >= 0.90:
            source_flags.append("high_cardinality")
        if round(max(float(value) for value in mi_values), PORTABLE_ARTIFACT_DECIMALS) >= 0.50:
            source_flags.append("strong_mutual_information")
        if (round(shallow["roc_auc"], PORTABLE_ARTIFACT_DECIMALS) >= 0.90
                or round(shallow["log_loss"], PORTABLE_ARTIFACT_DECIMALS) <= 0.40):
            source_flags.append("strong_shallow_model")
        for kind in source_flags:
            flags.append({"id": f"{kind}:{source}", "kind": kind, "source": source})
        results.append({
            "source": source, "output_width": len(indices),
            "train_unique_patterns": len(counts), "train_uniqueness_ratio": uniqueness,
            "train_majority_fraction": majority,
            "selection_unique_patterns": len(set(selection_patterns)),
            "mutual_information_max": max(float(value) for value in mi_values),
            "shallow_selection_metrics": shallow, "flags": source_flags,
        })
    perturbations = _targeted_perturbations(train, selection, groups, flags)
    dispositions = []
    for flag in flags:
        kind = flag["kind"]
        decision = "allow" if kind in {"fit_constant", "fit_near_constant", "high_cardinality"} else "investigate"
        rationale = (
            "approved point-in-time feature; the screen reflects expected continuous or sparse synthetic support"
            if decision == "allow" else
            "association screen requires R2-07 multi-seed and negative-control evidence before interpretation"
        )
        dispositions.append({"flag": flag["id"], "decision": decision, "rationale": rationale})
    # Missingness indicators are already numeric matrix columns; report their governed rates.
    missingness = {
        name: {
            "fit_rate": next(state.mean for state in fitted.numeric if state.name == name),
            "selection_rate": sum(
                row[fitted.feature_names.index(name)] * next(state.scale for state in fitted.numeric if state.name == name)
                + next(state.mean for state in fitted.numeric if state.name == name)
                for row in selection.values
            ) / len(selection.values),
        }
        for name in ("payment_attribute_missing", "contact_attribute_missing")
    }
    identifier_tokens = ("id", "uuid", "guid", "key", "index", "policy", "observation", "customer", "account", "scenario", "oracle", "frailty")
    identifier_hits = [name for name in groups if any(token == name or name.startswith(f"{token}_") or name.endswith(f"_{token}") for token in identifier_tokens)]
    return {
        "diagnostic_version": V2_DIAGNOSTIC_VERSION,
        "configuration": {
            "mutual_information_threshold": 0.50, "cardinality_ratio_threshold": 0.90,
            "near_constant_threshold": 0.95, "shallow_auc_threshold": 0.90,
            "shallow_log_loss_threshold": 0.40, "perturbation_auc_delta": 0.10,
            "perturbation_log_loss_delta": 0.10, "seed": RANDOM_SEED,
        },
        "identifier_screen": {"status": "passed" if not identifier_hits else "failed", "hits": identifier_hits},
        "missingness_indicator_rates": missingness,
        "source_results": results,
        "flags": flags,
        "selection_unknown_counts": {
            state.name: sum(row[fitted.feature_names.index(f"{state.name}={UNKNOWN_CATEGORY}")] == 1.0 for row in selection.values)
            for state in fitted.categorical
        },
        "targeted_perturbations": perturbations,
        "billing_frequency_support": {
            "fit": sorted(state.categories[:-1] for state in fitted.categorical if state.name == "billing_frequency")[0],
            "selection": ["annual", "monthly", "quarterly", "semiannual"],
        },
        "dispositions": dispositions,
        "decision": "investigate" if any(item["decision"] == "investigate" for item in dispositions) else "allow",
    }


def _targeted_perturbations(train: V2Matrix, selection: V2Matrix,
                            groups: dict[str, tuple[int, ...]], flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = sorted({flag["source"] for flag in flags})
    if not sources:
        return []
    logistic = LogisticRegression(penalty="l2", C=1.0, solver="liblinear", tol=1e-8,
                                  max_iter=1000, random_state=RANDOM_SEED).fit(train.values, train.targets)
    boosted = XGBClassifier(objective="binary:logistic", n_estimators=25, learning_rate=0.1,
                            max_depth=2, min_child_weight=2.0, tree_method="exact", n_jobs=1,
                            random_state=RANDOM_SEED, eval_metric="logloss", verbosity=0).fit(
                                train.values, train.targets, verbose=False)
    base = {
        "logistic": _metrics(selection.targets, tuple(float(v) for v in logistic.predict_proba(selection.values)[:, 1])),
        "xgboost": _metrics(selection.targets, tuple(float(v) for v in boosted.predict_proba(selection.values)[:, 1])),
    }
    output = []
    for offset, source in enumerate(sources):
        order = list(range(len(selection.values)))
        random.Random(RANDOM_SEED + offset).shuffle(order)
        indices = groups[source]
        rows = [list(row) for row in selection.values]
        for target_index, source_index in enumerate(order):
            for index in indices:
                rows[target_index][index] = selection.values[source_index][index]
        scores = {
            "logistic": _metrics(selection.targets, tuple(float(v) for v in logistic.predict_proba(rows)[:, 1])),
            "xgboost": _metrics(selection.targets, tuple(float(v) for v in boosted.predict_proba(rows)[:, 1])),
        }
        output.append({
            "source": source,
            "logistic_auc_delta": scores["logistic"]["roc_auc"] - base["logistic"]["roc_auc"],
            "logistic_log_loss_delta": scores["logistic"]["log_loss"] - base["logistic"]["log_loss"],
            "xgboost_auc_delta": scores["xgboost"]["roc_auc"] - base["xgboost"]["roc_auc"],
            "xgboost_log_loss_delta": scores["xgboost"]["log_loss"] - base["xgboost"]["log_loss"],
        })
    return output


def _feature_groups(feature_names: tuple[str, ...]) -> dict[str, tuple[int, ...]]:
    names = []
    for name in feature_names:
        source = name.split("=", 1)[0]
        if source not in names:
            names.append(source)
    return {source: tuple(index for index, name in enumerate(feature_names) if name.split("=", 1)[0] == source) for source in names}


def _metrics(targets: tuple[int, ...], probabilities: tuple[float, ...]) -> dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(targets, probabilities)),
        "log_loss": float(log_loss(targets, probabilities, labels=[0, 1])),
        "brier_score": float(brier_score_loss(targets, probabilities)),
    }


def matrix_digest(matrix: V2Matrix) -> str:
    return _digest(asdict(matrix))


def preprocessor_digest(fitted: V2Preprocessor) -> str:
    return _digest(asdict(fitted))


def _eligible(rows: tuple[V2Observation, ...], *, role: str, start: str | None, end: str) -> tuple[V2Observation, ...]:
    result = [row for row in rows if row.role == role and row.label_value in (0, 1)
              and (start is None or _time(row.as_of) >= _time(start)) and _time(row.as_of) <= _time(end)]
    return tuple(sorted(result, key=lambda row: (row.as_of, row.policy_id, row.observation_id)))


def _feature_map(row: V2Observation) -> dict[str, Any]:
    validate_v2_feature_payload(row.features)
    result = asdict(row.features)
    result["due_to_paid_delay_days"] = 0.0 if result["due_to_paid_delay_days"] is None else result["due_to_paid_delay_days"]
    return result


def _model_result(matrix: V2Matrix, probabilities: tuple[float, ...], state: dict[str, Any]) -> dict[str, Any]:
    positive = sum(matrix.targets)
    count = len(matrix.targets)
    metrics = {
        "records": count, "negative": count - positive, "positive": positive,
        "log_loss": float(log_loss(matrix.targets, probabilities, labels=[0, 1])),
        "roc_auc": float(roc_auc_score(matrix.targets, probabilities)),
        "brier_score": float(brier_score_loss(matrix.targets, probabilities)),
        "average_predicted_probability": sum(probabilities) / count,
        "observed_positive_fraction": positive / count,
    }
    prediction_sha = _prediction_digest(matrix.observation_ids, probabilities)
    return {"metrics": metrics, "prediction_sha256": prediction_sha, "safe_fitted_state": state,
            "safe_fitted_state_sha256": _digest(state)}


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()


def _prediction_digest(ids: tuple[str, ...], probabilities: tuple[float, ...]) -> str:
    return _digest({"ids": ids, "probabilities": [round(value, PORTABLE_ARTIFACT_DECIMALS) for value in probabilities]})


def _normalize_model_state(value: Any) -> Any:
    """Canonicalize native XGBoost numeric state across supported platforms."""

    if isinstance(value, float):
        rounded = round(value, PORTABLE_ARTIFACT_DECIMALS)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _normalize_model_state(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_model_state(item) for item in value]
    return value


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
