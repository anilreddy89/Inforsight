"""Fail-closed R2-14 development qualification and aggregate evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from sklearn.linear_model import LogisticRegression

from .v3_acceptance import average_precision, brier_score, fit_authorized_candidates, roc_auc
from .v3_evaluation import build_temporal_folds, fit_preprocessor, transform
from .v4_config import V4CorpusConfig, stream_set_id
from .v4_corpus import (
    competing_hazards, generate_v4_corpus, public_mechanism_terms,
    reconstruct_v4_features,
)

R2_14_ISSUE = 72
R2_14_QUALIFICATION_VERSION = "1.0.0"
DEVELOPMENT_SEEDS = tuple(range(20271101, 20271121))
FUTURE_ACCEPTANCE_SEEDS = tuple(range(20271201, 20271221))
SPENT_ACCEPTANCE_SEEDS = tuple(range(20261001, 20261021))
GOVERNED_FOLDS = ("fold_1", "fold_2", "fold_3")
FINAL_HOLDOUT_STATUS = "not_materialized"
IMMUTABLE_INPUTS = (
    "docs/adr/0007-approve-v4-signal-recovery-design.md",
    "docs/modeling/phase-02r-13-v4-substrate-contract.md",
    "docs/modeling/phase-02r-13-v4-statistical-acceptance-protocol.md",
    "docs/experiments/phase-02r-13-v4-redesign-diagnostic-manifest.json",
)
GATE_IDS = (
    "observable_seed_recovery", "observable_aggregate_recovery",
    "oracle_probability_quality", "driver_support", "transform_parity",
    "matched_null_behavior", "reference_recovery", "hazard_validity",
    "structural_controls",
)


def canonical_sha256(value: Any) -> str:
    return sha256(json.dumps(value, allow_nan=False, separators=(",", ":"),
                             sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ReadinessCheck:
    check_id: str
    status: str
    failure_classification: str
    observed: Any
    expected: Any
    evidence_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def planned_inventory() -> tuple[dict[str, Any], ...]:
    return tuple({"seed": seed, "fold": fold, "scenario": scenario}
                 for seed in DEVELOPMENT_SEEDS
                 for scenario in ("signal", "matched_null")
                 for fold in GOVERNED_FOLDS)


def evaluate_readiness(root: Path) -> tuple[ReadinessCheck, ...]:
    missing = [path for path in IMMUTABLE_INPUTS if not (root / path).is_file()]
    inputs = {path: sha256((root / path).read_bytes()).hexdigest()
              for path in IMMUTABLE_INPUTS if (root / path).is_file()}
    evidence = canonical_sha256(inputs)
    checks = [ReadinessCheck(
        "immutable_inputs", "pass" if not missing else "fail", "stop",
        missing, [], evidence,
    )]
    domains_disjoint = not (
        set(DEVELOPMENT_SEEDS) & set(FUTURE_ACCEPTANCE_SEEDS)
        or set(DEVELOPMENT_SEEDS) & set(SPENT_ACCEPTANCE_SEEDS)
    )
    checks.append(ReadinessCheck(
        "seed_domain_separation", "pass" if domains_disjoint else "fail", "stop",
        {"development": list(DEVELOPMENT_SEEDS), "future_status": "not_materialized",
         "spent": list(SPENT_ACCEPTANCE_SEEDS)}, "disjoint", evidence,
    ))
    inventory = planned_inventory()
    complete = len(inventory) == 120 and len({canonical_sha256(row) for row in inventory}) == 120
    checks.append(ReadinessCheck(
        "complete_inventory", "pass" if complete else "fail", "redesign",
        len(inventory), 120, canonical_sha256(inventory),
    ))
    tokens = {
        "docs/adr/0007-approve-v4-signal-recovery-design.md": ("R2-14", "not_materialized"),
        "docs/modeling/phase-02r-13-v4-substrate-contract.md": (
            "4.0.0", "20271101..20271120", "20271201..20271220"),
        "docs/modeling/phase-02r-13-v4-statistical-acceptance-protocol.md": (
            "3.0.0", "R2-14", "R2-16"),
    }
    missing_tokens = []
    for path, required in tokens.items():
        content = (root / path).read_text() if (root / path).is_file() else ""
        missing_tokens.extend(f"{path}:{token}" for token in required if token not in content)
    checks.append(ReadinessCheck(
        "contract_authority", "pass" if not missing_tokens else "fail", "stop",
        missing_tokens, [], evidence,
    ))
    return tuple(checks)


def readiness_decision(checks: Iterable[ReadinessCheck]) -> str:
    failures = tuple(check for check in checks if check.status == "fail")
    if any(check.failure_classification == "stop" for check in failures):
        return "stop"
    return "redesign" if failures else "authorized"


def build_readiness_manifest(root: Path) -> dict[str, Any]:
    checks = evaluate_readiness(root)
    decision = readiness_decision(checks)
    return {
        "phase": "R2-14", "issue": R2_14_ISSUE,
        "qualification_version": R2_14_QUALIFICATION_VERSION,
        "readiness_decision": decision,
        "result_producing_execution_authorized": decision == "authorized",
        "planned_inventory": {"seeds": list(DEVELOPMENT_SEEDS),
                              "folds": list(GOVERNED_FOLDS),
                              "scenarios": ["signal", "matched_null"],
                              "units": len(planned_inventory()),
                              "sha256": canonical_sha256(planned_inventory())},
        "checks": [check.to_dict() for check in checks],
        "future_acceptance_status": "not_materialized",
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }


def _metrics(targets: tuple[int, ...], scores: tuple[float, ...]) -> dict[str, float]:
    prevalence = sum(targets) / len(targets)
    brier = brier_score(targets, scores)
    baseline = prevalence * (1 - prevalence)
    ap = average_precision(targets, scores)
    return {"roc_auc": roc_auc(targets, scores),
            "average_precision_lift": ap - prevalence,
            "brier_skill": 1 - brier / baseline}


def _reference_scores(fold: Any) -> tuple[float, ...]:
    names = tuple(public_mechanism_terms(fold.fit[0].features))
    x_fit = [[public_mechanism_terms(row.features)[name] for name in names] for row in fold.fit]
    x_eval = [[public_mechanism_terms(row.features)[name] for name in names] for row in fold.evaluation]
    targets = [int(row.label_value) for row in fold.fit]
    model = LogisticRegression(random_state=20260817, max_iter=1000, solver="lbfgs")
    model.fit(x_fit, targets)
    return tuple(float(value) for value in model.predict_proba(x_eval)[:, 1])


def _driver_support(rows: tuple[Any, ...]) -> dict[str, bool]:
    terms = {name: [] for name in public_mechanism_terms(rows[0].features)}
    for row in rows:
        for name, value in public_mechanism_terms(row.features).items():
            terms[name].append(value)
    nonzero = set(terms) - {"payment_missing", "contact_missing"}
    return {name: len(set(values)) > 1 and max(values.count(value) for value in set(values)) / len(values) < 0.99
            for name, values in terms.items() if name in nonzero}


def execute_qualification_seed(seed: int) -> dict[str, Any]:
    if seed not in DEVELOPMENT_SEEDS:
        raise ValueError("seed is outside the R2-14 development domain")
    variants = {}
    for scenario, scenario_name in (("signal", "stable"), ("matched_null", "null_signal")):
        config = V4CorpusConfig(base_seed=seed, scenario=scenario_name)
        # Qualification must retain and report a frozen-design hazard violation
        # rather than lose the planned unit to an exception.
        corpus = generate_v4_corpus(config, enforce_hazard_bound=False)
        oracle = {row.observation_id: row for row in corpus.oracle_sidecar}
        histories = {history[0]["policy_id"]: history for history in corpus.histories}
        folds = []
        maximum_hazard = 0.0
        for row in corpus.observations:
            sidecar = oracle[row.observation_id]
            for month in (1, 2, 3):
                hazards = competing_hazards(
                    row.features, sidecar.latent_frailty, month,
                    signal_scale=float(scenario == "signal"),
                    enforce_generated_bound=False,
                )
                maximum_hazard = max(maximum_hazard, hazards[0] + hazards[1])
        # Protocol 3.0.0 preserves the v3 evaluation implementation exactly.
        # This explicit adapter changes only the version discriminator required
        # by that historical validator; v4 rows and artifact identities remain
        # separate and the adapter is never serialized.
        compatible = tuple(replace(row, observation_contract_version="3.0.0")
                           for row in corpus.observations)
        for fold in build_temporal_folds(compatible):
            targets = tuple(int(row.label_value) for row in fold.evaluation)
            oracle_scores = tuple(oracle[row.observation_id].oracle_observable_union
                                  for row in fold.evaluation)
            reference_scores = _reference_scores(fold)
            fitted = fit_preprocessor(fold)
            train = transform(fitted, fold.fit, purpose="fit", role="fit")
            evaluation = transform(fitted, fold.evaluation, purpose="acceptance", role="acceptance")
            predictions = fit_authorized_candidates(train, evaluation, fitted)
            logistic = next(item for item in predictions if item.candidate == "logistic")
            mismatch = 0
            for row in fold.evaluation:
                rebuilt, _ = reconstruct_v4_features(
                    histories[row.policy_id],
                    __import__("datetime").datetime.fromisoformat(row.as_of.replace("Z", "+00:00")))
                mismatch += asdict(rebuilt) != asdict(row.features)
            folds.append({
                "fold": fold.name, "observations": len(targets),
                "unique_policies": len({row.policy_id for row in fold.evaluation}),
                "observable_oracle": _metrics(targets, oracle_scores),
                "reference_model": _metrics(targets, reference_scores),
                "candidate_logistic": _metrics(targets, logistic.probabilities),
                "driver_support": _driver_support(fold.evaluation),
                "transform_parity": {"mismatch_count": mismatch,
                                     "maximum_absolute_error": 0.0 if not mismatch else None},
            })
        variants[scenario] = {"artifact_id": corpus.provenance["artifact_id"],
                              "stream_set_id": corpus.provenance["stream_set_id"],
                              "maximum_monthly_terminal_hazard": maximum_hazard,
                              "folds": folds}
    return {"seed": seed, "status": "complete", "variants": variants,
            "matched_stream_set": variants["signal"]["stream_set_id"] == variants["matched_null"]["stream_set_id"],
            "protected_intermediates_committed": False,
            "future_acceptance_status": "not_materialized",
            "final_holdout_status": FINAL_HOLDOUT_STATUS}


def aggregate_qualification(items: Iterable[dict[str, Any]], readiness: dict[str, Any]) -> dict[str, Any]:
    seeds = tuple(items)
    if tuple(row.get("seed") for row in seeds) != DEVELOPMENT_SEEDS:
        raise ValueError("complete ordered R2-14 seed evidence is required")
    if any(row.get("status") != "complete" or not row.get("matched_stream_set") for row in seeds):
        raise ValueError("invalid R2-14 seed evidence")
    def seed_medians(scenario: str, family: str, metric: str) -> list[float]:
        return [median(fold[family][metric] for fold in row["variants"][scenario]["folds"])
                for row in seeds]
    oracle_auc = seed_medians("signal", "observable_oracle", "roc_auc")
    oracle_ap = seed_medians("signal", "observable_oracle", "average_precision_lift")
    oracle_brier = seed_medians("signal", "observable_oracle", "brier_skill")
    reference_auc = seed_medians("signal", "reference_model", "roc_auc")
    null_oracle = seed_medians("matched_null", "observable_oracle", "roc_auc")
    null_candidate = seed_medians("matched_null", "candidate_logistic", "roc_auc")
    support_counts = {name: {fold: 0 for fold in GOVERNED_FOLDS}
                      for name in seeds[0]["variants"]["signal"]["folds"][0]["driver_support"]}
    for row in seeds:
        for fold in row["variants"]["signal"]["folds"]:
            for name, passed in fold["driver_support"].items():
                support_counts[name][fold["fold"]] += int(passed)
    parity_mismatches = sum(fold["transform_parity"]["mismatch_count"]
                            for row in seeds for variant in row["variants"].values()
                            for fold in variant["folds"])
    max_hazard = max(variant["maximum_monthly_terminal_hazard"]
                     for row in seeds for variant in row["variants"].values())
    gates = {
        "observable_seed_recovery": sum(value >= 0.65 for value in oracle_auc) >= 16,
        "observable_aggregate_recovery": median(oracle_auc) >= 0.68,
        "oracle_probability_quality": median(oracle_ap) >= 0.10 and median(oracle_brier) > 0,
        "driver_support": all(count >= 16 for folds in support_counts.values() for count in folds.values()),
        "transform_parity": parity_mismatches == 0,
        "matched_null_behavior": 0.45 <= median(null_oracle) <= 0.55 and 0.45 <= median(null_candidate) <= 0.55,
        "reference_recovery": sum(value >= 0.65 for value in reference_auc) >= 16,
        "hazard_validity": math.isfinite(max_hazard) and max_hazard < 0.20,
        "structural_controls": readiness["readiness_decision"] == "authorized"
        and all(row["matched_stream_set"] for row in seeds),
    }
    decision = "qualified" if all(gates.values()) else "redesign"
    return {
        "phase": "R2-14", "issue": R2_14_ISSUE,
        "qualification_version": R2_14_QUALIFICATION_VERSION,
        "substrate_contract_version": "4.0.0", "acceptance_protocol_version": "3.0.0",
        "coefficient_registry_version": "2.0.0", "random_stream_registry_version": "2.0.0",
        "readiness": readiness, "seed_count": len(seeds), "seeds": list(DEVELOPMENT_SEEDS),
        "summary": {"observable_oracle_auc_pass_count": sum(value >= 0.65 for value in oracle_auc),
                    "median_observable_oracle_auc": median(oracle_auc),
                    "median_observable_oracle_ap_lift": median(oracle_ap),
                    "median_observable_oracle_brier_skill": median(oracle_brier),
                    "reference_model_auc_pass_count": sum(value >= 0.65 for value in reference_auc),
                    "median_matched_null_oracle_auc": median(null_oracle),
                    "median_matched_null_candidate_auc": median(null_candidate),
                    "parity_mismatch_count": parity_mismatches,
                    "maximum_monthly_terminal_hazard": max_hazard,
                    "driver_support_pass_counts": support_counts},
        "gates": {gate: {"status": "pass" if passed else "fail"} for gate, passed in gates.items()},
        "decision": decision, "r2_15_authorized": decision == "qualified",
        "seed_evidence": list(seeds), "protected_intermediates_committed": False,
        "future_acceptance_status": "not_materialized",
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
        "claim_boundary": "fictional_mechanism_development_qualification_only",
    }
