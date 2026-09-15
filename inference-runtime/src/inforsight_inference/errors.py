"""Stable, payload-safe inference runtime failures."""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    BUNDLE_PATH_MISSING = "BUNDLE_PATH_MISSING"
    BUNDLE_NOT_REGULAR_FILE = "BUNDLE_NOT_REGULAR_FILE"
    BUNDLE_UNREADABLE = "BUNDLE_UNREADABLE"
    TRUST_CONFIGURATION_MISSING = "TRUST_CONFIGURATION_MISSING"
    BUNDLE_DIGEST_MISMATCH = "BUNDLE_DIGEST_MISMATCH"
    BUNDLE_ENCODING_INVALID = "BUNDLE_ENCODING_INVALID"
    BUNDLE_JSON_INVALID = "BUNDLE_JSON_INVALID"
    BUNDLE_SCHEMA_INVALID = "BUNDLE_SCHEMA_INVALID"
    BUNDLE_ID_MISMATCH = "BUNDLE_ID_MISMATCH"
    BUNDLE_VERSION_UNSUPPORTED = "BUNDLE_VERSION_UNSUPPORTED"
    PREPROCESSING_IDENTITY_MISMATCH = "PREPROCESSING_IDENTITY_MISMATCH"
    CATALOG_IDENTITY_MISMATCH = "CATALOG_IDENTITY_MISMATCH"
    ENGINE_INITIALIZATION_FAILED = "ENGINE_INITIALIZATION_FAILED"


class InferenceRuntimeError(ValueError):
    """A bounded runtime failure with a stable machine-readable code."""

    def __init__(self, code: ErrorCode | str, summary: str) -> None:
        self.code = ErrorCode(code)
        self.summary = summary
        super().__init__(f"{self.code.value}: {summary}")


class BundleLoadError(InferenceRuntimeError):
    """A failure while selecting, reading, trusting, or validating a bundle."""


class CatalogContractError(InferenceRuntimeError):
    """A failure while loading or applying the packaged semantic catalog."""

