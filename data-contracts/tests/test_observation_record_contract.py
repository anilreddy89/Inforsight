"""Contract tests for mutually exclusive observation-record states."""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


CONTRACTS_DIR = Path(__file__).resolve().parents[1]


class ObservationRecordContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        schema = json.loads(
            (CONTRACTS_DIR / "observation-record.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )
        cls.valid = {
            "observation_contract_version": "1.0.0",
            "label_policy_version": "1.0.0",
            "observation_id": "obs_0123456789abcdef01234567",
            "policy_id": "pol_0123456789ab",
            "as_of": "2024-02-01T00:00:00Z",
            "horizon_start": "2024-02-01T00:00:00Z",
            "horizon_end": "2024-05-01T00:00:00Z",
            "follow_up_through": "2024-05-01T00:00:00Z",
            "eligible": True,
            "eligibility_reason": "eligible_active",
            "features": {
                "current_status": "active",
                "product_variant": "level_term",
                "billing_frequency": "monthly",
                "premium_amount_cents": 7500,
                "currency": "USD",
                "policy_age_days": 31,
                "visible_event_count": 2,
                "visible_billing_count": 1,
                "visible_failed_payment_count": 0,
                "visible_received_payment_count": 0,
                "visible_notice_count": 0,
                "visible_service_contact_count": 0,
            },
            "label": {
                "status": "observed_negative",
                "value": 0,
                "outcome_type": None,
                "source_event_id": None,
                "source_effective_at": None,
                "source_ingested_at": None,
                "censoring_reason": None,
            },
            "visible_event_ids": ["evt_0123456789ab", "evt_0123456789ac"],
            "generator_version": "0.1.0",
            "event_schema_version": "1.0.0",
        }

    def test_valid_label_variants_are_accepted(self) -> None:
        variants = (
            {},
            {
                "status": "observed_positive",
                "value": 1,
                "outcome_type": "outcome.lapsed",
                "source_event_id": "evt_0123456789ad",
                "source_effective_at": "2024-03-01T00:00:00Z",
                "source_ingested_at": "2024-03-01T01:00:00Z",
                "censoring_reason": None,
            },
            {
                "status": "right_censored",
                "value": None,
                "outcome_type": None,
                "source_event_id": None,
                "source_effective_at": None,
                "source_ingested_at": None,
                "censoring_reason": "follow_up_ends_before_horizon",
            },
        )
        for label in variants:
            candidate = copy.deepcopy(self.valid)
            candidate["label"].update(label)
            self.assertEqual(list(self.validator.iter_errors(candidate)), [])

        ineligible = copy.deepcopy(self.valid)
        ineligible.update(
            eligible=False,
            eligibility_reason="policy_not_visible",
            features=None,
        )
        ineligible["label"] = {
            "status": "not_applicable",
            "value": None,
            "outcome_type": None,
            "source_event_id": None,
            "source_effective_at": None,
            "source_ingested_at": None,
            "censoring_reason": None,
        }
        self.assertEqual(list(self.validator.iter_errors(ineligible)), [])

    def test_contradictory_states_are_rejected(self) -> None:
        mutations = (
            ("label", "value", 1),
            ("label", "censoring_reason", "follow_up_ends_before_horizon"),
            (None, "features", None),
            (None, "eligibility_reason", "policy_not_visible"),
            (None, "event_schema_version", "9.0.0"),
            ("features", "currency", "EUR"),
            ("features", "visible_event_count", True),
        )
        for container, field, value in mutations:
            with self.subTest(container=container, field=field):
                candidate = copy.deepcopy(self.valid)
                target = candidate if container is None else candidate[container]
                target[field] = value
                self.assertTrue(list(self.validator.iter_errors(candidate)))


if __name__ == "__main__":
    unittest.main()
