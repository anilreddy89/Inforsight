"""Counterfactual simulation and Offline Policy Evaluation (OPE) package."""

from .evaluator import (
    OfflinePolicyEvaluator,
    build_ope_manifest,
    compute_policy_metrics,
    run_cluster_bootstrap,
)
from .hazard import (
    compute_action_logit_shift,
    counterfactual_competing_hazards,
    counterfactual_cumulative_incidence,
    counterfactual_observable_incidence,
)
from .models import (
    CANONICAL_INTERVENTIONS,
    CounterfactualOutcome,
    InterventionParameters,
    MetricInterval,
    OPEResultManifest,
    PairwiseContrast,
    PolicyEvaluationMetrics,
    TriageAssignment,
)
from .policies import (
    BaseTriagePolicy,
    ControlPolicy,
    DecisionEnginePolicy,
    HeuristicPolicy,
    NaiveMLPolicy,
    RandomPolicy,
)
from .simulator import CounterfactualSimulator

__all__ = [
    "CANONICAL_INTERVENTIONS",
    "CounterfactualOutcome",
    "InterventionParameters",
    "MetricInterval",
    "OPEResultManifest",
    "PairwiseContrast",
    "PolicyEvaluationMetrics",
    "TriageAssignment",
    "compute_action_logit_shift",
    "counterfactual_competing_hazards",
    "counterfactual_cumulative_incidence",
    "counterfactual_observable_incidence",
    "CounterfactualSimulator",
    "BaseTriagePolicy",
    "ControlPolicy",
    "DecisionEnginePolicy",
    "HeuristicPolicy",
    "NaiveMLPolicy",
    "RandomPolicy",
    "OfflinePolicyEvaluator",
    "build_ope_manifest",
    "compute_policy_metrics",
    "run_cluster_bootstrap",
]

