import json
from pathlib import Path

from typer.testing import CliRunner

from netagent_lab.cli import app


def test_sim_list_topologies() -> None:
    result = CliRunner().invoke(app, ["sim", "list-topologies"])

    assert result.exit_code == 0
    assert "simple_branch_app" in result.output


def test_sim_validate() -> None:
    result = CliRunner().invoke(
        app,
        ["sim", "validate", "--topology", "data/topologies/simple_branch_app.yaml"],
    )

    assert result.exit_code == 0
    assert "valid: simple_branch_app" in result.output


def test_sim_init_monitor_export_json(tmp_path: Path) -> None:
    db = tmp_path / "sim.db"
    runner = CliRunner()

    init_result = runner.invoke(
        app,
        [
            "sim",
            "init",
            "--topology",
            "data/topologies/simple_branch_app.yaml",
            "--db",
            str(db),
        ],
    )
    monitor_result = runner.invoke(app, ["sim", "monitor", "--db", str(db), "--once"])
    export_result = runner.invoke(app, ["sim", "export", "--db", str(db), "--format", "json"])

    assert init_result.exit_code == 0
    assert monitor_result.exit_code == 0
    assert export_result.exit_code == 0
    payload = json.loads(export_result.output)
    assert payload["inventory"]["topology_name"] == "simple_branch_app"


def test_sim_export_llm_context_is_budgeted_and_evidence_grounded(tmp_path: Path) -> None:
    db = tmp_path / "sim.db"
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "sim",
            "init",
            "--topology",
            "data/topologies/simple_branch_app.yaml",
            "--db",
            str(db),
        ],
    )
    runner.invoke(app, ["sim", "monitor", "--db", str(db), "--once"])

    result = runner.invoke(app, ["sim", "export", "--db", str(db), "--format", "llm-context"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "budget" in payload
    assert "evidence_refs" in payload
    assert "prompt" not in payload


def test_sim_scenario_link_failure_prints_link_down_alert() -> None:
    result = CliRunner().invoke(app, ["sim", "scenario", "--name", "link_failure"])

    assert result.exit_code == 0
    assert "link_down" in result.output


def test_sim_scenario_congestion_prints_loss_or_util_alert() -> None:
    result = CliRunner().invoke(app, ["sim", "scenario", "--name", "congestion"])

    assert result.exit_code == 0
    assert "high_utilization" in result.output or "high_packet_loss" in result.output


def test_sim_scenario_route_withdrawal_prints_unreachable() -> None:
    result = CliRunner().invoke(app, ["sim", "scenario", "--name", "route_withdrawal"])

    assert result.exit_code == 0
    assert "probe_unreachable" in result.output
