"""Cryptographically hash-chained append-only audit ledger.

Implements tamper-evident audit logging for conservation decision workflows
under ADR 0002 and regulatory market conduct standards.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any, Optional
import uuid

import fcntl

from inforsight_simulator.audit.serialization import canonical_json_dumps, compute_sha256

GENESIS_SEED = "INFORSIGHT_CONSERVATION_AUDIT_GENESIS_V0_3_0"
GENESIS_HASH = compute_sha256(GENESIS_SEED)


class AuditIntegrityError(Exception):
    """Raised when an audit record or chain fails integrity verification."""


class AuditWriterBusyError(AuditIntegrityError):
    """Raised when another process owns the single-writer lock."""


class AuditRecoveryError(AuditIntegrityError):
    """Raised when durable log/checkpoint state cannot be recovered safely."""


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
    """Single-writer append ledger with a durable recovery checkpoint.

    The checkpoint is a recovery boundary, not an authenticity mechanism. The
    bounded protocol writes and fsyncs the JSONL record before atomically
    replacing the checkpoint. A crash between those operations leaves an
    uncheckpointed suffix, which is truncated on the next open. A log shorter
    than its checkpoint, or a checkpoint that disagrees with the verified log,
    fails closed because committed history may have been lost or altered.
    """

    CHECKPOINT_VERSION = "audit-checkpoint/1.0.0"

    def __init__(self, log_path: Optional[str | Path] = None) -> None:
        self.log_path = Path(log_path) if log_path else None
        self.checkpoint_path = (
            self.log_path.with_name(f"{self.log_path.name}.checkpoint")
            if self.log_path
            else None
        )
        self.lock_path = (
            self.log_path.with_name(f"{self.log_path.name}.lock")
            if self.log_path
            else None
        )
        self._lock = threading.RLock()
        self._records: list[AuditRecord] = []
        self._current_sequence: int = -1
        self._current_hash: str = GENESIS_HASH

        if self.log_path and self.log_path.exists():
            self._load_and_validate_existing()
        elif self.log_path:
            self._write_checkpoint()

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
        checkpoint = self._read_checkpoint() if self.checkpoint_path and self.checkpoint_path.exists() else None
        file_size = self.log_path.stat().st_size
        if checkpoint and file_size < checkpoint["log_bytes"]:
            raise AuditRecoveryError("audit log is shorter than its trusted checkpoint")
        if checkpoint and file_size > checkpoint["log_bytes"]:
            # A crash may have fsynced a record before the checkpoint update.
            # Recover only the last committed prefix before parsing, so even
            # a torn/unparseable suffix cannot prevent safe restart recovery.
            with open(self.log_path, "rb") as f:
                f.seek(checkpoint["log_bytes"])
                suffix = f.read()
            if suffix.endswith(b"\n"):
                try:
                    for line in suffix.splitlines():
                        if line.strip():
                            json.loads(line)
                except json.JSONDecodeError as exc:
                    raise AuditIntegrityError(
                        "complete uncheckpointed audit record is malformed"
                    ) from exc
            with self._exclusive_writer() as handle:
                handle.truncate(checkpoint["log_bytes"])
            file_size = checkpoint["log_bytes"]

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue

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

        if checkpoint:
            expected = {
                "entry_count": len(self._records),
                "sequence_number": self._current_sequence,
                "tip_hash": self._current_hash,
            }
            if any(checkpoint[key] != value for key, value in expected.items()):
                raise AuditRecoveryError("audit checkpoint does not match verified log")
        else:
            self._write_checkpoint()

    def _read_checkpoint(self) -> dict[str, Any]:
        assert self.checkpoint_path is not None
        try:
            with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise AuditRecoveryError(f"invalid audit checkpoint: {exc}") from exc
        required = {"version", "entry_count", "sequence_number", "tip_hash", "log_bytes"}
        if set(checkpoint) != required or checkpoint["version"] != self.CHECKPOINT_VERSION:
            raise AuditRecoveryError("unsupported or malformed audit checkpoint")
        if not isinstance(checkpoint["log_bytes"], int) or checkpoint["log_bytes"] < 0:
            raise AuditRecoveryError("checkpoint log_bytes must be a nonnegative integer")
        return checkpoint

    def _write_checkpoint(self) -> None:
        if not self.checkpoint_path or not self.log_path:
            return
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "version": self.CHECKPOINT_VERSION,
            "entry_count": len(self._records),
            "sequence_number": self._current_sequence,
            "tip_hash": self._current_hash,
            "log_bytes": self.log_path.stat().st_size if self.log_path.exists() else 0,
        }
        temp_path = self.checkpoint_path.with_name(
            f".{self.checkpoint_path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint, f, sort_keys=True, separators=(",", ":"))
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.checkpoint_path)
            directory_fd = os.open(self.checkpoint_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _exclusive_writer(self):
        """Acquire the process-level writer lock for one durable operation."""
        if not self.lock_path:
            return _NullWriterLock()
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        return _FileWriterLock(self.lock_path, self.log_path)

    def _assert_checkpoint_current(self) -> None:
        """Reject an instance whose in-memory tip predates another writer."""
        if not self.log_path or not self.checkpoint_path or not self.checkpoint_path.exists():
            return
        checkpoint = self._read_checkpoint()
        if (
            checkpoint["entry_count"] != len(self._records)
            or checkpoint["sequence_number"] != self._current_sequence
            or checkpoint["tip_hash"] != self._current_hash
            or checkpoint["log_bytes"] != (
                self.log_path.stat().st_size if self.log_path.exists() else 0
            )
        ):
            raise AuditRecoveryError("stale audit writer state; reload before appending")

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
            if self.log_path:
                writer = self._exclusive_writer()
                writer.__enter__()
            else:
                writer = _NullWriterLock()
            try:
                self._assert_checkpoint_current()
                next_seq = self._current_sequence + 1
                entry_id = f"aud_{uuid.uuid4().hex[:26]}"
                ts = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

                prev_hash = self._current_hash
                context_digest = decision_context_digest or {}
                meta = metadata or {}
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
                if self.log_path:
                    self.log_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self.log_path, "a", encoding="utf-8") as f:
                        encoded = (canonical_json_dumps(record.to_dict()) + "\n").encode("utf-8")
                        f.write(encoded.decode("utf-8"))
                        f.flush()
                        os.fsync(f.fileno())
                self._records.append(record)
                self._current_sequence = next_seq
                self._current_hash = entry_hash
                self._write_checkpoint()
            finally:
                writer.__exit__(None, None, None)
            return record


class _NullWriterLock:
    def __enter__(self):
        return self

    def __exit__(self, *_args: Any) -> None:
        return None


class _FileWriterLock:
    def __init__(self, lock_path: Path, data_path: Path) -> None:
        self.lock_path = lock_path
        self.data_path = data_path
        self._file = None

    def __enter__(self):
        self._file = open(self.lock_path, "a+", encoding="utf-8")
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._file.close()
            raise AuditWriterBusyError("another audit writer owns the ledger") from exc
        return self

    def truncate(self, size: int) -> None:
        assert self._file is not None
        with open(self.data_path, "r+b") as log_file:
            log_file.truncate(size)
            log_file.flush()
            os.fsync(log_file.fileno())

    def flush(self) -> None:
        return None

    def __exit__(self, *_args: Any) -> None:
        if self._file is not None:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            self._file.close()
