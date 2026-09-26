import asyncio
import json
import unittest

from google.adk.models.base_llm import BaseLlm, LlmCapabilities
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from agents.adk_adapter import build_adk_agent, run_adk_draft
from agents.tests.test_adk_adapter import candidate, case


class FakeModel(BaseLlm):
    payload: str
    delay: float = 0.0
    fail: bool = False

    @property
    def capabilities(self):
        return LlmCapabilities(output_schema_and_tools=True)

    async def generate_content_async(self, llm_request, stream=False):
        if self.fail:
            raise RuntimeError("private model failure")
        await asyncio.sleep(self.delay)
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=self.payload)]),
                          turnComplete=True)


class ActualAdkRunnerTest(unittest.IsolatedAsyncioTestCase):
    async def test_agent_has_only_three_read_tools(self):
        agent = build_adk_agent(case(), FakeModel(model="fake", payload=json.dumps(candidate())))
        self.assertEqual([tool.name for tool in await agent.canonical_tools()],
                         ["read_case_evidence", "read_procedures", "read_rule_allowlist"])
        self.assertEqual(agent.mode, "chat")

    async def test_valid_and_mismatched_candidates(self):
        valid = await run_adk_draft(case(), FakeModel(model="fake", payload=json.dumps(candidate())))
        self.assertEqual(valid.status, "DRAFT_FOR_REVIEW")
        self.assertFalse(valid.authorized_to_act)
        bad = await run_adk_draft(case(), FakeModel(model="fake", payload=json.dumps({**candidate(), "action_id": "invented"})))
        self.assertEqual(bad.status, "ABSTAIN")

    async def test_timeout_and_model_error_abstain(self):
        timeout = await run_adk_draft(case(), FakeModel(model="fake", payload="{}", delay=0.1), timeout_seconds=0.01)
        self.assertEqual(timeout.reason_codes, ("ADK_TIMEOUT",))
        failed = await run_adk_draft(case(), FakeModel(model="fake", payload="{}", fail=True))
        self.assertEqual(failed.reason_codes, ("ADK_RUNTIME_FAILURE",))


if __name__ == "__main__":
    unittest.main()
