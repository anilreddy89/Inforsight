"""Rolling calibration tracking: ECE, Brier Score, and Brier Skill Score (BSS).

Mathematical formulation (Phase 3.04A design spec §2.3 and §2.4):

    ECE = SUM_m [ (|B_m| / n) * |y_bar_m - p_hat_bar_m| ]   (M=10 bins, W=500 rolling window)

    BS  = (1/n) * SUM_i [ (p_hat_i - y_i)^2 ]

    BSS = 1 - (BS_current / BS_ref)      where BS_ref = 0.1211 (Phase 2.08 baseline)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from serving.monitoring.models import (
    CalibrationReport,
    REFERENCE_BRIER_SCORE,
    REFERENCE_ECE,
    BSS_DEGRADED_THRESHOLD,
    ECE_GREEN_MAX,
    ECE_YELLOW_MAX,
    _ece_status,
)

_ROLLING_WINDOW = 500   # predeclared in Phase 3.04A spec §2.3
_ECE_BINS = 10


@dataclass
class _Observation:
    predicted_prob: float
    observed_outcome: float   # 0.0 or 1.0


def _compute_ece(observations: list[_Observation], n_bins: int = _ECE_BINS) -> float:
    """Compute Expected Calibration Error over the provided observations."""
    n = len(observations)
    if n == 0:
        return 0.0

    bin_width = 1.0 / n_bins
    bin_sum_probs = [0.0] * n_bins
    bin_sum_outcomes = [0.0] * n_bins
    bin_counts = [0] * n_bins

    for obs in observations:
        p = max(0.0, min(1.0, obs.predicted_prob))
        b = min(int(p / bin_width), n_bins - 1)
        bin_sum_probs[b] += p
        bin_sum_outcomes[b] += obs.observed_outcome
        bin_counts[b] += 1

    ece = 0.0
    for b in range(n_bins):
        cnt = bin_counts[b]
        if cnt == 0:
            continue
        mean_p = bin_sum_probs[b] / cnt
        mean_y = bin_sum_outcomes[b] / cnt
        ece += (cnt / n) * abs(mean_y - mean_p)

    return ece


def _compute_brier_score(observations: list[_Observation]) -> float:
    n = len(observations)
    if n == 0:
        return 0.0
    return sum((o.predicted_prob - o.observed_outcome) ** 2 for o in observations) / n


class CalibrationTracker:
    """Maintains a rolling window of scored+resolved observations and computes calibration metrics.

    Thread safety: not required (single-process, single-worker serving context).
    """

    def __init__(self, window_size: int = _ROLLING_WINDOW) -> None:
        self._window_size = window_size
        self._buffer: Deque[_Observation] = deque(maxlen=window_size)
        self._oldest_timestamp: str | None = None
        self._newest_timestamp: str | None = None

    def record(self, predicted_prob: float, observed_outcome: float, timestamp: str | None = None) -> None:
        """Add a resolved observation (outcome known) to the rolling window."""
        self._buffer.append(_Observation(predicted_prob=predicted_prob, observed_outcome=observed_outcome))
        if timestamp:
            if self._oldest_timestamp is None:
                self._oldest_timestamp = timestamp
            self._newest_timestamp = timestamp

    def compute(self) -> CalibrationReport:
        """Compute ECE, Brier Score, and BSS over the current rolling window."""
        observations = list(self._buffer)
        n = len(observations)

        ece = _compute_ece(observations)
        bs = _compute_brier_score(observations)

        if REFERENCE_BRIER_SCORE > 0:
            bss = 1.0 - (bs / REFERENCE_BRIER_SCORE)
        else:
            bss = 0.0

        ece_stat = _ece_status(ece)
        # BSS degraded overrides brier_status even if ECE is green
        brier_stat = "degraded" if bss < BSS_DEGRADED_THRESHOLD else "stable"

        return CalibrationReport(
            window_size=n,
            ece=ece,
            brier_score=bs,
            brier_skill_score=bss,
            ece_status=ece_stat,
            brier_status=brier_stat,
            reference_ece=REFERENCE_ECE,
            reference_brier_score=REFERENCE_BRIER_SCORE,
        )

    @property
    def window_size(self) -> int:
        return len(self._buffer)

    @property
    def oldest_timestamp(self) -> str | None:
        return self._oldest_timestamp

    @property
    def newest_timestamp(self) -> str | None:
        return self._newest_timestamp
