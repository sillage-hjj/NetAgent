from __future__ import annotations

import json

from netagent_lab.agent.agent_loop import NetworkAgent
from netagent_lab.agent.tool_registry import build_default_tool_registry
from netagent_lab.db import init_sim_db, initialize_runtime_state
from netagent_lab.evals.scenarios import prepare_agent_scenario_db
from netagent_lab.llm.config import LLMProviderConfig
from netagent_lab.llm.mock_client import MockLLMClient
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology
from netagent_lab.ui import data_access


def _conn_with_agent_run():
    conn = prepare_agent_scenario_db("link_failure")
    config = LLMProviderConfig(provider="mock")
    agent = NetworkAgent(
        db=conn,
        llm_client=MockLLMClient(script_name="link_failure"),
        tool_registry=build_default_tool_registry(conn, config),
        config=config,
    )
    agent.run("Why is App-B unreachable from Zurich?")
    return conn


def test_ui_overview_and_state_are_redacted() -> None:
    conn = prepare_agent_scenario_db("link_failure")

    overview = data_access.get_overview(conn)
    state = data_access.get_simulation_state(conn)

    assert overview["topology_name"] == "simple_branch_app"
    assert "link_r1_r2" in state["links"]
    assert "management_ip" not in json.dumps(state).lower()


def test_ui_snapshot_diff_data() -> None:
    conn = prepare_agent_scenario_db("link_failure")

    payload = data_access.get_snapshots_and_diff(conn)

    assert payload["snapshots"]
    assert payload["diff"]["changed_links"]


def test_ui_agent_run_trace_and_evidence_explorer() -> None:
    conn = _conn_with_agent_run()

    runs = data_access.list_agent_runs_readonly(conn)
    run_id = runs[0]["run_id"]
    trace = data_access.get_tool_trace(conn, run_id)
    evidence = data_access.get_evidence_explorer(conn, run_id)

    assert runs[0]["final_report"]["evidence"]
    assert trace
    assert evidence["evidence"]
    assert any(item["exists"] for item in evidence["evidence"])


def test_ui_mock_evals_data() -> None:
    payload = data_access.run_mock_evals_for_ui()
    assert payload["passed"] is True
    assert payload["results"][0]["score"]["evidence_relevance"]


def test_connect_readonly_uses_readonly_uri(tmp_path) -> None:
    db_path = tmp_path / "sim.db"
    conn = init_sim_db(db_path)
    initialize_runtime_state(conn, load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml"))
    conn.close()

    readonly = data_access.connect_readonly(db_path)
    try:
        assert data_access.get_overview(readonly)["topology_name"] == "simple_branch_app"
    finally:
        readonly.close()
