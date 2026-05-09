from __future__ import annotations

from netagent_lab.agent.agent_loop import NetworkAgent
from netagent_lab.agent.tool_registry import build_default_tool_registry
from netagent_lab.evals.scenarios import prepare_agent_scenario_db
from netagent_lab.llm.config import LLMProviderConfig
from netagent_lab.llm.mock_client import MockLLMClient


def _run(scenario: str):
    conn = prepare_agent_scenario_db(scenario)
    config = LLMProviderConfig(provider="mock")
    agent = NetworkAgent(
        db=conn,
        llm_client=MockLLMClient(script_name=scenario),
        tool_registry=build_default_tool_registry(conn, config),
        config=config,
    )
    return agent.run("Why is App-B unreachable from Zurich?")


def test_agent_loop_link_failure_mock() -> None:
    report = _run("link_failure")
    assert report.answer_type == "network_investigation"
    assert report.evidence
    assert report.tool_trace_ids
    assert "link" in report.summary.lower()


def test_agent_loop_congestion_mock() -> None:
    report = _run("congestion")
    assert "degraded" in report.summary.lower() or "congestion" in report.summary.lower()
    assert report.evidence


def test_agent_loop_route_withdrawal_mock() -> None:
    report = _run("route_withdrawal")
    assert "route" in report.summary.lower()
    assert report.evidence

