#!/usr/bin/env python3
"""Fail closed when the R2-08 design surface becomes inconsistent."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "adr": ROOT / "docs/adr/0005-replace-v2-with-a-dual-time-matched-control-v3-statistical-substrate.md",
    "contract": ROOT / "docs/modeling/phase-02r-08-v3-statistical-substrate-contract.md",
    "protocol": ROOT / "docs/modeling/phase-02r-08-statistical-acceptance-protocol.md",
    "backlog": ROOT / "docs/backlog.md",
    "limitations": ROOT / "docs/limitations.md",
    "readme": ROOT / "README.md",
}

REQUIRED = {
    "adr": ("issue #53", "R2-09", "R2-10", "R2-11", "not_materialized", "protocol `2.0.0`"),
    "contract": (
        "`3.0.0`",
        "Random-stream registry",
        "`stream_set_id`",
        "`artifact_id`",
        "`execution_id`",
        "14,400",
        "20261001",
        "not_materialized",
    ),
    "protocol": (
        "`2.0.0`",
        "20261001",
        "20261020",
        "1,000",
        "stop",
        "redesign",
        "proceed",
        "not_materialized",
    ),
    "backlog": ("R2-08", "R2-09", "R2-10", "R2-11", "issue #53", "protocol `2.0.0`"),
    "limitations": ("LIM-002-004", "issue #53", "R2-09 through R2-11", "protocol `2.0.0`"),
    "readme": ("R2-08", "issue #53", "R2-11", "not_materialized"),
}


def main() -> None:
    failures: list[str] = []
    for name, path in FILES.items():
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for token in REQUIRED[name]:
            if token not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {token!r}")

    forbidden_roots = (ROOT / "datasets/v3", ROOT / "docs/experiments/phase-02r-08-v3")
    for path in forbidden_roots:
        if path.exists():
            failures.append(f"R2-08 must not materialize {path.relative_to(ROOT)}")

    if failures:
        raise SystemExit("R2-08 design check failed:\n- " + "\n- ".join(failures))
    print("R2-08 design consistency check passed; no v3 output or final holdout materialized.")


if __name__ == "__main__":
    main()
