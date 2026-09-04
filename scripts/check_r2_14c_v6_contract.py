#!/usr/bin/env python3
"""Validate the Generation v6 bounded sigmoid substrate contract boundary."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ADR_PATH = ROOT / "docs/adr/0012-authorize-bounded-sigmoid-hazard-link-v6.md"
CONTRACT_PATH = ROOT / "docs/modeling/phase-02r-14c-v6-bounded-sigmoid-substrate-contract.md"
BACKLOG_PATH = ROOT / "docs/backlog.md"
ADR_INDEX_PATH = ROOT / "docs/adr/README.md"

EXPECTED_DOMAINS = {
    "v3_spent_acceptance": tuple(range(20261001, 20261021)),
    "v4_spent_qualification": tuple(range(20271101, 20271121)),
    "v4_reserved_acceptance": tuple(range(20271201, 20271221)),
    "v5_diagnostic_development": tuple(range(20280101, 20280121)),
    "v6_development": tuple(range(20280201, 20280221)),
}

REQUIRED_FORMULA_TOKENS = (
    r"\lambda_{\max, \text{lapse}} = 0.10",
    r"\lambda_{\max, \text{surrender}} = 0.05",
    r"0.10 + 0.05 = 0.1500 < 0.2000",
    r"\text{clip}(z, -15.0, 15.0)",
    r"\alpha_l = -2.20",
    r"\alpha_s = -2.80",
    r"\sigma_u = 0.20",
    r"32-node Gauss-Hermite quadrature",
)

REQUIRED_GATE_TOKENS = (
    "Monthly total hazard",
    "observable-oracle AUC",
    "AP) lift over baseline rate",
    "Brier skill score",
    "[0.45, 0.55]",
    "deterministic replay",
    "not_materialized",
)


class ContractError(ValueError):
    """Raised when the Generation v6 substrate contract boundary is invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def declared_range(text: str, domain: str) -> tuple[int, ...]:
    match = re.search(rf"\| `{re.escape(domain)}` \| `(\d+)\.\.(\d+)` \|", text)
    require(match is not None, f"missing seed declaration for {domain}")
    start, end = (int(value) for value in match.groups())
    return tuple(range(start, end + 1))


def validate(adr: str, contract: str, backlog: str, adr_index: str) -> None:
    combined = "\n".join((adr, contract, backlog, adr_index))
    require("issue #86" in adr.lower(), "ADR 0012 does not bind issue #86")
    require("0012-authorize-bounded-sigmoid-hazard-link-v6.md" in adr_index, "ADR index missing ADR 0012")
    require("Contract version | `6.0.0`" in contract, "contract version drifted")
    require("Coefficient registry | `3.0.0`" in contract, "coefficient registry version drifted")
    require("Random-stream registry | `3.0.0`" in contract, "random-stream registry version drifted")
    require("Implementation phase | R2-14D" in contract, "implementation phase must be R2-14D")
    require("R2-14C" in backlog and "R2-14D" in backlog, "successor sequence R2-14C -> R2-14D is incomplete in backlog")

    domains = {name: declared_range(contract, name) for name in EXPECTED_DOMAINS}
    require(domains == EXPECTED_DOMAINS, "seed domain values drifted")
    require(all(len(values) == 20 for values in domains.values()), "seed domains must contain 20 seeds")
    names = tuple(domains)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            require(set(domains[left]).isdisjoint(domains[right]), f"seed domains overlap: {left}, {right}")

    for token in REQUIRED_FORMULA_TOKENS:
        require(token in contract, f"missing required formula token: {token}")

    for token in REQUIRED_GATE_TOKENS:
        require(token in contract, f"missing required qualification gate token: {token}")

    require("| Final holdout | `not_materialized` |" in contract, "metadata final holdout must be not_materialized")
    require("| `final_holdout` | `not_materialized` |" in contract, "domain table final holdout must be not_materialized")

    for token in (
        "Proportional Hazards Trilemma",
        "ADR 0011",
        "ADR 0012",
    ):
        require(token in combined, f"missing boundary token: {token}")


def read(path: Path) -> str:
    require(path.is_file(), f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    try:
        validate(read(ADR_PATH), read(CONTRACT_PATH), read(BACKLOG_PATH), read(ADR_INDEX_PATH))
    except ContractError as error:
        raise SystemExit(f"R2-14C Generation v6 contract check failed: {error}") from error
    print("R2-14C Generation v6 bounded sigmoid substrate contract check passed.")


if __name__ == "__main__":
    main()
