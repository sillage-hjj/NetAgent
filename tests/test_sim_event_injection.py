import pytest

from netagent_lab.db import get_current_tick, init_sim_db, initialize_runtime_state, list_sim_events
from netagent_lab.sim.engine import SimulationEngine
from netagent_lab.sim.state import SimulationStateStore
from netagent_lab.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_link_events_mutate_state_and_history() -> None:
    conn = _conn()
    engine = SimulationEngine.load(conn)

    down = engine.inject_event("link_down", "link_r1_r2", {"reason": "fiber_cut"})
    up = engine.inject_event("link_up", "link_r1_r2", {})

    state = SimulationStateStore.load(conn)
    assert state.get_link("link_r1_r2").oper_state == "up"
    assert [event["id"] for event in list_sim_events(conn)] == [down.id, up.id]
    assert down.id != up.id


@pytest.mark.parametrize(
    ("event_type", "target", "params", "field", "value"),
    [
        ("link_flap", "link_r1_r2", {"count": 2}, "flap_count", 2),
        ("set_link_latency", "link_r1_r2", {"latency_ms": 120}, "latency_ms", 120),
        ("set_link_loss", "link_r1_r2", {"loss_percent": 8}, "loss_percent", 8),
        ("set_link_utilization", "link_r1_r2", {"utilization_percent": 93}, "utilization_percent", 93),
        ("set_link_errors", "link_r1_r2", {"error_rate_percent": 6}, "error_rate_percent", 6),
    ],
)
def test_link_metric_events(event_type: str, target: str, params: dict, field: str, value: float) -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event(event_type, target, params)

    link = SimulationStateStore.load(conn).get_link(target)

    assert getattr(link, field) == value


def test_device_and_service_events() -> None:
    conn = _conn()
    engine = SimulationEngine.load(conn)

    engine.inject_event("set_device_cpu", "r2", {"cpu_utilization_percent": 91})
    engine.inject_event("set_device_memory", "r2", {"memory_utilization_percent": 92})
    engine.inject_event("service_degraded", "app_b", {"latency_ms": 180, "loss_percent": 2, "reason": "app slow"})

    state = SimulationStateStore.load(conn)
    assert state.get_device("r2").cpu_utilization_percent == 91
    assert state.get_device("r2").memory_utilization_percent == 92
    assert state.get_service("app_b").status == "degraded"


def test_tick_is_explicit() -> None:
    conn = _conn()
    engine = SimulationEngine.load(conn)
    engine.inject_event("link_down", "link_r1_r2", {})

    assert get_current_tick(conn) == 0
    assert engine.tick(2)["new_tick"] == 2
    assert get_current_tick(conn) == 2


def test_invalid_target_and_params_fail_clearly() -> None:
    conn = _conn()
    engine = SimulationEngine.load(conn)

    with pytest.raises(KeyError, match="Unknown link"):
        engine.inject_event("link_down", "missing", {})
    with pytest.raises(ValueError, match="loss_percent must be <= 100"):
        engine.inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 101})
    with pytest.raises(ValueError, match="Unsupported event type"):
        engine.inject_event("do_magic", "r1", {})


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

