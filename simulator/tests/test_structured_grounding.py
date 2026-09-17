"""RH-08I structured-grounding contract regressions."""

from __future__ import annotations

import unittest

from inforsight_simulator.assistant import (
    Evidence,
    GroundingContractError,
    GroundingErrorCode,
    NarrativeContext,
    NarrativeStatement,
    StatementKind,
    render_statements,
    validate_provider_payload,
    context_from_case_evidence,
)


class TestStructuredGrounding(unittest.TestCase):
    def setUp(self) -> None:
        self.context = NarrativeContext(
            policy_id="pol_1",
            case_id="case_1",
            cutoff="2026-09-01T00:00:00Z",
            snapshot_id="snap_1",
            score_identity="bundle_1",
            eligibility_identity="eligibility_1",
            evidence=(
                Evidence("ev_policy", "pol_1", "2026-09-01T00:00:00Z", StatementKind.POLICY_ID, "pol_1"),
                Evidence("ev_score", "pol_1", "2026-09-01T00:00:00Z", StatementKind.RISK_SCORE, "0.42"),
                Evidence("ev_action", "pol_1", "2026-09-01T00:00:00Z", StatementKind.RECOMMENDED_ACTION, "abstain"),
            ),
        )

    def test_matching_typed_evidence_renders_deterministically(self) -> None:
        statement = NarrativeStatement("s1", "pol_1", StatementKind.POLICY_ID, "pol_1", ("ev_policy",))
        expected = ("Policy Id: pol_1.",)
        self.assertEqual(render_statements(self.context, (statement,)), expected)
        self.assertEqual(render_statements(self.context, (statement,)), expected)

    def test_foreign_policy_fails_closed(self) -> None:
        statement = NarrativeStatement("s1", "pol_other", StatementKind.POLICY_ID, "pol_other", ("ev_policy",))
        with self.assertRaises(GroundingContractError) as raised:
            render_statements(self.context, (statement,))
        self.assertEqual(raised.exception.code, GroundingErrorCode.CONTEXT_MISMATCH)

    def test_unknown_value_cannot_be_rendered(self) -> None:
        statement = NarrativeStatement("s1", "pol_1", StatementKind.POLICY_ID, None, ("ev_policy",))
        with self.assertRaises(GroundingContractError) as raised:
            render_statements(self.context, (statement,))
        self.assertEqual(raised.exception.code, GroundingErrorCode.UNKNOWN_VALUE)

    def test_evidence_value_mismatch_fails(self) -> None:
        statement = NarrativeStatement("s1", "pol_1", StatementKind.POLICY_ID, "pol_fake", ("ev_policy",))
        with self.assertRaises(GroundingContractError) as raised:
            render_statements(self.context, (statement,))
        self.assertEqual(raised.exception.code, GroundingErrorCode.VALUE_INVALID)

    def test_provider_must_return_grammar_statements(self) -> None:
        with self.assertRaises(GroundingContractError) as raised:
            validate_provider_payload({"headline": "unsupported prose"}, self.context)
        self.assertEqual(raised.exception.code, GroundingErrorCode.PROVIDER_OUTPUT_INVALID)

    def test_provider_action_is_rendered_as_recommendation_not_authority(self) -> None:
        rendered = validate_provider_payload(
            {"statements": [{
                "statement_id": "s1",
                "policy_id": "pol_1",
                "kind": "RECOMMENDED_ACTION",
                "value": "abstain",
                "evidence_ids": ["ev_action"],
            }]},
            self.context,
        )
        self.assertEqual(rendered, ("Modeled recommended action: abstain.",))

    def test_legacy_adapter_is_explicitly_named_and_bound(self) -> None:
        class Legacy:
            policy_id = "pol_legacy"
            case_id = "case_legacy"
            as_of_date = "2026-09-01T00:00:00Z"
            product_type = "term_life"
            policy_status = "unknown"
            primary_action = "abstain"
            calibrated_probability = 0.2

        context = context_from_case_evidence(Legacy())
        self.assertEqual(context.snapshot_id, "legacy-case-evidence")
        self.assertTrue(all(item.identity == "legacy-adapter" for item in context.evidence))


if __name__ == "__main__":
    unittest.main()
