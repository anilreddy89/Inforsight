"""Stable serialization for generated policy events."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any


def histories_to_jsonl(
    histories: Iterable[Iterable[Mapping[str, Any]]],
) -> str:
    """Serialize histories as compact, byte-stable JSON Lines."""

    lines = [
        json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        for history in histories
        for event in history
    ]
    return "".join(f"{line}\n" for line in lines)
