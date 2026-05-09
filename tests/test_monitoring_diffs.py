from netfabric_mini.db import get_snapshot, init_sim_db, initialize_runtime_state
from netfabric_mini.monitoring.diff import diff_latest_snapshots
from netfabric_mini.monitoring.monitor import run_monitor_once
from netfabric_mini.sim.engine import SimulationEngine
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_link_down_diff_shows_changed_link() -> None:
    conn = _conn()
    run_monitor_once(conn)
    SimulationEngine.load(conn).inject_event("link_down", "link_r1_r2", {})
    run_monitor_once(conn)

    diff = diff_latest_snapshots(conn)

    assert any(change["id"] == "link_r1_r2" for change in diff["changed_links"])
    assert diff["new_alerts"]


def test_high_loss_diff_shows_changed_metric_and_alert() -> None:
    conn = _conn()
    run_monitor_once(conn)
    SimulationEngine.load(conn).inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 9})
    run_monitor_once(conn)

    diff = diff_latest_snapshots(conn)

    change = next(item for item in diff["changed_links"] if item["id"] == "link_r1_r2")
    assert change["after"]["loss_percent"] == 9
    assert any(alert["alert_type"] == "high_packet_loss" for alert in diff["new_alerts"])


def test_no_change_between_snapshots_has_minimal_diff() -> None:
    conn = _conn()
    run_monitor_once(conn)
    run_monitor_once(conn)

    diff = diff_latest_snapshots(conn)

    assert diff["changed_links"] == []


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

