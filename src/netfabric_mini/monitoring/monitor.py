from __future__ import annotations

import sqlite3
import time
from typing import Any

from netfabric_mini.orchestration.monitoring_workflow import run_monitoring_cycle
from netfabric_mini.sim.schemas import MonitoringSnapshot
from netfabric_mini.sim.snapshots import (
    create_monitoring_snapshot,
    save_monitoring_snapshot,
)


def run_monitor_once(conn: sqlite3.Connection) -> dict[str, Any]:
    cycle = run_monitoring_cycle(conn)
    return {
        "ok": True,
        "tick": cycle.tick,
        "telemetry_samples": cycle.export_refs["telemetry_samples"],
        "alerts": cycle.alerts,
        "snapshot_id": cycle.snapshot_id,
        "normalized_state_id": cycle.normalized_state_id,
    }


def run_monitor_loop(
    conn: sqlite3.Connection,
    interval_seconds: float,
    max_iterations: int | None = None,
) -> dict[str, Any]:
    iterations = 0
    snapshots: list[str] = []
    while max_iterations is None or iterations < max_iterations:
        result = run_monitor_once(conn)
        snapshots.append(result["snapshot_id"])
        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break
        time.sleep(interval_seconds)
    return {"ok": True, "iterations": iterations, "snapshots": snapshots}


def create_snapshot_only(conn: sqlite3.Connection) -> MonitoringSnapshot:
    snapshot = create_monitoring_snapshot(conn)
    save_monitoring_snapshot(conn, snapshot)
    return snapshot
