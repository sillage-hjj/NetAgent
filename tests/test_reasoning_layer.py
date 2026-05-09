from netfabric_mini.db import init_sim_db, initialize_runtime_state
from netfabric_mini.knowledge.store import KnowledgeBase
from netfabric_mini.monitoring.monitor import run_monitor_once
from netfabric_mini.reasoning.alerts import evaluate_alerts
from netfabric_mini.reasoning.diff import diff_latest_snapshots
from netfabric_mini.reasoning.health import evaluate_link_health, evaluate_path_health
from netfabric_mini.reasoning.pathing import infer_path
from netfabric_mini.reasoning.reachability import check_service_reachability
from netfabric_mini.sim.engine import SimulationEngine
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def test_reasoning_path_and_backup_path() -> None:
    conn = _conn()
    kb = KnowledgeBase.from_db(conn)
    assert infer_path(kb, "client_zurich", "app_b")["links"] == [
        "link_client_r1",
        "link_r1_r2",
        "link_r2_r3",
        "link_r3_app_b",
    ]

    SimulationEngine.load(conn).inject_event("link_down", "link_r1_r2", {})
    result = infer_path(KnowledgeBase.from_db(conn), "client_zurich", "app_b")

    assert result["reachable"] is True
    assert "link_r1_r3_backup" in result["links"]
    assert result["evidence"]


def test_reasoning_degraded_path_and_health() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 9})
    kb = KnowledgeBase.from_db(conn)

    path_result = infer_path(kb, "client_zurich", "app_b")

    assert path_result["degraded"] is True
    assert evaluate_path_health(path_result)["status"] == "degraded"
    assert evaluate_link_health(kb, "link_r1_r2")["status"] == "degraded"


def test_reasoning_route_withdrawal_blocks_service_but_not_physical_path() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event(
        "route_withdrawal",
        "routeblock-1",
        {"source_device": "client_zurich", "target_service": "app_b", "reason": "bgp_withdrawal"},
    )
    kb = KnowledgeBase.from_db(conn)

    service = check_service_reachability(kb, "client_zurich", "app_b")
    physical = infer_path(kb, "client_zurich", "app_b")

    assert service["reachable"] is False
    assert physical["reachable"] is True


def test_reasoning_alerts_are_evidence_grounded() -> None:
    conn = _conn()
    SimulationEngine.load(conn).inject_event("link_down", "link_r1_r2", {})

    alerts = evaluate_alerts(KnowledgeBase.from_db(conn))

    assert any(alert["alert_type"] == "link_down" for alert in alerts)
    assert all(alert["evidence"] for alert in alerts)


def test_reasoning_diff_identifies_changed_link_alert_and_event() -> None:
    conn = _conn()
    run_monitor_once(conn)
    SimulationEngine.load(conn).inject_event("link_down", "link_r1_r2", {})
    run_monitor_once(conn)

    diff = diff_latest_snapshots(KnowledgeBase.from_db(conn))

    assert any(change["id"] == "link_r1_r2" for change in diff["changed_links"])
    assert diff["new_alerts"]
    assert diff["new_events"]
    assert diff["evidence"]


def _conn():
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / "simple_branch_app.yaml")
    initialize_runtime_state(conn, topology)
    return conn

