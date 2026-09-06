"""Unit and property tests for cryptographic audit ledger and verification."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from inforsight_simulator.audit.ledger import (
    GENESIS_HASH,
    AuditIntegrityError,
    AuditLedger,
    AuditRecord,
)
from inforsight_simulator.audit.serialization import canonical_json_dumps, compute_sha256
from inforsight_simulator.audit.verifier import AuditTrailVerifier


class TestCryptographicAuditLedger(unittest.TestCase):
    """Tests hash-chaining, tamper-evidence, and persistence of the audit ledger."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_path = Path(self.temp_dir.name) / "test-audit.jsonl"
        self.ledger = AuditLedger(self.log_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_genesis_hash_and_first_entry(self) -> None:
        """Verifies initial state starts at sequence 0 and chains from genesis anchor."""
        self.assertEqual(self.ledger.total_entries, 0)
        self.assertEqual(self.ledger.current_hash, GENESIS_HASH)

        rec0 = self.ledger.append(
            case_id="case_0001",
            policy_id="pol_0001",
            case_event_id="cev_0001",
            from_state="NONE",
            to_state="CREATED",
            timestamp="2026-09-01T10:00:00Z",
        )
        self.assertEqual(rec0.sequence_number, 0)
        self.assertEqual(rec0.prev_hash, GENESIS_HASH)
        self.assertEqual(self.ledger.total_entries, 1)

        # Re-compute expected entry hash manually
        payload = rec0.payload_for_hashing()
        expected_hash = compute_sha256(f"{GENESIS_HASH}{canonical_json_dumps(payload)}")
        self.assertEqual(rec0.entry_hash, expected_hash)
        self.assertEqual(self.ledger.current_hash, expected_hash)

    def test_multi_entry_chaining(self) -> None:
        """Verifies sequential hash chaining across multiple transitions."""
        records = []
        states = [
            ("NONE", "CREATED"),
            ("CREATED", "TRIAGED"),
            ("TRIAGED", "EVIDENCE_ASSEMBLED"),
            ("EVIDENCE_ASSEMBLED", "RECOMMENDED"),
        ]
        for i, (from_s, to_s) in enumerate(states):
            r = self.ledger.append(
                case_id="case_0001",
                policy_id="pol_0001",
                case_event_id=f"cev_{i:04d}",
                from_state=from_s,
                to_state=to_s,
                timestamp=f"2026-09-01T10:{i:02d}:00Z",
            )
            records.append(r)

        self.assertEqual(len(records), 4)
        for i in range(1, 4):
            self.assertEqual(records[i].prev_hash, records[i - 1].entry_hash)
            self.assertEqual(records[i].sequence_number, i)

        # Verifier passes cleanly
        res = AuditTrailVerifier.verify_file(self.log_path)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.total_entries, 4)
        self.assertIsNone(res.error_message)

    def test_tamper_detection_field_mutation(self) -> None:
        """Verifies that altering a single field in an entry breaks the hash chain."""
        for i in range(5):
            self.ledger.append(
                case_id="case_0001",
                policy_id=f"pol_{i:04d}",
                case_event_id=f"cev_{i:04d}",
                from_state="CREATED" if i > 0 else "NONE",
                to_state="TRIAGED" if i > 0 else "CREATED",
                timestamp=f"2026-09-01T10:{i:02d}:00Z",
            )

        # Tamper with line 2 (seq 1) in the log file
        with open(self.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        tampered = json.loads(lines[1])
        tampered["policy_id"] = "pol_TAMPERED"
        lines[1] = json.dumps(tampered) + "\n"

        with open(self.log_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        # Verifier must detect the tamper
        res = AuditTrailVerifier.verify_file(self.log_path)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.violating_sequence_number, 1)
        self.assertIn("tamper detected", res.error_message.lower())

    def test_tamper_detection_entry_deletion(self) -> None:
        """Verifies that deleting an intermediate line breaks sequence monotonicity or hash chain."""
        for i in range(5):
            self.ledger.append(
                case_id="case_0001",
                policy_id=f"pol_{i:04d}",
                case_event_id=f"cev_{i:04d}",
                from_state="NONE" if i == 0 else "CREATED",
                to_state="CREATED" if i == 0 else "TRIAGED",
                timestamp=f"2026-09-01T10:{i:02d}:00Z",
            )

        with open(self.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Delete line 2 (seq 1)
        del lines[1]

        with open(self.log_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        res = AuditTrailVerifier.verify_file(self.log_path)
        self.assertFalse(res.is_valid)
        self.assertIn("sequence number", res.error_message.lower())

    def test_adr_0002_governance_verification_invariants(self) -> None:
        """Verifies verifier catches unauthorized executions missing valid human reviews."""
        # 1. Direct RECOMMENDED -> EXECUTED entry
        rec_bad = {
            "audit_entry_id": "aud_bad01",
            "sequence_number": 0,
            "timestamp": "2026-09-01T10:00:00Z",
            "case_id": "case_bad",
            "policy_id": "pol_bad",
            "case_event_id": "cev_bad",
            "from_state": "RECOMMENDED",
            "to_state": "EXECUTED",
            "decision_context_digest": {},
            "human_review": None,
            "dispatched_action": None,
            "metadata": {},
            "prev_hash": GENESIS_HASH,
        }
        rec_bad["entry_hash"] = compute_sha256(f"{GENESIS_HASH}{canonical_json_dumps(rec_bad)}")

        res = AuditTrailVerifier.verify_records([rec_bad])
        self.assertFalse(res.is_valid)
        self.assertIn("ADR 0002 Violation", res.error_message)

        # 2. Transition to EXECUTED with REJECTED review decision
        rec_rejected_exec = {
            "audit_entry_id": "aud_bad02",
            "sequence_number": 0,
            "timestamp": "2026-09-01T10:00:00Z",
            "case_id": "case_bad",
            "policy_id": "pol_bad",
            "case_event_id": "cev_bad",
            "from_state": "HUMAN_REVIEWED",
            "to_state": "EXECUTED",
            "decision_context_digest": {},
            "human_review": {
                "reviewer_id": "usr_test_01",
                "reviewed_at": "2026-09-01T10:00:00Z",
                "decision": "REJECTED",
                "rationale_code": "REJECT_CODE",
                "justification": "Rejected outright.",
            },
            "dispatched_action": None,
            "metadata": {},
            "prev_hash": GENESIS_HASH,
        }
        rec_rejected_exec["entry_hash"] = compute_sha256(
            f"{GENESIS_HASH}{canonical_json_dumps(rec_rejected_exec)}"
        )
        res2 = AuditTrailVerifier.verify_records([rec_rejected_exec])
        self.assertFalse(res2.is_valid)
        self.assertIn("EXECUTED transition requires APPROVED or OVERRIDDEN", res2.error_message)

    def test_ledger_reload_and_resume(self) -> None:
        """Verifies that creating an AuditLedger instance on existing file continues seamlessly."""
        self.ledger.append(
            case_id="case_001",
            policy_id="pol_001",
            case_event_id="cev_001",
            from_state="NONE",
            to_state="CREATED",
            timestamp="2026-09-01T10:00:00Z",
        )
        last_hash = self.ledger.current_hash

        # Instantiate second ledger instance pointing to same file
        ledger2 = AuditLedger(self.log_path)
        self.assertEqual(ledger2.total_entries, 1)
        self.assertEqual(ledger2.current_hash, last_hash)
        self.assertEqual(ledger2.current_sequence, 0)

        # Append new entry via second instance
        rec1 = ledger2.append(
            case_id="case_001",
            policy_id="pol_001",
            case_event_id="cev_002",
            from_state="CREATED",
            to_state="TRIAGED",
            timestamp="2026-09-01T10:05:00Z",
        )
        self.assertEqual(rec1.sequence_number, 1)
        self.assertEqual(rec1.prev_hash, last_hash)

        # Validate whole file
        res = AuditTrailVerifier.verify_file(self.log_path)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.total_entries, 2)

    def test_corrupt_file_recovery_refusal(self) -> None:
        """Verifies that initializing an AuditLedger on a corrupted file raises AuditIntegrityError."""
        self.ledger.append(
            case_id="case_001",
            policy_id="pol_001",
            case_event_id="cev_001",
            from_state="NONE",
            to_state="CREATED",
        )
        # Corrupt file
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write("CORRUPT_NON_JSON_LINE\n")

        with self.assertRaises(AuditIntegrityError):
            AuditLedger(self.log_path)

    def test_cli_script_execution(self) -> None:
        """Tests scripts/verify_conservation_audit_trail.py via subprocess."""
        # Create a valid audit trail with human review and execution
        self.ledger.append(
            case_id="case_001",
            policy_id="pol_001",
            case_event_id="cev_001",
            from_state="NONE",
            to_state="CREATED",
            timestamp="2026-09-01T10:00:00Z",
        )
        self.ledger.append(
            case_id="case_001",
            policy_id="pol_001",
            case_event_id="cev_002",
            from_state="CREATED",
            to_state="RECOMMENDED",
            timestamp="2026-09-01T10:05:00Z",
        )
        self.ledger.append(
            case_id="case_001",
            policy_id="pol_001",
            case_event_id="cev_003",
            from_state="RECOMMENDED",
            to_state="HUMAN_REVIEWED",
            human_review={
                "reviewer_id": "usr_alice_01",
                "reviewed_at": "2026-09-01T10:10:00Z",
                "decision": "APPROVED",
                "rationale_code": "APPROVED_STANDARD",
            },
            timestamp="2026-09-01T10:10:00Z",
        )
        self.ledger.append(
            case_id="case_001",
            policy_id="pol_001",
            case_event_id="cev_004",
            from_state="HUMAN_REVIEWED",
            to_state="EXECUTED",
            human_review={
                "reviewer_id": "usr_alice_01",
                "reviewed_at": "2026-09-01T10:10:00Z",
                "decision": "APPROVED",
                "rationale_code": "APPROVED_STANDARD",
            },
            timestamp="2026-09-01T10:15:00Z",
        )

        script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "verify_conservation_audit_trail.py"

        # 1. Run on valid file
        proc = subprocess.run(
            [sys.executable, str(script_path), "--log", str(self.log_path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"CLI stderr: {proc.stderr}")
        self.assertIn("PASSED [INTEGRITY SECURE]", proc.stdout)
        self.assertIn("Total Entries   : 4", proc.stdout)

        # 2. Run with --json
        proc_json = subprocess.run(
            [sys.executable, str(script_path), "--log", str(self.log_path), "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc_json.returncode, 0)
        parsed = json.loads(proc_json.stdout)
        self.assertTrue(parsed["is_valid"])
        self.assertEqual(parsed["total_entries"], 4)


if __name__ == "__main__":
    unittest.main()

