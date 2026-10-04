#!/usr/bin/env python3
"""Independently verify journal chains and compare original/restored private DBs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from public_demo import DEFAULT_STATE, Preview, now


def inspect(state: Path):
    preview = Preview(state)
    query = """SELECT jsonb_build_object(
      'journals', (SELECT jsonb_agg(to_jsonb(j) ORDER BY correlation_id,sequence) FROM demo_journal j),
      'checkpoints', (SELECT jsonb_agg(to_jsonb(c) ORDER BY correlation_id) FROM demo_checkpoint c),
      'cases', (SELECT jsonb_agg(to_jsonb(c) ORDER BY correlation_id) FROM demo_case c),
      'decisions', (SELECT jsonb_agg(to_jsonb(d) ORDER BY correlation_id,idempotency_key) FROM demo_decision d),
      'inbox', (SELECT jsonb_agg(to_jsonb(i) ORDER BY correlation_id) FROM demo_inbox i)
    )::text;"""
    raw = preview.compose("exec", "-T", "postgres", "psql", "-U", "inforsight_app", "-d",
                          "inforsight_enterprise", "-At", "-c", query, capture=True).stdout
    data = json.loads(raw)
    rows_by_run = {}
    for row in data["journals"] or []:
        rows_by_run.setdefault(row["correlation_id"], []).append(row)
    receipts = []
    checkpoints = {c["correlation_id"]: c for c in data["checkpoints"] or []}
    for rid, rows in rows_by_run.items():
        parent = "0" * 64
        for sequence, row in enumerate(rows, start=1):
            assert row["sequence"] == sequence and row["parent_hash"] == parent, (rid, sequence)
            current = hashlib.sha256((parent + "\n" + row["canonical_payload"]).encode()).hexdigest()
            assert current == row["current_hash"], (rid, sequence)
            payload = json.loads(row["canonical_payload"])
            assert payload["journal_event_id"] == row["event_id"] and payload["stage"] == row["stage"]
            assert payload["producer"] == row["producer"] and payload["correlation_id"] == rid
            parent = current
        assert checkpoints[rid]["head_hash"] == parent and checkpoints[rid]["sequence"] == len(rows)
        receipts.append({"run_id": rid, "verified_entries": len(rows), "head_hash": parent})
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"project": preview.settings["project"], "fingerprint": fingerprint,
            "counts": {key: len(value or []) for key, value in data.items()}, "verified_receipts": receipts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--restore-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/public-demo/backup-restore.json"))
    args = parser.parse_args()
    source, restored = inspect(args.source_state), inspect(args.restore_state)
    assert source["fingerprint"] == restored["fingerprint"], "Restored database evidence differs from original."
    report = {"result": "PASS", "verified_at": now(), "source": source, "restored": restored,
              "scope": "Independent SHA-256 chains/checkpoints and exact case/decision/inbox persistence comparison; operator-only."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS exact restored evidence, {len(source['verified_receipts'])} verified run chains; {args.output}")


if __name__ == "__main__":
    main()
