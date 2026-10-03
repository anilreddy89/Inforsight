"""Replay a fictional, review-only case through the local control plane.

Requires the P4-06 Compose topology with the persistence profile. The agent
abstains because this harness has no trusted rules allowlist or case evidence.
"""

from __future__ import annotations

import json
import sys
from urllib.request import Request, urlopen

from agents.control_plane_bridge import local_http_transport, submit_review_draft
from agents.workflow import CaseInput, build_review_draft


BASE = "http://127.0.0.1:8080"
CUTOFF = "2026-09-25T00:00:00Z"


def request(method: str, path: str, body: dict | None = None) -> dict:
    encoded = None if body is None else json.dumps(body).encode("utf-8")
    req = Request(BASE + path, data=encoded, method=method,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as response:
        return json.load(response)


def run() -> dict:
    triage = request("POST", "/api/v1/cases/triage", {
        "as_of_date": CUTOFF, "policy_ids": ["fictional-demo-policy"]})
    assert triage["total_evaluated"] == 1
    case_id = triage["cases"][0]["case_id"]
    path = f"/api/v1/cases/{case_id}"
    brief = request("GET", path)
    assert brief["current_state"] == "RECOMMENDED"
    assert brief["authorized_to_act"] is False

    from datetime import datetime, timezone
    case = CaseInput(case_id, datetime(2026, 9, 25, tzinfo=timezone.utc),
                     (), (), (), (), (), 1.0)
    draft = build_review_draft(case)
    assert draft.status == "ABSTAIN" and draft.authorized_to_act is False
    recorded = submit_review_draft(draft, expected_case_version=0,
                                   idempotency_key="p5-04-local-demo-draft",
                                   transport=local_http_transport(BASE))
    assert recorded["draft"]["status"] == "ABSTAIN"
    assert request("GET", path)["authorized_to_act"] is False
    assert request("GET", path + "/agent-drafts")["draft"]["status"] == "ABSTAIN"

    decision = request("POST", path + "/decision", {
        "reviewer_id": "fictional-reviewer", "decision": "REJECTED",
        "selected_action": "abstain", "expected_case_version": 0,
        "idempotency_key": "p5-04-local-demo-review"})
    assert decision["transition_status"] == "DISMISSED"
    assert decision["authorized_to_act"] is False
    audit_hash = decision["audit_record_hash"]
    assert len(audit_hash) == 64 and all(char in "0123456789abcdef" for char in audit_hash)
    assert request("GET", path)["current_state"] == "DISMISSED"
    return {"case_id": case_id, "score": brief["calibrated_probability"],
            "draft_status": draft.status, "human_decision": "REJECTED",
            "audit_record_hash": audit_hash, "authorized_to_act": False}


if __name__ == "__main__":
    try:
        print(json.dumps(run(), indent=2, sort_keys=True))
    except Exception as error:
        print(f"P5-04 local demo failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
