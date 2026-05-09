from __future__ import annotations

import json

from typer.testing import CliRunner

from netfabric_mini.cli import app


runner = CliRunner()


def test_agent_tools_cli() -> None:
    result = runner.invoke(app, ["agent", "tools"])
    assert result.exit_code == 0
    assert "get_current_context" in result.stdout


def test_agent_config_cli_redacts() -> None:
    result = runner.invoke(app, ["agent", "config"])
    assert result.exit_code == 0
    assert "api_key" in result.stdout
    assert "OPENAI_API_KEY" not in result.stdout


def test_agent_demo_link_failure_json() -> None:
    result = runner.invoke(app, ["agent", "demo", "--scenario", "link_failure", "--provider", "mock", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["evidence"]
    assert "link" in payload["summary"].lower()


def test_agent_eval_json_cli_includes_relevance() -> None:
    result = runner.invoke(app, ["agent", "eval", "--provider", "mock", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    assert payload["results"][0]["score"]["evidence_relevance"]


def test_ui_help_cli_does_not_require_streamlit() -> None:
    result = runner.invoke(app, ["ui", "--help"])
    assert result.exit_code == 0
    assert "--db" in result.stdout
