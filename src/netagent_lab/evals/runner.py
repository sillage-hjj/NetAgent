from __future__ import annotations

from typing import Any

from netagent_lab.agent.agent_loop import NetworkAgent
from netagent_lab.agent.planner import classify_question
from netagent_lab.agent.tool_registry import build_default_tool_registry
from netagent_lab.evals.rubrics import score_report
from netagent_lab.evals.scenarios import prepare_agent_scenario_db, scenario_question
from netagent_lab.llm.config import LLMProviderConfig, load_llm_config, resolve_provider
from netagent_lab.llm.mock_client import MockLLMClient


def run_agent_eval(db, scenario_name: str, provider: str = "mock") -> dict[str, Any]:
    question = scenario_question(scenario_name)
    config = _config(provider)
    client = MockLLMClient(script_name=scenario_name) if provider == "mock" else resolve_provider(config)
    agent = NetworkAgent(
        db=db,
        llm_client=client,
        tool_registry=build_default_tool_registry(db, config),
        config=config,
    )
    report = agent.run(question)
    score = score_report(report, scenario_name, db)
    return {"scenario": scenario_name, "passed": score["passed"], "score": score, "report": report.model_dump(mode="json")}


def run_all_agent_evals(provider: str = "mock") -> dict[str, Any]:
    scenarios = ["link_failure", "congestion", "route_withdrawal", "healthy_network_summary"]
    results = []
    for scenario in scenarios:
        conn = prepare_agent_scenario_db(scenario)
        try:
            results.append(run_agent_eval(conn, scenario, provider))
        finally:
            conn.close()
    return {"passed": all(item["passed"] for item in results), "results": results}


def _config(provider: str) -> LLMProviderConfig:
    config = load_llm_config().model_copy(update={"provider": provider})
    if provider == "mock":
        return config.model_copy(update={"model": None})
    return config
