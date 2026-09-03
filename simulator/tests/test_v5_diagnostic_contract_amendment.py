"""Mutation tests for the documentation-only R2-14BA contract amendment."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = spec_from_file_location("r2_14ba_check", ROOT / "scripts/check_r2_14ba_diagnostic_contract.py")
assert SPEC and SPEC.loader
CHECK = module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class V5DiagnosticContractAmendmentTests(unittest.TestCase):
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
            CHECK.validate(self.adr.replace("issue #80", "issue #99"), self.contract, self.backlog)

    def test_feasibility_axis_omission_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("public_coefficient_scale", "removed_scale"))

    def test_disposition_token_omission_is_rejected(self) -> None:
        mutated = self.contract.replace("H1_LOG_HAZARD_SPREAD supported when", "H1_LOG_HAZARD_SPREAD omitted when")
        self.assert_contract_rejected(mutated)

    def test_feasibility_token_omission_is_rejected(self) -> None:
        mutated = self.contract.replace("H6_DESIGN_FEASIBILITY feasible when", "H6_DESIGN_FEASIBILITY omitted when")
        self.assert_contract_rejected(mutated)

    def test_aggregate_only_boundary_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("aggregate only", "row-level allowed"))


if __name__ == "__main__":
    unittest.main()

