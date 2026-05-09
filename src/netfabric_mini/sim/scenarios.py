from __future__ import annotations

import sqlite3
from typing import Any

from netfabric_mini.db import init_sim_db, initialize_runtime_state
from netfabric_mini.monitoring.collectors import collect_reachability_matrix
from netfabric_mini.monitoring.diff import diff_latest_snapshots
from netfabric_mini.monitoring.monitor import run_monitor_once
from netfabric_mini.sim.engine import SimulationEngine
from netfabric_mini.sim.topology_loader import DEFAULT_TOPOLOGIES_DIR, load_topology


def run_scenario(name: str) -> dict[str, Any]:
    if name == "link_failure":
        return _link_failure()
    if name == "backup_path_failover":
        return _backup_path_failover()
    if name == "congestion":
        return _congestion()
    if name == "device_failure":
        return _device_failure()
    if name == "route_withdrawal":
        return _route_withdrawal()
    raise ValueError(f"Unknown scenario: {name}")


def _link_failure() -> dict[str, Any]:
    conn = _scenario_conn("simple_branch_app.yaml")
    baseline = run_monitor_once(conn)
    engine = SimulationEngine.load(conn)
    event = engine.inject_event("link_down", "link_r1_r2", {"reason": "fiber_cut"})
    engine.tick(1)
    final = run_monitor_once(conn)
    return _summary(conn, "link_failure", baseline, final, [event.id])


def _backup_path_failover() -> dict[str, Any]:
    conn = _scenario_conn("ring_with_backup.yaml")
    baseline = run_monitor_once(conn)
    engine = SimulationEngine.load(conn)
    event = engine.inject_event("link_down", "link_r1_r2", {"reason": "ring_link_failure"})
    engine.tick(1)
    final = run_monitor_once(conn)
    return _summary(conn, "backup_path_failover", baseline, final, [event.id])


def _congestion() -> dict[str, Any]:
    conn = _scenario_conn("simple_branch_app.yaml")
    baseline = run_monitor_once(conn)
    engine = SimulationEngine.load(conn)
    event1 = engine.inject_event("set_link_utilization", "link_r1_r2", {"utilization_percent": 93})
    event2 = engine.inject_event("set_link_loss", "link_r1_r2", {"loss_percent": 9})
    event3 = engine.inject_event("set_link_latency", "link_r1_r2", {"latency_ms": 120})
    engine.tick(1)
    final = run_monitor_once(conn)
    return _summary(conn, "congestion", baseline, final, [event1.id, event2.id, event3.id])


def _device_failure() -> dict[str, Any]:
    conn = _scenario_conn("simple_branch_app.yaml")
    baseline = run_monitor_once(conn)
    engine = SimulationEngine.load(conn)
    event = engine.inject_event("device_down", "r2", {})
    engine.tick(1)
    final = run_monitor_once(conn)
    return _summary(conn, "device_failure", baseline, final, [event.id])


def _route_withdrawal() -> dict[str, Any]:
    conn = _scenario_conn("simple_branch_app.yaml")
    baseline = run_monitor_once(conn)
    engine = SimulationEngine.load(conn)
    event = engine.inject_event(
        "route_withdrawal",
        "routeblock-1",
        {"source_device": "client_zurich", "target_service": "app_b", "reason": "bgp_withdrawal"},
    )
    engine.tick(1)
    final = run_monitor_once(conn)
    return _summary(conn, "route_withdrawal", baseline, final, [event.id])


def _scenario_conn(topology_file: str) -> sqlite3.Connection:
    conn = init_sim_db(":memory:")
    topology = load_topology(DEFAULT_TOPOLOGIES_DIR / topology_file)
    initialize_runtime_state(conn, topology)
    return conn


def _summary(
    conn: sqlite3.Connection,
    name: str,
    baseline: dict[str, Any],
    final: dict[str, Any],
    event_ids: list[str],
) -> dict[str, Any]:
    diff = diff_latest_snapshots(conn)
    reachability = collect_reachability_matrix(conn)["result"]
    return {
        "scenario": name,
        "baseline_snapshot_id": baseline["snapshot_id"],
        "final_snapshot_id": final["snapshot_id"],
        "event_ids": event_ids,
        "alerts": final["alerts"],
        "diff_summary": diff["summary"],
        "diff": diff,
        "reachability": reachability,
    }

