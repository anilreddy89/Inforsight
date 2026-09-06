"""Phase 3.09: Pre-Release System Qualification & Integration Gate.

Exports:
- QualificationGateRunner: Orchestrates end-to-end qualification pipeline.
- GateResult, SystemQualificationResult: Core result dataclasses.
- Evaluators for Gates S1 through S6.
- Manifest and report generation utilities.
"""

from __future__ import annotations

from .gates import (
    GateResult,
    evaluate_gate_s1_authority_isolation,
    evaluate_gate_s2_eligibility_firewall,
    evaluate_gate_s3_capacity_adherence,
    evaluate_gate_s4_audit_tamper_resistance,
    evaluate_gate_s5_latency_sla,
    evaluate_gate_s6_reproducibility,
)
from .manifest import build_qualification_manifest
from .report import generate_qualification_report
from .runner import QualificationRunner, SystemQualificationResult

__all__ = [
    "GateResult",
    "SystemQualificationResult",
    "QualificationRunner",
    "evaluate_gate_s1_authority_isolation",
    "evaluate_gate_s2_eligibility_firewall",
    "evaluate_gate_s3_capacity_adherence",
    "evaluate_gate_s4_audit_tamper_resistance",
    "evaluate_gate_s5_latency_sla",
    "evaluate_gate_s6_reproducibility",
    "build_qualification_manifest",
    "generate_qualification_report",
]
