import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from agents.adk_adapter import read_only_tools, validate_candidate
from agents.workflow import CaseInput, Fact, Procedure, build_review_draft


def case():
    day = lambda n: datetime(2026, 9, n, tzinfo=timezone.utc)
    return CaseInput("fictional-case-1", day(25),
                     (Fact("payment_status", "late", day(20), "fictional-event-1"),),
                     (Procedure("fictional-procedure", "2.0", day(1), day(30),
                                ("courtesy_reminder",), "Review a reminder."),),
                     ("courtesy_reminder", "abstain"), ("payment_status",),
                     (("fictional-procedure", "2.0"),), 0.95)


def candidate():
    return dict(case_id="fictional-case-1", action_id="courtesy_reminder",
                evidence_source_ids=["fictional-event-1"],
                procedure_citations=["fictional-procedure@2.0"],
                authorized_to_act=False, human_review_required=True)


class CandidateValidationTest(unittest.TestCase):
    def test_matching_candidate_remains_review_only(self):
        self.assertEqual(validate_candidate(case(), json.dumps(candidate())), build_review_draft(case()))

    def test_invalid_shapes_fail_closed(self):
        for raw in ("not-json", "[]", "{}", "x" * 8193, json.dumps({**candidate(), "extra": 1})):
            with self.subTest(raw=raw[:20]):
                self.assertEqual(validate_candidate(case(), raw).reason_codes, ("ADK_INVALID_OUTPUT",))

    def test_mismatches_fail_closed(self):
        for key, value, reason in (
            ("case_id", "other", "ADK_IDENTITY_MISMATCH"),
            ("action_id", "invented", "ADK_ACTION_MISMATCH"),
            ("evidence_source_ids", ["invented"], "ADK_EVIDENCE_MISMATCH"),
            ("procedure_citations", ["invented@1"], "ADK_CITATION_MISMATCH"),
            ("authorized_to_act", True, "ADK_AUTHORITY_VIOLATION"),
            ("human_review_required", False, "ADK_AUTHORITY_VIOLATION"),
        ):
            with self.subTest(key=key):
                self.assertEqual(validate_candidate(case(), json.dumps({**candidate(), key: value})).reason_codes,
                                 (reason,))

    def test_preexisting_abstention_cannot_be_overridden(self):
        unsafe = replace(case(), confidence=0.1)
        self.assertEqual(validate_candidate(unsafe, json.dumps(candidate())), build_review_draft(unsafe))

    def test_tools_are_scoped_and_read_only(self):
        tools = read_only_tools(case())
        self.assertEqual([tool.__name__ for tool in tools],
                         ["read_case_evidence", "read_procedures", "read_rule_allowlist"])
        self.assertEqual(tools[0]()["facts"][0]["source_id"], "fictional-event-1")
        self.assertEqual(tools[1]()["procedures"][0]["version"], "2.0")
        self.assertEqual(tools[2]()["allowed_actions"], ["courtesy_reminder", "abstain"])


if __name__ == "__main__":
    unittest.main()
