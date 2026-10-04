"""Read-only source projection, modeled economics, and bounded agent worker.

This service has no credentials, connector, database, or execution tools. Java
owns ingestion, durable orchestration, rules, allocation, and human decisions.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agents.workflow import CaseInput, Fact, Procedure, build_review_draft
from inforsight_simulator.domain_snapshot import (
    LEGACY_PROFILE, V6_PROFILE, reconstruct_domain_snapshot, select_visible_events,
)
from inforsight_simulator.economics import load_economics_resource_contract
from inforsight_simulator.optimization.uplift import estimate_treatment_effect
from inforsight_simulator.safety_evidence import SAFETY_FIELDS, reconstruct_safety_evidence
from inforsight_simulator.semantic_catalog import (
    PREPROCESSING_PROFILE_ID, canonical_json_bytes, load_semantic_catalog,
)
from inforsight_simulator.v6_corpus import reconstruct_v6_features

VERSION = "1.0.0"
PROJECTION_ID = "fictional-dual-profile-projection/1.0.0"
WORKFLOW_ID = "inforsight-bounded-agent/1.0.0"
WORKER_ID = "bounded-worker-" + uuid4().hex
ROOT = Path(__file__).resolve().parents[1]
CATALOG = load_semantic_catalog(repository_root=ROOT)
CATALOG_FILE_SHA256 = sha256((ROOT / "data-contracts/rh/v1/semantic-catalog.json").read_bytes()).hexdigest()
ECONOMICS = load_economics_resource_contract(repository_root=ROOT, catalog=CATALOG)
CUTOFF = datetime(2026, 9, 25, 12, tzinfo=timezone.utc)
PROCEDURE_ID = "fictional-local-review"
PROCEDURE_VERSION = "1.0.0"
PROCEDURE_TEXT = (
    "Fictional local review procedure. A proposed action requires complete safety "
    "evidence, deterministic eligibility, and portfolio allocation. A human may "
    "approve the fictional recommendation, reject it, or request information. "
    "No customer contact or external execution is available in this demonstration."
)


def timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC timestamp required")
    return parsed.astimezone(timezone.utc)


def digest(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def producer() -> dict:
    return {"service": "demo-runtime", "version": VERSION, "worker_id": WORKER_ID}


class BoundedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SafeOverrides(BoundedModel):
    premium_amount_cents: int = Field(default=12500, ge=1000, le=100000, strict=True)
    delay_days: int = Field(default=15, ge=1, le=45, strict=True)


class ScenarioRequest(BoundedModel):
    scenario_id: Literal["late_payment", "missing_evidence", "legal_hold"]
    policy_id: str = Field(pattern=r"^pol_[a-z0-9]{12,64}$")
    event_id: str = Field(pattern=r"^evt_[a-z0-9]{12,64}$")
    overrides: SafeOverrides = Field(default_factory=SafeOverrides)


class SourceHistory(BoundedModel):
    policy_events: list[dict[str, Any]] = Field(min_length=1, max_length=128)
    payment_events: list[dict[str, Any]] = Field(min_length=1, max_length=128)
    safety_events: list[dict[str, Any]] = Field(max_length=128)


class ProjectRequest(BoundedModel):
    history: SourceHistory
    as_of: str
    policy_id: str
    event_id: str
    correlation_id: str | None = None


class ValueRequest(BoundedModel):
    snapshot: dict[str, Any]
    score: dict[str, Any]
    rules: list[dict[str, Any]] = Field(max_length=16)


class DraftRequest(ValueRequest):
    case_id: str = Field(min_length=1, max_length=128)
    case_version: int = Field(ge=0)
    event_id: str
    allocation: dict[str, Any]


def _source_event(policy_id: str, seed: str, kind: str, when: datetime,
                  payload: dict, *, profile: str = "6.0.0", event_id: str | None = None) -> dict:
    event = {"schema_version": profile,
             "event_id": event_id or "evt_" + sha256(seed.encode()).hexdigest()[:32],
             "policy_id": policy_id, "event_type": kind,
             "effective_at": timestamp(when), "ingested_at": timestamp(when), "payload": payload}
    if profile == "legacy":
        event["schema_version"] = "1.0.0"
        event["occurred_at"] = timestamp(when)
    return event


def scenario(req: ScenarioRequest) -> dict:
    """Generate bounded fictional source facts; never generate score/outcome states."""
    issued = CUTOFF - timedelta(days=365)
    base = {"billing_frequency": "monthly", "premium_amount_cents": req.overrides.premium_amount_cents,
            "currency": "USD"}
    policy = [_source_event(req.policy_id, req.event_id + "policy", "policy.issued", issued,
                            {**base, "product_variant": "fictional_term_life", "initial_status": "active"},
                            profile="legacy")]
    payments = [_source_event(req.policy_id, req.event_id + "billing", "policy.issued", issued,
                              {**base, "product_type": "fictional_term_life"})]
    for ordinal in range(1, 6):
        when = CUTOFF - timedelta(days=(6 - ordinal) * 30)
        payments.append(_source_event(req.policy_id, req.event_id + f"payment{ordinal}",
                                      "payment.recorded", when,
                                      {"arrears_days": 0, "delay_days": 0, "failed": 0, "on_time": 1,
                                       "recovered": 0, "retry": 0, "scheduled_opportunity_ordinal": ordinal}))
    trigger = _source_event(req.policy_id, req.event_id, "payment.recorded", CUTOFF,
                            {"arrears_days": req.overrides.delay_days, "delay_days": req.overrides.delay_days,
                             "failed": 1, "on_time": 0, "recovered": 0, "retry": 0,
                             "scheduled_opportunity_ordinal": 6}, event_id=req.event_id)
    payments.append(trigger)
    # Later recovery is retained as source evidence but must never leak into the cutoff.
    payments.append(_source_event(req.policy_id, req.event_id + "later", "payment.recorded",
                                  CUTOFF + timedelta(days=2),
                                  {"arrears_days": 0, "delay_days": 0, "failed": 0, "on_time": 0,
                                   "recovered": 1, "retry": 1, "scheduled_opportunity_ordinal": 7}))
    safety_facts = {name: False for name in SAFETY_FIELDS}
    if req.scenario_id == "legal_hold":
        safety_facts["has_legal_hold"] = True
    if req.scenario_id == "missing_evidence":
        safety_facts.pop("has_legal_hold")
    safety = [_source_event(req.policy_id, req.event_id + "safety", "safety.facts_recorded",
                            CUTOFF - timedelta(days=1), safety_facts, profile="1.0.0")]
    return {"scenario_id": req.scenario_id, "policy_id": req.policy_id, "event_id": req.event_id,
            "as_of": timestamp(CUTOFF), "source_event": trigger,
            "history": {"policy_events": policy, "payment_events": payments, "safety_events": safety},
            "fictional": True, "producer": producer(), "authorized_to_act": False}


def project(req: ProjectRequest) -> dict:
    cutoff = parse_time(req.as_of)
    domain = reconstruct_domain_snapshot(req.history.policy_events, policy_id=req.policy_id,
                                         as_of=cutoff, source_profile=LEGACY_PROFILE, catalog=CATALOG)
    payment = reconstruct_domain_snapshot(req.history.payment_events, policy_id=req.policy_id,
                                          as_of=cutoff, source_profile=V6_PROFILE, catalog=CATALOG)
    if domain is None or payment is None:
        raise ValueError("issuance evidence is unavailable at observation time")
    for field in ("policy_id", "issued_at", "premium_amount_cents", "billing_frequency", "product_type"):
        if getattr(domain, field) != getattr(payment, field):
            raise ValueError("source profiles disagree on " + field)
    visible = select_visible_events(req.history.payment_events, policy_id=req.policy_id,
                                   as_of=cutoff, source_profile=V6_PROFILE)
    if req.event_id not in {event["event_id"] for event in visible}:
        raise ValueError("submitted event is unavailable at observation time")
    features, lineage = reconstruct_v6_features(visible, cutoff)
    safety = reconstruct_safety_evidence(req.history.safety_events, policy_id=req.policy_id,
                                        as_of=timestamp(cutoff), snapshot_id=domain.snapshot_id)
    facts = {name: getattr(safety, name) for name in SAFETY_FIELDS}
    snapshot = {
        "projection_contract": PROJECTION_ID, "snapshot_version": domain.snapshot_version,
        "catalog_version": domain.catalog_version, "catalog_sha256": domain.catalog_sha256,
        "catalog_file_sha256": CATALOG_FILE_SHA256,
        "policy_id": domain.policy_id, "as_of": domain.as_of, "status": domain.status,
        "tenure_days": domain.tenure_days, "premium_amount_cents": domain.premium_amount_cents,
        "annual_premium_cents": domain.annual_premium_cents, "billing_frequency": domain.billing_frequency,
        "product_type": domain.product_type, "days_past_due": payment.days_past_due,
        "in_grace_period": domain.in_grace_period, "safety": facts,
        "domain_snapshot": domain.to_dict(), "payment_snapshot": payment.to_dict(),
        "safety_evidence": safety.to_dict(), "feature_lineage": lineage,
        "recent_contact_count": features.recent_contact_count,
    }
    visible_ids = {item.event_id for item in domain.provenance} | {item.event_id for item in payment.provenance}
    visible_ids.update(source for _, sources in safety.field_evidence for source in sources)
    snapshot["source_event_ids"] = sorted(visible_ids)
    snapshot["source_observed_at"] = {
        item["event_id"]: item["ingested_at"]
        for events in req.history.model_dump().values() for item in events if item["event_id"] in visible_ids
    }
    snapshot["snapshot_id"] = digest(snapshot)
    all_ids = {item["event_id"] for events in req.history.model_dump().values() for item in events}
    context = {"policy_id": domain.policy_id, "as_of": domain.as_of, "status": domain.status,
               "tenure_days": domain.tenure_days, "in_grace_period": domain.in_grace_period,
               "days_past_due": payment.days_past_due, **facts, "last_contact_date": None}
    return {"snapshot": snapshot, "features": asdict(features), "feature_lineage": lineage,
            "context": context, "safety": safety.to_dict(), "source_event_ids": sorted(visible_ids),
            "excluded_event_ids": sorted(all_ids - visible_ids), "feature_stage": "raw-v6-features",
            "preprocessing_profile_id": PREPROCESSING_PROFILE_ID, "producer": producer(),
            "authorized_to_act": False}


def validate_snapshot(snapshot: dict) -> None:
    content = dict(snapshot)
    identity = content.pop("snapshot_id", None)
    if identity != digest(content) or snapshot.get("projection_contract") != PROJECTION_ID:
        raise ValueError("snapshot identity mismatch")
    if snapshot.get("catalog_sha256") != CATALOG.sha256:
        raise ValueError("catalog identity mismatch")


def value(req: ValueRequest) -> dict:
    validate_snapshot(req.snapshot)
    if (req.score.get("policy_id") != req.snapshot["policy_id"]
            or req.score.get("authorized_to_act") is not False
            or parse_time(req.score["as_of_date"]) != parse_time(req.snapshot["as_of"])
            or req.score.get("bundle_digest") != CATALOG.data["preprocessing"]["bundle_file_sha256"]
            or req.score.get("catalog_sha256") != req.snapshot["catalog_file_sha256"]
            or req.score.get("preprocessing_profile_id") != PREPROCESSING_PROFILE_ID):
        raise ValueError("score context or authority mismatch")
    probability = req.score["calibrated_probability"]
    rules = {row["action_type"]: row["eligible"] is True for row in req.rules}
    if set(rules) != set(ECONOMICS.actions_by_type):
        raise ValueError("complete deterministic rule result required")
    candidates = []
    for action_type in ECONOMICS.actions_by_type:
        effect = estimate_treatment_effect(action_type, probability,
                    days_past_due=req.snapshot["days_past_due"] or 0,
                    prior_contact_count=req.snapshot["recent_contact_count"])
        valuation = ECONOMICS.value(policy_id=req.snapshot["policy_id"],
            snapshot_id=req.snapshot["snapshot_id"], snapshot_version=req.snapshot["snapshot_version"],
            catalog_sha256=req.snapshot["catalog_sha256"], action=action_type, effect=effect,
            annual_premium_cents=req.snapshot["annual_premium_cents"])
        candidates.append({"policy_id": req.snapshot["policy_id"], "action_type": action_type,
            "cost_micros": valuation.direct_cost_usd_micros, "personnel_seconds": valuation.personnel_seconds,
            "net_utility_micros": valuation.net_expected_value_usd_micros, "eligible": rules[action_type],
            "valuation": valuation.to_dict()})
    return {"candidates": candidates, "economics_contract_id": ECONOMICS.contract_id,
            "economics_contract_version": ECONOMICS.version, "economics_contract_sha256": ECONOMICS.sha256,
            "metric_id": candidates[0]["valuation"]["metric_id"], "snapshot_id": req.snapshot["snapshot_id"],
            "effect_model": "Existing deterministic modeled uplift; not measured treatment effect",
            "producer": producer(), "authorized_to_act": False}


def draft(req: DraftRequest) -> dict:
    validate_snapshot(req.snapshot)
    snapshot = req.snapshot
    as_of = parse_time(snapshot["as_of"])
    selected = req.allocation.get("selected_action")
    allowed = {item["action_type"] for item in req.rules if item.get("eligible") is True}
    if selected not in allowed:
        raise ValueError("allocated action is outside trusted rules")
    if req.event_id not in {p["event_id"] for p in snapshot["payment_snapshot"]["provenance"]}:
        raise ValueError("submitted event is not snapshot evidence")
    payment_sources = snapshot["payment_snapshot"]["field_evidence"]["days_past_due"]
    if not payment_sources:
        raise ValueError("payment status is missing source evidence")
    payment_source = payment_sources[-1]
    fact_list = [Fact("payment_status", "late" if snapshot["days_past_due"] else "current",
                      parse_time(snapshot["source_observed_at"][payment_source]), payment_source)]
    for key, fact_value in snapshot["safety"].items():
        if fact_value is not None:
            sources = snapshot["safety_evidence"]["field_evidence"][key]
            if not sources:
                raise ValueError("safety fact is missing source evidence")
            fact_list.append(Fact(key, str(fact_value).lower(),
                                  parse_time(snapshot["source_observed_at"][sources[-1]]), sources[-1]))
    procedure = Procedure(PROCEDURE_ID, PROCEDURE_VERSION, datetime(2026, 1, 1, tzinfo=timezone.utc),
                          datetime(2027, 1, 1, tzinfo=timezone.utc),
                          (selected,) if selected != "abstain" else (), PROCEDURE_TEXT)
    # Existing planner requires a confidence gate. 1.0 here explicitly means all
    # deterministic checks apply; it is never exposed as a measured confidence.
    case = CaseInput(req.case_id, as_of, tuple(fact_list), (procedure,),
                     (selected, "abstain") if selected != "abstain" else ("abstain",),
                     ("payment_status", *SAFETY_FIELDS), ((PROCEDURE_ID, PROCEDURE_VERSION),), 1.0)
    result = asdict(build_review_draft(case))
    return {**result, "case_version": req.case_version, "snapshot_id": snapshot["snapshot_id"],
            "workflow_id": WORKFLOW_ID, "producer": producer(),
            "procedure": {"citation": f"{PROCEDURE_ID}@{PROCEDURE_VERSION}", "text": PROCEDURE_TEXT,
                          "effective_from": timestamp(procedure.effective_from),
                          "effective_until": timestamp(procedure.effective_until)},
            "input_digest": digest(req.model_dump()), "generated_at": timestamp(datetime.now(timezone.utc)),
            "confidence_assessment": "Not estimated; deterministic evidence gates"}


app = FastAPI(title="Inforsight fictional demo adapters", version=VERSION)


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "producer": producer(), "catalog_sha256": CATALOG.sha256,
            "external_execution_enabled": False}


def bounded_call(operation, req):
    try:
        return operation(req)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/demo/scenario")
def scenario_endpoint(req: ScenarioRequest) -> dict:
    return bounded_call(scenario, req)


@app.post("/v1/demo/project")
def project_endpoint(req: ProjectRequest) -> dict:
    return bounded_call(project, req)


@app.post("/v1/demo/value")
def value_endpoint(req: ValueRequest) -> dict:
    return bounded_call(value, req)


@app.post("/v1/demo/draft")
def draft_endpoint(req: DraftRequest) -> dict:
    return bounded_call(draft, req)
