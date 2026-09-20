"""P4-07 qualification contract and fail-closed gate evaluator.

This module freezes the qualification *protocol* without pretending that a
local process is a distributed production benchmark.  Runtime measurements
must be supplied by a separately reviewed execution harness; missing or
incomplete measurements always produce a non-passing decision.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


CONTRACT_VERSION = "p4-07-qualification-1.0.0"
WORKLOAD_POLICIES = 100_000
EVENTS_PER_POLICY = 2
WORKLOAD_SEED = 407_2026
THROUGHPUT_MIN_EVENTS_PER_SECOND = 5_000.0
LATENCY_P99_MAX_MS = 50.0


@dataclass(frozen=True)
class GateDefinition:
    gate_id: str
    name: str
    metric: str
    threshold: str


GATES: tuple[GateDefinition, ...] = (
    GateDefinition("E1", "streaming_ingestion_throughput", "events_per_second", ">= 5000"),
    GateDefinition("E2", "end_to_end_latency", "p99_latency_ms", "<= 50"),
    GateDefinition("E3", "authority_isolation", "unauthorized_dispatches", "== 0"),
    GateDefinition("E4", "audit_immutability", "undetected_tamper_events", "== 0"),
    GateDefinition("E5", "fault_tolerance_recovery", "unreconciled_events", "== 0"),
    GateDefinition("E6", "runtime_parity", "parity_mismatches", "== 0"),
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def qualification_config() -> dict[str, Any]:
    """Return the immutable workload and gate configuration."""

    return {
        "contract_version": CONTRACT_VERSION,
        "workload": {
            "policy_count": WORKLOAD_POLICIES,
            "events_per_policy": EVENTS_PER_POLICY,
            "event_count": WORKLOAD_POLICIES * EVENTS_PER_POLICY,
            "seed": WORKLOAD_SEED,
            "namespace": "p4-07-enterprise-scale-synthetic",
            "partitions": 12,
            "final_holdout": "not_materialized",
            "input_class": "fictional_synthetic",
        },
        "gates": [
            {
                "gate_id": gate.gate_id,
                "name": gate.name,
                "metric": gate.metric,
                "threshold": gate.threshold,
            }
            for gate in GATES
        ],
        "authority": {
            "authorized_to_act": False,
            "external_execution_enabled": False,
            "required_human_review": True,
        },
        "runtime_contracts": {
            "kafka": "p4-02",
            "control_plane": "p4-03",
            "persistence_audit": "p4-04",
            "connectors": "p4-05",
            "deployment_baseline": "p4-06",
        },
    }


def workload_digest(config: Mapping[str, Any] | None = None) -> str:
    """Hash the canonical event identity stream without storing 200k events."""

    effective = config or qualification_config()
    workload = effective["workload"]
    seed = workload["seed"]
    namespace = workload["namespace"]
    digest = hashlib.sha256()
    for policy_number in range(workload["policy_count"]):
        policy_id = f"{namespace}:policy:{policy_number:06d}"
        for event_number in range(workload["events_per_policy"]):
            event_id = sha256_text(f"{seed}:{policy_id}:{event_number}")
            digest.update(
                canonical_json(
                    {
                        "event_id": event_id,
                        "event_number": event_number,
                        "policy_id": policy_id,
                    }
                ).encode("utf-8"),
            )
    return digest.hexdigest()


def manifest(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build the stable qualification manifest identity."""

    effective = dict(config or qualification_config())
    workload = dict(effective["workload"])
    workload["workload_sha256"] = workload_digest(effective)
    effective["workload"] = workload
    effective["manifest_sha256"] = sha256_text(canonical_json(effective))
    return effective


def _measurement_number(measurements: Mapping[str, Any], key: str) -> float | None:
    value = measurements.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def evaluate_gates(measurements: Mapping[str, Any] | None) -> dict[str, Any]:
    """Evaluate all gates; incomplete evidence is always a failed gate."""

    values = measurements or {}
    results: list[dict[str, Any]] = []
    for gate in GATES:
        value = _measurement_number(values, gate.metric)
        if value is None:
            passed = False
            disposition = "insufficient_evidence"
        elif gate.gate_id == "E1":
            passed = value >= THROUGHPUT_MIN_EVENTS_PER_SECOND
            disposition = "pass" if passed else "fail"
        elif gate.gate_id == "E2":
            passed = value <= LATENCY_P99_MAX_MS
            disposition = "pass" if passed else "fail"
        else:
            passed = value == 0
            disposition = "pass" if passed else "fail"
        results.append(
            {
                "gate_id": gate.gate_id,
                "metric": gate.metric,
                "observed": value,
                "threshold": gate.threshold,
                "passed": passed,
                "disposition": disposition,
            }
        )
    passed = all(result["passed"] for result in results)
    return {
        "decision": "proceed" if passed else "stop",
        "gates_passed": sum(result["passed"] for result in results),
        "gates_total": len(results),
        "results": results,
    }


def qualification_report(measurements: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return a report whose release decision is bounded by gate evidence."""

    stable_manifest = manifest()
    return {
        "contract_version": CONTRACT_VERSION,
        "manifest_sha256": stable_manifest["manifest_sha256"],
        "workload_sha256": stable_manifest["workload"]["workload_sha256"],
        "measurements": dict(measurements or {}),
        "gate_evaluation": evaluate_gates(measurements),
        "release_authorized": False,
        "claim_boundary": (
            "Synthetic qualification evidence only; no production, customer, "
            "regulatory, or autonomous-execution claim."
        ),
    }


def validate_contract() -> list[str]:
    """Return structural violations in the frozen contract."""

    violations: list[str] = []
    config = qualification_config()
    if config["workload"]["policy_count"] != WORKLOAD_POLICIES:
        violations.append("policy count drift")
    if config["workload"]["event_count"] != WORKLOAD_POLICIES * EVENTS_PER_POLICY:
        violations.append("event count drift")
    if config["workload"]["final_holdout"] != "not_materialized":
        violations.append("final holdout must remain not_materialized")
    if config["authority"] != {
        "authorized_to_act": False,
        "external_execution_enabled": False,
        "required_human_review": True,
    }:
        violations.append("authority boundary drift")
    if tuple(gate.gate_id for gate in GATES) != ("E1", "E2", "E3", "E4", "E5", "E6"):
        violations.append("gate inventory drift")
    stable = manifest()
    if stable["manifest_sha256"] != sha256_text(canonical_json({k: v for k, v in stable.items() if k != "manifest_sha256"})):
        violations.append("manifest self-identity drift")
    if stable["workload"]["workload_sha256"] != workload_digest():
        violations.append("workload digest drift")
    if evaluate_gates(None)["decision"] != "stop":
        violations.append("missing measurements must stop")
    return violations


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

