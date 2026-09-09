"""RH-02 regressions for explicit, dual-time safety evidence."""

from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker

from inforsight_simulator.domain_snapshot import reconstruct_domain_snapshot
from inforsight_simulator.rules import EligibilityRulesEngine, PolicyContext
from inforsight_simulator.semantic_catalog import load_semantic_catalog
from inforsight_simulator.safety_evidence import (
    SafetyEvidenceError, reconstruct_safety_evidence,
)


ROOT = Path(__file__).resolve().parents[2]


class SafetyEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_semantic_catalog()
        fixture = json.loads((ROOT / "data-contracts/rh/v1/acceptance-fixtures.json").read_text())
        case = copy.deepcopy(next(c for c in fixture["cases"] if c["id"] == "billing_monthly"))
        policy_id = "pol_" + sha256(case["policy_id"].encode()).hexdigest()[:20]
        ids = {e["event_id"]: "evt_" + sha256(e["event_id"].encode()).hexdigest()[:20] for e in case["events"]}
        case["policy_id"] = policy_id
        for event in case["events"]:
            event["policy_id"], event["event_id"] = policy_id, ids[event["event_id"]]
        cls.snapshot = reconstruct_domain_snapshot(
            case["events"], policy_id=policy_id, as_of=case["as_of"],
            source_profile=case["source_profile"], catalog=cls.catalog,
        )

    def _event(self, event_id: str, effective: str, payload: dict, *, ingested: str | None = None, kind: str = "safety.facts_recorded") -> dict:
        return {
            "schema_version": "1.0.0", "event_id": event_id,
            "policy_id": self.snapshot.policy_id, "event_type": kind,
            "effective_at": effective, "ingested_at": ingested or effective,
            "payload": payload,
        }

    def test_source_schema_is_valid_and_accepts_a_record(self) -> None:
        schema = json.loads((ROOT / "data-contracts/rh/v1/safety-event.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        event = self._event("valid", "2026-01-10T00:00:00Z", {"sms_opt_out": False})
        self.assertEqual(list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(event)), [])

    def test_omitted_mapping_values_remain_unknown_and_fail_closed(self) -> None:
        context = PolicyContext.from_dict({
            "policy_id": "p", "as_of": "2026-01-01T00:00:00Z",
            "status": "active", "tenure_days": 100,
            "in_grace_period": False, "days_past_due": 0,
        })
        self.assertIsNone(context.has_active_claim)
        result = EligibilityRulesEngine().evaluate(context)
        self.assertEqual(result.eligible_actions, ())
        self.assertEqual(result.freeze_reason, "DISQUALIFIED_MISSING_SAFETY_EVIDENCE")

    def test_full_clear_evidence_enables_only_satisfied_actions_and_binds_identity(self) -> None:
        clear = {field: False for field in (
            "has_active_claim", "has_legal_hold", "has_registered_dispute",
            "sms_opt_out", "email_opt_out", "phone_opt_out", "dnc_registered",
        )}
        evidence = reconstruct_safety_evidence(
            [self._event("clear", "2026-01-10T00:00:00Z", clear)],
            policy_id=self.snapshot.policy_id, as_of=self.snapshot.as_of,
            snapshot_id=self.snapshot.snapshot_id,
        )
        result = EligibilityRulesEngine().evaluate_snapshot(self.snapshot, self.catalog, evidence)
        self.assertTrue(result.is_eligible("courtesy_reminder"))
        self.assertEqual(result.snapshot_id, self.snapshot.snapshot_id)
        self.assertEqual(result.safety_evidence_id, evidence.evidence_id)

    def test_partial_and_delayed_evidence_stay_unavailable(self) -> None:
        events = [
            self._event("partial", "2026-01-10T00:00:00Z", {"has_active_claim": False}),
            self._event("delayed", "2026-01-10T00:00:00Z", {
                "has_legal_hold": False, "has_registered_dispute": False,
            }, ingested="2027-01-01T00:00:00Z"),
        ]
        evidence = reconstruct_safety_evidence(
            events, policy_id=self.snapshot.policy_id, as_of=self.snapshot.as_of,
            snapshot_id=self.snapshot.snapshot_id,
        )
        result = EligibilityRulesEngine().evaluate_snapshot(self.snapshot, self.catalog, evidence)
        self.assertEqual(result.eligible_actions, ())
        self.assertEqual(result.freeze_reason, "DISQUALIFIED_MISSING_SAFETY_EVIDENCE")

    def test_unknown_channel_evidence_disqualifies_only_that_channel(self) -> None:
        global_clear = {
            "has_active_claim": False, "has_legal_hold": False,
            "has_registered_dispute": False, "phone_opt_out": False,
            "dnc_registered": False,
        }
        evidence = reconstruct_safety_evidence(
            [self._event("phone-clear", "2026-01-10T00:00:00Z", global_clear)],
            policy_id=self.snapshot.policy_id, as_of=self.snapshot.as_of,
            snapshot_id=self.snapshot.snapshot_id,
        )
        result = EligibilityRulesEngine().evaluate_snapshot(self.snapshot, self.catalog, evidence)
        self.assertTrue(result.is_eligible("specialist_phone_outreach"))
        self.assertFalse(result.is_eligible("courtesy_reminder"))
        self.assertIn("DISQUALIFIED_MISSING_SAFETY_EVIDENCE", result.get_reasons("courtesy_reminder"))

    def test_affirmative_hold_blocks_contact_and_context_mismatch_is_rejected(self) -> None:
        values = {field: False for field in (
            "has_active_claim", "has_legal_hold", "has_registered_dispute",
            "sms_opt_out", "email_opt_out", "phone_opt_out", "dnc_registered",
        )}
        values["has_legal_hold"] = True
        evidence = reconstruct_safety_evidence(
            [self._event("hold", "2026-01-10T00:00:00Z", values)],
            policy_id=self.snapshot.policy_id, as_of=self.snapshot.as_of,
            snapshot_id=self.snapshot.snapshot_id,
        )
        result = EligibilityRulesEngine().evaluate_snapshot(self.snapshot, self.catalog, evidence)
        self.assertEqual(result.freeze_reason, "DISQUALIFIED_LEGAL_HOLD")
        with self.assertRaises(SafetyEvidenceError):
            evidence.validate_context(policy_id="other", as_of=self.snapshot.as_of, snapshot_id=self.snapshot.snapshot_id)

    def test_contradictory_same_instant_and_invalid_correction_fail(self) -> None:
        events = [
            self._event("a", "2026-01-10T00:00:00Z", {"sms_opt_out": False}),
            self._event("b", "2026-01-10T00:00:00Z", {"sms_opt_out": True}),
        ]
        with self.assertRaises(SafetyEvidenceError) as contradiction:
            reconstruct_safety_evidence(events, policy_id=self.snapshot.policy_id,
                as_of=self.snapshot.as_of, snapshot_id=self.snapshot.snapshot_id)
        self.assertEqual(contradiction.exception.code, "CONTRADICTORY_SAFETY_EVIDENCE")
        correction = self._event("c", "2026-01-11T00:00:00Z", {
            "target_event_id": "missing", "replacement": {"sms_opt_out": False},
        }, kind="safety.facts_corrected")
        with self.assertRaises(SafetyEvidenceError) as invalid:
            reconstruct_safety_evidence([correction], policy_id=self.snapshot.policy_id,
                as_of=self.snapshot.as_of, snapshot_id=self.snapshot.snapshot_id)
        self.assertEqual(invalid.exception.code, "INVALID_SAFETY_CORRECTION")


if __name__ == "__main__":
    unittest.main()
