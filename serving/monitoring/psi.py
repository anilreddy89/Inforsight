"""PSI (Population Stability Index) and CSI (Characteristic Stability Index) computation.

Mathematical formulation (Phase 3.04A design spec §2.1 and §2.2):

    PSI = SUM_b [ (p_current_b - p_ref_b) * ln(p_current_b / p_ref_b) ]

Zero-proportion guard: if p_ref_b == 0 or p_current_b == 0, substitute EPSILON = 1e-4.
"""

from __future__ import annotations

import math
from typing import Sequence

from serving.monitoring.baseline import NumericBaseline, CategoricalBaseline, _EPSILON, _N_BINS
from serving.monitoring.models import (
    FeatureDriftResult,
    PRIMARY_RISK_DRIVERS,
    _psi_status,
)

# ------------------------------------------------------------------
# Core PSI formula
# ------------------------------------------------------------------

def _psi_term(p_current: float, p_ref: float) -> float:
    """Compute a single PSI bin contribution with zero-proportion guard."""
    pc = p_current if p_current > 0 else _EPSILON
    pr = p_ref if p_ref > 0 else _EPSILON
    return (pc - pr) * math.log(pc / pr)


def compute_psi_from_proportions(
    current_proportions: Sequence[float],
    ref_proportions: Sequence[float],
) -> float:
    """Compute PSI from two aligned proportion vectors.

    Parameters
    ----------
    current_proportions:
        Proportion of current observations per bin (must sum to ~1.0).
    ref_proportions:
        Proportion of reference (training) observations per bin.

    Returns
    -------
    float
        PSI value.
    """
    if len(current_proportions) != len(ref_proportions):
        raise ValueError("current_proportions and ref_proportions must have the same length.")
    return sum(_psi_term(pc, pr) for pc, pr in zip(current_proportions, ref_proportions))


# ------------------------------------------------------------------
# Numeric PSI
# ------------------------------------------------------------------

def _bin_observations(values: Sequence[float], edges: Sequence[float]) -> list[float]:
    """Assign observations to bins defined by edges and return proportions."""
    n_bins = len(edges) - 1
    counts = [0] * n_bins
    n = len(values)
    for v in values:
        # Clamp to outer bin if outside training range
        if v <= edges[0]:
            counts[0] += 1
        elif v >= edges[-1]:
            counts[-1] += 1
        else:
            for i in range(n_bins):
                if edges[i] <= v < edges[i + 1]:
                    counts[i] += 1
                    break
    if n == 0:
        return [_EPSILON] * n_bins
    raw = [c / n for c in counts]
    # Apply zero-proportion guard
    guarded = [max(p, _EPSILON) for p in raw]
    total = sum(guarded)
    return [p / total for p in guarded]


def compute_numeric_psi(
    feature_name: str,
    current_values: Sequence[float],
    baseline: NumericBaseline,
) -> FeatureDriftResult:
    """Compute PSI for a continuous feature against the frozen training baseline."""
    current_proportions = _bin_observations(current_values, baseline.bin_edges)
    psi = compute_psi_from_proportions(current_proportions, baseline.ref_proportions)
    return FeatureDriftResult(
        feature_name=feature_name,
        feature_type="continuous",
        is_primary_risk_driver=feature_name in PRIMARY_RISK_DRIVERS,
        psi_or_csi=psi,
        status=_psi_status(psi),
        unseen_proportion=0.0,
        bin_count=_N_BINS,
    )


# ------------------------------------------------------------------
# Categorical CSI
# ------------------------------------------------------------------

def compute_categorical_csi(
    feature_name: str,
    current_values: Sequence[str],
    baseline: CategoricalBaseline,
) -> FeatureDriftResult:
    """Compute CSI for a categorical feature against the frozen training baseline.

    Categories not seen in training are collected into an ``_UNSEEN_`` overflow bucket.
    An ``unseen_proportion`` > 0.05 triggers a schema-change alert independent of CSI.
    """
    n = len(current_values)
    known_cats = set(baseline.categories)
    counts: dict[str, int] = {cat: 0 for cat in baseline.categories}
    unseen_count = 0

    for v in current_values:
        if v in known_cats:
            counts[v] += 1
        else:
            unseen_count += 1

    unseen_proportion = unseen_count / n if n > 0 else 0.0

    # Compute current proportions aligned with baseline category order
    current_proportions = []
    for cat in baseline.categories:
        p = counts[cat] / n if n > 0 else _EPSILON
        current_proportions.append(max(p, _EPSILON))

    # Normalise (unseen observations reduce the share of known categories)
    total = sum(current_proportions)
    current_proportions = [p / total for p in current_proportions]

    csi = compute_psi_from_proportions(current_proportions, baseline.ref_proportions)

    return FeatureDriftResult(
        feature_name=feature_name,
        feature_type="categorical",
        is_primary_risk_driver=feature_name in PRIMARY_RISK_DRIVERS,
        psi_or_csi=csi,
        status=_psi_status(csi),
        unseen_proportion=unseen_proportion,
        bin_count=len(baseline.categories),
    )
