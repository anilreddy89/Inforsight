"""FastAPI Model Serving and Inference Gateway for Inforsight."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from inforsight_simulator.bundle import ModelBundle, BundledInferenceEngine, ScoringResult
from serving.models import (
    ADR_0002_AUTHORITY_BOUNDARY_NOTICE,
    BatchScoreRequest,
    BatchScoreResponse,
    DriverDetail,
    HealthResponse,
    ModelInfoResponse,
    ScoreRequest,
    ScoreResponse,
)

DEFAULT_BUNDLE_PATH = (
    Path(__file__).resolve().parent.parent / "docs" / "experiments" / "phase-02-10-model-bundle.json"
)

# Global engine state
_bundle: ModelBundle | None = None
_engine: BundledInferenceEngine | None = None
_bundle_sha256: str = ""


def get_bundle_path() -> Path:
    env_path = os.getenv("INFORSIGHT_MODEL_BUNDLE_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    return DEFAULT_BUNDLE_PATH


def load_engine(bundle_path: Path | str | None = None) -> tuple[ModelBundle, BundledInferenceEngine, str]:
    target_path = Path(bundle_path) if bundle_path else get_bundle_path()
    if not target_path.exists():
        raise FileNotFoundError(f"Model bundle not found at: {target_path}")
    raw_bytes = target_path.read_bytes()
    import hashlib
    digest = hashlib.sha256(raw_bytes).hexdigest()
    bundle = ModelBundle.load(target_path)
    engine = BundledInferenceEngine(bundle)
    return bundle, engine, digest


def create_app(bundle_path: Path | str | None = None) -> FastAPI:
    global _bundle, _engine, _bundle_sha256
    _bundle, _engine, _bundle_sha256 = load_engine(bundle_path)

    app = FastAPI(
        title="Inforsight Model Serving Gateway",
        description=(
            "High-throughput, zero-dependency REST inference gateway hosting the frozen "
            "Inforsight Conservation Risk Model with strict ADR 0002 non-authority boundaries."
        ),
        version="1.0.0",
    )

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    def health_check() -> HealthResponse:
        if _engine is None or _bundle is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Engine not loaded")
        return HealthResponse(
            status="healthy",
            bundle_id=_bundle.bundle_id,
            bundle_sha256=_bundle_sha256,
            bundle_version=_bundle.bundle_version,
            engine_status="ready",
        )

    @app.get("/v1/model/info", response_model=ModelInfoResponse, tags=["Model Info"])
    def model_info() -> ModelInfoResponse:
        if _engine is None or _bundle is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Engine not loaded")
        b = _bundle
        return ModelInfoResponse(
            bundle_id=b.bundle_id,
            bundle_version=b.bundle_version,
            created_at_utc=b.created_at_utc,
            feature_count=len(b.preprocessor.ordered_columns),
            ordered_columns=list(b.preprocessor.ordered_columns),
            numeric_features=list(b.preprocessor.numeric.keys()),
            categorical_features=list(b.preprocessor.categorical.keys()),
            risk_tiers=[t.to_dict() if hasattr(t, "to_dict") else {
                "name": t.name, "min_prob": t.min_prob, "max_prob": t.max_prob, "action": t.action
            } for t in b.operational_policy.risk_tiers],
            review_queues=[q.to_dict() if hasattr(q, "to_dict") else {
                "capacity_percentile": q.capacity_percentile,
                "cutoff_probability": q.cutoff_probability,
                "expected_precision": q.expected_precision,
                "expected_recall": q.expected_recall,
                "lift": q.lift,
            } for q in b.operational_policy.review_queues],
            authority_boundaries=dict(b.operational_policy.authority_boundaries),
        )

    def _format_scoring_response(req: ScoreRequest, result: ScoringResult) -> ScoreResponse:
        return ScoreResponse(
            policy_id=req.policy_id,
            as_of_date=req.as_of_date,
            calibrated_probability=round(result.calibrated_probability, 6),
            raw_logit=round(result.raw_logit, 6),
            calibrated_logit=round(result.calibrated_logit, 6),
            risk_tier=result.risk_tier,
            review_queue_eligibility=result.review_queue_eligibility,
            root_attributions_log_odds={k: round(v, 6) for k, v in result.root_attributions_log_odds.items()},
            root_centered_shap={k: round(v, 6) for k, v in result.root_centered_shap.items()},
            top_risk_drivers=[
                DriverDetail(feature_name=f, attribution_log_odds=round(v, 6))
                for f, v in result.top_risk_drivers
            ],
            top_protective_drivers=[
                DriverDetail(feature_name=f, attribution_log_odds=round(v, 6))
                for f, v in result.top_protective_drivers
            ],
            authorized_to_act=False,
            action_authority_boundary=ADR_0002_AUTHORITY_BOUNDARY_NOTICE,
        )

    @app.post("/v1/score", response_model=ScoreResponse, tags=["Scoring"])
    def score_single(req: ScoreRequest) -> ScoreResponse:
        if _engine is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Engine not loaded")
        raw_map = req.features.to_feature_dict()
        try:
            result = _engine.score_record(raw_map)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Inference error: {str(e)}")
        return _format_scoring_response(req, result)

    @app.post("/v1/score/batch", response_model=BatchScoreResponse, tags=["Scoring"])
    def score_batch_endpoint(req: BatchScoreRequest) -> BatchScoreResponse:
        if _engine is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Engine not loaded")
        raw_maps = [r.features.to_feature_dict() for r in req.requests]
        try:
            results = _engine.score_batch(raw_maps)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Batch inference error: {str(e)}")
        scores = [_format_scoring_response(r, res) for r, res in zip(req.requests, results)]
        return BatchScoreResponse(count=len(scores), scores=scores)

    return app


app = create_app()
