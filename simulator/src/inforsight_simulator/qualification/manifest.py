"""Cryptographic manifest generator for Phase 3.09 System Qualification."""

from __future__ import annotations

from typing import Any

from inforsight_simulator.audit.serialization import canonical_json_dumps, compute_sha256

from .runner import SystemQualificationResult


def build_qualification_manifest(result: SystemQualificationResult) -> dict[str, Any]:
    """Assemble a canonical cryptographic manifest of qualification outcomes."""
    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "phase": "Phase 3.09",
        "title": "Inforsight Conservation Decision Engine System Qualification Manifest",
        "created_at": result.qualification_timestamp,
        "evaluation_seed": result.seed,
        "cohort_size": result.cohort_size,
        "model_bundle_id": result.bundle_id,
        "model_bundle_sha256": result.bundle_sha256,
        "overall_decision": result.overall_decision,
        "all_gates_passed": result.all_gates_passed,
        "pipeline_digest": result.pipeline_digest,
        "gates": {k: v.to_dict() for k, v in result.gates.items()},
        "allocations_summary": result.allocations_summary,
        "performance_summary": result.performance_summary,
    }

    # Canonical SHA-256 self-digest
    manifest_digest = compute_sha256(canonical_json_dumps(manifest))
    manifest["manifest_digest"] = manifest_digest

    return manifest
