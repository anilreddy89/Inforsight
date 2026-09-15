"""RH-06I focused tests for the bounded inference-only runtime."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from inforsight_inference import (
    BundleLoadError,
    CATALOG_FILE_SHA256,
    CatalogContractError,
    ErrorCode,
    MODEL_BUNDLE_VERSION,
    MODEL_ID,
    RUNTIME_CONTRACT_ID,
    RUNTIME_CONTRACT_VERSION,
    TRUSTED_BUNDLE_SHA256,
    load_configured_runtime,
    load_semantic_catalog,
    load_verified_runtime,
)


ROOT = Path(__file__).resolve().parents[2]
BUNDLE_PATH = ROOT / "docs/experiments/phase-02-10-model-bundle.json"
CATALOG_PATH = ROOT / "data-contracts/rh/v1/semantic-catalog.json"


def sample_features() -> dict[str, object]:
    return {
        "tenure_days": 0.55,
        "premium_amount_cents": 0.96,
        "recent_delay_days": 0.11,
        "recent_failed_payment_count": 0.01,
        "recent_retry_count": 0.01,
        "recent_recovery_count": 0.008,
        "arrears_duration_days": 0.012,
        "rolling_on_time_rate": 0.27,
        "rolling_payment_count": 0.16,
        "recent_notice_count": 0.11,
        "recent_contact_count": 0.10,
        "payment_attribute_missing": 0.02,
        "contact_attribute_missing": 0.0,
        "product_type": "fictional_term_life",
        "billing_frequency": "monthly",
        "notice_category": "none",
        "contact_category": "none",
    }


class RuntimeContractTests(unittest.TestCase):
    def test_verified_load_single_batch_and_identity(self) -> None:
        runtime = load_configured_runtime(BUNDLE_PATH, environ={})
        self.assertTrue(runtime.ready)
        self.assertEqual(runtime.bundle_sha256, TRUSTED_BUNDLE_SHA256)
        self.assertEqual(runtime.catalog.sha256, CATALOG_FILE_SHA256)
        self.assertEqual(RUNTIME_CONTRACT_ID, "inforsight.inference-runtime")
        self.assertEqual(RUNTIME_CONTRACT_VERSION, "1.0.0")
        single = runtime.engine.score_record(sample_features())
        batch = runtime.engine.score_batch([sample_features(), sample_features()])
        self.assertEqual(single, batch[0])
        self.assertEqual(batch[0], batch[1])
        self.assertFalse(hasattr(single, "authorized_to_act"))

    def test_public_api_exposes_no_training_or_evaluation_entry_points(self) -> None:
        import inforsight_inference

        prohibited_tokens = ("fit", "train", "evaluation", "qualification", "generate")
        public_names = tuple(inforsight_inference.__all__)
        self.assertFalse(
            any(token in name.lower() for token in prohibited_tokens for name in public_names)
        )

    def test_unknown_category_is_bounded_and_scores(self) -> None:
        runtime = load_configured_runtime(BUNDLE_PATH, environ={})
        features = sample_features()
        features["product_type"] = "fictional_unseen_product"
        result = runtime.engine.score_record(features)
        self.assertGreaterEqual(result.calibrated_probability, 0.0)
        self.assertLessEqual(result.calibrated_probability, 1.0)

    def test_packaged_catalog_is_byte_identical(self) -> None:
        catalog = load_semantic_catalog()
        self.assertEqual(sha256(CATALOG_PATH.read_bytes()).hexdigest(), catalog.sha256)
        self.assertEqual(catalog.sha256, CATALOG_FILE_SHA256)

    def test_runtime_import_does_not_load_prohibited_modules(self) -> None:
        prohibited = ("sklearn", "xgboost", "scipy", "pandas", "matplotlib", "streamlit")
        loaded = tuple(sys.modules)
        self.assertFalse(any(name == prefix or name.startswith(prefix + ".") for prefix in prohibited for name in loaded))
        self.assertFalse(any(name.startswith("inforsight_simulator") for name in loaded))

    def test_explicit_missing_path_never_falls_back(self) -> None:
        with self.assertRaises(BundleLoadError) as caught:
            load_configured_runtime(
                BUNDLE_PATH,
                environ={"INFORSIGHT_MODEL_BUNDLE_PATH": "/missing/rh06i-bundle.json"},
            )
        self.assertEqual(caught.exception.code, ErrorCode.BUNDLE_PATH_MISSING)

    def test_required_trust_configuration_is_fail_closed(self) -> None:
        with self.assertRaises(BundleLoadError) as caught:
            load_configured_runtime(
                BUNDLE_PATH, environ={"INFORSIGHT_REQUIRE_TRUSTED_BUNDLE": "true"}
            )
        self.assertEqual(caught.exception.code, ErrorCode.TRUST_CONFIGURATION_MISSING)

    def test_not_regular_and_unreadable_paths_use_stable_codes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(BundleLoadError) as caught:
                load_verified_runtime(
                    directory,
                    expected_sha256=TRUSTED_BUNDLE_SHA256,
                    expected_bundle_id=MODEL_ID,
                    expected_bundle_version=MODEL_BUNDLE_VERSION,
                )
            self.assertEqual(caught.exception.code, ErrorCode.BUNDLE_NOT_REGULAR_FILE)

            path = Path(directory) / "bundle.json"
            path.write_bytes(BUNDLE_PATH.read_bytes())
            original_read_bytes = Path.read_bytes

            def fail_selected_path(candidate: Path) -> bytes:
                if candidate == path:
                    raise OSError("fixture unreadable")
                return original_read_bytes(candidate)

            with patch.object(Path, "read_bytes", fail_selected_path):
                with self.assertRaises(BundleLoadError) as caught:
                    load_verified_runtime(
                        path,
                        expected_sha256=TRUSTED_BUNDLE_SHA256,
                        expected_bundle_id=MODEL_ID,
                        expected_bundle_version=MODEL_BUNDLE_VERSION,
                    )
            self.assertEqual(caught.exception.code, ErrorCode.BUNDLE_UNREADABLE)

    def test_digest_is_checked_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_bytes(b"not-json")
            with self.assertRaises(BundleLoadError) as caught:
                load_verified_runtime(
                    path,
                    expected_sha256="0" * 64,
                    expected_bundle_id=MODEL_ID,
                    expected_bundle_version=MODEL_BUNDLE_VERSION,
                )
        self.assertEqual(caught.exception.code, ErrorCode.BUNDLE_DIGEST_MISMATCH)

    def _load_mutation(self, raw: bytes) -> ErrorCode:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_bytes(raw)
            with self.assertRaises(BundleLoadError) as caught:
                load_verified_runtime(
                    path,
                    expected_sha256=sha256(raw).hexdigest(),
                    expected_bundle_id=MODEL_ID,
                    expected_bundle_version=MODEL_BUNDLE_VERSION,
                )
            return caught.exception.code

    def test_encoding_json_and_schema_failures_are_stable(self) -> None:
        self.assertEqual(self._load_mutation(b"\xff"), ErrorCode.BUNDLE_ENCODING_INVALID)
        self.assertEqual(self._load_mutation(b"{"), ErrorCode.BUNDLE_JSON_INVALID)
        duplicated = BUNDLE_PATH.read_text(encoding="utf-8").replace(
            "{\n", "{\n  \"bundle_id\": \"duplicate\",\n", 1
        ).encode("utf-8")
        self.assertEqual(self._load_mutation(duplicated), ErrorCode.BUNDLE_JSON_INVALID)
        value = json.loads(BUNDLE_PATH.read_bytes())
        del value["base_model"]["raw_coefficients"]["tenure_days"]
        malformed = json.dumps(value, sort_keys=True).encode("utf-8")
        self.assertEqual(self._load_mutation(malformed), ErrorCode.BUNDLE_SCHEMA_INVALID)

    def test_identity_version_and_preprocessing_failures_are_stable(self) -> None:
        value = json.loads(BUNDLE_PATH.read_bytes())
        value["bundle_id"] = "fictional-untrusted-id"
        raw = json.dumps(value, sort_keys=True).encode("utf-8")
        self.assertEqual(self._load_mutation(raw), ErrorCode.BUNDLE_ID_MISMATCH)

        value = json.loads(BUNDLE_PATH.read_bytes())
        value["bundle_version"] = "999.0.0"
        raw = json.dumps(value, sort_keys=True).encode("utf-8")
        self.assertEqual(self._load_mutation(raw), ErrorCode.BUNDLE_VERSION_UNSUPPORTED)

        value = json.loads(BUNDLE_PATH.read_bytes())
        value["preprocessor"]["numeric"]["tenure_days"]["mean"] += 0.01
        raw = json.dumps(value, sort_keys=True).encode("utf-8")
        self.assertEqual(self._load_mutation(raw), ErrorCode.PREPROCESSING_IDENTITY_MISMATCH)

    def test_catalog_and_engine_initialization_failures_are_stable(self) -> None:
        with patch(
            "inforsight_inference.bundle.load_semantic_catalog",
            side_effect=CatalogContractError(
                ErrorCode.CATALOG_IDENTITY_MISMATCH,
                "catalog fixture mismatch",
            ),
        ):
            with self.assertRaises(BundleLoadError) as caught:
                load_verified_runtime(
                    BUNDLE_PATH,
                    expected_sha256=TRUSTED_BUNDLE_SHA256,
                    expected_bundle_id=MODEL_ID,
                    expected_bundle_version=MODEL_BUNDLE_VERSION,
                )
        self.assertEqual(caught.exception.code, ErrorCode.CATALOG_IDENTITY_MISMATCH)

        with patch(
            "inforsight_inference.bundle.BundledInferenceEngine",
            side_effect=RuntimeError("fixture engine failure"),
        ):
            with self.assertRaises(BundleLoadError) as caught:
                load_verified_runtime(
                    BUNDLE_PATH,
                    expected_sha256=TRUSTED_BUNDLE_SHA256,
                    expected_bundle_id=MODEL_ID,
                    expected_bundle_version=MODEL_BUNDLE_VERSION,
                )
        self.assertEqual(caught.exception.code, ErrorCode.ENGINE_INITIALIZATION_FAILED)

    def test_feature_payload_failures_do_not_echo_values(self) -> None:
        runtime = load_configured_runtime(BUNDLE_PATH, environ={})
        features = sample_features()
        secret_value = "DO_NOT_ECHO_FEATURE_VALUE"
        features["product_type"] = secret_value
        runtime.engine.score_record(features)
        del features["tenure_days"]
        with self.assertRaises(ValueError) as caught:
            runtime.engine.score_record(features)
        self.assertNotIn(secret_value, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
