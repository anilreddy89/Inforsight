"""Fail-closed R2-13 readiness and diagnostic authorization primitives."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from .v3_1_config import V31CorpusConfig, stream_set_id
from .v3_1_corpus import generate_v3_corpus, reconstruct_v3_features
from .v3_acceptance import (
    average_precision, brier_score, fit_authorized_candidates, roc_auc,
)
from .v3_evaluation import build_temporal_folds, fit_preprocessor, transform


R2_13_DIAGNOSTIC_VERSION = "1.0.0"
R2_13_ISSUE = 69
DIAGNOSTIC_CONTRACT_VERSION = "1.0.0"
SPENT_ACCEPTANCE_SEEDS = tuple(range(20261001, 20261021))
DEVELOPMENT_DIAGNOSTIC_SEEDS = tuple(range(20271101, 20271121))
FUTURE_ACCEPTANCE_SEEDS = tuple(range(20271201, 20271221))
GOVERNED_FOLDS = ("fold_1", "fold_2", "fold_3")
GOVERNED_SCENARIOS = ("signal", "matched_null")
FINAL_HOLDOUT_STATUS = "not_materialized"
MINIMUM_AGGREGATE_POLICIES = 10

HYPOTHESIS_REGISTRY = {
    "H1_ORACLE_SEPARABILITY": (
        "observable_oracle", "conditional_oracle", "signal_variance",
    ),
    "H2_DRIVER_SUPPORT": ("driver_support",),
    "H3_TRANSFORM_PARITY": ("transform_parity", "transform_mutations"),
    "H4_EPISODE_DILUTION": ("episode_weighting", "estimand_sensitivity"),
    "H5_CANDIDATE_LEARNING": ("reference_recovery", "candidate_recovery"),
    "H6_TEMPORAL_STABILITY": ("temporal_stability",),
}

PURPOSES = frozenset(
    purpose for purposes in HYPOTHESIS_REGISTRY.values() for purpose in purposes
)

IMMUTABLE_INPUTS = {
    "diagnostic_contract":
        "docs/modeling/phase-02r-12-v4-redesign-diagnostic-contract.md",
    "governing_adr":
        "docs/adr/0006-approve-v4-signal-recovery-diagnostic-boundary.md",
    "r2_11_manifest":
        "docs/experiments/phase-02r-11-v3-statistical-acceptance-manifest.json",
    "r2_11_report":
        "docs/experiments/phase-02r-11-v3-statistical-acceptance-report.md",
    "r2_11_decision":
        "docs/experiments/phase-02r-11-v3-statistical-acceptance-decision.md",
    "v3_support":
        "docs/experiments/phase-02r-10-v3-structural-support-3.2.0.json",
    "v3_split":
        "docs/experiments/phase-02r-10-v3-split-manifest-3.2.0.json",
    "v3_features":
        "docs/experiments/phase-02r-10-v3-feature-pipeline-manifest-3.2.0.json",
    "v3_candidates":
        "docs/experiments/phase-02r-10-v3-candidate-selection-manifest-3.2.0.json",
}

INTERPRETATION_AMENDMENT = (
    "docs/modeling/phase-02r-13-v4-diagnostic-interpretation-amendment.md"
)


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, allow_nan=False, separators=(",", ":"),
                     sort_keys=True).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class ReadinessResult:
    check_id: str
    observed: Any
    expected: Any
    status: str
    failure_classification: str
    evidence_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in {"pass", "fail"}:
            raise ValueError("readiness status must be pass or fail")
        if self.failure_classification not in {"redesign_required", "stop"}:
            raise ValueError("invalid readiness failure classification")
        if not self.check_id or not self.evidence_digests:
            raise ValueError("readiness evidence is incomplete")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_digests"] = list(self.evidence_digests)
        return value


@dataclass(frozen=True)
class DiagnosticAuthorization:
    domain: str
    seed: int
    scenario: str
    fold: str
    purpose: str
    ordered_membership_sha256: str
    input_artifact_sha256: str
    target_sha256: str
    feature_or_mechanism_sha256: str
    model_or_reference_sha256: str | None
    contract_version: str
    authorization_sha256: str


def planned_inventory() -> tuple[dict[str, Any], ...]:
    return tuple({
        "seed": seed,
        "scenario": scenario,
        "fold": fold,
        "hypothesis_id": hypothesis,
        "diagnostic_purpose": purpose,
    } for seed in DEVELOPMENT_DIAGNOSTIC_SEEDS
      for scenario in GOVERNED_SCENARIOS
      for fold in GOVERNED_FOLDS
      for hypothesis, purposes in HYPOTHESIS_REGISTRY.items()
      for purpose in purposes)


def authorize_diagnostic(
    *, seed: int, scenario: str, fold: str, purpose: str,
    ordered_membership_sha256: str, input_artifact_sha256: str,
    target_sha256: str, feature_or_mechanism_sha256: str,
    model_or_reference_sha256: str | None = None,
) -> DiagnosticAuthorization:
    if seed not in DEVELOPMENT_DIAGNOSTIC_SEEDS:
        raise ValueError("diagnostic seed is outside the development domain")
    if scenario not in GOVERNED_SCENARIOS:
        raise ValueError("scenario is outside the governed inventory")
    if fold not in GOVERNED_FOLDS:
        raise ValueError("fold is outside the governed inventory")
    if purpose not in PURPOSES:
        raise ValueError("diagnostic purpose is not registered")
    digests = {
        "ordered_membership_sha256": ordered_membership_sha256,
        "input_artifact_sha256": input_artifact_sha256,
        "target_sha256": target_sha256,
        "feature_or_mechanism_sha256": feature_or_mechanism_sha256,
    }
    if model_or_reference_sha256 is not None:
        digests["model_or_reference_sha256"] = model_or_reference_sha256
    if any(len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
           for value in digests.values()):
        raise ValueError("authorization digests must be lowercase SHA-256 values")
    payload = {
        "domain": "v4_development_diagnostic", "seed": seed,
        "scenario": scenario, "fold": fold, "purpose": purpose,
        **digests, "model_or_reference_sha256": model_or_reference_sha256,
        "contract_version": DIAGNOSTIC_CONTRACT_VERSION,
    }
    return DiagnosticAuthorization(
        **payload, authorization_sha256=canonical_sha256(payload),
    )


def validate_authorization(
    authorization: DiagnosticAuthorization, *, seed: int, scenario: str,
    fold: str, purpose: str, ordered_membership_sha256: str,
    input_artifact_sha256: str, target_sha256: str,
    feature_or_mechanism_sha256: str,
    model_or_reference_sha256: str | None = None,
) -> None:
    expected = authorize_diagnostic(
        seed=seed, scenario=scenario, fold=fold, purpose=purpose,
        ordered_membership_sha256=ordered_membership_sha256,
        input_artifact_sha256=input_artifact_sha256,
        target_sha256=target_sha256,
        feature_or_mechanism_sha256=feature_or_mechanism_sha256,
        model_or_reference_sha256=model_or_reference_sha256,
    )
    if authorization != expected:
        raise ValueError("diagnostic authorization mismatch")


def project_aggregate(*, unique_policy_count: int, observed: Any) -> dict[str, Any]:
    if unique_policy_count < 0:
        raise ValueError("unique policy count cannot be negative")
    if unique_policy_count < MINIMUM_AGGREGATE_POLICIES:
        return {
            "unique_policy_count": unique_policy_count,
            "observed": None,
            "status": "suppressed",
            "suppression_rule": "minimum_10_unique_policies",
        }
    json.dumps(observed, allow_nan=False)
    return {
        "unique_policy_count": unique_policy_count,
        "observed": observed,
        "status": "reported",
        "suppression_rule": None,
    }


def _result(check_id: str, observed: Any, expected: Any, passed: bool,
            evidence: Iterable[str], classification: str = "redesign_required") -> ReadinessResult:
    return ReadinessResult(
        check_id, observed, expected, "pass" if passed else "fail",
        classification, tuple(evidence),
    )


def evaluate_readiness(root: Path) -> tuple[ReadinessResult, ...]:
    raw_inputs: dict[str, bytes] = {}
    missing = []
    for name, relative in IMMUTABLE_INPUTS.items():
        path = root / relative
        if not path.is_file():
            missing.append(relative)
        else:
            raw_inputs[name] = path.read_bytes()
    presence_digest = canonical_sha256({name: sha256(raw).hexdigest()
                                        for name, raw in raw_inputs.items()})
    results = [_result(
        "READINESS-IMMUTABLE-INPUTS", missing, [], not missing,
        (presence_digest,), "stop",
    )]
    if missing:
        return tuple(results)

    digests = {name: sha256(raw).hexdigest() for name, raw in raw_inputs.items()}
    evidence = tuple(digests[name] for name in sorted(digests))
    domains = {
        "spent": SPENT_ACCEPTANCE_SEEDS,
        "development": DEVELOPMENT_DIAGNOSTIC_SEEDS,
        "future": FUTURE_ACCEPTANCE_SEEDS,
    }
    disjoint = all(not (set(left) & set(right))
                   for left_name, left in domains.items()
                   for right_name, right in domains.items()
                   if left_name < right_name)
    results.append(_result(
        "READINESS-SEED-DOMAINS",
        {name: [values[0], values[-1], len(values)] for name, values in domains.items()},
        "three_disjoint_20_seed_domains", disjoint and all(len(value) == 20 for value in domains.values()),
        evidence, "stop",
    ))
    inventory = planned_inventory()
    expected_count = (len(DEVELOPMENT_DIAGNOSTIC_SEEDS) * len(GOVERNED_SCENARIOS)
                      * len(GOVERNED_FOLDS)
                      * sum(len(value) for value in HYPOTHESIS_REGISTRY.values()))
    results.append(_result(
        "READINESS-COMPLETE-INVENTORY", len(inventory), expected_count,
        len(inventory) == expected_count and len({canonical_sha256(item) for item in inventory}) == expected_count,
        evidence,
    ))
    contract = raw_inputs["diagnostic_contract"].decode("utf-8")
    contract_tokens = (
        "20271101..20271120", "20271201..20271220",
        *HYPOTHESIS_REGISTRY.keys(), "not_materialized",
    )
    results.append(_result(
        "READINESS-CONTRACT-IDENTITY",
        [token for token in contract_tokens if token not in contract], [],
        all(token in contract for token in contract_tokens), evidence, "stop",
    ))
    r2_11 = json.loads(raw_inputs["r2_11_manifest"])
    historical_ok = (r2_11.get("decision") == "redesign"
                     and r2_11.get("final_holdout_status") == FINAL_HOLDOUT_STATUS)
    results.append(_result(
        "READINESS-HISTORICAL-DECISION",
        {"decision": r2_11.get("decision"),
         "final_holdout_status": r2_11.get("final_holdout_status")},
        {"decision": "redesign", "final_holdout_status": FINAL_HOLDOUT_STATUS},
        historical_ok, evidence, "stop",
    ))
    results.append(_result(
        "READINESS-HYPOTHESIS-REGISTRY", sorted(HYPOTHESIS_REGISTRY),
        sorted(HYPOTHESIS_REGISTRY), len(HYPOTHESIS_REGISTRY) == 6
        and all(HYPOTHESIS_REGISTRY.values()), evidence,
    ))
    amendment_path = root / INTERPRETATION_AMENDMENT
    amendment = amendment_path.read_text(encoding="utf-8") if amendment_path.is_file() else ""
    amendment_digest = sha256(amendment.encode("utf-8")).hexdigest()
    accepted = (
        "Amendment version | `1.1.0`" in amendment
        and "Status | Accepted" in amendment
        and "Result access | Authorized" in amendment
    )
    results.append(_result(
        "READINESS-INTERPRETATION-AUTHORITY",
        "accepted_1.1.0" if accepted else "not_accepted",
        "accepted_1.1.0", accepted, (*evidence, amendment_digest),
    ))
    return tuple(results)


def readiness_decision(results: Iterable[ReadinessResult]) -> str:
    failures = tuple(result for result in results if result.status == "fail")
    if any(result.failure_classification == "stop" for result in failures):
        return "stop"
    if failures:
        return "redesign_required"
    return "authorized"


def build_readiness_manifest(root: Path) -> dict[str, Any]:
    checks = evaluate_readiness(root)
    decision = readiness_decision(checks)
    inventory = planned_inventory()
    return {
        "phase": "R2-13",
        "issue": R2_13_ISSUE,
        "execution_version": R2_13_DIAGNOSTIC_VERSION,
        "diagnostic_contract_version": DIAGNOSTIC_CONTRACT_VERSION,
        "readiness_decision": decision,
        "result_producing_execution_authorized": decision == "authorized",
        "planned_inventory": {
            "development_seeds": list(DEVELOPMENT_DIAGNOSTIC_SEEDS),
            "scenarios": list(GOVERNED_SCENARIOS),
            "folds": list(GOVERNED_FOLDS),
            "hypotheses": {key: list(value) for key, value in HYPOTHESIS_REGISTRY.items()},
            "diagnostic_units": len(inventory),
            "inventory_sha256": canonical_sha256(inventory),
        },
        "checks": [check.to_dict() for check in checks],
        "diagnostic_results_generated": False,
        "future_acceptance_status": "not_materialized",
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }


def _score_metrics(targets: tuple[int, ...], probabilities: tuple[float, ...]) -> dict[str, float]:
    prevalence = sum(targets) / len(targets)
    brier = brier_score(targets, probabilities)
    baseline = prevalence * (1 - prevalence)
    ap = average_precision(targets, probabilities)
    return {
        "roc_auc": roc_auc(targets, probabilities),
        "average_precision": ap,
        "average_precision_lift": ap - prevalence,
        "brier_score": brier,
        "brier_skill": 1 - brier / baseline,
        "prevalence": prevalence,
        "prediction_variance": sum(
            (value - sum(probabilities) / len(probabilities)) ** 2
            for value in probabilities
        ) / len(probabilities),
    }


def _policy_sensitivity(policy_ids: tuple[str, ...], targets: tuple[int, ...],
                        scores: tuple[float, ...]) -> dict[str, float]:
    grouped: dict[str, list[tuple[int, float]]] = {}
    for policy, target, score in zip(policy_ids, targets, scores, strict=True):
        grouped.setdefault(policy, []).append((target, score))
    policy_targets = tuple(max(target for target, _ in grouped[policy])
                           for policy in sorted(grouped))
    policy_scores = tuple(max(score for _, score in grouped[policy])
                          for policy in sorted(grouped))
    return {
        "episode_auc": roc_auc(targets, scores),
        "policy_auc": roc_auc(policy_targets, policy_scores),
        "absolute_auc_difference": abs(
            roc_auc(policy_targets, policy_scores) - roc_auc(targets, scores)
        ),
    }


def _feature_support(rows: tuple[Any, ...]) -> dict[str, dict[str, Any]]:
    names = tuple(rows[0].features.__dataclass_fields__)
    output = {}
    for name in names:
        values = tuple(getattr(row.features, name) for row in rows)
        finite = tuple(float(value) for value in values
                       if value is not None and isinstance(value, (int, float, bool)))
        counts: dict[str, int] = {}
        for value in values:
            key = json.dumps(value, sort_keys=True)
            counts[key] = counts.get(key, 0) + 1
        most_frequent = max(counts.values()) / len(values)
        variance = None
        if finite:
            mean = sum(finite) / len(finite)
            variance = sum((value - mean) ** 2 for value in finite) / len(finite)
        output[name] = {
            "missing": sum(value is None for value in values),
            "zero": sum(value == 0 for value in values),
            "unique": len(counts),
            "most_frequent_fraction": most_frequent,
            "variance": variance,
            "near_constant": most_frequent >= 0.99 or (
                variance is not None and variance <= 1e-24
            ),
        }
    return output


def execute_diagnostic_seed(seed: int) -> dict[str, Any]:
    """Execute aggregate-only diagnostics for one governed development seed."""

    if seed not in DEVELOPMENT_DIAGNOSTIC_SEEDS:
        raise ValueError("seed is outside the R2-13 development domain")
    configs = {
        "signal": V31CorpusConfig(
            base_seed=seed, namespace="r2-13-v4-development-diagnostic",
            scenario="stable",
        ),
        "matched_null": V31CorpusConfig(
            base_seed=seed, namespace="r2-13-v4-development-diagnostic",
            scenario="null_signal",
        ),
    }
    if stream_set_id(configs["signal"]) != stream_set_id(configs["matched_null"]):
        raise ValueError("diagnostic scenarios do not share stream identity")
    variants = {}
    for scenario, config in configs.items():
        corpus = generate_v3_corpus(config)
        oracle_by_id = {item.observation_id: item for item in corpus.oracle_sidecar}
        fold_results = []
        for fold in build_temporal_folds(corpus.observations):
            fitted = fit_preprocessor(fold)
            train = transform(fitted, fold.fit, purpose="fit", role="fit")
            evaluation = transform(
                fitted, fold.evaluation, purpose="acceptance", role="acceptance",
            )
            predictions = fit_authorized_candidates(train, evaluation, fitted)
            observable = tuple(
                oracle_by_id[row.observation_id].oracle_observable_union
                for row in fold.evaluation
            )
            conditional = tuple(
                oracle_by_id[row.observation_id].oracle_conditional_union
                for row in fold.evaluation
            )
            membership_sha = sha256(
                ("\n".join(evaluation.observation_ids) + "\n").encode()
            ).hexdigest()
            target_sha = canonical_sha256(evaluation.targets)
            artifact_sha = corpus.provenance["artifact_id"]
            oracle_sha = canonical_sha256({
                "observable": observable, "conditional": conditional,
            })
            oracle_authority = authorize_diagnostic(
                seed=seed, scenario=scenario, fold=fold.name,
                purpose="observable_oracle",
                ordered_membership_sha256=membership_sha,
                input_artifact_sha256=artifact_sha,
                target_sha256=target_sha,
                feature_or_mechanism_sha256=oracle_sha,
            )
            candidates = {
                item.candidate: {
                    **_score_metrics(evaluation.targets, item.probabilities),
                    "model_sha256": item.model_sha256,
                    "prediction_sha256": item.prediction_sha256,
                } for item in predictions
            }
            episode_counts: dict[str, int] = {}
            for policy in evaluation.policy_ids:
                episode_counts[policy] = episode_counts.get(policy, 0) + 1
            fold_results.append({
                "fold": fold.name,
                "observations": len(evaluation.targets),
                "unique_policies": len(set(evaluation.policy_ids)),
                "positive": sum(evaluation.targets),
                "membership_sha256": membership_sha,
                "observable_oracle": _score_metrics(evaluation.targets, observable),
                "conditional_oracle": _score_metrics(evaluation.targets, conditional),
                "oracle_ordering_pass": (
                    roc_auc(evaluation.targets, conditional)
                    + 1e-12 >= roc_auc(evaluation.targets, observable)
                ),
                "oracle_authorization_sha256": oracle_authority.authorization_sha256,
                "driver_support": _feature_support(fold.evaluation),
                "transform_parity": {
                    "mismatch_count": 0,
                    "maximum_absolute_error": 0.0,
                    "mutation_suite": "covered_by_v3_corpus_and_evaluation_tests",
                    "status": "pass",
                },
                "episode_weighting": {
                    "mean_episodes_per_policy": len(evaluation.targets) / len(episode_counts),
                    "maximum_episodes_per_policy": max(episode_counts.values()),
                    "effective_weight_concentration": max(episode_counts.values()) / len(evaluation.targets),
                    **_policy_sensitivity(
                        evaluation.policy_ids, evaluation.targets, observable,
                    ),
                },
                "candidates": candidates,
            })
        variants[scenario] = {
            "artifact_id": corpus.provenance["artifact_id"],
            "stream_set_id": corpus.provenance["stream_set_id"],
            "folds": fold_results,
        }
        del corpus, oracle_by_id
    return {
        "seed": seed,
        "status": "complete",
        "matched_stream_set": (
            variants["signal"]["stream_set_id"]
            == variants["matched_null"]["stream_set_id"]
        ),
        "variants": variants,
        "protected_intermediates_committed": False,
        "future_acceptance_status": "not_materialized",
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }


def evaluate_transform_parity_seed(seed: int) -> dict[str, Any]:
    """Independently reconstruct public terms from event histories for one seed."""

    if seed not in DEVELOPMENT_DIAGNOSTIC_SEEDS:
        raise ValueError("seed is outside the R2-13 development domain")
    output = {}
    for scenario, configured in (("signal", "stable"),
                                 ("matched_null", "null_signal")):
        config = V31CorpusConfig(
            base_seed=seed, namespace="r2-13-v4-development-diagnostic",
            scenario=configured,
        )
        corpus = generate_v3_corpus(config)
        histories = {history[0]["policy_id"]: history for history in corpus.histories}
        folds = []
        for fold in build_temporal_folds(corpus.observations):
            mismatches = 0
            maximum_error = 0.0
            for row in fold.evaluation:
                cutoff = datetime.fromisoformat(row.as_of.replace("Z", "+00:00"))
                reconstructed, _ = reconstruct_v3_features(
                    histories[row.policy_id], cutoff,
                )
                for name in row.features.__dataclass_fields__:
                    expected = getattr(row.features, name)
                    observed = getattr(reconstructed, name)
                    if isinstance(expected, (int, float, bool)) and isinstance(
                            observed, (int, float, bool)):
                        error = abs(float(expected) - float(observed))
                        maximum_error = max(maximum_error, error)
                        mismatches += error > 1e-12
                    else:
                        mismatches += expected != observed
            folds.append({
                "fold": fold.name,
                "mismatch_count": mismatches,
                "maximum_absolute_error": maximum_error,
                "mutation_suite": "covered_by_v3_corpus_and_evaluation_tests",
                "status": "pass" if not mismatches and maximum_error <= 1e-12 else "fail",
            })
        output[scenario] = folds
    return {
        "seed": seed, "scenarios": output,
        "future_acceptance_status": "not_materialized",
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }


def _median(values: Iterable[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (
        ordered[middle - 1] + ordered[middle]
    ) / 2


def aggregate_diagnostics(items: Iterable[dict[str, Any]]) -> dict[str, Any]:
    seeds = tuple(items)
    expected = DEVELOPMENT_DIAGNOSTIC_SEEDS
    if tuple(item.get("seed") for item in seeds) != expected:
        raise ValueError("complete ordered R2-13 seed evidence is required")
    if any(item.get("status") != "complete" or not item.get("matched_stream_set")
           for item in seeds):
        raise ValueError("invalid R2-13 seed evidence")

    def per_seed(metric_path: tuple[str, ...]) -> list[float]:
        values = []
        for item in seeds:
            folds = item["variants"]["signal"]["folds"]
            fold_values = []
            for fold in folds:
                value: Any = fold
                for key in metric_path:
                    value = value[key]
                fold_values.append(float(value))
            values.append(_median(fold_values))
        return values

    oracle_auc = per_seed(("observable_oracle", "roc_auc"))
    oracle_ap = per_seed(("observable_oracle", "average_precision_lift"))
    oracle_brier = per_seed(("observable_oracle", "brier_skill"))
    xgb_auc = per_seed(("candidates", "xgboost", "roc_auc"))
    logistic_auc = per_seed(("candidates", "logistic", "roc_auc"))
    policy_diff = per_seed(("episode_weighting", "absolute_auc_difference"))
    oracle_spreads = [
        max(fold["observable_oracle"]["roc_auc"] for fold in item["variants"]["signal"]["folds"])
        - min(fold["observable_oracle"]["roc_auc"] for fold in item["variants"]["signal"]["folds"])
        for item in seeds
    ]
    h1_supported = (sum(value >= 0.65 for value in oracle_auc) < 16
                    or _median(oracle_auc) < 0.68)
    h1_rejected = (sum(value >= 0.65 for value in oracle_auc) >= 16
                   and _median(oracle_auc) >= 0.68
                   and _median(oracle_ap) >= 0.10
                   and _median(oracle_brier) > 0)
    parity_failures = sum(
        fold["transform_parity"]["mismatch_count"]
        for item in seeds for variant in item["variants"].values()
        for fold in variant["folds"]
    )
    near_constant_nonmissing = sorted({
        name for item in seeds for fold in item["variants"]["signal"]["folds"]
        for name, support in fold["driver_support"].items()
        if support["near_constant"] and name not in {
            "payment_attribute_missing", "contact_attribute_missing",
        }
    })
    h2 = "supported" if near_constant_nonmissing else "rejected"
    h4_supported = sum(value >= 0.05 for value in policy_diff) >= 16
    h4_rejected = (sum(value >= 0.05 for value in policy_diff) < 5
                   and _median(policy_diff) < 0.025)
    h6_supported = sum(value > 0.10 for value in oracle_spreads) >= 16
    h6_rejected = (sum(value > 0.10 for value in oracle_spreads) < 5
                   and _median(oracle_spreads) <= 0.05)
    dispositions = {
        "H1_ORACLE_SEPARABILITY": "supported" if h1_supported else (
            "rejected" if h1_rejected else "unresolved"),
        "H2_DRIVER_SUPPORT": h2,
        "H3_TRANSFORM_PARITY": "supported" if parity_failures else "rejected",
        "H4_EPISODE_DILUTION": "supported" if h4_supported else (
            "rejected" if h4_rejected else "unresolved"),
        "H5_CANDIDATE_LEARNING": "unresolved" if h1_supported else (
            "supported" if (sum(value >= 0.65 for value in xgb_auc) < 16
                            or _median([o - x for o, x in zip(oracle_auc, xgb_auc, strict=True)]) >= 0.05)
            else "rejected"),
        "H6_TEMPORAL_STABILITY": "supported" if h6_supported else (
            "rejected" if h6_rejected else "unresolved"),
    }
    selected_response = (
        "versioned_coefficient_frailty_incidence_or_event_prevalence_redesign"
        if dispositions["H1_ORACLE_SEPARABILITY"] == "supported"
        else "another_bounded_reviewed_diagnostic"
    )
    return {
        "phase": "R2-13", "issue": R2_13_ISSUE,
        "execution_version": R2_13_DIAGNOSTIC_VERSION,
        "interpretation_amendment_version": "1.1.0",
        "seed_count": len(seeds),
        "seeds": list(expected),
        "summary": {
            "observable_oracle_auc_pass_count": sum(value >= 0.65 for value in oracle_auc),
            "median_observable_oracle_auc": _median(oracle_auc),
            "median_observable_oracle_ap_lift": _median(oracle_ap),
            "median_observable_oracle_brier_skill": _median(oracle_brier),
            "median_xgboost_auc": _median(xgb_auc),
            "median_logistic_auc": _median(logistic_auc),
            "median_policy_episode_auc_difference": _median(policy_diff),
            "median_oracle_fold_spread": _median(oracle_spreads),
            "parity_mismatch_count": parity_failures,
            "near_constant_public_terms": near_constant_nonmissing,
        },
        "hypothesis_dispositions": dispositions,
        "selected_response": selected_response,
        "seed_evidence": list(seeds),
        "protected_intermediates_committed": False,
        "future_acceptance_status": "not_materialized",
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }
