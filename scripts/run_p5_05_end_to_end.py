"""One fictional event through trusted Java rules, bounded agent, and human review."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError
from uuid import uuid4

from agents.control_plane_bridge import local_http_transport, review_payload, submit_review_draft
from agents.workflow import CaseInput, Fact, Procedure, build_review_draft
from scripts.run_p5_04_local_demo import request


def run() -> dict:
    identity = uuid4().hex
    event_id = "fictional-event-" + identity
    policy_id = "fictional-policy-" + identity
    event = {
        "event_id": event_id, "policy_id": policy_id,
        "as_of": "2026-09-25T00:00:00Z", "observed_at": "2026-09-20T00:00:00Z",
        "payment_status": "late", "status": "active", "tenure_days": 365,
        "has_active_claim": False, "has_legal_hold": False,
        "has_registered_dispute": False, "sms_opt_out": False,
        "email_opt_out": False, "phone_opt_out": False, "dnc_registered": False,
    }
    handoff = request("POST", "/api/v1/demo/events", event)
    case_id = handoff["case_id"]
    assert handoff["policy_id"] == policy_id and handoff["event_id"] == event_id
    assert handoff["contract_version"] == "1.0.0"
    assert handoff["authorized_to_act"] is False
    assert request("GET", f"/api/v1/demo/cases/{case_id}/handoff") == handoff
    for bad_event in ({**event, "event_id": "future-" + identity,
                       "observed_at": "2026-09-26T00:00:00Z"},
                      {**event, "event_id": "missing-" + identity,
                       "has_legal_hold": None}):
        try:
            request("POST", "/api/v1/demo/events", bad_event)
            raise AssertionError("invalid event was accepted")
        except HTTPError as error:
            assert error.code == 400
    try:
        request("POST", "/api/v1/demo/events", {**event, "policy_id": "conflicting-policy-" + identity})
        raise AssertionError("conflicting event identity was accepted")
    except HTTPError as error:
        assert error.code == 409

    def parse_time(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    as_of = parse_time(handoff["as_of"])
    observed = parse_time(handoff["observed_at"])
    procedure_id, version = handoff["procedure_citation"].split("@")
    case = CaseInput(
        case_id=case_id, as_of=as_of,
        facts=(Fact("payment_status", handoff["payment_status"], observed, event_id),),
        procedures=(Procedure(procedure_id, version, parse_time(handoff["procedure_effective_from"]),
                              parse_time(handoff["procedure_effective_until"]),
                              tuple(action for action in handoff["allowed_actions"] if action != "abstain"),
                              handoff["procedure_text"]),),
        allowed_actions=tuple(handoff["allowed_actions"]),
        required_fact_keys=("payment_status",),
        minimum_procedure_versions=((procedure_id, version),), confidence=0.95)
    draft = build_review_draft(case)
    assert draft.status == "DRAFT_FOR_REVIEW"
    assert draft.action_id in handoff["allowed_actions"] and draft.authorized_to_act is False
    forged = review_payload(draft, expected_case_version=0, idempotency_key="forged-" + identity)
    forged["action_id"] = "invented_action"
    try:
        request("POST", f"/api/v1/cases/{case_id}/agent-drafts", forged)
        raise AssertionError("invented agent action was accepted")
    except HTTPError as error:
        assert error.code == 400
    recorded = submit_review_draft(draft, expected_case_version=0,
                                   idempotency_key="p5-05-" + identity,
                                   transport=local_http_transport("http://127.0.0.1:8080"))
    assert recorded["snapshot_id"] == handoff["snapshot_id"]
    assert recorded["draft"]["action_id"] == draft.action_id
    assert request("GET", f"/api/v1/cases/{case_id}")["authorized_to_act"] is False

    try:
        request("POST", f"/api/v1/cases/{case_id}/decision", {
            "reviewer_id": "fictional-reviewer", "decision": "OVERRIDDEN",
            "selected_action": "invented_action", "expected_case_version": 0,
            "idempotency_key": "invalid-override-" + identity})
        raise AssertionError("invalid override was accepted")
    except HTTPError as error:
        assert error.code == 400
    assert request("GET", f"/api/v1/cases/{case_id}")["current_state"] == "RECOMMENDED"

    decision = request("POST", f"/api/v1/cases/{case_id}/decision", {
        "reviewer_id": "fictional-reviewer", "decision": "REJECTED",
        "selected_action": "abstain", "expected_case_version": 0,
        "idempotency_key": "human-reject-" + identity})
    assert decision["transition_status"] == "DISMISSED"
    assert decision["authorized_to_act"] is False
    assert len(decision["audit_record_hash"]) == 64
    audit = request("GET", f"/api/v1/demo/cases/{case_id}/audit")
    assert audit["valid"] is True
    assert audit["events"] == ["AGENT_DRAFT_RECORDED", "HUMAN_DECISION_RECORDED"]
    assert all(handoff["snapshot_id"] in entry["canonical_payload"] for entry in audit["entries"])
    return {"case_id": case_id, "event_id": event_id,
            "snapshot_id": handoff["snapshot_id"], "draft_action": draft.action_id,
            "human_decision": "REJECTED", "audit_verified": True,
            "authorized_to_act": False}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
