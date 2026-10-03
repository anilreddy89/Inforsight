import json
import unittest

from agents.control_plane_bridge import local_http_transport, submit_review_draft
from agents.tests.test_adk_adapter import case
from agents.workflow import build_review_draft


class ControlPlaneBridgeTest(unittest.TestCase):
    def test_review_only_payload_and_explicit_transport(self):
        calls = []

        def transport(path, body):
            calls.append((path, json.loads(body)))
            return {"case_id": "fictional-case-1", "case_version": 0, "authorized_to_act": False}

        result = submit_review_draft(build_review_draft(case()), expected_case_version=0,
                                     idempotency_key="fictional-idem-1", transport=transport)
        self.assertFalse(result["authorized_to_act"])
        self.assertEqual(calls[0][0], "/api/v1/cases/fictional-case-1/agent-drafts")
        self.assertEqual(calls[0][1]["action_id"], "courtesy_reminder")
        self.assertFalse(calls[0][1]["authorized_to_act"])
        self.assertTrue(calls[0][1]["human_review_required"])

    def test_invalid_version_and_remote_url_rejected(self):
        with self.assertRaises(ValueError):
            submit_review_draft(build_review_draft(case()), expected_case_version=-1,
                                idempotency_key="idem", transport=lambda *_: {})
        with self.assertRaises(ValueError):
            local_http_transport("https://example.com")


if __name__ == "__main__":
    unittest.main()
