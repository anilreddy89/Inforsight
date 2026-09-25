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
REQUIRED_EVIDENCE_FIELDS = (
    "run_id",
    "measurement_source",
    "topology_identity",
    "workload_sha256",
    "observed_event_count",
    "dropped_event_count",
    "measurement_window_seconds",
    "authority_probe_count",
    "tamper_probe_count",
    "restart_probe_count",
    "parity_fixture_count",
    "capabilities",
)


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


def validate_measurement_evidence(measurements: Mapping[str, Any] | None) -> list[str]:
    """Validate the evidence binding required before gate results are trusted."""

    if not isinstance(measurements, Mapping):
        return ["measurements must be a JSON object"]
    expected_workload = manifest()["workload"]
    violations: list[str] = []
    for field in REQUIRED_EVIDENCE_FIELDS:
        if field not in measurements:
            violations.append(f"missing evidence field: {field}")
    if violations:
        return violations
    if not isinstance(measurements["run_id"], str) or not measurements["run_id"]:
        violations.append("run_id must be a non-empty string")
    if measurements["measurement_source"] not in {
        "distributed_testcontainers",
        "distributed_compose",
        "kubernetes_cluster",
    }:
        violations.append("measurement_source must identify a distributed execution harness")
    if not isinstance(measurements["topology_identity"], str) or not measurements["topology_identity"]:
        violations.append("topology_identity must be a non-empty string")
    if measurements["workload_sha256"] != expected_workload["workload_sha256"]:
        violations.append("measurement workload identity mismatch")
    if measurements["observed_event_count"] != expected_workload["event_count"]:
        violations.append("observed event count does not match the frozen workload")
    if measurements["dropped_event_count"] != 0:
        violations.append("dropped events are not permitted")
    if _measurement_number(measurements, "measurement_window_seconds") is None or measurements["measurement_window_seconds"] <= 0:
        violations.append("measurement window must be positive")
    for field in ("authority_probe_count", "tamper_probe_count", "restart_probe_count", "parity_fixture_count"):
        if isinstance(measurements[field], bool) or not isinstance(measurements[field], int) or measurements[field] <= 0:
            violations.append(f"{field} must be a positive integer")
    capabilities = measurements["capabilities"]
    required_capabilities = (
        "kafka_ingress",
        "control_plane_consumer",
        "inference_http",
        "postgres_audit",
        "restart_replay",
        "parity_fixtures",
    )
    if not isinstance(capabilities, Mapping):
        violations.append("capabilities must be an object")
    else:
        for capability in required_capabilities:
            if capabilities.get(capability) is not True:
                violations.append(f"missing runtime capability: {capability}")
    return violations


def qualification_report(measurements: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return a report whose release decision is bounded by gate evidence."""

    stable_manifest = manifest()
    evidence_violations = validate_measurement_evidence(measurements) if measurements is not None else [
        "runtime measurements were not supplied"
    ]
    gate_evaluation = evaluate_gates(measurements)
    if evidence_violations:
        gate_evaluation = dict(gate_evaluation)
        gate_evaluation["decision"] = "stop"
    return {
        "contract_version": CONTRACT_VERSION,
        "manifest_sha256": stable_manifest["manifest_sha256"],
        "workload_sha256": stable_manifest["workload"]["workload_sha256"],
        "measurements": dict(measurements or {}),
        "evidence_valid": not evidence_violations,
        "evidence_violations": evidence_violations,
        "gate_evaluation": gate_evaluation,
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
