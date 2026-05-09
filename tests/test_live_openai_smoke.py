from __future__ import annotations

import os

import pytest

from netagent_lab.agent.agent_loop import NetworkAgent
from netagent_lab.agent.tool_registry import build_default_tool_registry
from netagent_lab.evals.scenarios import prepare_agent_scenario_db
from netagent_lab.llm.config import load_llm_config, resolve_provider


@pytest.mark.live_openai
def test_live_openai_agent_smoke_is_opt_in(monkeypatch) -> None:
    if not (os.getenv("OPENAI_API_KEY") and os.getenv("RUN_LIVE_OPENAI_TESTS") == "1"):
        pytest.skip("Live OpenAI smoke test is opt-in.")
    monkeypatch.setenv("NFM_AGENT_PROVIDER", "openai")
    conn = prepare_agent_scenario_db("link_failure")
    try:
        config = load_llm_config().model_copy(update={"max_tool_calls": 4, "max_output_tokens": 800})
        agent = NetworkAgent(
            db=conn,
            llm_client=resolve_provider(config),
            tool_registry=build_default_tool_registry(conn, config),
            config=config,
        )

        report = agent.run("Why is App-B unreachable from Zurich?")

        assert report.evidence
        assert report.tool_trace_ids
        assert "No remediation was executed." in report.guardrail_notes
    finally:
        conn.close()
