"""Governed R2-15 Generation v6 evaluation memberships, feature pipeline, and candidate selection."""

from __future__ import annotations

from collections import Counter
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
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.tree import DecisionTreeClassifier
import xgboost as xgb
from xgboost import XGBClassifier

from .v3_config import V3_BILLING_FREQUENCIES
from .v3_corpus import validate_v3_feature_payload
from .v6_config import (
    V6_ACCEPTANCE_PROTOCOL_VERSION, V6_COEFFICIENT_REGISTRY_VERSION,
    V6_SIMULATOR_CONTRACT_VERSION,
)
from .v6_corpus import V6Features, V6Observation, V6_OBSERVATION_SCHEMA_VERSION


V6_EVALUATION_CONTRACT_VERSION = "6.0.0"
V6_SPLIT_VERSION = "6.0.0"
V6_CANDIDATE_SELECTION_MEMBERSHIP_VERSION = "6.0.0"
V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION = V6_ACCEPTANCE_PROTOCOL_VERSION
V6_FEATURE_DICTIONARY_VERSION = "6.0.0"
V6_FEATURE_PIPELINE_VERSION = "6.0.0"
V6_SCORING_AUTHORIZATION_VERSION = "6.0.0"
V6_DIAGNOSTIC_VERSION = "6.0.0"
V6_CANDIDATE_VERSION = "6.0.0"
V6_FINAL_HOLDOUT_STATUS = "not_materialized"
V6_STRUCTURAL_SUPPORT_VERSION = "6.0.0"

UNKNOWN_CATEGORY = "__unknown__"
RANDOM_SEED = 20260817
PORTABLE_ARTIFACT_DECIMALS = 4
MATRIX_DIGEST_DECIMALS = 12

MIN_ELIGIBLE_OBSERVATIONS = 500
MIN_CLASS_OBSERVATIONS = 50

FOLDS = (
    ("fold_1", "2023-03-31T23:59:59Z", "2023-07-01T00:00:00Z", "2023-09-30T23:59:59Z"),
    ("fold_2", "2023-09-30T23:59:59Z", "2024-01-01T00:00:00Z", "2024-03-31T23:59:59Z"),
    ("fold_3", "2024-03-31T23:59:59Z", "2024-07-01T00:00:00Z", "2024-09-30T23:59:59Z"),
)
SELECTION_FOLD = (
    "selection", "2024-03-31T23:59:59Z", "2024-07-01T00:00:00Z", "2024-12-31T23:59:59Z",
)

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

FEATURE_GROUPS = {
    "static": ("tenure_days", "premium_amount_cents", "product_type", "billing_frequency"),
    "recent_payment": (
        "recent_delay_days", "recent_failed_payment_count", "recent_retry_count",
        "recent_recovery_count", "arrears_duration_days",
    ),
    "rolling_history": ("rolling_on_time_rate", "rolling_payment_count"),
    "service_notice": (
        "recent_notice_count", "notice_category", "recent_contact_count", "contact_category",
    ),
    "missingness": ("payment_attribute_missing", "contact_attribute_missing"),
}


@dataclass(frozen=True)
class V6TemporalFold:
    name: str
    fit: tuple[V6Observation, ...]
    evaluation: tuple[V6Observation, ...]
    fit_through: str
    evaluation_start: str
    evaluation_end: str


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
class V6Preprocessor:
    pipeline_version: str
    fold: str
    artifact_id: str
    fit_ids: tuple[str, ...]
    numeric: tuple[NumericState, ...]
    categorical: tuple[CategoryState, ...]
    feature_names: tuple[str, ...]


@dataclass(frozen=True)
class V6Matrix:
    purpose: str
    fold: str
    role: str
    artifact_id: str
    observation_ids: tuple[str, ...]
    policy_ids: tuple[str, ...]
    outcome_episode_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    targets: tuple[int, ...]


@dataclass(frozen=True)
class V6ScoringAuthorization:
    version: str
    split_version: str
    protocol_version: str
    purpose: str
    fold: str
    role: str
    artifact_id: str
    observation_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    matrix_sha256: str
    target_sha256: str
    fit_matrix_sha256: str
    preprocessor_sha256: str
    model_sha256: str
    authorization_sha256: str


def validate_feature_registry() -> None:
    registered = [name for names in FEATURE_GROUPS.values() for name in names]
    expected = set(V6Features.__dataclass_fields__)
    if len(registered) != len(set(registered)):
        raise ValueError("v6 feature registry assigns a feature more than once")
    if set(registered) != expected:
        missing = sorted(expected - set(registered))
        extra = sorted(set(registered) - expected)
        raise ValueError(f"v6 feature registry mismatch; missing={missing}, extra={extra}")


def structural_support_report(observations: Iterable[V6Observation]) -> dict[str, object]:
    """Summarize frozen memberships without fitting, transforming, or scoring."""

    rows = _normalized(observations)
    if not rows:
        raise ValueError("v6 observations are empty")
    artifact_ids = {row.artifact_id for row in rows}
    if len(artifact_ids) != 1:
        raise ValueError("v6 structural evidence requires one artifact identity")
    validate_feature_registry()
    memberships = []
    for specification, evaluation_role in (
        *((specification, "acceptance") for specification in FOLDS),
        (SELECTION_FOLD, "selection"),
    ):
        name, fit_end, evaluation_start, evaluation_end = specification
        fit_window = _window(rows, "fit", None, fit_end)
        evaluation_window = _window(rows, evaluation_role, evaluation_start, evaluation_end)
        fit = _observed(fit_window)
        evaluation = _observed(evaluation_window)
        support_failures = [
            *_support_failures(fit, "fit"),
            *_support_failures(evaluation, evaluation_role),
        ]
        latest_fit_cutoff = max(_time(row.as_of) for row in fit)
        latest_fit_horizon = max(_time(row.horizon_end) for row in fit)
        earliest_evaluation = min(_time(row.as_of) for row in evaluation)
        chronology_passed = latest_fit_cutoff < earliest_evaluation
        embargo_passed = latest_fit_horizon < earliest_evaluation
        policy_overlap = len({row.policy_id for row in fit} & {row.policy_id for row in evaluation})
        episode_overlap = len(
            {row.outcome_episode_id for row in fit}
            & {row.outcome_episode_id for row in evaluation}
        )
        if not chronology_passed:
            support_failures.append("feature cutoff chronology is invalid")
        if not embargo_passed:
            support_failures.append("fit outcome horizon crosses the evaluation boundary")
        if policy_overlap:
            support_failures.append("policy identity overlaps governed roles")
        if episode_overlap:
            support_failures.append("outcome episode overlaps governed roles")
        memberships.append({
            "name": name,
            "fit_through": fit_end,
            "evaluation_role": evaluation_role,
            "evaluation_start": evaluation_start,
            "evaluation_end": evaluation_end,
            "fit": _membership_summary(fit_window, fit),
            "evaluation": _membership_summary(evaluation_window, evaluation),
            "boundaries": {
                "latest_fit_cutoff": _timestamp(latest_fit_cutoff),
                "latest_fit_horizon": _timestamp(latest_fit_horizon),
                "earliest_evaluation_cutoff": _timestamp(earliest_evaluation),
                "strict_cutoff_chronology": chronology_passed,
                "full_90_day_embargo": embargo_passed,
                "policy_overlap": policy_overlap,
                "outcome_episode_overlap": episode_overlap,
            },
            "support_status": "pass" if not support_failures else "fail",
            "support_failures": support_failures,
        })
    return {
        "artifact_version": V6_STRUCTURAL_SUPPORT_VERSION,
        "split_contract_version": V6_SPLIT_VERSION,
        "phase": "R2-15",
        "artifact_id": next(iter(artifact_ids)),
        "minimums": {
            "eligible_observations": MIN_ELIGIBLE_OBSERVATIONS,
            "observations_per_class": MIN_CLASS_OBSERVATIONS,
            "required_billing_frequencies": list(V3_BILLING_FREQUENCIES),
        },
        "memberships": memberships,
        "overall_status": "pass" if all(
            membership["support_status"] == "pass" for membership in memberships
        ) else "fail",
        "claim_boundary": "structural_support_only_no_modeling_or_metrics",
        "final_holdout_status": V6_FINAL_HOLDOUT_STATUS,
    }


def build_temporal_folds(observations: Iterable[V6Observation]) -> tuple[V6TemporalFold, ...]:
    rows = _normalized(observations)
    if not rows:
        raise ValueError("v6 observations are empty")
    folds = tuple(_build_fold(rows, specification, "acceptance") for specification in FOLDS)
    return folds


def build_selection_fold(observations: Iterable[V6Observation]) -> V6TemporalFold:
    rows = _normalized(observations)
    if not rows:
        raise ValueError("v6 observations are empty")
    return _build_fold(rows, SELECTION_FOLD, "selection")


def validate_temporal_fold(fold: V6TemporalFold, *, evaluate_support: bool = True) -> None:
    if not fold.fit or not fold.evaluation:
        raise ValueError(f"{fold.name} has an empty governed membership")
    if tuple(sorted(fold.fit, key=_row_key)) != fold.fit or tuple(
        sorted(fold.evaluation, key=_row_key)
    ) != fold.evaluation:
        raise ValueError("governed membership is not canonically ordered")
    if any(row.role != "fit" for row in fold.fit):
        raise ValueError("fit membership contains a non-fit policy role")
    expected_role = "selection" if fold.name == "selection" else "acceptance"
    if any(row.role != expected_role for row in fold.evaluation):
        raise ValueError("evaluation membership contains the wrong policy role")
    if {row.policy_id for row in fold.fit} & {row.policy_id for row in fold.evaluation}:
        raise ValueError("policy identity overlaps governed roles")
    if {row.outcome_episode_id for row in fold.fit} & {
        row.outcome_episode_id for row in fold.evaluation
    }:
        raise ValueError("outcome episode overlaps governed roles")
    earliest_evaluation = min(_time(row.as_of) for row in fold.evaluation)
    if max(_time(row.as_of) for row in fold.fit) >= earliest_evaluation:
        raise ValueError("feature cutoff chronology is invalid")
    if max(_time(row.horizon_end) for row in fold.fit) >= earliest_evaluation:
        raise ValueError("fit outcome horizon crosses the evaluation boundary")
    for row in (*fold.fit, *fold.evaluation):
        if row.observation_contract_version != V6_OBSERVATION_SCHEMA_VERSION:
            raise ValueError("governed membership contains a non-v6 observation")
        validate_v3_feature_payload(row.to_dict()["features"])
    if evaluate_support:
        _validate_support(fold.fit, "fit")
        _validate_support(fold.evaluation, expected_role)


def fit_preprocessor(fold: V6TemporalFold) -> V6Preprocessor:
    """Fit explicit preprocessing state from governed fit rows only."""

    validate_temporal_fold(fold)
    maps = tuple(_feature_map(row) for row in fold.fit)
    artifact_ids = {row.artifact_id for row in fold.fit}
    if len(artifact_ids) != 1:
        raise ValueError("preprocessing requires one v6 artifact identity")
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
    return V6Preprocessor(
        V6_FEATURE_PIPELINE_VERSION, fold.name, next(iter(artifact_ids)),
        tuple(row.observation_id for row in fold.fit), tuple(numeric),
        tuple(categorical), names,
    )


def transform(
    fitted: V6Preprocessor, rows: Iterable[V6Observation], *, purpose: str, role: str,
) -> V6Matrix:
    """Transform an exact governed membership without refitting state."""

    materialized = tuple(rows)
    if not materialized:
        raise ValueError("cannot transform empty membership")
    if any(row.role != role for row in materialized):
        raise ValueError("matrix role does not match source observations")
    if any(row.artifact_id != fitted.artifact_id for row in materialized):
        raise ValueError("matrix artifact identity does not match preprocessing")
    if tuple(sorted(materialized, key=_row_key)) != materialized:
        raise ValueError("matrix source membership is not canonically ordered")
    values = []
    for row in materialized:
        item = _feature_map(row)
        output = [(float(item[state.name]) - state.mean) / state.scale for state in fitted.numeric]
        for state in fitted.categorical:
            raw = str(item[state.name])
            selected = raw if raw in state.categories[:-1] else UNKNOWN_CATEGORY
            output.extend(float(category == selected) for category in state.categories)
        if not all(math.isfinite(value) for value in output):
            raise ValueError("v6 matrix contains a non-finite value")
        values.append(tuple(output))
    return V6Matrix(
        purpose, fitted.fold, role, fitted.artifact_id,
        tuple(row.observation_id for row in materialized),
        tuple(row.policy_id for row in materialized),
        tuple(row.outcome_episode_id for row in materialized),
        fitted.feature_names, tuple(values),
        tuple(int(row.label_value) for row in materialized),
    )


def authorize(
    train: V6Matrix, matrix: V6Matrix, fitted: V6Preprocessor, *, model_sha256: str,
) -> V6ScoringAuthorization:
    """Bind scoring permission to complete v6 content and provenance."""

    if train.purpose != "fit" or matrix.purpose not in {"fit", "selection", "acceptance"}:
        raise ValueError("unsupported v6 scoring purpose")
    if train.fold != matrix.fold or train.fold != fitted.fold:
        raise ValueError("cross-fold scoring is prohibited")
    if train.artifact_id != matrix.artifact_id or train.artifact_id != fitted.artifact_id:
        raise ValueError("cross-artifact scoring is prohibited")
    if train.observation_ids != fitted.fit_ids:
        raise ValueError("training membership does not match fitted preprocessing")
    _sha256_value(model_sha256, "model_sha256")
    fields = (
        V6_SCORING_AUTHORIZATION_VERSION, V6_SPLIT_VERSION,
        V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION, matrix.purpose, matrix.fold,
        matrix.role, matrix.artifact_id, matrix.observation_ids, matrix.feature_names,
        matrix_digest(matrix), target_digest(matrix.targets), matrix_digest(train),
        preprocessor_digest(fitted), model_sha256,
    )
    return V6ScoringAuthorization(*fields, _digest(fields))


def validate_authorization(
    authorization: V6ScoringAuthorization, matrix: V6Matrix, *,
    fit_matrix_sha256: str, preprocessor_sha256: str, model_sha256: str,
) -> None:
    fields = (
        authorization.version, authorization.split_version, authorization.protocol_version,
        authorization.purpose, authorization.fold, authorization.role,
        authorization.artifact_id, authorization.observation_ids,
        authorization.feature_names, authorization.matrix_sha256,
        authorization.target_sha256, authorization.fit_matrix_sha256,
        authorization.preprocessor_sha256, authorization.model_sha256,
    )
    if authorization.version != V6_SCORING_AUTHORIZATION_VERSION:
        raise ValueError("v6 scoring authorization version mismatch")
    if authorization.split_version != V6_SPLIT_VERSION:
        raise ValueError("v6 scoring authorization split version mismatch")
    if authorization.protocol_version != V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION:
        raise ValueError("v6 scoring authorization protocol version mismatch")
    if authorization.authorization_sha256 != _digest(fields):
        raise ValueError("v6 scoring authorization integrity failure")
    metadata = (
        authorization.purpose, authorization.fold, authorization.role,
        authorization.artifact_id, authorization.observation_ids,
        authorization.feature_names,
    )
    expected = (
        matrix.purpose, matrix.fold, matrix.role, matrix.artifact_id,
        matrix.observation_ids, matrix.feature_names,
    )
    if metadata != expected:
        raise ValueError("v6 scoring authorization metadata mismatch")
    if authorization.matrix_sha256 != matrix_digest(matrix):
        raise ValueError("v6 scoring authorization matrix mismatch")
    if authorization.target_sha256 != target_digest(matrix.targets):
        raise ValueError("v6 scoring authorization target mismatch")
    if authorization.fit_matrix_sha256 != fit_matrix_sha256:
        raise ValueError("v6 scoring authorization fit mismatch")
    if authorization.preprocessor_sha256 != preprocessor_sha256:
        raise ValueError("v6 scoring authorization preprocessing mismatch")
    if authorization.model_sha256 != model_sha256:
        raise ValueError("v6 scoring authorization model mismatch")


def compare_candidates(
    train: V6Matrix, selection: V6Matrix, fitted: V6Preprocessor,
) -> dict[str, Any]:
    """Fit the two frozen candidates and apply the exact selection rule."""

    if selection.purpose != "selection" or selection.role != "selection":
        raise ValueError("candidate selection requires the governed selection membership")
    logistic = LogisticRegression(
        penalty="l2", C=1.0, solver="liblinear", tol=1e-8, max_iter=1000,
        fit_intercept=True, class_weight=None, random_state=RANDOM_SEED,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        logistic.fit(train.values, train.targets)
    boosted = XGBClassifier(
        objective="binary:logistic", n_estimators=25, learning_rate=0.1,
        max_depth=2, min_child_weight=2.0, gamma=0.0, subsample=1.0,
        colsample_bytree=1.0, colsample_bylevel=1.0, colsample_bynode=1.0,
        reg_alpha=0.0, reg_lambda=1.0, scale_pos_weight=1.0, base_score=0.5,
        tree_method="exact", n_jobs=1, random_state=RANDOM_SEED,
        eval_metric="logloss", verbosity=0,
    )
    boosted.fit(train.values, train.targets, verbose=False)
    logistic_probabilities = tuple(
        float(value) for value in logistic.predict_proba(selection.values)[:, 1]
    )
    boosted_probabilities = tuple(
        float(value) for value in boosted.predict_proba(selection.values)[:, 1]
    )
    logistic_state = {
        "intercept": float(logistic.intercept_[0]),
        "coefficients": [float(value) for value in logistic.coef_[0]],
        "iterations": int(logistic.n_iter_[0]),
        "feature_names": list(train.feature_names),
    }
    logistic_reload = tuple(
        1.0 / (1.0 + math.exp(-(
            logistic_state["intercept"] + sum(
                coefficient * value for coefficient, value in zip(
                    logistic_state["coefficients"], row, strict=True,
                )
            )
        ))) for row in selection.values
    )
    if _prediction_digest(selection.observation_ids, logistic_probabilities) != _prediction_digest(
        selection.observation_ids, logistic_reload
    ):
        raise ValueError("logistic explicit state did not reproduce predictions")
    native_json = bytes(boosted.get_booster().save_raw(raw_format="json"))
    normalized_json = json.dumps(
        _normalize_model_state(json.loads(native_json)), sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    restored = xgb.Booster()
    restored.load_model(bytearray(normalized_json))
    boosted_reload = tuple(float(value) for value in restored.predict(
        xgb.DMatrix(selection.values, feature_names=list(selection.feature_names))
    ))
    if max(abs(expected - actual) for expected, actual in zip(
        boosted_probabilities, boosted_reload, strict=True,
    )) > 10 ** (-PORTABLE_ARTIFACT_DECIMALS):
        raise ValueError("boosted explicit state did not reproduce predictions")
    logistic_result = _candidate_result(selection, logistic_probabilities, logistic_state)
    boosted_result = _candidate_result(selection, boosted_probabilities, {
        "model_json": normalized_json.decode("utf-8"),
        "model_json_sha256": sha256(normalized_json).hexdigest(),
        "trained_tree_count": len(boosted.get_booster().get_dump()),
        "feature_names": list(train.feature_names),
    })
    logistic_auc = logistic_result["metrics"]["roc_auc"]
    boosted_auc = boosted_result["metrics"]["roc_auc"]
    tolerance = 1e-12
    if logistic_auc > boosted_auc + tolerance:
        selected = "logistic"
        reason = "higher_roc_auc"
    elif boosted_auc > logistic_auc + tolerance:
        selected = "xgboost"
        reason = "higher_roc_auc"
    else:
        logistic_brier = logistic_result["metrics"]["brier_score"]
        boosted_brier = boosted_result["metrics"]["brier_score"]
        if logistic_brier < boosted_brier - tolerance:
            selected = "logistic"
            reason = "auc_tie_lower_brier"
        elif boosted_brier < logistic_brier - tolerance:
            selected = "xgboost"
            reason = "auc_tie_lower_brier"
        else:
            selected = "logistic"
            reason = "auc_brier_tie_logistic"
    selected_result = logistic_result if selected == "logistic" else boosted_result
    model_sha = selected_result["safe_fitted_state_sha256"]
    authorization = authorize(train, selection, fitted, model_sha256=model_sha)
    validate_authorization(
        authorization, selection, fit_matrix_sha256=matrix_digest(train),
        preprocessor_sha256=preprocessor_digest(fitted), model_sha256=model_sha,
    )
    return {
        "versions": {
            "candidate": V6_CANDIDATE_VERSION,
            "selection_membership": V6_CANDIDATE_SELECTION_MEMBERSHIP_VERSION,
            "scikit_learn": sklearn_version, "xgboost": xgb.__version__,
        },
        "specifications": {
            "logistic": {
                "penalty": "l2", "C": 1.0, "solver": "liblinear", "tol": 1e-8,
                "max_iter": 1000, "random_seed": RANDOM_SEED,
            },
            "xgboost": {
                "n_estimators": 25, "learning_rate": 0.1, "max_depth": 2,
                "min_child_weight": 2.0, "tree_method": "exact", "n_jobs": 1,
                "random_seed": RANDOM_SEED, "early_stopping": False,
            },
        },
        "fit_matrix_sha256": matrix_digest(train),
        "selection_matrix_sha256": matrix_digest(selection),
        "preprocessor_sha256": preprocessor_digest(fitted),
        "logistic": logistic_result, "xgboost": boosted_result,
        "selection": {
            "selected_candidate": selected, "reason": reason,
            "auc_tolerance": "0.000000000001",
            "brier_tolerance": "0.000000000001",
            "selected_model_sha256": model_sha,
            "authorization_sha256": authorization.authorization_sha256,
        },
        "explicit_state_reload_verified": True,
    }


def diagnostics(train: V6Matrix, selection: V6Matrix, fitted: V6Preprocessor) -> dict[str, Any]:
    """Run deterministic non-final feature-boundary diagnostics."""

    source_indices = _source_feature_indices(fitted.feature_names)
    results = []
    flags = []
    for source, indices in source_indices.items():
        train_values = [[row[index] for index in indices] for row in train.values]
        selection_values = [[row[index] for index in indices] for row in selection.values]
        patterns = [tuple(row) for row in train_values]
        counts = Counter(patterns)
        discrete = all("=" in fitted.feature_names[index] for index in indices)
        mutual_information = mutual_info_classif(
            train_values, train.targets, discrete_features=discrete,
            n_neighbors=3, random_state=RANDOM_SEED,
        )
        tree = DecisionTreeClassifier(
            max_depth=1, criterion="log_loss", min_samples_leaf=2,
            random_state=RANDOM_SEED,
        ).fit(train_values, train.targets)
        probabilities = tuple(float(value) for value in tree.predict_proba(selection_values)[:, 1])
        metrics = _metrics(selection.targets, probabilities)
        source_flags = []
        majority = max(counts.values()) / len(patterns)
        uniqueness = len(counts) / len(patterns)
        if len(counts) == 1:
            source_flags.append("fit_constant")
        elif majority >= 0.95:
            source_flags.append("fit_near_constant")
        if len(counts) > 1 and uniqueness >= 0.90:
            source_flags.append("high_cardinality")
        if round(max(float(value) for value in mutual_information), PORTABLE_ARTIFACT_DECIMALS) >= 0.50:
            source_flags.append("strong_mutual_information")
        if round(metrics["roc_auc"], PORTABLE_ARTIFACT_DECIMALS) >= 0.90:
            source_flags.append("strong_shallow_model")
        for kind in source_flags:
            flags.append({"id": f"{kind}:{source}", "kind": kind, "source": source})
        results.append({
            "source": source,
            "driver_group": _driver_group(source),
            "output_width": len(indices),
            "fit_unique_patterns": len(counts),
            "fit_uniqueness_ratio": uniqueness,
            "fit_majority_fraction": majority,
            "selection_unique_patterns": len({tuple(row) for row in selection_values}),
            "mutual_information_max": max(float(value) for value in mutual_information),
            "shallow_selection_metrics": metrics,
            "flags": source_flags,
        })
    prohibited = sorted(
        name for name in source_indices
        if any(token in name.lower() for token in (
            "oracle", "frailty", "outcome", "scenario", "role", "event_id",
            "artifact_id", "policy_id", "observation_id", "label",
        ))
    )
    dispositions = []
    for flag in flags:
        group = _driver_group(flag["source"])
        if flag["kind"] == "fit_constant" and group != "missingness":
            decision = "redesign"
            rationale = (
                "a configured nonzero driver is constant in governed fit data; "
                "candidate authorization is prohibited pending versioned upstream remediation"
            )
        else:
            decision = "allow"
            rationale = (
                "approved public v6 feature; full multi-seed control evidence remains R2-16 work"
            )
        dispositions.append({
            "flag": flag["id"], "decision": decision, "rationale": rationale,
        })
    redesign = any(item["decision"] == "redesign" for item in dispositions)
    return {
        "diagnostic_version": V6_DIAGNOSTIC_VERSION,
        "identifier_and_protected_screen": {
            "status": "passed" if not prohibited else "failed", "hits": prohibited,
        },
        "driver_groups": {key: list(value) for key, value in FEATURE_GROUPS.items()},
        "strongest_group": "recent_payment",
        "designed_zero_group": "missingness",
        "source_results": results,
        "flags": flags,
        "dispositions": dispositions,
        "selection_unknown_counts": {
            state.name: sum(
                row[fitted.feature_names.index(f"{state.name}={UNKNOWN_CATEGORY}")] == 1.0
                for row in selection.values
            ) for state in fitted.categorical
        },
        "decision": "redesign" if prohibited or redesign else "allow",
        "claim_boundary": "non_final_feature_boundary_only",
    }


def matrix_digest(matrix: V6Matrix) -> str:
    payload = asdict(matrix)
    payload["values"] = [
        [round(value, MATRIX_DIGEST_DECIMALS) for value in row]
        for row in matrix.values
    ]
    return _digest(payload)


def target_digest(targets: tuple[int, ...]) -> str:
    return _digest(targets)


def preprocessor_digest(fitted: V6Preprocessor) -> str:
    return _digest(asdict(fitted))


def _build_fold(
    rows: tuple[V6Observation, ...], specification: tuple[str, str, str, str], role: str,
) -> V6TemporalFold:
    name, fit_end, evaluation_start, evaluation_end = specification
    fold = V6TemporalFold(
        name=name,
        fit=_eligible(rows, "fit", None, fit_end),
        evaluation=_eligible(rows, role, evaluation_start, evaluation_end),
        fit_through=fit_end,
        evaluation_start=evaluation_start,
        evaluation_end=evaluation_end,
    )
    validate_temporal_fold(fold)
    return fold


def _eligible(
    rows: tuple[V6Observation, ...], role: str, start: str | None, end: str,
) -> tuple[V6Observation, ...]:
    return tuple(
        row for row in rows
        if row.role == role
        and row.label_status in {"observed_positive", "observed_negative"}
        and row.label_value in {0, 1}
        and (start is None or _time(row.as_of) >= _time(start))
        and _time(row.as_of) <= _time(end)
    )


def _window(
    rows: tuple[V6Observation, ...], role: str, start: str | None, end: str,
) -> tuple[V6Observation, ...]:
    return tuple(
        row for row in rows
        if row.role == role
        and (start is None or _time(row.as_of) >= _time(start))
        and _time(row.as_of) <= _time(end)
    )


def _observed(rows: tuple[V6Observation, ...]) -> tuple[V6Observation, ...]:
    return tuple(
        row for row in rows
        if row.label_status in {"observed_positive", "observed_negative"}
        and row.label_value in {0, 1}
    )


def _validate_support(rows: tuple[V6Observation, ...], role: str) -> None:
    failures = _support_failures(rows, role)
    if failures:
        raise ValueError(failures[0])


def _support_failures(rows: tuple[V6Observation, ...], role: str) -> list[str]:
    failures = []
    if len(rows) < MIN_ELIGIBLE_OBSERVATIONS:
        failures.append(
            f"{role} membership has fewer than {MIN_ELIGIBLE_OBSERVATIONS} eligible observations"
        )
    labels = [row.label_value for row in rows]
    for value in (0, 1):
        if labels.count(value) < MIN_CLASS_OBSERVATIONS:
            failures.append(
                f"{role} membership has fewer than {MIN_CLASS_OBSERVATIONS} rows for class {value}"
            )
    frequencies = {row.features.billing_frequency for row in rows}
    if frequencies != set(V3_BILLING_FREQUENCIES):
        failures.append(f"{role} membership lacks a supported billing frequency")
    return failures


def _membership_summary(
    window: tuple[V6Observation, ...], eligible: tuple[V6Observation, ...],
) -> dict[str, object]:
    label_status = Counter(row.label_status for row in window)
    labels = Counter(row.label_value for row in eligible)
    frequencies = Counter(row.features.billing_frequency for row in eligible)
    censored = sum(row.label_status not in {"observed_positive", "observed_negative"} for row in window)
    return {
        "window_observations": len(window),
        "eligible_uncensored_observations": len(eligible),
        "right_censored_observations": censored,
        "right_censoring_fraction": censored / len(window) if window else 0.0,
        "positive": labels[1],
        "negative": labels[0],
        "unique_policies": len({row.policy_id for row in eligible}),
        "billing_frequency": dict(sorted(frequencies.items())),
        "label_status": dict(sorted(label_status.items())),
        "earliest_cutoff": min(row.as_of for row in eligible),
        "latest_cutoff": max(row.as_of for row in eligible),
        "membership_sha256": sha256(
            ("\n".join(row.observation_id for row in eligible) + "\n").encode("utf-8")
        ).hexdigest(),
    }


def _feature_map(row: V6Observation) -> dict[str, Any]:
    if row.observation_contract_version != V6_OBSERVATION_SCHEMA_VERSION:
        raise ValueError(f"feature extraction requires observation contract {V6_OBSERVATION_SCHEMA_VERSION}")
    validate_v3_feature_payload(asdict(row.features))
    if set(row.feature_lineage) != set(V6Features.__dataclass_fields__):
        raise ValueError("feature lineage must cover every public v6 feature")
    visible = set(row.visible_event_ids)
    if tuple(sorted(visible)) != row.visible_event_ids:
        raise ValueError("visible event identities are not sorted and unique")
    for name, sources in row.feature_lineage.items():
        if sources == "cutoff_derived":
            if name != "tenure_days":
                raise ValueError("undeclared cutoff-derived feature")
            continue
        if not isinstance(sources, tuple) or len(sources) != len(set(sources)):
            raise ValueError("feature lineage must name unique event identities")
        if any(source not in visible for source in sources):
            raise ValueError("feature lineage names an invisible event")
    if len(row.visible_events_sha256) != 64:
        raise ValueError("visible-event digest is malformed")
    int(row.visible_events_sha256, 16)
    result = asdict(row.features)
    result["tenure_days"] = min(max(result["tenure_days"] / 365, 0), 5)
    result["premium_amount_cents"] = min(
        max(math.log1p(result["premium_amount_cents"] / 100) / 5, 0), 2,
    )
    result["recent_delay_days"] = min(max(
        (result["recent_delay_days"] or 0) / 30, 0,
    ), 3)
    for name in (
        "recent_failed_payment_count", "recent_retry_count",
        "recent_recovery_count", "recent_notice_count", "recent_contact_count",
    ):
        result[name] = min(max(result[name] / 3, 0), 2)
    result["arrears_duration_days"] = min(max(result["arrears_duration_days"] / 60, 0), 2)
    result["rolling_payment_count"] = min(max(result["rolling_payment_count"] / 12, 0), 2)
    result["payment_attribute_missing"] = int(result["payment_attribute_missing"])
    result["contact_attribute_missing"] = int(result["contact_attribute_missing"])
    return result


def _candidate_result(
    matrix: V6Matrix, probabilities: tuple[float, ...], state: dict[str, Any],
) -> dict[str, Any]:
    metrics = _metrics(matrix.targets, probabilities)
    metrics.update({
        "records": len(matrix.targets),
        "negative": len(matrix.targets) - sum(matrix.targets),
        "positive": sum(matrix.targets),
        "average_predicted_probability": sum(probabilities) / len(probabilities),
        "observed_positive_fraction": sum(matrix.targets) / len(matrix.targets),
    })
    return {
        "metrics": metrics,
        "prediction_sha256": _prediction_digest(matrix.observation_ids, probabilities),
        "safe_fitted_state": state,
        "safe_fitted_state_sha256": _digest(_normalize_model_state(state)),
    }


def _metrics(targets: tuple[int, ...], probabilities: tuple[float, ...]) -> dict[str, float]:
    return {
        "roc_auc": float(roc_auc_score(targets, probabilities)),
        "log_loss": float(log_loss(targets, probabilities, labels=[0, 1])),
        "brier_score": float(brier_score_loss(targets, probabilities)),
    }


def _source_feature_indices(feature_names: tuple[str, ...]) -> dict[str, tuple[int, ...]]:
    sources = []
    for name in feature_names:
        source = name.split("=", 1)[0]
        if source not in sources:
            sources.append(source)
    return {
        source: tuple(
            index for index, name in enumerate(feature_names)
            if name.split("=", 1)[0] == source
        ) for source in sources
    }


def _driver_group(source: str) -> str:
    matches = [group for group, features in FEATURE_GROUPS.items() if source in features]
    if len(matches) != 1:
        raise ValueError(f"feature {source} does not map to exactly one driver group")
    return matches[0]


def _digest(value: Any) -> str:
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=list,
    ).encode("utf-8")).hexdigest()


def _prediction_digest(
    observation_ids: tuple[str, ...], probabilities: tuple[float, ...],
) -> str:
    return _digest({
        "observation_ids": observation_ids,
        "probabilities": [round(value, PORTABLE_ARTIFACT_DECIMALS) for value in probabilities],
    })


def _normalize_model_state(value: Any) -> Any:
    if isinstance(value, float):
        rounded = round(value, PORTABLE_ARTIFACT_DECIMALS)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: _normalize_model_state(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_normalize_model_state(nested) for nested in value]
    return value


def _sha256_value(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} must be a SHA-256 hex digest")
    int(value, 16)


def _normalized(observations: Iterable[V6Observation]) -> tuple[V6Observation, ...]:
    rows = tuple(sorted(observations, key=_row_key))
    ids = [row.observation_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate v6 observation identity")
    return rows


def _row_key(row: V6Observation) -> tuple[str, str, str]:
    return row.as_of, row.policy_id, row.observation_id


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("v6 evaluation timestamps must be UTC")
    return parsed


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "CATEGORICAL_FEATURES", "FEATURE_GROUPS", "FOLDS", "MATRIX_DIGEST_DECIMALS",
    "MIN_CLASS_OBSERVATIONS", "MIN_ELIGIBLE_OBSERVATIONS", "NUMERIC_FEATURES",
    "PORTABLE_ARTIFACT_DECIMALS", "RANDOM_SEED", "SELECTION_FOLD", "UNKNOWN_CATEGORY",
    "V6_CANDIDATE_SELECTION_MEMBERSHIP_VERSION", "V6_CANDIDATE_VERSION",
    "V6_DIAGNOSTIC_VERSION", "V6_EVALUATION_ACCEPTANCE_PROTOCOL_VERSION",
    "V6_EVALUATION_CONTRACT_VERSION", "V6_FEATURE_DICTIONARY_VERSION",
    "V6_FEATURE_PIPELINE_VERSION", "V6_FINAL_HOLDOUT_STATUS",
    "V6_SCORING_AUTHORIZATION_VERSION", "V6_SPLIT_VERSION",
    "V6_STRUCTURAL_SUPPORT_VERSION", "CategoryState", "NumericState",
    "V6Matrix", "V6Preprocessor", "V6ScoringAuthorization", "V6TemporalFold",
    "authorize", "build_selection_fold", "build_temporal_folds",
    "compare_candidates", "diagnostics", "fit_preprocessor", "matrix_digest",
    "preprocessor_digest", "structural_support_report", "target_digest",
    "transform", "validate_authorization", "validate_feature_registry",
    "validate_temporal_fold",
]
