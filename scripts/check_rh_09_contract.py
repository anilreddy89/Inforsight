#!/usr/bin/env python3
"""Read-only RH-09D consistency checks for provisional P4-01 contracts."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PROTO = (ROOT / "proto/v1/inference_service.proto").read_text(encoding="utf-8")
OPENAPI = (ROOT / "api/openapi/control-plane-v1.yaml").read_text(encoding="utf-8")
ADR = (ROOT / "docs/adr/0014-enterprise-distributed-architecture.md").read_text(encoding="utf-8")
MATRIX = (ROOT / "docs/hardening/rh-09-contract-reconciliation.md").read_text(encoding="utf-8")


def require(text: str, pattern: str, label: str) -> None:
    if not re.search(pattern, text, re.MULTILINE):
        raise SystemExit(f"RH-09D contract check failed: {label}")


require(PROTO, r"optional bool authorized_to_act\s*=\s*4", "presence-aware authority marker")
for tier in ("TIER_1_LOW", "TIER_2_ELEVATED", "TIER_3_HIGH", "TIER_4_CRITICAL"):
    require(OPENAPI, re.escape(tier), f"canonical tier {tier}")
require(OPENAPI, r"bearerAuth", "authentication scheme")
require(OPENAPI, r"idempotency_key", "idempotency key")
require(OPENAPI, r"expected_case_version", "expected case version")
require(ADR, r"provisional until RH-09D/RH-09I acceptance", "provisional ADR status")
require(ADR, r"latency.*not evidence|latency targets", "latency claim boundary")
require(MATRIX, r"input[-/]to[-/]text consistency|input/text consistency", "grounding claim boundary")
print("RH-09D contract consistency check passed.")
