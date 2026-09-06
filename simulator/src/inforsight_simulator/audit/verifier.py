"""Verification engine for the cryptographically hash-chained audit ledger.

Validates sequence monotonicity, cryptographic continuity, ADR 0002 compliance,
and historical decision provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Optional

from inforsight_simulator.audit.ledger import GENESIS_HASH, AuditRecord
from inforsight_simulator.audit.serialization import canonical_json_dumps, compute_sha256

REVIEWER_ID_PATTERN = re.compile(r"^usr_[a-z0-9_]{3,32}$")


@dataclass(frozen=True)
class AuditVerificationResult:
    """Detailed scorecard resulting from audit trail verification."""

    is_valid: bool
    total_entries: int
    first_timestamp: Optional[str] = None
    last_timestamp: Optional[str] = None
    unique_cases: int = 0
    unique_policies: int = 0
    unique_reviewers: tuple[str, ...] = field(default_factory=tuple)
    approved_count: int = 0
    overridden_count: int = 0
    rejected_count: int = 0
    executed_count: int = 0
    violating_sequence_number: Optional[int] = None
    error_message: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "total_entries": self.total_entries,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "unique_cases": self.unique_cases,
            "unique_policies": self.unique_policies,
            "unique_reviewers": list(self.unique_reviewers),
            "approved_count": self.approved_count,
            "overridden_count": self.overridden_count,
            "rejected_count": self.rejected_count,
            "executed_count": self.executed_count,
            "violating_sequence_number": self.violating_sequence_number,
            "error_message": self.error_message,
            "details": self.details,
        }


class AuditTrailVerifier:
    """Verifies cryptographic hash chains and governance invariants on audit logs."""

    @classmethod
    def verify_file(cls, log_path: str | Path) -> AuditVerificationResult:
        """Reads and verifies an entire audit log file from disk."""
        path = Path(log_path)
        if not path.exists():
            return AuditVerificationResult(
                is_valid=False,
                total_entries=0,
                error_message=f"Log file not found at: {path}",
            )

        raw_records: list[dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    raw_records.append(parsed)
                except Exception as e:
                    return AuditVerificationResult(
                        is_valid=False,
                        total_entries=len(raw_records),
                        violating_sequence_number=len(raw_records),
                        error_message=f"Malformed JSON on line {line_idx + 1}: {e}",
                    )

        return cls.verify_records(raw_records)

    @classmethod
    def verify_records(cls, records: list[dict[str, Any]]) -> AuditVerificationResult:
        """Verifies an in-memory sequence of audit record dictionaries."""
        if not records:
            return AuditVerificationResult(
                is_valid=True,
                total_entries=0,
                error_message=None,
                details={"status": "EMPTY_LEDGER"},
            )

        cases: set[str] = set()
        policies: set[str] = set()
        reviewers: set[str] = set()
        approved = 0
        overridden = 0
        rejected = 0
        executed = 0

        first_ts = records[0].get("timestamp")
        last_ts = records[-1].get("timestamp")
        prev_hash = GENESIS_HASH
        prev_ts: Optional[datetime] = None

        for idx, rec in enumerate(records):
            seq = rec.get("sequence_number")
            # 1. Monotonic sequence check
            if seq != idx:
                return AuditVerificationResult(
                    is_valid=False,
                    total_entries=len(records),
                    violating_sequence_number=seq,
                    error_message=(
                        f"Non-monotonic sequence number at index {idx}: expected {idx}, got {seq}"
                    ),
                )

            # 2. Required field presence
            required_fields = [
                "audit_entry_id",
                "sequence_number",
                "timestamp",
                "case_id",
                "policy_id",
                "case_event_id",
                "from_state",
                "to_state",
                "prev_hash",
                "entry_hash",
            ]
            for rf in required_fields:
                if rf not in rec:
                    return AuditVerificationResult(
                        is_valid=False,
                        total_entries=len(records),
                        violating_sequence_number=seq,
                        error_message=f"Missing required field '{rf}' in entry seq {seq}",
                    )

            # 3. Timestamp sanity and monotonicity
            ts_str = rec["timestamp"]
            try:
                curr_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if prev_ts and curr_ts < prev_ts:
                    return AuditVerificationResult(
                        is_valid=False,
                        total_entries=len(records),
                        violating_sequence_number=seq,
                        error_message=(
                            f"Timestamp sequence inversion at seq {seq}: "
                            f"{ts_str} earlier than predecessor {prev_ts.isoformat()}"
                        ),
                    )
                prev_ts = curr_ts
            except Exception as e:
                return AuditVerificationResult(
                    is_valid=False,
                    total_entries=len(records),
                    violating_sequence_number=seq,
                    error_message=f"Invalid timestamp '{ts_str}' at seq {seq}: {e}",
                )

            # 4. Hash chain continuity
            actual_prev = rec["prev_hash"]
            if actual_prev != prev_hash:
                return AuditVerificationResult(
                    is_valid=False,
                    total_entries=len(records),
                    violating_sequence_number=seq,
                    error_message=(
                        f"Cryptographic chain broken at seq {seq}: "
                        f"expected prev_hash {prev_hash}, found {actual_prev}"
                    ),
                )

            # 5. Entry hash verification
            expected_entry_hash = rec["entry_hash"]
            payload_without_hash = dict(rec)
            del payload_without_hash["entry_hash"]
            payload_str = canonical_json_dumps(payload_without_hash)
            computed_entry_hash = compute_sha256(f"{prev_hash}{payload_str}")

            if computed_entry_hash != expected_entry_hash:
                return AuditVerificationResult(
                    is_valid=False,
                    total_entries=len(records),
                    violating_sequence_number=seq,
                    error_message=(
                        f"Cryptographic hash tamper detected at seq {seq}: "
                        f"payload hash {computed_entry_hash} does not match record {expected_entry_hash}"
                    ),
                )

            # 6. ADR 0002 Governance Invariants
            to_state = rec["to_state"]
            from_state = rec["from_state"]

            # Cannot transition RECOMMENDED -> EXECUTED directly
            if from_state == "RECOMMENDED" and to_state == "EXECUTED":
                return AuditVerificationResult(
                    is_valid=False,
                    total_entries=len(records),
                    violating_sequence_number=seq,
                    error_message=(
                        f"ADR 0002 Violation at seq {seq}: Direct autonomous transition "
                        f"from RECOMMENDED to EXECUTED is prohibited."
                    ),
                )

            hr = rec.get("human_review")
            if to_state == "EXECUTED":
                executed += 1
                if not hr:
                    return AuditVerificationResult(
                        is_valid=False,
                        total_entries=len(records),
                        violating_sequence_number=seq,
                        error_message=(
                            f"ADR 0002 Violation at seq {seq}: EXECUTED transition requires "
                            "a valid human_review record."
                        ),
                    )
                rev_id = hr.get("reviewer_id", "")
                if not REVIEWER_ID_PATTERN.match(rev_id):
                    return AuditVerificationResult(
                        is_valid=False,
                        total_entries=len(records),
                        violating_sequence_number=seq,
                        error_message=(
                            f"ADR 0002 Violation at seq {seq}: Invalid reviewer_id '{rev_id}'"
                        ),
                    )
                decision = hr.get("decision")
                if decision not in ("APPROVED", "OVERRIDDEN"):
                    return AuditVerificationResult(
                        is_valid=False,
                        total_entries=len(records),
                        violating_sequence_number=seq,
                        error_message=(
                            f"ADR 0002 Violation at seq {seq}: EXECUTED transition requires "
                            f"APPROVED or OVERRIDDEN decision, found '{decision}'"
                        ),
                    )

            if hr:
                dec = hr.get("decision")
                if dec == "APPROVED":
                    approved += 1
                elif dec == "OVERRIDDEN":
                    overridden += 1
                    # Overrides require justification >= 5 chars
                    just = hr.get("justification", "")
                    if not just or len(just.strip()) < 5:
                        return AuditVerificationResult(
                            is_valid=False,
                            total_entries=len(records),
                            violating_sequence_number=seq,
                            error_message=(
                                f"Governance Violation at seq {seq}: OVERRIDDEN decision "
                                "requires non-empty justification of at least 5 characters"
                            ),
                        )
                elif dec == "REJECTED":
                    rejected += 1
                    just = hr.get("justification", "")
                    if not just or len(just.strip()) < 5:
                        return AuditVerificationResult(
                            is_valid=False,
                            total_entries=len(records),
                            violating_sequence_number=seq,
                            error_message=(
                                f"Governance Violation at seq {seq}: REJECTED decision "
                                "requires non-empty justification of at least 5 characters"
                            ),
                        )

                rid = hr.get("reviewer_id")
                if rid:
                    reviewers.add(rid)

            cases.add(rec["case_id"])
            policies.add(rec["policy_id"])
            prev_hash = expected_entry_hash

        return AuditVerificationResult(
            is_valid=True,
            total_entries=len(records),
            first_timestamp=first_ts,
            last_timestamp=last_ts,
            unique_cases=len(cases),
            unique_policies=len(policies),
            unique_reviewers=tuple(sorted(reviewers)),
            approved_count=approved,
            overridden_count=overridden,
            rejected_count=rejected,
            executed_count=executed,
            details={
                "chain_tip_hash": prev_hash,
                "status": "CHAIN_INTEGRITY_VERIFIED",
            },
        )

