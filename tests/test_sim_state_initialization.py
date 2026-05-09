from netagent_lab.db import init_sim_db, initialize_runtime_state
from netagent_lab.sim.engine import SimulationEngine
from netagent_lab.sim.state import SimulationStateStore
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_initial_state_matches_topology() -> None:
    conn = _conn()

    state = SimulationStateStore.load(conn)

    assert len(state.list_devices()) == 5
    assert len(state.list_links()) == 5
    assert state.effective_link_up("link_r1_r2") is True


def test_device_down_makes_attached_links_unavailable() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("device_down", "r2", {})

    state = SimulationStateStore.load(conn)

    assert state.effective_device_up("r2") is False
    assert state.effective_link_up("link_r1_r2") is False
    assert state.effective_link_up("link_r2_r3") is False


def test_interface_down_makes_connected_link_unavailable() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("interface_down", "r1:eth1", {})

    state = SimulationStateStore.load(conn)

    assert state.effective_link_up("link_r1_r2") is False


def test_link_degradation_keeps_link_available() -> None:
    conn = _conn()
    engine = SimulationEngine.load(conn)
    engine.inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 12})

    state = SimulationStateStore.load(conn)

    assert state.effective_link_up("link_r1_r2") is True
    assert state.get_link("link_r1_r2").loss_percent == 12


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

