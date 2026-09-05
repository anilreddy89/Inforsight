"""Contract tests for Phase 3 conservation domain contracts.

Tests data-contracts/conservation-action.schema.json and
data-contracts/conservation-case-event.schema.json under Draft 2020-12,
enforcing ADR 0002 human review authority boundaries and action parameters.
"""

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

CONTRACTS_DIR = Path(__file__).resolve().parents[1]
ACTION_SCHEMA_PATH = CONTRACTS_DIR / "conservation-action.schema.json"
CASE_EVENT_SCHEMA_PATH = CONTRACTS_DIR / "conservation-case-event.schema.json"

ACTION_VALID_DIR = CONTRACTS_DIR / "examples" / "conservation-action" / "valid"
ACTION_INVALID_DIR = CONTRACTS_DIR / "examples" / "conservation-action" / "invalid"

CASE_EVENT_VALID_DIR = CONTRACTS_DIR / "examples" / "conservation-case-event" / "valid"
CASE_EVENT_INVALID_DIR = CONTRACTS_DIR / "examples" / "conservation-case-event" / "invalid"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


class ConservationContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.action_schema = load_json(ACTION_SCHEMA_PATH)
        cls.case_event_schema = load_json(CASE_EVENT_SCHEMA_PATH)

        # Check schema validity under Draft 2020-12
        Draft202012Validator.check_schema(cls.action_schema)
        Draft202012Validator.check_schema(cls.case_event_schema)

        cls.action_validator = Draft202012Validator(
            cls.action_schema,
            format_checker=FormatChecker(),
        )
        cls.case_event_validator = Draft202012Validator(
            cls.case_event_schema,
            format_checker=FormatChecker(),
        )

    def test_schemas_are_valid_draft202012(self) -> None:
        """Verify schemas pass Draft202012Validator.check_schema."""
        Draft202012Validator.check_schema(self.action_schema)
        Draft202012Validator.check_schema(self.case_event_schema)

    def test_all_valid_conservation_action_examples(self) -> None:
        """Verify all valid conservation action fixtures pass validation."""
        valid_files = list(ACTION_VALID_DIR.glob("*.json"))
        self.assertGreater(len(valid_files), 0, "No valid action fixtures found")
        for fixture_path in valid_files:
            with self.subTest(fixture=fixture_path.name):
                data = load_json(fixture_path)
                errors = list(self.action_validator.iter_errors(data))
                self.assertEqual(
                    len(errors), 0,
                    f"Valid action {fixture_path.name} had validation errors: {errors}"
                )

    def test_all_invalid_conservation_action_examples(self) -> None:
        """Verify all invalid conservation action fixtures fail validation."""
        invalid_files = list(ACTION_INVALID_DIR.glob("*.json"))
        self.assertGreater(len(invalid_files), 0, "No invalid action fixtures found")
        for fixture_path in invalid_files:
            with self.subTest(fixture=fixture_path.name):
                data = load_json(fixture_path)
                errors = list(self.action_validator.iter_errors(data))
                self.assertGreater(
                    len(errors), 0,
                    f"Invalid action {fixture_path.name} unexpectedly passed validation"
                )

    def test_all_valid_conservation_case_event_examples(self) -> None:
        """Verify all valid conservation case event fixtures pass validation."""
        valid_files = sorted(CASE_EVENT_VALID_DIR.glob("*.json"))
        self.assertGreater(len(valid_files), 0, "No valid case event fixtures found")
        for fixture_path in valid_files:
            with self.subTest(fixture=fixture_path.name):
                data = load_json(fixture_path)
                errors = list(self.case_event_validator.iter_errors(data))
                self.assertEqual(
                    len(errors), 0,
                    f"Valid case event {fixture_path.name} had validation errors: {errors}"
                )

    def test_all_invalid_conservation_case_event_examples(self) -> None:
        """Verify all invalid conservation case event fixtures fail validation."""
        invalid_files = list(CASE_EVENT_INVALID_DIR.glob("*.json"))
        self.assertGreater(len(invalid_files), 0, "No invalid case event fixtures found")
        for fixture_path in invalid_files:
            with self.subTest(fixture=fixture_path.name):
                data = load_json(fixture_path)
                errors = list(self.case_event_validator.iter_errors(data))
                self.assertGreater(
                    len(errors), 0,
                    f"Invalid case event {fixture_path.name} unexpectedly passed validation"
                )

    def test_direct_execution_forbidden_adr_0002(self) -> None:
        """ADR 0002 Invariant: Direct RECOMMENDED -> EXECUTED transition is forbidden."""
        invalid_direct_transition = {
            "schema_version": "1.0.0",
            "case_event_id": "cev_0123456789abcdef",
            "case_id": "case_0123456789abcdef",
            "policy_id": "pol_0123456789abcdef",
            "from_state": "RECOMMENDED",
            "to_state": "EXECUTED",
            "occurred_at": "2026-09-01T10:00:00Z",
            "payload": {
                "human_review": {
                    "reviewer_id": "usr_spec_101",
                    "reviewed_at": "2026-09-01T10:00:00Z",
                    "decision": "APPROVED",
                    "rationale_code": "APPROVED_STANDARD",
                    "justification": "Approved"
                }
            }
        }
        errors = list(self.case_event_validator.iter_errors(invalid_direct_transition))
        self.assertGreater(
            len(errors), 0,
            "Direct RECOMMENDED -> EXECUTED transition must fail schema validation under ADR 0002"
        )

    def test_action_cost_rules(self) -> None:
        """Verify positive cost for active interventions and zero cost for abstain."""
        base_action = {
            "schema_version": "1.0.0",
            "action_id": "act_test_action",
            "action_type": "courtesy_reminder",
            "channel": "sms",
            "direct_cost_usd": 0.0,  # Invalid: 0.0 for active intervention
            "personnel_hours": 0.0,
            "regulatory_cooling_off_days": 30,
            "minimum_policy_tenure_days": 30,
            "maximum_policy_tenure_days": None,
            "requires_grace_period": False
        }
        # 0.0 cost for courtesy_reminder fails
        errors = list(self.action_validator.iter_errors(base_action))
        self.assertGreater(len(errors), 0, "Active action with 0.0 cost must fail")

        # Change to abstain with 0.0 cost and none channel passes
        base_action["action_type"] = "abstain"
        base_action["channel"] = "none"
        errors = list(self.action_validator.iter_errors(base_action))
        self.assertEqual(len(errors), 0, "Abstain with 0.0 cost and channel none must pass")

    def test_action_channel_rules(self) -> None:
        """Verify active actions cannot have channel 'none'."""
        active_with_none_channel = {
            "schema_version": "1.0.0",
            "action_id": "act_test_action",
            "action_type": "specialist_phone_outreach",
            "channel": "none",  # Invalid for active intervention
            "direct_cost_usd": 65.0,
            "personnel_hours": 1.0,
            "regulatory_cooling_off_days": 30,
            "minimum_policy_tenure_days": 60,
            "maximum_policy_tenure_days": None,
            "requires_grace_period": False
        }
        errors = list(self.action_validator.iter_errors(active_with_none_channel))
        self.assertGreater(len(errors), 0, "Active intervention with channel 'none' must fail")


if __name__ == "__main__":
    unittest.main()

