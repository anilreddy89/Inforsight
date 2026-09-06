"""Deterministic canonical JSON serialization and cryptographic hashing.

Adheres to RFC 8785 principles for canonical JSON serialization:
- Strict lexicographical ordering of object keys
- Deterministic float and number formatting
- Compact separators with no extraneous whitespace
- Strict UTF-8 encoding
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_dumps(obj: Any) -> str:
    """Serializes a Python object to canonical deterministic JSON.

    Ensures that identical data structures always yield identical string and
    byte representations regardless of execution environment, Python dictionary
    insertion order, or platform formatting defaults.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
        default=_serialize_default,
    )


def _serialize_default(o: Any) -> Any:
    """Custom serializer fallback for objects like sets, enums, or path objects."""
    if hasattr(o, "to_dict") and callable(o.to_dict):
        return o.to_dict()
    if hasattr(o, "value"):
        return o.value
    if isinstance(o, (set, frozenset)):
        return sorted(list(o))
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")


def compute_sha256(data: str | bytes) -> str:
    """Computes SHA-256 hexadecimal digest for string or bytes."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

