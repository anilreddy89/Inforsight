import pytest

from simulator.rh09_contracts import (
    ContractViolation,
    IdempotencyGuard,
    require_authority,
    require_context,
    require_current_case_version,
    require_identity_bindings,
    require_override,
    require_risk_tier,
)


def test_mutation_context_is_explicit_and_typed():
    context = require_context({
        "case_id": "case-1",
        "expected_case_version": 3,
        "idempotency_key": "idem-1",
        "actor_id": "reviewer-1",
        "reviewed_evidence_digest": "sha256:abc",
    })
    assert context.expected_case_version == 3


@pytest.mark.parametrize("value", [None, "false", 0, 1])
def test_authority_requires_presence_aware_boolean(value):
    with pytest.raises(ContractViolation, match="AUTHORITY_EXPLICIT_REQUIRED"):
        require_authority(value)


def test_unknown_and_ordinal_risk_tiers_are_rejected():
    for value in ("HIGH", 3, "TIER_9_CRITICAL"):
        with pytest.raises(ContractViolation, match="UNKNOWN_RISK_TIER"):
            require_risk_tier(value)
    assert require_risk_tier("TIER_3_HIGH") == "TIER_3_HIGH"


def test_override_requires_trusted_reviewer_evidence():
    with pytest.raises(ContractViolation, match="OVERRIDE_EVIDENCE_REQUIRED"):
        require_override({"override": True})
    require_override({
        "override": True,
        "trusted_reviewer_id": "reviewer-1",
        "override_rationale": "verified",
        "reviewed_case_version": 3,
        "reviewed_evidence_digest": "sha256:abc",
    })


def test_identity_bindings_and_stale_versions_fail_without_payload_echo():
    with pytest.raises(ContractViolation, match="IDENTITY_MISMATCH"):
        require_identity_bindings({"model_id": "model-b"}, {"model_id": "model-a"})
    with pytest.raises(ContractViolation, match="STALE_CASE_VERSION"):
        require_current_case_version(2, 3)


def test_idempotency_guard_rejects_replay_and_key_reuse():
    guard = IdempotencyGuard()
    guard.check_and_record("idem-1", "fingerprint-a")
    with pytest.raises(ContractViolation, match="REQUEST_REPLAYED"):
        guard.check_and_record("idem-1", "fingerprint-a")
    with pytest.raises(ContractViolation, match="IDEMPOTENCY_KEY_REUSED"):
        guard.check_and_record("idem-1", "fingerprint-b")
