from netfabric_mini.db import init_sim_db, initialize_runtime_state
from netfabric_mini.monitoring.monitor import run_monitor_once
from netfabric_mini.sim.engine import SimulationEngine
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_normal_initial_state_has_no_critical_alerts() -> None:
    conn = _conn()

    result = run_monitor_once(conn)

    assert not [alert for alert in result["alerts"] if alert["severity"] == "critical"]


def test_link_down_creates_alert() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("link_down", "link_r1_r2", {})

    result = run_monitor_once(conn)

    assert any(alert["alert_type"] == "link_down" for alert in result["alerts"])


def test_high_loss_creates_warning() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 9})

    result = run_monitor_once(conn)

    assert any(alert["alert_type"] == "high_packet_loss" and alert["severity"] == "warning" for alert in result["alerts"])


def test_critical_service_unreachable_creates_critical_alert() -> None:
    conn = _conn()
    engine = SimulationEngine.load(conn)
    engine.inject_event("link_down", "link_r1_r2", {})
    engine.inject_event("link_down", "link_r1_r3_backup", {})

    result = run_monitor_once(conn)

    assert any(alert["alert_type"] == "probe_unreachable" and alert["severity"] == "critical" for alert in result["alerts"])


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

