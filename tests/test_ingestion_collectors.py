import json

from netagent_lab.db import get_current_tick, init_sim_db, initialize_runtime_state
from netagent_lab.ingestion.simulated_collectors import (
    collect_sim_all,
    collect_sim_link_states,
)
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_sim_collectors_return_json_serializable_collector_results() -> None:
    conn = _conn()

    results = collect_sim_all(conn)

    assert results
    for result in results:
        assert result.source == "simulation"
        assert result.ok is True
        json.dumps(result.model_dump(mode="json"))


def test_sim_collectors_do_not_mutate_tick() -> None:
    conn = _conn()
    before = get_current_tick(conn)

    collect_sim_all(conn)

    assert get_current_tick(conn) == before


def test_link_collector_contains_full_link_metadata() -> None:
    conn = _conn()

    result = collect_sim_link_states(conn)
    link = result.result["link_r1_r2"]

    required = {
        "link_id",
        "endpoint_a",
        "endpoint_b",
        "admin_state",
        "oper_state",
        "effective_state",
        "bandwidth_mbps",
        "latency_ms",
        "jitter_ms",
        "loss_percent",
        "utilization_percent",
        "error_rate_percent",
        "flap_count",
        "last_change_tick",
        "last_event_id",
        "failure_reason",
        "tags",
    }
    assert required <= set(link)


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

