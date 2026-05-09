import json

from netagent_lab.db import init_sim_db, initialize_runtime_state
from netagent_lab.monitoring.monitor import run_monitor_once
from netagent_lab.sim.engine import SimulationEngine
from netagent_lab.sim.exporters import (
    export_current_state_json,
    export_events_jsonl,
    export_latest_snapshot_json,
    export_llm_ready_context,
    export_telemetry_jsonl,
)
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_exports_are_json_serializable() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 7})
    run_monitor_once(conn)

    json.dumps(export_current_state_json(conn))
    json.dumps(export_latest_snapshot_json(conn))


def test_jsonl_exports_have_one_json_object_per_line() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("link_down", "link_r1_r2", {})
    run_monitor_once(conn)

    for payload in [export_events_jsonl(conn), export_telemetry_jsonl(conn)]:
        lines = payload.splitlines()
        assert lines
        for line in lines:
            assert isinstance(json.loads(line), dict)


def test_llm_ready_context_contains_no_prompt_and_includes_evidence() -> None:
    conn = _conn()
    run_monitor_once(conn)

    context = export_llm_ready_context(conn)

    assert "prompt" not in context
    assert "link_state_metadata" in context
    assert context["evidence_ids"]


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

