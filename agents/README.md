# Phase 5 bounded agent workflow

P5-01 provides a deterministic, fictional-data foundation for Evidence,
Procedure, and Conservation Planner agents. It does **not** call a model,
Google ADK, a CRM, or any external action tool. `workflow.py` defines a
versioned review-only contract; `tests/test_workflow.py` exercises fail-closed
behavior. Run `make p5-01-check` from the repository root.

The planner receives allowed actions only from a trusted deterministic rules
result. Procedure text is untrusted evidence, never an instruction source.
Missing/conflicting facts, stale procedures, injection indicators, adapter
deadline failures, oversized inputs,
and low confidence produce abstention. Even a recommendation has
`authorized_to_act=false` and requires human review; rejection or override is
handled by the existing governed decision workflow, not this module.
The injected deadline callback is checked at each seam; this local module
does not itself schedule or cancel external tool calls.

The [Phase 5 plan](../Documents/phase_docs/phase-05-agentic-case-workflow-plan.md)
separates this foundation from later ADK orchestration and service integration.
