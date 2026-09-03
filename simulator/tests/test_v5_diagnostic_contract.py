"""Mutation tests for the documentation-only R2-14A contract."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = spec_from_file_location("r2_14a_check", ROOT / "scripts/check_r2_14a_diagnostic_contract.py")
assert SPEC and SPEC.loader
CHECK = module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class V5DiagnosticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adr = CHECK.ADR_PATH.read_text(encoding="utf-8")
        cls.contract = CHECK.CONTRACT_PATH.read_text(encoding="utf-8")
        cls.backlog = CHECK.BACKLOG_PATH.read_text(encoding="utf-8")

    def test_repository_contract_passes(self) -> None:
        CHECK.validate(self.adr, self.contract, self.backlog)

    def assert_contract_rejected(self, contract: str) -> None:
        with self.assertRaises(CHECK.ContractError):
            CHECK.validate(self.adr, contract, self.backlog)

    def test_domain_overlap_is_rejected(self) -> None:
        mutated = self.contract.replace("`20280101..20280120`", "`20271201..20271220`")
        self.assert_contract_rejected(mutated)

    def test_diagnostic_omission_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("D17_SIMULTANEOUS_CONSTRAINT_STATUS", "REMOVED_STATUS"))

    def test_grid_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("exactly 320 cells", "exactly 640 cells"))

    def test_holdout_boundary_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("final_holdout: not_materialized", "final_holdout: created"))

    def test_issue_identity_drift_is_rejected(self) -> None:
        with self.assertRaises(CHECK.ContractError):
            CHECK.validate(self.adr.replace("issue #76", "issue #77"), self.contract, self.backlog)

    def test_feasibility_axis_omission_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("public_coefficient_scale", "removed_scale"))

    def test_aggregate_only_boundary_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("aggregate only", "row-level allowed"))

    def test_reserved_acceptance_boundary_drift_is_rejected(self) -> None:
        with self.assertRaises(CHECK.ContractError):
            CHECK.validate(
                self.adr.replace(
                    "reserved, unassigned, unmaterialized, and inaccessible",
                    "reserved and available",
                ),
                self.contract,
                self.backlog,
            )


if __name__ == "__main__":
    unittest.main()
