"""Freeze training-baseline distributions from the loaded ModelBundle.

Reference distributions are derived at service startup from the frozen
model bundle (inforsight-v6-logistic-platt-20260817).  No external training
data files are required — the serving container remains fully self-contained.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class NumericBaseline:
    """Reference distribution for one continuous feature (10 equal-width bins)."""

    feature_name: str
    bin_edges: tuple[float, ...]   # length 11 — boundaries for 10 bins
    ref_proportions: tuple[float, ...]  # length 10 — fraction of training rows per bin


@dataclass(frozen=True)
class CategoricalBaseline:
    """Reference distribution for one categorical feature."""

    feature_name: str
    categories: tuple[str, ...]
    ref_proportions: tuple[float, ...]   # aligned with categories


@dataclass(frozen=True)
class TrainingBaseline:
    """Complete frozen baseline extracted from the model bundle."""

    bundle_id: str
    reference_observation_count: int
    numeric: dict[str, NumericBaseline]
    categorical: dict[str, CategoricalBaseline]


_EPSILON = 1e-4   # zero-proportion guard (Phase 3.04A spec §2.1)
_N_BINS = 10


def _build_numeric_baseline(feature_name: str, mean: float, scale: float) -> NumericBaseline:
    """Reconstruct a plausible reference distribution from preprocessor statistics.

    The bundle stores (mean, scale) per numeric feature.  We cannot reconstruct the
    raw training rows, so we approximate the reference distribution as a normal
    N(mean, scale) discretised into 10 equal-width bins spanning ±3σ.  This gives
    well-defined reference proportions for PSI computation.

    Bin edges are frozen at baseline-construction time and reused for live scoring.
    """
    lo = mean - 3.0 * scale
    hi = mean + 3.0 * scale
    edges = np.linspace(lo, hi, _N_BINS + 1)

    # Compute reference proportions from the N(mean, scale) CDF
    from math import erf, sqrt

    def _normal_cdf(x: float) -> float:
        return 0.5 * (1.0 + erf((x - mean) / (scale * sqrt(2.0))))

    proportions = []
    for i in range(_N_BINS):
        p = _normal_cdf(float(edges[i + 1])) - _normal_cdf(float(edges[i]))
        proportions.append(max(p, _EPSILON))

    total = sum(proportions)
    proportions = [p / total for p in proportions]

    return NumericBaseline(
        feature_name=feature_name,
        bin_edges=tuple(float(e) for e in edges),
        ref_proportions=tuple(proportions),
    )


def _build_categorical_baseline(feature_name: str, categories: tuple[str, ...]) -> CategoricalBaseline:
    """Build a uniform reference distribution across observed training categories.

    The bundle records which categories were seen in training (order is stable).
    Without raw training counts we assume a uniform prior — this is conservative
    (any deviation from uniform shows up as drift immediately) and keeps the
    container self-contained.
    """
    n = len(categories)
    uniform_p = 1.0 / n if n > 0 else _EPSILON
    return CategoricalBaseline(
        feature_name=feature_name,
        categories=categories,
        ref_proportions=tuple(uniform_p for _ in categories),
    )


def build_training_baseline(bundle: Any) -> TrainingBaseline:
    """Extract and freeze the training baseline from a loaded ModelBundle.

    Parameters
    ----------
    bundle:
        A loaded ``inforsight_simulator.bundle.ModelBundle`` instance.

    Returns
    -------
    TrainingBaseline
        Frozen baseline used by PSI/CSI computations.
    """
    numeric: dict[str, NumericBaseline] = {}
    for feat_name, spec in bundle.preprocessor.numeric.items():
        numeric[feat_name] = _build_numeric_baseline(feat_name, spec.mean, spec.scale)

    categorical: dict[str, CategoricalBaseline] = {}
    for feat_name, spec in bundle.preprocessor.categorical.items():
        # spec.categories is a tuple of the training category strings
        categorical[feat_name] = _build_categorical_baseline(feat_name, tuple(spec.categories))

    return TrainingBaseline(
        bundle_id=bundle.bundle_id,
        reference_observation_count=0,  # not stored in bundle; documented as unknown
        numeric=numeric,
        categorical=categorical,
    )
