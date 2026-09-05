"""Pydantic request and response schemas for Inforsight model serving gateway."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


ADR_0002_AUTHORITY_BOUNDARY_NOTICE = "ADR_0002_REQUIRES_HUMAN_REVIEW"


class RawFeatures(BaseModel):
    """Raw observation feature vector ingested by the model serving gateway."""
    model_config = ConfigDict(extra="forbid")

    # Numeric features
    tenure_days: float = Field(..., ge=0.0, description="Policy tenure in years scaled or raw days")
    premium_amount_cents: float = Field(..., ge=0.0, description="Premium amount")
    recent_delay_days: float = Field(..., ge=0.0, description="Recent delay in days")
    recent_failed_payment_count: float = Field(..., ge=0.0, description="Failed payment count")
    recent_retry_count: float = Field(..., ge=0.0, description="Retry count")
    recent_recovery_count: float = Field(..., ge=0.0, description="Recovery count")
    arrears_duration_days: float = Field(..., ge=0.0, description="Arrears duration")
    rolling_on_time_rate: float = Field(..., ge=0.0, le=1.0, description="Rolling on-time payment rate [0.0, 1.0]")
    rolling_payment_count: float = Field(..., ge=0.0, description="Rolling payment count")
    recent_notice_count: float = Field(..., ge=0.0, description="Notice count")
    recent_contact_count: float = Field(..., ge=0.0, description="Contact count")
    payment_attribute_missing: float = Field(..., ge=0.0, le=1.0, description="Payment missing flag (0 or 1)")
    contact_attribute_missing: float = Field(..., ge=0.0, le=1.0, description="Contact missing flag (0 or 1)")

    # Categorical features
    product_type: str = Field(..., description="Product category (e.g. fictional_term_life, fictional_whole_life)")
    billing_frequency: str = Field(..., description="Billing cadence (monthly, quarterly, semiannual, annual)")
    notice_category: str = Field(..., description="Notice category (billing_reminder, grace_warning, none)")
    contact_category: str = Field(..., description="Contact category (none, service_request)")

    def to_feature_dict(self) -> dict[str, Any]:
        return self.model_dump()


class ScoreRequest(BaseModel):
    """Single policy scoring request."""
    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(..., min_length=1, description="Unique policy identifier")
    as_of_date: str = Field(..., description="Point-in-time timestamp (ISO 8601 UTC)")
    features: RawFeatures


class BatchScoreRequest(BaseModel):
    """Vectorized batch policy scoring request."""
    model_config = ConfigDict(extra="forbid")

    requests: list[ScoreRequest] = Field(..., min_length=1, max_length=1000, description="Batch of scoring requests")


class DriverDetail(BaseModel):
    feature_name: str
    attribution_log_odds: float


class ScoreResponse(BaseModel):
    """Single policy scoring response enforcing ADR 0002 boundary markers."""
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    as_of_date: str
    calibrated_probability: float
    raw_logit: float
    calibrated_logit: float
    risk_tier: str
    review_queue_eligibility: dict[str, bool]
    root_attributions_log_odds: dict[str, float]
    root_centered_shap: dict[str, float]
    top_risk_drivers: list[DriverDetail]
    top_protective_drivers: list[DriverDetail]

    # ADR 0002 Invariant Boundary Markers
    authorized_to_act: Literal[False] = Field(
        default=False,
        description="Strict ADR 0002 invariant: Predictive model has ZERO authority to alter policies or contact customers."
    )
    action_authority_boundary: Literal["ADR_0002_REQUIRES_HUMAN_REVIEW"] = Field(
        default=ADR_0002_AUTHORITY_BOUNDARY_NOTICE,
        description="ADR 0002 governance boundary requiring licensed human caseworker review."
    )


class BatchScoreResponse(BaseModel):
    """Batch scoring response envelope."""
    model_config = ConfigDict(extra="forbid")

    count: int
    scores: list[ScoreResponse]


class HealthResponse(BaseModel):
    """Liveness probe and model bundle integrity verification response."""
    status: str
    bundle_id: str
    bundle_sha256: str
    bundle_version: str
    engine_status: str


class ModelInfoResponse(BaseModel):
    """Detailed model bundle metadata, contract versions, risk tiers, and authority boundaries."""
    bundle_id: str
    bundle_version: str
    created_at_utc: str
    feature_count: int
    ordered_columns: list[str]
    numeric_features: list[str]
    categorical_features: list[str]
    risk_tiers: list[dict[str, Any]]
    review_queues: list[dict[str, Any]]
    authority_boundaries: dict[str, str]
