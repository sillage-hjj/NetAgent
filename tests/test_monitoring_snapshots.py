from netfabric_mini.db import get_snapshot, init_sim_db, initialize_runtime_state, list_snapshots, list_telemetry_samples
from netfabric_mini.monitoring.monitor import run_monitor_once
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_monitor_once_creates_telemetry_and_snapshot_with_link_metadata() -> None:
    conn = _conn()

    result = run_monitor_once(conn)

    assert result["telemetry_samples"] > 0
    assert list_telemetry_samples(conn)
    snapshot = get_snapshot(conn, result["snapshot_id"])
    assert snapshot["links"]["link_r1_r2"]["endpoint_a"]["device"] == "r1"


def test_running_monitor_twice_creates_two_snapshots_and_aliases_work() -> None:
    conn = _conn()

    run_monitor_once(conn)
    run_monitor_once(conn)

    assert len(list_snapshots(conn)) == 2
    assert get_snapshot(conn, "latest")["id"].endswith("0002")
    assert get_snapshot(conn, "latest-1")["id"].endswith("0001")


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

