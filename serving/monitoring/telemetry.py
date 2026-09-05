"""In-memory latency ring buffer and request counter.

Tracks wall-clock HTTP response latencies (ms) and request counts since
service start.  A fixed-size deque acts as a circular ring buffer capped
at MAX_LATENCY_SAMPLES so memory is bounded.
"""

from __future__ import annotations

from collections import deque

from serving.monitoring.models import TelemetrySnapshot

_MAX_LATENCY_SAMPLES = 2000   # ring buffer capacity


class TelemetryCollector:
    """Accumulates request counts and latency samples for the diagnostics endpoint."""

    def __init__(self, max_samples: int = _MAX_LATENCY_SAMPLES) -> None:
        self._requests_total: int = 0
        self._requests_single: int = 0
        self._requests_batch: int = 0
        self._latencies: deque[float] = deque(maxlen=max_samples)
        self._calibration_window_size: int = 0
        self._scoring_window_start: str | None = None
        self._scoring_window_end: str | None = None

    def record_single(self, latency_ms: float) -> None:
        self._requests_total += 1
        self._requests_single += 1
        self._latencies.append(latency_ms)

    def record_batch(self, latency_ms: float, count: int) -> None:
        self._requests_total += count
        self._requests_batch += count
        self._latencies.append(latency_ms)

    def set_calibration_window(
        self,
        size: int,
        start: str | None,
        end: str | None,
    ) -> None:
        self._calibration_window_size = size
        self._scoring_window_start = start
        self._scoring_window_end = end

    def _percentile(self, pct: float) -> float:
        samples = sorted(self._latencies)
        if not samples:
            return 0.0
        idx = max(0, min(int(len(samples) * pct / 100.0), len(samples) - 1))
        return samples[idx]

    def snapshot(self) -> TelemetrySnapshot:
        return TelemetrySnapshot(
            requests_total=self._requests_total,
            requests_single=self._requests_single,
            requests_batch=self._requests_batch,
            latency_p50_ms=self._percentile(50),
            latency_p95_ms=self._percentile(95),
            latency_p99_ms=self._percentile(99),
            window_size=self._calibration_window_size,
            scoring_window_start=self._scoring_window_start,
            scoring_window_end=self._scoring_window_end,
        )
