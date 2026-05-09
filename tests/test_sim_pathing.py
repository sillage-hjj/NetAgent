from netfabric_mini.db import init_sim_db, initialize_runtime_state
from netfabric_mini.sim.engine import SimulationEngine
from netfabric_mini.sim.pathing import check_service_reachability, infer_simulated_path
from netfabric_mini.sim.state import SimulationStateStore
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_path_exists_initially() -> None:
    conn = _conn("simple_branch_app.yaml")
    state = SimulationStateStore.load(conn)

    result = infer_simulated_path(state, "client_zurich", "app_b")

    assert result["reachable"] is True
    assert result["links"] == ["link_client_r1", "link_r1_r2", "link_r2_r3", "link_r3_app_b"]


def test_backup_path_used_when_primary_link_fails() -> None:
    conn = _conn("simple_branch_app.yaml")
    SimulationEngine.load(conn).inject_event("link_down", "link_r1_r2", {"reason": "fiber_cut"})
    state = SimulationStateStore.load(conn)

    result = infer_simulated_path(state, "client_zurich", "app_b")

    assert result["reachable"] is True
    assert "link_r1_r3_backup" in result["links"]


def test_device_down_makes_service_unreachable() -> None:
    conn = _conn("simple_branch_app.yaml")
    SimulationEngine.load(conn).inject_event("device_down", "app_b", {})
    state = SimulationStateStore.load(conn)

    result = check_service_reachability(state, "client_zurich", "app_b")

    assert result["reachable"] is False
    assert result["blocking_reasons"][0]["type"] == "service_down"


def test_high_loss_degrades_path_but_does_not_make_it_unreachable() -> None:
    conn = _conn("simple_branch_app.yaml")
    SimulationEngine.load(conn).inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 12})
    state = SimulationStateStore.load(conn)

    result = infer_simulated_path(state, "client_zurich", "app_b")

    assert result["reachable"] is True
    assert result["degraded"] is True
    assert result["degradation_reasons"][0]["type"] == "packet_loss"


def test_route_withdrawal_blocks_reachability_without_link_down() -> None:
    conn = _conn("simple_branch_app.yaml")
    SimulationEngine.load(conn).inject_event(
        "route_withdrawal",
        "routeblock-1",
        {"source_device": "client_zurich", "target_service": "app_b", "reason": "bgp_withdrawal"},
    )
    state = SimulationStateStore.load(conn)

    result = check_service_reachability(state, "client_zurich", "app_b")

    assert result["reachable"] is False
    assert result["blocking_reasons"][0]["type"] == "route_withdrawal"
    assert state.effective_link_up("link_r1_r2") is True


def _conn(topology_name: str):
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / topology_name)
    initialize_runtime_state(conn, topology)
    return conn

