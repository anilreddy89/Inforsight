#!/usr/bin/env python3
"""CLI utility to verify cryptographic chain integrity and ADR 0002 compliance.

Usage:
    python3 scripts/verify_conservation_audit_trail.py --log data/audit/conservation-audit-log.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure simulator src is on Python path
REPO_ROOT = Path(__file__).resolve().parent.parent
SIMULATOR_SRC = REPO_ROOT / "simulator" / "src"
if str(SIMULATOR_SRC) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_SRC))

from inforsight_simulator.audit.verifier import AuditTrailVerifier


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify cryptographic hash-chain integrity and ADR 0002 compliance for conservation audit logs."
    )
    parser.add_argument(
        "--log",
        type=str,
        required=True,
        help="Path to the conservation audit log file (.jsonl)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format instead of scorecard",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Display detailed entry breakdown",
    )

    args = parser.parse_args()
    log_path = Path(args.log)

    result = AuditTrailVerifier.verify_file(log_path)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.is_valid else 1

    print("=" * 78)
    print("      INFORSIGHT CONSERVATION AUDIT TRAIL VERIFICATION REPORT")
    print("=" * 78)
    print(f"Target Log File : {log_path}")
    print(f"Verification    : {'PASSED [INTEGRITY SECURE]' if result.is_valid else 'FAILED [COMPROMISED]'}")
    print("-" * 78)

    if not result.is_valid:
        print(f"Error Message   : {result.error_message}")
        print(f"Violating Seq # : {result.violating_sequence_number}")
        print(f"Entries Processed: {result.total_entries}")
        print("=" * 78)
        return 1

    print(f"Total Entries   : {result.total_entries}")
    print(f"Timeline Start  : {result.first_timestamp or 'N/A'}")
    print(f"Timeline End    : {result.last_timestamp or 'N/A'}")
    print(f"Unique Cases    : {result.unique_cases}")
    print(f"Unique Policies : {result.unique_policies}")
    print(f"Reviewers Count : {len(result.unique_reviewers)}")
    if args.verbose and result.unique_reviewers:
        print(f"Reviewer List   : {', '.join(result.unique_reviewers)}")
    print("-" * 78)
    print("DECISION BREAKDOWN (ADR 0002 COMPLIANCE):")
    print(f"  Approved      : {result.approved_count}")
    print(f"  Overridden    : {result.overridden_count}")
    print(f"  Rejected      : {result.rejected_count}")
    print(f"  Executed      : {result.executed_count}")
    print("-" * 78)
    print(f"Chain Tip Hash  : {result.details.get('chain_tip_hash', 'N/A')}")
    print("All sequence numbers monotonic; all SHA-256 links verified.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())

