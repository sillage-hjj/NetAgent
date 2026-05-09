import json

from netagent_lab.db import get_current_tick, init_sim_db, initialize_runtime_state
from netagent_lab.monitoring.collectors import (
    collect_link_states,
    collect_probe_results,
    collect_reachability_matrix,
)
from netagent_lab.sim.engine import SimulationEngine
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_collectors_are_json_serializable_and_read_only() -> None:
    conn = _conn()
    before = get_current_tick(conn)

    result = collect_link_states(conn)

    assert result["collector"] == "collect_link_states"
    assert result["ok"] is True
    assert get_current_tick(conn) == before
    json.dumps(result)


def test_link_collector_exposes_required_metadata() -> None:
    conn = _conn()

    link = collect_link_states(conn)["result"]["link_r1_r2"]

    assert link["endpoint_a"]["device"] == "r1"
    assert "effective_state" in link
    assert "failure_reason" in link


def test_probe_and_matrix_reflect_link_down() -> None:
    conn = _conn()
    engine = SimulationEngine.load(conn)
    engine.inject_event("link_down", "link_r1_r2", {})
    engine.inject_event("link_down", "link_r1_r3_backup", {})

    probes = collect_probe_results(conn)["result"]
    matrix = collect_reachability_matrix(conn)["result"]

    assert probes["probe_zurich_app_b_https"]["reachable"] is False
    assert matrix["services"]["client_zurich->app_b"]["reachable"] is False


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

