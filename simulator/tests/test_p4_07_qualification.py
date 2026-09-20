import unittest

from scripts.p4_07_qualification import (
    CONTRACT_VERSION,
    evaluate_gates,
    manifest,
    qualification_report,
    validate_measurement_evidence,
    validate_contract,
    workload_digest,
)


class P407QualificationTests(unittest.TestCase):
    def test_contract_preflight_passes(self) -> None:
        self.assertEqual(validate_contract(), [])

    def test_manifest_is_deterministic_and_bound(self) -> None:
        first = manifest()
        second = manifest()
        self.assertEqual(first, second)
        self.assertEqual(first["contract_version"], CONTRACT_VERSION)
        self.assertEqual(len(first["workload"]["workload_sha256"]), 64)
        self.assertEqual(len(first["manifest_sha256"]), 64)

    def test_workload_is_100000_policy_and_200000_event_bound(self) -> None:
        workload = manifest()["workload"]
        self.assertEqual(workload["policy_count"], 100_000)
        self.assertEqual(workload["event_count"], 200_000)
        self.assertEqual(workload["final_holdout"], "not_materialized")
        self.assertEqual(workload["workload_sha256"], workload_digest())

    def test_missing_measurements_fail_closed(self) -> None:
        result = evaluate_gates(None)
        self.assertEqual(result["decision"], "stop")
        self.assertEqual(result["gates_passed"], 0)
        self.assertTrue(all(item["disposition"] == "insufficient_evidence" for item in result["results"]))

    def test_all_gate_measurements_pass_only_when_exactly_valid(self) -> None:
        result = evaluate_gates(
            {
                "events_per_second": 5_000,
                "p99_latency_ms": 50,
                "unauthorized_dispatches": 0,
                "undetected_tamper_events": 0,
                "unreconciled_events": 0,
                "parity_mismatches": 0,
            }
        )
        self.assertEqual(result["decision"], "proceed")
        self.assertEqual(result["gates_passed"], 6)

    def test_threshold_or_authority_failure_stops(self) -> None:
        measurements = {
            "events_per_second": 4_999.9,
            "p99_latency_ms": 50.1,
            "unauthorized_dispatches": 1,
            "undetected_tamper_events": 0,
            "unreconciled_events": 0,
            "parity_mismatches": 0,
        }
        result = evaluate_gates(measurements)
        self.assertEqual(result["decision"], "stop")
        self.assertEqual(result["gates_passed"], 3)

    def test_report_never_authorizes_external_execution(self) -> None:
        report = qualification_report({"events_per_second": 5_000})
        self.assertEqual(report["gate_evaluation"]["decision"], "stop")
        self.assertFalse(report["evidence_valid"])
        self.assertFalse(report["release_authorized"])
        self.assertIn("Synthetic qualification", report["claim_boundary"])

    def test_measurements_require_bound_distributed_evidence(self) -> None:
        measurements = {
            "run_id": "run-001",
            "measurement_source": "distributed_compose",
            "topology_identity": "compose-sha256:topology",
            "workload_sha256": manifest()["workload"]["workload_sha256"],
            "observed_event_count": 200_000,
            "dropped_event_count": 0,
            "measurement_window_seconds": 40.0,
            "authority_probe_count": 100,
            "tamper_probe_count": 10,
            "restart_probe_count": 3,
            "parity_fixture_count": 20,
            "events_per_second": 5_000,
            "p99_latency_ms": 50,
            "unauthorized_dispatches": 0,
            "undetected_tamper_events": 0,
            "unreconciled_events": 0,
            "parity_mismatches": 0,
        }
        self.assertEqual(validate_measurement_evidence(measurements), [])
        report = qualification_report(measurements)
        self.assertTrue(report["evidence_valid"])
        self.assertEqual(report["gate_evaluation"]["decision"], "proceed")

    def test_mismatched_workload_or_dropped_event_stops_report(self) -> None:
        measurements = {
            "run_id": "run-002",
            "measurement_source": "distributed_testcontainers",
            "topology_identity": "testcontainers-sha256:topology",
            "workload_sha256": "wrong",
            "observed_event_count": 200_000,
            "dropped_event_count": 1,
            "measurement_window_seconds": 40.0,
            "authority_probe_count": 1,
            "tamper_probe_count": 1,
            "restart_probe_count": 1,
            "parity_fixture_count": 1,
        }
        violations = validate_measurement_evidence(measurements)
        self.assertIn("measurement workload identity mismatch", violations)
        self.assertIn("dropped events are not permitted", violations)

    def test_non_numeric_measurements_fail_closed(self) -> None:
        result = evaluate_gates({"events_per_second": "5000"})
        self.assertEqual(result["decision"], "stop")
        self.assertEqual(result["results"][0]["disposition"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
