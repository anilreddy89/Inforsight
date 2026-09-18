"""Versioned local workflow-state persistence for the RH-10 reference runtime."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import uuid
from typing import Any


STATE_VERSION = "workflow-state/1.0.0"


class WorkflowStateRecoveryError(RuntimeError):
    """Raised when a local workflow snapshot cannot be recovered safely."""


class WorkflowStateStore:
    """Atomically stores committed state and one pending audit-backed transition."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowStateRecoveryError(f"invalid workflow state: {exc}") from exc
        if payload.get("version") != STATE_VERSION or set(payload) != {
            "version", "committed", "pending"
        }:
            raise WorkflowStateRecoveryError("unsupported or malformed workflow state version")
        return payload

    def write(self, *, committed: dict[str, Any], pending: dict[str, Any] | None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": STATE_VERSION, "committed": committed, "pending": pending}
        temporary = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary.exists():
                temporary.unlink()

    def begin(self, *, committed: dict[str, Any], target: dict[str, Any], audit_entry_id: str) -> None:
        self.write(
            committed=committed,
            pending={"audit_entry_id": audit_entry_id, "target": deepcopy(target)},
        )

    def commit(self, target: dict[str, Any]) -> None:
        self.write(committed=target, pending=None)

    def rollback(self, committed: dict[str, Any]) -> None:
        self.write(committed=committed, pending=None)
