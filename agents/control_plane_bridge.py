"""Opt-in local bridge from a validated review draft to the Java review queue.

The HTTP boundary does not authenticate P5-01 provenance. The Java service
stores this as untrusted advisory material and never turns it into approval.
"""

from __future__ import annotations

import json
from typing import Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

from agents.workflow import ReviewDraft


def review_payload(draft: ReviewDraft, *, expected_case_version: int, idempotency_key: str) -> dict:
    if expected_case_version < 0 or not idempotency_key or len(idempotency_key) > 128:
        raise ValueError("invalid case version or idempotency key")
    if draft.authorized_to_act or not draft.human_review_required:
        raise ValueError("agent draft cannot authorize action")
    return {
        "contract_version": draft.contract_version,
        "case_id": draft.case_id,
        "expected_case_version": expected_case_version,
        "status": draft.status,
        "action_id": draft.action_id,
        "reason_codes": list(draft.reason_codes),
        "evidence_source_ids": list(draft.evidence_source_ids),
        "procedure_citations": list(draft.procedure_citations),
        "authorized_to_act": False,
        "human_review_required": True,
        "idempotency_key": idempotency_key,
    }


def submit_review_draft(draft: ReviewDraft, *, expected_case_version: int,
                        idempotency_key: str, transport: Callable[[str, bytes], dict]) -> dict:
    """Submit only through an explicitly supplied, bounded transport."""
    payload = review_payload(draft, expected_case_version=expected_case_version,
                             idempotency_key=idempotency_key)
    path = f"/api/v1/cases/{quote(draft.case_id, safe='')}/agent-drafts"
    result = transport(path, json.dumps(payload, sort_keys=True).encode("utf-8"))
    if (result.get("case_id") != draft.case_id or result.get("authorized_to_act") is not False
            or result.get("case_version") != expected_case_version):
        raise ValueError("control-plane response does not match the review-only case")
    return result


def local_http_transport(base_url: str, *, timeout_seconds: float = 2.0) -> Callable[[str, bytes], dict]:
    """Explicit loopback-only local demo transport; no credentials or cloud use."""
    if base_url not in {"http://127.0.0.1:8080", "http://localhost:8080"} or not 0 < timeout_seconds <= 10:
        raise ValueError("only the local control plane and bounded timeout are supported")

    def send(path: str, body: bytes) -> dict:
        request = Request(base_url + path, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=timeout_seconds) as response:
            result = json.load(response)
        return result

    return send
