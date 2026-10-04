"""The local demo stays review-only through the persisted decision boundary."""

import unittest
from unittest.mock import patch

from scripts.run_p5_04_local_demo import run


class LocalDemoTest(unittest.TestCase):
    def test_abstention_rejection_and_audit(self) -> None:
        calls = []
        case_id = "case-fictional"

        def fake_request(method, path, body=None):
            calls.append((method, path, body))
            if path.endswith("/triage"):
                return {"total_evaluated": 1, "cases": [{"case_id": case_id}]}
            if path.endswith("/agent-drafts"):
                return {"draft": {"status": "ABSTAIN"}}
            if path.endswith("/decision"):
                return {"transition_status": "DISMISSED", "authorized_to_act": False,
                        "audit_record_hash": "a" * 64}
            if len(calls) > 5:
                return {"current_state": "DISMISSED", "authorized_to_act": False}
            return {"current_state": "RECOMMENDED", "authorized_to_act": False,
                    "grounding_hash": "not-a-production-digest",
                    "calibrated_probability": 0.3}

        def fake_submit(draft, **kwargs):
            self.assertEqual(draft.status, "ABSTAIN")
            self.assertEqual(draft.reason_codes, ("MISSING_EVIDENCE",))
            return {"draft": {"status": "ABSTAIN"}}

        with patch("scripts.run_p5_04_local_demo.request", side_effect=fake_request), \
                patch("scripts.run_p5_04_local_demo.submit_review_draft", side_effect=fake_submit):
            result = run()
        self.assertFalse(result["authorized_to_act"])
        self.assertEqual(result["human_decision"], "REJECTED")
        self.assertEqual(result["qualification_scope"], "p5-04-legacy-review-only")
        self.assertEqual(calls[-1][1], "/api/v1/cases/case-fictional")

    def test_refuses_to_claim_released_model_qualification(self) -> None:
        responses = [
            {"total_evaluated": 1, "cases": [{"case_id": "case-fictional"}]},
            {"current_state": "RECOMMENDED", "authorized_to_act": False,
             "grounding_hash": "released-model-digest"},
        ]
        with patch("scripts.run_p5_04_local_demo.request", side_effect=responses), \
                patch("scripts.run_p5_04_local_demo.submit_review_draft") as submit:
            with self.assertRaisesRegex(AssertionError, "legacy review-only Compose overlay"):
                run()
            submit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
