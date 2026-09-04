"""Unit and mutation tests for the Generation v6 bounded sigmoid contract boundary."""

from importlib.util import module_from_spec, spec_from_file_location
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = spec_from_file_location("r2_14c_check", ROOT / "scripts/check_r2_14c_v6_contract.py")
assert SPEC and SPEC.loader
CHECK = module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def sigmoid_v6(z: float) -> float:
    clipped = max(-15.0, min(15.0, z))
    return 1.0 / (1.0 + math.exp(-clipped))


class V6BoundedSigmoidContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adr = CHECK.ADR_PATH.read_text(encoding="utf-8")
        cls.contract = CHECK.CONTRACT_PATH.read_text(encoding="utf-8")
        cls.backlog = CHECK.BACKLOG_PATH.read_text(encoding="utf-8")
        cls.adr_index = CHECK.ADR_INDEX_PATH.read_text(encoding="utf-8")

    def assert_contract_rejected(self, contract: str) -> None:
        with self.assertRaises(CHECK.ContractError):
            CHECK.validate(self.adr, contract, self.backlog, self.adr_index)

    def test_repository_contract_passes(self) -> None:
        # Note: Backlog will be updated in next step; test with self.backlog
        CHECK.validate(self.adr, self.contract, self.backlog, self.adr_index)

    def test_domain_overlap_is_rejected(self) -> None:
        mutated = self.contract.replace("`20280201..20280220`", "`20280101..20280120`")
        self.assert_contract_rejected(mutated)

    def test_contract_version_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("Contract version | `6.0.0`", "Contract version | `5.0.0`"))

    def test_holdout_boundary_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("final_holdout` | `not_materialized`", "final_holdout` | `created`"))

    def test_adr_issue_drift_is_rejected(self) -> None:
        with self.assertRaises(CHECK.ContractError):
            CHECK.validate(self.adr.replace("issue #86", "issue #99"), self.contract, self.backlog, self.adr_index)

    def test_hazard_ceiling_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("0.10 + 0.05 = 0.1500 < 0.2000", "0.25 + 0.15 = 0.4000"))

    def test_clipping_bounds_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace(r"\text{clip}(z, -15.0, 15.0)", r"\text{clip}(z, -50.0, 50.0)"))

    def test_quadrature_specification_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("32-node Gauss-Hermite quadrature", "10-node Monte Carlo"))

    def test_qualification_gate_drift_is_rejected(self) -> None:
        self.assert_contract_rejected(self.contract.replace("observable-oracle AUC", "removed-metric"))

    def test_mathematical_hazard_bounds_strictly_enforced(self) -> None:
        lambda_max_lapse = 0.10
        lambda_max_surrender = 0.05
        test_z_values = [-1000.0, -100.0, -15.0, -5.0, -1.0, 0.0, 1.0, 5.0, 15.0, 100.0, 1000.0]
        
        prev_sig = 0.0
        for z in test_z_values:
            sig = sigmoid_v6(z)
            self.assertGreater(sig, 0.0)
            self.assertLess(sig, 1.0)
            self.assertGreaterEqual(sig, prev_sig)
            prev_sig = sig

            h_lapse = lambda_max_lapse * sig
            h_surrender = lambda_max_surrender * sig
            h_total = h_lapse + h_surrender
            self.assertLessEqual(h_total, 0.1500)
            self.assertLess(h_total, 0.2000)

    def test_seed_domains_are_strictly_isolated(self) -> None:
        domains = CHECK.EXPECTED_DOMAINS
        self.assertEqual(len(domains), 5)
        for name, seeds in domains.items():
            self.assertEqual(len(seeds), 20, f"Domain {name} must have 20 seeds")
        
        all_seeds = set()
        for name, seeds in domains.items():
            intersection = all_seeds.intersection(seeds)
            self.assertEqual(len(intersection), 0, f"Domain {name} overlaps with previous domains: {intersection}")
            all_seeds.update(seeds)


if __name__ == "__main__":
    unittest.main()
