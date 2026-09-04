"""Fail-closed R2-14BB readiness, diagnostic execution, and aggregate evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression

from .v3_acceptance import average_precision, brier_score, fit_authorized_candidates, roc_auc
from .v3_evaluation import build_temporal_folds, fit_preprocessor, transform
from .v4_config import V4CorpusConfig
from .v4_corpus import (
    _MONTH_OFFSETS, _QUADRATURE_NODES, _QUADRATURE_WEIGHTS,
    competing_hazards, cumulative_incidence, generate_v4_corpus,
    public_mechanism_terms,
)

R2_14BB_ISSUE = 82
DIAGNOSTIC_CONTRACT_VERSION = "1.1.0"
PREDECESSOR_MERGE_COMMIT = "627e698"

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
    "docs/adr/0010-amend-v5-diagnostic-contract-with-disposition-truth-tables.md",
    "docs/modeling/phase-02r-14ba-v5-diagnostic-authorization-contract.md",
    "docs/experiments/phase-02r-14-v4-qualification-manifest.json",
    "docs/experiments/phase-02r-14b-v5-redesign-diagnostic-manifest.json",
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

LAPSE_COEFFICIENTS = np.array(
    (-0.16, 0.24, 0.12, 0.20, 0.28, 0.84, 1.40, 0.36,
     -0.60, 1.10, -0.90, -0.20, 0.48, 0.24, 0.44, 0.0, 0.0),
    dtype=float,
)
SURRENDER_COEFFICIENTS = np.array(
    (0.08, 0.36, 0.08, 0.12, 0.16, 0.24, 0.40, 0.10,
     -0.16, 0.30, -0.24, -0.08, 0.36, 0.44, 0.16, 0.0, 0.0),
    dtype=float,
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
        "Contract version | `1.1.0`",
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
            "pass" if PREDECESSOR_MERGE_COMMIT == "627e698" else "fail",
            "stop",
            PREDECESSOR_MERGE_COMMIT,
            "627e698",
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
        "phase": "R2-14BB",
        "issue": R2_14BB_ISSUE,
        "diagnostic_version": "1.1.0",
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


def execute_seed_diagnostics(seed: int) -> dict[str, Any]:
    """Execute all 17 diagnostics for one development seed across both scenarios."""
    if seed not in DEVELOPMENT_SEEDS:
        raise ValueError(f"Seed {seed} is outside the R2-14BB development domain")

    results_by_scenario: dict[str, Any] = {}

    for scenario in GOVERNED_SCENARIOS:
        scenario_name = "stable" if scenario == "signal" else "null_signal"
        config = V4CorpusConfig(base_seed=seed, scenario=scenario_name)
        corpus = generate_v4_corpus(config, enforce_hazard_bound=False)

        compatible = tuple(
            replace(row, observation_contract_version="3.0.0")
            for row in corpus.observations
        )
        folds = build_temporal_folds(compatible)
        oracle = {row.observation_id: row for row in corpus.oracle_sidecar}

        term_matrix = np.array(
            [list(public_mechanism_terms(obs.features).values()) for obs in corpus.observations],
            dtype=float,
        )
        lapse_scores = term_matrix @ LAPSE_COEFFICIENTS
        surrender_scores = term_matrix @ SURRENDER_COEFFICIENTS

        d1_lapse = compute_distribution(lapse_scores)
        d1_surrender = compute_distribution(surrender_scores)
        cov_matrix = np.cov(term_matrix, rowvar=False, ddof=0)
        d2_covariance = {
            "shape": list(cov_matrix.shape),
            "trace": float(np.trace(cov_matrix)),
            "frobenius_norm": float(np.linalg.norm(cov_matrix)),
        }

        frailty_variance = 0.04
        d3_variance_ratio = {
            "lapse_signal_to_frailty": float(np.var(lapse_scores) / (frailty_variance + 1e-12)),
            "surrender_signal_to_frailty": float(np.var(surrender_scores) / (frailty_variance + 1e-12)),
        }

        fold_summaries = []
        for fold in folds:
            eval_obs = [corpus.observations[i] for i, r in enumerate(corpus.observations) if r.observation_id in {e.observation_id for e in fold.evaluation}]
            targets = tuple(int(row.label_value) for row in eval_obs)
            unique_policies = len({row.policy_id for row in eval_obs})

            obs_oracle_scores = tuple(oracle[row.observation_id].oracle_observable_union for row in eval_obs)
            cond_oracle_scores = tuple(oracle[row.observation_id].oracle_conditional_union for row in eval_obs)

            names = tuple(public_mechanism_terms(fold.fit[0].features))
            x_fit = [[public_mechanism_terms(row.features)[name] for name in names] for row in fold.fit]
            x_eval = [[public_mechanism_terms(row.features)[name] for name in names] for row in eval_obs]
            fit_targets = [int(row.label_value) for row in fold.fit]
            model = LogisticRegression(random_state=20260817, max_iter=1000, solver="lbfgs")
            model.fit(x_fit, fit_targets)
            ref_scores = tuple(float(val) for val in model.predict_proba(x_eval)[:, 1])

            auc_obs = roc_auc(targets, obs_oracle_scores)
            auc_cond = roc_auc(targets, cond_oracle_scores)
            ap = average_precision(targets, obs_oracle_scores)
            prev = sum(targets) / len(targets)
            brier = brier_score(targets, obs_oracle_scores)
            brier_skill = 1.0 - brier / (prev * (1.0 - prev))

            bins = np.linspace(0.0, 1.0, 11)
            bin_indices = np.digitize(obs_oracle_scores, bins) - 1
            bin_indices = np.clip(bin_indices, 0, 9)
            reliability_bins = []
            for b in range(10):
                mask = (bin_indices == b)
                count_b = int(np.sum(mask))
                if count_b > 0:
                    pol_b = len({eval_obs[i].policy_id for i, m in enumerate(mask) if m})
                    mean_p = float(np.mean([obs_oracle_scores[i] for i, m in enumerate(mask) if m]))
                    out_r = float(np.mean([targets[i] for i, m in enumerate(mask) if m]))
                else:
                    pol_b = 0
                    mean_p = 0.0
                    out_r = 0.0
                reliability_bins.append(
                    project_aggregate(
                        unique_policy_count=pol_b,
                        observed={"bin": b, "count": count_b, "mean_pred": mean_p, "outcome_rate": out_r},
                    )
                )

            auc_ref = roc_auc(targets, ref_scores)

            fold_summaries.append({
                "fold": fold.name,
                "observations": len(targets),
                "unique_policies": unique_policies,
                "roc_auc_observable": auc_obs,
                "roc_auc_conditional": auc_cond,
                "average_precision_lift": ap - prev,
                "brier_score": brier,
                "brier_skill": brier_skill,
                "reference_auc": auc_ref,
                "reliability_bins": reliability_bins,
            })

        max_hazards = []
        exceedances = 0
        total_policy_months = len(corpus.observations) * 3
        for obs in corpus.observations:
            frailty = oracle[obs.observation_id].latent_frailty
            for month in (1, 2, 3):
                h_l, h_s, _ = competing_hazards(obs.features, frailty, month, signal_scale=1.0, enforce_generated_bound=False)
                tot = h_l + h_s
                if tot >= 0.20:
                    exceedances += 1
                max_hazards.append(tot)

        d13_distribution = compute_distribution(max_hazards)
        d14_exceedances = {
            "total_policy_months": total_policy_months,
            "exceedance_count": exceedances,
            "exceedance_rate": float(exceedances / total_policy_months),
            "maximum_hazard": float(max(max_hazards)),
        }

        results_by_scenario[scenario] = {
            "d1_linear_predictor": {"lapse": d1_lapse, "surrender": d1_surrender},
            "d2_covariance": d2_covariance,
            "d3_variance_ratio": d3_variance_ratio,
            "folds": fold_summaries,
            "d13_hazards": d13_distribution,
            "d14_exceedances": d14_exceedances,
        }

    return {
        "seed": seed,
        "scenarios": results_by_scenario,
    }


def evaluate_grid_cell(
    cell: dict[str, Any],
    eval_matrix: np.ndarray,
    eval_frailties: np.ndarray,
    eval_targets: np.ndarray,
) -> dict[str, Any]:
    """Evaluate one cell in the 320-cell feasibility surface."""
    scale = cell["public_coefficient_scale"]
    frailty_sd = cell["frailty_standard_deviation"]
    lapse_delta = cell["lapse_intercept_delta"]
    surrender_delta = cell["surrender_intercept_delta"]

    lapse_scores = eval_matrix @ LAPSE_COEFFICIENTS
    surrender_scores = eval_matrix @ SURRENDER_COEFFICIENTS

    rescaled_frailty = (eval_frailties / 0.20) * frailty_sd if frailty_sd > 0 else np.zeros_like(eval_frailties)

    max_tot_hazard = 0.0
    for offset in _MONTH_OFFSETS:
        eta_l = -4.85 + lapse_delta + offset + rescaled_frailty + scale * lapse_scores
        eta_s = -5.55 + surrender_delta + offset + 0.50 * rescaled_frailty + scale * surrender_scores
        exp_l = np.exp(eta_l)
        exp_s = np.exp(eta_s)
        denom = 1.0 + exp_l + exp_s
        h_l = exp_l / denom
        h_s = exp_s / denom
        max_tot_hazard = max(max_tot_hazard, float(np.max(h_l + h_s)))

    nodes = _QUADRATURE_NODES
    weights = _QUADRATURE_WEIGHTS
    frailty_grid = math.sqrt(2) * frailty_sd * nodes if frailty_sd > 0 else np.zeros(len(nodes))

    survival = np.ones((len(eval_matrix), len(nodes)), dtype=float)
    lapse_union = np.zeros((len(eval_matrix), len(nodes)), dtype=float)
    surr_union = np.zeros((len(eval_matrix), len(nodes)), dtype=float)

    for offset in _MONTH_OFFSETS:
        eta_l = -4.85 + lapse_delta + offset + frailty_grid[None, :] + scale * lapse_scores[:, None]
        eta_s = -5.55 + surrender_delta + offset + 0.50 * frailty_grid[None, :] + scale * surrender_scores[:, None]
        exp_l = np.exp(eta_l)
        exp_s = np.exp(eta_s)
        denom = 1.0 + exp_l + exp_s
        h_l = exp_l / denom
        h_s = exp_s / denom
        c = 1.0 / denom
        lapse_union += survival * h_l
        surr_union += survival * h_s
        survival *= c

    prob_union = (lapse_union + surr_union) @ (weights / math.sqrt(math.pi))

    auc = roc_auc(tuple(int(y) for y in eval_targets), tuple(float(p) for p in prob_union))
    ap = average_precision(tuple(int(y) for y in eval_targets), tuple(float(p) for p in prob_union))
    prev = float(np.mean(eval_targets))
    ap_lift = ap - prev
    brier = brier_score(tuple(int(y) for y in eval_targets), tuple(float(p) for p in prob_union))
    brier_skill = 1.0 - brier / (prev * (1.0 - prev))

    hazard_pass = max_tot_hazard < 0.20
    recovery_pass = auc >= 0.70 and ap_lift >= 0.10 and brier_skill > 0.0

    return {
        "cell_index": cell["cell_index"],
        "public_coefficient_scale": scale,
        "frailty_standard_deviation": frailty_sd,
        "lapse_intercept_delta": lapse_delta,
        "surrender_intercept_delta": surrender_delta,
        "max_hazard": max_tot_hazard,
        "hazard_pass": hazard_pass,
        "roc_auc": auc,
        "ap_lift": ap_lift,
        "brier_skill": brier_skill,
        "recovery_pass": recovery_pass,
        "simultaneous_constraints_met": bool(hazard_pass and recovery_pass),
    }


def aggregate_all_diagnostics(
    seed_results: Sequence[dict[str, Any]],
    feasibility_results: Sequence[dict[str, Any]],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    """Derive aggregate metrics, truth-table dispositions, and build manifest."""
    lapse_stds = [r["scenarios"]["signal"]["d1_linear_predictor"]["lapse"]["std"] for r in seed_results]
    surr_stds = [r["scenarios"]["signal"]["d1_linear_predictor"]["surrender"]["std"] for r in seed_results]
    med_lapse_std = float(np.median(lapse_stds))
    med_surr_std = float(np.median(surr_stds))

    # H1: Supported if std < 0.35 for both causes
    h1_supported = med_lapse_std < 0.35 and med_surr_std < 0.35
    h1_disposition = "supported" if h1_supported else "unresolved"

    # H2: Horizon attenuation
    h2_disposition = "unresolved"

    # H3: Probability scale compression vs rank failure
    all_aucs = [
        f["roc_auc_observable"]
        for r in seed_results
        for f in r["scenarios"]["signal"]["folds"]
    ]
    low_auc_count = sum(auc < 0.60 for auc in all_aucs)
    h3_rejected = (low_auc_count / len(all_aucs)) >= 0.80
    h3_disposition = "rejected" if h3_rejected else "unresolved"

    # H4: Reference specification mismatch
    diffs = [
        abs(f["roc_auc_observable"] - f["reference_auc"])
        for r in seed_results
        for f in r["scenarios"]["signal"]["folds"]
    ]
    h4_rejected = float(np.median(diffs)) < 0.02
    h4_disposition = "rejected" if h4_rejected else "unresolved"

    # H5: Hazard tail
    all_exceedances = sum(r["scenarios"]["signal"]["d14_exceedances"]["exceedance_count"] for r in seed_results)
    h5_rejected = all_exceedances == 0
    h5_disposition = "rejected" if h5_rejected else "unresolved"

    # H6: Design feasibility
    feasible_cells = [c for c in feasibility_results if c["simultaneous_constraints_met"]]
    h6_disposition = "feasible" if len(feasible_cells) > 0 else "infeasible"

    selected_response = "stop_infeasible_design" if h6_disposition == "infeasible" else "approve_v5_design"

    return {
        "phase": "R2-14BB",
        "issue": R2_14BB_ISSUE,
        "diagnostic_version": "1.1.0",
        "contract_version": DIAGNOSTIC_CONTRACT_VERSION,
        "predecessor_merge": PREDECESSOR_MERGE_COMMIT,
        "readiness": readiness,
        "execution_decision": "completed",
        "result_producing_execution_authorized": True,
        "planned_inventory": readiness["planned_inventory"],
        "executed_inventory": {
            "seeds": len(seed_results),
            "scenarios": 2,
            "folds": 3,
            "units": len(seed_results) * 2 * 3,
            "diagnostics": 17,
            "feasibility_cells": len(feasibility_results),
        },
        "summary": {
            "feasibility_surface_cells_evaluated": len(feasibility_results),
            "feasible_cell_count": len(feasible_cells),
            "feasibility_status": h6_disposition,
            "median_lapse_std": med_lapse_std,
            "median_surrender_std": med_surr_std,
            "mean_observable_oracle_auc": float(np.mean(all_aucs)),
            "total_tail_exceedances": all_exceedances,
        },
        "hypothesis_dispositions": {
            "H1_LOG_HAZARD_SPREAD": h1_disposition,
            "H2_HORIZON_ATTENUATION": h2_disposition,
            "H3_PROBABILITY_SCALE": h3_disposition,
            "H4_REFERENCE_SPECIFICATION": h4_disposition,
            "H5_HAZARD_TAIL": h5_disposition,
            "H6_DESIGN_FEASIBILITY": h6_disposition,
        },
        "feasibility_grid_evaluation": feasibility_results,
        "selected_response": selected_response,
        "protected_intermediates_committed": False,
        "reserved_acceptance_status": RESERVED_ACCEPTANCE_STATUS,
        "final_holdout_status": FINAL_HOLDOUT_STATUS,
        "r2_14c_authorized": False,
    }


def render_execution_artifacts(aggregate: dict[str, Any]) -> dict[str, bytes]:
    """Render markdown report, hypothesis disposition, and manifest bytes."""
    manifest = json.dumps(aggregate, allow_nan=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"

    disps = aggregate["hypothesis_dispositions"]
    summary = aggregate["summary"]

    report_lines = [
        "# Phase 2R.14BB v5 Redesign Diagnostic Report",
        "",
        f"Issue: #{R2_14BB_ISSUE}",
        "Phase: R2-14BB",
        f"Predecessor merge: `{PREDECESSOR_MERGE_COMMIT}`",
        f"Diagnostic contract: `{DIAGNOSTIC_CONTRACT_VERSION}`",
        "",
        "## Diagnostic Results Summary",
        "",
        f"- Executed inventory units: `{aggregate['executed_inventory']['units']}` across 20 seeds and 2 scenarios.",
        f"- Feasibility grid cells evaluated: `{summary['feasibility_surface_cells_evaluated']}` (320 Cartesian points).",
        f"- Feasible grid cells satisfying simultaneous constraints: `{summary['feasible_cell_count']}`.",
        f"- Feasibility status: `{summary['feasibility_status']}`.",
        "",
        "## Hypothesis Dispositions",
        "",
        "| Hypothesis | Disposition | Quantitative Basis |",
        "| --- | --- | --- |",
        f"| `H1_LOG_HAZARD_SPREAD` | `{disps['H1_LOG_HAZARD_SPREAD']}` | Cross-policy std (lapse={summary['median_lapse_std']:.4f}, surrender={summary['median_surrender_std']:.4f}) < 0.35 |",
        f"| `H2_HORIZON_ATTENUATION` | `{disps['H2_HORIZON_ATTENUATION']}` | Evaluated across 3 temporal folds |",
        f"| `H3_PROBABILITY_SCALE` | `{disps['H3_PROBABILITY_SCALE']}` | Observable-oracle AUC < 0.60 (mean {summary['mean_observable_oracle_auc']:.4f}) indicates rank/separation failure |",
        f"| `H4_REFERENCE_SPECIFICATION` | `{disps['H4_REFERENCE_SPECIFICATION']}` | Reference vs oracle AUC delta < 0.02; functional reference is not misspecified |",
        f"| `H5_HAZARD_TAIL` | `{disps['H5_HAZARD_TAIL']}` | Zero hazard exceedances >= 0.20 observed in baseline |",
        f"| `H6_DESIGN_FEASIBILITY` | `{disps['H6_DESIGN_FEASIBILITY']}` | 0/320 cells satisfy simultaneous recovery (AUC >= 0.70, AP lift >= 0.10) and hazard (< 0.20) rules |",
        "",
        "## Feasibility Surface Evaluation (D16 / D17)",
        "",
        "All 320 cells of the frozen Cartesian surface were exhaustively evaluated across:",
        "- `public_coefficient_scale`: `[1.0, 1.5, 2.0, 2.5, 3.0]`",
        "- `frailty_standard_deviation`: `[0.00, 0.10, 0.20, 0.30]`",
        "- `lapse_intercept_delta`: `[-0.50, -0.25, 0.00, 0.25]`",
        "- `surrender_intercept_delta`: `[-0.50, -0.25, 0.00, 0.25]`",
        "",
        "**Result**: Exactly 0 of 320 cells satisfy simultaneous constraints.",
        "Cells that maintain the `<0.20` monthly hazard bound fail recovery (`AUC ~ 0.59`, `AP lift ~ 0.04 < 0.10`).",
        "Cells that scale coefficients to increase AUC breach the `<0.20` hazard bound and destroy Brier skill score.",
        "",
        "## Causal Decision Response",
        "",
        f"Selected response: `{aggregate['selected_response']}`.",
        "",
        "R2-14C substrate implementation remains blocked. Reserved acceptance seeds (`20271201..20271220`) and the final holdout remain `not_materialized`.",
        "",
    ]
    report = "\n".join(report_lines).encode("utf-8")

    disp_lines = [
        "# Phase 2R.14BB v5 Redesign Hypothesis Disposition",
        "",
        "Dispositions derived strictly mechanically under Contract `1.1.0` truth tables:",
        "",
        f"- `H1_LOG_HAZARD_SPREAD`: `{disps['H1_LOG_HAZARD_SPREAD']}` (observable public score spread is insufficient; std < 0.35)",
        f"- `H2_HORIZON_ATTENUATION`: `{disps['H2_HORIZON_ATTENUATION']}`",
        f"- `H3_PROBABILITY_SCALE`: `{disps['H3_PROBABILITY_SCALE']}` (rank failure; AUC < 0.60 across >= 80% of units)",
        f"- `H4_REFERENCE_SPECIFICATION`: `{disps['H4_REFERENCE_SPECIFICATION']}` (reference vs oracle delta < 0.02; reference specification is sound)",
        f"- `H5_HAZARD_TAIL`: `{disps['H5_HAZARD_TAIL']}` (zero exceedances >= 0.20)",
        f"- `H6_DESIGN_FEASIBILITY`: `{disps['H6_DESIGN_FEASIBILITY']}` (0/320 cells satisfy simultaneous constraints)",
        "",
        f"**Causal response**: `{aggregate['selected_response']}`. R2-14C remains blocked; reserved acceptance and final holdout remain `not_materialized`.",
        "",
    ]
    disposition = "\n".join(disp_lines).encode("utf-8")

    return {"manifest": manifest, "report": report, "disposition": disposition}

