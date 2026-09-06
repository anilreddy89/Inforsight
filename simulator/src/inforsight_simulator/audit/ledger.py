"""Cryptographically hash-chained append-only audit ledger.

Implements tamper-evident audit logging for conservation decision workflows
under ADR 0002 and regulatory market conduct standards.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
import threading
from typing import Any, Optional
import uuid

from inforsight_simulator.audit.serialization import canonical_json_dumps, compute_sha256

GENESIS_SEED = "INFORSIGHT_CONSERVATION_AUDIT_GENESIS_V0_3_0"
GENESIS_HASH = compute_sha256(GENESIS_SEED)


class AuditIntegrityError(Exception):
    """Raised when an audit record or chain fails integrity verification."""


@dataclass(frozen=True)
class AuditRecord:
    """Immutable single entry in the conservation audit ledger."""

    audit_entry_id: str
    sequence_number: int
    timestamp: str
    case_id: str
    policy_id: str
    case_event_id: str
    from_state: str
    to_state: str
    decision_context_digest: dict[str, Any]
    human_review: Optional[dict[str, Any]]
    dispatched_action: Optional[dict[str, Any]]
    metadata: dict[str, Any]
    prev_hash: str
    entry_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_entry_id": self.audit_entry_id,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp,
            "case_id": self.case_id,
            "policy_id": self.policy_id,
            "case_event_id": self.case_event_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "decision_context_digest": self.decision_context_digest,
            "human_review": self.human_review,
            "dispatched_action": self.dispatched_action,
            "metadata": self.metadata,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }

    def payload_for_hashing(self) -> dict[str, Any]:
        """Returns the dictionary representation excluding entry_hash for cryptographic chaining."""
        d = self.to_dict()
        del d["entry_hash"]
        return d


class AuditLedger:
    """Append-only cryptographic ledger storing chained audit entries."""

    def __init__(self, log_path: Optional[str | Path] = None) -> None:
        self.log_path = Path(log_path) if log_path else None
        self._lock = threading.RLock()
        self._records: list[AuditRecord] = []
        self._current_sequence: int = -1
        self._current_hash: str = GENESIS_HASH

        if self.log_path and self.log_path.exists():
            self._load_and_validate_existing()

    @property
    def total_entries(self) -> int:
        with self._lock:
            return len(self._records)

    @property
    def current_hash(self) -> str:
        with self._lock:
            return self._current_hash

    @property
    def current_sequence(self) -> int:
        with self._lock:
            return self._current_sequence

    @property
    def records(self) -> list[AuditRecord]:
        with self._lock:
            return list(self._records)

    def _load_and_validate_existing(self) -> None:
        """Reads and cryptographically validates existing log file on disk."""
        assert self.log_path is not None
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                import json

                try:
                    raw = json.loads(line)
                except Exception as e:
                    raise AuditIntegrityError(
                        f"Corrupt JSON at line {line_idx + 1} of {self.log_path}: {e}"
                    )

                expected_prev = self._current_hash
                if raw.get("prev_hash") != expected_prev:
                    raise AuditIntegrityError(
                        f"Broken hash chain at line {line_idx + 1} (seq {raw.get('sequence_number')}): "
                        f"expected prev_hash {expected_prev}, found {raw.get('prev_hash')}"
                    )

                record = AuditRecord(
                    audit_entry_id=raw["audit_entry_id"],
                    sequence_number=raw["sequence_number"],
                    timestamp=raw["timestamp"],
                    case_id=raw["case_id"],
                    policy_id=raw["policy_id"],
                    case_event_id=raw["case_event_id"],
                    from_state=raw["from_state"],
                    to_state=raw["to_state"],
                    decision_context_digest=raw.get("decision_context_digest", {}),
                    human_review=raw.get("human_review"),
                    dispatched_action=raw.get("dispatched_action"),
                    metadata=raw.get("metadata", {}),
                    prev_hash=raw["prev_hash"],
                    entry_hash=raw["entry_hash"],
                )

                # Verify entry_hash
                payload_str = canonical_json_dumps(record.payload_for_hashing())
                computed_hash = compute_sha256(f"{expected_prev}{payload_str}")
                if computed_hash != record.entry_hash:
                    raise AuditIntegrityError(
                        f"Hash mismatch at line {line_idx + 1} (seq {record.sequence_number}): "
                        f"expected {computed_hash}, got {record.entry_hash}"
                    )

                self._records.append(record)
                self._current_sequence = record.sequence_number
                self._current_hash = record.entry_hash

    def append(
        self,
        *,
        case_id: str,
        policy_id: str,
        case_event_id: str,
        from_state: str,
        to_state: str,
        decision_context_digest: Optional[dict[str, Any]] = None,
        human_review: Optional[dict[str, Any]] = None,
        dispatched_action: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> AuditRecord:
        """Appends a new immutable audit record to the ledger."""
        with self._lock:
            next_seq = self._current_sequence + 1
            entry_id = f"aud_{uuid.uuid4().hex[:26]}"
            ts = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            prev_hash = self._current_hash
            context_digest = decision_context_digest or {}
            meta = metadata or {}

            # Construct preliminary record dict without entry_hash
            record_dict = {
                "audit_entry_id": entry_id,
                "sequence_number": next_seq,
                "timestamp": ts,
                "case_id": case_id,
                "policy_id": policy_id,
                "case_event_id": case_event_id,
                "from_state": from_state,
                "to_state": to_state,
                "decision_context_digest": context_digest,
                "human_review": human_review,
                "dispatched_action": dispatched_action,
                "metadata": meta,
                "prev_hash": prev_hash,
            }

            payload_str = canonical_json_dumps(record_dict)
            entry_hash = compute_sha256(f"{prev_hash}{payload_str}")

            record = AuditRecord(
                audit_entry_id=entry_id,
                sequence_number=next_seq,
                timestamp=ts,
                case_id=case_id,
                policy_id=policy_id,
                case_event_id=case_event_id,
                from_state=from_state,
                to_state=to_state,
                decision_context_digest=context_digest,
                human_review=human_review,
                dispatched_action=dispatched_action,
                metadata=meta,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )

            self._records.append(record)
            self._current_sequence = next_seq
            self._current_hash = entry_hash

            if self.log_path:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(canonical_json_dumps(record.to_dict()) + "\n")
                    f.flush()
                    os.fsync(f.fileno())

            return record

