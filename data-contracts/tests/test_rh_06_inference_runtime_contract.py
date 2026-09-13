"""Design validation for RH-06 inference runtime contract 1.0.0."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = ROOT / "data-contracts/rh/inference-runtime/v1"


class RH06InferenceRuntimeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((CONTRACT_DIR / "inference-runtime-contract.json").read_text())
        cls.schema = json.loads((CONTRACT_DIR / "inference-runtime-contract.schema.json").read_text())
        cls.fixtures = json.loads((CONTRACT_DIR / "acceptance-fixtures.json").read_text())

    def test_contract_matches_closed_schema(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        Draft202012Validator(self.schema).validate(self.contract)

    def test_trusted_release_bundle_identity_matches_repository_bytes(self) -> None:
        expected = self.contract["trusted_bundle"]
        artifact = ROOT / expected["repository_path"]
        self.assertEqual(sha256(artifact.read_bytes()).hexdigest(), expected["file_sha256"])
        parsed = json.loads(artifact.read_text())
        self.assertEqual(parsed["bundle_id"], expected["bundle_id"])
        self.assertEqual(parsed["bundle_version"], expected["bundle_version"])

    def test_semantic_catalog_identity_matches_canonical_bytes(self) -> None:
        expected = self.contract["semantic_catalog"]
        catalog_path = ROOT / expected["source_path"]
        self.assertEqual(sha256(catalog_path.read_bytes()).hexdigest(), expected["file_sha256"])
        catalog = json.loads(catalog_path.read_text())
        self.assertEqual(catalog["catalog_version"], expected["catalog_version"])
        self.assertEqual(
            catalog["preprocessing"]["profile_id"],
            self.contract["trusted_bundle"]["preprocessing_profile_id"],
        )

    def test_runtime_dependency_and_import_boundaries_are_explicit(self) -> None:
        self.assertEqual(self.contract["runtime_dependencies"], ["numpy==2.5.2"])
        prohibited = set(self.contract["prohibited_distributions"])
        self.assertTrue({"inforsight-simulator", "scikit-learn", "xgboost"}.issubset(prohibited))
        prefixes = set(self.contract["prohibited_module_prefixes"])
        self.assertTrue({"sklearn", "xgboost", "inforsight_simulator.v6_evaluation"}.issubset(prefixes))
        self.assertTrue(all(name.startswith("inforsight_inference.") for name in self.contract["runtime_modules"]))

    def test_explicit_path_and_trust_configuration_fail_closed(self) -> None:
        configuration = self.contract["configuration"]
        self.assertEqual(configuration["explicit_path_fallback"], "forbidden")
        self.assertTrue(configuration["canonical_image_requires_trusted_bundle"])
        self.assertEqual(
            self.contract["validation_order"][:4],
            ["resolve_path", "read_exact_bytes", "verify_byte_sha256", "parse_strict_json"],
        )
        codes = set(self.contract["failure_codes"])
        self.assertTrue(
            {
                "BUNDLE_PATH_MISSING",
                "TRUST_CONFIGURATION_MISSING",
                "BUNDLE_DIGEST_MISMATCH",
                "BUNDLE_ID_MISMATCH",
                "BUNDLE_VERSION_UNSUPPORTED",
            }.issubset(codes)
        )

    def test_serving_and_container_contract_exposes_only_implemented_http(self) -> None:
        serving = self.contract["serving"]
        containers = self.contract["containers"]
        self.assertEqual(serving["asgi_target"], "serving.app:app")
        self.assertEqual(serving["implemented_protocols"], ["http_rest"])
        self.assertIn("GET /health", serving["routes"])
        self.assertFalse(serving["authorized_to_act"])
        self.assertEqual(containers["canonical_exposed_ports"], [8000])
        self.assertEqual(containers["health_route"], "/health")
        self.assertEqual(containers["grpc"], "not_implemented")
        self.assertEqual(containers["java_control_plane"], "non_runnable_scaffold")

    def test_predeclared_fixture_matrix_is_complete_and_unique(self) -> None:
        cases = self.fixtures["cases"]
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 14)
        categories = {case["category"] for case in cases}
        self.assertEqual(
            categories,
            {"packaging", "imports", "compatibility", "startup_failure", "serving", "container", "scope"},
        )
        fixture_codes = {
            code
            for case in cases
            for code in ([case["expected_code"]] if "expected_code" in case else case.get("expected_codes", []))
        }
        self.assertTrue(fixture_codes.issubset(set(self.contract["failure_codes"])))


if __name__ == "__main__":
    unittest.main()
