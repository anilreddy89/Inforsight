import copy
from hashlib import sha256
import json
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


SIMULATOR_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SIMULATOR_DIR.parent
sys.path.insert(0, str(SIMULATOR_DIR / "src"))

from inforsight_simulator.domain_snapshot import (  # noqa: E402
    SnapshotContractError,
    load_json_events,
    reconstruct_domain_snapshot,
)
from inforsight_simulator.semantic_catalog import (  # noqa: E402
    CatalogContractError,
    load_semantic_catalog,
)


class DomainSnapshotFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_semantic_catalog(repository_root=REPOSITORY_ROOT)
        cls.fixture = json.loads(
            (REPOSITORY_ROOT / "data-contracts/rh/v1/acceptance-fixtures.json").read_text()
        )
        schema = json.loads(
            (REPOSITORY_ROOT / "data-contracts/rh/v1/domain-snapshot.schema.json").read_text()
        )
        cls.validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def test_all_accepted_fixture_projections_and_errors(self) -> None:
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                if "catalog_version" in case:
                    with self.assertRaises(CatalogContractError) as raised:
                        load_semantic_catalog(
                            case["catalog_version"], repository_root=REPOSITORY_ROOT
                        )
                    self.assertEqual(raised.exception.code, case["expected"]["error"])
                    continue
                expected = case["expected"]
                if "error" in expected:
                    with self.assertRaises(SnapshotContractError) as raised:
                        self._reconstruct(case)
                    self.assertEqual(raised.exception.code, expected["error"])
                    continue
                snapshot = self._reconstruct(case)
                if "result" in expected:
                    self.assertIsNone(snapshot)
                    continue
                assert snapshot is not None
                self.validator.validate(snapshot.to_dict())
                actual = snapshot.to_dict()
                for key, value in expected.items():
                    if key == "adapter_error":
                        continue
                    if key == "visible_ids":
                        self.assertEqual(
                            [item.event_id for item in snapshot.provenance],
                            [self._event_id(item) for item in value]
                            if case["source_profile"].startswith("legacy-") else value,
                        )
                    elif key == "all_safety_fields":
                        self.assertTrue(all(item is value for item in actual["safety"].values()))
                    else:
                        self.assertEqual(actual[key], value)

    def test_identity_is_stable_under_input_order_and_invisible_append(self) -> None:
        shuffled = self._case("shuffled")
        first = self._reconstruct(shuffled)
        reversed_case = copy.deepcopy(shuffled)
        reversed_case["events"].reverse()
        second = self._reconstruct(reversed_case)
        self.assertEqual(first, second)

        invisible = self._case("invisible_payload")
        full = self._reconstruct(invisible)
        issuance_only = copy.deepcopy(invisible)
        issuance_only["events"] = issuance_only["events"][:1]
        self.assertEqual(full, self._reconstruct(issuance_only))

    def test_identity_changes_with_cutoff_or_visible_content(self) -> None:
        case = self._case("billing_monthly")
        first = self._reconstruct(case)
        later = copy.deepcopy(case)
        later["as_of"] = "2026-01-21T00:00:00Z"
        changed = copy.deepcopy(case)
        changed["events"][0]["payload"]["premium_amount_cents"] += 1
        self.assertNotEqual(first.snapshot_id, self._reconstruct(later).snapshot_id)
        self.assertNotEqual(first.snapshot_id, self._reconstruct(changed).snapshot_id)

    def test_snapshot_is_frozen_and_does_not_retain_mutable_inputs(self) -> None:
        case = self._case("shuffled")
        snapshot = self._reconstruct(case)
        original = snapshot.to_dict()
        case["events"][0]["payload"]["new_status"] = "surrendered"
        self.assertEqual(snapshot.to_dict(), original)
        with self.assertRaises(FrozenInstanceError):
            snapshot.status = "active"  # type: ignore[misc]

    def test_duplicate_json_keys_and_nonfinite_values_are_rejected(self) -> None:
        with self.assertRaises(SnapshotContractError) as duplicate:
            load_json_events('{"event_id":"one","event_id":"two"}')
        self.assertEqual(duplicate.exception.code, "INVALID_ENVELOPE")
        with self.assertRaises(SnapshotContractError) as nonfinite:
            load_json_events('{"value":NaN}')
        self.assertEqual(nonfinite.exception.code, "INVALID_ENVELOPE")

    def test_catalog_adapters_are_explicit(self) -> None:
        self.assertEqual(self.catalog.risk_tier(0.1), "TIER_2_MODERATE")
        self.assertEqual(self.catalog.risk_tier(1.0), "TIER_4_CRITICAL")
        self.assertEqual(
            self.catalog.map_risk_tier(
                "TIER_2_ELEVATED", adapter_profile="provisional-proto-risk-tier/1.0.0"
            ),
            "TIER_3_HIGH",
        )
        with self.assertRaises(CatalogContractError):
            self.catalog.map_risk_tier("TIER_2_ELEVATED")
        mismatch = self._case("preprocessing_mismatch")
        with self.assertRaises(CatalogContractError) as raised:
            self.catalog.require_preprocessing_profile(mismatch["preprocessing_profile"])
        self.assertEqual(raised.exception.code, mismatch["expected"]["adapter_error"])

    def test_consumer_context_must_match_snapshot_policy_and_cutoff(self) -> None:
        snapshot = self._reconstruct(self._case("billing_monthly"))
        snapshot.validate_context(
            policy_id=snapshot.policy_id, as_of=snapshot.as_of, catalog=self.catalog
        )
        for policy_id, as_of in (
            ("another-policy", snapshot.as_of),
            (snapshot.policy_id, "2026-01-21T00:00:00Z"),
        ):
            with self.subTest(policy_id=policy_id, as_of=as_of):
                with self.assertRaises(SnapshotContractError) as raised:
                    snapshot.validate_context(
                        policy_id=policy_id, as_of=as_of, catalog=self.catalog
                    )
                self.assertEqual(raised.exception.code, "CONTEXT_MISMATCH")

    def test_v6_payment_correction_and_terminal_replay(self) -> None:
        events = [
            self._v6_event("issued", "policy.issued", "2025-01-01T00:00:00Z", {
                "billing_frequency": "monthly", "premium_amount_cents": 10000,
                "currency": "USD", "product_type": "fictional_term_life",
            }),
            self._v6_event("payment", "payment.recorded", "2025-02-01T00:00:00Z", {
                "arrears_days": 17, "delay_days": 8.0, "failed": 1, "on_time": 0,
                "recovered": 0, "retry": 0, "scheduled_opportunity_ordinal": 1,
            }),
            self._v6_event("correction", "event.corrected", "2025-02-02T00:00:00Z", {
                "target_event_id": "payment", "replacement_delay_days": 4.0,
            }),
            self._v6_event("lapsed", "outcome.lapsed", "2025-03-01T00:00:00Z", {
                "cause": "lapsed",
            }),
        ]
        snapshot = reconstruct_domain_snapshot(
            events, policy_id="v6-policy", as_of="2025-03-01T00:00:00Z",
            source_profile="v6-policy-events/6.0.0", catalog=self.catalog,
        )
        self.assertEqual(snapshot.status, "lapsed")
        self.assertEqual(snapshot.days_past_due, 17)
        self.assertEqual(snapshot.field_evidence.days_past_due, ("payment",))
        self.assertEqual([item.event_id for item in snapshot.provenance], [
            "issued", "payment", "correction", "lapsed",
        ])

    def test_v6_invalid_correction_and_ambiguous_terminal_fail(self) -> None:
        issuance = self._v6_event("issued", "policy.issued", "2025-01-01T00:00:00Z", {
            "billing_frequency": "annual", "premium_amount_cents": 120000,
            "currency": "USD", "product_type": "fictional_whole_life",
        })
        correction = self._v6_event("correction", "event.corrected", "2025-02-01T00:00:00Z", {
            "target_event_id": "missing", "replacement_delay_days": 1,
        })
        with self.assertRaises(SnapshotContractError) as invalid:
            reconstruct_domain_snapshot(
                [issuance, correction], policy_id="v6-policy", as_of="2025-03-01T00:00:00Z",
                source_profile="v6-policy-events/6.0.0", catalog=self.catalog,
            )
        self.assertEqual(invalid.exception.code, "INVALID_CORRECTION")

        outcomes = [
            self._v6_event("lapsed", "outcome.lapsed", "2025-02-01T00:00:00Z", {"cause": "lapsed"}),
            self._v6_event("surrendered", "outcome.surrendered", "2025-02-02T00:00:00Z", {"cause": "surrendered"}),
        ]
        with self.assertRaises(SnapshotContractError) as ambiguous:
            reconstruct_domain_snapshot(
                [issuance, *outcomes], policy_id="v6-policy", as_of="2025-03-01T00:00:00Z",
                source_profile="v6-policy-events/6.0.0", catalog=self.catalog,
            )
        self.assertEqual(ambiguous.exception.code, "AMBIGUOUS_STATUS")

    def _case(self, case_id: str) -> dict:
        return copy.deepcopy(next(item for item in self.fixture["cases"] if item["id"] == case_id))

    def _reconstruct(self, case: dict):
        case = self._expand_legacy_fixture(case)
        return reconstruct_domain_snapshot(
            case["events"],
            policy_id=case["policy_id"],
            as_of=case["as_of"],
            source_profile=case["source_profile"],
            catalog=self.catalog,
        )

    @staticmethod
    def _event_id(value: str) -> str:
        return "evt_" + sha256(value.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def _v6_event(event_id: str, event_type: str, effective_at: str, payload: dict) -> dict:
        return {
            "schema_version": "6.0.0", "event_id": event_id,
            "policy_id": "v6-policy", "event_type": event_type,
            "effective_at": effective_at, "ingested_at": effective_at,
            "payload": payload,
        }

    @classmethod
    def _expand_legacy_fixture(cls, case: dict) -> dict:
        case = copy.deepcopy(case)
        if not case["source_profile"].startswith("legacy-"):
            return case
        policy_id = "pol_" + sha256(case["policy_id"].encode("utf-8")).hexdigest()[:20]
        event_ids = {event["event_id"]: cls._event_id(event["event_id"]) for event in case["events"]}
        case["policy_id"] = policy_id
        for event in case["events"]:
            event["policy_id"] = policy_id
            event["event_id"] = event_ids[event["event_id"]]
            for reference in ("billing_event_id", "target_event_id"):
                if reference in event["payload"] and event["payload"][reference] in event_ids:
                    event["payload"][reference] = event_ids[event["payload"][reference]]
        return case


if __name__ == "__main__":
    unittest.main()
