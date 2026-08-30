"""Fail-closed R2-07 statistical-acceptance readiness and decision evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from .v2_config import (
    V2_ACCEPTANCE_PROTOCOL_VERSION,
    V2_FINAL_HOLDOUT_STATUS,
    V2_RANDOM_DOMAINS,
    V2CorpusConfig,
    v2_domain_seed,
)
from .v2_corpus import generate_v2_corpus


R2_ACCEPTANCE_EXECUTION_VERSION = "1.0.0"
R2_ACCEPTANCE_ARTIFACT_VERSION = "1.0.0"
R2_ACCEPTANCE_SEEDS = tuple(range(20260901, 20260921))
R2_ACCEPTANCE_FOLDS = ("fold_1", "fold_2", "fold_3")
FINAL_HOLDOUT_STATUS = "not_materialized"
NOT_RUN_STATUS = "not_run_protocol_not_executable"

_LINEAGE_PATHS = (
    "docs/modeling/phase-02r-04-statistical-acceptance-protocol.md",
    "docs/modeling/phase-02r-04-v2-statistical-simulator-and-observation-contract.md",
    "docs/modeling/phase-02r-06-v2-evaluation-pipeline-contract.md",
    "docs/modeling/phase-02r-07-v2-statistical-acceptance-execution-contract.md",
    "docs/modeling/phase-02r-06-v2-feature-dictionary.json",
    "docs/experiments/phase-02r-05-v2-corpus-manifest.json",
    "docs/experiments/phase-02r-06-v2-split-manifest.json",
    "docs/experiments/phase-02r-06-v2-feature-pipeline-manifest.json",
    "docs/experiments/phase-02r-06-v2-feature-diagnostics-manifest.json",
    "docs/experiments/phase-02r-06-v2-baseline-comparison-manifest.json",
    "simulator/src/inforsight_simulator/v2_config.py",
    "simulator/src/inforsight_simulator/v2_corpus.py",
    "simulator/src/inforsight_simulator/v2_acceptance.py",
    "scripts/run_v2_statistical_acceptance.py",
)


@dataclass(frozen=True)
class AcceptanceRuleResult:
    """One deterministic readiness rule and its decision consequence."""

    rule_id: str
    expected: Any
    observed: Any
    status: str
    failure_classification: str
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in ("pass", "fail"):
            raise ValueError("acceptance rule status must be pass or fail")
        if self.failure_classification not in ("redesign", "stop"):
            raise ValueError("failure classification must be redesign or stop")
        if not self.rule_id or not self.evidence:
            raise ValueError("acceptance rule requires an identifier and evidence")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"evidence": list(self.evidence)}


def aggregate_decision(results: Iterable[AcceptanceRuleResult]) -> str:
    """Apply the protocol's stop-over-redesign-over-proceed precedence."""

    items = tuple(results)
    if not items:
        return "redesign"
    failures = tuple(item for item in items if item.status == "fail")
    if any(item.failure_classification == "stop" for item in failures):
        return "stop"
    if failures:
        return "redesign"
    return "proceed"


def evaluate_readiness(root: Path) -> tuple[AcceptanceRuleResult, ...]:
    """Evaluate frozen prerequisites without fitting or scoring a model."""

    baseline = _load_json(
        root / "docs/experiments/phase-02r-06-v2-baseline-comparison-manifest.json"
    )
    diagnostic = _load_json(
        root / "docs/experiments/phase-02r-06-v2-feature-diagnostics-manifest.json"
    )
    corpus = _load_json(
        root / "docs/experiments/phase-02r-05-v2-corpus-manifest.json"
    )
    split = _load_json(
        root / "docs/experiments/phase-02r-06-v2-split-manifest.json"
    )
    feature = _load_json(
        root / "docs/experiments/phase-02r-06-v2-feature-pipeline-manifest.json"
    )

    selected = baseline.get("selected_candidate")
    selection_rule = baseline.get("selection_rule")
    selected_ok = (
        selected in ("logistic", "xgboost")
        and isinstance(selection_rule, str)
        and bool(selection_rule)
    )
    selected_observed: Any = selected
    if not selected_ok:
        selected_observed = {
            "selected_candidate": selected,
            "available_candidates": [
                name for name in ("logistic", "xgboost") if name in baseline
            ],
            "selection_rule": selection_rule,
        }

    groups = diagnostic.get("source_feature_groups")
    group_registry = {
        "source_feature_groups": groups,
        "strongest_driver_group": diagnostic.get("strongest_driver_group"),
        "zero_effect_group": diagnostic.get("zero_effect_group"),
        "expected_directions": diagnostic.get("expected_directions"),
    }
    groups_ok = (
        isinstance(groups, dict)
        and set(groups)
        == {"static", "recent_payment", "rolling_history", "service_notice", "missingness"}
        and bool(group_registry["strongest_driver_group"])
        and bool(group_registry["zero_effect_group"])
        and isinstance(group_registry["expected_directions"], dict)
    )

    configuration = corpus.get("provenance", {}).get("configuration", {})
    coefficient_registry = configuration.get("coefficient_registry")
    coefficient_ok = isinstance(coefficient_registry, dict) and bool(coefficient_registry)

    base = V2CorpusConfig(seed=R2_ACCEPTANCE_SEEDS[0], run_namespace="r2-07-readiness")
    null = replace(base, signal_mode="null_signal")
    null_matching = tuple(
        domain
        for domain in V2_RANDOM_DOMAINS
        if v2_domain_seed(base, domain, "paired-audit")
        == v2_domain_seed(null, domain, "paired-audit")
    )
    null_ok = set(null_matching) == set(V2_RANDOM_DOMAINS)

    moderate = replace(base, drift_scenario="moderate_drift")
    doubled_missingness = replace(
        base, mcar_missingness_rate=base.mcar_missingness_rate * 2.0
    )
    invariant_domains = (
        "allocation",
        "static_attributes",
        "frailty",
        "terminal_outcome",
        "event_censoring",
        "correction",
    )
    moderate_matching = tuple(
        domain
        for domain in invariant_domains
        if v2_domain_seed(base, domain, "paired-audit")
        == v2_domain_seed(moderate, domain, "paired-audit")
    )
    missingness_matching = tuple(
        domain
        for domain in invariant_domains
        if v2_domain_seed(base, domain, "paired-audit")
        == v2_domain_seed(doubled_missingness, domain, "paired-audit")
    )
    stress_ok = (
        set(moderate_matching) == set(invariant_domains)
        and set(missingness_matching) == set(invariant_domains)
    )

    shuffle_ok = "label_shuffle" in V2_RANDOM_DOMAINS

    fold_support = []
    for item in split.get("folds", []):
        if item.get("name") not in R2_ACCEPTANCE_FOLDS:
            continue
        membership = item.get("evaluation", {})
        observed = {
            "fold": item.get("name"),
            "observations": membership.get("observations"),
            "positive": membership.get("positive"),
            "negative": membership.get("negative"),
        }
        observed["passes"] = (
            isinstance(observed["observations"], int)
            and observed["observations"] >= 500
            and isinstance(observed["positive"], int)
            and observed["positive"] >= 50
            and isinstance(observed["negative"], int)
            and observed["negative"] >= 50
        )
        fold_support.append(observed)
    fold_support_ok = len(fold_support) == len(R2_ACCEPTANCE_FOLDS) and all(
        item["passes"] for item in fold_support
    )

    dual_time = _dual_time_visibility_audit()
    dual_time_ok = dual_time["observations_with_post_cutoff_ingestion_features"] == 0

    holdout_values = {
        "configuration": V2_FINAL_HOLDOUT_STATUS,
        "corpus_manifest": corpus.get("final_holdout_status"),
        "split_manifest": split.get("final_holdout_status"),
        "feature_manifest": feature.get("final_holdout_status"),
        "diagnostic_manifest": diagnostic.get("final_holdout_status"),
        "baseline_manifest": baseline.get("final_holdout_status"),
    }
    holdout_ok = set(holdout_values.values()) == {FINAL_HOLDOUT_STATUS}

    return (
        _result(
            "READINESS-SELECTED-CANDIDATE",
            "one of logistic or xgboost plus a frozen selection rule",
            selected_observed,
            selected_ok,
            "redesign",
            "docs/experiments/phase-02r-06-v2-baseline-comparison-manifest.json",
        ),
        _result(
            "READINESS-DRIVER-GROUPS",
            "five frozen macro groups, strongest group, zero-effect group, and directions",
            group_registry,
            groups_ok,
            "redesign",
            "docs/experiments/phase-02r-06-v2-feature-diagnostics-manifest.json",
        ),
        _result(
            "READINESS-COEFFICIENT-REGISTRY",
            "non-empty coefficient_registry in canonical v2 configuration",
            coefficient_registry,
            coefficient_ok,
            "redesign",
            "docs/experiments/phase-02r-05-v2-corpus-manifest.json",
        ),
        _result(
            "READINESS-MATCHED-NULL-STREAMS",
            {"matching_domains": list(V2_RANDOM_DOMAINS)},
            {"matching_domains": list(null_matching), "domain_count": len(V2_RANDOM_DOMAINS)},
            null_ok,
            "redesign",
            "simulator/src/inforsight_simulator/v2_config.py",
        ),
        _result(
            "READINESS-MATCHED-STRESS-STREAMS",
            {"matching_invariant_domains": list(invariant_domains)},
            {
                "moderate_drift_matching_domains": list(moderate_matching),
                "doubled_missingness_matching_domains": list(missingness_matching),
            },
            stress_ok,
            "redesign",
            "simulator/src/inforsight_simulator/v2_config.py",
        ),
        _result(
            "READINESS-SHUFFLE-DOMAIN",
            "label_shuffle present in the frozen random-domain registry",
            {"present": shuffle_ok, "registered_domains": list(V2_RANDOM_DOMAINS)},
            shuffle_ok,
            "redesign",
            "simulator/src/inforsight_simulator/v2_config.py",
        ),
        _result(
            "READINESS-FOLD-SUPPORT",
            {"observations_min": 500, "positive_min": 50, "negative_min": 50},
            fold_support,
            fold_support_ok,
            "redesign",
            "docs/experiments/phase-02r-06-v2-split-manifest.json",
        ),
        _result(
            "READINESS-DUAL-TIME-VISIBILITY",
            {"observations_with_post_cutoff_ingestion_features": 0},
            dual_time,
            dual_time_ok,
            "stop",
            "simulator/src/inforsight_simulator/v2_corpus.py",
        ),
        _result(
            "READINESS-HOLDOUT-ABSENCE",
            {"all_statuses": FINAL_HOLDOUT_STATUS},
            holdout_values,
            holdout_ok,
            "stop",
            "docs/experiments/phase-02r-05-v2-corpus-manifest.json",
            "docs/experiments/phase-02r-06-v2-split-manifest.json",
            "docs/experiments/phase-02r-06-v2-feature-pipeline-manifest.json",
            "docs/experiments/phase-02r-06-v2-feature-diagnostics-manifest.json",
            "docs/experiments/phase-02r-06-v2-baseline-comparison-manifest.json",
        ),
    )


def build_readiness_manifest(root: Path) -> dict[str, Any]:
    """Build deterministic R2-07 stop evidence without acceptance scoring."""

    results = evaluate_readiness(root)
    decision = aggregate_decision(results)
    blocked_by = [item.rule_id for item in results if item.status == "fail"]
    runs = [
        {
            "seed": seed,
            "signal_status": NOT_RUN_STATUS,
            "null_status": NOT_RUN_STATUS,
            "folds": [
                {"name": fold, "status": NOT_RUN_STATUS}
                for fold in R2_ACCEPTANCE_FOLDS
            ],
            "blocked_by": blocked_by,
        }
        for seed in R2_ACCEPTANCE_SEEDS
    ]
    return {
        "artifact_version": R2_ACCEPTANCE_ARTIFACT_VERSION,
        "phase": "R2-07",
        "execution_contract_version": R2_ACCEPTANCE_EXECUTION_VERSION,
        "acceptance_protocol_version": V2_ACCEPTANCE_PROTOCOL_VERSION,
        "execution_mode": "readiness_preflight_only",
        "acceptance_results_generated": False,
        "model_fit_performed": False,
        "prediction_performed": False,
        "bootstrap_performed": False,
        "decision": decision,
        "decision_precedence": ["stop", "redesign", "proceed"],
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
        "lineage": {
            path: _file_digest(root / path)
            for path in _LINEAGE_PATHS
        },
        "readiness_rules": [item.to_dict() for item in results],
        "planned_replications": runs,
        "protocol_sections_not_evaluated": [
            "negative_controls",
            "signal_recovery",
            "calibration_sanity",
            "learning_behavior",
            "driver_ablation",
            "robustness",
            "temporal_stability",
        ],
        "limitation_dispositions": {
            "LIM-002-001": "remains_scheduled_no_closure_evidence",
            "LIM-002-002": "remains_scheduled_no_closure_evidence",
            "LIM-002-003": "remains_scheduled_final_holdout_workflow_not_exercised",
            "LIM-002-004": "open_blocking_corrective_issue_required",
        },
        "downstream_status": {
            "P2-08": "paused",
            "P2-09": "paused",
        },
        "claim_boundary": "protocol_readiness_and_synthetic_pipeline_correctness_only",
        "reproduction_command": "python3 scripts/run_v2_statistical_acceptance.py --check",
    }


def _dual_time_visibility_audit() -> dict[str, int]:
    config = V2CorpusConfig(
        seed=R2_ACCEPTANCE_SEEDS[0],
        run_namespace="r2-07-readiness-audit",
        policy_count=5,
        cohort_count=1,
        policies_per_cohort=5,
    )
    corpus = generate_v2_corpus(config)
    histories = {history[0]["policy_id"]: history for history in corpus.histories}
    invisible_events = 0
    leaked_observations: set[str] = set()
    for observation in corpus.observations:
        cutoff = _time(observation.as_of)
        for event in histories[observation.policy_id]:
            if event["event_type"] != "behavior.snapshot":
                continue
            if not (event["effective_at"] <= observation.as_of < event["ingested_at"]):
                continue
            if (cutoff - _time(event["effective_at"])).days != 5:
                continue
            invisible_events += 1
            payload = event["payload"]
            expected_contact = (
                "missing"
                if payload["contact_category"] is None
                else payload["contact_category"]
            )
            if (
                event["event_id"] not in observation.visible_event_ids
                and observation.features.recent_failed_payment_count == payload["failed_payment_count"]
                and observation.features.recent_retry_count == payload["retry_count"]
                and observation.features.recent_recovery_count == payload["recovery_count"]
                and observation.features.notice_category == payload["notice_category"]
                and observation.features.contact_category == expected_contact
            ):
                leaked_observations.add(observation.observation_id)
    return {
        "audit_policies": config.policy_count,
        "audit_observations": len(corpus.observations),
        "post_cutoff_ingestion_behavior_events": invisible_events,
        "observations_with_post_cutoff_ingestion_features": len(leaked_observations),
    }


def _result(
    rule_id: str,
    expected: Any,
    observed: Any,
    passed: bool,
    failure_classification: str,
    *evidence: str,
) -> AcceptanceRuleResult:
    return AcceptanceRuleResult(
        rule_id=rule_id,
        expected=expected,
        observed=observed,
        status="pass" if passed else "fail",
        failure_classification=failure_classification,
        evidence=tuple(evidence),
    )


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _file_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
