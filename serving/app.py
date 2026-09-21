"""FastAPI Model Serving and Inference Gateway for Inforsight."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from inforsight_inference import (
    BundledInferenceEngine,
    ModelBundle,
    RUNTIME_CONTRACT_ID,
    RUNTIME_CONTRACT_VERSION,
    ScoringResult,
    SemanticCatalog,
    load_configured_runtime,
)
from serving.models import (
    ADR_0002_AUTHORITY_BOUNDARY_NOTICE,
    BatchScoreRequest,
    BatchScoreResponse,
    DriverDetail,
    HealthResponse,
    ModelInfoResponse,
    ResolvedOutcomeRequest,
    ResolvedOutcomeResponse,
    ScoreRequest,
    ScoreResponse,
    MinimalScoreResponse,
)
from serving.monitoring import DriftMonitor
from serving.monitoring.monitor import OutcomeJoinError

DEFAULT_BUNDLE_PATH = (
    Path(__file__).resolve().parent.parent / "docs" / "experiments" / "phase-02-10-model-bundle.json"
)

# Global engine state
_bundle: ModelBundle | None = None
_engine: BundledInferenceEngine | None = None
_bundle_sha256: str = ""
_monitor: DriftMonitor | None = None
_catalog: SemanticCatalog | None = None


def load_engine(bundle_path: Path | str | None = None) -> tuple[ModelBundle, BundledInferenceEngine, str]:
    runtime = load_configured_runtime(DEFAULT_BUNDLE_PATH, bundle_path=bundle_path)
    return runtime.bundle, runtime.engine, runtime.bundle_sha256


def create_app(bundle_path: Path | str | None = None) -> FastAPI:
    global _bundle, _engine, _bundle_sha256, _monitor, _catalog
    runtime = load_configured_runtime(DEFAULT_BUNDLE_PATH, bundle_path=bundle_path)
    _bundle, _engine, _bundle_sha256 = (
        runtime.bundle, runtime.engine, runtime.bundle_sha256
    )
    _monitor = DriftMonitor(_bundle)
    _catalog = runtime.catalog

    app = FastAPI(
        title="Inforsight Model Serving Gateway",
        description=(
            "Bounded REST inference gateway hosting the verified frozen "
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
            runtime_contract_id=RUNTIME_CONTRACT_ID,
            runtime_contract_version=RUNTIME_CONTRACT_VERSION,
            bundle_id=_bundle.bundle_id,
            bundle_sha256=_bundle_sha256,
            bundle_version=_bundle.bundle_version,
            catalog_version=_catalog.version if _catalog is not None else "",
            catalog_sha256=_catalog.sha256 if _catalog is not None else "",
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
        if _catalog is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Catalog not loaded")
        tier_id = _catalog.map_risk_tier(
            result.risk_tier, adapter_profile="historical-bundle-display/1.0.0"
        )
        return ScoreResponse(
            policy_id=req.policy_id,
            as_of_date=req.as_of_date,
            calibrated_probability=round(result.calibrated_probability, 6),
            raw_logit=round(result.raw_logit, 6),
            calibrated_logit=round(result.calibrated_logit, 6),
            risk_tier=result.risk_tier,
            risk_tier_id=tier_id,
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
        t0 = time.perf_counter()
        try:
            result = _engine.score_record(raw_map)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Inference error: {str(e)}")
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if _monitor is not None:
            _monitor.record_single_request(latency_ms)
            _monitor.record_score(
                policy_id=req.policy_id,
                observation_id=req.observation_id or req.as_of_date,
                features=raw_map,
                predicted_probability=result.calibrated_probability,
            )
        return _format_scoring_response(req, result)

    @app.post("/v1/score/minimal", response_model=MinimalScoreResponse, tags=["Scoring"])
    def score_minimal(req: ScoreRequest) -> MinimalScoreResponse:
        if _engine is None or _bundle is None or _catalog is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Engine not loaded")
        try:
            result = _engine.score_record(req.features.to_feature_dict())
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Inference error: {str(e)}")
        return MinimalScoreResponse(
            policy_id=req.policy_id,
            as_of_date=req.as_of_date,
            calibrated_probability=round(result.calibrated_probability, 6),
            risk_tier=result.risk_tier,
            risk_tier_id=_catalog.map_risk_tier(result.risk_tier, adapter_profile="historical-bundle-display/1.0.0"),
            bundle_version=_bundle.bundle_version,
            bundle_digest=_bundle_sha256,
        )

    @app.post("/v1/score/batch", response_model=BatchScoreResponse, tags=["Scoring"])
    def score_batch_endpoint(req: BatchScoreRequest) -> BatchScoreResponse:
        if _engine is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Engine not loaded")
        raw_maps = [r.features.to_feature_dict() for r in req.requests]
        t0 = time.perf_counter()
        try:
            results = _engine.score_batch(raw_maps)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Batch inference error: {str(e)}")
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if _monitor is not None:
            _monitor.record_batch_request(latency_ms, len(results))
            for item, raw_map, result in zip(req.requests, raw_maps, results):
                _monitor.record_score(
                    policy_id=item.policy_id,
                    observation_id=item.observation_id or item.as_of_date,
                    features=raw_map,
                    predicted_probability=result.calibrated_probability,
                )
        scores = [_format_scoring_response(r, res) for r, res in zip(req.requests, results)]
        return BatchScoreResponse(count=len(scores), scores=scores)

    @app.post(
        "/v1/monitoring/outcomes",
        response_model=ResolvedOutcomeResponse,
        tags=["Monitoring"],
    )
    def ingest_resolved_outcome(req: ResolvedOutcomeRequest) -> ResolvedOutcomeResponse:
        """Attach a resolved outcome to its exact retained score; no score is created here."""
        if _monitor is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Monitor not initialised")
        try:
            outcome_status = _monitor.ingest_resolved_outcome(
                policy_id=req.policy_id,
                observation_id=req.observation_id,
                model_version=req.model_version,
                observed_outcome=req.observed_outcome,
                resolved_at=req.resolved_at,
            )
        except OutcomeJoinError as exc:
            failure_status = (
                status.HTTP_409_CONFLICT
                if str(exc) in {"MODEL_VERSION_MISMATCH", "OUTCOME_CONFLICT"}
                else status.HTTP_404_NOT_FOUND
            )
            raise HTTPException(status_code=failure_status, detail=str(exc))
        return ResolvedOutcomeResponse(
            status=outcome_status,
            policy_id=req.policy_id,
            observation_id=req.observation_id,
            model_version=req.model_version,
        )

    @app.get("/v1/diagnostics", tags=["Monitoring"])
    def diagnostics() -> JSONResponse:
        """Return inference telemetry, PSI/CSI drift, rolling calibration, and alert summary.

        schema_version: 1.1.0; RH-07 adds evidence counts and insufficient-data states.
        ADR 0002: authorized_to_act is unconditionally False in the alert_summary section.
        """
        if _monitor is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Monitor not initialised")
        report = _monitor.diagnostics_report()
        return JSONResponse(content=report)

    return app




app = create_app()
