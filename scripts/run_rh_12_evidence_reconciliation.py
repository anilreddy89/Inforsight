#!/usr/bin/env python3
"""Generate and verify versioned RH-12 evidence reconciliation artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
for source_path in (REPO_ROOT / "simulator" / "src", REPO_ROOT / "inference-runtime" / "src"):
    if str(source_path) not in sys.path:
        sys.path.insert(0, str(source_path))

from inforsight_inference import (  # noqa: E402
    MODEL_BUNDLE_VERSION,
    MODEL_ID,
    TRUSTED_BUNDLE_SHA256,
    load_verified_runtime,
)
from inforsight_simulator.counterfactual import CounterfactualSimulator  # noqa: E402
from inforsight_simulator.optimization import (  # noqa: E402
    ALLOCATOR_ID,
    ALLOCATOR_VERSION,
    compare_portfolio_strategies,
)
from inforsight_simulator.rh12_evidence import (  # noqa: E402
    ECONOMICS,
    STRATEGY_IDS,
    build_recommendations,
    fast_resampled_strategy_results,
    occurrence_recommendations,
    summarize_bootstrap,
    summarize_strategy,
)
from inforsight_simulator.v6_corpus import V6CorpusConfig, generate_v6_corpus  # noqa: E402
from inforsight_simulator.v6_evaluation import _feature_map  # noqa: E402


ARTIFACT_ID = "inforsight.rh12.evidence-reconciliation"
ARTIFACT_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
DEFAULT_SEED = 20280201
DEFAULT_BOOTSTRAP_SAMPLES = 1000
DEFAULT_POLICY_COUNT = 3600
DEFAULT_BUDGET_MICROS = 5_000 * 1_000_000
DEFAULT_PERSONNEL_SECONDS = 50 * 3_600
DEFAULT_CREATED_AT = "2026-09-18T00:00:00Z"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--bootstrap-samples", type=int, default=DEFAULT_BOOTSTRAP_SAMPLES)
    parser.add_argument("--policy-count", type=int, default=DEFAULT_POLICY_COUNT)
    parser.add_argument("--budget-cap-usd", type=int, default=5_000)
    parser.add_argument("--personnel-capacity-hours", type=int, default=50)
    parser.add_argument("--bundle-path", default="docs/experiments/phase-02-10-model-bundle.json")
    parser.add_argument(
        "--output-json",
        default="docs/experiments/phase-rh-12-evidence-reconciliation-1.0.0.json",
    )
    parser.add_argument(
        "--output-report",
        default="docs/experiments/phase-rh-12-evidence-reconciliation-1.0.0.md",
    )
    parser.add_argument("--created-at", default=DEFAULT_CREATED_AT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def canonical_digest(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload["evidence_digest"] = ""
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _latest_observations(corpus: Any) -> tuple[list[Any], dict[str, float]]:
    latest: dict[str, Any] = {}
    frailties: dict[str, float] = {
        record.observation_id: record.latent_frailty for record in corpus.oracle_sidecar
    }
    for observation in corpus.observations:
        incumbent = latest.get(observation.policy_id)
        if incumbent is None or observation.as_of > incumbent.as_of:
            latest[observation.policy_id] = observation
    return list(latest.values()), frailties


def _metric_samples_template() -> dict[str, list[float]]:
    return {
        "modeled_expected_annual_premium_preserved_usd_micros": [],
        "direct_cost_usd_micros": [],
        "modeled_expected_net_value_usd_micros": [],
        "signed_combined_termination_effect_90d": [],
        "expected_harm_90d": [],
        "modeled_recall_at_capacity": [],
        "modeled_unnecessary_contact_count": [],
        "budget_used_usd_micros": [],
        "personnel_used_seconds": [],
    }


def _append_metrics(samples: dict[str, list[float]], metrics: dict[str, Any]) -> None:
    for metric in samples:
        samples[metric].append(float(metrics[metric]))


def _fixed_assignment_bootstrap(
    *,
    source_ids: list[str],
    source_recommendations: dict[str, Any],
    source_outcomes: dict[str, Any],
    base_selections: dict[str, list[tuple[str, str]]],
    budget_capacity_usd_micros: int,
    personnel_capacity_seconds: int,
    samples: int,
    seed: int,
) -> tuple[dict[str, dict[str, list[float]]], dict[str, Any]]:
    rng = np.random.default_rng(seed)
    metric_samples = {strategy: _metric_samples_template() for strategy in STRATEGY_IDS}
    point_estimates: dict[str, Any] = {}
    for strategy_id in STRATEGY_IDS:
        point_estimates[strategy_id] = summarize_strategy(
            strategy_id=strategy_id,
            selections=base_selections[strategy_id],
            recommendations=source_recommendations,
            potential_outcomes=source_outcomes,
            comparison_context_sha256="",
            budget_capacity_usd_micros=budget_capacity_usd_micros,
            personnel_capacity_seconds=personnel_capacity_seconds,
        )

    for _ in range(samples):
        indices = rng.integers(0, len(source_ids), size=len(source_ids))
        for strategy_id in STRATEGY_IDS:
            assignment_by_source = dict(base_selections[strategy_id])
            selections = [
                (source_ids[int(index)], assignment_by_source[source_ids[int(index)]])
                for index in indices
            ]
            metrics = summarize_strategy(
                strategy_id=strategy_id,
                selections=selections,
                recommendations=source_recommendations,
                potential_outcomes=source_outcomes,
                comparison_context_sha256="",
                budget_capacity_usd_micros=budget_capacity_usd_micros,
                personnel_capacity_seconds=personnel_capacity_seconds,
            )
            _append_metrics(metric_samples[strategy_id], metrics)
    return metric_samples, point_estimates


def _allocation_procedure_bootstrap(
    *,
    source_ids: list[str],
    source_recommendations: dict[str, Any],
    source_risk_scores: dict[str, float],
    source_outcomes: dict[str, Any],
    budget_capacity_usd_micros: int,
    personnel_capacity_seconds: int,
    as_of: datetime,
    portfolio_id: str,
    samples: int,
    seed: int,
) -> tuple[dict[str, dict[str, list[float]]], dict[str, Any], set[str]]:
    rng = np.random.default_rng(seed)
    metric_samples = {strategy: _metric_samples_template() for strategy in STRATEGY_IDS}
    base_recommendations = list(source_recommendations.values())
    base_comparison = compare_portfolio_strategies(
        base_recommendations,
        risk_scores=source_risk_scores,
        budget_capacity_usd_micros=budget_capacity_usd_micros,
        personnel_capacity_seconds=personnel_capacity_seconds,
        as_of=as_of,
        portfolio_id=portfolio_id,
    )
    point_estimates: dict[str, Any] = {}
    for result in base_comparison:
        selections = list(result.selections)
        point_estimates[result.strategy_id] = summarize_strategy(
            strategy_id=result.strategy_id,
            selections=selections,
            recommendations=source_recommendations,
            potential_outcomes=source_outcomes,
            comparison_context_sha256=result.comparison_context_sha256,
            budget_capacity_usd_micros=budget_capacity_usd_micros,
            personnel_capacity_seconds=personnel_capacity_seconds,
        )

    context_digests = {result.comparison_context_sha256 for result in base_comparison}
    for _ in range(samples):
        indices = rng.integers(0, len(source_ids), size=len(source_ids))
        occurrence_recs, occurrence_scores, occurrence_to_source = occurrence_recommendations(
            source_recommendations, source_risk_scores, indices, source_ids
        )
        results = fast_resampled_strategy_results(
            occurrence_recs,
            risk_scores=occurrence_scores,
            budget_capacity_usd_micros=budget_capacity_usd_micros,
            personnel_capacity_seconds=personnel_capacity_seconds,
            as_of=as_of,
            portfolio_id=portfolio_id,
        )
        occurrence_map = {recommendation.policy_id: recommendation for recommendation in occurrence_recs}
        context_digests.update(result[1] for result in results)
        for strategy_id, context_digest, selections in results:
            metrics = summarize_strategy(
                strategy_id=strategy_id,
                selections=selections,
                recommendations=occurrence_map,
                potential_outcomes=source_outcomes,
                comparison_context_sha256=context_digest,
                budget_capacity_usd_micros=budget_capacity_usd_micros,
                personnel_capacity_seconds=personnel_capacity_seconds,
            )
            _append_metrics(metric_samples[strategy_id], metrics)
    return metric_samples, point_estimates, context_digests


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if args.bootstrap_samples <= 0:
        raise ValueError("bootstrap sample count must be positive")
    if args.policy_count <= 0 or args.policy_count % 6:
        raise ValueError("policy count must be positive and divisible by six")
    if args.personnel_capacity_hours < 0 or args.budget_cap_usd < 0:
        raise ValueError("capacities must be nonnegative")
    datetime.fromisoformat(args.created_at.replace("Z", "+00:00"))

    bundle_path = REPO_ROOT / args.bundle_path
    runtime = load_verified_runtime(
        bundle_path,
        expected_sha256=TRUSTED_BUNDLE_SHA256,
        expected_bundle_id=MODEL_ID,
        expected_bundle_version=MODEL_BUNDLE_VERSION,
    )
    del runtime

    corpus = generate_v6_corpus(
        V6CorpusConfig(
            base_seed=args.seed,
            policy_count=args.policy_count,
            cohort_count=6,
            policies_per_cohort=args.policy_count // 6,
        )
    )
    observations, frailties = _latest_observations(corpus)
    if len(observations) != args.policy_count:
        raise ValueError("RH-12 cohort did not produce the requested unique-policy count")

    verified_runtime = load_verified_runtime(
        bundle_path,
        expected_sha256=TRUSTED_BUNDLE_SHA256,
        expected_bundle_id=MODEL_ID,
        expected_bundle_version=MODEL_BUNDLE_VERSION,
    )
    risk_scores = {
        observation.policy_id: verified_runtime.engine.score_record(
            _feature_map(observation)
        ).calibrated_probability
        for observation in observations
    }
    simulator = CounterfactualSimulator()
    potential_outcomes = simulator.simulate_cohort(
        observations,
        frailty_map={
            observation.policy_id: frailties[observation.observation_id]
            for observation in observations
        },
    )
    recommendations = build_recommendations(observations, risk_scores, potential_outcomes)
    recommendation_map = {recommendation.policy_id: recommendation for recommendation in recommendations}
    source_ids = sorted(recommendation_map)
    recommendation_map = {policy_id: recommendation_map[policy_id] for policy_id in source_ids}
    risk_scores = {policy_id: risk_scores[policy_id] for policy_id in source_ids}
    potential_outcomes = {policy_id: potential_outcomes[policy_id] for policy_id in source_ids}

    budget_capacity_usd_micros = args.budget_cap_usd * 1_000_000
    personnel_capacity_seconds = args.personnel_capacity_hours * 3_600
    as_of = max(
        datetime.fromisoformat(observation.as_of.replace("Z", "+00:00")).astimezone(timezone.utc)
        for observation in observations
    )
    portfolio_id = f"rh12-{args.seed}-{len(source_ids)}"
    comparison = compare_portfolio_strategies(
        list(recommendation_map.values()),
        risk_scores=risk_scores,
        budget_capacity_usd_micros=budget_capacity_usd_micros,
        personnel_capacity_seconds=personnel_capacity_seconds,
        as_of=as_of,
        portfolio_id=portfolio_id,
    )
    base_results = {result.strategy_id: result for result in comparison}
    base_summaries = {
        result.strategy_id: summarize_strategy(
            strategy_id=result.strategy_id,
            selections=result.selections,
            recommendations=recommendation_map,
            potential_outcomes=potential_outcomes,
            comparison_context_sha256=result.comparison_context_sha256,
            budget_capacity_usd_micros=budget_capacity_usd_micros,
            personnel_capacity_seconds=personnel_capacity_seconds,
        )
        for result in comparison
    }
    base_selections = {
        strategy_id: list(base_results[strategy_id].selections)
        for strategy_id in STRATEGY_IDS
    }

    fixed_samples, fixed_points = _fixed_assignment_bootstrap(
        source_ids=source_ids,
        source_recommendations=recommendation_map,
        source_outcomes=potential_outcomes,
        base_selections=base_selections,
        budget_capacity_usd_micros=budget_capacity_usd_micros,
        personnel_capacity_seconds=personnel_capacity_seconds,
        samples=args.bootstrap_samples,
        seed=args.seed,
    )
    allocation_samples, allocation_points, context_digests = _allocation_procedure_bootstrap(
        source_ids=source_ids,
        source_recommendations=recommendation_map,
        source_risk_scores=risk_scores,
        source_outcomes=potential_outcomes,
        budget_capacity_usd_micros=budget_capacity_usd_micros,
        personnel_capacity_seconds=personnel_capacity_seconds,
        as_of=as_of,
        portfolio_id=portfolio_id,
        samples=args.bootstrap_samples,
        seed=args.seed + 1,
    )

    old_json = REPO_ROOT / "docs/experiments/phase-03-08-ope-results.json"
    old_report = REPO_ROOT / "docs/experiments/phase-03-08-ope-report.md"
    contracts = {
        "economics_contract_id": ECONOMICS.contract_id,
        "economics_contract_version": ECONOMICS.version,
        "economics_contract_sha256": ECONOMICS.sha256,
        "semantic_catalog_version": ECONOMICS.catalog.snapshot_version,
        "semantic_catalog_sha256": ECONOMICS.catalog.sha256,
        "allocator_id": ALLOCATOR_ID,
        "allocator_version": ALLOCATOR_VERSION,
        "model_bundle_id": MODEL_ID,
        "model_bundle_version": MODEL_BUNDLE_VERSION,
        "model_bundle_sha256": TRUSTED_BUNDLE_SHA256,
    }
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "artifact_version": ARTIFACT_VERSION,
        "created_at": args.created_at,
        "status": "corrected_evidence",
        "primary_estimand": "new_portfolio_allocation_procedure_performance",
        "cohort": {
            "policy_count": len(source_ids),
            "cluster_key": "policy_id",
            "evaluation_seed": args.seed,
            "as_of": as_of.isoformat().replace("+00:00", "Z"),
            "horizon_days": 90,
            "source": "Generation v6 synthetic corpus with protected oracle sidecar for conditional potential outcomes",
            "final_holdout_access": "not_accessed",
        },
        "capacities": {
            "budget_capacity_usd_micros": budget_capacity_usd_micros,
            "personnel_capacity_seconds": personnel_capacity_seconds,
            "display_hours_only": args.personnel_capacity_hours,
        },
        "contracts": contracts,
        "comparison_context": {
            "portfolio_id": portfolio_id,
            "comparison_context_sha256": comparison[0].comparison_context_sha256,
            "strategies": list(STRATEGY_IDS),
            "same_cohort_cutoff_eligibility_catalog_budget_personnel": True,
            "strategy_results": base_summaries,
        },
        "estimands": {
            "frozen_assignment_sampling_uncertainty": summarize_bootstrap(
                fixed_samples,
                fixed_points,
                estimand_id="frozen_assignment_sampling_uncertainty",
            ),
            "new_portfolio_allocation_procedure_performance": summarize_bootstrap(
                allocation_samples,
                allocation_points,
                estimand_id="new_portfolio_allocation_procedure_performance",
            ),
        },
        "bootstrap_protocol": {
            "cluster": "policy_id",
            "resample_count": args.bootstrap_samples,
            "fixed_assignment_seed": args.seed,
            "allocation_procedure_seed": args.seed + 1,
            "draw_count_per_replicate": len(source_ids),
            "duplicate_occurrence_identity": "policy_id#draw_index",
            "source_policy_id_remains_join_key": True,
            "fixed_assignment_capacity_treatment": "observed resource totals may exceed original caps because assignments are not rerun",
            "allocation_procedure_capacity_treatment": "original total budget micros and personnel seconds remain fixed for every replicate",
            "model_refit": False,
            "calibration_refit": False,
            "treatment_effect_reestimation": False,
            "allocation_context_digest_count": len(context_digests),
        },
        "supported_metric_definitions": {
            "modeled_expected_annual_premium_preserved_usd_micros": "signed combined-termination effect multiplied by annual premium cents under RH-04's synthetic one-year value basis",
            "modeled_expected_net_value_usd_micros": "modeled expected annual premium preserved micros less direct action cost micros",
            "signed_combined_termination_effect_90d": "control combined lapse-or-surrender probability minus selected-action combined probability",
            "expected_harm_90d": "sum of the magnitude of negative selected-action effects; beneficial and neutral effects contribute zero",
            "modeled_recall_at_capacity": "selected-action expected combined-effect reduction divided by baseline combined-termination probability; not observed-outcome recall",
            "modeled_unnecessary_contact_count": "selected non-abstain occurrences with non-positive modeled effect; not a realized customer-contact outcome",
            "lead_time_days": "not supported by the current counterfactual contract because intervention and event timestamps are not attributed",
        },
        "protocol_disclosure": {
            "statistical_acceptance_protocol": "3.1.0",
            "post_result_amendment": "RH-12 is a post-result reconciliation after RH-04/RH-05 contract repairs; it does not alter the original acceptance result",
            "acceptance_seed_reuse": args.seed == DEFAULT_SEED,
            "fresh_seed_confirmation": "not_run; requires separate predeclared experiment issue",
        },
        "issue_130_disposition": {
            "disposition": "defer",
            "issue": 130,
            "rationale": "Fresh simulator stress variants are not required to repair or reconcile the core evidence. Execution remains separately gated by predeclared variants, thresholds, seeds, estimand, and artifact versions.",
        },
        "claim_boundaries": {
            "synthetic_conditional": True,
            "causal_treatment_effect": False,
            "realized_profit": False,
            "external_validity": False,
            "demographic_fairness": False,
            "production_readiness": False,
            "network_or_sustained_load_performance": False,
            "phase_4_authorization": False,
        },
        "historical_artifacts": {
            "preserved_byte_identical": True,
            "legacy_ope_manifest_sha256": sha256_file(old_json),
            "legacy_ope_report_sha256": sha256_file(old_report),
            "superseded_by": "phase-rh-12-evidence-reconciliation-1.0.0",
        },
    }
    manifest["evidence_digest"] = canonical_digest(manifest)
    return manifest


def _money(micros: int | float) -> str:
    return f"${float(micros) / 1_000_000:,.2f}"


def generate_report(manifest: dict[str, Any]) -> str:
    comparison = manifest["comparison_context"]["strategy_results"]
    fixed = manifest["estimands"]["frozen_assignment_sampling_uncertainty"]["strategies"]
    allocation = manifest["estimands"]["new_portfolio_allocation_procedure_performance"]["strategies"]
    lines = [
        "# RH-12 Evidence Reconciliation Report 1.0.0",
        "",
        f"- **Artifact:** `{manifest['artifact_id']}` / `{manifest['artifact_version']}`",
        f"- **Evidence digest:** `{manifest['evidence_digest']}`",
        f"- **Evaluation seed:** `{manifest['cohort']['evaluation_seed']}`",
        f"- **Cohort:** `{manifest['cohort']['policy_count']:,}` unique synthetic policies",
        f"- **Cutoff:** `{manifest['cohort']['as_of']}`; horizon `{manifest['cohort']['horizon_days']}` days",
        f"- **Final holdout:** `{manifest['cohort']['final_holdout_access']}`",
        "",
        "## Disposition",
        "",
        "This is corrected, versioned evidence generated after the RH-04 economics/resource and RH-05 allocation repairs. The historical Phase 3.08 OPE manifest and report remain unchanged. Results are synthetic and conditional on the frozen Generation v6 model, potential-outcome simulator, eligibility rules, catalog, economics contract, and allocator.",
        "",
        "The primary estimand is **new-portfolio allocation-procedure performance**. A separate fixed-assignment sampling estimand is reported below; the two are not pooled.",
        "",
        "## Contracts and comparison context",
        "",
        f"- Economics: `{manifest['contracts']['economics_contract_id']}` version `{manifest['contracts']['economics_contract_version']}` digest `{manifest['contracts']['economics_contract_sha256']}`.",
        f"- Allocation: `{manifest['contracts']['allocator_id']}` version `{manifest['contracts']['allocator_version']}`.",
        f"- Model bundle: `{manifest['contracts']['model_bundle_id']}` version `{manifest['contracts']['model_bundle_version']}`.",
        f"- Budget capacity: `{manifest['capacities']['budget_capacity_usd_micros']}` USD micros.",
        f"- Personnel capacity: `{manifest['capacities']['personnel_capacity_seconds']}` seconds; display-only equivalent `{manifest['capacities']['display_hours_only']}` hours.",
        "",
        "All four strategies use the same cohort, cutoff, eligibility results, semantic catalog, economics identity, budget capacity, and personnel capacity.",
        "",
        "| Strategy | Selected | Abstain | Net value | Signed effect | Expected harm | Modeled recall | Non-beneficial contacts |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    labels = {
        "non_intervention": "Non-intervention",
        "operational_rules_only": "Rules-only",
        "risk_ranked": "Risk-ranked",
        "allocation_engine": "Allocation engine",
    }
    for strategy in STRATEGY_IDS:
        row = comparison[strategy]
        lines.append(
            f"| {labels[strategy]} | {row['selected_count']} | {row['abstention_count']} | "
            f"{_money(row['modeled_expected_net_value_usd_micros'])} | "
            f"{row['signed_combined_termination_effect_90d']:.6f} | "
            f"{row['expected_harm_90d']:.6f} | "
            f"{row['modeled_recall_at_capacity']:.4%} | "
            f"{row['modeled_unnecessary_contact_count']} |"
        )
    lines.extend([
        "",
        "## Estimand 1 — frozen-assignment sampling uncertainty",
        "",
        "Each replicate draws exactly the original number of unique `policy_id` clusters with replacement. The already selected action assignment is retained for each sampled occurrence. Duplicate occurrences contribute separately to totals. Resource totals may exceed the original capacity because allocation is not rerun.",
        "",
        "| Strategy | Net value median [95% interval] | Signed effect median [95% interval] | Expected harm median [95% interval] |",
        "| --- | ---: | ---: | ---: |",
    ])
    for strategy in STRATEGY_IDS:
        rows = fixed[strategy]
        net = rows["intervals"]["modeled_expected_net_value_usd_micros"]
        effect = rows["intervals"]["signed_combined_termination_effect_90d"]
        harm = rows["intervals"]["expected_harm_90d"]
        lines.append(
            f"| {labels[strategy]} | {_money(net['median'])} [{_money(net['ci_lower'])}, {_money(net['ci_upper'])}] | "
            f"{effect['median']:.6f} [{effect['ci_lower']:.6f}, {effect['ci_upper']:.6f}] | "
            f"{harm['median']:.6f} [{harm['ci_lower']:.6f}, {harm['ci_upper']:.6f}] |"
        )
    lines.extend([
        "",
        "## Estimand 2 — new-portfolio allocation-procedure performance",
        "",
        "Each replicate retains source policy facts and frozen scores/effects, assigns duplicate occurrence identities as `policy_id#draw_index`, reruns the four-strategy comparison, and holds the original total budget micros and personnel seconds fixed. No model refit, calibration refit, or effect re-estimation occurs.",
        "",
        "| Strategy | Net value median [95% interval] | Signed effect median [95% interval] | Expected harm median [95% interval] |",
        "| --- | ---: | ---: | ---: |",
    ])
    for strategy in STRATEGY_IDS:
        rows = allocation[strategy]
        net = rows["intervals"]["modeled_expected_net_value_usd_micros"]
        effect = rows["intervals"]["signed_combined_termination_effect_90d"]
        harm = rows["intervals"]["expected_harm_90d"]
        lines.append(
            f"| {labels[strategy]} | {_money(net['median'])} [{_money(net['ci_lower'])}, {_money(net['ci_upper'])}] | "
            f"{effect['median']:.6f} [{effect['ci_lower']:.6f}, {effect['ci_upper']:.6f}] | "
            f"{harm['median']:.6f} [{harm['ci_lower']:.6f}, {harm['ci_upper']:.6f}] |"
        )
    lines.extend([
        "",
        "## Metric and claim boundaries",
        "",
        "- `modeled_expected_annual_premium_preserved_usd_micros` is a signed modeled value under RH-04's synthetic one-year annual-premium basis. It is not realized premium, revenue, margin, profit, or causal value.",
        "- `signed_combined_termination_effect_90d` is the combined lapse-or-surrender probability difference. It does not identify separate causal lapse and surrender treatment effects.",
        "- `modeled_recall_at_capacity` is an expected-effect ratio, not observed-outcome recall. The current counterfactual artifact supports no intervention-time lead-time estimate, so lead time is explicitly `not_supported`.",
        "- The synthetic corpus has no demographic attributes; no fairness or disparate-impact claim is made.",
        "- The v5 infeasibility result remains bounded to its examined design/search space and is not a universal impossibility claim.",
        "- Protocol 3.1.0 and acceptance-seed reuse remain visible. Fresh-seed confirmation was not run and requires a separate predeclared experiment issue.",
        "",
        "## Independent issue #130",
        "",
        "Disposition: **defer**. Fresh simulator stress variants are not required for the RH-12 core reconciliation. If later incorporated, variants, thresholds, estimand, seeds, and artifact versions must be predeclared before results are inspected; unfavorable results remain valid evidence.",
        "",
        "## Historical artifact preservation",
        "",
        f"- Legacy manifest SHA-256: `{manifest['historical_artifacts']['legacy_ope_manifest_sha256']}`",
        f"- Legacy report SHA-256: `{manifest['historical_artifacts']['legacy_ope_report_sha256']}`",
        "- The legacy files were read only and were not rewritten by this run.",
        "",
        "## Verification",
        "",
        "This artifact is generated with the repository's synthetic Generation v6 corpus, RH-04 contract 1.0.0, RH-05 allocator 1.0.0, and the verified model bundle. `--check` regenerates the manifest and compares the evidence digest without rewriting the published JSON or report.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    output_json = REPO_ROOT / args.output_json
    output_report = REPO_ROOT / args.output_report
    report = generate_report(manifest)

    if args.check:
        try:
            published = json.loads(output_json.read_text(encoding="utf-8"))
            published_report = output_report.read_text(encoding="utf-8")
        except (OSError, json.JSONDecodeError) as exc:
            print(f"RH-12 published evidence unavailable: {exc}", file=sys.stderr)
            return 1
        if published.get("evidence_digest") != manifest["evidence_digest"]:
            print("RH-12 evidence digest mismatch", file=sys.stderr)
            return 1
        if generate_report(published) != published_report:
            print("RH-12 report mismatch", file=sys.stderr)
            return 1
        print(f"RH-12 evidence check passed without rewriting {output_json}")
        return 0

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(report, encoding="utf-8")
    print(f"Wrote {output_json}")
    print(f"Wrote {output_report}")
    print(f"Evidence digest: {manifest['evidence_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
