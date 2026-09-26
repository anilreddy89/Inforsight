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

P5-02 adds an opt-in ADK adapter in `adk_adapter.py`. It runs with three
case-scoped read-only tools and validates a JSON candidate against the P5-01
deterministic result. A mismatch, malformed response, timeout, or model error
abstains. No model output can authorize action. `make p5-02-check` needs no
ADK installation. For the offline fake-model runner test, install
`agents/requirements-adk.txt` in an isolated environment and run
`make p5-02-adk-check PYTHON=python`. This does not call a provider.

The [Phase 5 plan](../Documents/phase_docs/phase-05-agentic-case-workflow-plan.md)
separates the foundation and ADK adapter from later service integration.

P5-03's `control_plane_bridge.py` formats a validated `ReviewDraft` for the
Java case review endpoint. Submission requires an explicit transport; the
optional HTTP helper is restricted to the local control plane. The Java
endpoint treats every submitted draft as untrusted advisory data and never
uses it as a human approval or action authorization. Run `make p5-03-check`;
the Docker-backed persistence test is `make p5-03-integration-check`.
