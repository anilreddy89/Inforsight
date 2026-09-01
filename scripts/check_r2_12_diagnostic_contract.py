#!/usr/bin/env python3
"""Validate the documentation-only R2-12 diagnostic authorization boundary."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs/adr/0006-approve-v4-signal-recovery-diagnostic-boundary.md"
CONTRACT = ROOT / "docs/modeling/phase-02r-12-v4-redesign-diagnostic-contract.md"
BACKLOG = ROOT / "docs/backlog.md"

SPENT = tuple(range(20261001, 20261021))
DEVELOPMENT = tuple(range(20271101, 20271121))
ACCEPTANCE = tuple(range(20271201, 20271221))

HYPOTHESES = (
    "H1_ORACLE_SEPARABILITY",
    "H2_DRIVER_SUPPORT",
    "H3_TRANSFORM_PARITY",
    "H4_EPISODE_DILUTION",
    "H5_CANDIDATE_LEARNING",
    "H6_TEMPORAL_STABILITY",
)

ARTIFACTS = (
    "phase-02r-13-v4-redesign-diagnostic-manifest.json",
    "phase-02r-13-v4-redesign-diagnostic-report.md",
    "phase-02r-13-v4-redesign-hypothesis-disposition.md",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"R2-12 diagnostic contract check failed: {message}")


def read(path: Path) -> str:
    require(path.is_file(), f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def declared_range(text: str, domain: str) -> tuple[int, ...]:
    pattern = rf"\| `{re.escape(domain)}` \| `(\d+)\.\.(\d+)` \|"
    match = re.search(pattern, text)
    require(match is not None, f"missing seed declaration for {domain}")
    start, end = (int(value) for value in match.groups())
    return tuple(range(start, end + 1))


def main() -> None:
    adr = read(ADR)
    contract = read(CONTRACT)
    backlog = read(BACKLOG)

    require("issue #66" in adr.lower(), "ADR does not bind issue #66")
    require("Contract version | `1.0.0`" in contract, "contract version is not 1.0.0")
    require("76c8cd3" in backlog, "backlog does not record the R2-11 merge")
    require("R2-12" in backlog and "R2-16" in backlog, "replacement sequence is incomplete")

    domains = {
        "v3_spent_acceptance": declared_range(contract, "v3_spent_acceptance"),
        "v4_development_diagnostic": declared_range(contract, "v4_development_diagnostic"),
        "v4_future_acceptance": declared_range(contract, "v4_future_acceptance"),
    }
    require(domains["v3_spent_acceptance"] == SPENT, "spent seed block drifted")
    require(domains["v4_development_diagnostic"] == DEVELOPMENT, "development seed block drifted")
    require(domains["v4_future_acceptance"] == ACCEPTANCE, "acceptance seed block drifted")
    require(all(len(values) == 20 for values in domains.values()), "each seed block must contain 20 seeds")

    names = tuple(domains)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            require(
                set(domains[left]).isdisjoint(domains[right]),
                f"seed domains overlap: {left} and {right}",
            )

    for hypothesis in HYPOTHESES:
        require(contract.count(hypothesis) >= 1, f"missing hypothesis {hypothesis}")
    require(len(set(HYPOTHESES)) == 6, "hypothesis identifiers are not unique")

    for artifact in ARTIFACTS:
        require(artifact in contract, f"missing planned artifact {artifact}")

    combined = "\n".join((adr, contract, backlog))
    for token in (
        "spent evidence",
        "result-producing",
        "not_materialized",
        "P2-08/P2-09 remain paused",
        "R2-13",
    ):
        require(token in combined, f"missing boundary token: {token}")

    print("R2-12 diagnostic authorization contract check passed.")


if __name__ == "__main__":
    main()
