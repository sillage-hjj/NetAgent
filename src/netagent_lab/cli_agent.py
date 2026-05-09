from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from netagent_lab.agent.agent_loop import NetworkAgent
from netagent_lab.agent.approvals import approve_request, list_pending_approvals, reject_request
from netagent_lab.agent.planner import classify_question
from netagent_lab.agent.report_renderer import render_agent_report_json, render_agent_report_markdown, render_agent_report_text
from netagent_lab.agent.run_store import list_runs, list_tool_calls
from netagent_lab.agent.session_store import ensure_agent_tables
from netagent_lab.agent.tool_registry import build_default_tool_registry
from netagent_lab.db import connect_db, init_sim_db
from netagent_lab.evals.runner import run_all_agent_evals
from netagent_lab.evals.scenarios import prepare_agent_scenario_db, scenario_question
from netagent_lab.llm.config import DEFAULT_OPENAI_MODEL, LLMProviderConfig, load_llm_config, redacted_diagnostics, resolve_provider
from netagent_lab.llm.mock_client import MockLLMClient


agent_app = typer.Typer(name="agent", help="LLM-powered evidence-grounded network agent.")
approvals_app = typer.Typer(name="approvals", help="Approval queue for simulated mutations.")
agent_app.add_typer(approvals_app, name="approvals")


@agent_app.command("config")
def config_command() -> None:
    config = load_llm_config()
    typer.echo(json.dumps(redacted_diagnostics(config), indent=2, sort_keys=True))


@agent_app.command("tools")
def tools_command(provider: str = typer.Option("mock", "--provider")) -> None:
    conn = init_sim_db(":memory:")
    config = _config(provider)
    registry = build_default_tool_registry(conn, config)
    payload = [
        {
            "name": tool.name,
            "read_only": tool.read_only,
            "requires_approval": tool.requires_approval,
            "description": tool.description,
        }
        for tool in registry.list_tools()
    ]
    conn.close()
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@agent_app.command("ask")
def ask_command(
    db: Path = typer.Option(..., "--db"),
    question: str = typer.Option(..., "--question"),
    provider: str = typer.Option("mock", "--provider"),
    output_format: str = typer.Option("markdown", "--format"),
) -> None:
    conn = connect_db(db)
    report = _run_agent(conn, question, provider, _script_for_question(question))
    conn.close()
    typer.echo(_render(report, output_format))


@agent_app.command("investigate")
def investigate_command(
    db: Path = typer.Option(..., "--db"),
    source: str = typer.Option(..., "--source"),
    service: str = typer.Option(..., "--service"),
    provider: str = typer.Option("mock", "--provider"),
    output_format: str = typer.Option("markdown", "--format"),
) -> None:
    question = f"Why is {service} unreachable or degraded from {source}?"
    conn = connect_db(db)
    report = _run_agent(conn, question, provider, "link_failure", {"source_device": source, "service_id": service})
    conn.close()
    typer.echo(_render(report, output_format))


@agent_app.command("monitor-summary")
def monitor_summary_command(
    db: Path = typer.Option(..., "--db"),
    provider: str = typer.Option("mock", "--provider"),
    output_format: str = typer.Option("markdown", "--format"),
) -> None:
    conn = connect_db(db)
    report = _run_agent(conn, "Summarize active network alerts and risk.", provider, "healthy_network_summary")
    conn.close()
    typer.echo(_render(report, output_format))


@agent_app.command("chat")
def chat_command(
    db: Path = typer.Option(..., "--db"),
    session: Optional[str] = typer.Option(None, "--session"),
    provider: str = typer.Option("mock", "--provider"),
) -> None:
    conn = connect_db(db)
    typer.echo("NetAgent Lab agent chat. Type 'exit' to stop.")
    while True:
        question = typer.prompt("question")
        if question.lower() in {"exit", "quit"}:
            break
        report = _run_agent(conn, question, provider, _script_for_question(question), session_id=session)
        typer.echo(render_agent_report_markdown(report))
    conn.close()


@agent_app.command("runs")
def runs_command(db: Path = typer.Option(..., "--db")) -> None:
    conn = connect_db(db)
    ensure_agent_tables(conn)
    payload = list_runs(conn)
    conn.close()
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@agent_app.command("trace")
def trace_command(
    db: Path = typer.Option(..., "--db"),
    run: str = typer.Option(..., "--run"),
) -> None:
    conn = connect_db(db)
    payload = list_tool_calls(conn, run)
    conn.close()
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@approvals_app.command("list")
def approvals_list_command(db: Path = typer.Option(..., "--db")) -> None:
    conn = connect_db(db)
    payload = list_pending_approvals(conn)
    conn.close()
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@approvals_app.command("approve")
def approvals_approve_command(
    approval_id: str,
    db: Path = typer.Option(..., "--db"),
) -> None:
    conn = connect_db(db)
    payload = approve_request(conn, approval_id).model_dump(mode="json")
    conn.close()
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@approvals_app.command("reject")
def approvals_reject_command(
    approval_id: str,
    db: Path = typer.Option(..., "--db"),
) -> None:
    conn = connect_db(db)
    payload = reject_request(conn, approval_id).model_dump(mode="json")
    conn.close()
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@agent_app.command("demo")
def demo_command(
    scenario: str = typer.Option("link_failure", "--scenario"),
    provider: str = typer.Option("mock", "--provider"),
    output_format: str = typer.Option("markdown", "--format"),
) -> None:
    conn = prepare_agent_scenario_db(scenario)
    report = _run_agent(conn, scenario_question(scenario), provider, scenario)
    conn.close()
    typer.echo(_render(report, output_format))


@agent_app.command("eval")
def eval_command(
    provider: str = typer.Option("mock", "--provider"),
    output_format: str = typer.Option("json", "--format"),
) -> None:
    payload = run_all_agent_evals(provider)
    if output_format == "json":
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return
    if output_format == "text":
        for result in payload["results"]:
            relevance = result["score"].get("evidence_relevance", {})
            typer.echo(
                f"{result['scenario']}: passed={result['passed']} "
                f"grounding={relevance.get('overall_grounding_score')} "
                f"missing={relevance.get('missing_expected_evidence', [])}"
            )
        return
    raise typer.BadParameter("format must be json or text")


def _run_agent(conn, question: str, provider: str, script_name: str, focus: dict | None = None, session_id: str | None = None):
    config = _config(provider)
    client = MockLLMClient(script_name=script_name) if provider == "mock" else resolve_provider(config)
    registry = build_default_tool_registry(conn, config)
    agent = NetworkAgent(db=conn, llm_client=client, tool_registry=registry, config=config)
    return agent.run(question, session_id=session_id, focus=focus)


def _config(provider: str) -> LLMProviderConfig:
    config = load_llm_config().model_copy(update={"provider": provider})
    if provider == "openai" and not config.model:
        config = config.model_copy(update={"model": DEFAULT_OPENAI_MODEL})
    if provider == "mock":
        config = config.model_copy(update={"model": None})
    return config


def _script_for_question(question: str) -> str:
    category = classify_question(question)["category"]
    if category in {"service_degraded", "congestion"}:
        return "congestion"
    if category == "route_withdrawal":
        return "route_withdrawal"
    if category in {"service_unreachable", "link_failure"}:
        return "link_failure"
    return "healthy_network_summary"


def _render(report, output_format: str) -> str:
    normalized = output_format.lower()
    if normalized == "json":
        return json.dumps(render_agent_report_json(report), indent=2, sort_keys=True)
    if normalized == "text":
        return render_agent_report_text(report)
    if normalized == "markdown":
        return render_agent_report_markdown(report)
    raise typer.BadParameter("format must be markdown, text, or json")
