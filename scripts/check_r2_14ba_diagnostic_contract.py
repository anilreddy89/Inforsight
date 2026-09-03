#!/usr/bin/env python3
"""Validate the documentation-only R2-14BA diagnostic contract amendment boundary."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ADR_PATH = ROOT / "docs/adr/0010-amend-v5-diagnostic-contract-with-disposition-truth-tables.md"
CONTRACT_PATH = ROOT / "docs/modeling/phase-02r-14ba-v5-diagnostic-authorization-contract.md"
BACKLOG_PATH = ROOT / "docs/backlog.md"

EXPECTED_DOMAINS = {
    "v3_spent_acceptance": tuple(range(20261001, 20261021)),
    "v4_spent_qualification": tuple(range(20271101, 20271121)),
    "v4_reserved_acceptance": tuple(range(20271201, 20271221)),
    "v5_diagnostic_development": tuple(range(20280101, 20280121)),
}
HYPOTHESES = (
    "H1_LOG_HAZARD_SPREAD", "H2_HORIZON_ATTENUATION", "H3_PROBABILITY_SCALE",
    "H4_REFERENCE_SPECIFICATION", "H5_HAZARD_TAIL", "H6_DESIGN_FEASIBILITY",
)
DIAGNOSTICS = tuple(f"D{i}_" for i in range(1, 18))
DISPOSITION_RULE_TOKENS = tuple(
    f"{hypothesis} supported when" for hypothesis in HYPOTHESES[:-1]
) + tuple(
    f"{hypothesis} rejected when" for hypothesis in HYPOTHESES[:-1]
)
FEASIBILITY_RULE_TOKENS = (
    "H6_DESIGN_FEASIBILITY feasible when",
    "H6_DESIGN_FEASIBILITY infeasible when",
)
ARTIFACTS = (
    "phase-02r-14b-v5-redesign-diagnostic-manifest.json",
    "phase-02r-14b-v5-redesign-diagnostic-report.md",
    "phase-02r-14b-v5-hypothesis-disposition.md",
)


class ContractError(ValueError):
    """Raised when the R2-14BA documentation boundary is invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def declared_range(text: str, domain: str) -> tuple[int, ...]:
    match = re.search(rf"\| `{re.escape(domain)}` \| `(\d+)\.\.(\d+)` \|", text)
    require(match is not None, f"missing seed declaration for {domain}")
    start, end = (int(value) for value in match.groups())
    return tuple(range(start, end + 1))


def validate(adr: str, contract: str, backlog: str) -> None:
    combined = "\n".join((adr, contract, backlog))
    require("issue #80" in adr.lower(), "ADR does not bind issue #80")
    require("Contract version | `1.1.0`" in contract, "contract version drifted")
    require("3088c4c" in combined, "R2-14B merge identity is missing")
    require("R2-14BA" in backlog and "R2-14C" in backlog, "successor sequence is incomplete")

    domains = {name: declared_range(contract, name) for name in EXPECTED_DOMAINS}
    require(domains == EXPECTED_DOMAINS, "seed domain values drifted")
    require(all(len(values) == 20 for values in domains.values()), "seed domains must contain 20 seeds")
    names = tuple(domains)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            require(set(domains[left]).isdisjoint(domains[right]), f"seed domains overlap: {left}, {right}")

    for hypothesis in HYPOTHESES:
        require(contract.count(hypothesis) >= 1, f"missing hypothesis {hypothesis}")
    for prefix in DIAGNOSTICS:
        require(re.search(rf"`{prefix}[A-Z_]+`", contract) is not None, f"missing diagnostic {prefix[:-1]}")
    require("exactly 320 cells" in contract, "feasibility grid size is not frozen")
    for axis in ("public_coefficient_scale", "frailty_standard_deviation", "lapse_intercept_delta", "surrender_intercept_delta"):
        require(axis in contract, f"missing feasibility axis {axis}")
    for artifact in ARTIFACTS:
        require(artifact in contract, f"missing planned artifact {artifact}")

    for token in DISPOSITION_RULE_TOKENS:
        require(token in contract, f"missing mechanical disposition rule token: {token}")
    for token in FEASIBILITY_RULE_TOKENS:
        require(token in contract, f"missing mechanical feasibility rule token: {token}")

    for token in (
        "aggregate only", "MUST NOT expand", "fewer than 10 unique policies",
        "final_holdout: not_materialized", "R2-14C, R2-15, R2-16",
    ):
        require(token in combined, f"missing boundary token: {token}")


def read(path: Path) -> str:
    require(path.is_file(), f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    try:
        validate(read(ADR_PATH), read(CONTRACT_PATH), read(BACKLOG_PATH))
    except ContractError as error:
        raise SystemExit(f"R2-14BA diagnostic contract check failed: {error}") from error
    print("R2-14BA diagnostic authorization contract check passed.")


if __name__ == "__main__":
    main()

