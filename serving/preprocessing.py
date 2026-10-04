"""Frozen V6 coefficient transforms before the bundle's population z-score.

This is the inference-only form of v6_evaluation._feature_map. The gateway
accepts raw V6Features, while BundledInferenceEngine expects coefficient-space
values. Keeping this seam explicit prevents a second transform in the engine.
"""
from __future__ import annotations

import math
from typing import Any, Mapping


def coefficient_features(raw: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(raw)
    result["tenure_days"] = min(max(result["tenure_days"] / 365, 0), 5)
    result["premium_amount_cents"] = min(max(math.log1p(result["premium_amount_cents"] / 100) / 5, 0), 2)
    result["recent_delay_days"] = min(max((result["recent_delay_days"] or 0) / 30, 0), 3)
    for name in ("recent_failed_payment_count", "recent_retry_count", "recent_recovery_count",
                 "recent_notice_count", "recent_contact_count"):
        result[name] = min(max(result[name] / 3, 0), 2)
    result["arrears_duration_days"] = min(max(result["arrears_duration_days"] / 60, 0), 2)
    result["rolling_payment_count"] = min(max(result["rolling_payment_count"] / 12, 0), 2)
    result["payment_attribute_missing"] = int(result["payment_attribute_missing"])
    result["contact_attribute_missing"] = int(result["contact_attribute_missing"])
    return result
