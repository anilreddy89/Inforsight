"""Fail-closed R2-14B readiness and governed stop evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

R2_14B_ISSUE = 78
R2_14B_DIAGNOSTIC_VERSION = "1.0.0"
DIAGNOSTIC_CONTRACT_VERSION = "1.0.0"
PREDECESSOR_MERGE_COMMIT = "52c03c8"

SPENT_V3_ACCEPTANCE_SEEDS = tuple(range(20261001, 20261021))
SPENT_V4_QUALIFICATION_SEEDS = tuple(range(20271101, 20271121))
RESERVED_V4_ACCEPTANCE_SEEDS = tuple(range(20271201, 20271221))
DEVELOPMENT_SEEDS = tuple(range(20280101, 20280121))
GOVERNED_FOLDS = ("fold_1", "fold_2", "fold_3")
GOVERNED_SCENARIOS = ("signal", "matched_null")
FINAL_HOLDOUT_STATUS = "not_materialized"
RESERVED_ACCEPTANCE_STATUS = "not_materialized"
MINIMUM_AGGREGATE_POLICIES = 10

HYPOTHESIS_IDS = (
    "H1_LOG_HAZARD_SPREAD",
    "H2_HORIZON_ATTENUATION",
    "H3_PROBABILITY_SCALE",
    "H4_REFERENCE_SPECIFICATION",
    "H5_HAZARD_TAIL",
    "H6_DESIGN_FEASIBILITY",
)

DIAGNOSTIC_IDS = (
    "D1_LINEAR_PREDICTOR_DISTRIBUTION",
    "D2_TERM_CONTRIBUTION_COVARIANCE",
    "D3_SIGNAL_VARIANCE_RATIO",
    "D4_CUMULATIVE_INCIDENCE_DECOMPOSITION",
    "D5_CAUSE_UNION_ORDERING",
    "D6_ATTENUATION_BY_FOLD",
    "D7_ORACLE_METRIC_DECOMPOSITION",
    "D8_RELIABILITY_SUMMARY",
    "D9_ORACLE_ORDERING",
    "D10_EXACT_SCORE_RECOVERY",
    "D11_EXACT_HAZARD_REFERENCE",
    "D12_CURRENT_REFERENCE_COMPARISON",
    "D13_HAZARD_QUANTILES",
    "D14_EXCEEDANCE_ATTRIBUTION",
    "D15_TAIL_SUPPORT",
    "D16_FROZEN_FEASIBILITY_SURFACE",
    "D17_SIMULTANEOUS_CONSTRAINT_STATUS",
)

IMMUTABLE_INPUTS = (
    "docs/adr/0008-authorize-post-v4-redesign-diagnostics.md",
    "docs/modeling/phase-02r-14a-v5-diagnostic-authorization-contract.md",
    "docs/modeling/phase-02r-v5-redesign-plan.md",
    "docs/experiments/phase-02r-14-v4-qualification-manifest.json",
    "docs/experiments/phase-02r-14-v4-qualification-report.md",
    "docs/experiments/phase-02r-14-v4-qualification-decision.md",
)

FEASIBILITY_GRID = tuple(
    {
        "cell_index": index,
        "public_coefficient_scale": scale,
        "frailty_standard_deviation": frailty,
        "lapse_intercept_delta": lapse,
        "surrender_intercept_delta": surrender,
    }
    for index, (scale, frailty, lapse, surrender) in enumerate(
        (s, f, l, u)
        for s in (1.0, 1.5, 2.0, 2.5, 3.0)
        for f in (0.00, 0.10, 0.20, 0.30)
        for l in (-0.50, -0.25, 0.00, 0.25)
        for u in (-0.50, -0.25, 0.00, 0.25)
    )
)


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return sha256(payload).hexdigest()


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
    return tuple(
        {"seed": seed, "scenario": scenario, "fold": fold}
        for seed in DEVELOPMENT_SEEDS
        for scenario in GOVERNED_SCENARIOS
        for fold in GOVERNED_FOLDS
    )


def evaluate_readiness(root: Path) -> tuple[ReadinessCheck, ...]:
    missing_inputs = [path for path in IMMUTABLE_INPUTS if not (root / path).is_file()]
    input_hashes = {
        path: sha256((root / path).read_bytes()).hexdigest()
        for path in IMMUTABLE_INPUTS
        if (root / path).is_file()
    }
    input_digest = canonical_sha256(input_hashes)
    checks = [
        ReadinessCheck(
            "immutable_inputs",
            "pass" if not missing_inputs else "fail",
            "stop",
            missing_inputs,
            [],
            input_digest,
        )
    ]

    domains = (
        SPENT_V3_ACCEPTANCE_SEEDS,
        SPENT_V4_QUALIFICATION_SEEDS,
        RESERVED_V4_ACCEPTANCE_SEEDS,
        DEVELOPMENT_SEEDS,
    )
    disjoint = len(set().union(*map(set, domains))) == 80 and all(
        len(domain) == 20 for domain in domains
    )
    checks.append(
        ReadinessCheck(
            "seed_domain_separation",
            "pass" if disjoint else "fail",
            "stop",
            [(domain[0], domain[-1], len(domain)) for domain in domains],
            "four_disjoint_20_seed_domains",
            input_digest,
        )
    )

    inventory = planned_inventory()
    inventory_ok = len(inventory) == 120 and len(
        {canonical_sha256(item) for item in inventory}
    ) == 120
    checks.append(
        ReadinessCheck(
            "complete_inventory",
            "pass" if inventory_ok else "fail",
            "redesign_required",
            len(inventory),
            120,
            canonical_sha256(inventory),
        )
    )

    contract_path = root / IMMUTABLE_INPUTS[1]
    contract_text = (
        contract_path.read_text(encoding="utf-8") if contract_path.is_file() else ""
    )
    required_contract_tokens = (
        "Contract version | `1.0.0`",
        "20280101..20280120",
        "20271201..20271220",
        "final_holdout: not_materialized",
        "exactly 320 cells",
        *HYPOTHESIS_IDS,
        *tuple(f"`{diagnostic_id}`" for diagnostic_id in DIAGNOSTIC_IDS),
    )
    missing_contract_tokens = [
        token for token in required_contract_tokens if token not in contract_text
    ]
    checks.append(
        ReadinessCheck(
            "contract_authority",
            "pass" if not missing_contract_tokens else "fail",
            "stop",
            missing_contract_tokens,
            [],
            canonical_sha256(required_contract_tokens),
        )
    )

    # ADR 0008 requires all material interpretation rules before result access.
    # Contract 1.0.0 never defines supported/rejected thresholds for H1-H5.
    disposition_rule_tokens = tuple(
        f"{hypothesis} supported when" for hypothesis in HYPOTHESIS_IDS[:-1]
    ) + tuple(
        f"{hypothesis} rejected when" for hypothesis in HYPOTHESIS_IDS[:-1]
    )
    missing_disposition_rules = [
        token for token in disposition_rule_tokens if token not in contract_text
    ]
    checks.append(
        ReadinessCheck(
            "mechanical_hypothesis_disposition_rules",
            "pass" if not missing_disposition_rules else "fail",
            "stop",
            missing_disposition_rules,
            [],
            canonical_sha256(disposition_rule_tokens),
        )
    )
    checks.append(
        ReadinessCheck(
            "predecessor_merge_commit",
            "pass" if PREDECESSOR_MERGE_COMMIT == "52c03c8" else "fail",
            "stop",
            PREDECESSOR_MERGE_COMMIT,
            "52c03c8",
            input_digest,
        )
    )
    checks.append(
        ReadinessCheck(
            "feasibility_grid_frozen",
            "pass" if len(FEASIBILITY_GRID) == 320 else "fail",
            "stop",
            len(FEASIBILITY_GRID),
            320,
            canonical_sha256(FEASIBILITY_GRID),
        )
    )
    checks.append(
        ReadinessCheck(
            "holdout_and_reserved_absence",
            "pass",
            "stop",
            {
                "reserved_acceptance": RESERVED_ACCEPTANCE_STATUS,
                "final_holdout": FINAL_HOLDOUT_STATUS,
            },
            {
                "reserved_acceptance": "not_materialized",
                "final_holdout": "not_materialized",
            },
            input_digest,
        )
    )
    return tuple(checks)


def readiness_decision(checks: Iterable[ReadinessCheck]) -> str:
    failures = tuple(check for check in checks if check.status == "fail")
    if any(check.failure_classification == "stop" for check in failures):
        return "stop"
    return "redesign_required" if failures else "authorized"


def build_readiness_manifest(root: Path) -> dict[str, Any]:
    checks = evaluate_readiness(root)
    decision = readiness_decision(checks)
    inventory = planned_inventory()
    return {
        "phase": "R2-14B",
        "issue": R2_14B_ISSUE,
        "diagnostic_version": R2_14B_DIAGNOSTIC_VERSION,
        "contract_version": DIAGNOSTIC_CONTRACT_VERSION,
        "predecessor_merge": PREDECESSOR_MERGE_COMMIT,
        "readiness_decision": decision,
        "result_producing_execution_authorized": decision == "authorized",
        "planned_inventory": {
            "development_seeds": list(DEVELOPMENT_SEEDS),
            "scenarios": list(GOVERNED_SCENARIOS),
            "folds": list(GOVERNED_FOLDS),
            "units": len(inventory),
            "sha256": canonical_sha256(inventory),
        },
        "registered_hypotheses": list(HYPOTHESIS_IDS),
        "registered_diagnostics": list(DIAGNOSTIC_IDS),
        "feasibility_surface_size": len(FEASIBILITY_GRID),
        "checks": [check.to_dict() for check in checks],
        "reserved_acceptance_status": RESERVED_ACCEPTANCE_STATUS,
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
    }


def build_governed_stop_manifest(readiness: dict[str, Any]) -> dict[str, Any]:
    if readiness.get("readiness_decision") != "stop":
        raise ValueError("a governed stop manifest requires a readiness stop")
    return {
        "phase": "R2-14B",
        "issue": R2_14B_ISSUE,
        "diagnostic_version": R2_14B_DIAGNOSTIC_VERSION,
        "contract_version": DIAGNOSTIC_CONTRACT_VERSION,
        "predecessor_merge": PREDECESSOR_MERGE_COMMIT,
        "readiness": readiness,
        "execution_decision": "stop",
        "result_producing_execution_authorized": False,
        "planned_inventory": readiness["planned_inventory"],
        "executed_inventory": {
            "seeds": 0,
            "scenarios": 0,
            "folds": 0,
            "units": 0,
            "diagnostics": 0,
            "feasibility_cells": 0,
        },
        "governed_failures": [
            {
                "diagnostic_id": diagnostic_id,
                "status": "not_executed",
                "reason": "readiness_stop_before_result_access",
            }
            for diagnostic_id in DIAGNOSTIC_IDS
        ],
        "summary": {
            "feasibility_surface_cells_evaluated": 0,
            "feasible_cell_count": 0,
            "feasibility_status": "unresolved",
        },
        "hypothesis_dispositions": {
            hypothesis_id: "unresolved" for hypothesis_id in HYPOTHESIS_IDS
        },
        "selected_response": "stop_contract_not_executable",
        "protected_intermediates_committed": False,
        "reserved_acceptance_status": RESERVED_ACCEPTANCE_STATUS,
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
        "r2_14c_authorized": False,
    }


def compute_distribution(values: Sequence[float]) -> dict[str, Any]:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        raise ValueError("distribution requires at least one finite value")
    array = np.asarray(finite, dtype=float)
    levels = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
    quantiles = np.quantile(array, levels, method="linear")
    return {
        "count": len(values),
        "finite_count": len(finite),
        "mean": float(np.mean(array)),
        "std": float(np.std(array, ddof=0)),
        "min": float(np.min(array)),
        "quantiles": {
            f"{level:.2f}": float(value)
            for level, value in zip(levels, quantiles, strict=True)
        },
    }


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


def render_artifacts(aggregate: dict[str, Any]) -> dict[str, bytes]:
    if aggregate.get("execution_decision") != "stop":
        raise ValueError("R2-14B only has authority to render its readiness stop")
    manifest = (
        json.dumps(aggregate, allow_nan=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    failed_checks = [
        check["check_id"]
        for check in aggregate["readiness"]["checks"]
        if check["status"] == "fail"
    ]
    report = "\n".join(
        [
            "# Phase 2R.14B v5 Redesign Diagnostic Report",
            "",
            "Issue: #78",
            "Phase: R2-14B",
            "Predecessor merge: `52c03c8`",
            "Diagnostic contract: `1.0.0`",
            "",
            "## Readiness Decision",
            "",
            "Result-producing execution stopped before authorized diagnostic access.",
            "",
            "Failed readiness checks: "
            + ", ".join(f"`{check_id}`" for check_id in failed_checks)
            + ".",
            "",
            "Contract `1.0.0` names the three dispositions but does not freeze the H1-H5 thresholds that mechanically select among them. ADR 0008 requires those rules before result access.",
            "",
            "## Inventory Accounting",
            "",
            "| Measure | Planned | Executed |",
            "| --- | ---: | ---: |",
            f"| Inventory units | `{aggregate['planned_inventory']['units']}` | `0` |",
            "| Registered diagnostics | `17` | `0` |",
            "| D16 feasibility cells | `320` | `0` |",
            "",
            "All diagnostics `D1` through `D17` record `readiness_stop_before_result_access`. All hypothesis dispositions remain `unresolved`.",
            "",
            "## Decision Boundary",
            "",
            "Selected response: `stop_contract_not_executable`.",
            "",
            "R2-14C remains blocked. Reserved acceptance seeds (`20271201..20271220`) and the final holdout remain `not_materialized`.",
            "",
        ]
    ).encode("utf-8")
    disposition = "\n".join(
        [
            "# Phase 2R.14B v5 Redesign Hypothesis Disposition",
            "",
            "R2-14B stopped at readiness because contract `1.0.0` does not freeze mechanical H1-H5 disposition thresholds.",
            "",
            *[f"- `{hypothesis_id}`: `unresolved`" for hypothesis_id in HYPOTHESIS_IDS],
            "",
            "Diagnostics `D1` through `D17` were not authorized for result-producing execution. R2-14C remains blocked; reserved acceptance and final holdout remain `not_materialized`.",
            "",
        ]
    ).encode("utf-8")
    return {"manifest": manifest, "report": report, "disposition": disposition}
